"""Put a drawer back the way it was, so binscan can be tested on it again.

Filing is a real write. Testing the walk on a real drawer therefore consumes
the drawer: once B2-R1C1 is filed and counted, the interesting case is gone and
the next test needs a different one. This resets a row to the pre-filing state
so the SAME known-good case can be run repeatedly.

    itq run scripts/binscan_reset.py            # dry run, shows the diff
    itq run scripts/binscan_reset.py --commit

The pre-filing state is: located at the CABINET, quantity = the purchased
figure, no stocktake date, and the McMaster import's transitional notes.

**The notes are RECONSTRUCTED, not restored.** They were overwritten during the
first field test before anyone thought to keep a copy, and InvenTree does not
version the notes field. The boilerplate below was lifted verbatim from stock
456, a sibling row the import wrote in the same pass; only the purchase details
differ, and those come from the row's own text captured before the overwrite.
Verbatim for the shape, reconstructed for the specifics -- do not treat it as a
recovered original.
"""
import argparse
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from stock.models import StockItem, StockLocation      # noqa: E402

# The known-good test case: a 10-32 fillister head whose vendor label is legible
# and whose McMaster row exists in the same cabinet. It exercises the label-text
# match, not the bag-tag match, which is the weaker of the two paths.
CASES = {
    514: dict(cabinet="B2", quantity=50, bought="2022-11-30", packs=1, pack_size=50),
}

NOTES = """[ESTIMATE] Quantity is what was PURCHASED on {bought} ({packs} pack(s) of \
{pack_size}), not a count. Bought between 2021 and 2025 and drawn from since — the \
real figure is almost certainly lower. No stocktake date on purpose, so the \
never-counted report keeps surfacing this. Correct it on the B1/B2 walk.

**DRAWER UNKNOWN — this row is filed at CABINET level, which is not a place.** \
{cabinet} is a container of 44 drawers; nothing can physically be put "in \
{cabinet}". Scott, 2026-08-22: *"B1 is an area, not a storage location. How do I \
store something in B1? That doesn't make sense."* Correct.

This is a TRANSITIONAL state from the McMaster import, which knew the cabinet but \
not the drawer and refused to guess one. That was the right call — a guessed \
drawer reads as knowledge — but a cabinet-level row renders identically to a \
filed one, so it claims to be put away when it is not. Retrieval fails and \
put-away has nowhere to go.

Resolve it by opening the drawer it is actually in and recording that. Until then \
treat this as UNFILED, not as a location.

[RECONSTRUCTED by scripts/binscan_reset.py — the original notes were overwritten \
during a binscan field test. Shape copied from sibling stock 456; purchase \
details are this row's own.]"""

ap = argparse.ArgumentParser()
ap.add_argument("pk", nargs="?", type=int, default=514)
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

case = CASES.get(a.pk)
if not case:
    sys.exit(f"no reset recipe for stock {a.pk}; known: {sorted(CASES)}")

s = StockItem.objects.get(pk=a.pk)
cab = StockLocation.objects.get(name=case["cabinet"])
want_notes = NOTES.format(**case)

print(f"  stock #{a.pk}  {s.part.name[:60]}")
for field, now, then in (
    ("location", s.location.name if s.location else None, cab.name),
    ("quantity", f"{float(s.quantity):g}", f"{case['quantity']:g}"),
    ("stocktake_date", str(s.stocktake_date), "None"),
    ("notes[0:46]", (s.notes or "")[:46], want_notes[:46]),
):
    flag = "  " if str(now) == str(then) else "->"
    print(f"    {field:<15} {str(now)[:46]:<48} {flag} {then}")

if not a.commit:
    print("\n  DRY RUN — add --commit")
    raise SystemExit

StockItem.objects.filter(pk=a.pk).update(
    location=cab, quantity=case["quantity"], stocktake_date=None, notes=want_notes)

s = StockItem.objects.get(pk=a.pk)
ok = (s.location_id == cab.pk and float(s.quantity) == float(case["quantity"])
      and s.stocktake_date is None and (s.notes or "").startswith("[ESTIMATE]"))
print(f"\n  location  : {s.location.pathstring}")
print(f"  quantity  : {float(s.quantity):g}")
print(f"  stocktake : {s.stocktake_date}")
print(f"  [ESTIMATE]: {(s.notes or '').startswith('[ESTIMATE]')}")
print(f"\n  {'RESET — ready to test again' if ok else 'RESET DID NOT VERIFY'}")
