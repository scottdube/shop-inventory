"""Bulk-assign Part.image from a tarball of files named part_<pk>.<ext>.

Queue A of the overnight job fetches image bytes on the LAPTOP (vendor CDNs
answer the laptop and challenge the Mini's IP), so the bytes arrive here as one
archive rather than as N separate transfers. One push, one run — the same reason
`itq` exists at all.

Rules this enforces, because both have already gone wrong once:

  * **Never overwrite a non-empty image slot.** A vendor stock photo must not
    eat a photo of the actual unit on the bench. Filled slots are reported as
    skips, not silently replaced.
  * **Verify the write by re-reading the row.** `.save()` on this install has
    reported success and written nothing (see docs/TRAPS.md). A save that does
    not stick is counted as a failure and named, not tallied as a win.
"""
import argparse
import os
import sys
import tarfile
import tempfile

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.core.files.base import ContentFile  # noqa: E402
from part.models import Part                    # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--tar", required=True, help="tarball of part_<pk>.<ext> files")
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

tmp = tempfile.mkdtemp(prefix="setimg_")
with tarfile.open(a.tar) as tf:
    tf.extractall(tmp)

files = []
for root, _dirs, names in os.walk(tmp):
    for n in sorted(names):
        if not n.startswith("part_"):
            continue
        stem = os.path.splitext(n)[0]
        try:
            pk = int(stem.split("_", 1)[1])
        except (IndexError, ValueError):
            print(f"?? cannot parse pk from {n}")
            continue
        files.append((pk, os.path.join(root, n), n))

set_ok = skipped_filled = missing = failed = 0
for pk, path, name in sorted(files):
    p = Part.objects.filter(pk=pk).first()
    if not p:
        print(f"?? {pk}: no such part")
        missing += 1
        continue
    if p.image:
        print(f"=  {pk}: already has an image ({p.image.name}) — left alone")
        skipped_filled += 1
        continue
    if not a.commit:
        print(f"~  {pk}: WOULD set {name} ({os.path.getsize(path)//1024}KB) — {p.name[:50]}")
        continue

    data = open(path, "rb").read()
    p.image.save(name, ContentFile(data), save=True)

    # Re-read rather than trust the save.
    fresh = Part.objects.get(pk=pk)
    if fresh.image:
        print(f"+  {pk}: {fresh.image.name} ({len(data)//1024}KB) — {p.name[:50]}")
        set_ok += 1
    else:
        print(f"!! {pk}: save reported success but the row is still empty")
        failed += 1

print(f"\nset={set_ok} skipped_already_had_image={skipped_filled} "
      f"missing_part={missing} failed_verify={failed} "
      f"{'(DRY RUN)' if not a.commit else ''}")

total = Part.objects.count()
have = Part.objects.exclude(image="").exclude(image__isnull=True).count()
print(f"coverage now: {have}/{total}")
