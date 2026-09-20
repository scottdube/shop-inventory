"""#1251 goes home to L2-D2, and MC-T3 is recorded as a drawer being EMPTIED.

Scott, 2026-09-20: "I don't think we should keep anything in T3 - the goal
should be for this to be empty. This had a specific project sitting in it
that we're trying to empty out."

That reframes the whole MC-T3 pass. It was being treated as a count: find out
what is in the drawer and write down how many. It is actually a DESTINATION
exercise - every row has to leave, either in the Florida bag or to a home bin.
A counted row still parked at MC-T3 is not done. The location description says
so now, because the next session will otherwise re-derive the wrong goal from
a drawer full of tidy, counted, correct rows.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part
from stock.models import StockItem, StockLocation

COMMIT = "--commit" in sys.argv
HOME = Part.objects.get(pk=1249).default_location      # L2-D2, the box headers
MCT3 = StockLocation.objects.get(pk=432)
row = StockItem.objects.get(pk=864)

print("home bin resolved from #1249: %s (pk=%s)" % (HOME.name, HOME.pk))
print("#1251 default_location: %s -> %s" % (Part.objects.get(pk=1251).default_location, HOME.name))
print("row 864: %s -> %s" % (row.location.name, HOME.name))
print()
print("rows still parked at MC-T3 (all must leave):")
for si in StockItem.objects.filter(location=MCT3).order_by('pk'):
    fl = 'florida' in list(si.tags.names())
    print("   %s [%s] %-52s qty=%-6s %s" % (si.pk, si.part.pk, si.part.name[:52],
          si.quantity, 'FLORIDA BAG' if fl else '** needs a home **'))

if not COMMIT:
    print("\nDRY RUN - add --commit")
    sys.exit()

Part.objects.filter(pk=1251).update(default_location=HOME)
row.location = HOME
row.notes = """COUNTED by Scott 2026-09-20: 23, from a 25-pack.

Filed to L2-D2 on 2026-09-20 - Scott's call, next to the 2x6 box headers
(#1249). Came out of MC-T3, which is being emptied, not restocked.

The box's OTHER compartment holds loose black bars, probably the strain
reliefs for these connectors. NOT COUNTED AND NOT CATALOGUED - Scott has not
confirmed what they are. If they are strain reliefs they belong with these;
if they are a separate connector they need their own line."""
row.save()

DESC = ("MC-T3 IS BEING EMPTIED - THE TARGET IS ZERO ROWS. Scott, 2026-09-20: "
        "\"I don't think we should keep anything in T3... this had a specific "
        "project sitting in it that we're trying to empty out.\" It is a "
        "staging tray for the G1000 PFD build (#3, BO-0017), NOT a home for "
        "anything. A row here is either (a) in the Florida bag for the LRD "
        "build - tagged 'florida' - or (b) a stray that still needs a home "
        "bin. COUNTING A ROW DOES NOT FINISH IT; it has to leave. Do not set "
        "any part's default_location to MC-T3. Spares deliberately live "
        "elsewhere: six leftover shields and two redundant FlightSimDIY "
        "control boards are at WS2-S4/Sim G1000 Spares. Still unexamined in "
        "this tray: bulk IDC flat cable and the ConnectorsPro kit. "
        "[6 x 4-9/16 x 2-3/16 in, large]")
StockLocation.objects.filter(pk=432).update(description=DESC)

p = Part.objects.get(pk=1251)
row = StockItem.objects.get(pk=864)
loc = StockLocation.objects.get(pk=432)
print("\n#1251 defloc = %s" % p.default_location.name)
print("row 864 loc  = %s qty=%s" % (row.location.name, row.quantity))
print("MC-T3 desc starts: %s" % loc.description[:52])
ok = (p.default_location_id == HOME.pk and row.location_id == HOME.pk
      and loc.description.startswith("MC-T3 IS BEING EMPTIED"))
print("VERIFIED" if ok else "MISMATCH - stop and look")
print("\nMC-T3 now holds %d rows:" % StockItem.objects.filter(location=loc).count())
for si in StockItem.objects.filter(location=loc).order_by('pk'):
    fl = 'florida' in list(si.tags.names())
    print("   %s [%s] %-50s %s" % (si.pk, si.part.pk, si.part.name[:50],
          'florida' if fl else '** STRAY **'))
