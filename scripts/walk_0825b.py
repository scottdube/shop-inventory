"""Red Bin walk, 2026-08-25: RB-20, and two corrections from Scott.

RB-20 holds three eBay SMD soldering practice kits. Scott expected to find
them in the catalogue; they are not there, and nothing close is -- the whole
eBay history is two supplier parts, which is the unknown-vendor blind spot
showing up as a missing part rather than a missing order.

Also records where the FX-951 tips actually live (BL-D1), and that RB-14 holds
more than the five rows filed against it.
"""
import os, sys, django
from datetime import date
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model
from part.models import Part, PartCategory
from stock.models import StockItem, StockLocation

COMMIT = "--commit" in sys.argv
TODAY = date.today()
user = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()

NAME = "Soldering Practice Kit, SMD components + BOM card (eBay)"
DESC = ("SMD soldering practice kit, sealed bag: cut-tape 0805/SOT23/LL34 parts "
        "plus a 16-line BOM card (10K, 2M, 1N4148, red and blue SMD LEDs, SMD "
        "transistors). Lot GYCQ0004-002 / A21-53-B-07, 2023-11-09. READ FROM "
        "PHOTOGRAPH - listing title unknown.")
NOTE = (
    f"Counted at 3 by Scott {TODAY} during the Red Bin walk - three sealed bags "
    "in RB-20, his figure, not a divided or purchased one.\n\n"
    "IDENTITY read from a photograph of one bag, so it is identity only: the "
    "BOM card lists rows 8-16 in 0805, SOT23 and LL34, with 10K, 2M, 1N4148, "
    "red and blue SMD LEDs and SMD transistors, quantities 1-4 each. Vendor lot "
    "label GYCQ0004-002 / A21-53-B-07, printed 2023-11-09 13:33:08.\n\n"
    "WHETHER A PRACTICE PCB IS INCLUDED IS NOT ESTABLISHED. The photograph "
    "shows the component bag only; a practice kit normally ships a board, and "
    "if one is in RB-20 it has not been seen. Do not assume either way.\n\n"
    "NOT IN THE CATALOGUE BEFORE TODAY. Searched by name, description, supplier "
    "SKU and PO line before creating this: nothing matched, and eBay carries "
    "only two supplier parts in the whole instance. The eBay listing title is "
    "still wanted - it is the string a future duplicate would arrive under."
)

# --- the part -------------------------------------------------------------
dupes = Part.objects.filter(name__icontains="practice")
print(f"duplicate check: {dupes.count()} part(s) matching 'practice'")
for p in dupes:
    print(f"  #{p.pk} {p.name}")

part = Part.objects.filter(name=NAME).first()
print(f"\npart: {'EXISTS #'+str(part.pk) if part else 'would create'} {NAME!r}")
print(f"  category: Consumables/Solder")
print(f"  desc ({len(DESC)}): {DESC}")

DESCS = {
    "BL-D1": ("FX-951 SOLDERING TIPS live here - Scott, 2026-08-25, asked where "
              "the station's tips are. NOT COUNTED and the specific parts are "
              "not yet pinned: #333 (T15, correct for the FM-2027 handpiece) and "
              "#160 (T12) both sit at zero stock with no rows, and 'the tips' "
              "could be either or both. Open the drawer and count before "
              "writing rows. NOTE: Hakko never states T12 fits the FM-2027."),
    "RB-20": ("THREE SOLDERING PRACTICE KITS, eBay, sealed bags of SMD parts "
              "with a BOM card. Counted at 3 by Scott 2026-08-25. Whether a "
              "practice PCB is in the bin has NOT been established - only the "
              "component bag was seen."),
}

print()
for name, d in DESCS.items():
    loc = StockLocation.objects.get(name=name)
    print(f"{name}: {len(d)} chars")

rb14 = StockLocation.objects.get(name="RB-14")
RB14_ADD = (" ALSO IN THIS BIN, NOT IN ITS FIVE ROWS: a jig (labelled \"JIG DONT "
            "TOSS OUT\") and other loose contents. Scott, 2026-08-25: the jig is "
            "part of this bin's group. So RB-14 reading '5 rows, 5 counted' means "
            "the ROWS are counted, NOT that the bin is fully recorded.")
print(f"RB-14: append {len(RB14_ADD)} -> {len(rb14.description) + len(RB14_ADD)} chars")

if not COMMIT:
    print("\n  DRY RUN - add --commit")
    sys.exit()

if part is None:
    part = Part.objects.create(
        name=NAME, description=DESC,
        category=PartCategory.objects.get(pathstring="Consumables/Solder"),
        purchaseable=True, component=False, active=True)
    print(f"\ncreated part #{part.pk}")

rb20 = StockLocation.objects.get(name="RB-20")
if StockItem.objects.filter(part=part).exists():
    sys.exit("stock row already exists - look first")
si = StockItem.objects.create(part=part, location=rb20, quantity=3, notes=NOTE)
# stocktake() only stamps when something CHANGES, so write the stamp directly.
StockItem.objects.filter(pk=si.pk).update(stocktake_date=TODAY, stocktake_user=user)

for name, d in DESCS.items():
    StockLocation.objects.filter(name=name).update(description=d)
StockLocation.objects.filter(pk=rb14.pk).update(description=rb14.description + RB14_ADD)

# --- verify ---------------------------------------------------------------
si = StockItem.objects.get(pk=si.pk)
ok = (si.quantity == 3 and si.location.name == "RB-20" and si.stocktake_date == TODAY)
print(f"\nstock #{si.pk} qty={si.quantity:g} @ {si.location.pathstring} "
      f"stocktake={si.stocktake_date} -> {'OK' if ok else 'MISMATCH'}")
for name, d in DESCS.items():
    got = StockLocation.objects.get(name=name).description
    print(f"  {name}: {'OK' if got == d else 'MISMATCH'}")
got14 = StockLocation.objects.get(pk=rb14.pk).description
print(f"  RB-14: {'OK' if got14.endswith(RB14_ADD) else 'MISMATCH'} ({len(got14)} chars)")
