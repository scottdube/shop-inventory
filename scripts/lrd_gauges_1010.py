"""Three measuring tools going to LRD for good, from Scott's photo 2026-10-10.

Scott: "a two to three inch micrometer, and two dial indicators ... these three
measuring devices will be permanently stationed down at" LRD (he said SLN; read
as LRD -- "down", Florida pack, he is driving south 2026-10-11).

Read off the photo (field marks, not memory):
  - Micrometer: FOWLER, Germany, frame stamped 1-2" .0001 (vernier sleeve),
    inspection sticker "INSP. 1 JAN 21". The frame says 1-2", NOT 2-3" as spoken.
    Not in inventory (the only outside mics are the Mitutoyo 0-3" SET, #461).
  - Federal C81 .001", Providence RI, green "Miracle Movement" dial. It is ONE
    of the four in the Federal lot row (part #1353, SI #1040: B21, C3K, C81,
    C81S). Carved out as its own part, because a qty-1 split of a lot row says
    "one of the four" and not which -- in Florida that is unanswerable.
  - Starrett No. 81-111-630, Cat. No. 82 -> already part #1352 / SI #1039.

One-way transfer, not a commuter: florida earmark only. Nothing moves to FL-01
until it is physically in the box (florida_pack.py), and nothing is filed at
LRD before it arrives. default_location left empty (home learned at LRD).

Also: Andonstar AD249S-M (#195) sat in Consumables/Solder -> Equipment/Test
Equipment, beside the Rigol.

    itq run scripts/lrd_gauges_1010.py            # dry run
    itq run scripts/lrd_gauges_1010.py --commit
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.utils import timezone  # noqa: E402
from part.models import Part, PartCategory  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

COMMIT = "--commit" in sys.argv
today = str(timezone.now().date())
WHY = "permanent at LRD (Scott 2026-10-10, Florida pack)"
MEAS = PartCategory.objects.get(pk=47); assert MEAS.pathstring == "Tooling/Measuring"
TEST = PartCategory.objects.get(pk=38); assert TEST.pathstring == "Equipment/Test Equipment"
SLN = StockLocation.objects.get(name="SLN", parent=None)
lot = StockItem.objects.select_related("part", "location").get(pk=1040)
assert lot.part_id == 1353 and float(lot.quantity) == 4, (lot.part_id, lot.quantity)
star = StockItem.objects.select_related("part").get(pk=1039)
assert star.part_id == 1352 and float(star.quantity) == 1
scope_m = Part.objects.get(pk=195); assert scope_m.name.startswith("Andonstar")

# duplicate guard: rerun-safe
fowler = Part.objects.filter(name__icontains="Fowler", category=MEAS).first()
c81 = Part.objects.filter(name__icontains="Federal C81", category=MEAS).first()
print(f"lot SI #{lot.pk} {lot.part.name} qty {float(lot.quantity):g} @ {lot.location.pathstring}")
print(f"starrett SI #{star.pk} {star.part.name}")
print(f"fowler exists: {fowler}, C81 exists: {c81}")
print(f"andonstar #{scope_m.pk} category {scope_m.category.pathstring} -> {TEST.pathstring}")
if not COMMIT:
    sys.exit("\nDRY RUN -- add --commit")

def earmark(s):
    meta = dict(s.metadata or {})
    meta["florida"] = {"qty": float(s.quantity), "why": WHY, "added": today}
    StockItem.objects.filter(pk=s.pk).update(metadata=meta)
    s.tags.add("florida")
    s.refresh_from_db()
    assert (s.metadata or {}).get("florida"), f"earmark did not stick on {s.pk}"
    print(f"  earmarked SI #{s.pk}")

if not fowler:
    fowler = Part(
        name='Fowler 1-2" Outside Micrometer, .0001" vernier',
        description='Outside micrometer, 1-2 in range, .0001 in vernier, '
                    'decimal-equivalent chart on frame, made in Germany',
        keywords="micrometer, outside micrometer, 1-2 inch, Fowler, vernier, .0001",
        category=MEAS, component=False, purchaseable=True, assembly=False,
        notes=('Identified from Scott\'s photo 2026-10-10: Fowler label, frame stamped '
               '1-2" .0001, GERMANY, inspection sticker "INSP. 1 JAN 21". Scott called it '
               'a 2-3" mic; the frame says 1-2".\n\nPurchase history unknown; no price.\n\n'
               '**Permanent at LRD** from the 2026-10 trip (one-way, not a commuter).'))
    fowler.save(); fowler.refresh_from_db()
    assert fowler.category_id == MEAS.pk
    print(f"CREATED part #{fowler.pk} {fowler.name}")
fs = StockItem.objects.filter(part=fowler).first()
if not fs:
    fs = StockItem(part=fowler, location=SLN, quantity=1,
                   notes="Filed 2026-10-10 from Scott's photo; exact SLN spot was not recorded.")
    fs.save(); fs.refresh_from_db()
    assert fs.location_id == SLN.pk and float(fs.quantity) == 1
    print(f"CREATED SI #{fs.pk} @ {SLN.pathstring}")

if not c81:
    c81 = Part(
        name='Federal C81 Dial Indicator, .001"',
        description='Federal (Providence RI) C81 dial indicator, .001 in graduation, '
                    'Miracle Movement, revolution counter, back lug',
        keywords="dial indicator, Federal, C81, .001, indicator",
        category=MEAS, component=False, purchaseable=True, assembly=False,
        notes=('Carved out of the Federal lot (part #1353: B21, C3K, C81, C81S) on '
               '2026-10-10 when this one went to LRD -- a qty-1 split of the lot row '
               'could not say WHICH indicator travelled.\n\n'
               '**Permanent at LRD** from the 2026-10 trip.'))
    c81.save(); c81.refresh_from_db()
    assert c81.category_id == MEAS.pk
    print(f"CREATED part #{c81.pk} {c81.name}")
cs = StockItem.objects.filter(part=c81).first()
if not cs:
    cs = StockItem(part=c81, location=lot.location, quantity=1,
                   notes=f"Carved from Federal lot SI #{lot.pk} 2026-10-10 (was 4, now 3).")
    cs.save(); cs.refresh_from_db()
    assert float(cs.quantity) == 1
    print(f"CREATED SI #{cs.pk} @ {cs.location.pathstring}")
    StockItem.objects.filter(pk=lot.pk).update(quantity=3)
    lp = lot.part
    Part.objects.filter(pk=lp.pk).update(
        name="Federal Dial Test Indicators (lot: B21, C3K, C81S)",
        notes=(lp.notes or "") + f"\n\n2026-10-10: C81 carved out as part #{c81.pk} (to LRD); lot 4 -> 3.")
    lot.refresh_from_db(); lp.refresh_from_db()
    assert float(lot.quantity) == 3 and "C81," not in lp.name, (lot.quantity, lp.name)
    print(f"lot SI #{lot.pk} -> 3, part renamed: {lp.name}")

for s in (fs, cs, star):
    earmark(s)

Part.objects.filter(pk=scope_m.pk).update(category=TEST)
scope_m.refresh_from_db(); assert scope_m.category_id == TEST.pk
print(f"andonstar #{scope_m.pk} -> {scope_m.category.pathstring}")
