"""Tormach dial-indicator tool height setter, MB-D7, 2026-10-10.

Scott: the loose dowel in D3 "came with tormach manual tool height setting
gauge"; the gauge lives in D7 and "was bought with the mill, is part of that
invoice". Tormach's "Tool Height Setter, Dial Indicator" ships as setter +
calibration dowel (tormach.com product page) -- which is exactly the pair.

Not on file: the mill order 3000048323 has 24 part lines and none is a height
setter, so it arrived inside a kit line. The BT30 Operator's Kit (39293, #566)
is the likely one, but Tormach publishes no contents list for 39293 that could
be found -- so the kit is named as a guess, and no price is split off it.
The dowel is not a part of its own: it is the setter's calibration standard.

    itq run scripts/mb_d7_height_setter_1010.py [--commit]
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part, PartCategory  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

COMMIT = "--commit" in sys.argv
MEAS = PartCategory.objects.get(pk=47); assert MEAS.pathstring == "Tooling/Measuring"
D7 = StockLocation.objects.get(name="MB-D7", parent__pk=381)
NAME = "Tormach Tool Height Setter, Dial Indicator"
print(f"CREATE {NAME!r} in {D7.pathstring}" + (" (exists)" if Part.objects.filter(name=NAME).exists() else ""))
if not COMMIT:
    sys.exit("DRY RUN -- add --commit")

p = Part.objects.filter(name=NAME).first()
if not p:
    p = Part(name=NAME,
             description="Manual tool height setting gauge with dial indicator, plus calibration dowel",
             keywords="tool height setter, tool height gauge, tool length, dial indicator, Tormach, calibration dowel",
             category=MEAS, component=False, purchaseable=True, assembly=False, default_location=D7,
             notes=("Filed 2026-10-10 from Scott. Lives in MB-D7. **Its calibration dowel is the loose "
                    "dowel in MB-D3** (Scott: it came with this gauge).\n\nBought with the mill -- "
                    "Tormach order 3000048323 (quote QT123040), per Scott. Not its own line on that "
                    "order; probably inside the BT30 Operator's Kit 39293 (part #566), unconfirmed. "
                    "No separate price."))
    p.save(); p.refresh_from_db()
    assert p.category_id == MEAS.pk and p.default_location_id == D7.pk
if not StockItem.objects.filter(part=p).exists():
    s = StockItem(part=p, location=D7, quantity=1, notes="Per Scott 2026-10-10; with calibration dowel (in MB-D3).")
    s.save(); s.refresh_from_db(); assert s.location_id == D7.pk
    print(f"CREATED part #{p.pk} SI #{s.pk}")
