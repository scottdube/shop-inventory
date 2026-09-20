"""Fix a duplicate I created, then catalogue the bulk 24-way ribbon.

WHAT WENT WRONG: #1252 was created an hour ago as a new part when #43
'uxcell 2.54mm Female 30-Pin Flat Cable IDC Socket Connector' already
existed. I did run a duplicate check and #43 WAS in its result set - then I
piped the output through `tail -60` and the match scrolled off the top. The
guard worked; I threw the answer away.

MERGE DIRECTION: fold #43 into #1252, not the reverse. #43 is a purchase-
history stub - description 'pack: 10; via Amazon; last ordered 2025-01-06',
no stock, no SupplierPart, no default_location, no notes. #1252 carries the
stock row, the ASIN, pack_quantity_native=10, a home and the write-up. The
only thing #43 holds that #1252 does not is its order date, captured below.
#43 has NO SupplierPart, so no PO line can be orphaned by this.

#44 'Keszoox 2.54mm IDC Flat Ribbon Cable FC 30-pin F-F 30cm' is NOT a
duplicate of the bulk ribbon: it is a 30cm made-up assembly with sockets
already on both ends, 30-pin, sold 3 to a pack. Different thing. My guard
matched it on the words and was over-broad. Cross-referenced, not merged.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()
from part.models import Part, PartCategory
from stock.models import StockItem, StockLocation
from company.models import SupplierPart

COMMIT = '--commit' in sys.argv
FOLD, KEEP = 43, 1252

f = Part.objects.get(pk=FOLD); k = Part.objects.get(pk=KEEP)
print(f"fold [{f.pk}] {f.name!r} stock={f.total_stock} SPs={SupplierPart.objects.filter(part=f).count()}")
print(f"keep [{k.pk}] {k.name!r} stock={k.total_stock} SPs={SupplierPart.objects.filter(part=k).count()}")
if not COMMIT:
    print("\nDRY RUN - rerun with --commit"); sys.exit(0)

StockItem.objects.filter(part=f).update(part=k)
SupplierPart.objects.filter(part=f).update(part=k)
f.active = False
f.description = f"MERGED into part #{KEEP} - {(f.description or '')[:180]}"
f.notes = (f.notes or '') + """

MERGED into #1252 on 2026-09-20. Same product: uxcell 30-pin female flat
cable IDC socket, ASIN B00977GM2M, 10 per pack. This row was a purchase-
history stub with no stock, no SupplierPart and no home; #1252 has all three
plus the physical 9 pieces found in MC-T3.

Order date preserved from this row's original description: last ordered
2025-01-06, pack of 10."""
f.save()

k.notes = (k.notes or '') + """

2026-09-20: part #43 (purchase-history stub, 'uxcell 2.54mm Female 30-Pin
Flat Cable IDC Socket Connector') was MERGED INTO THIS PART. It recorded the
same uxcell product with no stock and no supplier link. Its order date -
last ordered 2025-01-06, pack of 10 - is preserved here.

Note for anyone reading #1252 as a fresh part: it is not. The 2025-01-06
purchase is the origin of the nine pieces in hand."""
k.save()

f2 = Part.objects.get(pk=FOLD); k2 = Part.objects.get(pk=KEEP)
print(f"\nAFTER fold [{f2.pk}] active={f2.active} stock={f2.total_stock}")
print(f"    desc: {f2.description[:80]}")
print(f"AFTER keep [{k2.pk}] active={k2.active} stock={k2.total_stock} "
      f"SPs={[(s.pk, s.SKU) for s in SupplierPart.objects.filter(part=k2)]}")
merge_ok = (not f2.active and f2.total_stock == 0 and k2.total_stock == 9
            and SupplierPart.objects.filter(part=k2).count() == 1)
print("MERGE VERIFIED" if merge_ok else "*** MERGE VERIFY FAILED ***")

# ---- now the bulk ribbon ----
NAME = 'Ribbon Cable Flat 24-way 1.27mm Grey, bulk'
DESC = ("Bulk flat ribbon cable, 24 conductors, 1.27mm (0.05in) pitch, grey "
        "with a red edge stripe. Jacket printed CSA AWM I A FT1 FT2 105C 300V. "
        "Mates 2x12 IDC sockets #1252. NOT the made-up 30-pin assembly #44.")
assert len(DESC) <= 250, f"description too long: {len(DESC)}"
NOTES = """Pulled from MC-T3 on 2026-09-20, the drawer being emptied.

LENGTH IS AN ESTIMATE AND SCOTT SAID SO: "Estimated 8'". Not measured off a
reel marking. Measure before committing it to a cut list. The CONDUCTOR
COUNT is his flat statement at the bench and is treated as measured: 24.

JACKET PRINT, read off a photo: CSA AWM I A FT1 FT2 105C 300V. The brand
ahead of that ends in "CRON" and could not be resolved from the image. Not
guessed into the record - read it off the cable next time it is in hand.

WHAT IT IS FOR. This, the 23 x 2x12 IDC sockets (#1251) and the 9 x 2x15 IDC
sockets (#1252) are ONE SET: the connector kit for the GMA1347 audio panel.
The G1000 build #3 BOM records that the 2x15 and 2x12 IDC box headers - J13
and J17 - and both ribbon cables were DROPPED when the audio panel came out
of that build. That is the project that was sitting in MC-T3.

If Scott takes the GMA1347 faceplate after all, this set comes back onto the
BOM together. Do not scatter it or write it off as surplus.

NOT a G1000 build #3 part as currently scoped.

RELATED, NOT THE SAME: #44 Keszoox 30-pin F-F 30cm is a made-up assembly with
sockets already fitted, sold 3 to a pack."""

cat = PartCategory.objects.get(pk=18)
HOME = StockLocation.objects.get(pk=407)
p = Part.objects.create(name=NAME, description=DESC, category=cat,
                        default_location=HOME, units='ft',
                        component=True, purchaseable=True, active=True)
p.notes = NOTES; p.save()
si = StockItem.objects.create(part=p, quantity=8, location=HOME)
si.notes = NOTES; si.save()

FIX = f"""

2026-09-20, PURPOSE FOUND. Part of the GMA1347 audio panel connector set with
the bulk 24-way ribbon, part #{p.pk}. The build #3 BOM records J13 (2x15) and
J17 (2x12) box headers and both ribbons as dropped when the audio panel left
that build. This supersedes the earlier note on #1252 that these "terminate
nothing the catalogue knows about" - the catalogue did know, in a doc rather
than a part record, which is exactly why a part search could not see it. The
narrower claim still true: no 2x15 box header is IN STOCK."""
for spk in (864, 866):
    s = StockItem.objects.get(pk=spk); s.notes = (s.notes or '') + FIX; s.save()
for ppk in (1251, 1252):
    q = Part.objects.get(pk=ppk); q.notes = (q.notes or '') + FIX; q.save()

p2 = Part.objects.get(pk=p.pk); s2 = StockItem.objects.get(pk=si.pk)
print(f"\nAFTER part {p2.pk}: {p2.name!r} units={p2.units!r} qty={s2.quantity} loc={s2.location.name}")
for x in (864, 866):
    print(f"  stock {x} patched: {'PURPOSE FOUND' in (StockItem.objects.get(pk=x).notes or '')}")
for x in (1251, 1252):
    print(f"  part  {x} patched: {'PURPOSE FOUND' in (Part.objects.get(pk=x).notes or '')}")
ok = s2.quantity == 8 and p2.units == 'ft' and 'GMA1347' in (p2.notes or '')
print("RIBBON VERIFIED" if ok else "*** RIBBON VERIFY FAILED ***")
