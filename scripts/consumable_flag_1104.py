"""Set Part.consumable on the parts Scott approved 2026-11-04 ("Yes, as drafted") from
docs/consumable-flag-draft.md: section 1 (90) + group A wear parts (11) + group C wire (6)
+ the soldering practice kit from group D (1) = 108. NOT group B (build parts / fasteners)
and NOT the applicator bottle.

Writes with queryset .update(): a plain boolean with no derived fields, and Part.save()
runs full validation that can refuse an unrelated stale field. Every row is re-read after.
Dry run by default.  itq run scripts/consumable_flag_1104.py [--commit]"""
import os, sys
sys.path.insert(0, os.getcwd()); os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
import django; django.setup()
from part.models import Part

YES = [480,278,305,1107,452,451,174,266,88,148,471,            # solder, flux, paste, wick
       437,450,202,468,504,505,506,507,508,                     # heat-shrink tubing
       89,390,1254,1146,1147,                                   # tape
       848,1109,1110,1111,1112,1113,589,1274,1278,              # adhesives, sealants, glue
       1116,1115,                                               # glue-up disposables
       551,253,557,301,                                         # oils, coolant, cutting fluid
       279,212,347,170,188,230,                                 # abrasives
       922,923,1069,849,850,851,                                # labels and bags
       432,1489,493]                                            # cleaning, solder mask
FILAMENT_CAT = "Shop/Consumables/Filament"; FILAMENT_N = 35
A_WEAR = [854,160,333,1108,87,213,1084,121,433,482,467]
C_WIRE = [342,49,48,1194,1167,948]
D_KIT = [1096]
NOT = [852,855,856,857,858,859,860,861,862,863,864,865,866,435,186,368,181,441,137,345,385,431,346,847,1114]

fil = [p.pk for p in Part.objects.filter(active=True) if p.category and p.category.pathstring == FILAMENT_CAT]
assert len(fil) == FILAMENT_N, f"filament count moved: {len(fil)} != {FILAMENT_N}"
pks = YES + fil + A_WEAR + C_WIRE + D_KIT
assert len(pks) == len(set(pks)) == 108, (len(pks), len(set(pks)))
assert not set(pks) & set(NOT)
parts = Part.objects.in_bulk(pks)
assert len(parts) == 108, f"missing pks: {sorted(set(pks) - set(parts))}"
already = [p for p in parts.values() if p.consumable]
print(f"{len(parts)} parts, {len(already)} already flagged; total flagged on the instance now:",
      Part.objects.filter(consumable=True).count())
for pk in pks:
    p = parts[pk]; print(f"  {pk:5} {'*' if p.consumable else ' '} {p.name[:80]}")
if "--commit" not in sys.argv:
    print("DRY RUN - nothing written"); sys.exit(0)
n = Part.objects.filter(pk__in=pks, consumable=False).update(consumable=True)
print("updated:", n)
bad = [pk for pk, c in Part.objects.filter(pk__in=pks).values_list("pk", "consumable") if not c]
stray = Part.objects.filter(consumable=True).exclude(pk__in=pks).count()
print("re-read: not flagged", bad, "| flagged outside the list:", stray,
      "| total flagged:", Part.objects.filter(consumable=True).count())
print("VERDICT:", "SUCCESS" if not bad and stray == 0 else "FAILED")
