"""Split 35 x 150R 1/2W off to Florida Staging for the G1000 PFD build.

Same shape as the tactile switch split earlier today: splitStock keeps the
tracking history, the new row carries the florida earmark AND tag, and the
source row's in-place earmark is dropped so the two cannot double-count.

The BOM needs 12 (R1-R8, R11-R14). Scott is taking 35, which is his call and
recorded as such - the surplus is not build #3's and should not read as if
the faceplate needs it.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from stock.models import StockItem, StockLocation
from django.contrib.auth import get_user_model

COMMIT = "--commit" in sys.argv
TAKE = 35
src = StockItem.objects.get(pk=449)
BAG = StockLocation.objects.get(pk=503)
user = get_user_model().objects.filter(is_superuser=True).first()

print("source row 449 [%s] %s" % (src.part.pk, src.part.name))
print("  qty=%s  loc=%s" % (src.quantity, src.location.name))
print("  tags=%s" % list(src.tags.names()))
print("  metadata=%s" % src.metadata)
print("  taking %s -> %s, leaving %s" % (TAKE, BAG.name, src.quantity - TAKE))
assert src.quantity >= TAKE, "not enough on hand"

if not COMMIT:
    print("\nDRY RUN - add --commit")
    sys.exit()

new = src.splitStock(TAKE, location=BAG, user=user)
new = StockItem.objects.get(pk=new.pk)
new.batch = "G1000 PFD build #3"
new.metadata = {'florida': {
    'qty': float(TAKE),
    'why': ('G1000 build #3 (PFD) at LRD - BO-0017 - 12 fitted (R1-R8, R11-R14, '
            'the 3-LED groups) + the rest spare for LRD bench work'),
    'added': '2026-09-20'}}
new.notes = """Split from row 449 (A3-R8C2) on 2026-09-20 for the Florida bag.

THE BUILD NEEDS 12 of these - R1 to R8 and R11 to R14, the 3-LED groups.
Scott is taking 35; the other 23 are general LRD bench stock, NOT build #3
margin. Do not read this row's quantity as what the faceplate needs.

These are 1/2W where the BOM says 1/4W. That is fine and in fact preferred:
the 150R positions dissipate 60mW (24% of a 1/4W rating) and the board's
resistor footprint is drawn for a ~6mm body, which is 1/2W sized. See
flight-sim/docs/g1000-build3-bom.md."""
new.save()
new.tags.add('florida')

src = StockItem.objects.get(pk=449)
src.metadata = {}
src.notes = ((src.notes or '').rstrip() + """

2026-09-20: 35 split out to Florida Staging (row %s) for the G1000 PFD build
at LRD. The in-place florida earmark was dropped here so it cannot
double-count against that row.
REMAINDER IS ARITHMETIC, NOT A COUNT: %s - 35. Nobody has tallied this row
since the split.""" % (new.pk, int(src.quantity) + TAKE)).strip()
src.save()
src.tags.remove('florida')

src = StockItem.objects.get(pk=449)
new = StockItem.objects.get(pk=new.pk)
print("\nAFTER 449: qty=%s loc=%s tags=%s meta=%s"
      % (src.quantity, src.location.name, list(src.tags.names()), src.metadata))
print("AFTER %s: qty=%s loc=%s batch=%r tags=%s florida=%s"
      % (new.pk, new.quantity, new.location.name, new.batch,
         list(new.tags.names()), new.metadata['florida']['qty']))
ok = (src.quantity == 46 and new.quantity == TAKE and new.location_id == 503
      and 'florida' in list(new.tags.names()) and not src.metadata)
print("VERIFIED" if ok else "MISMATCH - stop and look")
