"""Correct BO-0016 to describe the orb actually built, and fix two stale records.

The old BOM was written in August from whatever was on the shelf, before the
design settled on the ESP32-S3. Allocating against it would have consumed a
dev kit still in the drawer and left the SuperMini that was soldered showing
as free stock.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part, PartCategory, BomItem
from build.models import Build, BuildLine, BuildItem
from stock.models import StockItem, StockLocation

b = Build.objects.get(reference="BO-0016")
asm = b.part
print(f"{b.reference} '{b.title}' assembly=#{asm.pk}\n")

# --- 1. release every existing allocation; the BOM they were made against is wrong
for line in BuildLine.objects.filter(build=b):
    items = BuildItem.objects.filter(build_line=line)
    if items.exists():
        print(f"   releasing {sum(i.quantity for i in items):g}x {line.bom_item.sub_part.name[:40]}")
        items.delete()

# --- 2. two parts that do not exist yet
cat_pcb = PartCategory.objects.filter(name__iexact="Electronics").first() or PartCategory.objects.filter(parent=None).first()
pcb, made = Part.objects.get_or_create(
    name="HoT Info Orbs PCB v1.1",
    defaults=dict(category=cat_pcb, component=True, purchaseable=True, assembly=False,
                  description="Bare 2-layer carrier PCB, 198.8 x 28.5mm, ESP32-S3 SuperMini + 5x GC9A01. JLCPCB, git tag v1.1-run1"[:250]))
print(f"\n   PCB part #{pcb.pk} {'created' if made else 'exists'}")
if made:
    pcb.notes = ("Ordered from JLCPCB 2026-08-29, quantity 10, from git tag `v1.1-run1`.\n\n"
                 "**Quantity 10 is the ORDERED figure, not a physical count.** Nobody has "
                 "counted the delivered boards. Correct it at the next stocktake.\n\n"
                 "Gerbers: hot-info-orbs repo, hardware/hot-info-orbs/fab/")
    pcb.save()

sock, made_s = Part.objects.get_or_create(
    name="Header Socket 1x7 Female 0.1in",
    defaults=dict(category=cat_pcb, component=True, purchaseable=True, assembly=False,
                  description="1x7 female header, 2.54mm pitch, for GC9A01 display modules"[:250]))
print(f"   socket part #{sock.pk} {'created' if made_s else 'exists'}")
if made_s:
    sock.notes = ("Used 5-per-board on the HoT Info Orbs carrier to socket the display modules.\n\n"
                  "**Not counted.** Created 2026-09-10 so BO-0016 could describe the build "
                  "honestly; quantity on hand is unknown and no stock row has been added.")
    sock.save()

# --- 3. the BOM as actually built
WANT = [
    (60,  1, "AITRIP ESP32-S3 SuperMini"),
    (418, 5, "GC9A01 1.28in round display"),
    (826, 3, "Adafruit 6mm tactile"),
    (687, 1, "220uF 10V electrolytic"),
    (pcb.pk, 1, "the carrier PCB"),
    (sock.pk, 5, "1x7 female header"),
]
print("\n   BOM:")
keep = set()
for pk, qty, why in WANT:
    sub = Part.objects.get(pk=pk)
    bi, created = BomItem.objects.get_or_create(part=asm, sub_part=sub, defaults={"quantity": qty})
    if not created and bi.quantity != qty:
        BomItem.objects.filter(pk=bi.pk).update(quantity=qty); bi.refresh_from_db()
    keep.add(bi.pk)
    print(f"      {qty}x #{sub.pk:5} {sub.name[:44]:44} {'added' if created else 'kept'}")
for stale in BomItem.objects.filter(part=asm).exclude(pk__in=keep):
    print(f"      REMOVED  #{stale.sub_part.pk} {stale.sub_part.name[:44]} (not used in this build)")
    stale.delete()

b.refresh_from_db()
BuildLine.objects.filter(build=b).delete()
b.create_build_line_items()
print(f"\n   build lines rebuilt: {BuildLine.objects.filter(build=b).count()}")
