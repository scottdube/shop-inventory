"""Queue D, 2026-10-31: the one empty-keyword part, #1460 Condensate Doser.

probe_1031_0205.py measured the pool tonight: 1 active part with empty
keywords, the Projects-category assembly 'Condensate Doser' (ESP32-S3 + 12 V
peristaltic pump dosing vinegar into the LRD air-handler condensate drain),
created with the condensate-doser project on 2026-10-30.

Vocabulary is what someone would type looking for the build months later:
the problem it solves (clogged drain line, algae), the HVAC words for the
line (condensate, drain pan, air handler, AC), and the parts it is made of.

Guards unchanged from kw_write_1024.py: never overwrite a non-empty field,
write through .update(), verify by re-reading the row, check the name token.

Usage:  kw_write_1031.py [--commit]
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
    1460: ("Condensate Doser",
           "condensate drain, drain line, AC drain, air handler, HVAC, "
           "clogged drain, algae, vinegar dosing, dosing pump, peristaltic pump, "
           "ESP32-S3, ESPHome, Home Assistant, LRD, project, build"),
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
