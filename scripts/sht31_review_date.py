"""Stamp the agreed review date on the two unlocated SHT31 rows.

Scott, 2026-08-26: "lets leave for another week if theyre not located by then
we'll write them off." The decision is made; only the date is outstanding. Put
it on the rows themselves so anyone who opens either one finds the deadline and
the already-agreed outcome, instead of re-opening the question.
"""
import argparse, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from stock.models import StockItem

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

STAMP = (
    "\n\nREVIEW 2026-09-02. Scott, 2026-08-26: leave one more week; if these are "
    "not located by then, WRITE THEM OFF. The decision is already made -- on that "
    "date the only question is 'found or not', not 'what should we do'.\n"
    "Do not merge these into stock 688/689 (the PO-0139 four, received "
    "2026-08-26 and physically in hand). These are the PO-0028 four and are a "
    "separate claim; merging would launder the uncertainty into a tidy number."
)

for pk in (573, 574):
    si = StockItem.objects.filter(pk=pk).first()
    if not si:
        print(f"[{pk}] gone")
        continue
    print(f"[{pk}] qty={si.quantity:g} loc={si.location or 'UNLOCATED'} "
          f"stamped={'REVIEW 2026-09-02' in (si.notes or '')}")
    if a.commit and "REVIEW 2026-09-02" not in (si.notes or ""):
        StockItem.objects.filter(pk=pk).update(notes=(si.notes or "").rstrip() + STAMP)

if a.commit:
    for pk in (573, 574):
        si = StockItem.objects.filter(pk=pk).first()
        print(f"[{pk}] verified: {'REVIEW 2026-09-02' in (si.notes or '')}")
else:
    print("\nDRY RUN -- add --commit")
