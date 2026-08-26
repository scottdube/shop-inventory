"""Stand up the LINEAR MOTION bin on WS2-S4, and point the homeless McMaster
motion parts at it WITHOUT claiming they are in it.

Scott 2026-08-26: two MGN9 rails off the wire shelves, ~200 mm, plus "a bunch
of bearings" he is gathering now; put them in one bucket together.

THE ONE THING THIS SCRIPT DELIBERATELY DOES NOT DO is file the McMaster
Mechanical rows into the bin. Those 9 rows have location=NULL, which means
nobody knows where the parts physically are -- setting a location would be
exactly the error that produced stock 573/574 in August: an allocation made on
paper, by plan, with nobody carrying anything. That reads as a fact afterwards
and is not one.

So the split is:
  default_location = the bin   -> a statement of INTENT. This is where the part
                                  goes home. True the moment it is decided.
  location         = untouched -> a statement of FACT. Stays NULL until Scott
                                  physically puts the part in the bucket.

Only the MGN9 rails get a real stock row here, because those are in his hand.
"""
import argparse, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model
from part.models import Part
from stock.models import StockItem, StockLocation

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

SHELF = 456      # SLN/Storage/WS2/WS2-S4
CAT = 137        # Mechanical
BIN_PART = 1089  # Storage Bins, 6 Quart

BIN_DESC = (
    "LINEAR MOTION & BEARINGS. Linear rails and carriages, plain and rolling "
    "bearings, shaft collars, rod ends, sprockets. Sterilite 6qt clear, "
    "snap-on lid, on WS2-S4. A HOME -- things filed here get it as "
    "default_location. The BIN is the location and the name travels WITH the "
    "bin, so moving it to another shelf is a re-parent, not a rename. "
    "Established 2026-08-26."
)

BIN_NOTES = (
    "**Several parts name this bin as their home but are NOT in it yet.**\n\n"
    "The McMaster mechanical import was catalogued and never filed: 9 motion "
    "rows carry location=NULL, meaning owned, physical whereabouts unknown. "
    "They now have this bin as default_location -- that is where they GO, not "
    "where they ARE. Their stock rows stay unlocated until somebody carries "
    "them here and files them.\n\n"
    "Do not 'tidy' that by setting their location to this bin. Allocating "
    "stock to a place by plan, with nobody carrying anything, is what produced "
    "the two unlocated SHT31 rows in August and cost a bench search.\n\n"
    "MATCHED SETS: the needle-roller thrust bearings (#1021 3/8\", #1018 7/8\") "
    "each have their own washers (#1022, #1019). File them touching. Separated, "
    "the washers are anonymous shims and the bearings are incomplete.\n\n"
    "STILL OPEN 2026-08-26: whether the 6.25in V-belt pulley (#1026), the 62in "
    "V-belt (#1027) and the five springs belong here. The pulley and belt would "
    "each eat a large share of a 6qt on their own."
)

RAIL = (
    "Linear Rail MGN9, 200 mm, with carriage",
    "Miniature linear guide, MGN9 profile -- 9 mm rail width, measured across "
    "the rail with calipers. ~200 mm long. Steel rail with a recirculating-ball "
    "carriage. Bought as a 2-pack.",
    "MEASURED 2026-08-26 by Scott: 9 mm across the rail, so MGN9 and not MGN12 "
    "or MGN15. The bag label was truncated at exactly the character that "
    "mattered -- '[2 Pack] MGN..nd CNC Machine' -- so the size came off "
    "calipers, not off the packaging.\n\n"
    "LENGTH ~200 mm is Scott's eye estimate ('I would say two hundred'), not a "
    "measurement. Rail length sets what it can be built into, so put a tape on "
    "it before designing around it.\n\n"
    "BLOCK TYPE NOT CONFIRMED: MGN9C (short) vs MGN9H (long) is unknown. They "
    "are not interchangeable for load or for mounting-hole spacing.\n\n"
    "Bag label SKU X0034UMO0N, 'Made in China'. No purchase order in this "
    "system matches it -- vendor and date unknown, so none is claimed here.",
    2,
)

# The 9 unambiguous motion parts from the unfiled McMaster import.
ADOPT = [1021, 1018, 1022, 1019, 1041, 1005, 1010, 1011, 1042]

ADOPT_NOTE = (
    "\n\n2026-08-26: default_location set to SLN/Storage/WS2/WS2-S4/Linear "
    "Motion. That is where this part GOES, not where it IS -- its stock row is "
    "still unlocated, because the McMaster import catalogued it and nobody ever "
    "filed it. The row gets a location when a person carries the part to the "
    "bin, and not before."
)

user = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
shelf = StockLocation.objects.get(pk=SHELF)
existing = StockLocation.objects.filter(name="Linear Motion", parent=shelf).first()
print(f"shelf: {shelf.pathstring}")
print(f"bin:   {'EXISTS ' + str(existing.pk) if existing else 'to create'}")
print(f"rail:  {RAIL[3]} x {RAIL[0]}")
print(f"adopt: {len(ADOPT)} parts get default_location, stock rows UNTOUCHED")
for pk in ADOPT:
    p = Part.objects.filter(pk=pk).first()
    n = StockItem.objects.filter(part=p, location__isnull=True).count()
    print(f"   [{pk}] {p.name[:58]:<58} unlocated rows: {n}")

if not a.commit:
    print("\nDRY RUN -- add --commit")
    sys.exit()

binloc = existing or StockLocation.objects.create(
    name="Linear Motion", parent=shelf, description=BIN_DESC)
# StockLocation has no `notes` field -- only `description`, and it is not
# length-validated on a queryset update. The existing Air System and B-01
# bins carry their whole write-up there too, so this matches the house shape.
StockLocation.objects.filter(pk=binloc.pk).update(description=BIN_DESC + "\n\n" + BIN_NOTES)
print(f"\nlocation [{binloc.pk}] {binloc.pathstring}")

stack = StockItem.objects.filter(part_id=BIN_PART).first()
if stack and "Linear Motion" not in (stack.notes or ""):
    stack.take_stock(1, user, notes="One bin taken to become the LINEAR MOTION bin on WS2-S4, 2026-08-26.")
    stack.refresh_from_db()
    StockItem.objects.filter(pk=stack.pk).update(
        notes=(stack.notes or "").rstrip() +
        "\n\n2026-08-26: one bin consumed to become the LINEAR MOTION bin on WS2-S4.")

name, desc, notes, qty = RAIL
rail = Part.objects.filter(name=name).first()
if not rail:
    rail = Part.objects.create(name=name, description=desc, category_id=CAT,
                               default_location=binloc, purchaseable=True, active=True)
    print(f"part [{rail.pk}] {name}")
Part.objects.filter(pk=rail.pk).update(notes=notes, default_location=binloc)
if not StockItem.objects.filter(part=rail, location=binloc).exists():
    si = StockItem.objects.create(part=rail, location=binloc, quantity=qty)
    StockItem.objects.filter(pk=si.pk).update(notes=(
        "TALLIED. Two rails, in hand, stated by Scott and matching the bag's "
        "'[2 Pack]'. Carriages: one is mounted on each rail; there is at least "
        "one more loose block in the white bag and the TOTAL IS NOT COUNTED, so "
        "no carriage row exists yet rather than a guessed one."))

for pk in ADOPT:
    p = Part.objects.get(pk=pk)
    Part.objects.filter(pk=pk).update(default_location=binloc)
    if "2026-08-26" not in (p.notes or ""):
        Part.objects.filter(pk=pk).update(notes=(p.notes or "").rstrip() + ADOPT_NOTE)

# verify
binloc.refresh_from_db()
print(f"\n=== {binloc.pathstring} ===")
print("PHYSICALLY IN THE BIN:")
for si in StockItem.objects.filter(location=binloc):
    print(f"  {si.quantity:g} x {si.part.name[:60]}")
print("HOMED HERE BUT NOT YET IN IT (stock row still unlocated):")
for pk in ADOPT:
    p = Part.objects.get(pk=pk)
    rows = StockItem.objects.filter(part=p)
    unl = sum(float(s.quantity) for s in rows if s.location is None)
    ok = "OK" if p.default_location_id == binloc.pk else "FAILED"
    print(f"  [{ok}] {unl:>5g} x {p.name[:58]}")
print(f"\nempty Sterilite bins left: "
      f"{sum(float(s.quantity) for s in StockItem.objects.filter(part_id=BIN_PART)):g}")
