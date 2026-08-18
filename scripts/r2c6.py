"""B3-R2C6: merge the duplicate level converters, then split 35 SLN / 13 LRD.

Also flags something visible in the photo that the counts do not capture: some
of these boards are POPULATED (MOSFETs and pull-ups fitted) and some are BARE
PCBs with only the silkscreen. A bare board is not a level converter, and once
they are mixed in a drawer they look identical from above.
"""
import argparse, os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model
from part.models import Part
from stock.models import StockItem, StockLocation
from company.models import SupplierPart

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

user = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
keep, fold = Part.objects.get(pk=20), Part.objects.get(pk=215)
drawer = StockLocation.objects.get(name="B3-R2C6")
lrd = StockLocation.objects.get(name="LRD")

print(f"  keep #{keep.pk} {keep.name}")
print(f"  fold #{fold.pk} {fold.name[:60]}")

if a.commit:
    StockItem.objects.filter(part=fold).update(part=keep)
    SupplierPart.objects.filter(part=fold).update(part=keep)
    fold.active = False
    fold.notes = ((fold.notes or "").rstrip() +
                  f"\n\n**MERGED** into #{keep.pk} on 2026-08-17 — both are the "
                  "Teyleten Robot 4-channel bi-directional level converter.").strip()
    fold.save()

    keep.notes = ((keep.notes or "").rstrip() + """

Merged with duplicate seed row #215 on 2026-08-17.

## ⚠ Populated vs bare boards — UNRESOLVED

The photo of this drawer shows **both populated boards** (MOSFETs and pull-up
resistors fitted) **and bare PCBs** carrying only the `Level Converter`
silkscreen. A bare board will not level-shift anything, and from above in a
drawer the two are almost indistinguishable.

The 35/13 counts below do NOT separate them. **Sort and re-count before relying
on this number**, and consider bagging or marking the bare ones separately.
Original pack was 50; 48 are accounted for.""").strip()
    keep.default_location = drawer
    keep.save()

    StockItem.objects.create(part=keep, location=drawer, quantity=35,
                             notes="Hand-counted 2026-08-17. Populated and bare "
                                   "boards NOT separated — see part notes.")
    StockItem.objects.create(part=keep, location=lrd, quantity=13,
                             notes="Carried to LRD 2026-08-17. Populated and bare "
                                   "boards NOT separated — see part notes.")

print()
for x in StockItem.objects.filter(part=keep):
    print(f"  qty {x.quantity:g} @ {x.location.pathstring if x.location else '-'}")
print(f"\n{'WROTE' if a.commit else 'DRY RUN'}")
