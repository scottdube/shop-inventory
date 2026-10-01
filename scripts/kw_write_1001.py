"""Queue D, 2026-10-01: the one LIVE empty-keyword row.

probe_1001_0205.py measured the pool tonight: exactly ONE active part with empty
keywords -- #1267 'Laser Exhaust Auto-Start', a Projects-category part created
2026-09-30 by the laser exhaust work (laser_exhaust_project.py). Queue D is one
night behind new parts, as predicted when it closed.

Vocabulary: search is a SUBSTRING match, so 'fume' does not find 'exhaust' and
'P2S' does not find 'xTool'. Both laser names are here because the duct is
shared; 'blast gate' and 'diverter' are the two words for the same flap.

Guards unchanged from kw_apply.py: never overwrite a non-empty field, write
through .update(), verify by re-reading the row.

Usage:  kw_write_1001.py [--commit]
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
    1267: ("laser exhaust, fume extraction, fume extractor, booster fan, "
           "inline fan, duct fan, auto start, current sensing, power monitor, "
           "blast gate, diverter, P2S, F1 Ultra, xTool, laser, project"),
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
