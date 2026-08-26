"""Declare B2-R7C1 the SPRINGS home. Intent only -- no stock is moved.

Scott 2026-08-26: "we have some assortments and some stowed but not properly
catalogued, b2r7c1 has springs in it".

THE SPRING SITUATION, MEASURED:

  In the DATABASE, six spring rows, ALL UNLOCATED:
    #976   6   Compression Spring, 3" Long, 0.5" OD
    #977   2   Extension Spring, loop ends, 4.5" Long
    #978   2   Extension Spring, hook ends, 5" Long
    #1001  5   302 Stainless Compression Springs, 1" Long
    #1002 12   Compression Spring, 0.938" Long, 0.188" OD
    #1132  2   Extension Spring, card P-9602

  In B2-R7C1: springs, per Scott. The database says ZERO rows.

  Assortments: exist physically, and are NOT in the catalogue at all -- no
  spring assortment or kit part of any kind.

So springs fail in both directions at once. The record holds springs with no
place; the shelf holds springs with no record. Neither half is visible to the
other, which is why "where do springs go" had no answer an hour ago.

B2-R7C1 IS ALREADY THE ANSWER. It is a large cell (6 x 4-9/16 x 2-3/16 in),
carries no description, and physically holds springs. Declaring it beats
inventing a new home: the shop already made this decision, it just never got
written down.

WHAT THIS SCRIPT DOES NOT DO: move any stock. The six rows get B2-R7C1 as
default_location — where they GO — and their locations stay null until somebody
carries them there or confirms they are already in the cell.

That last case is live. The M5/M6/M8 washers were "unlocated" all day and turned
out to have been sitting in B1-R7C3 the whole time. These six may be the very
springs Scott is looking at. Asking is one question; searching is an afternoon.
"""
import argparse, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part
from stock.models import StockItem, StockLocation

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

cell = StockLocation.objects.get(pk=289)
SPRINGS = [976, 977, 978, 1001, 1002, 1132]

DESC = (
    "SPRINGS. Compression and extension springs, loose and in assortments. A "
    "HOME — things filed here get it as default_location. Declared 2026-08-26 "
    "because the cell was ALREADY holding springs and nothing said so.\n\n"
    "**Several parts name this cell and are not yet recorded in it.** Six spring "
    "rows carry it as default_location with a null location: they are owned, and "
    "whether they are already in this cell is unconfirmed. Do not set their "
    "location from a keyboard — that is what stranded the SHT31 rows in August.\n\n"
    "**The assortments in here are NOT CATALOGUED AT ALL.** There is no spring "
    "assortment or kit part of any kind in the system as of 2026-08-26. Anything "
    "in this cell that is not one of the six named rows is invisible to every "
    "search and every stock check.\n\n"
    "Note this is the IMPERIAL FASTENER cabinet and a spring is not a fastener. "
    "It is here because it is a large cell that already had springs in it, not "
    "because of a scheme.")

print(f"cell: {cell.pathstring}")
print(f"  db rows: {StockItem.objects.filter(location=cell).count()}  (Scott: physically has springs)")
for pk in SPRINGS:
    p = Part.objects.get(pk=pk)
    rows = StockItem.objects.filter(part=p)
    q = sum(float(s.quantity) for s in rows)
    unl = all(s.location is None for s in rows)
    print(f"  [{pk}] {q:>4g} {'UNLOCATED' if unl else 'located'}  {p.name[:56]}")

if not a.commit:
    print("\nDRY RUN -- add --commit")
    sys.exit()

StockLocation.objects.filter(pk=cell.pk).update(description=DESC)
for pk in SPRINGS:
    p = Part.objects.get(pk=pk)
    Part.objects.filter(pk=pk).update(default_location=cell)
    if "SPRING HOME DECLARED" not in (p.notes or ""):
        Part.objects.filter(pk=pk).update(notes=(p.notes or "").rstrip() +
            "\n\nSPRING HOME DECLARED 2026-08-26: B2-R7C1, which already had "
            "springs in it and nothing saying so. This part now names that cell "
            "as default_location — where it GOES. Its stock row is still "
            "unlocated, because nobody has confirmed whether it is already in "
            "there.\n\n"
            "That is a live possibility, not a formality: the M5/M6/M8 washers "
            "read 'unlocated' all day and had been sitting in B1-R7C3 the whole "
            "time. Ask before searching.")

print(f"\ncell described; {len(SPRINGS)} parts now home to {cell.name}")
print("stock locations UNCHANGED — all six rows still unlocated, deliberately")
