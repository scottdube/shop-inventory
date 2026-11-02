"""Enter the 5 Arduino Nanos at LRD as stock in F1-R1C1 (2026-11-02).

Part 71 (AYWHP 5-pack, CH340G, USB-C; Amazon 113-2421163-1104249, 2026-03-15)
came in by the data conversion as purchase history only, never as stock.
Scott counted 5 at LRD and confirmed USB-C. The part's default_location was an
inference (SLN B3-R6C1, "Arduinos" drawer label) and that drawer holds a
BTS7960, so the home moves to where the only stock is.

    itq run scripts/nanos_lrd_1102.py [--commit]
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
p = Part.objects.get(pk=71)
loc = StockLocation.objects.get(pathstring="LRD/Akro Bins/F1/F1-R1C1")
u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
existing = StockItem.objects.filter(part=p)
print(p.name, "| existing rows:", [(s.pk, s.quantity, s.location.pathstring) for s in existing])
print("F1-R1C1 holds:", list(StockItem.objects.filter(location=loc).values_list("pk", "part__name")))
assert not existing.exists() and not StockItem.objects.filter(location=loc).exists()
if not commit:
    raise SystemExit("DRY RUN - add --commit")
s = StockItem(part=p, location=loc, quantity=5)
s.save()
s.add_tracking_entry(StockHistoryCode.CREATED, u, deltas={"quantity": 5.0},
                     notes="Scott counted 5 at LRD 2026-11-02, USB-C confirmed. Amazon "
                           "113-2421163-1104249 (2026-03-15), AYWHP 5-pack; entered from the "
                           "data-conversion purchase history, no PO.")
Part.objects.filter(pk=p.pk).update(default_location=loc)
s = StockItem.objects.get(pk=s.pk)
d = Part.objects.get(pk=p.pk).default_location
ok = s.quantity == 5 and s.location_id == loc.pk and d and d.pk == loc.pk
print(f"stock {s.pk}: {s.quantity:g} @ {s.location.pathstring}; default {d.pathstring}")
print("ALL VERIFIED" if ok else "NOT VERIFIED")
