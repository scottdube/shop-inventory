"""Stand up the ADHESIVES bin on WS2-S4 and seed what is in the photo.

Scott 2026-08-26, photo of the group plus: "everything goes in, some of it has
to lay down", 31 acid brushes, three applicator bottles, 20 popsicle-stick
spreaders, it was on shelf four and shelf four is fine, the blue mat is not
part of the group.

Follows the Air System / B-01 pattern exactly: the BIN is the location, so a
move to another shelf is a re-parent and not a rename, and the bin is a HOME --
things filed here get it as default_location.

COUNTS. Two tiers in this seed and the notes say which per row:
  - tallied      : acid brushes (31), applicator bottles (3), spreader sticks
                   (20). Scott counted and stated them.
  - [ESTIMATE]   : everything I counted off the photograph. A photo shows
                   identity, not quantity -- a second tube behind the first is
                   invisible. These carry no stocktake_date and want a look
                   when the bin is actually loaded.

Not seeded: the foil pouch at top-left of the frame. It is cut off and I cannot
read it. Guessing it would be the exact failure this repo keeps paying for.
"""
import argparse, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model
from part.models import Part, PartCategory
from stock.models import StockItem, StockLocation

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

SHELF = 456          # SLN/Storage/WS2/WS2-S4
CAT = 106            # Shop/Consumables/Adhesives
BIN_PART = 1089      # Storage Bins, 6 Quart -- 19 at WS2-S1

BIN_DESC = (
    "ADHESIVES. Solvent cements, contact adhesive, gasket maker, activator, and "
    "the brushes, spreader sticks and applicator bottles that go with them. Sterilite 6qt clear, "
    "snap-on lid, on WS2-S4. A HOME -- things filed here get it as "
    "default_location. The BIN is the location and the name travels WITH the "
    "bin, so moving it to another shelf is a re-parent, not a rename. "
    "Established 2026-08-26.\n\n"
    "SOME CONTENTS LIE DOWN, on purpose (Scott): the Weld-On 4 pint can and the "
    "activator aerosol both stand taller than the 6qt's ~4.5 in interior. That "
    "is a decision, not an oversight -- do not 'fix' it by standing them up "
    "with the lid off.\n\n"
    "NOT the only adhesive home. AT-D2 (Assembly & Test) is tape-and-adhesives "
    "and keeps the Loctite super glue gel #848 at the bench. Small stuff stays "
    "at the bench; bulk solvent cement lives here. If you are looking for glue "
    "and it is not here, look there."
)

# (name, description <=250 chars, long notes, qty, tier)
SEED = [
    ("Gorilla Clear Grip Contact Adhesive, 3 fl oz (88 mL)",
     "Crystal-clear flexible contact adhesive, 100% waterproof. Squeeze tube "
     "with a fine applicator tip.",
     "Bonds metal, glass, fabric, wood, ceramic, leather, paper and plastic. "
     "Contact adhesive: coat both faces, let tack off, then press. Grabs in "
     "seconds and stays flexible, which is what separates it from the solvent "
     "cements in this bin -- those weld the plastic, this one sticks to it.",
     2, "estimate"),
    ("Weld-On 16 Acrylic Solvent Cement, clear medium-bodied, tube (IPS 10315)",
     "IPS Weld-On #16, fast set, clear medium-bodied solvent cement for acrylic, "
     "butyrate, polycarbonate, styrene and other plastics. Tube with applicator "
     "tip. Stock no. 10315.",
     "Syrupy body -- it fills a joint that is not perfectly mated, where the "
     "water-thin #4 would just run out. SCAQMD 1168, <250 g/L VOC.\n\n"
     "TUBE VOLUME NOT RECORDED: the size line was not legible in the photo. "
     "Read it off the tube and correct this.",
     1, "estimate"),
    ("Weld-On 4 Acrylic Solvent Cement, water-thin, 1 pint can",
     "IPS Weld-On #4, fast set, clear water-thin solvent cement for acrylic and "
     "polycarbonate. 16 fl oz (473 mL) metal can. Fixture time ~3 min, 80% "
     "strength at 72 h.",
     "CAPILLARY cement: mate and clamp the joint FIRST, then run the cement in "
     "along the seam with a needle bottle. It is not spread and not gap-filling "
     "-- for a joint that does not close, reach for the #16 instead.\n\n"
     "Flammable, and it flashes off fast enough that an open can degrades. Lid "
     "on, and this is part of why the bin is a lidded one.\n\n"
     "Stored LYING DOWN -- the can is taller than the bin is deep.",
     1, "estimate"),
    ("Adhesive Guru Activator, aerosol, 6.76 fl oz",
     "Cyanoacrylate accelerator in an aerosol can. Kicks CA off in seconds, and "
     "lets CA fill a gap it otherwise could not.",
     "Use on the mating face, not on the wet glue, or the joint goes brittle "
     "and white. Stored LYING DOWN -- taller than the bin is deep.",
     1, "estimate"),
    ("Yonglian Grey 999 Gasket Maker, sensor-safe RTV",
     "Grey RTV silicone gasket maker, sensor safe, non-corrosive. Professional "
     "use. Supplied in a retail hang bag.",
     "Oxime cure, so it does not give off acetic acid and will not poison an "
     "oxygen sensor or corrode nearby metal -- that is what 'sensor safe' on "
     "the tube means, and it is why this is not interchangeable with ordinary "
     "acetoxy bathroom silicone.",
     2, "estimate"),
    ("Applicator Bottle, needle tip, LDPE",
     "Squeeze bottle with a fine metal needle tip, for running water-thin "
     "solvent cement into a closed acrylic joint by capillary action.",
     "The companion tool to Weld-On 4 -- the cement is unusable without one. "
     "Solvent attacks the needle's seal over time; expect to replace them.",
     3, "tallied"),
    ("Wood Spreader Stick, flat (popsicle stick)",
     "Flat wooden stick for spreading contact adhesive and gasket maker, and "
     "for mixing. Disposable.",
     "",
     20, "tallied"),
    ("Acid Brush, metal handle, horsehair",
     "Small tinned-steel-handle brush for flux, solvent cement and general "
     "adhesive work. Disposable.",
     "Solvent cement ruins one per session -- treat them as consumed, not "
     "cleaned.",
     31, "tallied"),
]

TIER_NOTE = {
    "estimate":
        "[ESTIMATE] Counted off Scott's photograph 2026-08-26, not in hand. A "
        "photo shows identity, not quantity -- anything behind the front item "
        "is invisible to it. No stocktake_date: nobody has counted this. "
        "Confirm when the bin is loaded.",
    "tallied":
        "TALLIED. Scott counted and stated this number 2026-08-26.",
}

user = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
shelf = StockLocation.objects.get(pk=SHELF)
cat = PartCategory.objects.get(pk=CAT)
print(f"shelf: {shelf.pathstring}\ncategory: {cat.pathstring}\n")

# --- duplicate guard, before anything is created --------------------------
clash = False
for name, _d, _n, _q, _t in SEED:
    key = name.split(",")[0]
    hits = Part.objects.filter(name__icontains=key)
    if hits.exists():
        clash = True
        for h in hits:
            print(f"  POSSIBLE DUPLICATE for {key!r}: [{h.pk}] {h.name[:70]}")
if not clash:
    print("duplicate guard: no existing part matches any seed name\n")

existing = StockLocation.objects.filter(name="Adhesives", parent=shelf).first()
print(f"bin location: {'EXISTS ' + str(existing.pk) if existing else 'to create'}")
for name, _d, _n, q, t in SEED:
    print(f"  seed {q:>3} x {name[:62]:<62} [{t}]")

if not a.commit:
    print("\nDRY RUN -- add --commit")
    sys.exit()

# --- the bin ---------------------------------------------------------------
binloc = existing or StockLocation.objects.create(
    name="Adhesives", parent=shelf, description=BIN_DESC)
if not existing:
    print(f"\ncreated location [{binloc.pk}] {binloc.pathstring}")

# --- take one empty Sterilite out of the stack -----------------------------
stack = StockItem.objects.filter(part_id=BIN_PART).first()
if stack and "2026-08-26" not in (stack.notes or ""):
    stack.take_stock(1, user, notes="One bin taken to become the ADHESIVES bin on WS2-S4, 2026-08-26.")
    stack.refresh_from_db()
    StockItem.objects.filter(pk=stack.pk).update(
        notes=(stack.notes or "").rstrip() +
        "\n\n2026-08-26: one bin consumed to become the ADHESIVES bin on WS2-S4."
    )
    print(f"empty bins remaining: {stack.quantity:g}")

# --- parts + stock ---------------------------------------------------------
for name, desc, longnote, qty, tier in SEED:
    p = Part.objects.filter(name=name).first()
    if not p:
        p = Part.objects.create(name=name, description=desc, category=cat,
                                default_location=binloc, component=False,
                                purchaseable=True, active=True)
        print(f"  part [{p.pk}] {name[:60]}")
    if longnote and not (p.notes or "").strip():
        Part.objects.filter(pk=p.pk).update(notes=longnote)
    if p.description != desc:
        Part.objects.filter(pk=p.pk).update(description=desc)
    if p.default_location_id != binloc.pk:
        Part.objects.filter(pk=p.pk).update(default_location=binloc)
    if not StockItem.objects.filter(part=p, location=binloc).exists():
        si = StockItem.objects.create(part=p, location=binloc, quantity=qty)
        StockItem.objects.filter(pk=si.pk).update(notes=TIER_NOTE[tier])

# --- WS1 has been advertising adhesives it does not have -------------------
ws1 = StockLocation.objects.get(pk=445)
if "2026-08-26" not in (ws1.description or ""):
    StockLocation.objects.filter(pk=445).update(
        description=(ws1.description or "").rstrip() +
        "  CORRECTED 2026-08-26: the ADHESIVES this line claimed are on WS2-S4, "
        "in the Adhesives bin. Like the wire (see WS2-S3), this description was "
        "written as intent before anyone checked. What WS1 actually holds is "
        "still unverified."
    )
    print("WS1 description corrected")

# --- verify ----------------------------------------------------------------
binloc.refresh_from_db()
print(f"\n=== {binloc.pathstring} ===")
tot = 0
for si in StockItem.objects.filter(location=binloc).order_by("part__name"):
    tot += 1
    mark = "[EST]" if "[ESTIMATE]" in (si.notes or "") else "     "
    print(f"  {mark} {si.quantity:>3g} x {si.part.name[:64]}")
    print(f"          default_location = {si.part.default_location}")
print(f"  {tot} rows")
print(f"\nempty Sterilite bins left: "
      f"{sum(float(s.quantity) for s in StockItem.objects.filter(part_id=BIN_PART)):g}")
