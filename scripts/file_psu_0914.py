import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()
from decimal import Decimal
from part.models import Part
from stock.models import StockItem, StockLocation

p = Part.objects.get(pk=1202)

# The earlier check was a false alarm from my own quoting. Verify properly:
# the ASSERTION is gone; only the quoted retraction remains.
bad_assertion = "**OUTPUT IS USUALLY TRIMMABLE** on these"
quoted = '"typically about +/-10%, roughly 10.8-13.2 V"'
print(f"old assertion gone : {bad_assertion not in p.notes}")
print(f"survives only as a quoted correction: {quoted in p.notes}")
print(f"correct figure present: {'10.2 V to 13.8 V' in p.notes}")

loc = StockLocation.objects.get(pk=455)          # WS2-S3
assert StockItem.objects.filter(part=p).count() == 0
si = StockItem.objects.create(
    part=p, location=loc, quantity=Decimal('1'),
    notes=("COUNTED 1 by Scott 2026-09-14 during the wire-shelf stock-in. "
           "Tallied, not an estimate.\n\n"
           "Amazon ASIN B07TZMMZ66, last purchased 2023-08-07 in the 30 A size. "
           "Filed beside #1160 S-250-24, the same maker's 24 V unit, so the two "
           "enclosed supplies live together."),
)
p.default_location = loc
p.save(); p.refresh_from_db()
if p.default_location_id != loc.pk:
    Part.objects.filter(pk=1202).update(default_location=loc)
    p.refresh_from_db()
print(f"\nstock {si.pk}: 1 @ {si.location.pathstring}")
print(f"home: {p.default_location.pathstring}")

# WS2-S3's description says "mostly wire". Two bricks now live there.
add = ("\n\nENCLOSED PSUs LIVE HERE TOO, as of 2026-09-14: #1160 S-250-24 "
       "(24V 10A) and #1202 S-360-12 (12V 30A), both SHNITPWR, kept together. "
       "The shelf description above is about WIRE because that is what was "
       "observed on it in August; the supplies are a second, deliberate use of "
       "the same shelf, not clutter.")
if 'ENCLOSED PSUs LIVE HERE' not in (loc.description or ''):
    loc.description = (loc.description or '') + add
    loc.save(); loc.refresh_from_db()
print(f"shelf note added: {'ENCLOSED PSUs LIVE HERE' in loc.description}")
