"""Florida pack, 2026-10-10, part 2.

Scott: "scope and microscope commute back in spring at least the o scope maybe
not the other. Also brady210 labelmaker going in box 2".

  1. Rigol DHO914 (#481) and Andonstar AD249S-M (#195) existed as PARTS with no
     stock row at all -- a commute marker needs a row and a home. Each gets one
     row at SLN/Electronics Bench (pk 6), the home trip.py captures. Marking is
     done afterwards with trip.py; the microscope's note carries Scott's "maybe
     not", because a commuter that stays is one unmark, while a one-way earmark
     on a tool that comes back loses its SLN home.
  2. FL-02 created beside FL-01, same contract: the box is the thing, a
     TransferOrder is its manifest. TO-0002 rather than more lines on TO-0001,
     because TO lines aggregate by PART and would lose which box a thing is in.
  3. Brady label maker: not in inventory (only the M21 heat-shrink cartridge,
     #437). Named "M210" from Scott's spoken "brady210" -- the Brady M210 takes
     M21 cartridges, which fits -- but the model plate has NOT been read.
     Filed straight into FL-02: Scott said it is going in box 2 tonight.

    itq run scripts/fl02_brady_scopes_1010.py            # dry run
    itq run scripts/fl02_brady_scopes_1010.py --commit
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model  # noqa: E402
from part.models import Part, PartCategory  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402
from order.models import (TransferOrder, TransferOrderLineItem,  # noqa: E402
                          TransferOrderAllocation)

COMMIT = "--commit" in sys.argv
BENCH = StockLocation.objects.get(pk=6); assert BENCH.pathstring == "SLN/Electronics Bench"
STAGE = StockLocation.objects.get(pk=503); assert STAGE.pathstring == "SLN/Florida Staging"
TEST = PartCategory.objects.get(pk=38); assert TEST.pathstring == "Equipment/Test Equipment"
TO1 = TransferOrder.objects.get(reference="TO-0001")
user = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()

for pk in (481, 195):
    p = Part.objects.get(pk=pk)
    rows = list(StockItem.objects.filter(part=p))
    print(f"part #{pk} {p.name[:50]}: {len(rows)} stock row(s)")
fl2 = StockLocation.objects.filter(name="FL-02", parent=STAGE).first()
brady = Part.objects.filter(name__icontains="Brady M210").first()
print(f"FL-02 exists: {fl2}; Brady part exists: {brady}")
if not COMMIT:
    sys.exit("\nDRY RUN -- add --commit")

for pk in (481, 195):
    p = Part.objects.get(pk=pk)
    if not StockItem.objects.filter(part=p).exists():
        s = StockItem(part=p, location=BENCH, quantity=1,
                      notes="Row created 2026-10-10: the part existed with no stock. "
                            "One unit, lives on the SLN electronics bench.")
        s.save(); s.refresh_from_db()
        assert s.location_id == BENCH.pk and float(s.quantity) == 1
        print(f"CREATED SI #{s.pk} {p.name[:40]} @ {BENCH.pathstring}")
    if p.default_location_id != BENCH.pk:
        Part.objects.filter(pk=pk).update(default_location=BENCH)
        print(f"  part #{pk} default_location {p.default_location} -> {BENCH.pathstring}")

if not fl2:
    fl2 = StockLocation(name="FL-02", parent=STAGE,
                        description="Florida carry box 2. Physical box at SLN being filled for "
                                    "the next trip. Everything in here should also appear on a "
                                    "TransferOrder (TO-0002) - the box is the thing, the TO is "
                                    "the manifest.")
    fl2.save(); fl2.refresh_from_db()
    assert fl2.parent_id == STAGE.pk
    print(f"CREATED location #{fl2.pk} {fl2.pathstring}")

if not brady:
    brady = Part(
        name="Brady M210 Portable Label Printer",
        description="Handheld label maker; takes Brady M21 cartridges (labels, PermaSleeve heat-shrink)",
        keywords="label maker, label printer, Brady, M210, M21, BMP21, handheld, wire marker",
        category=TEST, component=False, purchaseable=True, assembly=False,
        notes=("Filed 2026-10-10 from Scott's spoken \"brady210\". **Model plate not "
               "read** -- confirm M210 vs BMP21-PLUS off the back of the unit. "
               "Cartridge in stock: Brady M21-125-C-342 PermaSleeve (part #437).\n\n"
               "Packed in FL-02 for LRD, 2026-10-10."))
    brady.save(); brady.refresh_from_db()
    assert brady.category_id == TEST.pk
    print(f"CREATED part #{brady.pk} {brady.name}")
bs = StockItem.objects.filter(part=brady).first()
if not bs:
    bs = StockItem(part=brady, location=fl2, quantity=1,
                   notes="Filed straight into FL-02 2026-10-10 (Scott: going in box 2).")
    bs.save(); bs.refresh_from_db()
    assert bs.location_id == fl2.pk
    print(f"CREATED SI #{bs.pk} @ {fl2.pathstring}")

to2 = TransferOrder.objects.filter(reference="TO-0002").first()
if not to2:
    to2 = TransferOrder(reference="TO-0002", description="Florida carry box 2 (FL-02)",
                        take_from=TO1.take_from, destination=TO1.destination,
                        created_by=user, status=TO1.status)
    to2.save(); to2.refresh_from_db()
    assert to2.reference == "TO-0002"
    print(f"CREATED {to2.reference} (reference_int {to2.reference_int})")
line, _ = TransferOrderLineItem.objects.get_or_create(order=to2, part=brady, defaults={"quantity": 1})
TransferOrderAllocation.objects.get_or_create(line=line, item=bs, defaults={"quantity": 1})
print(f"{to2.reference}: {to2.lines.count()} line(s), "
      f"{sum(l.allocations.count() for l in to2.lines.all())} allocation(s)")
print(f"\nNEXT: trip.py mark the two scope rows above.")
