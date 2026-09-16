#!/usr/bin/env python3
"""Flag the DP-to-2x-HDMI MST hub as received-but-undecided.

Scott, 2026-09-16: "po-163 is also recieved but may be returned."

Received to SLN/Receiving rather than filed into a drawer, ON PURPOSE. An item
whose disposition is undecided should stay where it is easy to find and still
boxed; burying it in the bin wall is how a return window quietly expires. No
default_location is set for the same reason -- default_location means "where a
spare goes home", and this may not become a spare at all.

THE DEADLINE COLLIDES WITH THE FLORIDA DEPARTURE, which is the reason this
note exists at all rather than a bare "may be returned". Amazon's standard
window is 30 days from delivery -- NOT verified for this order -- which from a
2026-09-14 target lands around 2026-10-14. Scott leaves for LRD about
2026-10-12. The decision therefore has to be made BEFORE departure, not when
the window nominally closes, because after the 12th the hub is in New
Hampshire and he is not.

    itq run scripts/po163_pending_return.py
    itq run scripts/po163_pending_return.py --commit
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from stock.models import StockItem  # noqa: E402

COMMIT = "--commit" in sys.argv

si = StockItem.objects.filter(part_id=1181).select_related("part", "location").first()
assert si, "no stock row for #1181"
print(f"{si.part.name}")
print(f"  stock {si.pk} qty={float(si.quantity):g} @ {si.location.pathstring}")

if not COMMIT:
    print("\nDRY RUN — nothing written. Re-run with --commit.")
    sys.exit(0)

note = (si.notes or "").rstrip() + (
    "\n\n**DISPOSITION UNDECIDED — MAY BE RETURNED.** Scott, 2026-09-16: "
    "\"po-163 is also recieved but may be returned.\"\n\n"
    "Left in SLN/Receiving and NOT filed into a drawer, and given no "
    "default_location. Both deliberate: an item that may go back should stay "
    "easy to find and still boxed, and default_location means \"where a spare "
    "goes home\" — this may never become a spare.\n\n"
    "**DECIDE BEFORE THE FLORIDA DEPARTURE, not before the return window.** "
    "Amazon's standard window is 30 days from delivery (NOT verified for this "
    "order), which from the 2026-09-14 target lands near 2026-10-14. Scott "
    "leaves for LRD around 2026-10-12. After that the hub is in New Hampshire "
    "and he is not, so the real deadline is the earlier date.\n\n"
    "Its DisplayPort-to-2x-DisplayPort sibling (#1185, PO-0165) was already "
    "returned on 2026-09-16.")
StockItem.objects.filter(pk=si.pk).update(notes=note)
si.refresh_from_db()
print(f"  pending-return flag set: {'MAY BE RETURNED' in si.notes}")
print(f"  departure deadline recorded: {'2026-10-12' in si.notes}")
print(f"  default_location: {si.part.default_location}")
