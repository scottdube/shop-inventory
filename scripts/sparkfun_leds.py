"""File the SparkFun kit's surviving LEDs — which are 3mm, not 5mm.

The SparkFun kit list says "LED 5mm". The box says otherwise: on 2026-08-21
Scott counted what is actually left and found **one 3mm each of red, yellow
and green**. The list was wrong, or the 5mm ones are long gone; either way the
parts in hand are 3mm and get filed as 3mm.

This also corrects a merge made earlier the same day. `dissolve_sparkfun.py`
folded the kit's `LED 5mm Green` (#707) and `LED 5mm Red` (#709) into the
existing Clear 5mm records on the strength of that list. Footprint is part
identity here — a 3mm and a 5mm LED are different parts — so those merges
asserted something the box then disproved. No stock moved (both losers were at
zero), so the fix is to the record, not to the shelf: the keepers get a note
saying what the absorption was based on and that it turned out to be wrong.

    itq run scripts/sparkfun_leds.py            # dry run
    itq run scripts/sparkfun_leds.py --commit
"""
import argparse, os, sys, django
from datetime import date

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.contrib.auth import get_user_model
from part.models import Part
from stock.models import StockItem, StockLocation

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

DRAWER = 303          # B3-R2C2, where LED 3mm Red already lives
RED_3MM = 814
today = date.today()

# Named after #814 "LED 3mm Red", which asserts no clear/diffused distinction.
# Neither will these — nobody has stated it, and a guess is not an improvement.
NEW = [("LED 3mm Green", "green"), ("LED 3mm Yellow", "yellow")]

CORRECTION = (
    "\n\n**Correction 2026-08-21:** the SparkFun kit record absorbed above was "
    "matched on the kit list's claim of *5mm*. Counting the box the same day "
    "found its surviving LEDs are **3mm**, so that match was wrong on "
    "footprint. No stock moved — the absorbed record was at zero — and the "
    "kit's actual LEDs were filed as 3mm at B3-R2C2. This part's own stock is "
    "unaffected."
)

drawer = StockLocation.objects.get(pk=DRAWER)
red = Part.objects.get(pk=RED_3MM)
cat = red.category
user = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()

print(f"drawer: {drawer.name}   category: {cat}\n")

print("=== red: add to the existing record ===")
si = StockItem.objects.filter(part=red, location=drawer).first()
before = si.quantity if si else 0
print(f"  #{RED_3MM} {red.name}: {before} -> {before + 1}  (stocktake {today})")

print("\n=== green / yellow: no 3mm record exists, create ===")
for name, colour in NEW:
    ex = Part.objects.filter(name=name).first()
    print(f"  {name}: " + (f"already exists as #{ex.pk}" if ex else "CREATE, qty 1"))

print("\n=== correct the merge notes on the 5mm keepers ===")
for pk in (762, 764):
    p = Part.objects.get(pk=pk)
    done = "Correction 2026-08-21" in (p.notes or "")
    print(f"  #{pk} {p.name[:34]:34} " + ("already noted" if done else "add correction"))

if not a.commit:
    print("\nDRY RUN")
    sys.exit(0)

# ---- write ----
if si:
    si.quantity = before + 1
else:
    si = StockItem.objects.create(part=red, location=drawer, quantity=1)
si.stocktake_date = today
si.notes = ((si.notes or "").rstrip() +
            f"\n\nCounted 2026-08-21: +1 absorbed from the SparkFun beginners "
            f"kit as it was dissolved.").strip()
si.save()

made = []
for name, colour in NEW:
    p = Part.objects.filter(name=name).first()
    if not p:
        p = Part.objects.create(
            name=name, category=cat,
            description=f"3mm through-hole LED, {colour}"[:250],
            notes=("Absorbed from the SparkFun beginners parts kit when it was "
                   "dissolved on 2026-08-21. The kit list called its LEDs 5mm; "
                   "the survivors measured 3mm. Clear vs diffused not stated — "
                   "left blank rather than guessed."),
            default_location=drawer, active=True, component=True,
            purchaseable=True)
    s = StockItem.objects.filter(part=p, location=drawer).first()
    if not s:
        s = StockItem.objects.create(part=p, location=drawer, quantity=1)
    s.quantity = 1
    s.stocktake_date = today
    s.save()
    made.append((p.pk, name, s.pk))

for pk in (762, 764):
    p = Part.objects.get(pk=pk)
    if "Correction 2026-08-21" not in (p.notes or ""):
        p.notes = ((p.notes or "").rstrip() + CORRECTION).strip()
        p.save()

# ---- verify by re-read ----
print("\n=== verify ===")
fail = []


def chk(label, ok, detail=""):
    print(f'  {"ok  " if ok else "FAIL"} {label}' + (f"  ({detail})" if detail else ""))
    if not ok:
        fail.append(label)


s = StockItem.objects.filter(part_id=RED_3MM, location=drawer).first()
chk(f"#{RED_3MM} LED 3mm Red qty {before + 1}", s and int(s.quantity) == before + 1,
    f"qty={s.quantity if s else None}")
chk(f"#{RED_3MM} stocktake stamped", s and s.stocktake_date == today,
    f"{s.stocktake_date if s else None}")

for pk, name, spk in made:
    p = Part.objects.filter(pk=pk).first()
    s = StockItem.objects.filter(pk=spk).first()
    chk(f"#{pk} {name} exists, homed B3-R2C2",
        p is not None and p.default_location_id == DRAWER)
    chk(f"#{pk} qty 1, stocktake stamped",
        s is not None and int(s.quantity) == 1 and s.stocktake_date == today,
        f"qty={s.quantity if s else None} date={s.stocktake_date if s else None}")

for pk in (762, 764):
    p = Part.objects.get(pk=pk)
    chk(f"#{pk} carries the footprint correction",
        "Correction 2026-08-21" in (p.notes or ""))

print()
if fail:
    print(f"VERIFY FAILED on {len(fail)}: " + "; ".join(fail))
    sys.exit(1)
print("WROTE and verified")
