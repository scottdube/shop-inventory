"""B0-R1C3 is home for PO-0184's panel jacks + test pins; re-read, 2026-10-04.

Scott put both "with the b[arrel] jacks". default_location is set because this
is a real home, not staging. Writes by queryset .update().

Rejected: widening B0-R1C3's description to say so. It is already at the
250-char limit (it ends mid-word, "This drawer had be"), so an append sliced
to 250 is a silent no-op -- the first run of this script did exactly that.
The parts' default_location carries the fact instead.
"""
import os, sys, django
sys.path.insert(0, os.getcwd()); os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings"); django.setup()
from part.models import Part
from stock.models import StockItem, StockLocation
loc = StockLocation.objects.get(name="B0-R1C3")
Part.objects.filter(pk__in=(1263, 1264)).update(default_location=loc)
for s in StockItem.objects.filter(part_id__in=(1263, 1264)):
    print(s.pk, s.part.name[:40], s.quantity, s.location.name, "PO", s.purchase_order.reference if s.purchase_order else None,
          "| home", s.part.default_location.name if s.part.default_location else None, "| fl", s.metadata.get("florida"))
