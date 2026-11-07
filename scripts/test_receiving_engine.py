"""plan -> commit -> re-read -> undo -> re-read on a THROWAWAY PO.
    itq run scripts/test_receiving_engine.py
Creates part 'ZZ-TEST receiving engine', an Amazon supplier part with pack 60,
a PLACED PO with two lines; exercises merge, new row, partial and pack 60;
deletes everything it made and proves it is gone."""
import datetime, os, sys
import django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from company.models import Company, SupplierPart  # noqa: E402
from order.models import PurchaseOrder, PurchaseOrderLineItem  # noqa: E402
from part.models import Part, PartCategory  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402
from plugins.notes_compat import note_set, note_text  # noqa: E402
from plugins.receiving import engine as E  # noqa: E402

amazon = Company.objects.get(pk=9)
recv = StockLocation.objects.get(pk=473)          # LRD/Receiving
made = {"parts": [], "sps": [], "pos": [], "stock": []}
try:
    cat = PartCategory.objects.first()
    p = Part.objects.create(name="ZZ-TEST receiving engine", description="throwaway", category=cat,
                            purchaseable=True, default_location=recv)
    made["parts"].append(p.pk)
    sp = SupplierPart(supplier=amazon, part=p, SKU="B0ZZTEST001", description="ZZ test 60 pcs")
    sp.pack_quantity = "60"; sp.save(); sp.refresh_from_db()
    made["sps"].append(sp.pk)
    assert float(sp.pack_quantity_native) == 60.0
    po = PurchaseOrder.objects.create(supplier=amazon, reference=PurchaseOrder.generate_reference(),
                                      supplier_reference="113-0000000-0000001",
                                      description="Amazon order 113-0000000-0000001 — ZZ test x2 (to The Villages FL)",
                                      issue_date=datetime.date.today(), status=20)
    made["pos"].append(po.pk)
    note_set(po, "Auto-created by test. Ships to The Villages FL (LRD).")
    l1 = PurchaseOrderLineItem.objects.create(order=po, part=sp, quantity=2, purchase_price=6.99, purchase_price_currency="USD")
    l2 = PurchaseOrderLineItem.objects.create(order=po, part=sp, quantity=1, purchase_price=6.99, purchase_price_currency="USD")

    print("=== site_of / card ===")
    assert E.site_of(po) == "LRD"
    card = E.po_card(po)
    assert card["supplier_reference"] == "113-0000000-0000001" and card["lines"][0]["pack"] == 60.0, card
    assert any(c["po"] == po.pk for c in E.open_orders("LRD"))

    print("=== suggest_destination: default_location first ===")
    d = E.suggest_destination(p, "LRD")
    assert d["pk"] == 473 and d["source"] == "default_location", d

    print("=== plan: full ===")
    pl = E.plan(po.pk)
    assert pl["closes_order"] is True and len(pl["lines"]) == 2, pl
    a = pl["lines"][0]
    assert a["pieces"] == 120.0 and abs(a["unit"] - 6.99 / 60) < 1e-4 and a["merge_into"] is None, a
    assert a["dest"]["pk"] == 473

    print("=== plan: partial (line 2 left out) ===")
    pl = E.plan(po.pk, lines={l2.pk: {"packs": 0}})
    assert [x["line"] for x in pl["lines"]] == [l1.pk] and pl["closes_order"] is False, pl

    print("=== commit partial -> new row, order stays open ===")
    rc = E.commit(pl)
    made["stock"] += [x["stock"] for x in rc["lines"]]
    row = StockItem.objects.get(pk=rc["lines"][0]["stock"])
    assert float(row.quantity) == 120.0 and row.location_id == 473 and row.purchase_order_id == po.pk
    assert "RECEIVED 120 on" in note_text(row), note_text(row)
    l1.refresh_from_db(); po.refresh_from_db()
    assert float(l1.received) == 2.0 and po.status == 20, (l1.received, po.status)

    print("=== commit the rest -> MERGE into that row, order closes ===")
    pl2 = E.plan(po.pk)
    assert pl2["lines"][0]["merge_into"] == row.pk and pl2["lines"][0]["before"] == 120.0, pl2
    rc2 = E.commit(pl2)
    row.refresh_from_db(); po.refresh_from_db()
    assert float(row.quantity) == 180.0 and po.status == 30 and po.complete_date == datetime.date.today()
    assert rc2["status"] == 30 and rc2["lines"][0]["created"] is False

    print("=== undo second commit -> 120, order reopens ===")
    u = E.undo(rc2)
    row.refresh_from_db(); po.refresh_from_db(); l2.refresh_from_db()
    assert float(row.quantity) == 120.0 and po.status == 20 and float(l2.received) == 0.0, (row.quantity, po.status)
    assert u["lines"][0]["action"] == "reduced"

    print("=== undo first commit -> row deleted ===")
    u = E.undo(rc)
    assert not StockItem.objects.filter(pk=row.pk).exists() and u["lines"][0]["action"] == "deleted"
    l1.refresh_from_db(); assert float(l1.received) == 0.0

    print("=== undo refuses when the row moved on ===")
    rc3 = E.commit(E.plan(po.pk))
    made["stock"] += [x["stock"] for x in rc3["lines"]]
    StockItem.objects.filter(pk=rc3["lines"][0]["stock"]).update(quantity=5)
    try:
        E.undo(rc3); raise AssertionError("undo should have refused")
    except RuntimeError as e:
        print("  refused:", e)

    print("=== pending: [NEEDS-DECISION] and overdue ===")
    po.refresh_from_db()
    PurchaseOrder.objects.filter(pk=po.pk).update(status=20, target_date=datetime.date.today() - datetime.timedelta(days=5))
    PurchaseOrderLineItem.objects.filter(order=po).update(received=0)
    note_set(po, "[NEEDS-DECISION] refund $6.99 against a $13.98 line: one of two returned, or both?")
    kinds = {(x["kind"], x["po"]) for x in E.pending("LRD")}
    assert ("decision", po.pk) in kinds and ("overdue", po.pk) in kinds, kinds
    print("\nALL OK")
finally:
    StockItem.objects.filter(pk__in=made["stock"]).delete()
    StockItem.objects.filter(part_id__in=made["parts"]).delete()
    PurchaseOrderLineItem.objects.filter(order_id__in=made["pos"]).delete()
    PurchaseOrder.objects.filter(pk__in=made["pos"]).delete()
    SupplierPart.objects.filter(pk__in=made["sps"]).delete()
    Part.objects.filter(pk__in=made["parts"]).delete()
    assert not Part.objects.filter(pk__in=made["parts"]).exists()
    assert not PurchaseOrder.objects.filter(pk__in=made["pos"]).exists()
    print("teardown OK:", made)
