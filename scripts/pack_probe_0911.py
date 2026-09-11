"""Read-only: does the pack size on the four newest supplier parts match the
listing that was actually bought?

Raised by queue A tonight, not by a pack sweep. Attaching images to pk 1185-1188
put each Amazon listing title next to its part name, and two of them disagree
about quantity:

    pk 1186  part: "USB-C Right-Angle Adapter, male to female, 90 deg, 100W"
             listing: "Vanjua 4 Pack 90 Degree USB-C Male to Female Adapter"
    pk 1187  part: "Cable, USB-A to Micro-USB, 3 ft, USB 2.0"
             listing: "Amazon Basics 5-Pack USB-A to Micro USB Charging Cable"

That is exactly the failure CLAUDE.md describes: an importer builds a supplier
part from an order line reading "1 x <seller's title>" whether that is one cable
or a bag of five, InvenTree's default pack_quantity of 1 sticks, and the pack
size stays buried in the title until goods land and the price per piece is
absurd ($6.54 for one 3-ft cable rather than $1.31).

These POs are still PLACED, so this is cheap to fix BEFORE receiving. It is not
fixed here — pack sizes must be written through .save(), never .update() (only
pack_quantity_native is read at receive time), and the receive script refuses to
run on a mismatch, so this reports and lets the decision be Scott's.
"""
import os
import re
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import SupplierPart          # noqa: E402
from order.models import PurchaseOrderLineItem   # noqa: E402
from part.models import Part                     # noqa: E402

# pk -> the listing title read off the /dp/ page tonight
LISTINGS = {
    1185: "Monoprice DisplayPort 1.2 to DisplayPort Multi-Stream Transport (MST) Hub",
    1186: "Vanjua 4 Pack 90 Degree USB-C Male to Female Adapter, Right Angle 100W",
    1187: "Amazon Basics 5-Pack USB-A to Micro USB Charging Cable, 480Mbps, 3 Foot",
    1188: "VSDISPLAY 12.6'' IPS LCD Screen Monitor 1920x515 as PC Secondary screen",
}

# "4 Pack", "5-Pack", "Pack of 3", "10pcs"
PACK_RE = re.compile(
    r"(?:(\d+)\s*[- ]?\s*(?:pack|pcs|pieces|count|ct)\b)|(?:pack\s+of\s+(\d+))",
    re.I,
)


def claimed_pack(title):
    m = PACK_RE.search(title)
    if not m:
        return None
    return int(m.group(1) or m.group(2))


for pk in sorted(LISTINGS):
    title = LISTINGS[pk]
    p = Part.objects.filter(pk=pk).first()
    if not p:
        print(f"?? no part {pk}")
        continue
    print()
    print(f"pk {pk}: {p.name}")
    print(f"   listing : {title}")
    want = claimed_pack(title)
    print(f"   listing claims pack = {want if want else '1 (no pack wording)'}")

    for sp in SupplierPart.objects.filter(part=p):
        # Stored twice; only *_native is read at receive time (docs/TRAPS.md).
        text = sp.pack_quantity
        native = sp.pack_quantity_native
        print(f"   supplierpart {sp.pk} {sp.supplier.name if sp.supplier else '?'}"
              f":{sp.SKU}  pack_quantity={text!r} native={native}")
        if text is not None and native is not None:
            try:
                if float(str(text)) != float(native):
                    print("   !! text and native DISAGREE — the screens lie, "
                          "receive reads native")
            except ValueError:
                pass
        if want and float(native or 1) != float(want):
            print(f"   !! MISMATCH: listing says {want}, native says {native} — "
                  f"receiving would book the whole pack price against one piece")
        elif want:
            print("   ok: pack size matches the listing")
        else:
            print("   ok: single item, nothing to reconcile")

    for li in PurchaseOrderLineItem.objects.filter(part__part=p).select_related("order"):
        unit = li.purchase_price
        per_piece = None
        if unit is not None and want:
            try:
                per_piece = float(unit.amount) / want
            except (AttributeError, TypeError, ZeroDivisionError):
                per_piece = None
        extra = f"  -> ${per_piece:.2f}/piece if pack={want}" if per_piece else ""
        print(f"   PO {li.order.reference} qty={li.quantity} "
              f"price={unit} received={li.received}{extra}")
