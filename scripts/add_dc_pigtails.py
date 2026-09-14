#!/usr/bin/env python3
"""Catalogue the male and female 5.5 x 2.1 mm DC barrel pigtails.

Wire-shelf stock-in, 2026-09-14. Neither ASIN was in InvenTree and there was
no DC barrel pigtail part of any kind -- a gap worth noting, since a barrel
pigtail is the single most-reached-for way to get 12 V into a prototype.

TWO PARTS, NOT ONE. Male and female do not substitute for each other; a
drawer holding "DC pigtails" that turns out to be all one gender is worse than
an empty drawer, because you plan around it. Same size, opposite ends,
separate rows.

Barrel size 5.5 x 2.1 mm. Printed on the MALE bag only; the female label says
just "Female DC Pigtail Cables". Scott confirmed the match verbally -- "syes
same size" -- so it is recorded as CONFIRMED BY SCOTT rather than read off a
label, because the female packaging does not actually say it and a later
reader should know which kind of fact this is.

COUNTS ARE TALLIED, so neither carries an [ESTIMATE] marker. Both fall short
of the 20-piece pack, and the female shortfall has a known cause worth
recording: Scott, "female 10 some went to LRD." That is consumption to the
other site, NOT loss, and nothing here creates an LRD stock row -- he did not
say how many went or where they landed, and inventing a Florida row would be
allocation-by-plan with nobody carrying anything.

    itq run scripts/add_dc_pigtails.py
    itq run scripts/add_dc_pigtails.py --commit
"""
import os
import sys
from decimal import Decimal

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import Company, SupplierPart  # noqa: E402
from part.models import Part, PartCategory  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

COMMIT = "--commit" in sys.argv
CAT = PartCategory.objects.get(pk=119)          # Electronics/Cables
LOC = StockLocation.objects.get(pk=565)         # B0-R1C4, power & misc cables

COMMON = (
    "\n\nBARREL SIZE 5.5 x 2.1 mm — the common 12 V size, and the one that "
    "matters: 5.5 x 2.5 mm looks identical and will seem to fit while making a "
    "poor or intermittent centre-pin contact. Printed on the MALE bag; the "
    "female packaging does not state it, and Scott CONFIRMED the two match "
    "(2026-09-14) rather than it being read off a label.\n\n"
    "POLARITY IS NOT MARKED ON THE CONNECTOR. Red to centre pin, black to "
    "sleeve, is the near-universal convention and what these are wired to — but "
    "centre-negative supplies exist and a reversed pigtail destroys whatever it "
    "feeds. Meter the first one out of a bag before trusting a batch."
)

ITEMS = [
    dict(
        name="DC Barrel Pigtail, 5.5 x 2.1 mm FEMALE jack, flying leads",
        asin="X001F7ARKB", pack="20", qty=Decimal("10"),
        desc=("Female DC barrel jack (5.5 x 2.1 mm) on flying red/black leads. "
              "Takes a male plug from a wall adapter and hands you bare wire."),
        kw=("dc pigtail, barrel jack, 5.5x2.1, female, power lead, 12v, "
            "socket, adapter tail"),
        notes=("Female DC barrel JACK on flying leads — the end that ACCEPTS a "
               "wall-adapter plug. Use this when the project needs to be fed "
               "from an existing power brick." + COMMON +
               "\n\nCOUNTED 10 by Scott 2026-09-14. Sold as a 20-piece pack; "
               "the balance went to LRD (Scott: \"some went to LRD\"). Consumed "
               "to the other site, not lost — and deliberately NOT given an LRD "
               "stock row, because how many went and where they landed is "
               "unknown and a row invented here would be fiction."),
    ),
    dict(
        name="DC Barrel Pigtail, 5.5 x 2.1 mm MALE plug, 12 in leads (UltraPoE CT-DCCORD-M)",
        asin="B0BTHSHJHB", pack="20", qty=Decimal("14"),
        desc=("Male DC barrel plug (5.5 x 2.1 mm) on 12 in red/black leads. "
              "UltraPoE model CT-DCCORD-M. Feeds a device that has a barrel "
              "socket from a bare-wire supply."),
        kw=("dc pigtail, barrel plug, 5.5x2.1, male, power lead, 12v, "
            "CT-DCCORD-M, ultrapoe, security camera"),
        notes=("Male DC barrel PLUG on 12 inch flying leads — the end that goes "
               "INTO a device's power socket. Use this to run a device from a "
               "bench supply or a bare-wire rail. UltraPoE model CT-DCCORD-M, "
               "sold for security-camera wiring." + COMMON +
               "\n\nCOUNTED 14 by Scott 2026-09-14, from a 20-piece pack."),
    ),
]

amazon = Company.objects.filter(name__istartswith="Amazon").first()

for it in ITEMS:
    existing = Part.objects.filter(name=it["name"]).first()
    print(f"\n{it['name'][:70]}")
    print(f"   {'EXISTS' if existing else 'will create'}   qty {float(it['qty']):g}  "
          f"SKU {it['asin']} pack {it['pack']}")
    if not COMMIT:
        continue

    p = existing or Part.objects.create(
        name=it["name"], description=it["desc"], category=CAT,
        keywords=it["kw"], notes=it["notes"], active=True,
        purchaseable=True, component=True, default_location=LOC)

    if not StockItem.objects.filter(part=p).exists():
        si = StockItem.objects.create(
            part=p, location=LOC, quantity=it["qty"],
            notes=f"COUNTED {float(it['qty']):g} by Scott 2026-09-14 during the "
                  f"wire-shelf stock-in. Tallied, not an estimate.")
        print(f"   stock {si.pk}: {float(si.quantity):g} @ {si.location.pathstring}")

    if amazon and not SupplierPart.objects.filter(part=p, SKU=it["asin"]).exists():
        sp = SupplierPart.objects.create(
            part=p, supplier=amazon, SKU=it["asin"],
            link=f"https://www.amazon.com/dp/{it['asin']}",
            note=f"Sold as a {it['pack']}-piece pack.")
        SupplierPart.objects.filter(pk=sp.pk).update(pack_quantity=it["pack"])
        sp.refresh_from_db()
        print(f"   supplier {sp.pk}: {sp.SKU} pack_quantity={sp.pack_quantity}")

    p.refresh_from_db()
    print(f"   #{p.pk}  home={p.default_location.pathstring}")

if not COMMIT:
    print("\nDRY RUN — nothing written. Re-run with --commit.")
