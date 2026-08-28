"""Blade fuse kit #346 into L2-D2 — the part existed, the stock never did.

Another imported-but-never-stocked row: #346 has carried ASIN B01E5MM63C and a
purchase history since import, with default_location set to SLN (the site root,
which is not a home) and zero stock rows. The box has been in the shop the whole
time.

Filed to L2-D2 to sit with the XFFCSEC glass fuses, following Scott's "fuses
L2D2". Blade and glass do not interchange, but "where are the fuses" is one
question and should have one answer.
"""
import argparse, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part                                     # noqa: E402
from stock.models import StockItem, StockLocation                # noqa: E402

PART, BIN, QTY = 346, "L2-D2", 120
NAME = "Fuse Kit, ATO/ATC blade 32V, 7 values, 120 pc + puller (Everything Automobiles)"
DESC = ("Everything Automobiles / RETTUN assortment of standard ATO/ATC blade "
        "fuses: 5, 7.5, 10, 15, 20, 25, 30 A, 120 pieces, with a fuse puller. "
        "Kit as sold also lists 10 inline fuse holders.")
NOTES = (
 "[ESTIMATE] 120 is the PRINTED PACK FIGURE off the lid, not a count. No "
 "stocktake_date, so this stays on the never-counted report.\n\n"
 "THE 10 INLINE FUSE HOLDERS ARE UNACCOUNTED FOR. The lid sells this as \"120 "
 "Assorted Fuses, 10 Inline Fuse Holders - Includes Puller\". In the 2026-08-28 "
 "photo the fuses and the puller are there and NO HOLDERS ARE VISIBLE. Either "
 "they were used, or they are elsewhere in the box. Not resolved, and worth "
 "resolving: #252 is a separate in-line ATC holder part, so if these ten exist "
 "they belong on that row rather than being implied by this one.\n\n"
 "VALUES AND COLOUR CODE — the colour IS the rating on ATO/ATC, which is why "
 "grabbing by colour is safe and grabbing by eye is not:\n"
 "  5 A tan · 7.5 A brown · 10 A red · 15 A blue · 20 A yellow · 25 A clear/"
 "natural · 30 A green\n\n"
 "STANDARD ATO/ATC SIZE, not mini, not maxi, not low-profile. Those are "
 "different footprints and will not fit each other's holders — check the holder "
 "before assuming a spare fits.\n\n"
 "32 V AUTOMOTIVE RATING. These are DC-rated for vehicle circuits and are NOT "
 "mains parts. They do not substitute for the 5x20 glass fuses in #1143 or the "
 "392-series in #494, and neither of those substitutes for these.\n\n"
 "Amazon ASIN B01E5MM63C. Related parts already in the catalogue, all at zero "
 "stock: #252 in-line ATC holders, #239 WATERWICH 6-way blade fuse box.")

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

loc = StockLocation.objects.get(name__iexact=BIN)
p = Part.objects.get(pk=PART)
print(f"#{p.pk} {p.name[:56]}")
print(f"  home was {p.default_location} (site root, not a home)")
print(f"  -> {loc.pathstring}, qty {QTY} [ESTIMATE], no stocktake")
if StockItem.objects.filter(part=p).exists():
    sys.exit("!! already has stock rows")
if not a.commit:
    raise SystemExit("\nDRY RUN — add --commit")

s = StockItem.objects.create(part=p, location=loc, quantity=QTY, notes=NOTES)
Part.objects.filter(pk=PART).update(name=NAME, description=DESC, notes=NOTES,
                                    default_location=loc)
f = StockItem.objects.get(pk=s.pk)
assert float(f.quantity) == QTY and f.location_id == loc.pk, "row did not stick"
assert f.stocktake_date is None, "something stamped a stocktake date"
k = Part.objects.get(pk=PART)
assert k.default_location_id == loc.pk and k.name == NAME, "part did not stick"
print(f"\nOK  #{PART} renamed, homed to {loc.name}, stock #{f.pk} qty=120")
