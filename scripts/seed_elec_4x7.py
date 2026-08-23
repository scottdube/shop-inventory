"""Seed the 10-value 4x7 electrolytic kit from a HAND COUNT, 2026-08-23.

Scott counted all ten bags at the drawer. These are real counts, so every row
gets a `stocktake_date` -- that is the whole basis of the rolling bin check
later, where the staleness of a count only means something if the fresh ones
are marked.

Two things the physical bags settled that the printed lid got wrong, and the
bags win -- the SparkFun kit taught this expensively, where every single error
came from trusting the list over the object:

  * The lid lists 22uF 16V. There is no 16V bag. There are TWO bags of
    22uF 25V, 8 and 10. Part #736 (22uF 16V, 4x7) is therefore NOT in this
    box; it stays in the catalogue at zero stock because it may belong to one
    of the other two electrolytic kits.
  * So the kit holds NINE distinct values, not ten. "10value" on the lid
    counts bags.

The two 22uF bags are filed as ONE row of 18 rather than two rows of 8 and 10:
same part, same location, and a recount picks up both bags in the same motion.
The bag split lives in the note so nothing is lost.

Idempotent -- a value that already has stock at this location is skipped, not
added to. Every write is re-read and verified, because `.save()` on this
install has reported success and written nothing.

    itq run scripts/seed_elec_4x7.py            # dry run
    itq run scripts/seed_elec_4x7.py --commit
"""
import argparse, os, sys, django
from datetime import date
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model
from part.models import Part
from stock.models import StockLocation, StockItem

KIT = "Kit - 10-Value Electrolytic 4x7"
TODAY = date.today().isoformat()

# (part pk, name fragment that MUST match, counted qty, extra note)
# The name fragment is a guard: a bare pk list is one renumbering away from
# seeding the wrong capacitor, and these values differ by one character.
COUNTS = [
    (673, "0.1uF 50V",  9,  ""),
    (676, "1uF 50V",    9,  ""),
    (677, "2.2uF 50V",  10, ""),
    (678, "3.3uF 50V",  10, ""),
    (679, "4.7uF 50V",  10, ""),
    (680, "10uF 25V",   10, ""),
    (681, "22uF 25V",   18, "TWO bags, 8 + 10. The lid claims a 22uF 16V "
                            "value; there is no 16V bag in this box."),
    (737, "47uF 10V",   10, ""),
    (685, "100uF 10V",  9,  ""),
]

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

loc = StockLocation.objects.filter(name=KIT).first()
if not loc:
    sys.exit(f"no such location: {KIT}")
print(f"location: {loc.pathstring}")
print(f"counted by Scott at the drawer, {TODAY}\n")

user = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()

wrote = skipped = failed = 0
total = 0
for pk, frag, qty, extra in COUNTS:
    p = Part.objects.filter(pk=pk).first()
    if not p:
        print(f"  #{pk}: NO SUCH PART - skipping")
        failed += 1
        continue
    if frag.lower() not in (p.name or "").lower():
        print(f"  #{pk}: name guard FAILED - expected {frag!r} in {p.name!r}")
        failed += 1
        continue

    existing = StockItem.objects.filter(part=p, location=loc).first()
    if existing:
        print(f"  #{pk} {p.name[:44]:<46} already here ({existing.quantity:g}) - skipped")
        skipped += 1
        total += float(existing.quantity)
        continue

    total += qty
    print(f"  #{pk} {p.name[:44]:<46} qty {qty}" + (f"  [{extra[:40]}...]" if extra else ""))
    if not a.commit:
        continue

    note = (f"Hand-counted {TODAY} by Scott at drawer A3-R8C5. Kept in its own "
            f"bag inside the kit so a recount needs no sorting.")
    if extra:
        note += " " + extra
    si = StockItem.objects.create(part=p, location=loc, quantity=qty, notes=note)
    si.stocktake_date = date.today()
    si.stocktake_user = user
    si.save()

    # Re-read. A create that reports success and stores nothing is the failure
    # this repo has already been bitten by.
    again = StockItem.objects.filter(pk=si.pk).first()
    ok = (again is not None
          and float(again.quantity) == float(qty)
          and again.location_id == loc.pk
          and again.stocktake_date is not None)
    if not ok:
        print(f"       WRITE DID NOT VERIFY: {again and again.quantity!r} "
              f"loc={again and again.location_id} st={again and again.stocktake_date}")
        failed += 1
        continue
    wrote += 1

    # The kit bag is where a spare of this value goes home.
    if p.default_location_id != loc.pk:
        Part.objects.filter(pk=p.pk).update(default_location=loc)
        if Part.objects.get(pk=p.pk).default_location_id != loc.pk:
            print(f"       default_location did not stick for #{p.pk}")

print(f"\n{'WROTE' if a.commit else 'DRY RUN'}: "
      f"{wrote} written, {skipped} already present, {failed} failed")
print(f"kit total: {total:g} capacitors across {len(COUNTS)} values")
sys.exit(1 if failed else 0)
