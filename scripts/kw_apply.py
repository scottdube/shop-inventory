"""Apply queue-D search keywords from a TSV of `pk<TAB>keywords`.

Two guards, both load-bearing:

  * **Never overwrite a non-empty keywords field.** It may be Scott's own
    wording, which beats anything generated here. Non-empty rows are reported
    as skips so the count of "written" stays honest.
  * **Verify by re-reading.** `.save()` on this install has reported success and
    written nothing (docs/TRAPS.md), so a write that does not stick is counted
    as a failure and named rather than tallied as a win.

InvenTree caps keywords at 250 chars; longer input is trimmed at a comma
boundary rather than mid-word, because a half-word is not a search term.
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

ap = argparse.ArgumentParser()
ap.add_argument("--tsv", required=True)
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()


def trim(s):
    s = s.strip()
    if len(s) <= LIMIT:
        return s
    cut = s[:LIMIT]
    if "," in cut:
        cut = cut[: cut.rfind(",")]
    return cut.strip()


rows = []
for line in open(a.tsv):
    line = line.rstrip("\n")
    if not line or line.startswith("#"):
        continue
    pk, _, kw = line.partition("\t")
    if not kw.strip():
        continue
    rows.append((int(pk), trim(kw)))

wrote = skipped_nonempty = missing = failed = 0
for pk, kw in rows:
    p = Part.objects.filter(pk=pk).first()
    if not p:
        print(f"?? {pk}: no such part")
        missing += 1
        continue
    if (p.keywords or "").strip():
        print(f"=  {pk}: keywords already set — left alone ({p.keywords[:45]})")
        skipped_nonempty += 1
        continue
    if not a.commit:
        print(f"~  {pk}: WOULD set [{kw}]")
        continue

    Part.objects.filter(pk=pk).update(keywords=kw)
    fresh = Part.objects.get(pk=pk)
    if (fresh.keywords or "").strip() == kw:
        print(f"+  {pk}: {kw[:70]}")
        wrote += 1
    else:
        print(f"!! {pk}: write did not stick (row reads {fresh.keywords!r})")
        failed += 1

EMPTY = Q(keywords="") | Q(keywords__isnull=True)
print(f"\nwrote={wrote} skipped_nonempty={skipped_nonempty} missing={missing} "
      f"failed_verify={failed} {'(DRY RUN)' if not a.commit else ''}")
print(f"keywords still empty: {Part.objects.filter(EMPTY).count()} / {Part.objects.count()}")
