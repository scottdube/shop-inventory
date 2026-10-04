"""Read-only, 02:05 run 2026-10-04: Bambu Lab supplier-part links for the
imageless parts #1269-#1316, and any Bambu part that already has an image."""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import SupplierPart  # noqa: E402

for sp in (SupplierPart.objects.filter(supplier__name="Bambu Lab")
           .select_related("part").order_by("part_id")):
    p = sp.part
    print(f"#{p.pk} img={'Y' if p.image else 'N'} sp#{sp.pk} {sp.SKU} | {sp.link} "
          f"| {(p.description or '')[:90]}")
