"""Put the BOJACK T3AL250V 3 A 5x20 slow-blow fuses on the books, homed in the
Tormach 1100MX electrical cabinet (Scott, 2026-10-04: "their location is 1100MX
electrical cabinet").

Part #36 already exists (seeded from purchase history, stock 0, no home), so this
ENRICHES it rather than creating a twin. No PO exists for Amazon order
112-7363556-2703463 and none is created: receiving one would only restate the
purchase, and the quantity below is not a count either way.

Quantity: 20 bought 2025-07-27, one went into ECM1 F1 on 2026-10-04 -> 19.
That is tier-3 arithmetic, not a count: [ESTIMATE], no stocktake_date.

Dry run by default; --commit writes, then re-reads every write.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part
from stock.models import StockItem, StockLocation

COMMIT = "--commit" in sys.argv
PART_PK, PARENT_PK = 36, 420          # part #36; SLN/Machine Shop
LOC_NAME = "1100MX Electrical Cabinet"
LOC_DESC = ("Electrical cabinet at the BACK of the Tormach 1100MX (controls are at the front, so "
            "the cabinet is awkward to reach). Holds the machine's own spares: the 3 A slow-blow "
            "5x20 fuses for ECM1 F1 (flood) / F2 (mist). Service records: ~/code/tormach-1100mx.")
QTY = 19
STOCK_NOTE = ("[ESTIMATE] 19 = 20-pack (Amazon 112-7363556-2703463, 2025-07-27) minus the one fitted "
              "to ECM1 F1 on 2026-10-04. Arithmetic, not a count; whether a spare also went into F2 "
              "at the 2025 mist-outlet install is unknown. Count the box to replace this figure.")
PART_NOTE = ("\n\n2026-10-04: these are the Tormach 1100MX coolant-outlet fuses (ECM1 F1 flood, "
             "F2 mist). Tormach PN 31120, DigiKey 507-1297-ND equivalent; rating checked against "
             "SB10828 (3 A slow-blow 5x20). Bought for the mist-outlet install, Amazon order "
             "112-7363556-2703463, 2025-07-27, pack of 20, $6.99. Homed in the 1100MX electrical "
             "cabinet per Scott. Fault record: ~/code/tormach-1100mx/docs/coolant-outlet-fault.md.")
KEYWORDS = "fuse, slow blow fuse, time delay fuse, glass fuse, 5x20mm, 3A, T3AL250V, Tormach 31120, ECM1, F1, F2, coolant, 1100MX"

p = Part.objects.get(pk=PART_PK)
print(f"part #{p.pk} active={p.active} name={p.name!r}")
print(f"  desc={p.description!r}\n  keywords={p.keywords!r}\n  default_loc={p.default_location}")
print(f"  notes={p.notes!r}")
print(f"  supplier parts: {[ (sp.pk, str(sp.supplier), sp.SKU, sp.pack_quantity) for sp in p.supplier_parts.all()]}")
print(f"  stock rows: {[(s.pk, s.quantity, str(s.location)) for s in StockItem.objects.filter(part=p)]}")
parent = StockLocation.objects.get(pk=PARENT_PK)
print(f"parent loc {parent.pk} {parent.pathstring}; children: {[c.name for c in parent.get_children()]}")
existing = StockLocation.objects.filter(parent=parent, name__iexact=LOC_NAME).first()
print(f"target location exists: {existing}")

if not COMMIT:
    print("DRY RUN - nothing written"); sys.exit(0)

loc = existing or StockLocation.objects.create(name=LOC_NAME, description=LOC_DESC, parent=parent)
loc = StockLocation.objects.get(pk=loc.pk)
assert loc.parent_id == PARENT_PK and loc.name == LOC_NAME, "location write did not land"

p.default_location = loc
if "112-7363556-2703463" not in (p.notes or ""):
    p.notes = (p.notes or "") + PART_NOTE
p.keywords = KEYWORDS
p.save()
p2 = Part.objects.get(pk=PART_PK)
if p2.default_location_id != loc.pk or "112-7363556-2703463" not in (p2.notes or ""):
    print("save() did not land - falling back to queryset update")
    Part.objects.filter(pk=PART_PK).update(default_location=loc, notes=p.notes, keywords=KEYWORDS)
    p2 = Part.objects.get(pk=PART_PK)
assert p2.default_location_id == loc.pk and "112-7363556-2703463" in p2.notes and p2.keywords == KEYWORDS

if StockItem.objects.filter(part=p2, location=loc).exists():
    print("stock row already present at the location - not adding a second")
else:
    StockItem.objects.create(part=p2, location=loc, quantity=QTY, notes=STOCK_NOTE)
rows = list(StockItem.objects.filter(part=p2, location=loc))
assert len(rows) == 1 and rows[0].quantity == QTY and rows[0].notes.startswith("[ESTIMATE]") \
    and rows[0].stocktake_date is None, rows
print(f"VERIFIED: location #{loc.pk} {loc.pathstring}; part #{p2.pk} default_loc set; "
      f"stock #{rows[0].pk} qty={rows[0].quantity} [ESTIMATE], stocktake_date=None")
