"""The mailbox Meshtastic project claims its ToF sensor — by allocation, not location.

Creates the minimal honest structure: an assembly Part for the project, a BOM
line for the VL53L1X, a Build order, and an allocation of the specific stock
item. Result: 'do I have a VL53L1X?' answers 1 in stock, 0 AVAILABLE — the
truth. The two VL53L4CDs in the same red bin stay free stock: same bin,
different commitment. That is the whole principle.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model
from part.models import Part, PartCategory, BomItem
from build.models import Build, BuildLine, BuildItem
from stock.models import StockItem

user = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()

tof = Part.objects.filter(name__istartswith="VL53L1X").first()
si = StockItem.objects.filter(part=tof).first()
print(f"part:  #{tof.pk} {tof.name[:50]}")
print(f"stock: {si.quantity:g} @ {si.location.name}  price={si.purchase_price}")
print(f"unallocated before: {si.unallocated_quantity():g}")

cat, _ = PartCategory.objects.get_or_create(name="Projects", parent=None)
asm, created = Part.objects.get_or_create(
    name="Mailbox Meshtastic Node",
    defaults=dict(category=cat, assembly=True, component=False, purchaseable=False,
                  description="Meshtastic mailbox monitor - LoRa node with ToF "
                              "sensor detecting mail presence"[:250]))
print(f"\nassembly: #{asm.pk} {'created' if created else 'exists'}")

bom, created = BomItem.objects.get_or_create(part=asm, sub_part=tof,
                                             defaults={"quantity": 1})
print(f"BOM line: 1x {tof.name[:40]} {'created' if created else 'exists'}")

build = Build.objects.filter(part=asm).first()
if not build:
    build = Build.objects.create(
        part=asm, quantity=1, title="Mailbox Meshtastic build",
        reference="BO-0001", issued_by=user)
    print(f"build:    {build.reference} created")
else:
    print(f"build:    {build.reference} exists")

line = BuildLine.objects.filter(build=build, bom_item=bom).first()
if not line:
    # older path: create the line from the BOM if it was not auto-generated
    build.create_build_line_items()
    line = BuildLine.objects.filter(build=build, bom_item=bom).first()
alloc, created = BuildItem.objects.get_or_create(
    build_line=line, stock_item=si, defaults={"quantity": 1})
print(f"allocated: 1x from stock item {si.pk} {'created' if created else 'exists'}")

si.refresh_from_db()
print(f"\nunallocated after: {si.unallocated_quantity():g}")
print(f"=> VL53L1X: {si.quantity:g} in stock, {si.unallocated_quantity():g} available")
l4 = Part.objects.filter(name__istartswith="VL53L4CD").first()
free = sum(x.unallocated_quantity() for x in StockItem.objects.filter(part=l4))
print(f"=> VL53L4CD (same bin): {free:g} available - untouched, free inventory")
