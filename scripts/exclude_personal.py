"""Deactivate personal-care/medical records that must not be tracked.

Task-file rule 3: medical/personal-care items never belong in the shop
inventory. Three were found in the catalog on 2026-08-23; #227 and #378 were
already deactivated. Scott confirmed 2026-08-24 that all three are not to be
tracked, so this closes out #354.

DEACTIVATE, never delete — a deleted part takes its PO lines and history with
it, and the record is the evidence that the exclusion was a decision rather
than an oversight. Verified by re-read: .save() on this install has reported
success and written nothing.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part  # noqa: E402

NOTE = "NOT INVENTORY - personal-care/medical, excluded by rule 3."

for pk in (227, 354, 378):
    p = Part.objects.filter(pk=pk).first()
    if not p:
        print(f"?? #{pk}: no such part")
        continue
    if not p.active:
        print(f"=  #{pk}: already inactive — left alone ({p.name[:45]})")
        continue

    desc = p.description or ""
    if "NOT INVENTORY" not in desc:
        desc = f"{NOTE} {desc}"[:250]
    Part.objects.filter(pk=pk).update(active=False, description=desc)

    fresh = Part.objects.get(pk=pk)
    if fresh.active:
        print(f"!! #{pk}: write did not stick — still active")
    else:
        print(f"+  #{pk}: deactivated — {fresh.name[:50]}")
        print(f"      desc now: {fresh.description[:90]}")

print()
for pk in (227, 354, 378):
    p = Part.objects.get(pk=pk)
    print(f"#{pk} active={p.active} stock={p.total_stock}")
