"""Queue C probe: Amazon order 113-9688006-8089017 (2026-09-13), 6 lines.

Read-only. Answers the two questions that must be settled BEFORE any part is
created: does an equivalent part already exist (by name, description, IPN or
supplier SKU), and which category does each belong in.

Tactile transducers / audio amp / speakon — this is sim-cockpit hardware, so
the plausible existing duplicates are anything already filed for the flight
sim. Search wide and print everything; a confident negative from a narrow
query is the failure mode here.
"""
import os
import sys

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import Company, SupplierPart  # noqa: E402
from part.models import Part, PartCategory  # noqa: E402

ITEMS = [
    ("B08LZW3RQL", "Dayton Audio TT25-8 Puck Tactile Transducer Mini Bass Shaker 8 Ohm 4 Pack",
     ["tactile", "transducer", "shaker", "TT25", "dayton"]),
    ("B004W4TYMA", "Behringer EUROPOWER EPQ304 300W 4-Channel Power Amplifier",
     ["amplifier", "behringer", "EPQ", "europower"]),
    ("B0CLXPRY45", "Sinus Live 16-18AWG OFC Speaker Wire 50FT",
     ["speaker wire", "OFC", "sinus"]),
    ("B07PHVMTNT", "Cable Matters 3.5mm TRS to Dual 6.35mm TS Breakout Cable 10ft",
     ["TRS", "6.35", "breakout cable", "3.5mm"]),
    ("B01CDDPJTI", "Dayton Audio BST-1 Tactile Bass Shaker 50W 4 Ohm",
     ["BST-1", "bass shaker", "tactile"]),
    ("B09231Q2WV", "bnafes NL4FC speakon Connector 4 Pole 2 PCS",
     ["speakon", "NL4", "NL2", "bnafes"]),
]

amazon = Company.objects.get(name="Amazon")
print(f"Amazon company pk={amazon.pk}\n")

for asin, label, terms in ITEMS:
    print("=" * 72)
    print(f"{asin}  {label}")
    sp = SupplierPart.objects.filter(SKU=asin)
    print(f"  SupplierPart SKU={asin}: {sp.count()}")
    for s in sp:
        print(f"    sp#{s.pk} supplier={s.supplier.name} -> part #{s.part.pk} "
              f"{s.part.name} active={s.part.active}")
    hits = Part.objects.none()
    for t in terms:
        hits = hits | Part.objects.filter(
            Q(name__icontains=t) | Q(description__icontains=t)
            | Q(keywords__icontains=t) | Q(IPN__icontains=t))
    hits = hits.distinct()
    print(f"  name/desc/keyword/IPN hits: {hits.count()}")
    for p in hits:
        print(f"    #{p.pk} [{'A' if p.active else 'x'}] {p.name}  "
              f"| cat={p.category.pathstring if p.category else None}")

print()
print("=" * 72)
print("CANDIDATE CATEGORIES")
for t in ["audio", "electronic", "cable", "wire", "connector", "hardware",
          "sim", "flight"]:
    for c in PartCategory.objects.filter(name__icontains=t):
        print(f"  pk={c.pk:4d}  {c.pathstring}  (parts={c.parts.count()})")
