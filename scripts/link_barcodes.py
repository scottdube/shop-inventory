"""Link each drawer location's own address as its scannable barcode.

The label QR carries the plain address ("A1-R1C1"). InvenTree will only resolve
that to a location if the same string is registered as the location's
barcode_data. This does that for every drawer in the bin wall, and nothing else.

MIRRORED NAMES (Scott, 2026-11-02): a name may exist at both sites on purpose
(RB-01, the bench drawers) so the same place has the same name for muscle
memory. Barcodes must stay unique, so an LRD location whose name also exists
elsewhere gets "LRD:<name>" as its barcode. SLN keeps the bare name, because
its labels are already printed. The printed TEXT is the bare name at both sites.

Idempotent: re-running changes nothing. Reversible: unassign_barcode() on any
location, or run with --undo.
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

# A1-R3C5 / B3-R2C4 - the drawer address form and nothing else. Cabinets,
# areas and every other location in the 467 are deliberately left alone.
DRAWER = re.compile(r"^[A-Z][0-9]+-R\d+C\d+$")

ap = argparse.ArgumentParser()
ap.add_argument("--undo", action="store_true", help="strip the barcodes again")
ap.add_argument("--commit", action="store_true", help="write (default is dry run)")
a = ap.parse_args()

drawers = [l for l in StockLocation.objects.all() if DRAWER.match(l.name)]


def code_for(loc):
    """The barcode string for a location (see MIRRORED NAMES above)."""
    if (loc.pathstring or "").startswith("LRD/") and \
            StockLocation.objects.filter(name=loc.name).exclude(pk=loc.pk).exists():
        return f"LRD:{loc.name}"
    return loc.name


print(f"drawer locations matched: {len(drawers)}")

changed = skipped = collided = 0
for loc in drawers:
    current = getattr(loc, "barcode_data", "") or ""

    if a.undo:
        if current:
            if a.commit:
                loc.unassign_barcode()
            changed += 1
        else:
            skipped += 1
        continue

    code = code_for(loc)
    if current == code:
        skipped += 1
        continue
    if current and current != code:
        print(f"  !! {loc.name}: already holds {current!r} - left alone")
        collided += 1
        continue

    if a.commit:
        try:
            loc.assign_barcode(barcode_data=code, raise_error=True)
        except Exception as exc:  # a duplicate hash elsewhere in the DB
            print(f"  !! {loc.name}: {exc}")
            collided += 1
            continue
    changed += 1

verb = "unlinked" if a.undo else "linked"
mode = "WROTE" if a.commit else "DRY RUN - nothing written"
print(f"\n{mode}")
print(f"  {verb}:        {changed}")
print(f"  already ok:   {skipped}")
print(f"  left alone:   {collided}")

total = StockLocation.objects.count()
with_bc = StockLocation.objects.exclude(barcode_data="").count()
print(f"\nlocations: {total}   with a linked barcode: {with_bc}")
if not a.commit:
    print("\nre-run with --commit to apply")
