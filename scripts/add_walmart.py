"""Create the Walmart Company record.

Scott confirmed 2026-08-24 that the two Walmart orders (Sterilite set of 10,
Akro-Mils 24-drawer cabinet) are shop purchases and should be known about.
vendor_triage.py correctly refused to create a PO for them because no Company
existed - an unknown vendor has nowhere to hang a PO. This removes that block.

Deliberately does NOT create POs or parts. The line items are still unverified:
Walmart is signed OUT in the agent's Chrome, so no order-details page can be
read, and the emails give only order totals ($10.98 / $99.98), never per-item
prices. Inventing a line price from an order total is the exact mistake the
Amazon rewards-points trap exists to prevent.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import Company  # noqa: E402

existing = Company.objects.filter(name__icontains="walmart").first()
if existing:
    print(f"SKIP (exists): #{existing.pk} {existing.name} supplier={existing.is_supplier}")
    sys.exit(0)

c = Company.objects.create(
    name="Walmart",
    description="Mixed-use retailer - shop storage and hardware alongside household goods. Classify per order.",
    website="https://www.walmart.com",
    is_supplier=True,
    is_customer=False,
    is_manufacturer=False,
)
fresh = Company.objects.get(pk=c.pk)
assert fresh.name == "Walmart", "company write did not stick"
print(f"+ created Company #{fresh.pk} {fresh.name} supplier={fresh.is_supplier}")
