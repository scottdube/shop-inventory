"""Bag the superseded FlightSimDIY boards as one kit, inside the spares bin.

Scott 2026-08-29: "create a kit that includes these two G1000 FlightSimDIY
boards and this audio panel board, GMA1347 control board ... stick that in a
plastic bag and give that one a label and keep that so that I don't go through
this exercise again."

THE LABEL IS THE POINT. Today cost hours reconstructing why two apparently good
control boards were sitting loose. The kit's description carries that answer,
and the QR on the label reaches it — so the next person who finds the bag gets
the reasoning, not just the boards.

Child of Sim G1000 Spares because that is physically true: a bag inside the bin.
"""
import argparse, datetime, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from stock.models import StockItem, StockLocation                # noqa: E402

SPARES, TODAY = 591, datetime.date.today()
NAME = "Kit - FSD G1000 Original (superseded)"
DESC = (
 "SUPERSEDED — KEPT ON PURPOSE, NOT FORGOTTEN. FlightSimDIY control boards for "
 "the ORIGINAL, pre-NXi G1000 architecture. Bagged together 2026-08-29 so the "
 "set and its explanation stay in one place.\n\n"
 "WHY THEY ARE NOT IN SERVICE: Peter Eier's NXi shield carries BOTH MEGAs — one "
 "for the G1000 NXi and one for the GMA1347 — so a single board replaces both "
 "of these at once. Scott's built MFD proves it: the shield drives the audio "
 "panel over two ribbons with no separate control board anywhere.\n\n"
 "SO DO NOT 'FIX' AN NXi BUILD BY REACHING IN HERE. Nothing in this bag belongs "
 "in one. They are only useful for an original non-NXi G1000, and there is no "
 "plan to build one — Scott's hand-wired original (build #1) is staying as it "
 "is.\n\n"
 "STILL WORTH SOMETHING TO SOMEBODY. Both are current FlightSimDIY products "
 "with an active community, so selling or giving them on is a real option "
 "beside keeping them. That is why they are bagged and labelled rather than "
 "binned.\n\n"
 "Full story: docs/G1000.md.")

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

bin_ = StockLocation.objects.get(pk=SPARES)
rows = list(StockItem.objects.filter(location=bin_, part__pk__in=(1156, 1157))
            .select_related("part"))
print(f"parent {bin_.pathstring}")
print(f"new kit: {NAME}")
for s in rows:
    print(f"  moving [{s.pk}] x{float(s.quantity):g} {s.part.name[:52]}")
if len(rows) != 2:
    sys.exit(f"!! expected 2 rows, found {len(rows)}")
if not a.commit:
    raise SystemExit("\nDRY RUN — add --commit")

kit = StockLocation.objects.filter(name=NAME, parent=bin_).first()
if not kit:
    kit = StockLocation.objects.create(name=NAME, parent=bin_, description=DESC)
    assert StockLocation.objects.get(pk=kit.pk).parent_id == SPARES
    print(f"\nOK  location #{kit.pk} {kit.pathstring}")

for s in rows:
    StockItem.objects.filter(pk=s.pk).update(location=kit)
    assert StockItem.objects.get(pk=s.pk).location_id == kit.pk, "move did not stick"
    print(f"OK  [{s.pk}] -> {kit.name}")

d = bin_.description.rstrip().rstrip(".")
StockLocation.objects.filter(pk=SPARES).update(description=(
    d + ". The two FSD control boards are now BAGGED as their own kit inside "
    "this bin — see 'Kit - FSD G1000 Original (superseded)'.")[:900])
print(f"\nspares bin now: {StockItem.objects.filter(location=bin_).count()} loose rows "
      f"+ 1 kit")
