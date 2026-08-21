"""Dissolve the SparkFun beginners kit into the B3 category drawers.

The box is heavily depleted (Scott, 2026-08-21) and was taking bench space to
hold a handful of parts, each of which has peers already filed in B3. Kits
earn their keep as locations when they answer "do I have a 4.7k?" without
unpacking; a mostly-empty box answers nothing and costs a surface.

This script does the part of the job that does not need a count: merging the
duplicate records the kit created, and giving every surviving part a home in
the drawer where its peers already live. Stock quantities land separately,
from a physical count, so they carry a real stocktake date.

Three records for one 555: the kit added `IC 555 Timer`, and `#16 NE555P
Precision Timer DIP-8` (qty 0, no home) already duplicated `#796 NE555P Timer
IC, DIP-8` (qty 12, B3-R3C1) before the kit was ever entered. #16 is not the
kit's fault and is merged here because it surfaced here.

LED colours merge into the *Clear* records per Scott. Yellow is deliberately
NOT merged into `LED 5mm Amber Clear` — amber and yellow may or may not be the
same part, colour is identity for an LED, and nobody has had both in hand at
once. It gets the same drawer and a note saying so.

    itq run scripts/dissolve_sparkfun.py            # dry run
    itq run scripts/dissolve_sparkfun.py --commit
"""
import argparse, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part
from stock.models import StockItem, StockLocation
from company.models import SupplierPart

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

KIT = 469

# loser -> (keeper, why)
MERGES = {
    706: (796, "the kit listed a generic '555 Timer'; the shop already stocks "
               "NE555P DIP-8 at B3-R3C1"),
    16:  (796, "duplicate NE555P record with no stock and no home, predating "
               "the kit — found while dissolving it"),
    707: (762, "kit LED record carried no clear/diffused distinction; Scott "
               "confirmed 2026-08-21 these are clear"),
    709: (764, "kit LED record carried no clear/diffused distinction; Scott "
               "confirmed 2026-08-21 these are clear"),
}

# part -> (drawer pk, drawer name, why this drawer)
HOMES = {
    696: (305, "B3-R2C4", "diode drawer"),
    697: (305, "B3-R2C4", "diode drawer"),
    698: (326, "B3-R5C1", "empty drawer opened for headers"),
    699: (326, "B3-R5C1", "empty drawer opened for headers"),
    703: (310, "B3-R3C1", "DIP IC drawer"),
    708: (304, "B3-R2C3", "clear 5mm LED drawer"),
    710: (303, "B3-R2C2", "misc LED / display drawer"),
    711: (325, "B3-R4C8", "sensor drawer"),
    # NOT B3-R3C2: it reads as empty only because it has no StockItem rows.
    # Its description says it holds the SMD bridge rectifier kit and "takes
    # the kit bag and not much else". R5C2 says VERIFIED EMPTY.
    704: (327, "B3-R5C2", "verified-empty large drawer opened for regulators"),
    705: (327, "B3-R5C2", "verified-empty large drawer opened for regulators"),
    700: (297, "B3-R1C4", "switch row"),
    701: (296, "B3-R1C3", "6mm tactile / power button drawer"),
    702: (319, "B3-R4C2", "potentiometer drawer"),
    # The four ceramics were only ever homed at the kit because the kit list
    # named them. Their loose bags live at A3-R8C3 and were counted there.
    688: (197, "A3-R8C3", "counted loose bags live here"),
    689: (197, "A3-R8C3", "counted loose bags live here"),
    690: (197, "A3-R8C3", "counted loose bags live here"),
    691: (197, "A3-R8C3", "counted loose bags live here"),
}

YELLOW_NOTE = (
    "\n\n**Possible duplicate of #763 LED 5mm Amber Clear** — filed in the same "
    "drawer (B3-R2C3) but deliberately not merged on 2026-08-21. Amber and "
    "yellow may be the same part; colour is identity for an LED and nobody has "
    "had both in hand at once. Resolve by comparing two of them, not from a "
    "catalog."
)

fail = []


def verify(label, ok, detail=""):
    print(f'  {"ok  " if ok else "FAIL"} {label}' + (f'  ({detail})' if detail else ""))
    if not ok:
        fail.append(label)


print("=== merges ===")
for loser_pk, (keeper_pk, why) in MERGES.items():
    loser = Part.objects.filter(pk=loser_pk).first()
    keeper = Part.objects.filter(pk=keeper_pk).first()
    if not loser or not keeper:
        print(f"  SKIP #{loser_pk} -> #{keeper_pk}: part missing")
        continue
    if not loser.active:
        print(f"  have #{loser_pk} already inactive")
        continue
    n_stock = StockItem.objects.filter(part=loser).count()
    print(f"  #{loser_pk} {loser.name[:34]:34} -> #{keeper_pk} {keeper.name[:34]:34} "
          f"({n_stock} stock items to move)")
    if not a.commit:
        continue
    StockItem.objects.filter(part=loser).update(part=keeper)
    SupplierPart.objects.filter(part=loser).update(part=keeper)
    keeper.notes = ((keeper.notes or "").rstrip() +
                    f"\n\nAbsorbed part #{loser_pk} ({loser.name}) on 2026-08-21 "
                    f"— {why}.").strip()
    keeper.save()
    loser.active = False
    loser.notes = ((loser.notes or "").rstrip() +
                   f"\n\n**MERGED** into #{keeper_pk} {keeper.name} on "
                   f"2026-08-21 — {why}.").strip()
    loser.name = f"{loser.name} [merged {loser_pk}]"[:100]
    loser.save()

print("\n=== homes ===")
for pk, (loc_pk, loc_name, why) in HOMES.items():
    p = Part.objects.filter(pk=pk).first()
    if not p:
        print(f"  SKIP #{pk}: part missing")
        continue
    cur = p.default_location
    print(f"  #{pk:4} {p.name[:40]:40} {cur.name if cur else '-':>10} -> {loc_name}  ({why})")
    if not a.commit:
        continue
    loc = StockLocation.objects.get(pk=loc_pk)
    p.default_location = loc
    if pk == 708 and "Possible duplicate of #763" not in (p.notes or ""):
        p.notes = ((p.notes or "").rstrip() + YELLOW_NOTE).strip()
    p.save()

if not a.commit:
    print("\nDRY RUN")
    sys.exit(0)

# ---- verify by re-reading; .save() has silently no-opped on this install ----
print("\n=== verify ===")
for loser_pk, (keeper_pk, _) in MERGES.items():
    loser = Part.objects.filter(pk=loser_pk).first()
    if loser is None:
        continue
    verify(f"#{loser_pk} deactivated", loser.active is False,
           f"active={loser.active}")
    verify(f"#{loser_pk} has no stock left",
           not StockItem.objects.filter(part_id=loser_pk).exists())

for pk, (loc_pk, loc_name, _) in HOMES.items():
    p = Part.objects.filter(pk=pk).first()
    if p is None:
        continue
    got = p.default_location_id
    verify(f"#{pk} home = {loc_name}", got == loc_pk,
           f"default_location_id={got}")

y = Part.objects.filter(pk=708).first()
if y:
    verify("#708 carries the amber/yellow caveat",
           "Possible duplicate of #763" in (y.notes or ""))

still = Part.objects.filter(default_location_id=KIT, active=True).count()
verify(f"no active part still homed at the kit", still == 0, f"{still} remain")

print()
if fail:
    print(f"VERIFY FAILED on {len(fail)}:")
    for f in fail:
        print(f"  {f}")
    sys.exit(1)
print("WROTE and verified: merges and homes all confirmed by re-read")
