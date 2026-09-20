"""Catalogue the Guzon waxed lacing tape.

Scott: "nearly full". That is a FILL STATE, not a length, and it is recorded
as one. The spool is nominally 260 m; nobody has measured what is left and
260 m of 0.8 mm tape is not something anyone is going to measure. So the
stock row is 1 SPOOL and the fullness lives in the notes.

Rejected: storing 260 as a quantity in metres, or guessing "about 230". Both
would turn Scott's two words into a number the record cannot support, and
every later report would treat it as measured. This is the same failure as
dividing a kit label by its value count.

Price $9.99 read LIVE off the listing 2026-09-20, so it takes no +40%
estimate escalator.

Duplicate guard: narrow terms (lacing / waxed / guzon / lace tape / wax
thread / tying cord) across name, description and notes, plus the ASIN.
One hit, a false positive - "lacing" inside "replacing" in the depinning
tool's notes. Read whole, not tailed.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()
from part.models import Part, PartCategory
from stock.models import StockItem, StockLocation
from company.models import Company, SupplierPart

COMMIT = '--commit' in sys.argv
ASIN = 'B01L6SMDU4'

NAME = 'Lacing Tape, waxed flat polyester 0.8mm black, 260m spool'
DESC = ("Waxed flat lacing tape for tying wire harnesses, black polyester, "
        "0.8mm wide, 150D, 260m nominal spool (spool 10.5 x 5cm). Guzon, "
        "ASIN B01L6SMDU4, $9.99 verified live 2026-09-20. Sold as leather "
        "sewing thread.")
assert len(DESC) <= 250, f"description too long: {len(DESC)}"

NOTES = """Catalogued 2026-09-20.

QUANTITY IS ONE SPOOL. Scott's report of what is on it is "NEARLY FULL" -
a fill state, not a measurement. The 260 m is the vendor's nominal figure for
a new spool and says nothing about this one. Do not convert "nearly full"
into metres anywhere downstream; if a length is ever needed, weigh it against
a known tare or buy a fresh spool.

WHAT IT IS FOR. Waxed lacing tape ties wire bundles into a harness - the
traditional alternative to zip ties, and the right thing for anything that has
to look period-correct or sit where a zip tie head would foul. Sold in the
sewing category as leather thread, which is why a search for cable or harness
parts will never surface it.

Homed at L2-D2 on theme (WIRE TERMINATION & CONNECTORS). Nobody has said this
drawer is where Scott wants it - it is the thematically right home, not an
instruction he gave. Move it if the bench says otherwise.

Last ordered 2023-08-14. Price above was read off the live listing today, so
it carries no estimate escalator."""

cat = PartCategory.objects.get(pk=18)
HOME = StockLocation.objects.get(pk=407)
amazon = Company.objects.get(name='Amazon')

if SupplierPart.objects.filter(SKU=ASIN).exists():
    print("ABORT - ASIN already attached:",
          [(s.pk, s.part.pk, s.part.name) for s in SupplierPart.objects.filter(SKU=ASIN)])
    sys.exit(1)

print(f"would create {NAME!r}")
print(f"  desc ({len(DESC)}): {DESC}")
print(f"  stock 1 spool @ {HOME.pathstring}")
if not COMMIT:
    print("\nDRY RUN - rerun with --commit"); sys.exit(0)

p = Part.objects.create(name=NAME, description=DESC, category=cat,
                        default_location=HOME, component=True,
                        purchaseable=True, active=True)
p.notes = NOTES; p.save()

sp = SupplierPart.objects.create(part=p, supplier=amazon, SKU=ASIN,
                                 description='Guzon DIY Hand Work Waxed Lacing Tape Flat Leather Thread, 260m Spool Black')
sp.pack_quantity = '1'
sp.save()

si = StockItem.objects.create(part=p, quantity=1, location=HOME)
si.notes = NOTES; si.save()

p2 = Part.objects.get(pk=p.pk); s2 = StockItem.objects.get(pk=si.pk)
sp2 = SupplierPart.objects.get(pk=sp.pk)
print(f"\nAFTER part {p2.pk}: {p2.name!r}")
print(f"  defloc={p2.default_location.name}")
print(f"  SP{sp2.pk} {sp2.SKU} pack={sp2.pack_quantity!r} native={sp2.pack_quantity_native}")
print(f"AFTER stock {s2.pk}: qty={s2.quantity} loc={s2.location.name} notes_len={len(s2.notes or '')}")
ok = (s2.quantity == 1 and s2.location_id == HOME.pk
      and sp2.pack_quantity_native == 1 and 'NEARLY FULL' in (s2.notes or ''))
print("VERIFIED" if ok else "*** VERIFY FAILED ***")
