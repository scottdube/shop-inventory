#!/usr/bin/env python3
"""File 7 STARELO R13-507 panel buttons into B0-R2C1, opening the controls row.

Wire-shelf stock-in, 2026-09-14. Scott produced a bag labelled
"R13-507 FIVE COLOR-5PCS", ASIN X0038F1NUV.

ONE PART, TWO SUPPLIER SKUS -- not a new part. #203 already IS this switch:
STARELO R13-507, 16 mm, SPST momentary, pre-soldered leads. What differs is
the LISTING: #203's ASIN B09YTYHZQM is a 10-pack (two each of five colours),
this bag's X0038F1NUV is a 5-pack. A pack is a supplier fact and stock counts
pieces, so the second ASIN becomes a SupplierPart at pack_quantity 5 and the
part stays one.

THE BAG IS NO LONGER AN AS-SOLD PACK. It says 5 PCS; Scott counted SEVEN. So
the label is not evidence of quantity here and the count is the tallied
figure, carrying no [ESTIMATE] marker. Recorded explicitly, because a future
reader seeing 7 against a 5-pack SKU would reasonably suspect a data error.

THE 2022 TEN-PACK IS CONSUMED, NOT MISSING. #203's notes have carried
"Placed in B3-R1C7 -- INFERRED from the drawer label; verify" since August,
an open question about ten switches nobody had confirmed. Scott, today: "the
10 pack is long gone." That closes it as consumption rather than leaving a
phantom ten on the books.

WHY B0-R2C1 AND NOT THE PTT DRAWER. Scott: "going to need space wont fit in
small drawer." B3 has ZERO empty large drawers, and B3-R1C7 already holds
eight button types. B0 has 20 empty large drawers and its R1 row is the cable
row, so R2 opens as panel controls -- pre-wired switches with long leads
belong beside cables, not in a fastener cabinet.

    itq run scripts/file_starelo_buttons.py
    itq run scripts/file_starelo_buttons.py --commit
"""
import os
import sys
from decimal import Decimal

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import Company, SupplierPart  # noqa: E402
from part.models import Part  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

COMMIT = "--commit" in sys.argv
ASIN = "X0038F1NUV"
COUNT = Decimal("7")

p = Part.objects.get(pk=203)
loc = StockLocation.objects.get(pk=566)          # B0-R2C1
print(f"part  [{p.pk}] {p.name[:70]}")
print(f"dest  {loc.pathstring}")
print(f"count {float(COUNT):g} (tallied by Scott; bag is labelled 5)")
print(f"existing stock rows: {StockItem.objects.filter(part=p).count()}")

if not COMMIT:
    print("\nDRY RUN — nothing written. Re-run with --commit.")
    sys.exit(0)

si = StockItem.objects.create(
    part=p, location=loc, quantity=COUNT,
    notes=("COUNTED 7 by Scott 2026-09-14 during the wire-shelf stock-in. A "
           "tallied figure, not an estimate.\n\n"
           "SEVEN IN A BAG LABELLED FIVE. The bag is STARELO ASIN "
           "X0038F1NUV, 'R13-507 FIVE COLOR-5PCS'. It holds 7, so it is no "
           "longer an as-sold pack -- do not 'correct' this to 5 on the "
           "strength of the label. Mixed colours; no per-colour breakdown was "
           "taken, and nobody should infer one."),
)
print(f"\nstock {si.pk}: {float(si.quantity):g} @ {si.location.pathstring}")

amazon = Company.objects.filter(name__istartswith="Amazon").first()
if not SupplierPart.objects.filter(part=p, SKU=ASIN).exists():
    sp = SupplierPart.objects.create(
        part=p, supplier=amazon, SKU=ASIN,
        link=f"https://www.amazon.com/dp/{ASIN}",
        note="5-pack, one each of five colours. The OTHER SKU for this same "
             "switch, B09YTYHZQM, is a 10-pack (two each). Same part, "
             "different listing.")
    SupplierPart.objects.filter(pk=sp.pk).update(pack_quantity="5")
    sp.refresh_from_db()
    print(f"supplier part {sp.pk}: {ASIN} pack_quantity={sp.pack_quantity}")

p.default_location = loc
p.save()
p.refresh_from_db()
if p.default_location_id != loc.pk:
    Part.objects.filter(pk=p.pk).update(default_location=loc)
    p.refresh_from_db()
print(f"default_location -> {p.default_location.pathstring}")

# Close the August "verify" question rather than leaving it hanging.
STALE = "Placed in **B3-R1C7** (Momentary mini PTT) — INFERRED from the drawer label; verify."
closed = ("> **RESOLVED 2026-09-14.** The August note below guessed B3-R1C7 from a "
          "drawer label and asked someone to verify it. Scott: \"the 10 pack is long "
          "gone\" — the 2022-12-30 ten-pack was USED, not mislaid, so there is no "
          "phantom stock to find. Current stock is a separate later purchase (ASIN "
          "X0038F1NUV), 7 pieces, now in B0-R2C1.\n>\n> ~~" + STALE + "~~")
if STALE in (p.notes or ""):
    Part.objects.filter(pk=p.pk).update(notes=p.notes.replace(STALE, closed, 1))
    p.refresh_from_db()
print(f"August 'verify' question closed: {'RESOLVED 2026-09-14' in p.notes}")

loc.description = (
    "PANEL CONTROLS — switches, buttons and indicators that mount THROUGH a "
    "panel, with their leads. Pre-wired 16 mm pushbuttons, pilot lights, "
    "rotary and toggle switches in panel-mount bodies. Established 2026-09-14, "
    "opening B0 row 2.\n\n"
    "WHY HERE AND NOT B3. B3 is the electronics cabinet and is the right "
    "category, but it has ZERO empty large drawers and its small 'Momentary "
    "mini PTT' drawer (B3-R1C7) already holds eight button types. Scott: "
    "\"going to need space wont fit in small drawer.\" These come with six "
    "inches of lead on them and need the volume.\n\n"
    "NOT the PCB-mount buttons. Tactile switches and anything that solders "
    "into a board stay in B3-R1C2. The test is whether it needs a hole in a "
    "panel. [6 x 4-9/16 x 2-3/16 in, large]"
)
loc.save()
loc.refresh_from_db()
print(f"B0-R2C1 scope written: {'PANEL CONTROLS' in loc.description}")
