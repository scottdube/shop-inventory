"""Create the GMA1347's own consumption record. Scott, 2026-09-21: "yes".

Mirrors BO-0020's role but not its mistake. BO-0020 carried ONE of the ~24
parts its panel consumed and nothing said so on the face of it, which cost
Scott a morning of "I don't know which is which" (docs/TRAPS.md). So this
record is built the other way round: the BOM carries every line FSD's parts
list names, and the build order's NOTES enumerate, by name, the lines that
could NOT be resolved to a catalogue part. A record that states its own gaps
is not a partial record.

NOTHING IS ALLOCATED AND NOTHING IS CONSUMED. Allocation needs the count
basis decided per line (docs/G1000.md), and stock does not move until the
build is completed, so this is reversible in full.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part, PartCategory, BomItem
from build.models import Build

COMMIT = "--commit" in sys.argv

RESOLVED = [
    (1156, 1,  "PCB, GMA1347 Control Board v2.2"),
    (74,   1,  "Arduino Mega2560 Pro Mini - FSD names this exact board"),
    (95,   1,  "Dual shaft encoder EC11EBB24C03"),
    (98,   22, "White LED tactile 6x6x7"),
    (760,  21, "2x5x7mm white diffused rectangular LED"),
    (1158, 23, "M2 x 5 mm screw - NOTE only 16 on hand, fewer than this panel "
               "consumed, so that row cannot be the source without going "
               "negative. Quantity is FSD's requirement, not a claim on stock."),
]

UNRESOLVED = """UNRESOLVED LINES - named here so this record cannot be mistaken for complete:

  28 x Resistor 150 ohm - TWO candidates and the choice is not obvious.
       #949 150R 1% 1/2W (81 on hand, tallied, docs record it as bought
       specifically for these boards) vs #609 150R 1% 1/4W (28 on hand,
       [ESTIMATE], lives in the EAONE 30-value kit). Ask Scott which went in.
   5 x M2 x 20 mm screw - NO SUCH PART EXISTS in the catalogue. Create it
       before this line can be carried.
   2 x M5 bolt 20mm or longer - #1032 M5 socket head is plausible, unconfirmed.
   2 x M5 nut and 2 x M5 washer - no clean M5 hex nut; #1037 washer is an
       [ESTIMATE] row. Both unconfirmed.
   1 x IDC ribbon cable 24 pin and 1 x 30 pin, 6-8 inch - #1251 (2x12/24P) and
       #1252 (2x15/30P) are the crimp SOCKETS; the cable itself is a separate
       line and was not matched.
       2.54mm header pins male/female, various lengths - #40 exists at 0 on hand.

ALSO FOUND: #97 "2x5x7mm White Diffused Rectangular LED" (0 stock) and #760
"LED 2x5x7mm White Diffused Rectangular" (75 on hand) are the same component
entered twice. #760 is used here. The duplicate wants merging."""

NOTES = ("[RECONSTRUCTED] 2026-09-21. The GMA1347 audio panel was built before "
         "this system existed - docs/G1000.md records it BUILT from Scott's "
         "2026-08-29 count of the physical pile.\n\n"
         "**The physical build date is unknown.** Do not compare stocktake "
         "dates against anything here.\n\n"
         "BOM SOURCE: FSD's own GMA1347 parts list, attached to part #1156, "
         "pulled 2026-09-21 from flightsimdiy.com/fsd-downloads/ - a PUBLIC "
         "download, not the $8.99 entitlement FSD removed from the account.\n\n"
         "NOTHING IS ALLOCATED YET. Allocating needs the count basis decided "
         "per line: a TALLIED row already excludes what this panel ate and "
         "must be inflated first, an [ESTIMATE] row still contains it and is "
         "allocated straight out, and a row with no marker must not be guessed "
         "either way. See docs/G1000.md.\n\n"
         "SCOPE: the panel's own faceplate parts. The SECOND Mega2560 on "
         "Peter's shield belongs to the MFD (BO-0020), which is Peter's "
         "documented reason the PFD shield needs only one.\n\n" + UNRESOLVED)

print("=== would create ===")
print("PART  'Sim G1000 GMA1347' (assembly)")
print("BUILD 'Sim G1000 GMA1347 - consumption record'  status Production, 0 allocations")
for pk, qty, why in RESOLVED:
    p = Part.objects.get(pk=pk)
    print("  BOM %-4s x #%-5s %s" % (qty, pk, p.name[:46]))
print("\n" + UNRESOLVED)

if Part.objects.filter(name="Sim G1000 GMA1347").exists():
    print("\nABORT: part already exists"); sys.exit(1)

if not COMMIT:
    print("\nDRY RUN - add --commit"); sys.exit()

tmpl = Part.objects.get(pk=1255)
part = Part.objects.create(
    name="Sim G1000 GMA1347",
    description="[RECONSTRUCTED] GMA1347 audio panel, built before InvenTree. "
                "BOM from FSD's own published parts list, not inferred.",
    category=tmpl.category, assembly=True, component=False, purchaseable=False,
    active=True)
for pk, qty, why in RESOLVED:
    BomItem.objects.create(part=part, sub_part=Part.objects.get(pk=pk),
                           quantity=qty, note=why[:250])
build = Build.objects.create(part=part, title="Sim G1000 GMA1347 - consumption record",
                             quantity=1, status=20, notes=NOTES)

part = Part.objects.get(pk=part.pk); build = Build.objects.get(pk=build.pk)
print("\n=== re-read ===")
print("part  #%s %r assembly=%s" % (part.pk, part.name, part.assembly))
print("BOM lines: %d" % BomItem.objects.filter(part=part).count())
for b in BomItem.objects.filter(part=part):
    print("   %-6s x #%s %s" % (b.quantity, b.sub_part.pk, b.sub_part.name[:44]))
print("build %s %r status=%s" % (build.reference, build.title, build.status))
print("notes carry UNRESOLVED: %s" % ("UNRESOLVED LINES" in (build.notes or "")))
