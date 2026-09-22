"""Queue B probe 3 — dedup check for the 4 orders that really ARE un-imported.

Probe 2 established the task file has queue B backwards: 3000048956/3000053997/
225102790 are already PO-0026/0025/0027, while the three orders the file calls
"imported" (3000070065, 3000069852, 3000069522) and MSC 251613620 have no PO at
all. These are their line SKUs.

Checks BOTH directions per the dedup rule — the SKU token across name /
description / IPN / keywords / SupplierPart.SKU, AND the requirement in plain
words, because a canonicalized part name never matches a vendor title and a
part bought elsewhere (microARC, coolant nozzles, end mills) will only be found
by the word probe.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import SupplierPart  # noqa: E402
from order.models import PurchaseOrder  # noqa: E402
from part.models import Part  # noqa: E402

SKUS = {
    "38412": "microARC 4 - 100 mm 4th Axis",
    "52643": "microARC 4 Subplate",
    "38954": "4th Axis Driver and Installation Kit (M/MX)",
    "34697": '1/2 in. x 1-1/4 in. x 1/2 in. Thread Mill',
    "34696": '3/8 in. x 1 in. x 3/8 in. Thread Mill',
    "34695": '5/16 x 3/4 in. x 5/16 in. Thread Mill',
    "35724": "4 Inch Length Coolant Nozzle for Turret 10-Pack",
    "32624": "Aluminum Fixture Plate, 20 in. x 9.5 in. x 10 mm",
    "53400": "Tormach Branded T-shirt Green (EXCLUDED, rule 7)",
    "89629687": "210GPH TRANSPARENT OIL SKIMMER",
    "82976713": "1/2X1/2X2X4 ZIR 3FL CARB HP 40D CC SEM",
}

print("=== PO idempotency (the 4 to create) ===")
for o in ("3000069522", "3000069852", "3000070065", "251613620"):
    hits = list(PurchaseOrder.objects.filter(supplier_reference=o))
    print(f"{'EXISTS' if hits else 'absent':7s} {o}"
          + (f" -> {[p.reference for p in hits]}" if hits else ""))

print("\n=== SKU token ===")
for sku, desc in SKUS.items():
    print(f"\n-- {sku}  {desc}")
    found = False
    for sp in SupplierPart.objects.filter(SKU__icontains=sku):
        found = True
        print(f"   SupplierPart pk={sp.pk} SKU={sp.SKU!r} supplier={sp.supplier.name} "
              f"part=#{sp.part.pk} {sp.part.name!r} pack={sp.pack_quantity!r}")
    q = (Part.objects.filter(name__icontains=sku)
         | Part.objects.filter(description__icontains=sku)
         | Part.objects.filter(IPN__icontains=sku)
         | Part.objects.filter(keywords__icontains=sku)).distinct()
    for p in q:
        found = True
        print(f"   Part #{p.pk} {p.name!r} active={p.active} cat={p.category}")
    if not found:
        print("   (nothing carries this SKU)")

print("\n=== the requirement in plain words ===")
TERMS = ["microarc", "4th axis", "thread mill", "coolant nozzle", "nozzle",
         "fixture plate", "oil skimmer", "skimmer", "t-shirt", "subplate",
         "3 flute", "3fl", "zrn"]
for term in TERMS:
    hits = (Part.objects.filter(name__icontains=term)
            | Part.objects.filter(description__icontains=term)
            | Part.objects.filter(keywords__icontains=term)).distinct()
    print(f"\n-- {term!r}: {hits.count()}")
    for p in hits[:15]:
        print(f"   #{p.pk} {p.name!r} active={p.active} cat={p.category} "
              f"stock={p.total_stock}")

print("\n=== categories that may be the home for these ===")
from part.models import PartCategory  # noqa: E402
for term in ("Tooling", "Equipment", "Cutting Tools", "Workholding", "Machine",
             "Coolant", "CNC"):
    for c in PartCategory.objects.filter(name__icontains=term):
        print(f"pk={c.pk:4d} {c.pathstring!r} parts={c.parts.count()}")
