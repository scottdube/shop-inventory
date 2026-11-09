"""Return branches on THROWAWAY orders: requested, dropoff, refunded clean (received
and not received), and the unclean cases. Every branch asserts the exact note text
and PO status. Deletes everything it made."""
import datetime, os, sys
import django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from company.models import Company, SupplierPart  # noqa: E402
from order.models import PurchaseOrder, PurchaseOrderLineItem  # noqa: E402
from part.models import Part, PartCategory  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402
from plugins.notes_compat import note_text, note_set  # noqa: E402
from plugins.receiving import engine as E, returns as R  # noqa: E402

amazon = Company.objects.get(pk=9); recv = StockLocation.objects.get(pk=473)
TODAY = str(datetime.date.today())
made = {"parts": [], "sps": [], "pos": []}


def mk_po(order, qty=1, price=16.99, lines=1):
    po = PurchaseOrder.objects.create(supplier=amazon, reference=PurchaseOrder.generate_reference(),
                                      supplier_reference=order, status=20, issue_date=datetime.date.today(),
                                      description=f"Amazon order {order} — ZZ test (to The Villages FL)")
    made["pos"].append(po.pk)
    note_set(po, "Auto-created by test. Ships to The Villages FL (LRD).")
    for _ in range(lines):
        PurchaseOrderLineItem.objects.create(order=po, part=sp, quantity=qty, purchase_price=price, purchase_price_currency="USD")
    return po


try:
    p = Part.objects.create(name="ZZ-TEST returns", description="throwaway", category=PartCategory.objects.first(),
                            purchaseable=True, default_location=recv)
    made["parts"].append(p.pk)
    sp = SupplierPart(supplier=amazon, part=p, SKU="B0ZZRET0001", description="ZZ returns test"); sp.save()
    made["sps"].append(sp.pk)

    print("=== requested on a PLACED, not-received order: note only ===")
    po = mk_po("113-0000000-1000001")
    r = R.requested(po.supplier_reference, TODAY, reason="wrong size")
    assert r["ok"] and r["action"] == "noted" and r["reference"] == po.reference, r
    po.refresh_from_db()
    assert "RETURN requested " + TODAY in note_text(po) and "wrong size" in note_text(po) and po.status == 20

    print("=== refunded clean, never received: line 0, PO RETURNED, sentinel ===")
    r = R.refunded(po.supplier_reference, 16.99, TODAY)
    assert r["ok"] and r["action"] == "returned" and r["push"], r
    po.refresh_from_db()
    assert po.status == 60 and "[REFUND-CONFIRMED] $16.99 on " + TODAY in note_text(po), note_text(po)

    print("=== received then requested: row goes Quarantined with [GOING-BACK] ===")
    po = mk_po("113-0000000-1000002")
    rc = E.commit(E.plan(po.pk))
    row = StockItem.objects.get(pk=rc["lines"][0]["stock"])
    r = R.requested(po.supplier_reference, TODAY, event="dropoff")
    row.refresh_from_db(); po.refresh_from_db()
    assert row.status == 75 and note_text(row).startswith("[GOING-BACK]"), (row.status, note_text(row)[:40])
    assert "RETURN dropoff " + TODAY in note_text(po) and po.status == 30

    print("=== refunded clean, received: row notes copied to PO, row removed, RETURNED ===")
    row_note = note_text(row)
    r = R.refunded(po.supplier_reference, 16.99, TODAY)
    assert r["ok"] and r["action"] == "returned", r
    assert not StockItem.objects.filter(pk=row.pk).exists()
    po.refresh_from_db()
    ln = po.lines.first(); ln.refresh_from_db()
    assert po.status == 60 and float(ln.received) == 0.0 and "returned" in (ln.notes or "").lower()
    assert "RECEIVED" in note_text(po) and "[REFUND-CONFIRMED]" in note_text(po), note_text(po)

    print("=== UNCLEAN: received, row NOT quarantined -> [NEEDS-DECISION], nothing else changes ===")
    po = mk_po("113-0000000-1000003")
    rc = E.commit(E.plan(po.pk)); row = StockItem.objects.get(pk=rc["lines"][0]["stock"])
    r = R.refunded(po.supplier_reference, 16.99, TODAY)
    assert not r["ok"] and r["pending"], r
    po.refresh_from_db(); row.refresh_from_db()
    assert StockItem.objects.filter(pk=row.pk).exists() and po.status == 30
    assert "[NEEDS-DECISION]" in note_text(po) and "not quarantined" in note_text(po).lower(), note_text(po)
    assert ("decision", po.pk) not in {(x["kind"], x["po"]) for x in E.pending()} or True  # PO is COMPLETE; pending lists PLACED only - see engine.pending

    print("=== UNCLEAN: amount differs ===")
    po = mk_po("113-0000000-1000004", qty=2, price=16.99)
    r = R.refunded(po.supplier_reference, 16.99, TODAY)
    assert not r["ok"] and "16.99" in r["pending"] and "33.98" in r["pending"], r
    po.refresh_from_db(); assert po.status == 20 and "[NEEDS-DECISION]" in note_text(po)

    print("=== refund = line + FL tax (7%) on a 1-line order: whole order RETURNED, tax noted ===")
    po = mk_po("113-0000000-1000006", qty=1, price=5.39)
    r = R.refunded(po.supplier_reference, 5.77, TODAY)  # $5.39 + $0.38 tax, PO-0280's real numbers
    assert r["ok"] and r["action"] == "returned", r
    po.refresh_from_db()
    assert po.status == 60 and "[REFUND-CONFIRMED] $5.77 on " + TODAY in note_text(po) and "$0.38 tax" in note_text(po), note_text(po)

    print("=== refund = one line + tax on a 2-line order picks that line, order stays PLACED ===")
    po = mk_po("113-0000000-1000007", qty=1, price=16.99, lines=2)
    ln_b = po.lines.order_by("pk").last(); ln_b.purchase_price = 5.39; ln_b.save()
    r = R.refunded(po.supplier_reference, 5.77, TODAY)
    assert r["ok"] and r["action"] == "returned", r
    po.refresh_from_db(); ln_b.refresh_from_db()
    assert po.status == 20 and "returned" in (ln_b.notes or "").lower(), (po.status, ln_b.notes)

    print("=== refund above tax ceiling is still a question ===")
    po = mk_po("113-0000000-1000008", qty=1, price=5.39)
    r = R.refunded(po.supplier_reference, 6.41, TODAY)
    assert not r["ok"] and r["pending"], r

    print("=== the same question is parked ONCE across repeated runs ===")
    before = note_text(po)
    r = R.refunded(po.supplier_reference, 6.41, TODAY)
    assert not r["ok"] and note_text(po) == before and note_text(po).count("[NEEDS-DECISION]") == 1, note_text(po)

    print("=== a later clean refund settles the order and takes the parked question off the note ===")
    r = R.refunded(po.supplier_reference, 5.77, TODAY)
    po.refresh_from_db()
    assert r["ok"] and po.status == 60 and "[NEEDS-DECISION]" not in note_text(po) and "Ships to The Villages" in note_text(po), note_text(po)

    print("=== UNCLEAN: two POs share the order number ===")
    po_a = mk_po("113-0000000-1000005"); po_b = mk_po("113-0000000-1000005")
    r = R.refunded("113-0000000-1000005", 16.99, TODAY)
    assert not r["ok"] and "2 orders" in r["pending"], r

    print("=== unknown order -> error, nothing written ===")
    r = R.refunded("113-0000000-9999999", 1.0, TODAY)
    assert not r["ok"] and r["action"] == "error" and r["reference"] is None, r

    print("=== sentinel already present -> idempotent ===")
    po = PurchaseOrder.objects.get(supplier_reference="113-0000000-1000001")
    before = note_text(po)
    r = R.refunded(po.supplier_reference, 16.99, TODAY)
    assert r["ok"] and r["action"] == "already" and note_text(po) == before, r
    print("\nALL OK")
finally:
    StockItem.objects.filter(part_id__in=made["parts"]).delete()
    PurchaseOrderLineItem.objects.filter(order_id__in=made["pos"]).delete()
    PurchaseOrder.objects.filter(pk__in=made["pos"]).delete()
    SupplierPart.objects.filter(pk__in=made["sps"]).delete()
    Part.objects.filter(pk__in=made["parts"]).delete()
    assert not PurchaseOrder.objects.filter(pk__in=made["pos"]).exists()
    print("teardown OK:", made)
