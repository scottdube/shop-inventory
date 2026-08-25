"""Make the QL-810W a serialised asset, and fix a note that says something false.

Answering "don't we have a type for that?": InvenTree has no asset/tool part
type. The only mechanism that means "this is one identified machine, not a
quantity on a shelf" is `trackable`, which forces qty-1 serialised stock. Two
parts on this instance use it (#930, #1047) and both are serialised, so the
convention exists — the printer just was not filed into it.

Safe to flip here precisely because part #1057 has ZERO stock rows: trackable
cannot be set on a part with unserialised stock, and there is none.

Also corrects PO-0134's note. It claims a second PO would double-count
"while the returned one was still counted". Measured today: PO-0134's line
says received=1 but no StockItem exists, so nothing is counted at all. The
decision it justifies is unchanged and still right — a $0.00 warranty
replacement is not a purchase — but the reason written down was wrong, and a
wrong reason in a note is worse than no note.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part
from stock.models import StockItem
from order.models import PurchaseOrder

p = Part.objects.get(pk=1057)
assert StockItem.objects.filter(part=p).count() == 0, "stock exists — do NOT flip trackable blind"

if not p.trackable:
    Part.objects.filter(pk=p.pk).update(trackable=True)
    p.refresh_from_db()
    assert p.trackable is True, "trackable write did not stick"
    print(f"part #{p.pk}: trackable -> True (verified)")
else:
    print(f"part #{p.pk}: already trackable")

# --- correct the PO-0134 note -------------------------------------------
po = PurchaseOrder.objects.filter(supplier_reference="113-0519734-2405002").first()
BAD = ("A $0.00 PO would later be received and put a SECOND printer in stock while the "
       "returned one was still counted.")
GOOD = ("A $0.00 PO would later be received and put a second printer in stock for a "
        "one-machine swap. CORRECTION 2026-08-25: an earlier version of this note said "
        "the returned unit was 'still counted'. It is not. This PO's line reads "
        "received=1, but part #1057 has ZERO stock rows — the receipt was recorded on "
        "the line and no StockItem was ever created. Separate problem, logged for Scott; "
        "it does not change the swap decision.")
notes = po.notes or ""
if BAD in notes:
    PurchaseOrder.objects.filter(pk=po.pk).update(notes=notes.replace(BAD, GOOD))
    po.refresh_from_db()
    assert GOOD in po.notes and BAD not in po.notes, "note correction did not stick"
    print("PO-0134: false clause corrected (verified)")
else:
    print("PO-0134: clause not found — note left alone")

print(f"\nfinal: #{p.pk} {p.name!r} trackable={p.trackable} category={p.category.pathstring} stock={p.total_stock}")
