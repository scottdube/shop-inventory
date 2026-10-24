"""Queue D, 2026-10-24: the 35 passive-kit parts #1419-#1453.

probe_1024_0205.py measured the pool tonight: 35 active parts with empty
keywords, all seeded 2026-10-23 from the ALLECIN kit lids now in Cab2-D3 --
11 electrolytics (#1419-#1429) and 24 1% 1/2W resistors (#1430-#1453).

Vocabulary: search is a SUBSTRING match, so 'e-cap' does not find
'electrolytic' and '220nF' does not find '0.22uF'. Each part gets the
alternate value spellings, the hobbyist names, and for the resistors the
5-band 1% color code of the value (standard code for that value, not read
off a body -- nobody has photographed the bands).

Guards unchanged from kw_apply.py: never overwrite a non-empty field, write
through .update(), verify by re-reading the row. Each pk is also checked
against the value it expects in its name, so a renumbered part is skipped.

Usage:  kw_write_1024.py [--commit]
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

# pk: (name token, alternate value spellings, body size)
CAPS = {
    1419: ("0.22uF 50V", "220nF, 0.22 uF, 0.22µF", "5x11"),
    1420: ("0.47uF 50V", "470nF, 0.47 uF, 0.47µF", "5x11"),
    1421: ("10uF 50V", "10 uF, 10µF", "5x11"),
    1422: ("100uF 16V", "100 uF, 100µF", "5x11"),
    1423: ("100uF 25V", "100 uF, 100µF", "5x11"),
    1424: ("220uF 10V", "220 uF, 220µF", "5x11"),
    1425: ("220uF 25V", "220 uF, 220µF", "6x11"),
    1426: ("330uF 25V", "330 uF, 330µF", "8x12"),
    1427: ("470uF 16V", "470 uF, 470µF", "8x12"),
    1428: ("680uF 16V", "680 uF, 680µF", "8x12"),
    1429: ("1000uF 16V", "1000 uF, 1000µF, 1mF", "10x16"),
}

# pk: (name token, alternate value spellings, 5-band 1% color code)
RES = {
    1430: ("1R ", "1 ohm, 1R0", "brown black black silver brown"),
    1431: ("2.2R ", "2.2 ohm, 2R2", "red red black silver brown"),
    1432: ("3.3R ", "3.3 ohm, 3R3", "orange orange black silver brown"),
    1433: ("10R ", "10 ohm", "brown black black gold brown"),
    1434: ("22R ", "22 ohm", "red red black gold brown"),
    1435: ("47R ", "47 ohm", "yellow violet black gold brown"),
    1436: ("68R ", "68 ohm", "blue gray black gold brown"),
    1437: ("100R ", "100 ohm", "brown black black black brown"),
    1438: ("120R ", "120 ohm", "brown red black black brown"),
    1439: ("220R ", "220 ohm", "red red black black brown"),
    1440: ("330R ", "330 ohm", "orange orange black black brown"),
    1441: ("470R ", "470 ohm", "yellow violet black black brown"),
    1442: ("560R ", "560 ohm", "green blue black black brown"),
    1443: ("680R ", "680 ohm", "blue gray black black brown"),
    1444: ("1k ", "1 kohm, 1000 ohm, 1K0", "brown black black brown brown"),
    1445: ("2k ", "2 kohm, 2000 ohm, 2K0", "red black black brown brown"),
    1446: ("2.2k ", "2.2 kohm, 2200 ohm, 2K2", "red red black brown brown"),
    1447: ("4.7k ", "4.7 kohm, 4700 ohm, 4K7", "yellow violet black brown brown"),
    1448: ("5.6k ", "5.6 kohm, 5600 ohm, 5K6", "green blue black brown brown"),
    1449: ("10k ", "10 kohm, 10000 ohm", "brown black black red brown"),
    1450: ("22k ", "22 kohm, 22000 ohm", "red red black red brown"),
    1451: ("47k ", "47 kohm, 47000 ohm", "yellow violet black red brown"),
    1452: ("100k ", "100 kohm, 100000 ohm", "brown black black orange brown"),
    1453: ("1M ", "1 Mohm, 1 meg, 1000k, 1M0", "brown black black yellow brown"),
}

KW = {}
for pk, (tok, alt, size) in CAPS.items():
    KW[pk] = (tok, f"{alt}, electrolytic, e-cap, elko, aluminum electrolytic, "
                   f"polarized, radial, through-hole, THT, {size}, ALLECIN kit")
for pk, (tok, alt, bands) in RES.items():
    KW[pk] = (tok, f"{alt}, metal film, 1/2 watt, 0.5W, half watt, 1%, axial, "
                   f"through-hole, THT, {bands}, ALLECIN kit")

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
