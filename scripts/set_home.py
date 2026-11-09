#!/usr/bin/env python3
"""Give a received order's parts a HOME that is not where they sit today.

Scott, walking the open-PO list 2026-11-09: the screwdriver (PO-0290) and the
tweezers (PO-0287) were both "on the countertop for now, ends up in BR-D1 /
BL-D1" - the LRD bench pedestals are not assembled yet. The row's location is
where the thing physically is; default_location is where it goes home
(docs/TRAPS.md: never a staging spot). This sets the default_location of every
part on the order and writes the plan on each of the order's rows, so the
next person reading the row knows why it is not at home.

    itq run scripts/set_home.py PO-0287 --home BL-D1 --why "once the LRD bench pedestal is assembled"
    itq run scripts/set_home.py PO-0287 --home 851   --why "..." --commit

--home takes a pk, a unique name, or a full pathstring. Dry run by default.
Every write is re-read.
"""
import argparse, datetime, os, sys
import django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.db import transaction  # noqa: E402
from order.models import PurchaseOrder  # noqa: E402
from part.models import Part  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402
from plugins.notes_compat import note_text, note_append  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("reference")
ap.add_argument("--home", required=True, help="StockLocation pk, unique name, or pathstring")
ap.add_argument("--why", default="", help="when/why it moves home, in Scott's words")
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

if a.home.isdigit():
    home = StockLocation.objects.get(pk=int(a.home))
else:
    hits = list(StockLocation.objects.filter(name=a.home)) or list(StockLocation.objects.filter(pathstring=a.home))
    if len(hits) != 1:
        sys.exit(f"{a.home!r} matches {len(hits)} locations: " + ", ".join(f"{h.pk} {h.pathstring}" for h in StockLocation.objects.filter(name=a.home)))
    home = hits[0]

po = PurchaseOrder.objects.get(reference=a.reference)
today = str(datetime.date.today())


class DryRun(Exception):
    pass


try:
    with transaction.atomic():
        for ln in po.lines.select_related("part__part"):
            part = ln.part.part
            Part.objects.filter(pk=part.pk).update(default_location=home)
            part.refresh_from_db()
            if part.default_location_id != home.pk:
                raise RuntimeError(f"part {part.pk}: default_location did not stick")
            rows = list(StockItem.objects.filter(part=part, purchase_order=po)) or \
                   list(StockItem.objects.filter(part=part).exclude(location=home))
            for row in rows:
                where = row.location.pathstring if row.location else "(no location)"
                line = f"Scott {today}: at {where} for now; home is {home.pathstring}" + (f" {a.why}" if a.why else "") + \
                       f". default_location set to {home.name} the same day."
                note_append(row, line)
                if line not in (note_text(row) or ""):
                    raise RuntimeError(f"stock {row.pk}: note did not stick")
                print(f"stock {row.pk} {part.full_name[:48]} at {where} -> home {home.pathstring}")
            if not rows:
                print(f"part {part.pk} {part.full_name[:48]}: default_location -> {home.pathstring} (no rows to annotate)")
        if not a.commit:
            raise DryRun()
except DryRun:
    print("DRY RUN - rolled back. Re-run with --commit.")
else:
    print("COMMITTED")
