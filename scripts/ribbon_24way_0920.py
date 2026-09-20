"""Catalogue the bulk 24-way ribbon from MC-T3 and name what the set is for.

Scott: 24 pin, "Estimated 8'". He flagged the length himself, so it is an
ESTIMATE and recorded as one; the conductor count he gave flat, so it is a
measurement.

THE FINDING THIS CLOSES: the 2x12 sockets (#1251, 23 pcs), the 2x15 sockets
(#1252, 9 pcs) and this ribbon are one set. The build #3 BOM says the 2x15
and 2x12 IDC box headers - J13 and J17 - and BOTH RIBBON CABLES were dropped
along with the GMA1347 audio panel. That is the "specific project sitting in
MC-T3" Scott was emptying. They are audio-panel stock, not orphans.

Corrects what I wrote on #1252 an hour ago: "they terminate nothing the
catalogue knows about". Wrong framing - the catalogue did know, in a doc
rather than in a part record. The 2x15 still has no mating header IN STOCK,
which is the narrower true claim.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()
from part.models import Part, PartCategory
from stock.models import StockItem, StockLocation

COMMIT = '--commit' in sys.argv

dupes = (Part.objects.filter(name__icontains='ribbon').filter(name__icontains='cable') |
         Part.objects.filter(name__icontains='flat cable'))
dupes = [p for p in dupes.distinct() if 'jumper' not in p.name.lower()]
print("duplicate guard:", [(p.pk, p.name) for p in dupes] or "none")
if dupes and COMMIT:
    print("ABORT - possible duplicate"); sys.exit(1)

NAME = 'Ribbon Cable Flat 24-way 1.27mm Grey, bulk'
DESC = ("Bulk flat ribbon cable, 24 conductors, 1.27mm (0.05in) pitch, grey "
        "with a red edge stripe. Jacket printed CSA AWM I A FT1 FT2 105C 300V. "
        "Mates the 2x12 IDC sockets #1251 and 2x12 box headers #96.")
assert len(DESC) <= 250, f"description too long: {len(DESC)}"

NOTES = """Pulled from MC-T3 on 2026-09-20, the drawer being emptied.

LENGTH IS AN ESTIMATE AND SCOTT SAID SO: "Estimated 8'". Not measured, not
counted off a reel marking. Measure it before committing it to a cut list.
The CONDUCTOR COUNT is his flat statement at the bench and is treated as
measured: 24.

JACKET PRINT, read off a photo: CSA AWM I A FT1 FT2 105C 300V. The brand
ahead of that ends in "CRON" and could not be resolved from the image - do
not guess it into the record.

WHAT IT IS FOR. This, the 23 x 2x12 IDC sockets (#1251) and the 9 x 2x15 IDC
sockets (#1252) are one set: the connector kit for the GMA1347 audio panel.
The G1000 build #3 BOM records that the 2x15 and 2x12 IDC box headers - J13
and J17 - and both ribbon cables were DROPPED when the audio panel came out
of that build. That is the project that was sitting in MC-T3.

SO: if Scott takes the GMA1347 faceplate after all, this set comes back onto
the BOM together. Do not scatter it or write it off as surplus.

NOT a G1000 build #3 part as currently scoped."""

cat = PartCategory.objects.get(pk=18)
HOME = StockLocation.objects.get(pk=407)
print(f"would create {NAME!r} units=ft qty=8 @ {HOME.pathstring}")
if not COMMIT:
    print("\nDRY RUN - rerun with --commit"); sys.exit(0)

p = Part.objects.create(name=NAME, description=DESC, category=cat,
                        default_location=HOME, units='ft',
                        component=True, purchaseable=True, active=True)
p.notes = NOTES; p.save()
si = StockItem.objects.create(part=p, quantity=8, location=HOME)
si.notes = NOTES; si.save()

# correct the two socket rows now that the set has a purpose
FIX = """

2026-09-20, LATER THE SAME DAY - PURPOSE FOUND. This is part of the GMA1347
audio panel connector set, together with the bulk 24-way ribbon catalogued as
part #%d. The build #3 BOM records J13 (2x15) and J17 (2x12) box headers and
both ribbons as dropped when the audio panel left that build.

This supersedes the earlier note on #1252 saying these "terminate nothing the
catalogue knows about". The catalogue did know - in a doc, not in a part
record, which is why a part search could not see it. The narrower claim that
is still true: no 2x15 box header is IN STOCK.""" % p.pk

for spk in (864, 866):
    s = StockItem.objects.get(pk=spk)
    s.notes = (s.notes or '') + FIX; s.save()
for ppk in (1251, 1252):
    q = Part.objects.get(pk=ppk)
    q.notes = (q.notes or '') + FIX; q.save()

p2 = Part.objects.get(pk=p.pk); s2 = StockItem.objects.get(pk=si.pk)
print(f"\nAFTER part {p2.pk}: {p2.name!r} units={p2.units!r} defloc={p2.default_location.name}")
print(f"AFTER stock {s2.pk}: qty={s2.quantity} loc={s2.location.name} notes_len={len(s2.notes or '')}")
for x in (864, 866):
    print(f"  stock {x} note patched: {'PURPOSE FOUND' in (StockItem.objects.get(pk=x).notes or '')}")
for x in (1251, 1252):
    print(f"  part  {x} note patched: {'PURPOSE FOUND' in (Part.objects.get(pk=x).notes or '')}")
ok = (s2.quantity == 8 and s2.location_id == HOME.pk and p2.units == 'ft'
      and 'GMA1347' in (p2.notes or ''))
print("VERIFIED" if ok else "*** VERIFY FAILED ***")
