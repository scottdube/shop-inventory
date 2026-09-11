import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()
from stock.models import StockItem

s = StockItem.objects.get(pk=797)
meta = s.metadata or {}
print("trips before:", meta['commutes'].get('trips'))
meta['commutes']['trips'] = []
s.metadata = meta
s.save()
s.refresh_from_db()
if s.metadata['commutes']['trips']:
    StockItem.objects.filter(pk=797).update(metadata=meta)
    s.refresh_from_db()
print("trips after: ", s.metadata['commutes'].get('trips'))
print("location:    ", s.location.pathstring)
assert s.location_id == 431 and not s.metadata['commutes']['trips']
print("✓ clean: back at MC-T2, no phantom trip history")
