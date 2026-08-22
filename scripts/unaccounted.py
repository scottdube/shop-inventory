"""Where did the missing ones go? Compare purchased against counted.

Reconstructing consumption from build records did not work: those records were
written up after the fact, so their dates describe when someone typed them, not
when anything was soldered. See docs/TRAPS.md.

This works the other way round, from the two facts that ARE trustworthy —
**what was bought** (purchase orders, with real quantities) and **what is on the
shelf right now** (a count you just did). The gap between them is consumption,
and Scott can usually name the project that ate it *if asked while holding the
part*. Six months later nobody can.

    itq run scripts/unaccounted.py                 # everything counted so far
    itq run scripts/unaccounted.py --location B3   # just what you are counting
    itq run scripts/unaccounted.py --min-gap 2

Only counted stock is compared. An [ESTIMATE] quantity cannot reveal a gap —
subtracting a guess from a purchase produces a fictional shortfall, which is
worse than no answer because it looks like evidence.

Stock installed into an assembly (`belongs_to`) counts as ACCOUNTED FOR, not
missing: it is inside something and the record says which. That is the whole
point of installing it rather than deleting it.
"""
import argparse, os, sys, django
from collections import defaultdict

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part
from stock.models import StockItem
from order.models import PurchaseOrderLineItem
from build.models import Build, BuildLine

ap = argparse.ArgumentParser()
ap.add_argument("--location", help="restrict to parts stocked under this location name")
ap.add_argument("--min-gap", type=float, default=1.0, help="ignore shortfalls below this")
ap.add_argument("--all", action="store_true", help="include never-counted parts (noisy)")
a = ap.parse_args()

# --- what was bought -----------------------------------------------------
bought = defaultdict(float)
packs = {}
for li in (PurchaseOrderLineItem.objects
           .filter(order__status__in=[20, 30])          # placed or complete
           .select_related("part", "part__part", "order")):
    if not li.part or not li.part.part:
        continue
    try:
        pack = float(li.part.pack_quantity or 1) or 1.0
    except (TypeError, ValueError):
        pack = 1.0
    # received is what actually arrived; fall back to ordered for old imports
    qty = float(li.received or 0) or float(li.quantity or 0)
    bought[li.part.part_id] += qty * pack
    packs[li.part.part_id] = pack

# --- what is here now ----------------------------------------------------
free, installed, counted, est = (defaultdict(float), defaultdict(float),
                                 defaultdict(bool), defaultdict(bool))
for s in StockItem.objects.select_related("part", "location"):
    if a.location and not (s.location and a.location.lower() in s.location.pathstring.lower()):
        continue
    q = float(s.quantity)
    if s.belongs_to_id:
        installed[s.part_id] += q
    else:
        free[s.part_id] += q
    if s.stocktake_date:
        counted[s.part_id] = True
    if (s.notes or "").startswith("[ESTIMATE]"):
        est[s.part_id] = True

rows = []
for pk, buy in bought.items():
    if not counted[pk] and not a.all:
        continue
    if est[pk] and not a.all:
        continue
    have = free[pk] + installed[pk]
    gap = buy - have
    if gap >= a.min_gap:
        rows.append((gap, pk, buy, free[pk], installed[pk]))

# --- can a build already explain the gap? -------------------------------
# Asking "what used 3 of these?" is a memory test. Asking "BO-0013 needed 1 —
# was it that?" is a yes/no. Always prefer confirmation to recall: it is far
# more reliable, and it fails safe, because a wrong suggestion gets corrected
# while a blank prompt gets a shrug.
suspects = defaultdict(list)
for bl in (BuildLine.objects
           .filter(build__status__in=[20, 40])          # in production or complete
           .select_related("build", "bom_item__sub_part")):
    suspects[bl.bom_item.sub_part_id].append(
        (bl.build.reference, bl.build.title, float(bl.quantity), bl.build.status))

rows.sort(reverse=True)
if not rows:
    print("  Nothing unaccounted for among counted parts.")
    print("  (Parts still on [ESTIMATE] are skipped — a guess cannot reveal a gap.)")
    sys.exit()

print(f"  {len(rows)} counted part(s) where fewer are on hand than were bought.\n")
print("  Ask about each ONE AT A TIME, while the part is in hand:\n")
for gap, pk, buy, fr, ins in rows:
    p = Part.objects.get(pk=pk)
    inst = f", {ins:g} installed in an assembly" if ins else ""
    print(f"  #{pk:<5} {p.name[:56]}")
    print(f"        bought {buy:g}, on shelf {fr:g}{inst}  ->  MISSING {gap:g}")
    hits = suspects.get(pk, [])
    if hits:
        for ref, title, need, st in hits:
            state = "completed" if st == 40 else "in production"
            match = "  <-- matches the gap exactly" if abs(need - gap) < 0.01 else ""
            print(f"        candidate: {ref} ({state}) needs {need:g} — {title[:34]}{match}")
        print(f"        \"Was it {hits[0][0]}?\"  (yes / no / cannot remember)")
    else:
        print(f"        no build lists this part.")
        print(f"        \"What used {gap:g}? Any project you remember?\"")
print("\n  An answer becomes a note on the part. 'Cannot remember' is also an")
print("  answer and should be recorded as one — it stops the question being")
print("  asked again every time somebody re-counts that drawer.")
