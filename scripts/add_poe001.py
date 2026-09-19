#!/usr/bin/env python3
"""Catalogue POE-001, the active PoE splitter, into bin B-02.

The 2026-09-19 salvage triage filed three wall-warts into B-02 (#1217-#1219)
and left the two PoE splitters documented in sln-ha-config but not catalogued.
This adds the one that is fully identified. POE-002 -- the white "Data+Power"
unit -- deliberately stays OUT until its label is photographed: it is either
active or passive and those fail in opposite directions, so a record now would
be a guess written down as a fact.

Category is Electronics/Power, mirroring the three bricks, NOT a networking
category. The part is a power-delivery device that happens to arrive over
Ethernet; filing it with the supplies is what makes "what can power this?"
answerable from one shelf. Electronics/Power/AC-DC Modules and .../Converters
were both rejected -- this is neither, it is a PD.

    itq run scripts/add_poe001.py
    itq run scripts/add_poe001.py --commit
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part, PartCategory  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

COMMIT = "--commit" in sys.argv

CATEGORY_PK = 54          # Electronics/Power
BIN_PK = 617              # SLN/Storage/WS2/WS2-S3/B-02

NAME = "POE-001 PoE Splitter 802.3af/at, 5V 2.4A USB-C"
DESC = ("Active PoE splitter. RJ45 in, gigabit data out + 5V 2.4A on USB-C. "
        "IEEE 802.3af/at, galvanically isolated. Black. Reads LS-POE-0525LK, "
        "S/N 20190108001. Runs straight off the SLN USW PoE ports.")
KEYWORDS = ("POE-001 LS-POE-0525LK PoE splitter 802.3af 802.3at active gigabit "
            "isolated 5V 2.4A USB-C ethernet power")
NOTES = """Active PoE splitter, everything below read off the unit's own label:

    LS-POE-0525LK
    IEEE 802.3af/at        (active - negotiates with the PSE)
    千兆隔离型              (gigabit, galvanically isolated)
    OUTPUT 5V 2.4A, USB-C
    CE FC RoHS, QC passed, S/N 20190108001

**ACTIVE, WHICH IS THE FIELD THAT MATTERS.** SLN runs 802.3af/at switch
infrastructure (USW Lite 16 PoE, USW 24 PoE - SLN ADR-002), so this works
directly off any PoE port with no injector. A PASSIVE splitter on those same
ports most likely gets nothing at all, because the switch will not energize a
port that does not negotiate. Do not treat the two as interchangeable.

Three things put it above the usual budget splitter: active, gigabit (most
cheap splitters cap the link at 100 Mbit), and isolated (no ground loop between
switch and powered device).

**NOT FOR THE LAB-WALL PI 4** (sln-ha-config docs/lab-wall-pi-runbook.md, SLN
ADR-014). A Pi 4 wants 5V/3A and this delivers 2.4A; Pi 4 undervoltage does not
degrade gracefully - CPU throttling, USB ports dropping, random reboots. There
is also little headroom against the 802.3af PD budget (12.95 W) once splitter
losses are counted. For PoE on that Pi the right part is an 802.3AT splitter
rated 5V/4A, or a PoE+ HAT. Good fits here: ESP32 nodes, a Pi Zero 2 W, a
camera.

**NO PURCHASE RECORD.** An Amazon order (#111-5444316-5430637, 13 Apr 2025,
qty 2, "Gigabit PoE to USB C Converter ... IEEE802.3af") was matched to this
unit and then RETRACTED - it described a different product, and the "two of
these" and an LRD siting came from the same bad match. The match rested on
product category alone; no model number in the listing matched LS-POE-0525LK,
and the tell was already transcribed above: S/N 20190108001 is a 2019 date, six
years before that order. An order record identifies a device when a model
number, serial or photograph ties it - not when the category matches.

**POE-002 is its sibling and is NOT this part.** White "Data+Power" splitter,
RJ45 in to RJ45 + female barrel, no IEEE marking visible in the 2026-09-19
photo. Probably passive, but that is inference from appearance and it has no
record until the label is photographed. Store the two apart - they read as the
same class of accessory and are not.

Full write-up: sln-ha-config docs/reference/power-supply-inventory.md section 8."""

QTY = 1     # one unit, in hand, seen in the 2026-09-19 photo


def check_limits():
    lim = {"name": (NAME, 100), "description": (DESC, 250),
           "keywords": (KEYWORDS, 250)}
    bad = [f"{f}: {len(v)} > {n}" for f, (v, n) in lim.items() if len(v) > n]
    if bad:
        print("FIELD TOO LONG — Part.save() calls full_clean(), this would abort:")
        for b in bad:
            print("   ", b)
        sys.exit(1)
    for f, (v, n) in lim.items():
        print(f"   {f:12s} {len(v):3d}/{n}")


cat = PartCategory.objects.get(pk=CATEGORY_PK)
loc = StockLocation.objects.get(pk=BIN_PK)
print(f"category: {cat.pathstring}")
print(f"bin:      {loc.pathstring}")
check_limits()

existing = Part.objects.filter(name__startswith="POE-001 ").first()
print(f"part:     {'EXISTS #%d' % existing.pk if existing else 'will create'}")

if not COMMIT:
    print("\nDRY RUN — nothing written. Re-run with --commit.")
    sys.exit(0)

if existing is None:
    p = Part.objects.create(
        name=NAME, description=DESC, category=cat, keywords=KEYWORDS,
        notes=NOTES, default_location=loc,
        active=True, purchaseable=True, component=True)
else:
    p = existing
    # .save() has silently written nothing on this install; go through the
    # queryset, then re-read.
    Part.objects.filter(pk=p.pk).update(
        name=NAME, description=DESC, category=cat, keywords=KEYWORDS,
        notes=NOTES, default_location=loc)

p.refresh_from_db()

si = StockItem.objects.filter(part=p, location=loc).first()
if si is None:
    si = StockItem.objects.create(part=p, location=loc, quantity=QTY)
si.refresh_from_db()

print(f"\n#{p.pk} {p.name}")
print(f"    category         {p.category.pathstring}")
print(f"    default_location {p.default_location.pathstring}")
print(f"    active-vs-passive note present: {'ACTIVE, WHICH IS THE FIELD' in p.notes}")
print(f"    Pi 4 exclusion present:         {'NOT FOR THE LAB-WALL PI 4' in p.notes}")
print(f"    stock [{si.pk}] qty {si.quantity:g} @ {si.location.pathstring}")
