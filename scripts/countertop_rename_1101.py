"""Rename the LRD "bench" that is really the countertop, 2026-11-01.

Scott: "I also want to stop calling the existing work top 'bench' and rename it
countertop wherever we have been saying bench. When the new bench gets here it
will be bench and have the same layout as SLN."

So the cabinet run `LRD/Bench Wall` (pk 524) becomes `LRD/Countertop Wall`, and
its descriptions say countertop. "Bench" at LRD is kept free for the new bench.
Notes mentioning a bench are LISTED, not rewritten: a dated note is a record of
what was said then.

    itq run scripts/countertop_rename_1101.py            # dry run
    itq run scripts/countertop_rename_1101.py --commit
"""
import argparse
import os
import re
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from stock.models import StockLocation  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

NEW = "Countertop Wall"
wall = StockLocation.objects.get(pk=524)
assert wall.name in ("Bench Wall", NEW), wall.name
print(f"524  {wall.pathstring!r}  ->  name {NEW!r}")

PAT = re.compile(r"bench[ -]?(wall|top)|\bbench\b", re.I)


def fix(text):
    # Exact strings only. A blanket case-insensitive replace rewrote the real
    # file name docs/lrd/bench-wall-installer-render.png in the dry run.
    t = text.replace("LRD/Bench Wall", "LRD/Countertop Wall")
    t = t.replace("The bench run in the Florida garage.",
                  "The countertop run in the Florida garage (called the bench wall "
                  "until 2026-11-01; 'bench' at LRD now means the new electronics bench).")
    return t


changes = []
for loc in [wall] + list(wall.get_descendants()):
    d = loc.description or ""
    if PAT.search(d):
        nd = fix(d)
        print(f"\n{loc.pk}  {loc.name}")
        print(f"   was: {d}")
        print(f"   new: {nd}")
        if re.search(r"\bbench\b", nd, re.I):
            print("   !! still says 'bench' - left for a human to word")
        changes.append((loc, nd))

if not a.commit:
    print(f"\nDRY RUN - {len(changes)} descriptions + 1 rename. Re-run with --commit.")
    sys.exit(0)

StockLocation.objects.filter(pk=524).update(name=NEW)
for loc, nd in changes:
    StockLocation.objects.filter(pk=loc.pk).update(description=nd)
# pathstring is derived; rebuild it for the whole subtree via save()
wall = StockLocation.objects.get(pk=524)
wall.save()
for loc in wall.get_descendants():
    loc.save()

wall.refresh_from_db()
assert wall.name == NEW, wall.name
bad = [l.pathstring for l in [wall] + list(wall.get_descendants())
       if "Bench Wall" in l.pathstring]
assert not bad, bad
print(f"\n524 is now {wall.pathstring!r}; {wall.get_descendants().count()} descendants re-pathed")
