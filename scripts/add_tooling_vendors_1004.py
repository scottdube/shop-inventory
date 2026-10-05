"""Create Company records for the tooling vendors the 2026-10-04 email sweep found.

Scott, 2026-10-04: inventory every machine tool bought, "search email for
indications of others". That request is the approval vendor_triage.py waits
for: these two have whole, itemised order confirmations in email, so they get
a Company and their orders go through hist_import.py like every other vendor.

LittleMachineShop was held back on the first run: order 22010514's emails carry
an unfilled %OrderDetails% template, so there were no lines to hang a PO on.
Added 2026-10-05 once Scott sent a screenshot of the order page from his
LittleMachineShop account.

    itq run scripts/add_tooling_vendors_1004.py [--commit]
"""
import argparse
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import Company  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

VENDORS = [
    ("Saunders Machine Works", r"saunders",
     "Workholding for Tormach-class mills - Mod Vise, soft jaws, fixture plates.",
     "https://saundersmachineworks.com"),
    ("Zoro", r"^zoro",
     "Industrial supply (Grainger-owned). Mixed shop supplies; classify per order.",
     "https://www.zoro.com"),
    ("LittleMachineShop", r"little ?machine",
     "Mini-mill/lathe accessories, measuring and layout tools (Pasadena CA).",
     "https://www.littlemachineshop.com"),
]

for name, rx, desc, web in VENDORS:
    hit = Company.objects.filter(name__iregex=rx).first()
    if hit:
        print(f"SKIP (exists): #{hit.pk} {hit.name} supplier={hit.is_supplier}")
        continue
    print(f"+ would create {name}")
    if not a.commit:
        continue
    c = Company.objects.create(name=name, description=desc, website=web,
                               is_supplier=True, is_customer=False, is_manufacturer=False)
    fresh = Company.objects.get(pk=c.pk)
    assert fresh.name == name and fresh.is_supplier
    print(f"  created Company #{fresh.pk} {fresh.name}")

print("COMMITTED" if a.commit else "DRY RUN - add --commit")
