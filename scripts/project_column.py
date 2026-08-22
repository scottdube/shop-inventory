"""Populate a 'Project' parameter on parts, so the parts table can show it.

Scott wanted a Project column in the parts list — which project(s) have used
this part. InvenTree has no project concept and no plugin hook for custom table
columns (the UI mixin offers panels and dashboard items, not columns). What it
DOES have is part parameters, which the parts table can display as columns. So
the answer is a parameter named 'Project', rebuilt from the data.

    itq run scripts/project_column.py            # dry run
    itq run scripts/project_column.py --commit

Three sources, in descending order of how much they prove:

1. **`belongs_to`** — the part is physically installed inside an assembly.
   Proof: someone put it there and the record says which unit.
2. **`CONSUMED BY:` notes** — Scott answered "what used the missing ones?"
   during a count, recorded by scripts/unaccounted.py. Testimony, not proof,
   but from the one person who knows and at the only moment he could say.
3. **Build BOM lines** — the project's design calls for this part. This is a
   PLAN. A pending build has consumed nothing, so those are marked with a
   trailing '?' rather than being presented as history.

The distinction is kept in the value itself because a column that mixes "this
is inside a finished device" with "some project intends to use this someday"
is worse than no column: it reads as fact and is half intention.
"""
import argparse, os, re, sys, django
from collections import defaultdict

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

import django.apps as apps
from django.contrib.contenttypes.models import ContentType
from part.models import Part
from stock.models import StockItem
from build.models import BuildLine

ParameterTemplate = apps.apps.get_model("common", "ParameterTemplate")
Parameter = apps.apps.get_model("common", "Parameter")

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
ap.add_argument("--name", default="Project")
a = ap.parse_args()

tmpl = ParameterTemplate.objects.filter(name=a.name).first()
if tmpl is None:
    print(f"  template {a.name!r} does not exist yet"
          f"{' — creating' if a.commit else ' (would create)'}")
    if a.commit:
        tmpl = ParameterTemplate.objects.create(
            name=a.name, units="",
            description="Project(s) that have used this part. Rebuilt by "
                        "scripts/project_column.py. A trailing '?' means a build "
                        "PLANS to use it and has not consumed it.")
else:
    print(f"  template {a.name!r} exists (pk {tmpl.pk})")

MARK = "CONSUMED BY:"
projects = defaultdict(set)

# 1. physically installed in an assembly
for s in StockItem.objects.filter(belongs_to__isnull=False).select_related("part", "belongs_to__part"):
    projects[s.part_id].add(s.belongs_to.part.name.split(",")[0][:34])

# 2. Scott's recorded answers
for p in Part.objects.exclude(notes="").exclude(notes__isnull=True).only("pk", "notes"):
    for line in (p.notes or "").splitlines():
        if MARK in line:
            what = line.split(MARK, 1)[1].strip().rstrip(".")
            if what and not what.startswith("?"):
                projects[p.pk].add(what.split("(")[0].strip()[:34])

def tidy(title):
    """Turn a build title into something a column can show.

    Split on a SPACED hyphen only: "Rat GDO - Florida pair" is a title plus a
    qualifier, but "Shrink-fit controller" is one word and an earlier version
    chopped it to "Shrink". Also drop a trailing "build", which every title has
    and none needs in a column.
    """
    head = re.split(r"\s+-\s+", title)[0].strip()
    head = re.sub(r"\s+build$", "", head, flags=re.I)
    return head[:30]


# 2b. consumed_by — InvenTree's own record of what a build actually ate.
# Authoritative, and it SURVIVES COMPLETION, unlike BuildItem allocations which
# are cleared when a build completes. So "zero allocations on a completed
# build" proves nothing by itself; you have to look at consumed_by. An earlier
# version keyed planned-vs-actual off build STATUS, which rendered three
# complete-but-consumed-nothing builds as though they were history.
for s in StockItem.objects.filter(consumed_by__isnull=False).select_related("consumed_by"):
    projects[s.part_id].add(tidy(s.consumed_by.title))

# 3. build BOMs — a REQUIREMENT, not a record. Flagged '?' unless that same
# build has actually consumed this part.
planned = defaultdict(set)
for bl in BuildLine.objects.select_related("build", "bom_item__sub_part"):
    pid = bl.bom_item.sub_part_id
    consumed_here = StockItem.objects.filter(consumed_by=bl.build, part_id=pid).exists()
    (projects if consumed_here else planned)[pid].add(tidy(bl.build.title))

# A project that has actually consumed the part outranks one that plans to.
# Listing "Rat GDO, Rat GDO?" is noise that makes the column look unreliable.
for pid, names in planned.items():
    for n in names:
        if n not in projects[pid]:
            projects[pid].add(f"{n}?")

print(f"  {len(projects)} parts have at least one project association\n")
ct = ContentType.objects.get_for_model(Part)
changed = 0
for pk, names in sorted(projects.items()):
    val = ", ".join(sorted(names))[:500]
    part = Part.objects.filter(pk=pk).first()
    if not part:
        continue
    existing = Parameter.objects.filter(
        model_type=ct, model_id=pk, template=tmpl).first() if tmpl else None
    if existing and existing.data == val:
        continue
    changed += 1
    if changed <= 12:
        print(f"  #{pk:<5} {part.name[:40]:<40} {val[:60]}")
    if a.commit and tmpl:
        if existing:
            Parameter.objects.filter(pk=existing.pk).update(data=val)
        else:
            Parameter.objects.create(model_type=ct, model_id=pk,
                                     template=tmpl, data=val)
if changed > 12:
    print(f"  ... and {changed - 12} more")

print(f"\n  {'wrote' if a.commit else 'would write'} {changed} value(s)")
if a.commit and tmpl:
    n = Parameter.objects.filter(template=tmpl).count()
    print(f"  VERIFY: {n} parts now carry a {a.name!r} parameter")
    print(f"  Show it: Parts table -> column selector -> {a.name}")
