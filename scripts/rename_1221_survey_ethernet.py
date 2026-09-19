#!/usr/bin/env python3
"""Rename #1221 so its label stops clipping, and survey what an Ethernet bin
would actually gather.

The rename: "Thermal Circuit Breaker, 20A push-button reset, panel mount
(mxuteuk L1-ls-20A)" is 77 chars and wraps to a 4th line, so the rendered label
lost the model number entirely. Same failure as the POE naming earlier today,
and the fix is the same: the label carries identity + address, the record
carries the detail. panel mount and the mxuteuk model stay in the description
and keywords, which already hold them.

The survey exists because "a bin with just ethernet stuff" is only worth doing
if it GATHERS -- a fourth bin holding four PoE parts is a relabel, not a
consolidation. So: find everything already catalogued that would belong, and
where it currently lives.

    itq run scripts/rename_1221_survey_ethernet.py [--commit]
"""
import os
import re
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part  # noqa: E402

COMMIT = "--commit" in sys.argv

PK = 1221
OLD_NAME = "Thermal Circuit Breaker, 20A push-button reset, panel mount (mxuteuk L1-ls-20A)"
NEW_NAME = "Thermal Circuit Breaker 20A, push-button reset"

p = Part.objects.get(pk=PK)
print(f"#{PK} rename")
print(f"   from {len(p.name):3d}  {p.name}")
print(f"   to   {len(NEW_NAME):3d}  {NEW_NAME}")
if p.name != OLD_NAME:
    print("   WARNING: current name is not the expected one; renaming anyway is unsafe")
    sys.exit(1)
print(f"   model still in description: {'mxuteuk' in (p.description or '')}")
print(f"   model still in keywords:    {'mxuteuk' in (p.keywords or '')}")
print(f"   'panel mount' in description: {'panel' in (p.description or '').lower()}")

# --- survey -------------------------------------------------------------
PAT = re.compile(r'ethernet|rj-?45|rj45|cat\s?[56]|patch cable|keystone|poe|'
                 r'network|lan\b|crimp|8p8c', re.I)
print("\nEthernet-adjacent parts already catalogued:")
rows = []
for q in Part.objects.filter(active=True):
    blob = " ".join([q.name or "", q.description or "", q.keywords or ""])
    if PAT.search(blob):
        loc = q.default_location.pathstring if q.default_location else "(no home)"
        qty = sum(s.quantity for s in q.stock_items.all())
        rows.append((loc, q.pk, q.name, qty))
for loc, pk, name, qty in sorted(rows):
    print(f"   {loc:38} #{pk:<5} qty {qty:<6g} {name[:58]}")
print(f"\n   {len(rows)} parts, {len(set(r[0] for r in rows))} distinct locations")

if not COMMIT:
    print("\nDRY RUN — nothing written. Re-run with --commit.")
    sys.exit(0)

Part.objects.filter(pk=PK).update(name=NEW_NAME)
p.refresh_from_db()
print(f"\n   renamed: {p.name == NEW_NAME}  -> {p.name}")
