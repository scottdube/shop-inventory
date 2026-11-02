"""Create the LRD electronics bench: red bins RB-01..RB-24 and the BL/BR pedestals.

The bench arrives ~2026-11-14 "with the same scheme" as SLN's (Scott). Created
2026-11-02 BEFORE it arrives, as the Akros were, so the label sheet
(`make_labels_avery.py --set lrd-bench`) scans on the first try. Descriptions
say "not yet assembled" until it is.

    itq run scripts/make_lrd_bench_1102.py            # dry run
    itq run scripts/make_lrd_bench_1102.py --commit

**Same names as SLN, on purpose** (Scott, 2026-11-02: muscle memory at either
bench). LRD/Electronics Bench/Red Bins/RB-01 is the twin of the SLN one; the
site is in the path. Barcodes can't repeat, so every twin here gets
`LRD:<name>` as barcode_data, which is what its QR carries. Rejected: distinct
LRD names (RB-29.., LRB-01), the old rule, which cost the one thing names are for.

24 bins because the LRD pack is 24 (PO-0272); SLN has 28. Five drawers per
pedestal is SLN's count, assumed for "the same scheme" -- check on assembly.
"""
import argparse
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from stock.models import StockLocation  # noqa: E402

# rb_state.py treats a bin carrying exactly this as never opened: keep it identical to SLN's.
BOILERPLATE = "Red bin. Holds ONE project's kit OR free storage - never both."
NOT_YET = "NOT YET ASSEMBLED (created 2026-11-02 so the labels scan; bench due ~2026-11-14)."

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

lrd = StockLocation.objects.get(name="LRD", parent=None)
made, twins = [], []


def ensure(name, parent, desc=""):
    """Return the location (None on a dry run when it would be new). Clashes are
    checked only within LRD -- an SLN location of the same name is the point."""
    if parent is not None:
        loc = StockLocation.objects.filter(name=name, parent=parent).first()
        if loc:
            return loc
    clash = StockLocation.objects.filter(name=name, pathstring__startswith="LRD/")
    assert not clash.exists(), f"{name} already exists at LRD: {clash.first().pathstring}"
    made.append(name)
    if not a.commit:
        return None
    return StockLocation.objects.create(name=name, parent=parent, description=desc)


bench = ensure("Electronics Bench", lrd,
               "LRD electronics bench, the same scheme as SLN's: BL/BR drawer "
               "pedestals, red bins RB-01..RB-24 above. Location names mirror SLN's "
               "on purpose (muscle memory); QRs carry LRD:<name>. " + NOT_YET)
rack = ensure("Red Bins", bench,
              "The red bin rack on the LRD electronics bench, RB-01..RB-24 "
              "(Akro-Mils 30220, 7 x 4 x 3 in, PO-0272). Each bin holds ONE project "
              "kit OR free storage, never both, as at SLN. " + NOT_YET)
for n in range(1, 25):
    twins.append((f"RB-{n:02d}", rack, BOILERPLATE))
for ped, side in (("BL", "Left"), ("BR", "Right")):
    p = ensure(ped, bench, f"{side} pedestal under the LRD electronics bench. " + NOT_YET)
    for d in range(1, 6):
        twins.append((f"{ped}-D{d}", p, f"{side} pedestal drawer {d}."))

locs = [ensure(name, parent, desc) for name, parent, desc in twins]
print(f"{'created' if a.commit else 'would create'} {len(made)}: "
      f"{', '.join(made[:5])} ... {made[-1] if made else ''}")

# Barcodes. Re-read each row by pk first: creating rows shifts MPTT lft/rght and a
# stale in-memory node has assigned to the wrong rows before (TRAPS, 2026-10-25).
codes = {f"LRD:{n}" for n, _, _ in twins}
taken = StockLocation.objects.filter(barcode_data__in=codes)
assert not taken.exclude(pathstring__startswith="LRD/Electronics Bench/").exists(), \
    f"barcode already used: {[(l.pathstring, l.barcode_data) for l in taken]}"
linked = 0
for (name, _, _), loc in zip(twins, locs):
    if loc is None:
        linked += 1
        continue
    loc = StockLocation.objects.get(pk=loc.pk)
    if (loc.barcode_data or "") == f"LRD:{name}":
        continue
    assert not loc.barcode_data, f"{loc.pathstring} already holds {loc.barcode_data!r}"
    loc.assign_barcode(barcode_data=f"LRD:{name}", raise_error=True)
    linked += 1
print(f"barcodes: {'linked' if a.commit else 'would link'} {linked}")

if not a.commit:
    print("DRY RUN - add --commit")
    raise SystemExit

# Verify by re-read: this install has reported .save() success and written nothing.
bad = []
for name, _, _ in twins:
    hit = StockLocation.objects.filter(name=name, pathstring__startswith="LRD/Electronics Bench/")
    if hit.count() != 1 or hit[0].barcode_data != f"LRD:{name}":
        bad.append(f"{name}: {[(h.pathstring, h.barcode_data) for h in hit]}")
stale = [l.pathstring for l in StockLocation.objects.filter(pathstring__startswith="LRD/")
         if l.pathstring != l.construct_pathstring()]
print("ALL VERIFIED" if not bad else "NOT VERIFIED:\n  " + "\n  ".join(bad))
print(f"stale pathstrings: {stale or 'none'}")
