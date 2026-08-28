"""Undo a wrong claim: BO-0016 allocated the Waveshare display, which is not the
part this build will use. Release it; leave the BOM line flagged pending the
real part choice."""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from build.models import Build, BuildLine, BuildItem
from stock.models import StockItem
from part.models import Part

b = Build.objects.get(reference="BO-0016")
wave = Part.objects.get(pk=70)

line = BuildLine.objects.filter(build=b, bom_item__sub_part=wave).first()
items = BuildItem.objects.filter(build_line=line)
print(f"releasing {items.count()} allocation(s) of #{wave.pk} {wave.name[:40]}")
for bi in items:
    print(f"   stock item {bi.stock_item.pk}: {bi.quantity:g}")
items.delete()

note = ("\n\n**Display part is NOT settled (2026-08-27).** The BOM line points at "
        "part #70 (Waveshare, $20.59) only because it was the sole GC9A01 in "
        "stock when this build was created — it was never the intended module "
        "and its allocation has been released. The plan is generic GC9A01 "
        "clones from AliExpress. Two things to confirm on the actual module "
        "before ordering five: whether it carries an onboard AMS1117 (which "
        "makes 5V VCC safe and takes the load off the ESP32 regulator), and "
        "whether it is the 7-pin variant or an 8-pin with BL broken out. "
        "Note part #418 (HiLetgo generic) is recorded as 3.3V only, so this "
        "genuinely varies between modules.")
Build.objects.filter(pk=b.pk).update(notes=(b.notes or "") + note)

b.refresh_from_db()
print(f"\nverify: notes now {len(b.notes)} chars, ends: ...{b.notes[-60:].strip()}")
free = sum(s.unallocated_quantity() for s in StockItem.objects.filter(part=wave))
total = sum(s.quantity for s in StockItem.objects.filter(part=wave))
print(f"verify: #{wave.pk} now {total:g} in stock, {free:g} available (was 1 in stock, 0 available)")
