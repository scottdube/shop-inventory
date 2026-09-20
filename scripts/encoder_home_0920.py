"""Give part #95 a home at B3-R2C7, alongside the PropWash dual encoder kit.

Scott's call, 2026-09-20. The drawer already holds a dual CONCENTRIC encoder -
the PropWash kit - so this puts two parts that answer the same description and
are NOT interchangeable into one bin. That is precisely the B3-R1C2 tactile
switch failure from this same morning: three look-alike bags, no label, and an
hour spent working out which one the build wanted.

So the bin description leads with the discriminator instead of the contents,
and the spare gets its own labelled bag.
"""
import os, sys, django
from datetime import date
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part
from stock.models import StockItem, StockLocation

COMMIT = "--commit" in sys.argv
HOME = StockLocation.objects.get(pk=308)
p = Part.objects.get(pk=95)
row = StockItem.objects.get(pk=863)

print("part #95 default_location: %s -> %s" % (p.default_location, HOME))
print("row 863 location        : %s -> %s" % (row.location, HOME))
print("\nbin 308 description now:\n%s" % HOME.description)

DESC = ("TWO DIFFERENT DUAL CONCENTRIC ENCODERS LIVE HERE AND THEY DO NOT "
        "INTERCHANGE. Tell them apart by the base: GREEN loose encoder = part "
        "#95 (bags read SKU GFKA0001-001), the one the G1000 faceplate uses. "
        "BOXED KIT with breakout PCB, headers, nut, washer and knobs = PropWash "
        "part #1250 - keep that kit together, it is build #1 salvage and is NOT "
        "a G1000 BOM part. Also B0505S-1W isolated DC-DC converter 5V 1W. "
        "[6 x 2-7/32 x 1-9/16 in, small]")
print("\nnew (%d chars):\n%s" % (len(DESC), DESC))

if not COMMIT:
    print("\nDRY RUN - add --commit")
    sys.exit()

Part.objects.filter(pk=95).update(default_location=HOME)
row.location = HOME
row.notes = """The SIXTH green-base dual encoder, found loose in MC-T3 on
2026-09-20 beyond the 5 the G1000 faceplate needs. Scott: stays at SLN, does
not travel to LRD for build #3.

Filed to B3-R2C7 on 2026-09-20 by Scott's call, next to the PropWash dual
encoder kit.

WARNING - THE NEIGHBOUR IS A LOOK-ALIKE, NOT A SUBSTITUTE. Stock 860 in this
same drawer is the PropWash Dual Encoder Kit (part #1250), which is also a
dual concentric encoder and is NOT interchangeable with this one. Green base
and the GFKA0001-001 bag are the field marks for #95; the PropWash arrives as
a kit with its own breakout PCB. Reaching for the wrong one is how this
morning went at B3-R1C2."""
row.save()
StockLocation.objects.filter(pk=308).update(description=DESC)

p = Part.objects.get(pk=95)
row = StockItem.objects.get(pk=863)
loc = StockLocation.objects.get(pk=308)
print("\n#95 defloc = %s" % p.default_location)
print("row 863 loc = %s  qty=%s" % (row.location.name, row.quantity))
print("bin desc starts: %s" % loc.description[:60])
ok = (p.default_location_id == 308 and row.location_id == 308
      and loc.description.startswith("TWO DIFFERENT"))
print("VERIFIED" if ok else "MISMATCH - stop and look")
for si in StockItem.objects.filter(location=loc):
    print("   %s [%s] %s qty=%s" % (si.pk, si.part.pk, si.part.name[:50], si.quantity))
