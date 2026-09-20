#!/usr/bin/env python3
"""PO-0175 / PO-0177 aftermath, 2026-09-20.

Two things the receive script does not do:

1. Annotate the two new stock rows with WHY they are where they are. The AP is
   installed and in service; the adapters are parked in Receiving waiting on the
   T400 (PO-0176, still open) and are NOT loose stock anyone should pick.

2. Put the Mini DP -> DP adapter (#1216) on the Cessna sim's BOM. Scott,
   2026-09-20: "the cable can be added to the sim bo" -> BO-0006, confirmed,
   because BO-0006 already carries the rest of that display chain (#1188 bar
   monitor, #1180 power splitter). BO-0019 "Sim Cockpit Misc" was the other
   candidate and was rejected: the adapter is not a small loose item under the
   sim, it is the link between the new card and a monitor already on BO-0006.

   Qty 1, not 2. The pack of two yields ONE adapter into the build and one
   spare; putting 2 on the BOM would claim the sim needs both and would make the
   spare invisible as a spare.

BOM-added-after-build trap (docs/TRAPS.md): build lines are generated from the
BOM at build time, so a line added now does not appear on BO-0006 by itself.
create_build_line_items() is called to pick it up. Nothing is ALLOCATED -- the
adapter is not fitted, the card has not arrived.

default_location is left EMPTY on both parts. The AP is installed, so it has no
"home" to go back to; the adapters sit in Receiving, which is a staging area and
policy says a staging area is never a default_location.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part, BomItem
from stock.models import StockItem
from build.models import Build

COMMIT = "--commit" in sys.argv

AP_NOTE = (
    "INSTALLED 2026-09-20 in the SLN mechanical room (Scott). In service, not "
    "spare -- do not pick this row. Received on PO-0175 at $61.99; the Amazon "
    "Grand Total on that order reads $0.00 because a gift card and points paid "
    "it, which is a fact about the payment and not about the AP. See TRAPS.md."
)
ADAPTER_NOTE = (
    "PARKED IN RECEIVING 2026-09-20, waiting on the NVIDIA T400 (part #1215, "
    "PO-0176, used, from an eBay private seller -- condition unstated, check it "
    "on arrival). 2 pieces from a 2-pack at $8.4950 each. ONE goes into the "
    "Cessna sim (BO-0006) to feed the bar monitor #1188 off the T400's Mini DP; "
    "the second is the spare. Not a home: when the build consumes one, the "
    "spare wants a real drawer -- B0-R2C2 is the empty large drawer earmarked "
    "2026-09-14 as the video/display cable home."
)

def annotate(part_pk, note):
    si = StockItem.objects.filter(part_id=part_pk).order_by("-pk").first()
    print(f"stock {si.pk}: part #{part_pk} qty={si.quantity} loc={si.location}")
    if not COMMIT:
        return
    StockItem.objects.filter(pk=si.pk).update(notes=note)
    got = StockItem.objects.get(pk=si.pk).notes
    assert got == note, f"note did not stick on stock {si.pk}"
    print(f"   note written and re-read OK ({len(note)} chars)")

annotate(1214, AP_NOTE)
annotate(1216, ADAPTER_NOTE)

# --- BOM ---
build = Build.objects.get(reference="BO-0006")
assembly = build.part
adapter = Part.objects.get(pk=1216)
print(f"\nBO-0006 {build.title!r} assembly={assembly.name!r} pk={assembly.pk} status={build.status}")

existing = BomItem.objects.filter(part=assembly, sub_part=adapter)
if existing.exists():
    print("   adapter already on the BOM")
else:
    print(f"   would add BOM line: {adapter.name[:60]!r} qty 1")
    if COMMIT:
        bi = BomItem.objects.create(
            part=assembly, sub_part=adapter, quantity=1,
            reference="DP-ADAPT",
            note="Mini DP on the T400 (#1215) -> DP on the bar monitor (#1188). "
                 "One of a 2-pack; the other is a spare, deliberately not on this BOM.",
        )
        got = BomItem.objects.get(pk=bi.pk)
        assert got.sub_part_id == 1216 and got.quantity == 1, "BOM line did not stick"
        print(f"   BOM line {bi.pk} written and re-read OK")

if COMMIT:
    before = build.build_lines.count()
    build.create_build_line_items()
    build.refresh_from_db()
    after = build.build_lines.count()
    print(f"   build lines {before} -> {after}")

print("\nBOM now:")
for bi in BomItem.objects.filter(part=assembly).order_by("pk"):
    print(f"   #{bi.sub_part.pk} {bi.sub_part.name[:62]!r} qty={bi.quantity}")
print("build lines:")
for bl in Build.objects.get(reference="BO-0006").build_lines.all():
    print(f"   #{bl.bom_item.sub_part.pk} qty={bl.quantity} allocated={bl.allocated_quantity()}")
if not COMMIT:
    print("\nDRY RUN -- nothing written.")
