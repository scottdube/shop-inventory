"""Record the QL-810W replacement on the stock row and the part.

Amazon replacement confirmed 2026-08-24: dead unit goes back to any Staples by
2026-11-19, replacement (also a Renewed unit) lands 2026-08-26.

The quantity stays 1 and is NOT zeroed. The printer is still physically on the
bench today -- it leaves when Scott carries it to Staples, and that is a
separate event from initiating an RMA. Same rule as a receipt: initiating a
return records a DECISION, not a movement, and only the drop-off is a movement.

    itq run scripts/printer_rma.py
    itq run scripts/printer_rma.py --commit
"""
import argparse
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part            # noqa: E402
from stock.models import StockItem      # noqa: E402

NOTE = ("DEAD 2026-08-24 — will not power up, no LED, and the PA-AD-001A "
        "adapter measures nothing at the barrel jack on a known-good outlet. "
        "Amazon replacement initiated the same day (PO-0134, bought 2026-08-19, "
        "$129.99): drop this unit at any Staples by 2026-11-19, replacement due "
        "2026-08-26. STILL PHYSICALLY HERE until it is carried out — initiating "
        "a return is a decision, not a movement, so the quantity stays 1. "
        "Last successful print was 2026-08-20 20:42.")

DESC_ADD = (" Bought RENEWED (refurbished), not new — $129.99, 2026-08-19; the "
            "replacement is Renewed too.")

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

si = StockItem.objects.get(pk=570)
p = Part.objects.get(pk=1057)
print(f"stock #{si.pk}  {si.part.name[:52]}")
print(f"   qty={float(si.quantity):g}  loc={si.location.pathstring}")
print(f"   notes now: {' '.join((si.notes or '').split())[:90] or '(none)'}")
print(f"\npart #{p.pk} description {len(p.description)} chars"
      f" -> {len(p.description + DESC_ADD)} (limit 250)")

if len(p.description + DESC_ADD) > 250:
    print("!! description would exceed 250 — trimming is a judgement call, stopping")
    raise SystemExit(1)

if not a.commit:
    print("\nDRY RUN — add --commit")
    raise SystemExit

StockItem.objects.filter(pk=si.pk).update(notes=NOTE)
assert StockItem.objects.get(pk=si.pk).notes == NOTE, "note did not stick"
print("\nOK  stock #570 note written")

if "RENEWED" not in p.description:
    Part.objects.filter(pk=p.pk).update(description=p.description + DESC_ADD)
    assert "RENEWED" in Part.objects.get(pk=p.pk).description
    print("OK  part #1057 description records the Renewed provenance")

fresh = StockItem.objects.get(pk=si.pk)
print(f"\nqty still {float(fresh.quantity):g} @ {fresh.location.name} "
      f"— unchanged, correctly")
