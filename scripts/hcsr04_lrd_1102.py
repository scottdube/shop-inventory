"""Enter the HC-SR04s found loose at LRD into F1-R2C5 (2026-11-02).

Part 56 (ELEGOO 5-pack, Amazon 2026-03-15, bought at LRD) had only
data-conversion purchase history and no stock. Its note says one went to SLN.
Scott counted 2 loose here. The other 2 weren't seen loose; where they are is
not established. Same pattern as nanos_lrd_1102.py.

    itq run scripts/hcsr04_lrd_1102.py [--commit]
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
p = Part.objects.get(pk=56)
loc = StockLocation.objects.get(pathstring="LRD/Akro Bins/F1/F1-R2C5")
u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
rows = StockItem.objects.filter(part=p)
held = StockItem.objects.filter(location=loc)
print(p.name, "| rows:", list(rows.values_list("pk", "quantity")), "| F1-R2C5 holds:", list(held.values_list("pk", "part__name")))
assert not rows.exists() and not held.exists()
if not commit:
    raise SystemExit("DRY RUN - add --commit")
s = StockItem(part=p, location=loc, quantity=2)
s.save()
s.add_tracking_entry(StockHistoryCode.CREATED, u, deltas={"quantity": 2.0}, notes=(
    "Scott counted 2 loose at LRD 2026-11-02, of the ELEGOO 5-pack (Amazon 2026-03-15, "
    "113-5814816-7797840). 1 went to SLN per the part note; 2 not seen loose, whereabouts not "
    "established. Data-conversion purchase history, no PO."))
Part.objects.filter(pk=p.pk).update(default_location=loc)
s = StockItem.objects.get(pk=s.pk)
d = Part.objects.get(pk=p.pk).default_location
ok = s.quantity == 2 and s.location_id == loc.pk and d and d.pk == loc.pk
print(f"stock {s.pk}: {s.quantity:g} @ {s.location.pathstring}; default {d.pathstring}")
print("ALL VERIFIED" if ok else "NOT VERIFIED")
