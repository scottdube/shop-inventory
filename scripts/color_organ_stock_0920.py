"""Stock check for the color-organ first build: 12 V supply and 1 W ballast resistors.

Searches the REQUIREMENT, not a chosen part number -- a 12 V 2 A brick may be
catalogued as an adapter, a PSU, a wall wart or by its barrel size, and the
ballast resistors only have to land in a range, not on a value. Prints the
whole result set with active flag and stock so nothing is concluded from a
truncated list.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part                                    # noqa: E402

BASE = "http://192.168.50.10:8001/web/part/%d/"


def show(title, qs, note=""):
    qs = list(qs.distinct().order_by("name"))
    print("\n" + "=" * 78)
    print(f"{title}   -- {len(qs)} row(s){note}")
    print("=" * 78)
    if not qs:
        print("   (no rows)")
        return
    for p in qs:
        try:
            stock = p.total_stock
        except Exception:
            stock = "?"
        flag = "" if p.active else "  [INACTIVE - merge receipt, not a live part]"
        cat = p.category.pathstring if p.category else "-"
        print(f"  {p.name}")
        print(f"      stock={stock}  cat={cat}{flag}")
        print(f"      {BASE % p.pk}")


# ---- 1. the 12 V supply -------------------------------------------------
supply_terms = ["power supply", "psu", "adapter", "adaptor", "wall wart",
                "wallwart", "brick", "power brick", "dc supply", "smps"]
q = Part.objects.none()
for t in supply_terms:
    q = q | Part.objects.filter(name__icontains=t) | Part.objects.filter(description__icontains=t)
show("SUPPLY -- anything shaped like an external DC supply", q)

# Narrower: anything mentioning 12 V at all, in case it is named by voltage
q12 = (Part.objects.filter(name__icontains="12v") |
       Part.objects.filter(name__icontains="12 v") |
       Part.objects.filter(description__icontains="12v") |
       Part.objects.filter(description__icontains="12 v"))
show("SUPPLY -- anything mentioning 12 V", q12)

# ---- 2. the ballast resistors -------------------------------------------
qr = (Part.objects.filter(name__icontains="resistor") |
      Part.objects.filter(description__icontains="resistor"))
qr = qr.distinct()
print("\n" + "=" * 78)
print(f"RESISTORS -- {qr.count()} part(s) total in the catalogue")
print("=" * 78)
for p in qr.order_by("name"):
    try:
        stock = p.total_stock
    except Exception:
        stock = "?"
    flag = "" if p.active else "  [INACTIVE]"
    print(f"  {p.name}   stock={stock}{flag}   {BASE % p.pk}")

print("\nDONE -- every row above is printed in full; nothing was capped.")
