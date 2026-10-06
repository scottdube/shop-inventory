#!/usr/bin/env python3
"""Back-fill the two XoomSpeed (David Loomes, UK) orders: company, parts, POs, stock.

Why its own script and not hist_import.py: there is no vendor yet, one line is
software (no stock row), and one part gets a second unit that came from no
order at all. hist_import's spec format has no place for any of that.

    itq run scripts/xoomspeed_import_1005.py            # dry run
    itq run scripts/xoomspeed_import_1005.py --commit
"""
import argparse, datetime, os, sys
from decimal import Decimal
import django
sys.path.insert(0, os.getcwd()); os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings"); django.setup()
from company.models import Company, SupplierPart  # noqa: E402
from order.models import PurchaseOrder, PurchaseOrderLineItem  # noqa: E402
from part.models import Part, PartCategory  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

ap = argparse.ArgumentParser(); ap.add_argument("--commit", action="store_true"); a = ap.parse_args()
TODAY = datetime.date.today()
D = lambda x: Decimal(str(x))

cat = PartCategory.objects.get(pk=87); assert cat.pathstring == "Equipment/CNC/Accessories", cat.pathstring
loc = StockLocation.objects.get(pk=420); assert loc.pathstring == "SLN/Machine Shop", loc.pathstring
probe = Part.objects.get(pk=567); assert "probe" in probe.name.lower(), probe.name
assert not Company.objects.filter(name__icontains="xoom").exists(), "XoomSpeed company already exists"
for nm in ("XoomSpeed wireless probe kit", "XoomSpeed USB I/O board", "XoomSpector"):
    assert not Part.objects.filter(name__istartswith=nm[:12]).exists(), nm

DOC = "~/code/tormach-1100mx/docs/wireless-probe-xoomspeed.md"
PARTS = {
  "kit": dict(name="XoomSpeed wireless probe kit, Tormach passive probe (silver body, 2020-on)",
      description="Wireless conversion module clipped to the Tormach passive probe + base station in the mill accessory port; ATmega32U4/AVR109 on both",
      keywords="xoomspeed wireless probe base station tormach passive 39295", link="https://shop.xoomspeed.com", virtual=False,
      notes=(f"Converts the Tormach passive probe (part #567) to wireless. Installed and in use since March 2024.\n\n"
             f"Scott 2026-10-05: less accurate than Ashraf reports for the GP-800, very touchy to dial in, not moisture "
             f"resistant, cannot go in the ATC. Battery killed summer 2026 by 5 months uncharged; spares were sold out.\n\n"
             f"Firmware backups (David's Probe.hex + StdConfig.wpb + BaseStation_V1_04.hex, plus Scott's 2026-07-30 dumps): "
             f"iCloud xoomspeed-backup/ and ~/Documents/Reference/Electronics/. Loading procedure and caveats: {DOC}")),
  "usbio": dict(name="XoomSpeed USB I/O board, standard, uncased",
      description="ATmega328P + FlashForth 5.0 USB I/O board for PathPilot: 4 in / 4 out, 24 V, Arduino-Uno shield footprint, (c) XoomSpeed 2020-23",
      keywords="xoomspeed usb io board flashforth atmega328p pathpilot M64 M65 M66 ETS air blast", link="https://shop.xoomspeed.com", virtual=False,
      notes=(f"Two boards held. (1) New from order #1374 (2025-08-12) at $152, uncased; Scott built an enclosure Sept 2025 from "
             f"David's DXF. (2) An OLDER board bought USED in the first half of 2026 while XoomSpeed showed sold out: source, "
             f"price and variant UNRECORDED - ask Scott. Both are believed to be the standard (no-DIN, 24 V) variant; only (1) "
             f"is confirmed from a photo. Drives the 3 s ETS air blast (G370remap.ngc edit). Record: {DOC}")),
  "spector": dict(name="XoomSpector inspection software (license)",
      description="XoomSpeed XoomSpector probing/inspection software for PathPilot, .NET 3.5, runs under Parallels on the Mac",
      keywords="xoomspeed xoomspector inspection software license", link="https://shop.xoomspeed.com", virtual=True,
      notes="Software license, not a physical item: part is VIRTUAL and carries no stock row. Bought in bundle with the "
            "wireless probe kit, order #1298, $91 list less 30% bundle = $63.70."),
}
ORDERS = [
  dict(num="1298", issued="2024-02-21", delivered="2024-03-04", shipping=D("33.00"), total=D("451.70"),
       desc="Wireless probe kit for Tormach passive probe + XoomSpector bundle",
       lines=[("kit", "WPK-TORMACH-PASSIVE", D("355.00")), ("spector", "XOOMSPECTOR", D("63.70"))]),
  dict(num="1374", issued="2025-08-12", delivered="2025-08-29", shipping=D("45.00"), total=D("197.00"),
       desc="USB I/O board, without case",
       lines=[("usbio", "USBIO-NOCASE", D("152.00"))]),
]
for o in ORDERS:
    assert sum(p for _, _, p in o["lines"]) + o["shipping"] == o["total"], o["num"]
    print(f"PLAN PO {o['num']} {o['issued']} -> {o['delivered']}  {o['desc']}  total ${o['total']}")
    for k, sku, p in o["lines"]: print(f"    {sku:22s} ${p:>8}  {PARTS[k]['name'][:60]}")
print("PLAN stock: kit x1, usbio x2 (one from PO, one used/unrecorded), spector none (virtual)  @ SLN/Machine Shop")
if not a.commit: print("DRY RUN - add --commit"); sys.exit(0)

co = Company(name="XoomSpeed", description="David Loomes, UK. Tormach/PathPilot accessories: USB I/O board, wireless probe conversion, XoomSpector, Fusion post",
             website="https://shop.xoomspeed.com", email="david@xoomspeed.com", contact="David Loomes", currency="GBP",
             is_supplier=True, is_manufacturer=True, is_customer=False,
             notes="Shopify store, prices shown and charged in USD at checkout. Ships from the UK. One-man shop: stock often sold out, "
                   "shipping can slip when David is away (order #1374 took 17 days). Historical orders back-filled 2026-10-05.")
co.save(); co.refresh_from_db(); assert co.pk and co.is_supplier
print(f"WROTE company #{co.pk} {co.name}")

parts, sps = {}, {}
for k, spec in PARTS.items():
    p = Part(category=cat, component=True, purchaseable=True, **spec); p.save(); p.refresh_from_db()
    assert p.pk and p.virtual == spec["virtual"]; parts[k] = p; print(f"WROTE part #{p.pk} {p.name[:60]}")

for o in ORDERS:
    ref = PurchaseOrder.generate_reference()
    po = PurchaseOrder(supplier=co, reference=ref, supplier_reference=o["num"], issue_date=datetime.date.fromisoformat(o["issued"]),
        status=20, description=f"XoomSpeed order #{o['num']} - {o['desc']}"[:250],
        notes=(f"Historical order back-filled {TODAY} from the Shopify receipt in Gmail. Shipping ${o['shipping']} intl, "
               f"total ${o['total']} USD. Delivered {o['delivered']}; complete_date set to the delivery date, not the back-fill date."))
    po.save(); po.refresh_from_db(); assert po.supplier_reference == o["num"]
    for k, sku, price in o["lines"]:
        sp = SupplierPart(supplier=co, part=parts[k], SKU=sku, description=PARTS[k]["name"][:250], link="https://shop.xoomspeed.com")
        sp.pack_quantity = "1"; sp.save(); sp.refresh_from_db(); assert float(sp.pack_quantity_native) == 1.0; sps[k] = sp
        li = PurchaseOrderLineItem(order=po, part=sp, quantity=1, purchase_price=price, purchase_price_currency="USD", received=1)
        li.save(); li.refresh_from_db(); assert float(li.purchase_price.amount) == float(price) and float(li.received) == 1.0
        if k != "spector":
            qty = 2 if k == "usbio" else 1
            row = StockItem.objects.create(part=parts[k], location=loc, quantity=qty, supplier_part=sp, purchase_order=po,
                purchase_price=price, purchase_price_currency="USD",
                notes=(f"XoomSpeed order #{o['num']} ({o['issued']}, {po.reference}): 1 purchased at ${price}. "
                       + ("Quantity 2 = that board PLUS the older board bought used in 2026 (source/price unrecorded); purchase_price "
                          "applies to the new one only. One row because one part per location. " if k == "usbio" else "")
                       + "Installed on the 1100MX; exact spot in the Machine Shop unrecorded. Purchase-based, not counted."))
            row.refresh_from_db(); assert float(row.quantity) == qty and row.location_id == loc.pk
            print(f"WROTE stock #{row.pk} x{qty} {parts[k].name[:50]}")
    po.refresh_from_db(); po.status = 30; po.complete_date = datetime.date.fromisoformat(o["delivered"]); po.save(); po.refresh_from_db()
    if po.status != 30:
        PurchaseOrder.objects.filter(pk=po.pk).update(status=30, complete_date=datetime.date.fromisoformat(o["delivered"])); po.refresh_from_db()
    assert po.status == 30 and str(po.complete_date) == o["delivered"], (po.status, po.complete_date)
    print(f"WROTE {po.reference} = #{o['num']} COMPLETE lines={po.lines.count()}")

probe.notes = (probe.notes or "") + (f"\n\n2026-10-05: runs WIRELESS on the XoomSpeed conversion (part #{parts['kit'].pk}) since March 2024. "
    f"Scott's verdict: less accurate than the GP-800 per Ashraf, very touchy to dial in, not moisture resistant, no ATC. "
    f"Firmware backups and procedure: {DOC}")
probe.save(); probe.refresh_from_db(); assert "XoomSpeed conversion" in probe.notes
print(f"UPDATED part #567 notes\nCOMMITTED")
