"""Earmark one VL53L4CD for LRD via a TransferOrder — intent, not a fake move.

The stock stays truthfully at SLN/Project Bins until it is physically carried;
the TO records the destination and its allocation RESERVES the unit
(unallocated_quantity counts transfer allocations). When Scott actually packs
it, completing the TO performs the move.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model
from part.models import Part
from stock.models import StockLocation, StockItem
from order.models import TransferOrder, TransferOrderLineItem, TransferOrderAllocation

user = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
l4 = Part.objects.filter(name__istartswith="VL53L4CD").first()
si = StockItem.objects.filter(part=l4).first()
print(f"part:  #{l4.pk} {l4.name[:46]}")
print(f"stock: {si.quantity:g} @ {si.location.pathstring}")
print(f"available before: {si.unallocated_quantity():g}")

sln = StockLocation.objects.get(name="SLN", parent__isnull=True)
lrd = StockLocation.objects.get(name="LRD", parent__isnull=True)

to = TransferOrder.objects.filter(destination=lrd).first()
if not to:
    to = TransferOrder.objects.create(
        reference="TO-0001", take_from=sln, destination=lrd,
        description="Parts earmarked for the next Florida carry"[:250],
        created_by=user)
    print(f"\ncreated {to.reference}: SLN -> LRD")
else:
    print(f"\nexists {to.reference}")

line, created = TransferOrderLineItem.objects.get_or_create(
    order=to, part=l4, defaults={"quantity": 1})
print(f"line: 1x {l4.name[:40]} {'created' if created else 'exists'}")

alloc, created = TransferOrderAllocation.objects.get_or_create(
    line=line, item=si, defaults={"quantity": 1})
print(f"allocation from stock {si.pk}: {'created' if created else 'exists'}")

si.refresh_from_db()
print(f"\navailable after: {si.unallocated_quantity():g}")
print(f"=> VL53L4CD: {si.quantity:g} at SLN, {si.unallocated_quantity():g} free, "
      f"1 reserved for LRD, still physically in the red bin")
