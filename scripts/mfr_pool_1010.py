#!/usr/bin/env python3
"""2026-10-10 queue A new instrument: the 10-07 pool measurement grouped
imageless parts by SupplierPart and Part.link only. This asks the third
place a vendor handle can live - ManufacturerPart (MPN + manufacturer link) -
and then the fourth: an IPN that is itself a vendor identifier (Adafruit PID,
Amazon ASIN, maker part number). Found 0 ManufacturerPart rows and 9 IPN rows
on 2026-10-10; 6 of the 9 produced images (img_1010.py). Read-only.
Run from ~/code: scripts/itq run scripts/mfr_pool_1010.py"""
import os
import sys
from collections import defaultdict

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part  # noqa: E402
from company.models import SupplierPart, ManufacturerPart  # noqa: E402

missing = Part.objects.filter(active=True, image='').order_by('pk')
print(f"active, no image: {missing.count()}")

no_handle = []
by_mfr = defaultdict(list)
for p in missing:
    has_sp = SupplierPart.objects.filter(part=p).exists()
    mps = list(ManufacturerPart.objects.filter(part=p).select_related('manufacturer'))
    if has_sp or p.link:
        continue  # already in the 10-07 pool accounting
    if mps:
        for mp in mps:
            by_mfr[mp.manufacturer.name if mp.manufacturer else '?'].append((p, mp))
    else:
        no_handle.append(p)

print(f"no SP, no link, no ManufacturerPart: {len(no_handle)}")
print(f"no SP, no link, but HAVE a ManufacturerPart: {sum(len(v) for v in by_mfr.values())}")
for m in sorted(by_mfr, key=lambda k: -len(by_mfr[k])):
    print(f"\n== {m} ({len(by_mfr[m])})")
    for p, mp in by_mfr[m][:40]:
        print(f"  [{p.pk}] MPN={mp.MPN}  link={(mp.link or '-')[:70]}\n        {p.name[:70]}")

# IPN as a handle: parts whose IPN looks like a catalogue number
ipn = [p for p in no_handle if (p.IPN or '').strip()]
print(f"\nno-handle parts that carry an IPN: {len(ipn)}")
for p in ipn[:40]:
    print(f"  [{p.pk}] IPN={p.IPN}  cat={p.category.name if p.category else '-'}  {p.name[:60]}")
