"""2026-09-20  Correct the WS1-S4 relocation rationale, and probe for an
antenna duplicate.

Rejected: leaving the form/bulk explanation in place as "close enough". It is
not a softer version of the right answer, it is the opposite one - it says
DON'T group by function, and Scott grouped by function. A note that argues
against the arrangement it describes will be believed by the next reader.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()
from part.models import Part
from stock.models import StockItem, StockLocation

WRONG = '2026-09-20 RELOCATED to WS1-S4'

CORRECT = """2026-09-20 RELOCATED to WS1-S4 on Scott's instruction ("ws1 s4"),
and then he gave the reason: "I put it there cuz thats where the zip ties are
currently."

IT LIVES WITH THE ZIP TIES. The grouping is BY FUNCTION - lacing tape and zip
ties are both bundling/tying materials for a harness, so they share a shelf.
If this spool is ever rehomed, it follows the zip ties.

CORRECTION TO WHAT I WROTE EARLIER ON THIS ROW: I had claimed the move was
about form and bulk (discrete termination pieces in L2-D2, bulk spools on the
wire rack). I invented that to explain a correction whose reason I had not
asked for, and it was wrong in the worst direction - it argued AGAINST
grouping by use, which is exactly what this shelf does.

NOTE FOR ANYONE SEARCHING: the zip ties themselves are NOT IN INVENTREE. A
search of zip tie / cable tie / tie wrap / wire tie / velcro returns only the
shop-printed tie-wrap hold-down at AT-D3. Before this row, WS1-S4 held zero
stock rows. The catalogue could not have told me where this belonged."""

for obj, label in [(Part.objects.get(pk=1254), 'part 1254'),
                   (StockItem.objects.get(pk=871), 'stock 871')]:
    n = obj.notes or ''
    i = n.find(WRONG)
    if i == -1:
        print(f"!! {label}: marker not found, appending instead")
        obj.notes = (n + "\n\n" + CORRECT).strip()
    else:
        obj.notes = (n[:i] + CORRECT).strip()
    obj.save()

for pk, label in [(1254, 'part 1254'), (871, 'stock 871')]:
    o = Part.objects.get(pk=pk) if pk == 1254 else StockItem.objects.get(pk=pk)
    ok = 'zip ties' in (o.notes or '') and 'form and bulk' not in (o.notes or '').split('CORRECTION')[0]
    print(f"{'OK ' if ok else 'BAD'} {label}: {len(o.notes or '')} chars, "
          f"mentions zip ties = {'zip ties' in (o.notes or '')}")

# ---- WS1-S4 location description: record the uncatalogued zip ties ----
loc = StockLocation.objects.get(pk=449)
print(f"\nloc 449 desc before: {loc.description!r}")
loc.description = ("Bundling and tying materials - zip ties (LOOSE, NOT CATALOGUED, "
                   "Scott 2026-09-20) and lacing tape. Group by function: anything "
                   "that ties a harness lands here.")
loc.save()
print(f"loc 449 desc after : {StockLocation.objects.get(pk=449).description!r}")

# ---- antenna duplicate probe: read this WHOLE, do not tail it ----
print("\n=== ANTENNA DUPLICATE PROBE (read whole) ===")
terms = ['antenna', 'aerial', 'whip', 'magnetic mount', 'mag mount', 'mmcx', 'mcx ', 'sma ']
hits = {}
for t in terms:
    for p in Part.objects.filter(name__icontains=t):
        hits.setdefault(p.pk, (p, f'name~{t.strip()}'))
    for p in Part.objects.filter(description__icontains=t):
        hits.setdefault(p.pk, (p, f'desc~{t.strip()}'))
print(f"candidates: {len(hits)}  terms={terms}")
for pk in sorted(hits):
    p, t = hits[pk]
    st = [(s.pk, float(s.quantity), s.location.pathstring if s.location else None)
          for s in StockItem.objects.filter(part=p)]
    print(f"[{p.pk}] act={p.active} {t}  {p.name!r}")
    print(f"     {(p.description or '')[:140]}")
    print(f"     stock: {st or 'NONE'}")
print(f"=== END probe: {len(hits)} printed, nothing truncated ===")
