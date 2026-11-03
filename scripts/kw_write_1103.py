"""Queue D, 2026-11-03: the 22 empty-keyword parts from the 11-02 put-away.

probe_1103_0205.py measured the pool tonight: 22 active parts with empty
keywords, #1465-#1487 minus #1480, all created by the 2026-11-02 LRD drawer
session (swap-meet lots, C&K switches, knobs, binding posts, Zooz sensor,
terminal-block kit). The PO-sweep parts #1480/#1488-#1490 already had
keywords from creation.

Vocabulary is what someone would type at the bench months later: the
hobbyist name, abbreviations AND expansions (search is substring), and the
use the part gets put to.

Guards unchanged from kw_write_1031.py: never overwrite a non-empty field,
write through .update(), verify by re-reading the row, check the name token.

Usage:  kw_write_1103.py [--commit]
"""
import argparse
import os
import sys

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part  # noqa: E402

LIMIT = 250

KW = {
    1465: ("1N4935",
           "diode, rectifier, fast recovery, fast-recovery rectifier, 1A, 200V, "
           "DO-41, axial, through-hole, flyback, freewheeling"),
    1466: ("series link",
           "battery contact, battery terminal, AA, double A, battery holder, "
           "spring contact, series link, jumper plate, cell connector"),
    1467: ("negative spring",
           "battery contact, battery terminal, AA, double A, battery holder, "
           "negative, spring, coil spring, solder tab"),
    1468: ("positive flat",
           "battery contact, battery terminal, AA, double A, battery holder, "
           "positive, button contact, flat plate, solder tab"),
    1469: ("2x5",
           "pin header, male header, 0.1 inch, 2.54mm, dual row, double row, "
           "2x5, 10-pin, IDC, box header, JTAG, breakout"),
    1470: ("2x8",
           "pin header, male header, 0.1 inch, 2.54mm, dual row, double row, "
           "2x8, 16-pin, IDC, breakout"),
    1471: ("Pin Header Assortment",
           "pin header, male header, header pins, breakaway header, 0.1 inch, "
           "2.54mm, assortment, mixed lot, swap meet, Dupont, Arduino"),
    1472: ("Pin Socket Assortment",
           "pin socket, female header, header socket, 0.1 inch, 2.54mm, "
           "assortment, mixed lot, swap meet, Dupont, Arduino, stackable"),
    1473: ("Knob, plastic",
           "knob, pot knob, potentiometer knob, control knob, pointer knob, "
           "panel knob, plastic, black, blue, dial"),
    1474: ("Knob, aluminum",
           "knob, pot knob, potentiometer knob, control knob, metal knob, "
           "aluminium, aluminum, knurled, anodized, black, dial"),
    1475: ("LMC662",
           "op amp, op-amp, opamp, operational amplifier, dual op amp, CMOS, "
           "rail-to-rail, low power, DIP-8, DIP8, National, LMC662"),
    1476: ("Binding Post, single, red",
           "binding post, banana jack, banana socket, terminal post, "
           "panel mount, red, positive, power supply output, test lead"),
    1477: ("Binding Post, single, black",
           "binding post, banana jack, banana socket, terminal post, "
           "panel mount, black, negative, ground, GND, power supply output"),
    1478: ("C&K 8121",
           "push button, pushbutton, momentary, SPDT, panel mount, "
           "threaded bushing, C&K, CK, 8100 series, switch, vintage"),
    1479: ("C&K 7201",
           "toggle switch, mini toggle, miniature toggle, DPDT, ON-ON, "
           "panel mount, threaded bushing, C&K, CK, 7000 series, vintage"),
    1481: ("C&K 7105",
           "toggle switch, mini toggle, miniature toggle, SPDT, ON-OFF-ON, "
           "center off, centre off, three position, 3-position, C&K, CK, 7000 series"),
    1482: ("ITT Rotary DIP",
           "rotary switch, hex switch, rotary DIP, DIP switch, 16 position, "
           "hexadecimal, BCD, address switch, coded switch, ITT, C&K, screwdriver"),
    1483: ("Push Button, miniature",
           "push button, pushbutton, momentary, panel mount, mini push button, "
           "red button, red cap, switch"),
    1484: ("ZSE41",
           "door sensor, window sensor, open/close sensor, contact sensor, "
           "reed switch, Z-Wave, ZWave, Z-Wave LR, long range, 800 series, Zooz, "
           "Home Assistant"),
    1485: ("Waterproof Case",
           "waterproof case, enclosure, cover, outdoor, weatherproof, Zooz, "
           "XS sensor, ZSE41, door sensor, open/close sensor"),
    1486: ("microSDXC",
           "micro SD, microSD, SD card, memory card, TF card, 128GB, 128 GB, "
           "UHS-I, U3, V30, A2, SD adapter, Raspberry Pi, storage"),
    1487: ("Mardatt",
           "terminal block, pluggable terminal, plug-in terminal, screw terminal, "
           "Phoenix style, Euro block, 5.08mm, 2-pin, 10-pin, PCB terminal, "
           "assortment, kit"),
}

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()


def trim(s):
    s = " ".join(s.split())
    if len(s) <= LIMIT:
        return s
    cut = s[:LIMIT]
    return cut[: cut.rfind(",")].strip() if "," in cut else cut.strip()


wrote = skipped = missing = failed = inactive = mismatch = 0
for pk, (tok, raw) in sorted(KW.items()):
    kw = trim(raw)
    p = Part.objects.filter(pk=pk).first()
    if not p:
        print(f"?? {pk}: no such part")
        missing += 1
        continue
    if tok not in p.name + " ":
        print(f"!! {pk}: name {p.name!r} lacks {tok.strip()!r} -- skipped")
        mismatch += 1
        continue
    if not p.active:
        print(f"-  {pk}: active=False -- tombstone, deliberately left blank")
        inactive += 1
        continue
    if (p.keywords or "").strip():
        print(f"=  {pk}: keywords already set -- left alone ({p.keywords[:45]})")
        skipped += 1
        continue
    if not a.commit:
        print(f"~  {pk}: [{len(kw)}] {kw}")
        continue

    Part.objects.filter(pk=pk).update(keywords=kw)
    fresh = Part.objects.get(pk=pk)
    if (fresh.keywords or "").strip() == kw:
        print(f"+  {pk}: {kw[:72]}")
        wrote += 1
    else:
        print(f"!! {pk}: write did not stick (row reads {fresh.keywords!r})")
        failed += 1

EMPTY = Q(keywords="") | Q(keywords__isnull=True)
still = Part.objects.filter(EMPTY)
print(f"\nwrote={wrote} skipped_nonempty={skipped} inactive={inactive} missing={missing} "
      f"name_mismatch={mismatch} failed_verify={failed}{'  (DRY RUN)' if not a.commit else ''}")
print(f"keywords still empty: {still.count()} / {Part.objects.count()} "
      f"({still.filter(active=True).count()} of them LIVE)")
