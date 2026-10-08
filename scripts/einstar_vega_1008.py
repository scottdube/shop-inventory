#!/usr/bin/env python3
"""File the Shining 3D Einstar Vega 3D scanner and put it in FL-01 as a commuting tool.

Scott, 2026-10-08: "3d scanner going to fl". It had NO InvenTree record:
trip.py where scanner found only an SDR, and the only "scan" hit in the docs
is BinScan. Identity and price come from Gmail: Amazon order
114-1898072-3656217, ASIN B0DL5L2MJH, "Shining 3D Einstar Vega", ordered
2025-01-22, Key Delivery 2025-01-25 to Dover NH, order total $1,799.00
(seller SHINING 3D TECHNOLOGY INC, fulfilled by Amazon).

Filed straight into FL-01 because that is where it is going, and the SLN home
is NOT recorded: nobody has said where it lives at SLN and the rule is that a
home is learned with the thing in hand, never planned (commuting-tools). The
commute marker is written with home=None; trip.py list shows it away, land
works, and the SLN home gets set when it comes back north in 2027.

No PO is created: the PPK2 and thermal camera carry price on the stock row
only, and a raw Amazon reference as a PO number is the reference_int trap.

    itq run scripts/einstar_vega_1008.py [--commit]
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.utils import timezone  # noqa: E402
from part.models import Part, PartCategory  # noqa: E402
from company.models import Company, SupplierPart  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

COMMIT = "--commit" in sys.argv
NAME = "Shining 3D Einstar Vega 3D Scanner, handheld, wireless"
ASIN = "B0DL5L2MJH"
cat = PartCategory.objects.get(pk=38); assert cat.pathstring == "Equipment/Test Equipment"
fl = StockLocation.objects.get(pk=504); assert fl.name == "FL-01"
amazon = Company.objects.get(pk=9); assert amazon.name == "Amazon"

if Part.objects.filter(name__icontains="einstar").exists():
    print("already filed:", list(Part.objects.filter(name__icontains="einstar").values_list("pk", "name")))
    sys.exit(1)
print(f"create part {NAME!r} in {cat.pathstring}")
print(f"  supplier part Amazon {ASIN}; stock 1 @ {fl.pathstring} @ $1,799.00; commutes, home UNKNOWN")
if not COMMIT:
    print("\nDRY RUN - nothing written. Re-run with --commit."); sys.exit(0)

p = Part(name=NAME, category=cat, purchaseable=True, component=False, trackable=True,
         description="Shining 3D Einstar Vega: standalone handheld 3D scanner with built-in screen and battery, no PC needed while scanning. Amazon listing title 'Shining 3D Einstar Vega'.",
         keywords="3D scanner, Einstar, Vega, Shining 3D, scanning, point cloud, mesh, handheld",
         link=f"https://www.amazon.com/dp/{ASIN}",
         notes="Bought on Amazon 2025-01-22, order 114-1898072-3656217, ASIN "
               f"{ASIN}, seller SHINING 3D TECHNOLOGY INC (fulfilled by Amazon), Key Delivery "
               "2025-01-25 to Dover NH, order total $1,799.00. Filed 2026-10-08 from the Gmail "
               "order confirmation when Scott packed it for Florida; it had no record before.\n\n"
               "Commuting tool (one only). SLN home NOT recorded - set it with the scanner in "
               "hand when it returns north. Related consumable: HXOGYUB 3D scanning spray, "
               "Amazon 2025-05-27, also unrecorded.")
p.save(); p.refresh_from_db(); assert p.pk and p.name == NAME
sp = SupplierPart(supplier=amazon, part=p, SKU=ASIN, link=f"https://www.amazon.com/dp/{ASIN}",
                  description="Shining 3D Einstar Vega")
sp.save(); sp.refresh_from_db()
s = StockItem.objects.create(part=p, location=fl, quantity=1, supplier_part=sp,
                             purchase_price=1799.00, purchase_price_currency="USD",
                             notes="Packed for Florida 2026-10-08 (Scott: '3d scanner going to fl'). "
                                   "Price is the order total of a single-item order.")
meta = {"commutes": {"home": None,
                     "home_path": "UNKNOWN - SLN home not recorded; set on return north",
                     "since": str(timezone.now().date()),
                     "note": "3D scanner, one only, carry both ways (Scott 2026-10-08)",
                     "trips": []}}
StockItem.objects.filter(pk=s.pk).update(metadata=meta)
s.refresh_from_db(); s.tags.add("commutes")
ok = (s.metadata or {}).get("commutes", {}).get("home_path", "").startswith("UNKNOWN")
print(f"\npart {p.pk}  supplier part {sp.pk}  stock {s.pk} @ {s.location.pathstring} "
      f"price {s.purchase_price}  commute meta persisted: {ok}")
print(f"http://192.168.50.10:8001/web/part/{p.pk}/")
