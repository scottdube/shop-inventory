"""Create the Mill Cart and empty the Machine Shop waiting room into real homes.

Scott, 2026-08-27: the microARC set and the big workholding live on a rolling
cart next to the mill. The cart is a REAL HOME -- things there are where they
belong -- so it becomes a location, unlike #502 which is a waiting room.

THE ACTUAL BUG IS NOT THE FILING. 17 of the 21 rows carry
`default_location = SLN`, the site root. That is not a home, it is the whole
building: it satisfies the not-null check while telling nobody anything, so the
rows read as filed and drift straight back to unfiled. Every move here sets a
real default_location as well as a location.

Destinations are read off the drawers' own descriptions, not guessed. Anything
whose drawer is not obvious from those descriptions is LEFT WHERE IT IS and
listed at the end for Scott, because a confident wrong drawer is worse than an
honest waiting room.

    itq run scripts/file_mill_cart.py            # dry run
    itq run scripts/file_mill_cart.py --commit
"""
import argparse, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part                                     # noqa: E402
from stock.models import StockItem, StockLocation                # noqa: E402

MACHINE_SHOP, UNFILED = 420, 502
CART_NAME = "Mill Cart"
CART_DESC = ("MILL CART. Rolling cart beside the Tormach 1100MX. Home for mill "
             "accessories that are used at the machine and are too big for a "
             "drawer -- the microARC 4th axis set, fixture plates, oil skimmer. "
             "A real home, not a staging area: what is here is where it belongs.")

# stock pk -> (destination location pk or 'CART', why)
PLAN = {
    28:  ("CART", "microARC 4th axis - the machine accessory itself"),
    29:  ("CART", "microARC subplate - part of the same assembly"),
    30:  ("CART", "microARC driver kit - part of the same assembly"),
    24:  ("CART", "20in fixture plates - will not go in a drawer"),
    31:  ("CART", "oil skimmer - coolant tank accessory, used at the machine"),
    19:  (423, "BT30 ER20 holders -> Toolholder Rack, 'wall rack beside the mill'"),
    20:  (423, "BT30 ER20 holders -> Toolholder Rack"),
    16:  (438, "ER20 collet set -> TC-D3, 'torque wrenches, ER-20 collet sets'"),
    32:  (437, "1/2in end mill -> TC-D2, 'cutting tools - endmills'"),
    15:  (437, "chamfer mill -> TC-D2"),
    17:  (437, "cobalt reamer -> TC-D2"),
    583: (437, "carbide insert -> TC-D2"),
    23:  (442, "coolant nozzles -> TC-D7, 'coolant - Loc-Line nozzles'"),
}
LEAVE = {
    586: "Tapmatic No.90X tapping head, $2,005 — spindle accessory or TC-D1 "
         "(tap wrenches)? Too expensive to guess at.",
    9:   "RKJXT1F42001 navigation switch x2 — ELECTRONICS. Does not belong in "
         "the machine shop at all; needs a bin on the wall.",
    11:  "BT30 pull studs — rack with the holders, or their own drawer? "
         "CLAUDE.md has a stud convention; ask before splitting them up.",
    14:  "BT30 pull studs, TSC — same question.",
    587: "zero-quantity row.", 588: "zero-quantity row.",
    589: "zero-quantity row.", 590: "zero-quantity row.",
}

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

cart = StockLocation.objects.filter(name=CART_NAME, parent_id=MACHINE_SHOP).first()
print(f"cart: {'exists #' + str(cart.pk) if cart else 'will be created'}")

rows = {s.pk: s for s in StockItem.objects.filter(location_id=UNFILED)
        .select_related("part")}
print(f"{len(rows)} rows in the waiting room\n")
for pk, (dest, why) in PLAN.items():
    s = rows.get(pk)
    if not s:
        print(f"  [{pk}] NOT in the waiting room — skipping"); continue
    d = "Mill Cart" if dest == "CART" else StockLocation.objects.get(pk=dest).name
    home = s.part.default_location
    hs = home.pathstring if home else "(none)"
    print(f"  [{pk:4}] {float(s.quantity):>3g}x {s.part.name[:38]:40} -> {d:16} "
          f"home was {hs.split('/')[-1] if home else '(none)'}")
    print(f"         {why}")

print(f"\nLEFT in the waiting room ({len(LEAVE)}):")
for pk, why in LEAVE.items():
    s = rows.get(pk)
    nm = s.part.name[:36] if s else "?"
    print(f"  [{pk:4}] {nm:38} {why}")

if not a.commit:
    raise SystemExit("\nDRY RUN — add --commit")

if not cart:
    cart = StockLocation.objects.create(
        name=CART_NAME, parent_id=MACHINE_SHOP, description=CART_DESC)
    got = StockLocation.objects.get(pk=cart.pk)
    assert got.parent_id == MACHINE_SHOP and got.description == CART_DESC
    print(f"\nOK  location #{cart.pk} {got.pathstring}")

moved = 0
for pk, (dest, _why) in PLAN.items():
    s = rows.get(pk)
    if not s:
        continue
    loc = cart if dest == "CART" else StockLocation.objects.get(pk=dest)
    StockItem.objects.filter(pk=pk).update(location=loc)
    Part.objects.filter(pk=s.part_id).update(default_location=loc)
    fresh = StockItem.objects.get(pk=pk)
    assert fresh.location_id == loc.pk, f"[{pk}] location did not stick"
    assert Part.objects.get(pk=s.part_id).default_location_id == loc.pk, \
        f"[{pk}] default_location did not stick"
    moved += 1
print(f"OK  {moved}/{len(PLAN)} moved, each with a real default_location")
left = StockItem.objects.filter(location_id=UNFILED).count()
print(f"    waiting room now holds {left}")
