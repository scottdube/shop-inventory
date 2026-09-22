"""2026-09-22  Four DE-9 solder-cup sockets onto the bin wall at B3-R3C7.

Identity read off the photo: 9-position D-subminiature, blue insulator,
nickel shell with a 2-hole flange, solder cups (no PCB legs, no crimp
housings, no jack screws). Count of 4 and "all female" came from Scott, not
the photograph - two were visibly sockets and two were face-down.

Rejected: calling it DB9. DB is the D-sub SHELL size that carries 25
positions; a 9-position part is DE shell. The name says DE-9 and the
keywords carry DB9 so a search for the wrong-but-universal term still
lands here.

Rejected: one part covering both genders. A plug and a socket are not
interchangeable pieces, so they would never share a stock row even if
both were on hand. Only sockets are.

Rejected: a supplier part. No PO line and no packaging - provenance is
unknown, and inventing a vendor would put a fact in the record that
nobody established.

Rejected: category Electronics/Connectors (pk 60, 5 parts). The flat
Connectors root (pk 18, 79 parts) is where every comparable crimp/solder
connector already lives.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()

from part.models import Part, PartCategory
from stock.models import StockItem, StockLocation

COMMIT = "--commit" in sys.argv

NAME = "D-Sub DE-9 Socket, 9-position Female, solder cup"
DESC = ("9-position D-subminiature socket (DE-9 / commonly DB9), female contacts, "
        "solder-cup termination, blue insulator, nickel shell with 2-hole flange. "
        "No jack screws or backshell included.")
KEYWORDS = "DB9 DE9 DE-9 D-sub DSUB serial RS232 RS-232 9-pin socket female solder cup"
CAT_PK = 18
LOC_PATH = "SLN/Bin Wall/B3/B3-R3C7"
QTY = 4

cat = PartCategory.objects.get(pk=CAT_PK)
loc = None
for l in StockLocation.objects.all():
    if l.pathstring == LOC_PATH:
        loc = l
        break
assert loc is not None, "location not found: %s" % LOC_PATH
print("category : %s (pk=%s)" % (cat.pathstring, cat.pk))
print("location : %s (pk=%s)" % (loc.pathstring, loc.pk))

dupes = Part.objects.filter(name__iexact=NAME)
print("dupe check by exact name: %d" % dupes.count())
for d in dupes:
    print("   EXISTING pk=%s active=%s qty=%s" % (d.pk, d.active, d.total_stock))

if not COMMIT:
    print()
    print("DRY RUN -- would create:")
    print("   name  : %s" % NAME)
    print("   desc  : %s" % DESC)
    print("   cat   : %s" % cat.pathstring)
    print("   home  : %s" % loc.pathstring)
    print("   stock : %d pieces at %s" % (QTY, loc.pathstring))
    sys.exit(0)

if dupes.exists():
    part = dupes.first()
    print("reusing existing part %s" % part.pk)
else:
    part = Part.objects.create(
        name=NAME, description=DESC, keywords=KEYWORDS,
        category=cat, default_location=loc,
        component=True, purchaseable=True, active=True,
    )
    print("created part pk=%s" % part.pk)

# --- verify the part row actually wrote (this install has lied about .save())
part.refresh_from_db()
ok = True
for f, want in (("name", NAME), ("description", DESC), ("keywords", KEYWORDS)):
    got = getattr(part, f)
    if got != want:
        ok = False
        print("   MISMATCH %s: %r" % (f, got))
if part.category_id != cat.pk:
    ok = False; print("   MISMATCH category: %s" % part.category_id)
if part.default_location_id != loc.pk:
    ok = False; print("   MISMATCH default_location: %s" % part.default_location_id)
print("part fields verified: %s" % ("OK" if ok else "FAILED"))

# --- one stock row per part per location: merge, never add a second
existing = StockItem.objects.filter(part=part, location=loc)
if existing.exists():
    si = existing.first()
    before = si.quantity
    si.quantity = before + QTY
    si.save()
    si.refresh_from_db()
    print("merged into stock %s: %s -> %s" % (si.pk, before, si.quantity))
else:
    si = StockItem.objects.create(part=part, location=loc, quantity=QTY)
    si.refresh_from_db()
    print("created stock pk=%s qty=%s at %s" % (si.pk, si.quantity, si.location.pathstring))

part.refresh_from_db()
print()
print("READBACK  part %s  total_stock=%s  home=%s"
      % (part.pk, part.total_stock, part.default_location.pathstring))
for s in StockItem.objects.filter(part=part):
    print("          stock %s qty=%s at %s" % (s.pk, s.quantity, s.location.pathstring if s.location else "-"))
print("URL http://192.168.50.10:8001/web/part/%s" % part.pk)
