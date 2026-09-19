#!/usr/bin/env python3
"""Catalogue the Raspberry Pi 3 Model B, cased, with its Pi-hole SD card.

Scott 2026-09-19: free stock, card in it, Pi-hole DNS, goes to RB-11.

IDENTIFIED OFF THE BOARD, NOT GUESSED FROM SHAPE. Two independent markings
agree and they rule out the 3B+, which is the easy mistake:

    BROADCOM BCM2837RIFBG   bare package -> Pi 3 Model B.
                            The 3B+ is BCM2837B0 under a METAL heat spreader.
    FCC ID 2ABCB-RPI32      -> Pi 3 Model B. The 3B+ is 2ABCB-RPI3BP.
    no 4-pin PoE header     -> the B+ has one. This does not.

That matters more than model pedantry: the 3B is 2.4 GHz Wi-Fi ONLY and
100 Mbit Ethernet, and the 3B+ is dual-band with gigabit-class silicon.
Calling this a 3B+ would promise a 5 GHz radio that is not on the board.

CATEGORY: flat "Modules" (pk 22), NOT Electronics/Modules/Dev Boards. Against
the tidier tree, and deliberately: the Pi 4 kit #395, the Pi 4 PSU #350 and
the Pi Zero WH #73 are all in flat Modules, so the structured category would
separate this Pi from every other Pi. The shadow-root split is a known mess;
the rule that keeps working is to follow the siblings.

NOT CATALOGUED HERE: the power supply. Scott said one comes with it, and the
answer to which one came back as "pihole dns" -- plainly the SD card answer
landing in the PSU slot. Reinterpreting it as a PSU spec would be inventing
hardware. #189 Smraza is ruled OUT on the evidence regardless: it is USB-C,
for a Pi 4, and the 3B takes micro-USB.

THE CASE IS NOT IDENTIFIED either. It is black plastic with an internal
heatsink block. No model is legible in the photo and a guess would read the
same as a reading.

LOCATION IS A PROPOSAL. RB-11 holds the Pi 4 kit and a Kill A Watt in 2 rows.
Twice today a location right by category turned out to be physically full.

    itq run scripts/add_rpi3b.py [--commit]
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
CATEGORY_PK = 22          # flat "Modules", where every other Pi lives
BIN_PK = 484              # SLN/Electronics Bench/Red Bins/RB-11
PREFIX = "Raspberry Pi 3 Model B"
QTY = 1                   # stated by Scott

NAME = "Raspberry Pi 3 Model B (BCM2837, 1GB), cased, with Pi-hole SD card"
DESC = ("Raspberry Pi 3 Model B: BCM2837 quad A53, 1 GB RAM, 2.4 GHz Wi-Fi + BT "
        "4.1, 100 Mbit Ethernet, 4x USB 2.0, micro-USB power. In an unidentified "
        "black case. SD card fitted, carrying a Pi-hole DNS install. Free stock.")
KEYWORDS = ("raspberry pi 3 model B rpi3 rpi BCM2837 BCM2837RIFBG 2ABCB-RPI32 "
            "SBC single board computer linux pihole pi-hole DNS adblock 40-pin "
            "GPIO micro-usb wifi bluetooth LAN9514 cased")

NOTES = """**Raspberry Pi 3 Model B**, in a black case, with an SD card in it. Free stock (Scott, 2026-09-19).

**Identified off the board, and it is a 3B — NOT a 3B+.** Two markings agree:

    BROADCOM BCM2837RIFBG   bare package. The 3B+ is BCM2837B0 under a METAL lid.
    FCC ID 2ABCB-RPI32      the 3B+ is 2ABCB-RPI3BP.
    no 4-pin PoE header     the B+ has one; this board does not.

**That distinction is not pedantry — it is two capabilities the B+ has and this does not:**

| | 3B (this board) | 3B+ |
|---|---|---|
| Wi-Fi | **2.4 GHz only** | dual-band, adds 5 GHz |
| Ethernet | 100 Mbit | gigabit-class PHY |

Promising a 5 GHz radio that is not on the board is the failure this note exists to prevent.

**⚠ THE ETHERNET AND ALL FOUR USB PORTS SHARE ONE USB 2.0 BUS.** The LAN9514 hangs the NIC off the same hub as the USB ports. Wire speed and a busy USB disk compete for the same 480 Mbit, and the practical Ethernet ceiling is around 95 Mbit even before that. Fine for DNS; not a file server.

**⚠ MICRO-USB POWER, AND THIS IS THE CLASSIC PI 3 FAILURE.** It wants 5.1 V at 2.5 A. A thin micro-USB cable drops enough voltage under load to brown the board out — which shows as random SD corruption, USB devices dropping, and throttling, not as a clean power failure. **Symptoms look like a failing SD card or a failing board.** Use a proper supply and a short heavy cable before condemning anything.

**Do NOT back-feed 5 V through the GPIO header** to get around that. It bypasses the input polyfuse, so nothing protects the board.

**THE SD CARD HAS A PI-HOLE DNS INSTALL ON IT** (Scott, 2026-09-19). Two things follow:

1. **That card is the only copy of that configuration** — blocklists, upstream resolvers, local DNS records, DHCP reservations if it was serving DHCP. **Image it before reusing the card.** `dd` to a file costs minutes; rebuilding a curated blocklist and a set of local DNS names does not.
2. **A Pi-hole is a DNS server, and a DNS server that stops answering takes the network with it.** This one is on the bench as free stock, so it is not answering now — meaning DNS points somewhere else and the question is settled. Recorded so nobody later finds "Pi-hole" on a shelf and wonders whether something is still pointed at it.

**THE CASE IS NOT IDENTIFIED.** Black plastic with an internal heatsink block; no model legible. Not named rather than guessed — a guessed case model reads exactly like a read one.

**NO POWER SUPPLY ON THIS RECORD.** Scott said one comes with it. Which one is unresolved: the answer came back as *"pihole dns"*, which is the SD card answer in the PSU slot. **[#189 Smraza 5.1V 3A] is ruled OUT on the evidence** — it is USB-C, sold for the Pi 4, and this board takes micro-USB. [#350] is the Pi 4 official USB-C supply, also wrong. Whatever it is, it is probably a new part.

**Location RB-11 is a PROPOSAL.** It holds [#395 Vilros Pi 4 kit] and [#1070 Kill A Watt] — SBCs together — but a cased Pi is bulky and nobody has looked at the space. Twice on 2026-09-19 a location correct by category turned out to be physically full."""


def check():
    lim = (("name", NAME, 100), ("description", DESC, 250), ("keywords", KEYWORDS, 250))
    bad = [f"{f}: {len(v)} > {n}" for f, v, n in lim if len(v) > n]
    for f, v, n in lim:
        print(f"   {f:12s} {len(v):3d}/{n}")
    if bad:
        print("FIELD TOO LONG — full_clean() would abort:", *bad)
        sys.exit(1)


cat = PartCategory.objects.get(pk=CATEGORY_PK)
bin_ = StockLocation.objects.get(pk=BIN_PK)
existing = Part.objects.filter(name__startswith=PREFIX).first()
print(f"category: {cat.pathstring}\nbin:      {bin_.pathstring} "
      f"({StockItem.objects.filter(location=bin_).count()} rows)\n{NAME}")
check()
print(f"\nexisting: {('#%d' % existing.pk) if existing else 'will create'}")

if not COMMIT:
    print("\nDRY RUN — nothing written. Re-run with --commit.")
    sys.exit(0)

if existing is None:
    p = Part.objects.create(name=NAME, description=DESC, category=cat,
                            keywords=KEYWORDS, notes=NOTES, default_location=bin_,
                            active=True, purchaseable=False, component=False)
else:
    p = existing
    Part.objects.filter(pk=p.pk).update(name=NAME, description=DESC, category=cat,
                                        keywords=KEYWORDS, notes=NOTES,
                                        default_location=bin_)
p.refresh_from_db()
si = StockItem.objects.filter(part=p, location=bin_).first()
if si is None:
    si = StockItem.objects.create(part=p, location=bin_, quantity=QTY)
si.refresh_from_db()

print(f"\n#{p.pk} {p.name}")
print(f"    {p.category.pathstring}   default_location {p.default_location.pathstring}")
print(f"    stock [{si.pk}] qty {si.quantity:g} @ {si.location.pathstring}"
      f"  {'ok' if float(si.quantity) == QTY else '!! WRONG'}")
for label, probe in (("3B not 3B+", "NOT a 3B+"),
                     ("2.4GHz only", "2.4 GHz only"),
                     ("shared USB bus", "SHARE ONE USB 2.0 BUS"),
                     ("undervolt trap", "CLASSIC PI 3 FAILURE"),
                     ("image the card", "Image it before reusing the card"),
                     ("case unnamed", "THE CASE IS NOT IDENTIFIED"),
                     ("no PSU claimed", "NO POWER SUPPLY ON THIS RECORD"),
                     ("#189 ruled out", "ruled OUT on the evidence"),
                     ("loc is proposal", "Location RB-11 is a PROPOSAL")):
    print(f"    {label:16s} {probe in p.notes}")
print(f"    RB-11 now holds {StockItem.objects.filter(location=bin_).count()} rows")
