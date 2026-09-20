"""Catalogue the nine 2x15 (30P) IDC ribbon sockets pulled from MC-T3.

Scott counted 9 and called the pin count: 30 pins = 2x15. Both figures are
his, not mine — the photo shows identity (IDC clamp socket, separate strain
relief bar moulded '...30P') and nothing about how many there are.

Home is L2-D2, same drawer as the 2x12 sockets (#1251) catalogued an hour ago
and the box headers. MC-T3 is being emptied; nothing goes back in it.

Duplicate guard ran first: no existing 2x15 / 30P / 30-pin IDC part.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()
from part.models import Part, PartCategory
from stock.models import StockItem, StockLocation
from django.contrib.auth import get_user_model

COMMIT = '--commit' in sys.argv
user = get_user_model().objects.filter(is_superuser=True).first()

NAME = 'IDC Ribbon Socket 2x15 (30P) Female, crimp-on'
DESC = ("2.54mm IDC female socket for FLAT RIBBON CABLE, 2x15 = 30 positions, "
        "clamp termination, supplied with a separate strain-relief cover bar "
        "moulded 30P. Mates a 2x15 shrouded box header - NONE in stock. "
        "Sibling of the 2x12 #1251.")
assert len(DESC) <= 250, f"description too long: {len(DESC)}"

NOTES = """Nine pulled out of MC-T3 on 2026-09-20 while emptying that drawer.

COUNT AND PIN COUNT ARE SCOTT'S, at the bench: 9 pieces, 30 pins. Not derived
from the photo - a photograph shows identity, never quantity.

NO MATING PART IS IN STOCK. L2-D2 holds 2x12 (#96) and 2x6 (#1249) box
headers; there is no 2x15. Nor is any 30-conductor ribbon cable catalogued -
the bulk ribbon in MC-T3 was never entered. So these nine terminate nothing
that the catalogue knows about. That is a lead, not a fault: find what they
were bought for before assuming they are surplus.

NOT a G1000 build #3 part. The PFD faceplate uses 2x12 and 2x6.

The separate bars seen loose in the 24P socket box earlier today are now much
more likely to be strain-relief covers of this same family - but that is a
HYPOTHESIS, nobody has matched a bar to a body."""

cat = PartCategory.objects.get(pk=18)
HOME = StockLocation.objects.get(pk=407)

dupes = (Part.objects.filter(name__icontains='2x15') |
         Part.objects.filter(name__icontains='30P').filter(name__icontains='IDC'))
if dupes.exists():
    print("ABORT - possible duplicate:", [(p.pk, p.name) for p in dupes])
    sys.exit(1)

print(f"would create: {NAME!r}")
print(f"  cat={cat} home={HOME.pathstring}")
print(f"  desc ({len(DESC)}): {DESC}")
print(f"  stock 9 @ {HOME.pathstring}")

if not COMMIT:
    print("\nDRY RUN - rerun with --commit")
    sys.exit(0)

p = Part.objects.create(name=NAME, description=DESC, category=cat,
                        default_location=HOME, component=True,
                        purchaseable=True, active=True)
p.notes = NOTES
p.save()

si = StockItem.objects.create(part=p, quantity=9, location=HOME)
si.notes = NOTES
si.save()

# verify by re-read - .save() has silently written nothing on this install
p2 = Part.objects.get(pk=p.pk)
s2 = StockItem.objects.get(pk=si.pk)
print(f"\nAFTER part {p2.pk}: {p2.name!r}")
print(f"  defloc={p2.default_location} cat={p2.category}")
print(f"  desc={p2.description}")
print(f"  notes_len={len(p2.notes or '')}")
print(f"AFTER stock {s2.pk}: qty={s2.quantity} loc={s2.location.pathstring} notes_len={len(s2.notes or '')}")
ok = (p2.default_location_id == HOME.pk and s2.quantity == 9
      and s2.location_id == HOME.pk and (p2.notes or '') and (s2.notes or ''))
print("VERIFIED" if ok else "*** VERIFY FAILED ***")
