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
ap.add_argument("--answer", action="append", metavar="PART=WHAT",
                help='record an answer, e.g. --answer 291="pool controller wiring". '
                     'Use "?" for cannot-remember so it stops being asked.')
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

MARK = "CONSUMED BY:"


def known_projects():
    """Every project previously named as consuming something.

    Most shop consumption has no build order behind it — a repair, a fixture, a
    one-off — so a BOM lookup explains only a minority of gaps. The vocabulary
    has to be grown from the answers themselves, and it is stored ON THE PARTS
    rather than in a side file so it cannot drift away from the data it
    describes. Offering that list back turns the next question from recall
    ("what used these?") into recognition ("one of these?"), which is both
    easier to answer and much harder to answer wrongly.
    """
    seen = {}
    for prt in Part.objects.exclude(notes="").exclude(notes__isnull=True).only("pk", "notes"):
        for line in (prt.notes or "").splitlines():
            if MARK in line:
                what = line.split(MARK, 1)[1].strip().rstrip(".")
                if what and what != "?":
                    seen[what.lower()] = what
    return sorted(seen.values())


if a.answer:
    from datetime import date
    for spec in a.answer:
        pk_s, _, what = spec.partition("=")
        prt = Part.objects.filter(pk=int(pk_s.strip())).first()
        if not prt:
            print(f"  no part #{pk_s}"); continue
        what = what.strip() or "?"
        line = (f"{MARK} {what}  (recorded {date.today().isoformat()}, from a "
                f"purchased-vs-counted shortfall)")
        if what == "?":
            line = (f"{MARK} ? — Scott could not recall, asked "
                    f"{date.today().isoformat()}. Do not ask again; a repeated "
                    f"unanswerable question trains people to ignore the report.")
        Part.objects.filter(pk=prt.pk).update(
            notes=((prt.notes or "").rstrip() + "\n" + line).strip())
        print(f"  #{prt.pk} {prt.name[:44]}\n     {line}")
    sys.exit()

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

# Parts short at the same time, sharing a name stem, were probably used on the
# same job. Asking about the group is one question instead of several, and the
# grouping is itself the hint that jogs the memory.
groups = defaultdict(list)
for r in rows:
    groups[Part.objects.get(pk=r[1]).name.split()[0].upper()].append(r)

vocab = known_projects()
print(f"  {len(rows)} counted part(s) where fewer are on hand than were bought.\n")
if vocab:
    print("  Projects named before (recognise, do not recall):")
    for v in vocab:
        print(f"     - {v}")
    print()
print("  Ask about each ONE AT A TIME, while the part is in hand:\n")
for stem, grp in sorted(groups.items(), key=lambda kv: -max(g[0] for g in kv[1])):
  if len(grp) > 1:
      print(f"  ** {len(grp)} '{stem}' parts are short together — likely ONE job **")
  for gap, pk, buy, fr, ins in grp:
    p = Part.objects.get(pk=pk)
    if MARK in (p.notes or ""):
        continue
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
        print(f"        no build order lists this part — most consumption has none.")
        print(f"        \"What used {gap:g}?\"  answer with:")
        print(f"           itq run scripts/unaccounted.py --answer {pk}=\"the project\"")
        print(f"           itq run scripts/unaccounted.py --answer {pk}=?   (cannot recall)")
print("\n  An answer becomes a note on the part. 'Cannot remember' is also an")
print("  answer and should be recorded as one — it stops the question being")
print("  asked again every time somebody re-counts that drawer.")
