"""Queue D, 2026-09-21: keywords for the 17 LIVE empty-keyword rows.

That is the whole remaining live backlog -- 54 rows read empty, but 37 are merge
receipts and refund/not-inventory tombstones and are DELIBERATELY left blank. A
tombstone with good keywords answers a plain-English search and reads as a live
part, which is the failure docs/TRAPS.md records under "inactive parts are merge
receipts". Blank is what keeps them out of the way.

Vocabulary rule, from the task file: search is a SUBSTRING match, so an
abbreviation does not find its expansion. Every row therefore carries both
("IDC" and "ribbon cable", "MFD" and "multi function display"), plus the size
written the two ways a person types it ("2x12" and "24 pin"), plus the name the
vendor does not use but Scott would ("dupont", "berg strip", "harness lacing").

Guards are kw_apply.py's, unchanged: never overwrite a non-empty field, write
through .update(), and verify by re-reading the row because .save() on this
install has reported success and written nothing.

Usage:  kw_write_0921.py [--commit]
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

_SOCKET = ("female header, pin header socket, header socket, socket strip, "
           "receptacle, double row, {pos}, {pins} pin, {pins}-pin, 2.54mm, "
           "0.1in pitch, 0.1 inch, dupont, berg strip, breadboard, PCB socket")

KW = {
    1239: _SOCKET.format(pos="2x40", pins=80),
    1240: _SOCKET.format(pos="2x20", pins=40),
    1241: _SOCKET.format(pos="2x12", pins=24),
    1242: _SOCKET.format(pos="2x10", pins=20),
    1243: _SOCKET.format(pos="2x8", pins=16),
    1244: _SOCKET.format(pos="2x6", pins=12),
    1245: _SOCKET.format(pos="2x5", pins=10),
    1246: _SOCKET.format(pos="2x4", pins=8),
    1247: _SOCKET.format(pos="2x3", pins=6),
    1248: _SOCKET.format(pos="2x2", pins=4),
    1249: ("box header, shrouded header, male header, IDC header, keyed shroud, "
           "ISP header, JTAG, programming header, ribbon cable header, 2x6, "
           "12 pin, 12P, 2.54mm, 0.1in pitch"),
    1250: ("dual concentric encoder, concentric encoder, double knob encoder, "
           "rotary encoder, encoder kit, push switch, detent, radio knob, "
           "avionics knob, comm nav, flight sim radio, PropWash"),
    1251: ("IDC socket, ribbon socket, ribbon cable connector, flat cable socket, "
           "crimp-on connector, female IDC, 2x12, 24 pin, 24P, 24 way, 2.54mm, "
           "0.1in pitch, mates box header"),
    1252: ("IDC socket, ribbon socket, ribbon cable connector, flat cable socket, "
           "crimp-on connector, female IDC, strain relief, 2x15, 30 pin, 30P, "
           "30 way, 2.54mm, 0.1in pitch, uxcell"),
    1253: ("ribbon cable, flat ribbon cable, flat cable, bulk cable, 24 way, "
           "24-way, 24 conductor, 1.27mm pitch, 0.05in pitch, grey ribbon, "
           "red stripe, IDC cable"),
    1254: ("lacing tape, cable lacing, harness lacing, lacing cord, waxed tape, "
           "waxed string, spot tie, wire harness, loom, cable tying, 0.8mm, "
           "black polyester, Guzon"),
    1255: ("G1000, MFD, multi function display, multifunction display, "
           "glass cockpit, Garmin, avionics, sim panel, flight sim, "
           "cockpit build, project"),
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


wrote = skipped = missing = failed = inactive = 0
for pk, raw in sorted(KW.items()):
    kw = trim(raw)
    p = Part.objects.filter(pk=pk).first()
    if not p:
        print(f"?? {pk}: no such part")
        missing += 1
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
      f"failed_verify={failed}{'  (DRY RUN)' if not a.commit else ''}")
print(f"keywords still empty: {still.count()} / {Part.objects.count()} "
      f"({still.filter(active=True).count()} of them LIVE)")
