"""Duplicate + category probe for the 2026-09-10 22:40 sweep.

One new order in the window: Amazon 113-8888047-4781028, a VSDISPLAY 12.6"
1920x515 IPS bar monitor, ASIN B0C3CSW624.

Read-only. Searches name / description / IPN / keywords and supplier
SKU+description+note+MPN, then dumps the display-ish categories and any
existing parts that are actual DISPLAYS, so the new part lands next to its
siblings rather than in a tidier-looking empty branch.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.db.models import Q  # noqa: E402
from part.models import Part, PartCategory  # noqa: E402
from company.models import SupplierPart  # noqa: E402

TERMS = [
    "B0C3CSW624", "VSDISPLAY", "1920x515", "1920 x 515", "12.6", "bar monitor",
    "stretched", "ultrawide", "second display", "secondary display", "IPS",
    "LCD screen", "LCD monitor", "monitor", "display panel", "HDMI display",
    "screen", "panel", "eDP", "LVDS", "driver board", "backlight",
]

print("=" * 72)
print("PART SEARCH — name / description / IPN / keywords")
for t in TERMS:
    q = (Q(name__icontains=t) | Q(description__icontains=t)
         | Q(IPN__icontains=t) | Q(keywords__icontains=t))
    hits = Part.objects.filter(q)
    print(f"\n  {t!r}: {hits.count()} hit(s)")
    for p in hits[:12]:
        cat = p.category.pathstring if p.category else "(none)"
        print(f"      #{p.pk:<5} active={p.active!s:<5} {p.name[:58]:<58} cat={cat}")

print("=" * 72)
print("SUPPLIERPART SEARCH — SKU / description / note / MPN")
for t in TERMS:
    q = (Q(SKU__icontains=t) | Q(description__icontains=t)
         | Q(note__icontains=t) | Q(manufacturer_part__MPN__icontains=t))
    hits = SupplierPart.objects.filter(q)
    if not hits.exists():
        continue
    print(f"\n  {t!r}: {hits.count()} hit(s)")
    for sp in hits[:12]:
        print(f"      sp{sp.pk:<5} {sp.supplier.name[:18]:<18} SKU={sp.SKU[:18]:<18} "
              f"-> #{sp.part_id} {sp.part.name[:40]}")

print("=" * 72)
print("CANDIDATE CATEGORIES (anything display/video/module shaped)")
for c in PartCategory.objects.all().order_by("pathstring"):
    low = c.pathstring.lower()
    if any(k in low for k in ("display", "video", "screen", "module", "electronic")):
        n = Part.objects.filter(category=c).count()
        print(f"  #{c.pk:<5} {c.pathstring:<52} parts={n}")

print("=" * 72)
print("EXISTING PARTS THAT ARE ACTUAL DISPLAYS (name match)")
disp = Part.objects.filter(
    Q(name__icontains="display") | Q(name__icontains="lcd")
    | Q(name__icontains="oled") | Q(name__icontains="screen")
    | Q(name__icontains="tft") | Q(name__icontains="monitor")
).order_by("pk")
for p in disp:
    cat = p.category.pathstring if p.category else "(none)"
    print(f"  #{p.pk:<5} active={p.active!s:<5} {p.name[:56]:<56} cat={cat}")
print(f"  ({disp.count()} total — NOT truncated)")
