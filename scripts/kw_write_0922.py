"""Queue D, 2026-09-22: the one LIVE empty-keyword row.

kw_active_probe_0921.py re-measured the pool tonight: 38 rows read empty, 37 of
them inactive tombstones that stay blank on purpose, and exactly ONE live part —
#1256 'Sim G1000 GMA1347', created 2026-09-21 by the G1000 build work. So queue D
is not re-opened, it is one night behind, which is what the 09-21 closure
predicted would happen as new parts land.

Vocabulary, same rule as 09-21: search is a SUBSTRING match, so an abbreviation
never finds its expansion. 'GMA1347' and 'GMA 1347' are both here because the
panel is silkscreened one way and catalogued the other; 'audio panel' and
'intercom' are what Scott would actually type six months from now, and neither
appears in the part name.

Guards unchanged from kw_apply.py: never overwrite a non-empty field, write
through .update(), verify by re-reading the row.

Usage:  kw_write_0922.py [--commit]
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
    1256: ("GMA1347, GMA 1347, audio panel, intercom, comm selector, "
           "marker beacon, audio selector, avionics, G1000, glass cockpit, "
           "Garmin, sim panel, flight sim, cockpit build, project"),
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
