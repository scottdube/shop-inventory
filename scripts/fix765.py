"""Real identification for the battery contacts, now the label has been read.

Critical detail: the pack is 10 PAIRS, not 10 pieces. A pair is one sprung
negative contact plus one flat positive plate - one cell position. The stock
quantity of 10 is therefore correct ONLY if the unit is stated, or someone
later reads it as 10 individual contacts and is off by half.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part
from stock.models import StockItem
from company.models import Company, SupplierPart

p = Part.objects.get(pk=765)
p.name = "Airhso Battery Spring Contact Plate (pair)"[:100]
p.description = ("Battery contact PAIR - one sprung negative + one flat positive. "
                 "One pair = one cell position")[:250]
p.IPN = "X004T1PV1F"
p.notes = """Battery contact set for AA-size cells.

**UNIT IS A PAIR** — one sprung negative contact plus one flat positive plate,
i.e. one cell position. Stock of 10 means **10 pairs / 20 individual pieces**.
Do not read the quantity as 10 contacts.

| | |
|---|---|
| brand | Airhso |
| pack | **10 pairs** |
| ASIN | X004T1PV1F |
| label | `727728_1-62-200`, size begins `12x1…` (truncated on the label) |
| origin | Made in China |

Package **unopened** as of 2026-08-17, so all 10 pairs are present."""
p.save()

amz = Company.objects.filter(name__iexact="Amazon").first()
if amz:
    sp, created = SupplierPart.objects.get_or_create(
        part=p, supplier=amz, SKU="X004T1PV1F",
        defaults={"note": "Airhso, sold as 10 pairs", "pack_quantity": "10"})
    print(f"supplierpart: {'created' if created else 'exists'} Amazon X004T1PV1F")

for si in StockItem.objects.filter(part=p):
    si.notes = ("Unopened pack, 2026-08-17. Quantity is **10 PAIRS** "
                "(20 individual contacts).")
    si.save()

print(f"\n#{p.pk} {p.name}")
print(p.description)
