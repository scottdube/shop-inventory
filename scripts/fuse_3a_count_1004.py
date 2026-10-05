"""Scott counted the T3AL250V 3 A fuse box in the 1100MX electrical cabinet: 18
(2026-10-04). Replaces the [ESTIMATE] 19 on stock #904, which was 20-pack minus
the F1 fit; the gap of one is consistent with F2 having taken a spare at the
2025 mist-outlet install, but that is not established and is not recorded as fact.
"""
import os, sys, datetime, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model
from stock.models import StockItem

TODAY = datetime.date(2026, 10, 4)
NOTE = ("Counted 18 by Scott 2026-10-04 (box in the 1100MX electrical cabinet). Source: Amazon "
        "112-7363556-2703463, 2025-07-27, pack of 20. One went into ECM1 F1 on 2026-10-04; the "
        "other missing one is unaccounted for (possibly F2 at the 2025 mist-outlet install, not checked). "
        "Replaces an [ESTIMATE] of 19.")
user = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
si = StockItem.objects.get(pk=904)
assert si.part_id == 36, si.part_id
si.stocktake(18, user, notes="Hand count 2026-10-04 by Scott")
StockItem.objects.filter(pk=904).update(notes=NOTE, stocktake_date=TODAY)  # stamp directly: stocktake() may not
r = StockItem.objects.get(pk=904)
assert r.quantity == 18 and r.stocktake_date == TODAY and not r.notes.startswith("[ESTIMATE]"), \
    (r.quantity, r.stocktake_date, r.notes[:20])
print(f"VERIFIED stock #904 qty={r.quantity} stocktake_date={r.stocktake_date} location={r.location}")
