"""Info Orbs project: assembly Part + BOM + Build order, and claim what's on hand.

Allocates by BOM allocation, not by moving parts into a project bin — the shelf
keeps saying where a spare lives, the build says what is committed.
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
cat, _ = PartCategory.objects.get_or_create(name="Projects", parent=None)

asm, created = Part.objects.get_or_create(
    name="Info Orbs",
    defaults=dict(category=cat, assembly=True, component=False, purchaseable=False,
                  description="ESP32 desk widget driving five 1.28in round GC9A01 "
                              "TFTs over one SPI bus, three buttons"[:250]))
print(f"assembly: #{asm.pk} {'created' if created else 'exists'}")

# (part pk, qty, why this one)
BOM = [
    (62,  1, "ESP-WROOM-32 devkit - platformio env is esp32doit-devkit-v1"),
    (70,  5, "GC9A01 1.28in 240x240 SPI round LCD"),
    (738, 3, "6x6mm tactile, the three buttons on G14/G26/G27"),
]
lines = []
for pk, qty, why in BOM:
    sub = Part.objects.get(pk=pk)
    bom, c = BomItem.objects.get_or_create(part=asm, sub_part=sub,
                                           defaults={"quantity": qty})
    if not c and bom.quantity != qty:
        BomItem.objects.filter(pk=bom.pk).update(quantity=qty)
        bom.refresh_from_db()
    lines.append((bom, sub, qty))
    print(f"  BOM {qty}x #{sub.pk} {sub.name[:44]:44} {'created' if c else 'exists'}")

build = Build.objects.filter(part=asm).first()
if not build:
    nxt = max((int(b.reference.split("-")[-1]) for b in Build.objects.all()), default=0) + 1
    build = Build.objects.create(part=asm, quantity=1, title="Info Orbs build",
                                 reference=f"BO-{nxt:04d}", issued_by=user)
    print(f"build: {build.reference} created")
else:
    print(f"build: {build.reference} exists")

if not BuildLine.objects.filter(build=build).exists():
    build.create_build_line_items()

print("\nallocating what is on hand:")
for bom, sub, need in lines:
    line = BuildLine.objects.filter(build=build, bom_item=bom).first()
    if line is None:
        print(f"  #{sub.pk} NO BUILD LINE - skipped"); continue
    got = 0
    for si in StockItem.objects.filter(part=sub).order_by("pk"):
        if got >= need:
            break
        free = si.unallocated_quantity()
        if free <= 0:
            continue
        take = min(free, need - got)
        BuildItem.objects.get_or_create(build_line=line, stock_item=si,
                                        defaults={"quantity": take})
        got += take
    short = need - got
    flag = "" if short == 0 else f"  << SHORT {short:g}"
    print(f"  {sub.name[:40]:40} need {need}  allocated {got:g}{flag}")

# verify by re-reading, never trust the write
print("\nverify:")
for bom, sub, need in lines:
    line = BuildLine.objects.filter(build=build, bom_item=bom).first()
    alloc = sum(bi.quantity for bi in BuildItem.objects.filter(build_line=line))
    onhand = sum(s.quantity for s in StockItem.objects.filter(part=sub))
    free = sum(s.unallocated_quantity() for s in StockItem.objects.filter(part=sub))
    print(f"  #{sub.pk:4} {sub.name[:38]:38} stock={onhand:g} free={free:g} allocated={alloc:g}/{need}")
print(f"\n{build.reference}  {build.title}")
