"""Backfill PO + supplier part on the 14 older rows receive_po.py left unlinked, 2026-10-04.

Same bug as link_po_rows_1004.py (SI 898/899): before the 2026-10-04 fix,
receive_po.py's new-row branch never set purchase_order/supplier_part, so these
rows are missing from their PO's received-items tab.

A row is linked only when its notes name exactly ONE PO, that PO has exactly one
line for the row's part, and nothing in the notes says another quantity was
merged into it. Everything else is SKIPPED, with the reason printed:

  - two or more POs named: a merged row. The history lives in the notes on
    purpose, and pointing purchase_order at one PO would claim the whole
    quantity came from it.
  - one PO named but the notes record a merge: same problem. Naming one PO
    does not prove there was one receipt. 608 was counted at 3 BEFORE PO-0146 merged 5 into it.
  - no PO named, or the named PO has no line for this part: nothing to link
    (762 names PO-0130, which is the SPROCKET's order, not the chain's).

Dry run by default. --commit writes with a queryset .update() (a .save() on
this install can report success and write nothing), then re-reads every row.

    itq run scripts/link_po_rows_legacy_1004.py            # plan
    itq run scripts/link_po_rows_legacy_1004.py --commit
"""
import os, re, sys, django
sys.path.insert(0, os.getcwd()); os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings"); django.setup()
from order.models import PurchaseOrder
from stock.models import StockItem

PKS = (558, 608, 656, 674, 759, 761, 762, 789, 798, 799, 806, 807, 842, 877)
COMMIT = "--commit" in sys.argv
PO_RE = re.compile(r"\bPO-\d+\b")
MERGE_RE = re.compile(r"\bmerged\b", re.I)


def plan(s):
    notes = s.notes or ""
    refs = sorted(set(PO_RE.findall(notes)))
    if s.purchase_order_id:
        return "SKIP", f"already linked to PO {s.purchase_order.reference}", None
    if not refs:
        return "SKIP", "no PO named in notes", None
    if len(refs) > 1:
        return "SKIP", f"merged row: notes name {', '.join(refs)}", None
    if MERGE_RE.search(notes):
        return "SKIP", f"merged row: names only {refs[0]}, but the notes record a merge", None
    po = PurchaseOrder.objects.filter(reference=refs[0]).first()
    if po is None:
        return "SKIP", f"{refs[0]} does not exist", None
    lines = [ln for ln in po.lines.select_related("part") if ln.part and ln.part.part_id == s.part_id]
    if len(lines) != 1:
        return "SKIP", f"{refs[0]} has {len(lines)} lines for part {s.part_id}", None
    ln = lines[0]
    return "LINK", f"{po.reference} ({po.get_status_display()}) line rcvd {ln.received:g}/{ln.quantity:g}, SP {ln.part.SKU}", (po, ln.part)


print("COMMIT" if COMMIT else "DRY RUN — nothing written")
linked = skipped = 0
for pk in PKS:
    s = StockItem.objects.select_related("part", "location").get(pk=pk)
    verdict, why, target = plan(s)
    where = s.location.pathstring if s.location else "(no location)"
    print(f"{verdict:4} SI {pk:4} {s.part.name[:38]:38} qty {s.quantity:g} @ {where}\n       {why}")
    if verdict != "LINK":
        skipped += 1
        continue
    if COMMIT:
        po, sp = target
        StockItem.objects.filter(pk=pk, purchase_order__isnull=True).update(purchase_order=po, supplier_part=sp)
        s.refresh_from_db()
        ok = s.purchase_order_id == po.pk and s.supplier_part_id == sp.pk
        print(f"       re-read: PO {s.purchase_order.reference if s.purchase_order else None}"
              f" SP {s.supplier_part.SKU if s.supplier_part else None} {'OK' if ok else 'MISMATCH'}")
        assert ok, pk
    linked += 1

print(f"\n{'linked' if COMMIT else 'would link'} {linked}, skipped {skipped}")
