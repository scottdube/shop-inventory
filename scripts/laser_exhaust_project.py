"""Laser Exhaust Auto-Start project: assembly Part + BOM + Build order, claim what's on hand.

Designed 2026-09-30, parked (Scott: "not sure when I'll get to it"). The design
lives in sln-ha-config/docs/laser-exhaust-autostart-build.md; the part's notes
carry the short form so the record stands on its own.

Allocates by BOM allocation, not by moving parts into a project bin — the shelf
keeps saying where a spare lives, the build says what is committed. The SuperMini
is allocated from the SLN row explicitly: the first row by pk is at LRD, and the
diverter is at SLN.

    itq run scripts/laser_exhaust_project.py            # dry run
    itq run scripts/laser_exhaust_project.py --commit
"""
import argparse, os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model
from django.db import transaction
from part.models import Part, PartCategory, BomItem
from build.models import Build, BuildLine, BuildItem
from stock.models import StockItem

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

NAME = "Laser Exhaust Auto-Start"
DESC = ("Starts the inline booster fan on the shared P2S/F1 Ultra duct when either "
        "laser draws power; senses which way the duct diverter is set. PARKED.")
NOTES = """**PARKED — designed 2026-09-30, not started.** Full design: `sln-ha-config/docs/laser-exhaust-autostart-build.md`.

**Setup:** P2S + F1 Ultra share one duct with a manual diverter (pulls through one or the other, never both) and a 120 V plug-in inline booster fan. Each laser keeps its own built-in exhaust fan, so a failure here loses the boost, not the extraction.

**Design:** ESPHome power-monitoring plug on each laser + one on the fan; HA turns the fan on when either laser is over threshold ~10 s, off 5 min after both are idle. TLV493D + magnet on the diverter flap reports its position; alert (glyph, not color) when a running laser is not the one the diverter is set to.

**Measure first (Kill A Watt, RB-11):** P2S idle / engrave / cut watts; fan watts; **does the fan restart at its set speed after unplug/replug?** — if not, plug switching won't work.

**Not yet:** magnet for the flap (none recorded), the 3 plugs (0 on hand). Diverter servo deferred until the diverter is actually found set wrong.
"""

# (part pk, qty, stock row to take from or None, why)
BOM = [
    (1257, 3, None, "Athom ESPHome power plug: P2S, F1 Ultra, booster fan"),
    (809,  1, 210,  "TLV493D 3-axis Hall: diverter flap position"),
    (60,   1, 79,   "ESP32-S3 SuperMini for the diverter sensor (SLN row)"),
]

user = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
cat = PartCategory.objects.get(name="Projects", parent=None)

existing = Part.objects.filter(name=NAME).first()
print(f"assembly: {'#%d exists' % existing.pk if existing else 'would create'}")
last = Build.objects.order_by("-reference_int").first()
nxt = last.reference_int + 1
assert last.reference == f"BO-{last.reference_int:04d}", f"reference_int diverged on {last.reference}"
print(f"next build reference: BO-{nxt:04d} (last {last.reference})")
for pk, qty, row, why in BOM:
    p = Part.objects.get(pk=pk)
    free = sum(s.unallocated_quantity() for s in StockItem.objects.filter(part=p))
    print(f"  BOM {qty}x #{pk} {p.name[:44]:44} free={free:g}  {why}")
if not a.commit:
    print("\nDRY RUN — nothing written"); sys.exit()

with transaction.atomic():
    asm, created = Part.objects.get_or_create(
        name=NAME, defaults=dict(category=cat, assembly=True, component=False,
                                 purchaseable=False, description=DESC[:250]))
    Part.objects.filter(pk=asm.pk).update(notes=NOTES)
    lines = []
    for pk, qty, row, why in BOM:
        sub = Part.objects.get(pk=pk)
        bom, _ = BomItem.objects.get_or_create(part=asm, sub_part=sub,
                                               defaults={"quantity": qty, "note": why[:500]})
        lines.append((bom, sub, qty, row))
    build = Build.objects.filter(part=asm).first()
    if not build:
        build = Build.objects.create(part=asm, quantity=1, reference=f"BO-{nxt:04d}",
                                     title="Laser exhaust auto-start - parked", issued_by=user)
    if not BuildLine.objects.filter(build=build).exists():
        build.create_build_line_items()
    for bom, sub, need, row in lines:
        if row is None:
            continue
        line = BuildLine.objects.get(build=build, bom_item=bom)
        si = StockItem.objects.get(pk=row, part=sub)
        BuildItem.objects.get_or_create(build_line=line, stock_item=si,
                                        defaults={"quantity": min(need, si.unallocated_quantity())})

# verify by re-reading, never trust the write
asm = Part.objects.get(name=NAME)
build = Build.objects.get(part=asm)
print(f"\nverify: part #{asm.pk} assembly={asm.assembly} cat={asm.category.name} notes={len(asm.notes or '')} chars")
print(f"build {build.reference} reference_int={build.reference_int} status={build.status} '{build.title}'")
for bom in BomItem.objects.filter(part=asm):
    line = BuildLine.objects.filter(build=build, bom_item=bom).first()
    alloc = sum(bi.quantity for bi in BuildItem.objects.filter(build_line=line)) if line else 0
    rows = ", ".join(f"#{bi.stock_item.pk}@{bi.stock_item.location.name if bi.stock_item.location else '-'}"
                     for bi in BuildItem.objects.filter(build_line=line)) if line else ""
    print(f"  #{bom.sub_part.pk:4} {bom.sub_part.name[:40]:40} need {bom.quantity:g} allocated {alloc:g} {rows}")
