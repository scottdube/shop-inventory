"""Four multi-conductor hookup cables into B-01, with purchased lengths.

Identified from Scott's Amazon order history 2026-08-24 -- none of the four was
in the catalogue and none appears on any PO, so the order pages are the only
record of what was bought.

Quantities are the PURCHASED lengths, marked [ESTIMATE], because Scott reports
barely any has been used and nothing has been measured. Knowingly a little
high, and said so on each row rather than shaved by a guess -- a fabricated
subtraction is not more honest than an acknowledged ceiling.

units='ft' so a cut can be entered as "18 in" and converted, same as the sleeve.
These are loose coils with NO reel, which is what makes the weighing route work
later: coil weight IS cable weight, so grams / purchased-feet gives g/ft with
nothing cut and no tare to find.
"""
import argparse, datetime, os, sys
import django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.db.models import Q                         # noqa: E402
from part.models import Part, PartCategory             # noqa: E402
from stock.models import StockItem, StockLocation      # noqa: E402

WIRES = [
    dict(name="Multi-Conductor Cable 24 AWG 4-core, white PVC",
         ft=30, ordered="2026-06-07", sheath="white",
         desc=("24 AWG 4-conductor cable, white PVC sheath, tinned copper "
               "stranded. 30 ft as bought. Low-voltage runs needing four wires "
               "in one jacket — LED, 12/24V, sensor runs."),
         listing="24 Gauge Wire 4 Conductor Electrical Wire 30FT, 24 AWG 4 Core Cable Tinned Copper/PVC Flexible/Stranded 24/4"),
    dict(name="Multi-Conductor Cable 24 AWG 3-core, black UL2464",
         ft=25, ordered="2024-01-14", sheath="black",
         desc=("24 AWG 3-conductor UL2464 cable, black sheath, cores red/black/"
               "yellow. 25 ft as bought. Power-plus-signal runs where three "
               "wires should stay together."),
         listing="24AWG 25Ft UL 2464 Audio Power Cable Copper Wire 3 Conductors Red & Black & Yellow (24-3C-25ft)"),
    dict(name="Multi-Conductor Cable 28 AWG 3-core, black UL2464",
         ft=25, ordered="2024-01-14", sheath="black",
         desc=("28 AWG 3-conductor UL2464 cable, black sheath, cores red/black/"
               "yellow. 25 ft as bought. The thin one — signal runs where 24 "
               "AWG is bulkier than it needs to be."),
         listing="28AWG UL2464 Power Cable LED Red & Black & Yellow 3 Conductors 25ft"),
    dict(name="Multi-Conductor Cable 20 AWG 2-core, black PVC",
         ft=100, ordered="2023-06-25", sheath="black",
         desc=("20 AWG 2-conductor cable, black PVC sheath, oxygen-free copper "
               "stranded. 100 ft as bought. The heaviest of the four — LED "
               "strip and lamp runs where 24 AWG would drop too much volts."),
         listing="20 Gauge 2 Conductor Electrical Wire 20AWG Stranded PVC Oxygen-free copper 100FT/30.5M (20/2AWG-100FT)"),
]

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

loc = StockLocation.objects.get(name="B-01")
cat = (PartCategory.objects.filter(name__icontains="cable").first()
       or PartCategory.objects.filter(name__icontains="wire").first()
       or Part.objects.get(pk=342).category)
print(f"category {cat}\nlocation {loc.pathstring}\n")

for w in WIRES:
    dupe = Part.objects.filter(Q(name__iexact=w["name"]))
    assert len(w["desc"]) <= 250, f"{w['name']}: desc {len(w['desc'])} chars"
    print(f"  {w['name'][:56]:56} {w['ft']:>4} ft  dupe={dupe.count()}")
    if dupe.exists():
        print("!! duplicate — stopping"); raise SystemExit(1)

if not a.commit:
    print("\nDRY RUN"); raise SystemExit

for w in WIRES:
    p = Part.objects.create(
        name=w["name"], description=w["desc"], category=cat,
        default_location=loc, active=True, units="ft",
        keywords=("multi-conductor, multicore, hookup wire, cable, sheathed, "
                  f"{w['sheath']}, UL2464, low voltage, LED wire"),
        notes=(f"## As bought\n\n**{w['ft']} ft**, Amazon, ordered "
               f"**{w['ordered']}**. Listing:\n\n> {w['listing']}\n\n"
               f"Found in Scott's order history 2026-08-24 — this cable was not "
               f"in the catalogue and is on no purchase order, so the order page "
               f"is the only record of it.\n\n## On-hand figure\n\nThe quantity "
               f"is the PURCHASED length, not a measurement. Scott, 2026-08-24: "
               f"barely any has been used. Knowingly a little high, and left "
               f"that way — a guessed subtraction would not be more honest than "
               f"an acknowledged ceiling.\n\n**To make it real without cutting "
               f"anything:** these are loose coils with no reel, so the coil "
               f"weight IS the cable weight. Weigh it, divide by {w['ft']} ft "
               f"for g/ft, and every later weighing gives absolute feet with no "
               f"tare and no waste.\n"))
    f = Part.objects.get(pk=p.pk)
    assert f.units == "ft" and f.default_location_id == loc.pk
    si = StockItem.objects.create(
        part=f, location=loc, quantity=w["ft"],
        notes=(f"[ESTIMATE] {w['ft']} ft is the PURCHASED length (Amazon, "
               f"{w['ordered']}), not a measurement. Scott reports barely any "
               f"used, 2026-08-24. No stocktake_date: nobody has measured or "
               f"weighed it. Weigh the coil to convert this into a real figure "
               f"— no reel, so coil weight is cable weight."))
    c = StockItem.objects.get(pk=si.pk)
    assert float(c.quantity) == w["ft"] and c.stocktake_date is None
    print(f"OK  #{f.pk} {f.name[:50]:50} stock #{c.pk} {w['ft']} ft")

NEWDESC = ("WIRE & SLEEVING. Multi-conductor hookup cable and wire sleeving. "
           "BIN B-01 — Sterilite 6qt clear, snap-on lid, on WS2-S3 with the "
           "wire. A HOME — things here get default_location. The BIN is the "
           "location and the ID travels WITH the bin, so moving it to another "
           "shelf is a re-parent, not a rename. Established 2026-08-24.")
StockLocation.objects.filter(pk=loc.pk).update(description=NEWDESC)
assert StockLocation.objects.get(pk=loc.pk).description == NEWDESC
print(f"\nOK  B-01 re-described: wire AND sleeving")
