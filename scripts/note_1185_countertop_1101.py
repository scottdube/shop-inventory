"""Stock 1185 (wired lav, PO-0264) says 'On the LRD bench'. That means the
countertop: Scott renamed it 2026-11-01. Append, don't rewrite the dated note."""
import os, sys
import django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from stock.models import StockItem  # noqa: E402
from plugins.notes_compat import note_append, note_text  # noqa: E402
r = StockItem.objects.get(pk=1185)
line = ("2026-11-01: 'the LRD bench' above is the COUNTERTOP (renamed by Scott; "
        "'bench' at LRD now means the new electronics bench).")
if line not in (note_text(r) or ""):
    note_append(r, line)
assert line in note_text(StockItem.objects.get(pk=1185)), "note did not stick"
print("1185 note appended, verified")
