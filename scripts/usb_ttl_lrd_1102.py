"""Enter the two USB-TTL serial adapters found loose at LRD into F1-R2C4 (2026-11-02).

Like the Nanos (nanos_lrd_1102.py), both parts came in through the data conversion
as Amazon purchase history only, never as stock, with the bare LRD root as
default_location. Scott counted 1 of each:
- CP2102 board ("CP2102 MODULES USB TO TTL" silkscreen) -> part 77, HJHYUL 3-pack
  ordered 2026-05-01.
- YP-05 board -> part 76, AITRIP Type-C FT232RL 2-pack ordered 2026-05-11. The
  silkscreen says YP-05, not the chip. The match assumes this is the only FT232
  board bought, which is how part 76 reads, and the USB connector type was NOT
  confirmed from the photo. If it turns out to be mini-USB, it is a different
  board and needs its own part.
The rest of each pack wasn't seen loose; where those are isn't established.
One drawer for both: serial adapters are one kind.

    itq run scripts/usb_ttl_lrd_1102.py [--commit]
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model  # noqa: E402
from InvenTree.status_codes import StockHistoryCode  # noqa: E402
from part.models import Part  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

commit = "--commit" in sys.argv
loc = StockLocation.objects.get(pathstring="LRD/Akro Bins/F1/F1-R2C4")
u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
NOTES = {
    77: "Scott counted 1 loose at LRD 2026-11-02 (of the HJHYUL 3-pack, Amazon 2026-05-01); "
        "the other 2 not seen loose. Data-conversion purchase history, no PO.",
    76: "Scott counted 1 loose at LRD 2026-11-02: a YP-05 board, matched to the AITRIP "
        "Type-C FT232RL 2-pack (Amazon 2026-05-11) by elimination; connector type not "
        "confirmed. The other 1 not seen loose. Data-conversion purchase history, no PO.",
}
held = StockItem.objects.filter(location=loc)
assert not held.exists(), f"F1-R2C4 holds {list(held.values_list('pk', 'part__name'))}"
for pk in NOTES:
    p = Part.objects.get(pk=pk)
    rows = StockItem.objects.filter(part=p)
    print(p.pk, p.name, "| rows:", [(s.pk, s.quantity, s.location.pathstring) for s in rows])
    assert p.active and not rows.exists()
if not commit:
    raise SystemExit("DRY RUN - add --commit")
made = []
for pk, note in NOTES.items():
    p = Part.objects.get(pk=pk)
    s = StockItem(part=p, location=loc, quantity=1)
    s.save()
    s.add_tracking_entry(StockHistoryCode.CREATED, u, deltas={"quantity": 1.0}, notes=note)
    Part.objects.filter(pk=pk).update(default_location=loc)
    made.append((s.pk, pk))
bad = []
for spk, pk in made:
    s = StockItem.objects.get(pk=spk)
    d = Part.objects.get(pk=pk).default_location
    print(f"stock {s.pk}: {s.part.name} x{s.quantity:g} @ {s.location.pathstring}; default {d.pathstring}")
    if s.quantity != 1 or s.location_id != loc.pk or not d or d.pk != loc.pk:
        bad.append(spk)
print("ALL VERIFIED" if not bad else f"NOT VERIFIED: {bad}")
