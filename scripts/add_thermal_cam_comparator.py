"""File two metrology items Scott photographed at SLN, 2026-10-03.

  1. Thermal Master P2 Pro thermal camera, iOS, macro lens included.
     SN P200013E23499805, read off the box sticker. Home SLN BL-5.
     COMMUTES SLN <-> LRD -- marked with trip.py after this runs, not here, so
     there is one code path that writes the `commutes` metadata.
  2. Surface roughness comparator, 30 specimens (6 x 5 in the case, Scott
     counted), ISO 2632/1-1975, maker not marked anywhere visible.
     Stays at SLN -- does not commute. Lives in BR-2, bench right drawer 2
     (Scott: "metrology bench is right drawer 2").

CATEGORIES. The comparator goes to Tooling/Measuring beside the AMTAST AMT220
profilometer (#1268) -- every metrology instrument lives there, per
po_1003_amtast_roughness.py. The camera goes to Equipment/Test Equipment: it is
an electrical/thermal diagnostic instrument like the scope, not a gauge that
measures a part. If Scott disagrees, that is a one-field move.

Read from the packaging only. Nothing here is from a listing; no price, no PO
-- purchase history unknown, and an invented one is worse than none.

    itq run scripts/add_thermal_cam_comparator.py            # dry run
    itq run scripts/add_thermal_cam_comparator.py --commit

Then:
    itq run scripts/trip.py mark <camera SI pk> "thermal camera, one only, carry both ways"
    itq run scripts/print_part_label.py <camera SI pk> <comparator SI pk> --stockitem
    itq run scripts/print_part_label.py <BR-2 loc pk> --location --compact
(add --print to the last two once the render looks right)
"""
import argparse
import os
import sys

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part, PartCategory  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
ap.add_argument("--comparator-loc", default="BR-2",
                help="StockLocation name for the comparator (Scott: right drawer 2)")
args = ap.parse_args()


def loc_named(name):
    hits = list(StockLocation.objects.filter(name__iexact=name))
    if len(hits) != 1:
        print(f"!! location {name!r}: {len(hits)} matches "
              f"{[(h.pk, h.pathstring) for h in hits]}")
        return None
    return hits[0]


# ------------------------------------------------------------ locations
cam_loc = loc_named("BL-5")
if cam_loc is None:
    bl = StockLocation.objects.filter(name__iexact="BL").first()
    if bl:
        print("   children of BL:", [(c.pk, c.name) for c in bl.get_children()])
if args.comparator_loc and not StockLocation.objects.filter(name__iexact=args.comparator_loc).exists():
    br = StockLocation.objects.filter(name__iexact="BR").first()
    if br:
        print("   children of BR:", [(c.pk, c.name) for c in br.get_children()])
cmp_loc = loc_named(args.comparator_loc) if args.comparator_loc else None
if cam_loc:
    print(f"camera home     = loc #{cam_loc.pk} {cam_loc.pathstring}")
if cmp_loc:
    print(f"comparator loc  = loc #{cmp_loc.pk} {cmp_loc.pathstring}")

# ------------------------------------------------------------ categories
cat_meas = PartCategory.objects.get(name="Measuring", parent__name="Tooling")
cat_test = PartCategory.objects.get(name="Test Equipment", parent__name="Equipment")
print(f"categories: #{cat_meas.pk} {cat_meas.pathstring} | #{cat_test.pk} {cat_test.pathstring}")

# ------------------------------------------------------------ parts
SN = "P200013E23499805"
CAM = dict(
    name="Thermal Master P2 Pro Thermal Camera, iOS, macro lens",
    description="Phone-mount thermal camera, iOS version, macro lens included "
                "(box: 'P2 Pro (Macro Lens in)', System: iOS)",
    keywords="thermal camera, thermal imager, IR camera, infrared, P2 Pro, "
             "Thermal Master, macro lens, iPhone, iOS, heat, hot spot",
    category=cat_test, component=False, purchaseable=True, trackable=True,
    notes=("Read off the box, 2026-10-03.\n\n"
           "| | |\n|---|---|\n"
           "| Product | P2 Pro (Macro Lens in) |\n"
           "| System | iOS |\n"
           "| Manufacturer | Thermal Master Technology Co., Ltd. (Yantai) |\n"
           "| Web | www.thermalmaster.com |\n\n"
           "**iOS version.** Thermal Master sells the P2 Pro in separate iOS and "
           "Android versions; the box does not say which connector this one has. "
           "Check the plug before planning to use it with an Android or USB-C phone.\n\n"
           "**Commutes SLN <-> LRD** -- one camera, carried both ways. Tracked by "
           "trip.py, not by a second unit."),
)
CMP = dict(
    name="Surface Roughness Comparator, 30 specimens, 6 processes",
    description="Visual/tactile Ra comparison blocks, ISO 2632/1-1975, uin AA + um Ra; "
                "turning, V/H milling, plain/ext grinding, lapping",
    keywords="surface roughness, roughness comparator, surface finish, finish "
             "comparator, Ra, microinch, AA, ISO 2632, N-grade, metrology, specimen",
    category=cat_meas, component=False, purchaseable=True,
    notes=("Read off the card in the case, 2026-10-03. Maker not marked.\n\n"
           "30 specimens in a 6 x 5 array (counted by Scott).\n\n"
           "| Process | um Ra | uin AA | blocks |\n|---|---|---|---|\n"
           "| Turning | 0.4-12.5 | 16-500 | 6 (N5-N10) |\n"
           "| Vertical milling | 0.4-12.5 | 16-500 | 6 |\n"
           "| Horizontal milling | 0.4-12.5 | 16-500 | 6 |\n"
           "| Plain grinding | 0.05-1.6 | 2-63 | 6 (N2-N7) |\n"
           "| External grinding | 0.2-1.6 | 8-63 | 4 |\n"
           "| Flat lapping | 0.05-0.1 | 2-4 | 2 |\n\n"
           "Card: blocks are 45 carbon steel, lapping blocks GCr15. Do not touch the "
           "faces bare-handed; keep oiled against rust; compare under the same "
           "lighting as the workpiece.\n\n"
           "Complements the AMTAST AMT220 profilometer (#1268): the comparator is "
           "the quick check at the machine, the AMT220 the number."),
)

dups = []
for spec, terms in ((CAM, ["P2 Pro", "Thermal Master", "thermal camera", "thermal imager"]),
                    (CMP, ["comparator", "roughness comparator", "ISO 2632"])):
    q = Q(name__iexact=spec["name"])
    for t in terms:
        q |= Q(name__icontains=t) | Q(keywords__icontains=t)
    hits = list(Part.objects.filter(q).values_list("pk", "name"))
    # the AMT220 tester legitimately matches roughness terms; it is not a duplicate
    hits = [h for h in hits if h[0] != 1268]
    if hits:
        dups.append((spec["name"], hits))
if StockItem.objects.filter(serial=SN).exists():
    dups.append(("serial", SN))
for d in dups:
    print("!! possible duplicate:", d)

for spec in (CAM, CMP):
    assert len(spec["name"]) <= 100 and len(spec["description"]) <= 250 \
        and len(spec["keywords"]) <= 250, spec["name"]

missing = [n for n, v in (("BL-5", cam_loc), (args.comparator_loc, cmp_loc)) if v is None]
if not args.commit:
    print("\nDRY RUN -- add --commit"
          + (f"\n   unresolved: {missing}" if missing else "")
          + ("" if cmp_loc else "\n   no --comparator-loc: comparator part only, no stock row"))
    sys.exit(0)
if dups:
    sys.exit("refusing to commit with possible duplicates -- check them first")
if missing:
    sys.exit(f"refusing to commit: unresolved {missing}")


# ------------------------------------------------------------ write
def make_part(spec, home):
    p = Part(default_location=home, assembly=False, **spec)
    p.save()
    p.refresh_from_db()
    assert p.name == spec["name"] and p.category_id == spec["category"].pk, "part did not stick"
    print(f"CREATED part #{p.pk} {p.name}  cat={p.category.pathstring}")
    return p


def make_stock(part, loc, serial=None):
    s = StockItem(part=part, location=loc, quantity=1, serial=serial,
                  notes="Filed 2026-10-03 from Scott's photos; quantity 1 seen.")
    s.save()
    s.refresh_from_db()
    assert s.location_id == loc.pk and float(s.quantity) == 1 and s.serial == serial
    print(f"CREATED stock item #{s.pk}  {part.name[:40]}  @ {loc.pathstring}"
          + (f"  SN {serial}" if serial else ""))
    return s


cam = make_part(CAM, cam_loc)
cam_si = make_stock(cam, cam_loc, serial=SN)
cmp_part = make_part(CMP, cmp_loc)
cmp_si = make_stock(cmp_part, cmp_loc) if cmp_loc else None

print("\nNEXT:")
print(f'  itq run scripts/trip.py mark {cam_si.pk} "thermal camera, one only, carry both ways"')
pks = " ".join(str(s.pk) for s in (cam_si, cmp_si) if s)
print(f"  itq run scripts/print_part_label.py {pks} --stockitem")
print(f"  itq run scripts/print_part_label.py {cmp_loc.pk} --location --compact"
      "   # only if BR-2 has no label yet (metadata.labeled)")
