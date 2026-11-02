#!/usr/bin/env python3
"""Land the 2026-10-11 Florida carry at LRD/Receiving (Scott, 2026-11-02:
"Yes, they came down" - FL-01, FL-02 and the loose Einstar).

1. Each open SLN->LRD TransferOrder is pointed at LRD/Receiving, issued and
   completed, so InvenTree does the move and the stock history links to the
   TO (the box is the thing, the TO is the manifest). REFUSED for a TO with
   any allocation whose stock row is not under SLN/Florida Staging:
   florida_pack.py split rows, and completing an allocation that still points
   at the SLN home row would carry home stock to Florida on paper.
2. Rows still under Florida Staging that no TO moved are moved directly.
3. Every landed row: commuting tools get a trips[] entry (what trip.py land
   writes), and any leftover florida earmark + tag is dropped.
default_location is untouched: the SLN home stays the spare's home.

    itq run scripts/land_fl_boxes_1102.py [--skip <stock_pk> ...]            # dry run
    itq run scripts/land_fl_boxes_1102.py [--skip <stock_pk> ...] --commit
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model  # noqa: E402
from django.db import transaction  # noqa: E402
from django.utils import timezone  # noqa: E402
from order.models import TransferOrder, TransferOrderAllocation  # noqa: E402
from order.status_codes import TransferOrderStatus  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

argv = sys.argv[1:]
COMMIT = "--commit" in argv
skip = set()
if "--skip" in argv:
    for a in argv[argv.index("--skip") + 1:]:
        if not a.isdigit():
            break
        skip.add(int(a))

user = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
staging = StockLocation.objects.get(pathstring="SLN/Florida Staging")
staged_locs = staging.get_descendants(include_self=True)
dest = StockLocation.objects.get(pathstring="LRD/Receiving")
lrd = StockLocation.objects.get(name="LRD", parent__isnull=True)
today = str(timezone.now().date())

before = list(StockItem.objects.filter(location__in=staged_locs)
              .exclude(pk__in=skip).select_related("part", "location"))
want = {s.pk for s in before}
print(f"{len(before)} rows to land under {staging.pathstring} -> {dest.pathstring}"
      f"  skip={sorted(skip) or '-'}  ({'COMMIT' if COMMIT else 'dry run'})\n")

# 1. TransferOrders
open_tos = TransferOrder.objects.filter(
    destination__in=lrd.get_descendants(include_self=True),
    status__in=[TransferOrderStatus.PENDING, TransferOrderStatus.ISSUED])
for to in open_tos:
    allocs = list(TransferOrderAllocation.objects.filter(line__order=to)
                  .select_related("item__part", "item__location"))
    bad = [a for a in allocs if a.item.location_id not in {l.pk for l in staged_locs}
           or a.item_id in skip or a.quantity != a.item.quantity]
    print(f"{to.reference}: {len(allocs)} allocations, {len(bad)} not a whole staged row")
    for a in bad:
        loc = a.item.location.pathstring if a.item.location else "-"
        print(f"   ! stock {a.item_id} alloc {a.quantity:g} of {a.item.quantity:g} @ {loc}"
              f"  {a.item.part.name[:44]}")
    if bad:
        print(f"   -> {to.reference} NOT completed; its rows are moved directly instead")
        continue
    if COMMIT:
        try:
            with transaction.atomic():
                to.destination = dest
                to.save()
                if to.status == TransferOrderStatus.PENDING:
                    to.issue_order()
                    to.refresh_from_db()
                to.complete_order(user=user)
        except Exception as e:
            print(f"   -> {to.reference} refused ({e}); rolled back, rows moved directly")
        to.refresh_from_db()
        print(f"   -> status now {to.status} ({'COMPLETE' if to.status == 30 else 'NOT complete'})")

# 2. Whatever is still staged
rest = StockItem.objects.filter(location__in=staged_locs, pk__in=want)
print(f"\nmoved directly (no TO): {rest.count()} rows")
for s in rest.select_related("part"):
    print(f"   {s.pk:5} {s.quantity:>6g}  {s.part.name[:56]}")
if COMMIT:
    rest.update(location=dest)

# 3. Metadata, then verify
if COMMIT:
    for s in StockItem.objects.filter(pk__in=want):
        meta = dict(s.metadata or {})
        if "commutes" in meta:
            meta["commutes"].setdefault("trips", []).append({"on": today, "to": dest.pathstring})
        meta.pop("florida", None)
        StockItem.objects.filter(pk=s.pk).update(metadata=meta)
        if "florida" in [t.name for t in s.tags.all()]:
            s.tags.remove("florida")
    at = StockItem.objects.filter(pk__in=want, location=dest).count()
    left = StockItem.objects.filter(location__in=staged_locs).count()
    stale = StockItem.objects.filter(pk__in=want, metadata__has_key="florida").count()
    print(f"\nverify: {at}/{len(want)} at {dest.pathstring}; {left} left in staging; "
          f"{stale} still earmarked")
