"""Stock check for the orb RC-reset bench test (hot-info-orbs sim/reset-rc).

Read-only. Searches by REQUIREMENT, not part number: every active part in a
resistor / capacitor / diode category, matched on value text across name and
description, plus every assortment kit in those categories (a kit can hold the
value without naming it). Prints every stock row with its site root, so the
LRD-vs-SLN answer is on the page.

Needed: 10k (R1), 1 uF (C2, ceramic preferred), 100 uF >= 6.3 V (C1),
and for the fix variant 10 uF + one small-signal / Schottky diode.

Usage:  itq run scripts/orb_reset_test_passives_1023.py
"""

import os
import re
import sys

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part  # noqa: E402

WANT = {
    "R 10k": (r"resist", r"(?<![\d.])10\s?k(?!\d)|10\s?k\s?ohm|10\s?kΩ|10000\s?ohm|\b103\b"),
    "C 1uF": (r"capac", r"(?<![\d.])1(\.0)?\s?[uµμ]f|\b105\b"),
    "C 10uF": (r"capac", r"(?<![\d.])10\s?[uµμ]f|\b106\b"),
    "C 100uF": (r"capac", r"(?<![\d.])100\s?[uµμ]f|\b107\b"),
    "diode": (r"diode", r"1n4148|1n914|bat54|bat85|bat43|1n581[79]|1n5711|small.?signal|schottky"),
}
KIT = re.compile(r"kit|assort|set of|book", re.I)


def site(loc):
    return loc.pathstring.split("/")[0] if loc else "(no location)"


def show(p):
    rows = list(p.stock_items.select_related("location").all())
    total = sum(float(s.quantity) for s in rows)
    print(f"  {p.name[:75]}  [part/{p.pk}]  total={total:g}")
    print(f"      cat={p.category.pathstring if p.category else '-'}")
    if p.description:
        print(f"      desc={p.description[:120]}")
    if not rows:
        print("      stock rows: NONE")
    for s in rows:
        loc = s.location.pathstring if s.location else "(no location)"
        print(f"      {site(s.location):5} {float(s.quantity):g} @ {loc}  [stock/{s.pk}]")


for label, (cat_re, val_re) in WANT.items():
    pool = Part.objects.filter(active=True, category__pathstring__iregex=cat_re)
    if label == "diode":
        pool = Part.objects.filter(active=True).filter(
            Q(category__pathstring__iregex=cat_re) | Q(name__iregex=val_re))
    rx = re.compile(val_re, re.I)
    hits = [p for p in pool.distinct().order_by("name")
            if rx.search(p.name or "") or rx.search(p.description or "")]
    kits = [p for p in pool.distinct().order_by("name")
            if p not in hits and KIT.search(p.name or "")]
    print(f"\n=== {label}: {len(hits)} value hit(s), {len(kits)} kit(s) "
          f"out of {pool.distinct().count()} active part(s) searched")
    for p in hits:
        show(p)
    if kits:
        print(f"  -- kits in the same categories (value not named) --")
        for p in kits:
            show(p)
