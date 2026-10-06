import os, sys, django
sys.path.insert(0, os.getcwd()); os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings"); django.setup()
from part.models import Part
from stock.models import StockItem
p = Part.objects.get(pk=1377)
old = ("bought USED in the first half of 2026 while XoomSpeed showed sold out, from Facebook Marketplace, "
       "seller Brad Selph (Scott 2026-10-05, 'I think'), about $100, standard variant per Scott.")
assert old in p.notes
p.notes = p.notes.replace(old, "bought USED Dec 2025 from Brad Selph via Facebook Marketplace for $135 (Scott confirmed 2026-10-06), standard variant.")
p.save(); p.refresh_from_db(); assert "$135" in p.notes and "I think" not in p.notes
st = StockItem.objects.get(pk=1063)
old2 = "bought used in 2026 (Facebook Marketplace, Brad Selph, about $100)"
assert old2 in st.notes
st.notes = st.notes.replace(old2, "bought used Dec 2025 (Facebook Marketplace, Brad Selph, $135)")
st.save(); st.refresh_from_db(); assert "$135" in st.notes
print("part 1377 + stock 1063 updated")
