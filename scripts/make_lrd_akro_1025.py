"""Create the LRD Akro-Mils cabinets F0/F1/F2 and make every LRD label scannable.

Bought 2026-10-23, delivered 2026-10-24: two 10164 (64 small drawers each) and
one 10124 (24 large). Created 2026-10-25 on Scott's request, BEFORE they are on
the wall, so the Avery sheet can be printed and every QR resolves on the first
scan. make_a0b0.py waited for the wall; here the request came first, and the
cabinet description says "not yet hung" until it is.

    itq run scripts/make_lrd_akro_1025.py            # dry run
    itq run scripts/make_lrd_akro_1025.py --commit

**Why F, and not A/B/C.** A QR carries only the plain name, so every name must
be unique across BOTH sites. A and B are the SLN bin wall, C is reserved for its
third row (OPEN.md), D would read as a drawer (`Cab2-D1`), L is the SLN laser
drawers. F is unused and still matches `^[A-Z][0-9]+-R\\d+C\\d+$`, the drawer
form every counter and link_barcodes.py already recognise. F0 = the 24-large
cabinet, F1/F2 = the 64s, mirroring SLN's A0/A1. The number names the CABINET,
not its spot on the wall, so the labels survive however they get hung.

**Parent is `LRD/Akro Bins`, not `Bin Wall`.** Four scripts look up
`name="Bin Wall"` with .get() / parent__name, and a second one would break them
or silently pull LRD drawers into SLN-only counts.

Also, because the same sheet labels them:
  - Cab1-S1..S3 (door base levels, decided in the LRD storage plan) are created
    bare; their kind gets written with the rest of the plan.
  - every LRD label name gets its own string as barcode_data. link_barcodes.py
    only links the drawer form, so `Cab2-D3` or `F1` would otherwise print a QR
    InvenTree cannot resolve.
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

SMALL = "[6 x 2-7/32 x 1-9/16 in, small]"   # same drawer as the SLN A wall
LARGE = "[6 x 4-9/16 x 2-3/16 in, large]"   # same drawer as SLN A0/B0
CABS = [  # name, model, rows, cols, drawer
    ("F0", "10124", 6, 4, LARGE),
    ("F1", "10164", 8, 8, SMALL),
    ("F2", "10164", 8, 8, SMALL),
]
DESC = ("Akro-Mils {model} — {n} drawers, {rows} rows x {cols} wide, all "
        "{kind}. Bought 2026-10-23, delivered 2026-10-24. NOT YET HUNG "
        "(created 2026-10-25 so the labels scan); planned spot is the back wall "
        "beside Cab5, see the LRD storage plan. The name is the cabinet, not "
        "its position.")

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

lrd = StockLocation.objects.get(name="LRD", parent=None)
bench = StockLocation.objects.get(name="Bench Wall", parent=lrd)


def ensure(name, parent, desc=""):
    """Return (location or None on a dry run, created?).

    On a dry run the new parents do not exist, so `parent` is None; the
    cross-site name check still runs, which is the one a dry run is for.
    """
    clash = StockLocation.objects.filter(name=name)
    if parent is not None:
        loc = clash.filter(parent=parent).first()
        if loc:
            return loc, False
        clash = clash.exclude(parent=parent)
    assert not clash.exists(), f"{name} already exists elsewhere: {clash.first().pathstring}"
    if not a.commit:
        return None, True
    return StockLocation.objects.create(name=name, parent=parent, description=desc), True


made = []
akro, new = ensure("Akro Bins", lrd,
                   "Akro-Mils drawer cabinets F0/F1/F2. F is the LRD letter: "
                   "A/B/C are SLN's bin wall, so names stay unique across sites.")
if new:
    made.append("Akro Bins")
for name, model, rows, cols, drawer in CABS:
    cab, new = ensure(name, akro, DESC.format(
        model=model, n=rows * cols, rows=rows, cols=cols,
        kind="large" if drawer == LARGE else "small"))
    if new:
        made.append(name)
    for r in range(1, rows + 1):
        for c in range(1, cols + 1):
            dn = f"{name}-R{r}C{c}"
            if ensure(dn, cab, drawer)[1]:
                made.append(dn)

cab1 = StockLocation.objects.get(name="Cab1", parent=bench)
for s in (1, 2, 3):
    if ensure(f"Cab1-S{s}", cab1)[1]:
        made.append(f"Cab1-S{s}")

print(f"{'created' if a.commit else 'would create'} {len(made)} locations: "
      f"{', '.join(made[:6])}{' ...' if len(made) > 6 else ''}")

# Barcodes: exactly the names the LRD sheet prints (on a dry run the Akro rows
# do not exist yet). Filtered by name because the bench wall also holds kit
# locations ("Kit - ALLECIN ...", inside Cab2-D3) that carry no sheet label.
PRINTED = re.compile(r"^(Cab[1-8](-[DS][1-5])?|F[0-2](-R\d+C\d+)?)$")
# RE-READ the roots first. Creating rows in the LRD tree shifts every node's
# lft/rght, and get_descendants() on the stale in-memory `bench` returned the
# first 47 Akro rows instead of the bench wall (2026-10-25); the second root
# then hit those rows again and died on 'Existing barcode found'.
roots = [StockLocation.objects.get(pk=r.pk) for r in (bench, akro) if r]
targets = list({l.pk: l for r in roots for l in r.get_descendants(include_self=False)
                if PRINTED.match(l.name)}.values())
linked = skipped = collided = 0
for loc in targets:
    cur = getattr(loc, "barcode_data", "") or ""
    if cur == loc.name:
        skipped += 1
        continue
    if cur:
        print(f"  !! {loc.name}: already holds {cur!r} - left alone")
        collided += 1
        continue
    if a.commit:
        loc.assign_barcode(barcode_data=loc.name, raise_error=True)
    linked += 1
print(f"barcodes: {'linked' if a.commit else 'would link'} {linked}, "
      f"already right {skipped}, collisions {collided}")

if not a.commit:
    print("DRY RUN - add --commit")
    raise SystemExit

# Verify by re-read: this install has reported .save() success and written nothing.
bad = []
for name, model, rows, cols, drawer in CABS:
    n = StockLocation.objects.filter(parent__name=name, parent__parent__name="Akro Bins").count()
    if n != rows * cols:
        bad.append(f"{name}: {n} drawers, expected {rows * cols}")
for s in (1, 2, 3):
    if not StockLocation.objects.filter(name=f"Cab1-S{s}", parent__name="Cab1").exists():
        bad.append(f"Cab1-S{s} missing")
for loc in StockLocation.objects.filter(pk__in=[l.pk for l in targets]):
    if (loc.barcode_data or "") != loc.name:
        bad.append(f"{loc.name}: barcode {loc.barcode_data!r}")
stale = [l.name for l in StockLocation.objects.all()
         if (l.pathstring or "") != l.construct_pathstring()]
print("ALL VERIFIED" if not bad else "NOT VERIFIED:\n  " + "\n  ".join(bad))
print(f"stale pathstrings: {stale or 'none'}")
