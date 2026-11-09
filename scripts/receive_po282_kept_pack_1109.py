"""PO-0282: receive the ONE pack Scott kept (of 2), into the HOT Info Orbs Club Tub.

Scott 2026-11-09, after the order was closed RETURNED on Amazon's 1-of-2 refund:
"Second pack is here". The order's other pack went back ($6.41 refunded 2026-11-06).

Why by hand: the receiving engine takes a pack count per line, but the order is
RETURNED (60) and a non-open order refuses line saves, so the status is walked back
to PLACED first, the engine books 1 pack x 20 = 20 pieces (merging into the tub's
100uF row), and the order is then set COMPLETE by hand - the engine only completes
when every line is fully received, and this line never will be (1 kept, 1 returned).
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
from plugins.notes_compat import note_text, note_append
from plugins.receiving import engine as E

COMMIT = "--commit" in sys.argv
TUB, WHEN = 863, "2026-11-09"
po = PurchaseOrder.objects.get(reference="PO-0282")
assert po.supplier_reference == "113-5723051-9981849" and po.status == POS.RETURNED.value, (po.supplier_reference, po.status)
ln = po.lines.get()
assert float(ln.quantity) == 2 and float(ln.received) == 0, (ln.quantity, ln.received)

class DryRun(Exception):
    pass

try:
    with transaction.atomic():
        PurchaseOrder.objects.filter(pk=po.pk).update(status=POS.PLACED.value, complete_date=None)
        po.refresh_from_db(); assert po.status == POS.PLACED.value
        pl = E.plan(po.pk, lines={ln.pk: {"packs": 1, "dest": TUB}}, when=WHEN)
        assert not pl["warnings"] and len(pl["lines"]) == 1, pl
        x = pl["lines"][0]
        print(f"plan: {x['packs']:g} pack x {x['pack']:g} = {x['pieces']:g} pieces at ${x['unit']:.4f} -> "
              f"{x['dest']['path'] if isinstance(x['dest'], dict) and 'path' in x['dest'] else x['dest']}  "
              f"{'merge into stock %s (%g before)' % (x['merge_into'], x['before']) if x['merge_into'] else 'new row'}")
        rc = E.commit(pl)
        ln.refresh_from_db(); assert float(ln.received) == 1, ln.received
        PurchaseOrderLineItem.objects.filter(pk=ln.pk).update(
            notes="1 pack kept and received 2026-11-09 to HOT Info Orbs Club Tub; 1 pack returned, refunded $6.41 2026-11-06")
        PurchaseOrder.objects.filter(pk=po.pk).update(status=POS.COMPLETE.value, complete_date=datetime.date.fromisoformat(WHEN))
        po.refresh_from_db(); ln.refresh_from_db()
        assert po.status == POS.COMPLETE.value and "kept" in ln.notes, (po.status, ln.notes)
        note_append(po, f"Scott 2026-11-09: the second pack is here (not returned after all). Received 1 pack = 20 pieces "
                        f"to HOT Info Orbs Club Tub, stock {rc['lines'][0]['stock']}; order COMPLETE by hand "
                        f"(1 kept + 1 returned/refunded, so the line will never read 2/2). "
                        f"Replaces the 'whole order went back' line above.")
        assert "second pack is here" in note_text(po)
        print(f"PO-0282 -> {po.get_status_display()}  line received={ln.received}  stock {rc['lines'][0]['url']}")
        if not COMMIT:
            raise DryRun()
except DryRun:
    print("DRY RUN - rolled back. Re-run with --commit.")
else:
    print("COMMITTED  http://192.168.50.10:8001/web/purchasing/purchase-order/%d" % po.pk)
