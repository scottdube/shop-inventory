"""PO-0282 (Amazon 113-5723051-9981849, 2 x Tnisesm 100uF 25V 20-pack): RETURNED by hand.

Why not returns.py: Amazon's return request and refund mail both say QUANTITY 1 of the 2
units ($6.41 = $5.99 + $0.42 FL tax), so the engine can only ask "part of one?" -- it has no
branch for a partial line. Scott, 2026-11-09, answering three mornings of that question:
"280 and 282 were both returned to amazon". Nothing from this order was ever received
(line received=0, no stock row), so the shelf is already right; this closes the order.

Records both facts: the mail's 1-of-2 refund, and Scott's statement. If the second
$6.41 ever arrives, append it; if the second pack turns up, receive it against this line.
Dry run by default; --commit writes. Every write is re-read.
"""
import datetime, os, sys
import django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.db import transaction
from order.models import PurchaseOrder, PurchaseOrderLineItem
from order.status_codes import PurchaseOrderStatus as POS
from plugins.notes_compat import note_text, note_set, note_append

COMMIT = "--commit" in sys.argv
REFUND_DATE = "2026-11-06"
po = PurchaseOrder.objects.get(reference="PO-0282")
assert po.supplier_reference == "113-5723051-9981849" and po.status == POS.PLACED.value, (po.supplier_reference, po.status)
lines = list(po.lines.all())
assert len(lines) == 1 and float(lines[0].received) == 0 and float(lines[0].quantity) == 2, [(l.received, l.quantity) for l in lines]
ln = lines[0]
from stock.models import StockItem
assert not StockItem.objects.filter(purchase_order=po).exists(), "a stock row is linked to PO-0282"

txt = note_text(po) or ""
kept = [p for p in txt.split("\n\n") if not p.strip().startswith("[NEEDS-DECISION]")]
print(f"note paragraphs: {len(txt.split(chr(10)+chr(10)))} -> {len(kept)} (parked questions removed)")

class DryRun(Exception):
    pass

try:
    with transaction.atomic():
        note_set(po, "\n\n".join(kept))
        PurchaseOrderLineItem.objects.filter(pk=ln.pk).update(
            received=0, notes=f"returned, refunded $6.41 {REFUND_DATE} (Amazon: 1 of 2 units; Scott 2026-11-09: whole order went back)")
        PurchaseOrder.objects.filter(pk=po.pk).update(status=POS.RETURNED.value,
                                                      complete_date=datetime.date.fromisoformat(REFUND_DATE))
        note_append(po, f"[REFUND-CONFIRMED] $6.41 on {REFUND_DATE} (Amazon refund mail; $5.99 line + $0.42 tax, "
                        f"for QUANTITY 1 of the 2 packs ordered - return request DLzxxKH5RRMA, reason 'Changed Mind').")
        note_append(po, "RETURNED by hand 2026-11-09 (scripts/close_po282_returned_1109.py): Scott says the order went back "
                        "to Amazon; nothing from it was ever received. Amazon has refunded only one of the two packs - "
                        "the second $6.41 is not in the mail as of 2026-11-09.")
        po.refresh_from_db(); ln.refresh_from_db()
        assert po.status == POS.RETURNED.value and po.complete_date == datetime.date.fromisoformat(REFUND_DATE)
        assert "[REFUND-CONFIRMED] $6.41" in note_text(po) and "[NEEDS-DECISION]" not in note_text(po)
        assert "returned, refunded" in ln.notes
        print(f"PO-0282 -> {po.get_status_display()} complete_date={po.complete_date}")
        print("note now:", note_text(po)[:300].replace("\n", " | "))
        if not COMMIT:
            raise DryRun()
except DryRun:
    print("DRY RUN - rolled back. Re-run with --commit.")
else:
    print("COMMITTED  http://192.168.50.10:8001/web/purchasing/purchase-order/%d" % po.pk)
