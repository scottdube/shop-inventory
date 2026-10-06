import os, sys, django
sys.path.insert(0, os.getcwd()); os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings"); django.setup()
from part.models import Part
from stock.models import StockItem
NEW = ("(2) An OLDER board bought USED in the first half of 2026 while XoomSpeed showed sold out, from Facebook Marketplace, "
       "seller Brad Selph (Scott 2026-10-05, 'I think'), about $100, standard variant per Scott. Both boards are the standard "
       "(no-DIN, 24 V) variant. ")
p = Part.objects.get(pk=1377)
assert "UNRECORDED - ask Scott" in p.notes
s = p.notes.index("(2) An OLDER"); e = p.notes.index("Drives the 3 s")
p.notes = p.notes[:s] + NEW + p.notes[e:]; p.save(); p.refresh_from_db(); assert "Brad Selph" in p.notes and "UNRECORDED" not in p.notes
st = StockItem.objects.get(pk=1063)
st.notes = st.notes.replace("the older board bought used in 2026 (source/price unrecorded)", "the older board bought used in 2026 (Facebook Marketplace, Brad Selph, about $100)")
st.save(); st.refresh_from_db(); assert "Brad Selph" in st.notes
print("part 1377 + stock 1063 updated")
