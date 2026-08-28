"""Move the VFD control block to A3-R8C7 -> A3-R7C4, with the other VFD salvage.

Scott 2026-08-28: "No room in r eight c seven. It should go with the other
salvaged connectors off of the VFD, though."

That overrides the pitch rule, and correctly. A3-R8 sorts PCB terminal blocks by
pitch because you go there holding a board and needing a match. A salvage set is
looked for the other way round -- you remember the drive, not the pitch -- so
provenance beats pitch here. The three VFD connectors now sit together in
A3-R7C4 and the bin says what it is.

Also undoes the "odd-pitch oddments" line added to A3-R8C7, which is no longer
true of that bin.
"""
import argparse, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part                                     # noqa: E402
from stock.models import StockItem, StockLocation                # noqa: E402

PART, STOCK, DEST, OLD = 1140, 724, "A3-R7C4", "A3-R8C7"

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

dest = StockLocation.objects.get(name__iexact=DEST)
old = StockLocation.objects.get(name__iexact=OLD)
s = StockItem.objects.get(pk=STOCK)
print(f"stock #{s.pk} {s.part.name[:50]}")
print(f"  {s.location.name} -> {dest.name}")
print(f"  {dest.name} currently holds:")
for x in StockItem.objects.filter(location=dest):
    print(f"    [{x.pk}] {float(x.quantity):g}x {x.part.name[:52]}")
if not a.commit:
    raise SystemExit("\nDRY RUN — add --commit")

StockItem.objects.filter(pk=STOCK).update(location=dest)
Part.objects.filter(pk=PART).update(default_location=dest)
assert StockItem.objects.get(pk=STOCK).location_id == dest.pk, "move did not stick"
assert Part.objects.get(pk=PART).default_location_id == dest.pk, "home did not stick"
print(f"OK  moved to {dest.pathstring}")

# the destination now holds control-side as well as mains-side salvage
dd = dest.description or ""
if "control" not in dd.lower():
    StockLocation.objects.filter(pk=dest.pk).update(
        description=dd.rstrip().rstrip(".") + ". ALSO THE CONTROL-SIDE CONNECTOR "
        "off the same drive: an 18-way 3.5mm PCB-mount block. Grouped by WHERE IT "
        "CAME FROM rather than by pitch (Scott 2026-08-28) -- a salvage set is "
        "looked for by remembering the machine, not the pitch. Nothing in this bin "
        "mates with anything else in it.")
    assert "CONTROL-SIDE" in StockLocation.objects.get(pk=dest.pk).description
    print("OK  A3-R7C4 description updated")

# undo the oddments line on the old bin
od = old.description or ""
cut = od.find(". Also odd-pitch PCB terminal")
if cut > 0:
    StockLocation.objects.filter(pk=old.pk).update(description=od[:cut] + ".")
    assert "odd-pitch" not in StockLocation.objects.get(pk=old.pk).description
    print("OK  A3-R8C7 oddments line removed — no longer true")

# and correct the part's own note, which argued for the pitch bin
p = Part.objects.get(pk=PART)
n = p.notes.replace(
 "Filed here anyway because one "
 "salvaged connector does not earn its own drawer on a wall that is 89% full — "
 "but it will NOT mate with anything else in this bin.",
 "Originally filed with the 5.08mm blocks by pitch; moved to A3-R7C4 on Scott's "
 "call — no room there, and it belongs with the other connectors off the same "
 "drive. Provenance beats pitch for a salvage set: you go looking for it "
 "remembering the machine, not the millimetres. It mates with nothing else in "
 "the bin either way.")
Part.objects.filter(pk=PART).update(notes=n)
assert "Provenance beats pitch" in Part.objects.get(pk=PART).notes, "note did not stick"
print("OK  part note corrected")
