"""Allocate what was actually soldered, and correct two stale records on #418."""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part
from build.models import Build, BuildLine, BuildItem
from stock.models import StockItem, StockLocation

b = Build.objects.get(reference="BO-0016")

# the PCB has no stock row yet - create one from the JLCPCB delivery
pcb = Part.objects.get(name="HoT Info Orbs PCB v1.1")
if not StockItem.objects.filter(part=pcb).exists():
    loc = StockLocation.objects.filter(name__iexact="SLN").first() or StockLocation.objects.filter(parent=None).first()
    si = StockItem.objects.create(part=pcb, quantity=10, location=loc)
    StockItem.objects.filter(pk=si.pk).update(
        notes="JLCPCB delivery for git tag v1.1-run1. Quantity 10 is the ORDERED figure, not a physical count.")
    print(f"   PCB stock row created: 10 @ {loc.name if loc else '?'}  (ordered qty, NOT counted)")

print("\n   allocating:")
for line in BuildLine.objects.filter(build=b):
    sub = line.bom_item.sub_part
    need = float(line.bom_item.quantity)
    got = 0.0
    for si in StockItem.objects.filter(part=sub).order_by("pk"):
        if got >= need: break
        free = float(si.unallocated_quantity())
        if free <= 0: continue
        take = min(free, need - got)
        BuildItem.objects.get_or_create(build_line=line, stock_item=si, defaults={"quantity": take})
        got += take
    short = need - got
    print(f"      #{sub.pk:5} {sub.name[:42]:42} need {need:g}  allocated {got:g}"
          + (f"   << SHORT {short:g}" if short > 0 else ""))

# --- correct #418: brand in the name is wrong for this stock, and 3.3V is wrong
d = Part.objects.get(pk=418)
Part.objects.filter(pk=418).update(
    description="1.28in round TFT LCD, GC9A01 driver, 240x240 IPS, 4-wire SPI. Onboard regulator: runs from 5V VCC with 3.3V logic - verified in the HoT Info Orbs build 2026-09-10.")
d.refresh_from_db()
note = ("\n\n**2026-09-10 — two corrections.** The stock on hand came from AliExpress "
        "(PO-0148, PO-0149) despite the HiLetgo brand in the part name; treat the name as "
        "the form factor, not the maker. And the earlier '3.3V' description was wrong for "
        "this build: these carry an onboard regulator, and five of them run from a 5V bus "
        "with 3.3V logic in BO-0016. That is the whole reason the ESP32-S3 does not overheat.")
Part.objects.filter(pk=418).update(notes=(d.notes or "") + note)
d.refresh_from_db()
print(f"\n   #418 description now: {d.description[:96]}...")
print(f"   #418 notes end: ...{d.notes[-70:].strip()}")
