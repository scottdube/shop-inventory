"""Catalogue the 2x12 24P IDC ribbon sockets found in MC-T3, 2026-09-20.

Identity is off the box label, read through an Amazon LPN sticker:
PCAccessories.com 28-DR24-25PK, "2X12 24P Dual Row Socket, 25-Pack".
Count is Scott's: 23.

NOT a duplicate of #1241 'Pin Header Socket 2.54mm Double Row 2x12 Female
(24-pin)'. Those words describe both parts and they are not interchangeable:
#1241 solders into a board, this one clamps onto flat ribbon cable. The name
here leads with IDC and Ribbon so a truncated label still tells them apart -
see docs/LABELLING.md.

No SupplierPart created. The LPN is an Amazon warehouse sticker, not an ASIN,
and 28-DR24-25PK is the maker's number. Inventing a supplier link from a
sticker is how a wrong reorder happens; the MPN goes in the notes instead.

default_location left EMPTY - L2-D2 is the obvious home (it already holds the
2x6 box headers, #1249) but that is Scott's call, not mine.
"""
import os, sys, django
from datetime import date
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part, PartCategory
from stock.models import StockItem, StockLocation

COMMIT = "--commit" in sys.argv
QTY = 23
MCT3 = StockLocation.objects.get(pk=432)

NAME = "IDC Ribbon Socket 2x12 (24P) Female, crimp-on"
DESC = ("2.54mm IDC female socket for FLAT RIBBON CABLE, 2x12 = 24 positions, "
        "clamp termination. Mates a 2x12 shrouded box header. PCAccessories.com "
        "28-DR24-25PK, 25/pack. NOT the solder-in pin header #1241.")

dupe = Part.objects.filter(name__iexact=NAME).first()
print("duplicate check on exact name: %s" % (dupe or "none"))
cat = Part.objects.get(pk=1249).category
print("category taken from #1249 (box header): %s" % cat)
print("name (%d): %s" % (len(NAME), NAME))
print("desc (%d): %s" % (len(DESC), DESC))
assert len(DESC) <= 250, "description too long: %d" % len(DESC)
print("label would show: %r" % NAME[:40])
print("qty to record: %d at %s" % (QTY, MCT3.name))

if not COMMIT:
    print("\nDRY RUN - add --commit")
    sys.exit()

p = Part.objects.create(name=NAME, description=DESC, category=cat,
                        active=True, purchaseable=True, component=True)
p.notes = """Found in MC-T3 during the G1000 drawer count, 2026-09-20, in its
original white box with an Amazon LPN sticker (LPN RR HO304 1443) partly
covering the printed label. Maker's number 28-DR24-25PK, PCAccessories.com,
25-pack.

COUNTED by Scott 2026-09-20: 23. A 25-pack with 2 gone.

No SupplierPart. The LPN is a warehouse sticker, not an ASIN, and nothing on
the box gives a purchase link - so there is no verified way to reorder these
yet. Find the order before adding a supplier part.

WHAT THIS IS FOR: it is the ribbon-cable mate for a 2x12 shrouded box header.
On the G1000 that is J17 on the Peter Eier shield - which was DROPPED along
with the GMA1347 audio panel and the 2x15 (J13) header. So this is NOT a
build #3 part. It is on hand for the audio panel if that ever comes back.

DO NOT CONFUSE WITH #1241 'Pin Header Socket 2.54mm Double Row 2x12 Female
(24-pin)'. Both are '2x12 24-pin female'. #1241 solders into a PCB; this
clamps onto flat ribbon cable. They do not substitute."""
p.save()

si = StockItem.objects.create(part=p, quantity=QTY, location=MCT3)
si.notes = """COUNTED by Scott 2026-09-20: 23, from a 25-pack.

Parked at MC-T3 because that is where the box physically sits during the
drawer count. Part has no default_location yet - L2-D2 (WIRE TERMINATION &
CONNECTORS, already home to the 2x6 box headers #1249) is the obvious home,
but it was left unset rather than guessed.

The box's OTHER compartment holds loose black bars, probably the strain
reliefs for these connectors. NOT COUNTED AND NOT CATALOGUED - Scott has not
confirmed what they are. If they are strain reliefs they belong with these;
if they are a separate connector they need their own line."""
si.save()

p2 = Part.objects.get(pk=p.pk)
si2 = StockItem.objects.get(pk=si.pk)
print("\ncreated part #%s '%s'" % (p2.pk, p2.name))
print("  qty=%s defloc=%s" % (p2.total_stock, p2.default_location))
print("  stock row %s qty=%s loc=%s" % (si2.pk, si2.quantity, si2.location.name))
ok = (p2.total_stock == QTY and p2.default_location is None
      and si2.location_id == 432)
print("VERIFIED" if ok else "MISMATCH - stop and look")
print("  http://192.168.50.10:8001/web/part/%s" % p2.pk)
