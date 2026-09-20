"""Attach the uxcell source to #1252 now that Scott found the listing.

ASIN B00977GM2M, 10 per pack, last purchased 2025-01-06, $8.09/pack.
Listing gives Pin/Position 30, Row Number 2, pitch 2.54mm, body 43x16x7mm.
That independently confirms the 30 pins Scott called at the bench.

Nine in hand out of a 10-pack reads as one used - stated as an inference,
not a fact: 'last purchased' does not rule out an earlier order.

pack_quantity written with .save() and re-read. A queryset .update() changes
the text field and NOT pack_quantity_native, which is the one receive reads.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()
from part.models import Part
from stock.models import StockItem
from company.models import Company, SupplierPart

COMMIT = '--commit' in sys.argv
p = Part.objects.get(pk=1252)
si = StockItem.objects.get(pk=866)
amazon = Company.objects.get(name='Amazon')

DESC = ("2.54mm IDC female socket for FLAT RIBBON CABLE, 2x15 = 30 positions, "
        "clamp termination, with strain-relief cover bar. Body 43x16x7mm. "
        "uxcell B00977GM2M, 10/pack. Mates a 2x15 box header - NONE in stock. "
        "Sibling of the 2x12 #1251.")
assert len(DESC) <= 250, f"description too long: {len(DESC)}"

ADD = """

SOURCE FOUND 2026-09-20: uxcell, Amazon ASIN B00977GM2M, 10 per pack, $8.09,
last purchased 2025-01-06. Listing specs - Pin/Position 30, Row Number 2,
pitch 2.54mm/0.1in, total size 43 x 16 x 7 mm, 44 g. The listing's 30 pins
agree with the count Scott called at the bench, two independent sources.

INFERENCE, NOT FACT: 9 in hand from a 10-pack suggests one was used. Amazon
says 'last purchased', which does not exclude an earlier order, and nobody
has looked for where the missing one went."""

print(f"before desc: {p.description}")
print(f"existing SupplierParts: {[(s.pk, s.SKU) for s in SupplierPart.objects.filter(part=p)]}")
dupe = SupplierPart.objects.filter(SKU='B00977GM2M')
print(f"ASIN already used by: {[(s.pk, s.part.pk, s.part.name) for s in dupe]}")
if not COMMIT:
    print("\nDRY RUN - rerun with --commit"); sys.exit(0)
if dupe.exists():
    print("ABORT - that ASIN is already attached somewhere"); sys.exit(1)

sp = SupplierPart.objects.create(part=p, supplier=amazon, SKU='B00977GM2M',
                                 description='uxcell 10 x 2.54mm Female 30 Pin Flat Cable IDC Socket Connector Black')
sp.pack_quantity = '10'
sp.save()

p.description = DESC
p.notes = (p.notes or '') + ADD
p.save()
si.notes = (si.notes or '') + ADD
si.save()

p2 = Part.objects.get(pk=1252); s2 = StockItem.objects.get(pk=866)
sp2 = SupplierPart.objects.get(pk=sp.pk)
print(f"\nAFTER SP{sp2.pk}: SKU={sp2.SKU} pack_quantity={sp2.pack_quantity!r} native={sp2.pack_quantity_native}")
print(f"AFTER part desc: {p2.description}")
print(f"AFTER part notes_len={len(p2.notes or '')} stock notes_len={len(s2.notes or '')}")
ok = (sp2.pack_quantity_native == 10 and 'uxcell' in p2.description
      and 'B00977GM2M' in (p2.notes or '') and 'B00977GM2M' in (s2.notes or ''))
print("VERIFIED" if ok else "*** VERIFY FAILED ***")
