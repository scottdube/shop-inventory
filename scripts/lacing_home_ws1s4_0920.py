"""Move the lacing tape to WS1-S4, Scott's call, overriding my L2-D2 guess.

I filed it in L2-D2 because that drawer is WIRE TERMINATION & CONNECTORS and
lacing tape ties harnesses. Scott: "ws1 s4". WS1 is the wire rack - cable,
wire, adhesives, CONSUMABLES.

The distinction is worth keeping, because I will guess wrong the same way
again: L2-D2 holds TERMINATION HARDWARE - the discrete pieces that end a
wire. A 260m spool of consumable tape is bulk stock, and bulk stock lives on
the rack. 'Related by use' is not the same as 'belongs in the same place'.

Both default_location and the stock row move. Leaving default_location at
L2-D2 would send the next spool back to the wrong place.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()
from part.models import Part
from stock.models import StockItem, StockLocation
from django.contrib.auth import get_user_model

user = get_user_model().objects.filter(is_superuser=True).first()
DEST = StockLocation.objects.get(pk=449)
p = Part.objects.get(pk=1254)
si = StockItem.objects.get(pk=871)

print(f"before: part defloc={p.default_location.name}  stock loc={si.location.name}")
print(f"dest [{DEST.pk}] {DEST.pathstring}")

NOTE = """

2026-09-20 RELOCATED to WS1-S4 on Scott's instruction ("ws1 s4"). I had filed
it in L2-D2 on theme - that drawer is WIRE TERMINATION & CONNECTORS and
lacing tape ties harnesses. Wrong axis. L2-D2 holds TERMINATION HARDWARE, the
discrete pieces that end a wire; a 260m spool is a bulk consumable and those
live on the wire rack. Related by use is not the same as belongs together."""

si.location = DEST
si.notes = (si.notes or '') + NOTE
si.save()
p.default_location = DEST
p.notes = (p.notes or '') + NOTE
p.save()

p2 = Part.objects.get(pk=1254); s2 = StockItem.objects.get(pk=871)
print(f"\nAFTER part 1254 defloc={s2.location.pathstring if False else p2.default_location.pathstring}")
print(f"AFTER stock 871 qty={s2.quantity} loc={s2.location.pathstring}")
ok = (p2.default_location_id == 449 and s2.location_id == 449
      and 'RELOCATED to WS1-S4' in (s2.notes or ''))
print("VERIFIED" if ok else "*** VERIFY FAILED ***")

print()
print("NOTE: WS1-S4 shows 0 other rows. That is the inventory, not the shelf -")
print("WS1's own description records the rack as FULL as of 2026-08-21 and")
print("never walked. Do not read this move as 'filed onto an empty shelf'.")
