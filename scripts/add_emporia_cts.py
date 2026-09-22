"""2026-09-22  Emporia Vue 3 leftover current transformers onto the bin wall.

Provenance, read off Amazon rather than assumed: order 113-7086030-7655409,
placed 2026-07-04, delivered 07-06, ASIN B0C79PNK84, "Emporia Vue 3 Home
Energy Monitor", $191.48, sold by Emporia Corp. Amazon's own bullet for that
ASIN: "Comes with sixteen branch (50A) sensors". Scott confirmed these four
50A and two 200A clamps are leftovers from that kit's install.

Counts came from Scott (4 and 2). Nothing here was counted from a photograph.

Rejected: a supplier part on either CT. B0C79PNK84 is the whole kit - monitor,
sixteen branch CTs and the mains pair - which makes it an ASSORTMENT, not a
multipack. Hanging that SKU on one clamp books $191.48 against a single piece,
which is the exact failure CLAUDE.md records for pack_quantity. The order lives
in the notes instead.

Rejected: a per-CT purchase price. Dividing the kit price across the CTs and
the monitor would put a number in the record that nobody measured, and the
monitor is most of the value.

Rejected: one part for both ratings. A 50A branch clamp and a 200A mains clamp
are not interchangeable pieces and could never share a stock row.

Rejected: category Electronics/Sensors (pk 64, 8 parts) for the flat Sensors
root (pk 21, 34 parts), which is where the other whole-device sensors live.

Rejected: B3, the electronics cabinet - all twelve of its large drawers have
contents recorded. Rejected B1 (metric fasteners). B2's large bottom rows are
already general bulky storage, not fasteners: B2-R5C1 holds a 775 DC motor and
B2-R7C1 holds springs. B2-R6C1/C2 are adjacent so the pair reads as one family.

NOTE: both drawers have NOTHING RECORDED in them, which is not the same as
verified empty. Scott confirms by eye when he files them.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()

from part.models import Part, PartCategory
from stock.models import StockItem, StockLocation

COMMIT = "--commit" in sys.argv
CAT_PK = 21
ORDER = "Amazon order 113-7086030-7655409, placed 2026-07-04, delivered 2026-07-06."
KIT = ("From the Emporia Vue 3 kit, ASIN B0C79PNK84, $191.48 for the whole kit "
       "(monitor + sixteen 50A branch CTs + mains pair). Left over from the SLN "
       "panel install. No supplier part and no unit price on purpose: the ASIN is "
       "an assortment, not a multipack, so a per-piece cost would be invented.")

SPEC = [
    dict(name="Current Transformer 50A split-core, Emporia Vue branch sensor",
         desc=("50A split-core clamp-on current transformer, Emporia Vue branch-circuit "
               "sensor. Flying lead with screw-terminal/port termination at the monitor."),
         kw="CT current transformer 50A split core clamp Emporia Vue branch circuit energy monitor",
         loc="SLN/Bin Wall/B2/B2-R6C1", qty=4),
    dict(name="Current Transformer 200A split-core, Emporia Vue mains sensor",
         desc=("200A split-core clamp-on current transformer, Emporia Vue mains sensor. "
               "Larger body than the 50A branch clamps."),
         kw="CT current transformer 200A split core clamp Emporia Vue mains main energy monitor",
         loc="SLN/Bin Wall/B2/B2-R6C2", qty=2),
]

cat = PartCategory.objects.get(pk=CAT_PK)
paths = {l.pathstring: l for l in StockLocation.objects.all()}
print("category: %s (pk=%s)\n" % (cat.pathstring, cat.pk))

for s in SPEC:
    loc = paths.get(s["loc"])
    assert loc is not None, "no such location: %s" % s["loc"]
    dupes = Part.objects.filter(name__iexact=s["name"])
    print("%-62s -> %s (pk=%s)  dupes=%d" % (s["name"][:62], loc.name, loc.pk, dupes.count()))
    existing_rows = StockItem.objects.filter(location=loc).count()
    print("    drawer currently has %d stock rows recorded (NOT a claim it is empty)" % existing_rows)
    if not COMMIT:
        print("    DRY RUN: would create part + %d pieces\n" % s["qty"])
        continue

    if dupes.exists():
        part = dupes.first(); print("    reusing part %s" % part.pk)
    else:
        part = Part.objects.create(
            name=s["name"], description=s["desc"], keywords=s["kw"],
            category=cat, default_location=loc,
            notes="%s\n\n%s" % (ORDER, KIT),
            component=True, purchaseable=True, active=True,
        )
        print("    created part pk=%s" % part.pk)

    part.refresh_from_db()
    bad = [f for f, want in (("name", s["name"]), ("description", s["desc"]),
                             ("keywords", s["kw"])) if getattr(part, f) != want]
    if part.default_location_id != loc.pk: bad.append("default_location")
    if part.category_id != cat.pk: bad.append("category")
    if not (part.notes or "").startswith(ORDER): bad.append("notes")
    print("    fields verified: %s" % ("OK" if not bad else "FAILED %s" % bad))

    row = StockItem.objects.filter(part=part, location=loc).first()
    if row:
        before = row.quantity
        row.quantity = before + s["qty"]; row.save(); row.refresh_from_db()
        print("    merged stock %s: %s -> %s" % (row.pk, before, row.quantity))
    else:
        row = StockItem.objects.create(part=part, location=loc, quantity=s["qty"])
        row.refresh_from_db()
        print("    created stock %s qty=%s at %s" % (row.pk, row.quantity, row.location.pathstring))

    part.refresh_from_db()
    print("    READBACK total_stock=%s home=%s" % (part.total_stock, part.default_location.pathstring))
    print("    http://192.168.50.10:8001/web/part/%s\n" % part.pk)
