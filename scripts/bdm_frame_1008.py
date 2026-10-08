#!/usr/bin/env python3
"""File the BDM frame and put it in FL-01 as a commuting tool.

Scott, 2026-10-08: "BDM Frame going". The only BDM record was part 495,
the AliExpress 4-pack of probe PENS (no stock rows, never filed). The frame
itself had no record. Identity and price from Gmail: Amazon order
113-9975085-1113813, "BDM Frame with 4 Pcs Probe Pins, with LED Test Board
Assembly, Support for 22pcs BDM Adapter ... Work for Kess v2, for KTAG for
FGTECH", $39.99 (total $42.79), ordered 2026-05-11, delivered 2026-05-12
to THE VILLAGES FL - so it was bought at LRD, came north in late May, and
is going back. Commuting tool, home unknown until Scott names it.

    itq run scripts/bdm_frame_1008.py [--asin B0XXXXXXXX] [--commit]
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
ASIN = sys.argv[sys.argv.index("--asin") + 1] if "--asin" in sys.argv else None
NAME = "BDM Frame with 4 probe pins and LED test board, ECU programming jig (Kess/KTAG/FGTECH)"
cat = PartCategory.objects.get(pk=59); assert cat.pathstring == "Tools/Diagnostics"
fl = StockLocation.objects.get(pk=504); assert fl.name == "FL-01"
amazon = Company.objects.get(pk=9); assert amazon.name == "Amazon"
if Part.objects.filter(name__istartswith="BDM Frame with").exists():
    print("already filed:", list(Part.objects.filter(name__istartswith="BDM Frame with").values_list("pk", "name"))); sys.exit(1)
print(f"create part {NAME!r} in {cat.pathstring}")
print(f"  supplier part Amazon {ASIN or '(no ASIN)'}; stock 1 @ {fl.pathstring} @ $39.99; commutes, home UNKNOWN")
if not COMMIT:
    print("\nDRY RUN - nothing written. Re-run with --commit."); sys.exit(0)
p = Part(name=NAME, category=cat, purchaseable=True, component=False, trackable=True,
         description="Multifunctional BDM frame set: frame, 4 probe pins, LED test board assembly, supports 22-piece BDM adapter sets; for Kess v2 / KTAG / FGTECH ECU bench programming.",
         keywords="BDM frame, ECU, bench programming, Kess, KTAG, FGTECH, probe pins, jig",
         link=f"https://www.amazon.com/dp/{ASIN}" if ASIN else "",
         notes="Bought on Amazon 2026-05-11, order 113-9975085-1113813, $39.99 (grand total $42.79), "
               "delivered 2026-05-12 to The Villages FL. Carried north in May 2026. Filed 2026-10-08 "
               "from the Gmail order when Scott packed it for Florida; it had no record before.\n\n"
               "Commuting tool. SLN home NOT recorded - set it with the frame in hand.\n\n"
               "Related: part 495 is a separate AliExpress 4-pack of probe pens for this frame "
               "(order 8211697285825753, June 2026), still with no stock row.")
p.save(); p.refresh_from_db(); assert p.pk and p.name == NAME
sp = None
if ASIN:
    sp = SupplierPart(supplier=amazon, part=p, SKU=ASIN, link=f"https://www.amazon.com/dp/{ASIN}",
                      description="BDM Frame with 4 Pcs Probe Pins, with LED Test Board Assembly")
    sp.save(); sp.refresh_from_db()
s = StockItem.objects.create(part=p, location=fl, quantity=1, supplier_part=sp,
                             purchase_price=39.99, purchase_price_currency="USD",
                             notes="Packed for Florida 2026-10-08 (Scott: 'BDM Frame going').")
meta = {"commutes": {"home": None, "home_path": "UNKNOWN - SLN home not recorded",
                     "since": str(timezone.now().date()),
                     "note": "BDM frame, one only, carry both ways (Scott 2026-10-08)", "trips": []}}
StockItem.objects.filter(pk=s.pk).update(metadata=meta)
s.refresh_from_db(); s.tags.add("commutes")
ok = (s.metadata or {}).get("commutes", {}).get("home_path", "").startswith("UNKNOWN")
print(f"\npart {p.pk}  supplier part {sp.pk if sp else '-'}  stock {s.pk} @ {s.location.pathstring} "
      f"price {s.purchase_price}  commute meta persisted: {ok}")
print(f"http://192.168.50.10:8001/web/part/{p.pk}/")
