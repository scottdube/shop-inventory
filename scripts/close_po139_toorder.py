"""Post-receipt tidy for PO-0139: record the receipt, drop the satisfied want.

TO-ORDER line 41 was "CONFIRMED SHORT 2 for the Florida pair (BO-0009)". PO-0139
delivered the 4-pack and two went to RB-12, so the want is met. A standing
to-order list that still asks for what just arrived is how a thing gets bought
twice -- the line goes, and PO-0139's notes carry why it existed.
"""
import argparse, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from order.models import PurchaseOrder, PurchaseOrderLineItem

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

po = PurchaseOrder.objects.get(reference="PO-0139")
want = PurchaseOrderLineItem.objects.filter(pk=41).first()

print(f"PO-0139: {po.get_status_display()}")
print(f"TO-ORDER line 41: {'present' if want else 'already gone'}")
if not a.commit:
    print("\nDRY RUN -- add --commit")
    sys.exit()

PurchaseOrder.objects.filter(pk=po.pk).update(
    notes=(po.notes or "").rstrip() + (
        "\n\nRECEIVED 2026-08-26. One pack, 4 pieces, counted in hand by Scott. "
        "2 -> RB-12 (RAT GDO kit, BO-0009), 2 -> B3-R4C8 as spares.\n"
        "Line repaired at receiving from qty=1 @ $16.99 to 4 @ $4.2475; the "
        "sweep had booked the pack price against one piece. Line total is still "
        "exactly $16.99 -- the $4.25 shown in the UI is display rounding, the "
        "stored price carries six decimals.\n"
        "TO-ORDER line 41 (4 more of this ASIN, raised when the drawer counted "
        "zero on 2026-08-20) removed here as satisfied by this order.\n"
        "Does NOT resolve stock 573/574 -- the PO-0028 four are still "
        "owned-but-location-unknown, and 8 on the books means 4 findable."
    )
)
if want:
    want.delete()

po.refresh_from_db()
print("\nnotes tail:", po.notes.strip().splitlines()[-1])
print("TO-ORDER line 41 now:",
      "gone" if not PurchaseOrderLineItem.objects.filter(pk=41).exists() else "STILL THERE")
print("TO-ORDER remaining lines:")
for l in PurchaseOrder.objects.get(reference="TO-ORDER").lines.all():
    print(f"  {l.pk}: {l.part.part.name[:55]} qty={l.quantity:g}")
