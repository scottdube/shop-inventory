"""Close the QL-810W replacement decision as a SWAP against PO-0134.

Scott approved option (a) on 2026-08-25: no PO for Amazon 113-8789992-1384241.
Two writes, both verified by re-reading:
  1. the decision line moves from `open` to a `[x] DONE` line in the queue file
  2. PO-0134 gains a note saying the physical unit in stock is the REPLACEMENT

(2) is the load-bearing one. Without it the only record that the received
printer is not the printer PO-0134 paid for lives in a chat message.
"""
import os, sys, re, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from order.models import PurchaseOrder

QUEUE = "/Volumes/4TB_Removable/inventree/pending_decisions.md"
KEY = "amazon-113-8789992-1384241-replacement"
DONE = ("- [x] DONE 2026-08-25. Scott approved option (a): treated as a SWAP against PO-0134, "
        "NO PurchaseOrder created for Amazon 113-8789992-1384241. Stock stays at one QL-810W, "
        "which is correct - the unit on the shelf is now the REPLACEMENT, not the unit PO-0134 "
        "paid for. Recorded on PO-0134's notes so the substitution is not chat-only.\n      was: ")

src = open(QUEUE).read()

# Find the open line for this decision and rewrite it in place.
pat = re.compile(r"^- \[ \] " + re.escape(KEY) + r" \|.*$", re.M)
m = pat.search(src)
if not m:
    print("!! open decision line not found — nothing changed")
    sys.exit(1)
old_line = m.group(0)
new_line = DONE + old_line[len("- [ ] "):]
out = src[:m.start()] + new_line + src[m.end():]
open(QUEUE, "w").write(out)

fresh = open(QUEUE).read()                       # verify the write stuck
assert new_line in fresh, "queue write did not stick"
assert old_line not in fresh, "open line still present"
print("queue: decision closed")

# --- PO-0134 note -------------------------------------------------------
po = PurchaseOrder.objects.filter(supplier_reference="113-0519734-2405002").first()
assert po, "PO-0134 not found by supplier_reference"
NOTE = (
    "\n\n2026-08-25 — WARRANTY SWAP, not a second purchase. The unit this PO paid for "
    "was returned; Amazon shipped a free replacement as its own order "
    "113-8789992-1384241 (TOTAL $0.00, delivered ~2026-08-26). Scott approved treating "
    "it as a swap: NO PO exists for that order number, deliberately. A $0.00 PO would "
    "later be received and put a SECOND printer in stock while the returned one was "
    "still counted. So the physical QL-810W on the shelf is the REPLACEMENT unit, and "
    "its serial will not match anything recorded against this PO."
)
before = po.notes or ""
if "113-8789992-1384241" in before:
    print("PO-0134: note already present, not duplicated")
else:
    PurchaseOrder.objects.filter(pk=po.pk).update(notes=before + NOTE)
    po.refresh_from_db()
    assert "113-8789992-1384241" in (po.notes or ""), "PO note write did not stick"
    print("PO-0134: note written and verified")

print("\n--- PO-0134 notes now ---")
print(PurchaseOrder.objects.get(pk=po.pk).notes)
