"""Queue C, 12:40 daytime sweep 2026-10-15: one Amazon order -> one PO, one part.

  113-9243561-9680217  placed 2026-10-15, ship to The Villages FL (LRD), "Arriving tomorrow" (10-16)
    NETGEAR 5-Port Gigabit Ethernet Unmanaged Network Switch (GS305), Essentials Model
    B07S98YLHM  sold by Amazon.com  $13.49 x1

AMAZON PRICE SOURCE -- the order-details page: Item(s) Subtotal $13.49, shipping
$0.00, tax $0.94, Rewards Points -$0.50, Grand Total $13.93. The email's 13.93
grand total is cash after points and tax, not the price.

A network switch may well end up installed at LRD -- if so, close the PO with
deploy_po.py at receive time (installed infrastructure is not inventory). That
is not a reason to skip the PO; precedent (#1409 Aeotec ZW150) imports first.

Dry run lists the networking categories and any GS305 / 5-port switch part, so
the category is chosen from what exists; --cat <pk> with --commit writes.
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

RUN = "12:40 daytime sweep 2026-10-15"
TODAY = datetime.date(2026, 10, 15)
ORDER = "113-9243561-9680217"
ASIN = "B07S98YLHM"
PRICE = "13.49"

NAME = "Ethernet Switch, 5-port Gigabit unmanaged, NETGEAR GS305"
DESC = ("orig: NETGEAR 5-Port Gigabit Ethernet Unmanaged Network Switch (GS305) | Home Network "
        "Hub, Office Ethernet Splitter, Plug-and-Play, Silent Operation, Desktop or Wall Mount, "
        "Essentials Model; Amazon B07S98YLHM")
KW = ("ethernet switch, network switch, unmanaged switch, gigabit, 5 port, 5-port, GS305, "
      "NETGEAR, LAN, RJ45, desktop switch, wall mount")
SP_DESC = "NETGEAR GS305 5-port gigabit unmanaged switch (Amazon.com)"
NOTES = ("5-port 10/100/1000 unmanaged desktop Ethernet switch, external power adapter, "
         "fanless. Counted as ONE switch.\n\n"
         f"Ordered 2026-10-15 to The Villages FL (LRD), Amazon {ORDER}. If it is put into "
         "service in the house network, close the PO with deploy_po.py rather than stocking it.")

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
ap.add_argument("--cat", type=int)
args = ap.parse_args()

amazon = Company.objects.get(name="Amazon")

# ------------------------------------------------------------ checks
dup = PurchaseOrder.objects.filter(Q(supplier_reference=ORDER) | Q(reference=ORDER))
if dup.exists():
    sys.exit(f"!! PO already exists for {ORDER}: {[p.reference for p in dup]}")
if SupplierPart.objects.filter(SKU__iexact=ASIN).exists():
    sys.exit(f"!! supplier part {ASIN} already exists")
hits = Part.objects.filter(Q(name__icontains="GS305") | Q(description__icontains="GS305")
                           | Q(description__icontains=ASIN) | Q(IPN__icontains="GS305")
                           | (Q(name__icontains="switch") & (Q(name__icontains="port")
                                                             | Q(name__icontains="ethernet"))))
for h in hits:
    print(f"  existing switch-ish part #{h.pk}: {h.name}  active={h.active}  cat={h.category}")
if hits.filter(Q(name__icontains="GS305") | Q(description__icontains="GS305")
               | Q(description__icontains=ASIN)).exists():
    sys.exit("!! a GS305 / B07S98YLHM part already exists -- reuse it, do not create")
assert len(KW) <= 250 and len(NAME) <= 100 and len(DESC) <= 250, (len(KW), len(NAME), len(DESC))

print("networking categories:")
for c in PartCategory.objects.filter(Q(name__icontains="network") | Q(name__icontains="ethernet")
                                     | Q(name__icontains="comput")):
    print(f"  {c.pk}: {c.pathstring}  ({c.parts.count()} parts)")
elec = PartCategory.objects.get(pk=119).parent
print(f"Electronics root {elec.pk}: {elec.pathstring}; children:")
for c in elec.children.all():
    print(f"  {c.pk}: {c.pathstring}  ({c.parts.count()} parts)")
print("where existing Ethernet / PoE / router parts live:")
for p in Part.objects.filter(Q(name__icontains="ethernet") | Q(name__icontains="poe")
                             | Q(name__icontains="router") | Q(name__icontains="injector")):
    print(f"  #{p.pk} {p.name[:60]}  -> {p.category_id}: {p.category}")

if not args.commit:
    raise SystemExit("\nDRY RUN -- add --cat <pk> --commit")
cat = PartCategory.objects.get(pk=args.cat)
print(f"category {cat.pk} {cat.pathstring}")

# ------------------------------------------------------------ part
part = Part(name=NAME, description=DESC, category=cat, keywords=KW,
            component=False, purchaseable=True, assembly=False,
            notes=NOTES + f"\n\nCreated by the queue C daytime sweep, {RUN}.")
part.save()
part.refresh_from_db()
assert part.name == NAME and part.category_id == cat.pk and part.keywords == KW
sp = SupplierPart(supplier=amazon, part=part, SKU=ASIN,
                  link=f"https://www.amazon.com/dp/{ASIN}", description=SP_DESC)
sp.pack_quantity = "1"
sp.save()
sp.refresh_from_db()
assert sp.SKU == ASIN and sp.part_id == part.pk, "sp did not stick"
print(f"CREATED part #{part.pk} {part.name}  cat={part.category.pathstring}  sp #{sp.pk}")

# ------------------------------------------------------------ PO
po = PurchaseOrder(
    supplier=amazon,
    reference=PurchaseOrder.generate_reference(),
    supplier_reference=ORDER,
    description=f"Amazon order {ORDER} — NETGEAR GS305 5-port switch (to The Villages FL)",
    issue_date=TODAY, target_date=datetime.date(2026, 10, 16),
    status=PurchaseOrderStatus.PLACED.value,
    notes=(f"Auto-created by the queue C daytime sweep, {RUN}.\n\n"
           "Ships to The Villages FL (LRD).\n\n"
           f"PRICE SOURCE: the order-details page — ${PRICE} for one NETGEAR GS305, sold by "
           "Amazon.com. Item(s) Subtotal $13.49, shipping $0.00, tax $0.94, Rewards Points "
           "-$0.50, Grand Total $13.93.\n\n"
           "The $13.93 grand total is cash after tax and rewards points; it is not the price "
           "and is deliberately not on the line.\n\nPLACED, not received."),
)
po.save()
po.refresh_from_db()
assert po.status == PurchaseOrderStatus.PLACED.value
assert po.supplier_reference == ORDER and po.reference != ORDER
li = PurchaseOrderLineItem(
    order=po, part=sp, quantity=1,
    purchase_price=PRICE, purchase_price_currency="USD",
    notes=f"Per-item price from the Amazon order-details page (${PRICE}), NOT the $13.93 "
          "grand total.")
li.save()
li.refresh_from_db()
assert float(li.purchase_price.amount) == float(PRICE), li.purchase_price
po.refresh_from_db()
print(f"CREATED {po.reference} supplier_ref={po.supplier_reference} status={po.status} "
      f"target={po.target_date} lines={po.lines.count()} @ {li.purchase_price}")
