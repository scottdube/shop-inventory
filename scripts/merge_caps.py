"""Collapse three duplicate electrolytic pairs to one record each.

explode_kits.py created parallel parts because the SparkFun list carried no body
size while KIT15 did. Same value, same voltage, same physical shelf - one record.
Keep the sized name (size matters when it has to fit a board), retire the twin
with a pointer rather than deleting it.
"""
import argparse, os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part
from stock.models import StockItem

PAIRS = [(693, 676), (694, 680), (695, 686)]   # (retire, keep)

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

for dup_pk, keep_pk in PAIRS:
    dup = Part.objects.filter(pk=dup_pk).first()
    keep = Part.objects.filter(pk=keep_pk).first()
    if not dup or not keep:
        print(f"  #{dup_pk}/#{keep_pk}: missing, skipped")
        continue

    moved = StockItem.objects.filter(part=dup).count()
    print(f"  retire #{dup.pk} {dup.name}")
    print(f"    into #{keep.pk} {keep.name}   (stock items to move: {moved})")

    if a.commit:
        StockItem.objects.filter(part=dup).update(part=keep)
        keep.notes = ((keep.notes or "").rstrip() +
                      f"\n\nAlso supplied in the SparkFun Beginners Parts Kit "
                      f"(was separate part #{dup.pk}, merged 2026-08-17).").strip()
        keep.save()
        dup.active = False
        dup.notes = ((dup.notes or "").rstrip() +
                     f"\n\n**MERGED** into #{keep.pk} {keep.name} on 2026-08-17 — "
                     "same value and voltage, duplicate created by explode_kits "
                     "because the SparkFun list carried no body size.").strip()
        dup.save()

print(f"\n{'WROTE' if a.commit else 'DRY RUN'}")
