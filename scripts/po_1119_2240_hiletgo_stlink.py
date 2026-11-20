"""Queue C, 22:40 daytime sweep 2026-11-19: one Amazon order -> one PLACED PO.

  order                 ASIN        qty  price  arrives
  113-0278692-1379417   B07SQV6VLZ  1    9.49   "Arriving tomorrow" (11-20)

HiLetgo ST-Link V2 clone (USB dongle, STM8/STM32 SWD/SWIM) with cable. Placed 2026-11-19
~21:52 EST, ships to The Villages FL (LRD). Price is the item line on the Amazon order-details
page read in Chrome 2026-11-19 22:4x: $9.49; Item(s) Subtotal $9.49, shipping $0, tax $0.66,
grand total $10.15. Single unit, pack 1.

Scott ran find_stlink_1119.py at 21:50 (commit 4399205) before buying, so no ST-Link was
expected; this script re-checks across name/description/keywords/IPN/SKU before creating.

Dry run prints duplicates and candidate categories; --commit --category <pk> writes.
PLACED, never received.
"""
import argparse
import datetime
import os
import sys

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import Company, SupplierPart  # noqa: E402
from order.models import PurchaseOrder, PurchaseOrderLineItem  # noqa: E402
from order.status_codes import PurchaseOrderStatus  # noqa: E402
from part.models import Part, PartCategory  # noqa: E402
from plugins.notes_compat import note_set, note_text  # noqa: E402

RUN = "22:40 daytime sweep 2026-11-19"
ORDER = "113-0278692-1379417"
ASIN = "B07SQV6VLZ"
QTY, PRICE, PACK = 1, "9.49", "1"
ISSUE = datetime.date(2026, 11, 19)
ARRIVE = datetime.date(2026, 11, 20)
NAME = "ST-Link V2 programmer/debugger, USB dongle (clone), STM8/STM32"
DESC = ("orig: HiLetgo ST-Link V2 Emulator Downloader Programmer STM32F103C8T6 STM8 STM32 "
        "with Cable (Random Color)")
KW = ("ST-Link, STLink, ST-Link V2, SWD, SWIM, programmer, debugger, debug probe, STM32, STM8, "
      "STM32F103C8T6, Blue Pill, OpenOCD, st-flash, clone, HiLetgo")
NOTES = ("ST-Link V2 clone USB dongle with 10-pin ribbon/Dupont cable; programs and debugs STM32 "
         "over SWD and STM8 over SWIM (OpenOCD / st-flash / STM32CubeProgrammer). Clone, not ST "
         "genuine: firmware updates from ST tools can brick or flag clones. Amazon B07SQV6VLZ, "
         "sold by HiLetgo. Bought 2026-11-19 after find_stlink_1119.py found no SWD programmer.")
SP_DESC = "HiLetgo ST-Link V2 clone programmer with cable"

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
ap.add_argument("--category", type=int)
args = ap.parse_args()

amazon = Company.objects.get(name="Amazon")

terms = ["st-link", "stlink", "st link", "swd", "jtag", "debugger", "debug probe", "hiletgo st",
         ASIN]
q = Q()
for t in terms:
    q |= (Q(name__icontains=t) | Q(description__icontains=t) | Q(keywords__icontains=t)
          | Q(IPN__icontains=t))
cands = Part.objects.filter(q).distinct()
for c in cands:
    print(f"  cand #{c.pk} active={c.active} {c.name!r} cat={c.category.pathstring if c.category else None!r}")
sp_hits = SupplierPart.objects.filter(Q(SKU__iexact=ASIN) | Q(description__icontains="st-link"))
print(f"  sp hits: {[(s.pk, s.SKU, s.part_id) for s in sp_hits]}")
dup = PurchaseOrder.objects.filter(Q(supplier_reference=ORDER) | Q(reference=ORDER))
print(f"{ORDER}: existing={[(p.reference, p.lines.count()) for p in dup]}")
assert not any("st-link" in c.name.lower() or "stlink" in c.name.lower() for c in cands), "ST-Link dupe?"

for cat in PartCategory.objects.filter(
        Q(name__icontains="program") | Q(name__icontains="debug") | Q(name__icontains="dev")
        | Q(name__icontains="test") | Q(name__icontains="usb") | Q(name__icontains="interface")
        | Q(name__icontains="adapter") | Q(name__icontains="tool")):
    print(f"  category #{cat.pk} {cat.pathstring!r} parts={cat.parts.count()}")

if not args.commit:
    raise SystemExit("\nDRY RUN -- add --commit --category <pk>")
assert args.category, "--category required with --commit"
category = PartCategory.objects.get(pk=args.category)

sp = SupplierPart.objects.filter(supplier=amazon, SKU__iexact=ASIN).first()
if sp is None:
    part = Part.objects.filter(name__iexact=NAME).first()
    if part is None:
        part = Part(name=NAME, description=DESC, keywords=KW, category=category,
                    link=f"https://www.amazon.com/dp/{ASIN}",
                    component=False, purchaseable=True, assembly=False)
        part.save()
        part.refresh_from_db()
        assert part.name == NAME and part.keywords == KW, "part did not stick"
        note_set(part, NOTES + f"\n\nCreated by the queue C daytime sweep, {RUN}.")
        assert note_text(part).startswith(NOTES[:30]), "part note did not stick"
        print(f"CREATED part #{part.pk} {part.name} in {category.pathstring}")
    else:
        print(f"REUSE part #{part.pk} {part.name}")
    sp = SupplierPart(supplier=amazon, part=part, SKU=ASIN,
                      link=f"https://www.amazon.com/dp/{ASIN}", description=SP_DESC)
    sp.pack_quantity = PACK
    sp.save()  # .save(), never .update(): only pack_quantity_native is read at receive
    sp.refresh_from_db()
    assert sp.SKU == ASIN and sp.part_id == part.pk, "sp did not stick"
    assert float(sp.pack_quantity_native) == float(PACK), sp.pack_quantity_native
    print(f"CREATED sp #{sp.pk} {ASIN} -> part #{part.pk} pack native={sp.pack_quantity_native}")

if dup.exists():
    assert dup.count() == 1
    po = dup.first()
    if po.lines.count():
        raise SystemExit(f"SKIP {ORDER}: {po.reference} already has lines")
    print(f"RESUMING {po.reference} (0 lines)")
else:
    po = PurchaseOrder(supplier=amazon, reference=PurchaseOrder.generate_reference(),
                       supplier_reference=ORDER,
                       description=f"Amazon order {ORDER} — {SP_DESC} x{QTY} (to The Villages FL)",
                       issue_date=ISSUE, target_date=ARRIVE,
                       status=PurchaseOrderStatus.PLACED.value)
    po.save()
    po.refresh_from_db()
assert po.supplier_id == amazon.pk and po.supplier_reference == ORDER
assert po.status == PurchaseOrderStatus.PLACED.value and po.reference != ORDER
note_set(po, f"Auto-created by the queue C daytime sweep, {RUN}.\n\nShips to The Villages FL (LRD).\n\n"
             "Line price is the item line from the Amazon order-details page: $9.49, shipping $0.00, "
             "tax $0.66, grand total $10.15.\n\nPLACED, not received.")
assert note_text(po).startswith("Auto-created"), "PO note did not stick"
li = PurchaseOrderLineItem(order=po, part=sp, quantity=QTY,
                           purchase_price=PRICE, purchase_price_currency="USD")
li.save()
li.refresh_from_db()
assert float(li.quantity) == QTY and float(li.purchase_price.amount) == float(PRICE)
po.refresh_from_db()
print(f"CREATED {po.reference} supplier_ref={po.supplier_reference} status={po.status} "
      f"target={po.target_date} lines={po.lines.count()} ({QTY} x sp #{sp.pk} @ {PRICE})")
