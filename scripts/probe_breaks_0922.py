"""Is a missing SupplierPriceBreak an anomaly or the house norm?

Probe 4 found MSC SupplierParts 29/30 carry no price break while all eight
Tormach ones from the same cost-mining pass do. Before "fixing" that, measure
whether breaks are the norm on this instance at all — a convention nobody
follows is not a defect in two rows.

Read-only. Prints, per supplier, how many of its supplier parts carry at least
one price break.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import Company, SupplierPart, SupplierPriceBreak  # noqa: E402

with_break = set(SupplierPriceBreak.objects.values_list("part_id", flat=True))
total = SupplierPart.objects.count()
print(f"supplier parts: {total}   carrying >=1 price break: {len(with_break)} "
      f"({100.0 * len(with_break) / total:.1f}%)\n")

rows = []
for c in Company.objects.filter(is_supplier=True):
    sps = list(SupplierPart.objects.filter(supplier=c).values_list("pk", flat=True))
    if not sps:
        continue
    have = sum(1 for pk in sps if pk in with_break)
    rows.append((len(sps), have, c.name))
for n, have, name in sorted(rows, reverse=True):
    flag = "" if have == n else ("   <-- none" if have == 0 else "   <-- partial")
    print(f"{n:5d} parts  {have:5d} priced  {name[:44]}{flag}")

print("\n--- MSC detail ---")
for sp in SupplierPart.objects.filter(supplier__name__icontains="MSC"):
    brk = list(SupplierPriceBreak.objects.filter(part=sp))
    print(f"sp={sp.pk} SKU={sp.SKU!r} part=#{sp.part.pk} {sp.part.name[:40]!r} "
          f"breaks={[(str(b.quantity), str(b.price)) for b in brk] or 'NONE'}")
