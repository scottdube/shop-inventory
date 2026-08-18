"""Attach the recovered eBay purchase to the 2x5x7mm white LED.

Scott remembered buying these for the simulator audio panels and said there
should be an email; there was. Price is recorded per DEVICE per the house
convention (order/models.py:1195), shipping noted separately rather than
smeared into unit cost.
"""
import argparse, os, sys, django
from decimal import Decimal
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part
from company.models import Company, SupplierPart

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

p = Part.objects.get(pk=760)
ebay = Company.objects.filter(name__iexact="eBay").first()
print(f"part:     #{p.pk} {p.name}")
print(f"supplier: {ebay.name if ebay else 'eBay (WILL CREATE)'}")

SKU = "221473038845"
if a.commit:
    if not ebay:
        ebay = Company.objects.create(name="eBay", is_supplier=True,
                                      description="Marketplace - real seller recorded per SupplierPart")
    sp, created = SupplierPart.objects.get_or_create(
        part=p, supplier=ebay, SKU=SKU,
        defaults={"note": "seller colorfulplace888 (Shenzhen) - 100 pcs pack",
                  "pack_quantity": "100"})
    print(f"supplierpart: {'created' if created else 'exists'} SKU={SKU}")
    p.notes = (p.notes.rstrip() + """

## Purchase (recovered from email 2026-08-17)

| | |
|---|---|
| eBay item | 221473038845 |
| order | 12-11712-91342 |
| seller | colorfulplace888, Shenzhen |
| ordered | 2024-06-19 |
| delivered | 2024-06-27 |
| item price | $5.50 for 100 |
| shipping | $2.00 |
| **total** | **$7.50** |
| unit | **$0.055** per LED (item price / 100) |

**75 of 100 remain** as of 2026-08-17, so **25 went into the simulator audio
panels** - consumption evidenced by pack size minus count, not recalled.""")
    p.save()

print(f"\n{'WROTE' if a.commit else 'DRY RUN'}")
