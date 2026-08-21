"""File the SparkFun switches — and unpick a merge that footprint disproved.

3 PCB-mount slide switches to B3-R1C5 (Scott chose C5 over the toggle drawer
C4: same size class, but C5 holds one part and has the room).

The tactiles are the interesting part. They measured 6x6mm, so #701 was merged
into #738 `Tactile Switch 6x6mm SPST` as a measured match. Scott then looked
underneath: **the SparkFun ones have four legs; the ones already in R1C3 have
two.** A 2-pin and a 4-pin tactile switch do not share a PCB footprint, so they
are different parts under this shop's first rule about part identity. The merge
is reversed here and they become their own record, in the same drawer — Scott:
"it's a good location, just a different description."

Body size was the wrong discriminator to stop at. 6x6mm names the *envelope*;
what a board needs is the pin pattern, and that is only visible from the
underside. Asking for the measurement was right; asking for only one
measurement was not.

Idempotent: safe to re-run.

    itq run scripts/sparkfun_switches.py            # dry run
    itq run scripts/sparkfun_switches.py --commit
"""
import argparse, os, sys, django
from datetime import date

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part
from stock.models import StockItem, StockLocation

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

R1C3, R1C5 = 296, 298
today = date.today()

# Text this script's earlier, wrong version wrote. Removed rather than left to
# contradict the record.
BAD_KEEPER = ("\n\nAbsorbed part #701 (SparkFun 'Switch Push Button') on "
              "2026-08-21. Measured 6x6mm in hand and confirmed PCB mount, so "
              "this is a measured match, not one inherited from the kit list.")
BAD_STOCK = ("\n\nCounted 2026-08-21: 50 + 2 absorbed from the SparkFun "
             "beginners kit = 52.")
BAD_LOSER = ("\n\n**MERGED** into #738 Tactile Switch 6x6mm SPST on 2026-08-21 "
             "— measured 6x6mm PCB mount, same part.")

keeper = Part.objects.get(pk=738)
loser = Part.objects.get(pk=701)

print("=== reverse the 6x6 tactile merge ===")
print(f"  #738 {keeper.name}: strip absorbed note, qty back to 50")
print(f"  #701 {loser.name}: reactivate as a 4-pin record, 2 at B3-R1C3")

print("\n=== slide switches ===")
slide = Part.objects.get(pk=700)
ss = StockItem.objects.filter(part=slide).first()
print(f"  #700 {slide.name}: qty {ss.quantity if ss else 0} at "
      f"{ss.location.name if ss and ss.location else '-'} (target B3-R1C5)")

if not a.commit:
    print("\nDRY RUN")
    sys.exit(0)

# ---- 1. slide switches to R1C5 ----
c5 = StockLocation.objects.get(pk=R1C5)
if ss and ss.location_id != R1C5:
    ss.location = c5
    ss.save()
if ss:
    ss.stocktake_date = today
    ss.save()
if slide.default_location_id != R1C5:
    slide.default_location = c5
    slide.save()
if "Filed to B3-R1C5" not in (slide.notes or ""):
    slide.notes = ((slide.notes or "").rstrip() +
        "\n\nFiled to B3-R1C5 rather than the toggle drawer B3-R1C4: Scott, "
        "2026-08-21, looking at both — C5 holds one part and has the room, C4 "
        "already holds four toggle types.").strip()
    slide.save()

# ---- 2. undo the merge on #738 ----
keeper.notes = (keeper.notes or "").replace(BAD_KEEPER, "")
if "2-pin" not in (keeper.notes or ""):
    keeper.notes = ((keeper.notes or "").rstrip() +
        "\n\n**2-pin.** Checked at the drawer 2026-08-21. The 4-pin 6x6mm "
        "tactiles from the SparkFun kit are #701, filed in the same drawer — "
        "same envelope, different footprint, do not substitute.").strip()
keeper.save()

ks = StockItem.objects.filter(part=keeper, location_id=R1C3).first()
if ks:
    ks.notes = (ks.notes or "").replace(BAD_STOCK, "")
    ks.quantity = 50
    ks.stocktake_date = today
    ks.save()

# ---- 3. restore #701 as its own 4-pin record ----
loser.notes = (loser.notes or "").replace(BAD_LOSER, "")
loser.name = "Tactile Switch 6x6mm 4-pin"
loser.description = ("6x6mm through-hole tactile switch, 4-pin PCB mount")[:250]
loser.active = True
loser.default_location = StockLocation.objects.get(pk=R1C3)
if "four legs" not in (loser.notes or ""):
    loser.notes = ((loser.notes or "").rstrip() +
        "\n\n**4-pin**, confirmed by Scott 2026-08-21 with the part in hand. "
        "Briefly merged into #738 Tactile Switch 6x6mm SPST that day on a 6x6mm "
        "body match; reversed on discovering #738 is 2-pin. Same envelope, "
        "different PCB footprint. From the SparkFun beginners kit.").strip()
loser.save()

ls = StockItem.objects.filter(part=loser, location_id=R1C3).first()
if not ls:
    ls = StockItem.objects.create(part=loser, location_id=R1C3, quantity=2)
ls.quantity = 2
ls.stocktake_date = today
ls.save()

# ---- verify ----
print("\n=== verify ===")
fail = []


def chk(label, ok, detail=""):
    print(f'  {"ok  " if ok else "FAIL"} {label}' + (f"  ({detail})" if detail else ""))
    if not ok:
        fail.append(label)


s = StockItem.objects.filter(part_id=700).first()
chk("#700 slide x3 at B3-R1C5",
    s and s.location_id == R1C5 and int(s.quantity) == 3,
    f"{s.location.name if s else None} qty={s.quantity if s else None}")

k = Part.objects.get(pk=738)
ks = StockItem.objects.filter(part_id=738, location_id=R1C3).first()
chk("#738 back to 50", ks and int(ks.quantity) == 50, f"qty={ks.quantity if ks else None}")
chk("#738 absorbed note removed", "Absorbed part #701" not in (k.notes or ""))
chk("#738 marked 2-pin", "2-pin" in (k.notes or ""))

l = Part.objects.get(pk=701)
ls = StockItem.objects.filter(part_id=701, location_id=R1C3).first()
chk("#701 active again", l.active is True)
chk("#701 renamed 4-pin", l.name == "Tactile Switch 6x6mm 4-pin", l.name)
chk("#701 no stale MERGED note", "**MERGED**" not in (l.notes or ""))
chk("#701 qty 2 at B3-R1C3, stamped",
    ls and int(ls.quantity) == 2 and ls.stocktake_date == today,
    f"qty={ls.quantity if ls else None} date={ls.stocktake_date if ls else None}")

print()
if fail:
    print(f"VERIFY FAILED on {len(fail)}: " + "; ".join(fail))
    sys.exit(1)
print("WROTE and verified")
