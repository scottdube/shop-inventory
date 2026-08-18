"""Two PCA9685-class products, each duplicated by the seed vs export imports.

Keepers are the rows carrying ASIN + SupplierPart + purchase history; the
hand-seeded twins fold into them, per the established non-destructive pattern.
Pack size from the seed row is preserved in the keeper's notes - it is the only
place that fact exists.
"""
import argparse, os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part
from stock.models import StockItem
from company.models import SupplierPart

# (fold, keep, why)
PAIRS = [
    (24, 344, "both are the Teyleten Robot PCA9685, ASIN B0CNVBWX2M"),
    (25, 367, "both are the 16-Channel 12-bit PWM Servo Driver, ASIN B00EIB0U7A"),
]

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

for fold_pk, keep_pk, why in PAIRS:
    f = Part.objects.filter(pk=fold_pk).first()
    k = Part.objects.filter(pk=keep_pk).first()
    if not f or not k:
        print(f"  #{fold_pk}->#{keep_pk}: missing")
        continue
    print(f"  fold #{f.pk} {f.name[:44]}")
    print(f"    -> #{k.pk} {k.name[:44]}")
    print(f"       {why}")
    if a.commit:
        StockItem.objects.filter(part=f).update(part=k)
        SupplierPart.objects.filter(part=f).update(part=k)
        extra = (f.description or "")
        k.notes = ((k.notes or "").rstrip() +
                   f"\n\nMerged with hand-seeded part #{f.pk} on 2026-08-17 — {why}."
                   f"\nSeed row recorded: {extra}").strip()
        k.save()
        f.active = False
        f.notes = ((f.notes or "").rstrip() +
                   f"\n\n**MERGED** into #{k.pk} {k.name} on 2026-08-17 — {why}.").strip()
        f.save()

print(f"\n{'WROTE' if a.commit else 'DRY RUN'}")
