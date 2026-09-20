"""Record what the ALLECIN 1/2W kit contains and that it is verifiably in FL.

Part #1 has been sitting in the catalogue with zero stock rows since it was
seeded from purchase history, so a search for '330R' or '470R' could never
see inside it. That is what made the G1000 BOM say 'not stocked' for two
values that Scott very likely already owns 1500 miles away.

MEASURED 2026-09-20, not inferred:
  - contents, from the live Amazon listing: 25 values x 10 pcs, 1/2W 1%,
    and 150R / 330R / 470R are all on the list
  - location, from Amazon order 113-4288189-7490647 placed 2026-02-12:
    Ship to 1879 LAKE RIDGE DR, THE VILLAGES FL. Not the Dover address.

Deliberately NOT exploding the kit into 25 value-parts here. That is the
right end state - it is how the EAONE kit is modelled and #6's description
already states the policy, 'an assortment kit is a LOCATION, not a part' -
but it is a job Scott has not asked for and it needs an LRD location built
first. A note that the next searcher will actually hit is worth more today
than a half-done re-model.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()
from part.models import Part
from stock.models import StockItem

COMMIT = '--commit' in sys.argv

NOTE = """

=== CONTENTS AND LOCATION ESTABLISHED 2026-09-20 ===

CONTENTS, from the live Amazon listing (ASIN B0BTP63DGQ, style 1/2W):
250 pcs, 25 values, 10 PCS OF EACH VALUE, 1% metal film, 1/2W.
  1R 2.2R 3.3R 10R 22R 47R 68R 100R 120R 150R 220R 330R 470R 560R 680R
  1K 2K 2.2K 4.7K 5.6K 10K 22K 47K 100K 1M
Body 9mm long x 3mm dia, leads 27mm.

LOCATION: IT IS IN FLORIDA. Amazon order 113-4288189-7490647, placed
2026-02-12, Ship to 1879 LAKE RIDGE DR, THE VILLAGES FL 32162. That is the
order record, not a recollection and not the default_location field.
Caveat worth keeping: shipped there in February proves where it ARRIVED. No
one has laid eyes on it since, so it is 'should be at LRD', not 'seen at LRD'.

WHY THIS MATTERS - it hid from a BOM search. This part carries ZERO stock
rows, so its 250 resistors are invisible to any search by value. The G1000
build #3 BOM recorded 330R and 470R as 'not stocked' and queued a purchase.
Both are in this box, in 1/2W, which is the rating that build actually wants.

TODO, not done: explode into 25 value-parts homed at an LRD kit location,
the way the EAONE 30-value kit is modelled. Needs LRD storage designed first.
See #6's description for the standing policy."""

p = Part.objects.get(pk=1)
print(f"[{p.pk}] {p.name!r} active={p.active} stock_rows={StockItem.objects.filter(part=p).count()}")
print(f"  notes_len before = {len(p.notes or '')}")
if not COMMIT:
    print("\nDRY RUN - rerun with --commit"); sys.exit(0)

p.notes = (p.notes or '') + NOTE
p.save()
p2 = Part.objects.get(pk=1)
print(f"  notes_len after  = {len(p2.notes or '')}")
ok = 'LAKE RIDGE' in (p2.notes or '') and '10 PCS OF EACH' in (p2.notes or '')
print("VERIFIED" if ok else "*** VERIFY FAILED ***")

# The two EAONE rows earmarked for this trip may no longer need to travel.
COND = """

2026-09-20: BEFORE CARRYING THIS TO FLORIDA, READ THIS. The ALLECIN 25-value
1/2W kit (part #1) is confirmed AT LRD and holds 10 pcs of this value in
1/2W. If Scott decides not to carry these, DROP THE FLORIDA TAG ON THIS ROW
in the same turn - an earmark whose reason has evaporated is exactly how the
10k row (#634) ended up stale earlier today."""
for pk in (138, 140):
    si = StockItem.objects.get(pk=pk)
    si.notes = (si.notes or '') + COND
    si.save()
    s2 = StockItem.objects.get(pk=pk)
    print(f"stock {pk} [{s2.part.pk}] {s2.part.name}: tags={[t.name for t in s2.tags.all()]} "
          f"note_ok={'DROP THE FLORIDA TAG' in (s2.notes or '')}")
