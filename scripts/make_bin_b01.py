"""Create bin B-01 on WS2-S3 and move the fiberglass sleeve into it.

Addressing decided 2026-08-24. A bin gets a PERMANENT ID that travels with it
(B-01, B-02, ...), never a shelf-position code like WS2-S3-B1. Ten identical
clear bins on one shelf are indistinguishable by contents alone -- Scott: "you
could get ten of them on one of these shelves, how would you know where to
look" -- so the ID is what the label shouts and what a barcode resolves to.

Baking the shelf into the name was rejected for the reason already written on
the Air System bin: the BIN is the location, so it can move or upsize freely.
A shelf-coded name means renaming the bin and every default_location pointing
at it the first time it moves.

Name carries both: the code finds it on the shelf, the words find it in search.

One bin leaving the 10-pack goes from STOCK to LOCATION, so #1089 drops to 9.
"""
import argparse, os, sys
import django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part                       # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

NAME = "B-01 Sleeving & Loom"
DESC = ("BIN B-01 — Sterilite 6qt clear, snap-on lid, on WS2-S3 with the wire. "
        "Wire sleeving and loom: fiberglass high-temp sleeve, braided sleeving, "
        "split loom. A HOME — things here get default_location. The BIN is the "
        "location and the ID travels WITH the bin, so moving it to another "
        "shelf is a re-parent, not a rename. Heat-shrink not decided; it lives "
        "in the bin wall today. Established 2026-08-24.")

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

shelf = StockLocation.objects.get(name="WS2-S3")
clash = StockLocation.objects.filter(name__istartswith="B-01")
print(f"name collisions for 'B-01': {[l.pathstring for l in clash] or 'none'}")
if clash.exists():
    print("!! collision — stopping"); raise SystemExit(1)

sleeve = StockItem.objects.get(pk=657)
pack = StockItem.objects.get(pk=667)
print(f"parent      {shelf.pathstring}")
print(f"sleeve      #{sleeve.pk} {float(sleeve.quantity):g} m @ {sleeve.location.name} -> {NAME}")
print(f"bin 10-pack #{pack.pk} {float(pack.quantity):g} -> {float(pack.quantity)-1:g}  (one goes into service)")
if not a.commit:
    print("\nDRY RUN"); raise SystemExit

loc = StockLocation.objects.create(name=NAME, description=DESC, parent=shelf)
f = StockLocation.objects.get(pk=loc.pk)
assert f.parent_id == shelf.pk and f.description == DESC
print(f"\nOK  location #{f.pk} {f.pathstring}")

StockItem.objects.filter(pk=sleeve.pk).update(location=loc)
assert StockItem.objects.get(pk=sleeve.pk).location_id == loc.pk
Part.objects.filter(pk=790).update(default_location=loc)
assert Part.objects.get(pk=790).default_location_id == loc.pk
print(f"OK  sleeve stock #{sleeve.pk} and #790's home -> {f.pathstring}")

StockItem.objects.filter(pk=pack.pk).update(quantity=float(pack.quantity) - 1)
assert float(StockItem.objects.get(pk=pack.pk).quantity) == 9
print("OK  #1089 bin stock 10 -> 9")
