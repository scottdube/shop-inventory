"""Add the precision-tip cotton swabs, which the 11-02 daytime sweep skipped as "personal"
(Amazon files the listing under Personal Care, "for Makeup"). Scott 2026-11-04: they are a
shop item, bought twice: 2026-06-17 (SLN; that order number was not captured, an Amazon
checkpoint stopped the browser) and 2026-11-02, the third line of 113-8879085-9694659 =
PO-0288, delivered to LRD 2026-11-03.

Creates the part (consumable, not a component; Tools/Consumables like the Kimwipes #1489 on
the same order), an Amazon supplier part B0BT8VZ3GQ, and the missing $9.99 line on
PO-0288. Stock counts PACKS of 1000 (pack_quantity 1), the Kimwipes convention, so an
opened pack never needs a swab count. Receiving is separate (receive_po.py --part) and
waits on Scott naming the LRD spot.

Dry run by default.  itq run scripts/swabs_1104.py [--commit]"""
import os, sys
sys.path.insert(0, os.getcwd()); os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
import django; django.setup()
from django.db.models import Q
from company.models import Company, SupplierPart
from order.models import PurchaseOrder, PurchaseOrderLineItem
from part.models import Part, PartCategory
from plugins.notes_compat import note_set, note_append, note_text

ASIN, CAT, PRICE = "B0BT8VZ3GQ", 56, "9.99"
NAME = "Cotton Swabs Precision Tip Double-Pointed (pack 1000)"
DESC = "orig: Precision Tip Cotton Swabs/Double Pointed Cotton Buds for Makeup 1000pcs"
KW = "cotton swabs, swabs, q-tips, precision tip, pointed swab, cleaning, flux cleanup, IPA, consumable"
NOTE = ("Precision-tip, double-pointed cotton swabs, 1000 per pack. Stock counts PACKS, not swabs "
        "(pack_quantity 1, the Kimwipes #1489 convention).\n\n"
        "## Purchase history (Amazon)\n\n"
        "| Date | Qty | Unit | Order | Ship to |\n|---|---|---|---|---|\n"
        "| 2026-06-17 | 1 | not captured | not captured | SLN |\n"
        "| 2026-11-02 | 1 | $9.99 | 113-8879085-9694659 (PO-0288) | LRD, delivered 2026-11-03 |\n\n"
        "Added 2026-11-04 at Scott's ask. The 11-02 sweep had skipped the line as personal care.")

hits = Part.objects.filter(Q(name__icontains="swab") | Q(keywords__icontains="swab") | Q(description__icontains="swab"))
assert not hits.exists(), f"swab part already exists: {list(hits.values_list('pk', 'name'))}"
assert not SupplierPart.objects.filter(SKU__iexact=ASIN).exists(), "supplier part exists"
po = PurchaseOrder.objects.get(reference="PO-0288")
assert po.supplier_reference == "113-8879085-9694659" and po.status == 20, (po.supplier_reference, po.status)
assert po.lines.count() == 2, po.lines.count()
cat = PartCategory.objects.get(pk=CAT); assert cat.pathstring == "Tools/Consumables", cat.pathstring
print(f"part   {NAME!r} in {cat.pathstring}, consumable, not component")
print(f"sp     Amazon {ASIN} pack 1")
print(f"line   PO-0288 + 1 x ${PRICE}")
if "--commit" not in sys.argv:
    print("DRY RUN - nothing written"); sys.exit(0)

amazon = Company.objects.get(name="Amazon")
part = Part(name=NAME, description=DESC, keywords=KW, category=cat, link=f"https://www.amazon.com/dp/{ASIN}",
            component=False, purchaseable=True, assembly=False, consumable=True)
part.save(); part.refresh_from_db()
if not part.consumable or part.component:
    Part.objects.filter(pk=part.pk).update(consumable=True, component=False); part.refresh_from_db()
note_set(part, NOTE)
sp = SupplierPart(supplier=amazon, part=part, SKU=ASIN, link=f"https://www.amazon.com/dp/{ASIN}",
                  description="Precision tip cotton swabs 1000pcs")
sp.pack_quantity = "1"; sp.save(); sp.refresh_from_db()  # .save(): pack_quantity_native
li = PurchaseOrderLineItem(order=po, part=sp, quantity=1, purchase_price=PRICE, purchase_price_currency="USD")
li.save(); li.refresh_from_db()
note_append(po, "2026-11-04: added the third line, cotton swabs $9.99 (part #%d). The sweep had skipped it as "
                "personal care; Scott says it is a shop item." % part.pk)

p = Part.objects.get(pk=part.pk)
ok = (p.name == NAME and p.consumable and not p.component and p.category_id == CAT
      and note_text(p).startswith("Precision-tip") and float(sp.pack_quantity_native) == 1
      and sp.part_id == p.pk and float(li.quantity) == 1 and float(li.purchase_price.amount) == 9.99
      and po.lines.count() == 3 and "third line" in note_text(PurchaseOrder.objects.get(pk=po.pk)))
print(f"part #{p.pk} sp #{sp.pk} line #{li.pk}; PO-0288 lines={po.lines.count()}")
print("VERDICT:", "SUCCESS" if ok else "FAILED")
