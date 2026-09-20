"""MC-T3 drawer count, 2026-09-20: the third HiLetgo pot and a sixth dual encoder.

Three jobs, one run, because they came out of the same drawer in the same pass.

1. Fold #256 into #812. Textbook import twins - both are the 3590S-2-103L.
   #812 is the keeper AND keeps its own name: #256's name is a truncated Amazon
   title, so this is the reverse of the #53/#242 merge where the tidy name was
   on the folded part. #256 carries SP156 and the purchase history, which move.

2. Stock 214 goes 2 -> 3. The row's own note from 2026-08-19 said a HiLetgo
   3-pack was bought, two were in the bag, and "one is unaccounted for - may
   turn up in another drawer." It turned up in MC-T3. The date code on the
   part in hand, 2218M, matches the description already on #812, so this is
   the same pack and not a second purchase.

3. Part #95 gets a real description and its first stock rows. Six on hand, not
   the five the count sheet had. default_location stays EMPTY on purpose - an
   empty field asks where a spare goes home, a wrong one answers it badly.
"""
import os, sys, django
from datetime import date
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part
from stock.models import StockItem, StockLocation
from company.models import SupplierPart
from django.contrib.auth import get_user_model

COMMIT = "--commit" in sys.argv
TODAY = date.today()
MCT3 = StockLocation.objects.get(pk=432)
user = get_user_model().objects.filter(is_superuser=True).first()

f, k = Part.objects.get(pk=256), Part.objects.get(pk=812)
print("=== 1. fold #256 -> #812 ===")
print("  fold : %s" % f.name[:70])
print("  keep : %s" % k.name)
print("  SPs to move: %s   stock rows to move: %s"
      % (SupplierPart.objects.filter(part=f).count(),
         StockItem.objects.filter(part=f).count()))
print("  --- FULL NOTES ON #256 (read before touching pack size) ---")
print(f.notes or "(none)")
print("  --- end ---")

p95 = Part.objects.get(pk=95)
NEW95 = ("Dual-shaft concentric rotary encoder, GREEN base, 30 positioning, "
         "5 pins + 2. Sold as EC11EBB24C03 but NOT a genuine Alps part "
         "(Scott, 2026-09-20). Field marks: green body, bag SKU GFKA0001-001. "
         "G1000 faceplate uses 5.")
print()
print("=== 3. part #95 description ===")
print("  old: %s" % p95.description)
print("  new: %s  (%d chars)" % (NEW95, len(NEW95)))
assert len(NEW95) <= 250, "description too long"
print("  existing stock rows: %s" % StockItem.objects.filter(part=p95).count())

if not COMMIT:
    print("\nDRY RUN - add --commit")
    sys.exit()

# --- 1. merge ---
SupplierPart.objects.filter(part=f).update(part=k)
StockItem.objects.filter(part=f).update(part=k)
k_notes = ((k.notes or "").rstrip() + """

Merged with import twin part #%d on %s - both are the 3590S-2-103L 10k
10-turn. #%d was built from an Amazon order line (SKU B079JN626M, HiLetgo
3pcs, 2023-07-22, $9.79) and never had stock; its SupplierPart and purchase
history moved here. This part keeps its own name: #%d's was a truncated
vendor title, which is the opposite of the #53/#242 case.

Genuine-vs-clone was the one real risk in merging these, since HiLetgo is a
reseller and "3590S-2-103L" is widely copied. Settled by the part in hand on
%s: stamped MEXICO / BOURNS / 3590S-2-103L / 2218M, the same date code
already recorded in this description. HiLetgo shipped genuine Bourns.
""" % (f.pk, TODAY, f.pk, f.pk, TODAY)).strip()
Part.objects.filter(pk=812).update(notes=k_notes)
f_notes = ((f.notes or "").rstrip() +
           "\n\n**MERGED** into #812 on %s - both are the 3590S-2-103L." % TODAY).strip()
Part.objects.filter(pk=256).update(
    active=False, notes=f_notes,
    description=("MERGED into part #812 (Bourns 3590S-2-103L Precision "
                 "Potentiometer 10k, 10-turn). " + (f.description or ""))[:250])

# --- 2. stock 214: 2 -> 3 ---
si = StockItem.objects.get(pk=214)
si.quantity = 3
si.notes = """Counted in hand 2026-08-19: two in the bag. Bought as a HiLetgo
3-pack, so one was unaccounted for.

FOUND 2026-09-20 in MC-T3 during the G1000 drawer count - the third of the
pack. Now 3, which closes the 3-pack. Scott: not used, not salvage, NEW.

ONE OF THE THREE IS NOT PRISTINE: it carries white and yellow flying leads
soldered to its lugs with heatshrink, fitted for a job that was never done.
Electrically unused and new, but do not expect three bare parts in this bag.
Unsolder it or use it as-is; nothing about the pot itself was modified."""
si.save()

# --- 3. part #95 + its first stock ---
Part.objects.filter(pk=95).update(description=NEW95)

five = StockItem.objects.create(
    part=p95, quantity=5, location=MCT3,
    batch="G1000 PFD build #3", purchase_price=None)
five.notes = """Counted by Scott 2026-09-20 during the MC-T3 drawer count:
4 in bags marked SKU GFKA0001-001 plus 1 loose, all green-base. This is the
full set the G1000 faceplate needs - 5 fitted, ZERO spare in the bag.

Bound for LRD for build #3 (the PFD). A sixth was found in the same drawer
(stock row below) but Scott is keeping that one at SLN, so it is NOT margin
for this build - it would be 1500 miles from the bench."""
five.metadata = {'florida': {'qty': 5.0, 'why': 'G1000 build #3 (PFD) at LRD - BO-0017 - 5 fitted on the faceplate, no spare', 'added': '2026-09-20'}}
five.save()
five.tags.add('florida')

one = StockItem.objects.create(part=p95, quantity=1, location=MCT3)
one.notes = """Found loose in MC-T3 on 2026-09-20, a SIXTH dual encoder beyond
the 5 the G1000 faceplate needs. Scott: stays at SLN as stock, does not travel.

PARKED AT MC-T3 ONLY BECAUSE THAT IS WHERE IT PHYSICALLY IS. This is not its
home - part #95 has no default_location yet and the field was deliberately
left empty rather than guessed. Move this row when the home bin is chosen.
B3-R2C7 already holds the PropWash dual concentric encoder kit and is the
obvious neighbour, but that is a suggestion, not a decision."""
one.save()

# --- verify by re-read ---
f, k = Part.objects.get(pk=256), Part.objects.get(pk=812)
si = StockItem.objects.get(pk=214)
p95 = Part.objects.get(pk=95)
rows = StockItem.objects.filter(part=p95).order_by('pk')
print()
print("#256 active=%s  %s" % (f.active, f.description[:50]))
print("#812 SPs=%s  stock=%s" % (SupplierPart.objects.filter(part=k).count(), k.total_stock))
print("stock 214 qty=%s" % si.quantity)
print("#95 qty=%s defloc=%s" % (p95.total_stock, p95.default_location))
for r in rows:
    print("   row %s qty=%s loc=%s tags=%s" % (r.pk, r.quantity, r.location, list(r.tags.names())))
ok = (not f.active and SupplierPart.objects.filter(part=k).count() == 1
      and si.quantity == 3 and p95.total_stock == 6
      and p95.default_location is None and rows.count() == 2)
print("VERIFIED" if ok else "MISMATCH - stop and look")
