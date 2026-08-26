"""Add a counted bearing to the Bearings & Motion bin. One stable command shape.

    itq run scripts/add_bearing.py 6203RS 2 --commit

Exists because Scott is walking a shelf and calling out designations one at a
time, and the fourth hand-written near-identical script is where copy-paste
errors start. Same reason `itq` exists.

DIMENSIONS ARE LOOKED UP, NEVER DERIVED. The table below is the ISO
deep-groove series and the miniature-linear designations, which are standards
rather than measurements. An unknown designation is a hard error: this script
will not guess a bore, because a wrong bore is worse than a missing part.

CLOSURE IS PART OF THE PART. 608RS and 608ZZ are separate parts with separate
rows -- see their notes. The suffix is carried into the name so the two can
never merge by accident.

Quantities passed here are TALLIED: the caller is holding the parts. The
stocktake_date is set. Do not use this for a number read off a bag.
"""
import argparse, os, re, sys, django, datetime

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part
from stock.models import StockItem, StockLocation

BIN, CAT = 587, 137

# designation -> (bore, OD, width) in mm. ISO 15 deep-groove series.
DIMS = {
    "623": (3, 10, 4),    "624": (4, 13, 5),    "625": (5, 16, 5),
    "626": (6, 19, 6),    "627": (7, 22, 7),    "628": (8, 24, 8),
    "629": (9, 26, 8),    "688": (8, 16, 4),    "608": (8, 22, 7),
    "6000": (10, 26, 8),  "6001": (12, 28, 8),  "6002": (15, 32, 9),
    "6003": (17, 35, 10), "6004": (20, 42, 12), "6005": (25, 47, 12),
    "6200": (10, 30, 9),  "6201": (12, 32, 10), "6202": (15, 35, 11),
    "6203": (17, 40, 12), "6204": (20, 47, 14), "6205": (25, 52, 15),
    "6800": (10, 19, 5),  "6801": (12, 21, 5),  "6802": (15, 24, 5),
    "6803": (17, 26, 5),  "6804": (20, 32, 7),  "6805": (25, 37, 7),
}
# INCH series (R). Bore/OD/width in inches, with the mm equivalents that the
# cross-reference maths needs. These are ABEC/inch standards, same status as
# the metric table: looked up, not measured.
INCH = {
    "R2":  ("1/8",  "3/8",    "5/32",  3.175,   9.525,  3.967),
    "R3":  ("3/16", "1/2",    "5/32",  4.762,  12.700,  3.967),
    "R4":  ("1/4",  "5/8",    "0.196", 6.350,  15.875,  4.978),
    "R6":  ("3/8",  "7/8",    "7/32",  9.525,  22.225,  5.556),
    "R8":  ("1/2",  "1-1/8",  "5/16", 12.700,  28.575,  7.938),
    "R10": ("5/8",  "1-3/8",  "11/32",15.875,  34.925,  8.733),
    "R12": ("3/4",  "1-5/8",  "7/16", 19.050,  41.275, 11.113),
    "R14": ("7/8",  "1-7/8",  "1/2",  22.225,  47.625, 12.700),
    "R16": ("1",    "2",      "1/2",  25.400,  50.800, 12.700),
}

# Seals ADD WIDTH on the inch R-series, so the INCH table's open-bearing width
# is wrong for a sealed part. R6 open is 7/32; R6-2RS is 9/32. That error is
# already in this shop's record once -- the R6-2RS in the bin was entered at
# 7/32 off the open table, and the Amazon listing it was bought from says 9/32.
# An unlisted sealed size falls back to the open width and SAYS SO in the note,
# rather than quietly asserting a number nobody checked.
SEALED_WIDTH = {
    "R6": {"2RS": ("9/32", 7.14), "RS": ("9/32", 7.14)},
    "R8": {"2RS": ("5/16", 7.94), "RS": ("5/16", 7.94)},
    # R4-2RS VERIFIED off the XiKe box 2026-08-26: "ID 1/4" x OD 5/8" x Width
    # 0.196"". Same as the open width -- on this size the seals do not add any.
    # That is worth having explicitly: without it the script would keep printing
    # WIDTH UNVERIFIED for a figure the manufacturer had already stated.
    "R4": {"2RS": ("0.196", 4.978), "RS": ("0.196", 4.978)},
}

CLOSURE = {
    "RS":  ("rubber sealed", "single contact rubber seal"),
    "2RS": ("rubber sealed both sides", "two contact rubber seals"),
    "ZZ":  ("metal shielded", "two non-contact metal shields"),
    "Z":   ("metal shielded one side", "single non-contact metal shield"),
    "":    ("open", "no seal or shield"),
}

ap = argparse.ArgumentParser()
ap.add_argument("designation", help="e.g. 6203RS, 608ZZ, 6001")
ap.add_argument("qty", type=float)
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

m = re.fullmatch(r"(R\d{1,2}|\d{3,4})[- ]?(2RS|RS|ZZ|Z)?", a.designation.upper())
if not m:
    sys.exit(f"cannot parse designation {a.designation!r}")
series, suffix = m.group(1), (m.group(2) or "")
if series not in DIMS and series not in INCH:
    sys.exit(f"unknown series {series!r} -- add it to DIMS or INCH with a real "
             f"datasheet figure. This script does not guess bores.")

short, longd = CLOSURE[suffix]
# Inch designations hyphenate before the suffix (R6-2RS); metric ones do not
# (608ZZ, 6203RS). "R62RS" is not a part number anybody would recognise.
desig = (f"{series}-{suffix}" if suffix and series.startswith("R") and len(series) <= 3
         else series + suffix)
if series in INCH:
    fb, fo, fw, bore, od, w = INCH[series]
    width_caveat = ""
    if suffix:
        sw = SEALED_WIDTH.get(series, {}).get(suffix)
        if sw:
            fw, w = sw
        else:
            width_caveat = (
                f"WIDTH UNVERIFIED: {fw} in is the OPEN {series} width and this "
                f"is a sealed bearing. Seals add width on the inch R-series and "
                f"no figure for {desig} is on file. Measure before cutting "
                f"anything to fit.\n\n")
    sizetxt = f"{fb} x {fo} x {fw} in"
    NAME = f"Ball Bearing {desig}, {sizetxt}"
    DESC = (f"Deep-groove radial ball bearing, {series} INCH series -- {fb} in "
            f"bore ({bore:.3f} mm), {fo} in OD ({od:.3f} mm), {fw} in wide, "
            f"{short}.")
    UNITS = (width_caveat +
             "INCH SERIES. This bearing is dimensioned in inches and is NOT a "
             "metric size with a converted label. Do not substitute a metric "
             "bearing for it or the reverse -- the fits are what fail, not the "
             "nominal numbers.\n\n")
else:
    bore, od, w = DIMS[series]
    sizetxt = f"{bore} x {od} x {w} mm"
    NAME = f"Ball Bearing {desig}, {sizetxt}"
    DESC = (f"Deep-groove radial ball bearing, {series} series -- {bore} mm bore, "
            f"{od} mm OD, {w} mm wide, {short}.")
    UNITS = ""
NOTES = (
    f"BORE {bore:.3f} mm · OD {od:.3f} mm · WIDTH {w:.3f} mm\n\n" +
    UNITS +
    f"Dimensions {sizetxt} are the standard for the {series} designation, not a "
    f"measurement of these parts. Closure: {longd}.\n\n"
    f"CLOSURE IS NOT COSMETIC. Rubber seals retain grease and exclude fine grit "
    f"at the cost of drag and speed; metal shields are the reverse. Bearings in "
    f"this bin that differ only by suffix are SEPARATE parts for that reason.\n\n"
    f"No purchase order in this system matches these; vendor and date unknown, "
    f"so none is claimed.")

binloc = StockLocation.objects.get(pk=BIN)
print(f"{desig}: {sizetxt}, {short}")
print(f"name: {NAME}")
same = Part.objects.filter(name__icontains=f"Bearing {series}")
if same:
    print(f"same series already in the catalogue:")
    for p in same:
        q = sum(float(s.quantity) for s in StockItem.objects.filter(part=p))
        print(f"  [{p.pk}] {q:g} x {p.name}")

if not a.commit:
    print(f"\nwould seed {a.qty:g}\nDRY RUN -- add --commit")
    sys.exit()

p = Part.objects.filter(name=NAME).first()
if not p:
    p = Part.objects.create(name=NAME, description=DESC, category_id=CAT,
                            default_location=binloc, purchaseable=True, active=True)
    print(f"part [{p.pk}] created")
Part.objects.filter(pk=p.pk).update(notes=NOTES, default_location=binloc)

si = StockItem.objects.filter(part=p, location=binloc).first()
if not si:
    si = StockItem.objects.create(part=p, location=binloc, quantity=a.qty)
else:
    StockItem.objects.filter(pk=si.pk).update(quantity=a.qty)
StockItem.objects.filter(pk=si.pk).update(
    stocktake_date=datetime.date(2026, 8, 26),
    notes=f"TALLIED 2026-08-26. Scott counted {a.qty:g} in hand.")

# --- cross-reference by BORE and by OD ------------------------------------
# Bore is what you check when matching a bearing to a shaft; section is what
# you forget. 6203 and 6803 are both 17mm bore at 40x12 and 26x5.
#
# The OD check is the subtler one and the reason it exists: R6 is 22.225mm OD
# against the 608's 22.000mm. A quarter of a millimetre. They will both go into
# a 22mm housing, one of them wrongly, and their bores differ by 1.5mm -- so
# the part that LOOKS like a drop-in is the one that is not.
#
# Dimensions are read back from the BORE line this script writes at the head of
# every note, which is why that line is both human-readable and parseable.
def dims_of(q):
    mm = re.search(r"BORE ([\d.]+) mm · OD ([\d.]+) mm", q.notes or "")
    if mm:
        return float(mm.group(1)), float(mm.group(2))
    if "LM8UU" in q.name:
        return 8.0, 15.0
    mm = re.search(r"(\d+) x (\d+) x (\d+) mm", q.name)
    return (float(mm.group(1)), float(mm.group(2))) if mm else (None, None)

BORE_TAG, OD_TAG = "SAME BORE", "NEAR-IDENTICAL OD"
same_bore, near_od = [], []
for q in Part.objects.filter(default_location_id=BIN):
    if q.pk == p.pk:
        continue
    qb, qo = dims_of(q)
    if qb is None:
        continue
    if abs(qb - bore) < 0.05:
        same_bore.append(q)
    elif abs(qo - od) < 0.6:
        near_od.append((q, qb, qo))

def label(q):
    return q.name.replace("Ball Bearing ", "")

lines = ""
if same_bore:
    lines += (f"\n\n{BORE_TAG}, NOT INTERCHANGEABLE — other {bore:.3f} mm bore "
              f"parts in this bin: " + "; ".join(f"{label(q)} (#{q.pk})" for q in same_bore) +
              ". Matching bores make these easy to grab for each other; section "
              "width, load rating and even the kind of motion differ.")
if near_od:
    lines += (f"\n\n{OD_TAG} — " + "; ".join(
        f"{label(q)} (#{q.pk}) is {qo:.3f} mm OD against this one's {od:.3f} mm, "
        f"but bores {qb:.3f} vs {bore:.3f}" for q, qb, qo in near_od) +
        ". Both will enter the same housing bore. Only one fits the shaft. "
        "This is the failure that gets found after assembly.")

if lines:
    cur = Part.objects.get(pk=p.pk).notes or ""
    Part.objects.filter(pk=p.pk).update(notes=cur.rstrip() + lines)
    for q in same_bore:
        qn = Part.objects.get(pk=q.pk).notes or ""
        if f"(#{p.pk})" not in qn:
            Part.objects.filter(pk=q.pk).update(notes=qn.rstrip() +
                f"\n\n{BORE_TAG}, NOT INTERCHANGEABLE — {label(p)} (#{p.pk}) "
                f"shares this {bore:.3f} mm bore.")
    for q, qb, qo in near_od:
        qn = Part.objects.get(pk=q.pk).notes or ""
        if f"(#{p.pk})" not in qn:
            Part.objects.filter(pk=q.pk).update(notes=qn.rstrip() +
                f"\n\n{OD_TAG} — {label(p)} (#{p.pk}) is {od:.3f} mm OD against "
                f"this one's {qo:.3f} mm, but its bore is {bore:.3f} mm not "
                f"{qb:.3f} mm. Both enter the same housing; only one fits the shaft.")
    print(f"cross-referenced: {len(same_bore)} same-bore, {len(near_od)} near-OD")

si.refresh_from_db()
print(f"[{p.pk}] stock[{si.pk}] qty={si.quantity:g} stocktake={si.stocktake_date}")
