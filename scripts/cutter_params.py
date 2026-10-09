"""Cutter Diameter / Profile part parameters, derived from the part NAME.

The tool-tag label strip reads "T22  1/4"  120deg": the T number, the diameter and
the profile (flat, ball, bull, 120deg, 90deg, 60deg, thread, rough, drill, reamer,
engrave).  Nothing on this install carried either value (probed 2026-10-09: the only
parameter templates were Body Size / Lead Pitch / Footprint / Project), so this
script derives both from the part name with the patterns below and writes them as
part parameters "Cutter Diameter" and "Cutter Profile".  A derived value is marked
in the parameter note so a later hand-check (or the Fusion library, which carries
the true diameter) can replace it.  Re-running only touches parts whose note still
says derived; a hand-edited parameter (note changed) is left alone.

  itq run scripts/cutter_params.py            # dry run: what it would write
  itq run scripts/cutter_params.py --commit
"""
import argparse, os, re, sys
import django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.contenttypes.models import ContentType  # noqa: E402
from common.models import Parameter, ParameterTemplate  # noqa: E402
from part.models import Part, PartCategory  # noqa: E402

DERIVED = "derived from part name by cutter_params.py"
SKIP_CATS = ("Inserts", "Turning", "Parting", "Threading", "PCB Drills")  # not rotating single cutters

DIA = [  # cut dia first: a thread mill's fraction is its SHANK
    (re.compile(r'\.(\d{3})\s*cut dia'), lambda m: "." + m.group(1) + '"'),
    (re.compile(r'(\d+/\d+)\s*(?:"|in\b|inch)'), lambda m: m.group(1) + '"'),
    (re.compile(r'(\d+(?:\.\d+)?)\s*mm\b'), lambda m: m.group(1) + " mm"),
]
PROFILE = [
    (re.compile(r'(\d{2,3})\s*deg', re.I), lambda m: m.group(1) + "deg"),
    (re.compile(r'ball', re.I), lambda m: "ball"),
    (re.compile(r'bull|corner rad|\.0\d+\s*r\b', re.I), lambda m: "bull"),
    (re.compile(r'thread', re.I), lambda m: "thread"),
    (re.compile(r'shredder|rough', re.I), lambda m: "rough"),
    (re.compile(r'engrav|scoring', re.I), lambda m: "engrave"),
    (re.compile(r'reamer', re.I), lambda m: "reamer"),
    (re.compile(r'face mill', re.I), lambda m: "face"),
    (re.compile(r'drill\b(?! mill)', re.I), lambda m: "drill"),
    (re.compile(r'end mill|endmill|fish-tail|router', re.I), lambda m: "flat"),
]


def derive(name):
    dia = prof = None
    for rx, f in DIA:
        m = rx.search(name)
        if m:
            dia = f(m); break
    for rx, f in PROFILE:
        m = rx.search(name)
        if m:
            prof = f(m); break
    return dia, prof


def cutter_cats():
    pks = set()
    for c in PartCategory.objects.filter(pathstring__icontains="cutt"):
        pks.add(c.pk)
        pks.update(PartCategory.objects.filter(pathstring__startswith=c.pathstring + "/").values_list("pk", flat=True))
    return pks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true")
    a = ap.parse_args()
    ct = ContentType.objects.get_for_model(Part)
    tpls = {}
    for name, units in (("Cutter Diameter", ""), ("Cutter Profile", "")):
        t = ParameterTemplate.objects.filter(name=name).first()
        if not t:
            if a.commit:
                t = ParameterTemplate.objects.create(name=name, units=units, description="tool-tag label strip; see scripts/cutter_params.py")
                print(f"created template {t.pk} {name}")
            else:
                print(f"would create template {name}")
        tpls[name] = t
    parts = Part.objects.filter(category_id__in=cutter_cats(), active=True).order_by("name")
    writes = skipped = 0
    for p in parts:
        if p.total_stock <= 0 or p.category.name in SKIP_CATS or "set" in p.name.lower() or "kit" in p.name.lower():
            continue
        dia, prof = derive(p.name)
        print(f"[{p.pk:4}] {p.name[:62]:62} -> dia={dia!s:8} profile={prof}")
        if not a.commit:
            continue
        for tname, val in (("Cutter Diameter", dia), ("Cutter Profile", prof)):
            if val is None:
                continue
            t = tpls[tname]
            q = Parameter.objects.filter(model_type=ct, model_id=p.pk, template=t).first()
            if q and q.note and not q.note.startswith(DERIVED):
                skipped += 1; continue
            if q:
                q.data = val; q.note = DERIVED; q.save()
            else:
                q = Parameter.objects.create(model_type=ct, model_id=p.pk, template=t, data=val, note=DERIVED)
            got = Parameter.objects.get(pk=q.pk)
            assert got.data == val, (p.pk, tname, got.data, val)
            writes += 1
    print(f"{'wrote' if a.commit else 'DRY RUN, would write'} {writes} parameters, left {skipped} hand-edited alone" if a.commit else "DRY RUN -- add --commit")


if __name__ == "__main__":
    main()
