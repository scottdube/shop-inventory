#!/usr/bin/env python3
"""Consume 3 x M4 x 40 flat head (#997) into BO-0006, the Cessna sim.

Scott, 2026-09-13: "relieve the m4x40 by 3 for the sim ulator project bo",
then confirmed BOTH ambiguities when asked -- part #997 (Phillips flat head,
18-8 stainless) of the THREE M4 x 40 parts in cabinet B1, and consume rather
than allocate, because they are already fitted.

Asking was not ceremony. #988 pan head, #997 flat head and #1177 flat head cap
are all "M4 x 40" and all live in B1; countersunk and non-countersunk are not
interchangeable in a fixture. Guessing between three had already cost a batch
of wrong labels last week.

WHY take_stock AND NOT A QUANTITY EDIT. Writing 93 -> 90 directly leaves no
record of who removed three or why, and the next person reconciling the drawer
finds a number that changed for no visible reason. take_stock() writes a
StockItemTracking entry, so the removal is in the item's own history with its
reason attached.

NOT ALLOCATED TO THE BUILD, deliberately. Allocation reserves stock that is
still on the shelf; these are in the machine. The power splitter yesterday WAS
allocated because it has not been fitted yet. Same build, different treatment,
because the physical facts differ -- see the note left on the row.

    itq run scripts/sim_m4x40_consume.py
    itq run scripts/sim_m4x40_consume.py --commit
"""
import os
import sys
from decimal import Decimal

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from build.models import Build  # noqa: E402
from stock.models import StockItem  # noqa: E402

COMMIT = "--commit" in sys.argv
TAKE = Decimal("3")

rows = list(StockItem.objects.filter(part_id=997).select_related("part", "location"))
assert len(rows) == 1, f"expected one row for #997, found {len(rows)}"
si = rows[0]
b = Build.objects.get(reference="BO-0006")

print(f"[{si.part.pk}] {si.part.name}")
print(f"   row {si.pk}: {float(si.quantity):g} @ {si.location.pathstring}")
print(f"   take {float(TAKE):g} for {b.reference} ({b.title})")
print(f"   -> {float(si.quantity) - float(TAKE):g} remaining")

if not COMMIT:
    print("\nDRY RUN — nothing written. Re-run with --commit.")
    sys.exit(0)

user = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
before = float(si.quantity)

si.take_stock(
    TAKE, user,
    notes=f"Fitted to {b.reference} ({b.title}). Scott, 2026-09-13.",
)
si.refresh_from_db()

if float(si.quantity) != before - float(TAKE):
    print(f"✗ take_stock did not land: still {float(si.quantity):g}")
    sys.exit(1)

note = (si.notes or "").rstrip() + (
    f"\n\n2026-09-13: 3 pieces removed and fitted to {b.reference} "
    f"(Cessna Flight Simulator), leaving {float(si.quantity):g}. CONSUMED, not "
    f"allocated -- these are in the machine, not reserved on the shelf. The "
    f"power cord splitter #1180 on the same build is allocated instead, because "
    f"that one has not been fitted yet. Same build, different treatment, because "
    f"the physical facts differ."
)
StockItem.objects.filter(pk=si.pk).update(notes=note)
si.refresh_from_db()

print(f"\n✓ {before:g} -> {float(si.quantity):g} @ {si.location.pathstring}")
tracking = si.tracking_info.order_by("-pk").first()
print(f"  tracking entry: {tracking.pk if tracking else '(none)'} "
      f"— {(tracking.notes or '')[:60] if tracking else ''}")
print(f"  note recorded: {'BO-0006' in si.notes}")
