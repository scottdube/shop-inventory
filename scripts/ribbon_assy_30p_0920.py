"""Stock the two made-up 30-pin F-F ribbon assemblies against #44.

Scott: "two one foot by 30 pin IDC ribbon cables" ... "with connectors".
Both figures are his, at the bench, and treated as measured.

IDENTIFICATION. A full untruncated candidate sweep over ribbon / flat cable /
idc / 30-pin / 30p / fc-30 across names AND descriptions returned 14 parts
and exactly ONE made-up 30-pin assembly: #44, Keszoox FC 30-pin F-F 30cm,
3 per pack, ordered 2024-06-30, zero stock.

The one soft spot, stated rather than buried: Scott said ONE FOOT and #44 is
30cm = 11.8in. Those are the same cable in every vendor listing, but they are
not the same number. If these measure a true 12.0in they are not #44.

Renaming for the label. 'Keszoox 2.54mm IDC Flat Ribbon Cable FC 30-pin F-F
30cm' truncates at template 12's ~40 chars to '...Flat Ribbon Cable FC', which
throws away 30-pin, F-F and the length - every discriminating fact. Same
failure as the PropWash encoder this morning.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()
from part.models import Part
from stock.models import StockItem, StockLocation
from company.models import Company, SupplierPart

COMMIT = '--commit' in sys.argv
p = Part.objects.get(pk=44)
HOME = StockLocation.objects.get(pk=407)
amazon = Company.objects.get(name='Amazon')
ASIN = 'B0CP5XP4VX'

NEWNAME = 'Ribbon Cable Assy 30P F-F 30cm, sockets both ends'
DESC = ("Made-up flat ribbon cable assembly, 30 conductors (2x15), 1.27mm "
        "pitch, 30cm / ~1ft, with a 2.54mm IDC female socket already fitted "
        "at BOTH ends. Keszoox, 3 per pack. NOT bulk cable - that is #1253.")
assert len(DESC) <= 250, f"description too long: {len(DESC)}"

NOTES = """

=== STOCKED 2026-09-20 ===
Two in hand, Scott at the bench: "two one foot by 30 pin IDC ribbon cables",
"with connectors". Count and pin count are his and are treated as measured.

TWO OF A THREE-PACK reads as one used. That is an INFERENCE - nobody has
looked for the third.

LENGTH CAVEAT: Scott said one foot; this part is 30cm = 11.8in. Same cable in
every listing, but not the same number. A true 12.0in measurement would mean
these are not #44.

WHERE IT FITS. This is the J13 leg of the GMA1347 audio panel connector set
that filled MC-T3:
  J13, 2x15 / 30-pin : THIS made-up assembly, plus 9 loose sockets (#1252)
                       for cutting a custom length
  J17, 2x12 / 24-pin : 23 loose sockets (#1251) + bulk 24-way ribbon (#1253)
The build #3 BOM records J13, J17 and both ribbons as dropped when the audio
panel left that build. If the GMA1347 faceplate goes to Florida, this comes
back on the BOM with the rest of the set.

Renamed from 'Keszoox 2.54mm IDC Flat Ribbon Cable FC 30-pin F-F 30cm'. The
old name truncated on a 62mm label to '...Flat Ribbon Cable FC', dropping
30-pin, F-F and the length - every fact that tells it from #1253."""

print(f"[{p.pk}] {p.name!r}")
print(f"  active={p.active} stock={p.total_stock} defloc={p.default_location}")
print(f"  existing SPs: {[(s.pk, s.SKU) for s in SupplierPart.objects.filter(part=p)]}")
print(f"  ASIN {ASIN} used by: {[(s.pk, s.part.pk) for s in SupplierPart.objects.filter(SKU=ASIN)]}")
if not COMMIT:
    print("\nDRY RUN - rerun with --commit"); sys.exit(0)

if not SupplierPart.objects.filter(SKU=ASIN).exists():
    sp = SupplierPart.objects.create(part=p, supplier=amazon, SKU=ASIN,
                                     description='Keszoox 2.54mm IDC Flat Ribbon Cable FC 30-pin F-F 30cm')
    sp.pack_quantity = '3'
    sp.save()

p.name = NEWNAME
p.description = DESC
p.default_location = HOME
p.notes = (p.notes or '') + NOTES
p.save()

si = StockItem.objects.create(part=p, quantity=2, location=HOME)
si.notes = NOTES.strip()
si.save()

p2 = Part.objects.get(pk=44); s2 = StockItem.objects.get(pk=si.pk)
sp2 = SupplierPart.objects.get(SKU=ASIN)
print(f"\nAFTER part 44: {p2.name!r}")
print(f"  desc: {p2.description}")
print(f"  defloc={p2.default_location.name} stock={p2.total_stock}")
print(f"  SP{sp2.pk} SKU={sp2.SKU} pack={sp2.pack_quantity!r} native={sp2.pack_quantity_native}")
print(f"AFTER stock {s2.pk}: qty={s2.quantity} loc={s2.location.name} notes_len={len(s2.notes or '')}")
ok = (p2.name == NEWNAME and p2.default_location_id == HOME.pk and s2.quantity == 2
      and sp2.pack_quantity_native == 3 and sp2.part_id == 44)
print("VERIFIED" if ok else "*** VERIFY FAILED ***")
