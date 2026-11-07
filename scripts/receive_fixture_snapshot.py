"""Dump every PO of the last 90 days as a receiving card, for local matcher
tests. Real records, not synthetic ones: the "rod" in "product" lesson.
    itq run scripts/receive_fixture_snapshot.py > binscan/fixtures/receive/pos-$(date +%F).json
"""
import datetime, json, os, sys
import django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from order.models import PurchaseOrder  # noqa: E402
from plugins.receiving.engine import po_card  # noqa: E402

since = datetime.date.today() - datetime.timedelta(days=90)
qs = PurchaseOrder.objects.filter(creation_date__gte=since).order_by("-pk")
print(json.dumps([po_card(po) for po in qs], indent=1, default=str))
