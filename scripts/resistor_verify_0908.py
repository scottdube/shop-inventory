"""Falsify-before-reporting pass on the two resistor trees.

TRAPS.md already rules that `Passives/*` holds KIT-LEVEL records at qty 0 and
`Electronics/Passives/*` holds the DECOMPOSED children with real counts. So a
zero in the legacy tree is decomposition, not shortage. Before proposing any
move, prove for each legacy part whether a decomposition exists.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part, PartCategory  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

print("=" * 72)
print("KIT LOCATIONS -- is each legacy kit record decomposed into a LOCATION?")
print("=" * 72)
for loc in StockLocation.objects.filter(name__icontains="kit").order_by("pathstring"):
    rows = StockItem.objects.filter(location=loc)
    parts = {r.part_id for r in rows}
    print(f"  {loc.pathstring}")
    print(f"      {rows.count()} stock rows / {len(parts)} distinct parts"
          f"  qty={sum(r.quantity for r in rows):g}")

print()
print("=" * 72)
print("EACH PART IN [2] Passives/Resistors -- full record")
print("=" * 72)
cat2 = PartCategory.objects.get(pk=2)
for p in Part.objects.filter(category=cat2).order_by("pk"):
    print(f"#{p.pk}  {p.name}")
    print(f"    active={p.active}  IPN={p.IPN!r}  qty={p.total_stock:g}  "
          f"default_location={p.default_location.pathstring if p.default_location else '-'}")
    print(f"    desc={p.description}")
    if p.notes:
        print(f"    notes={p.notes[:400]}")
    for sp in p.supplier_parts.all():
        print(f"    supplier: {sp.supplier} SKU={sp.SKU} pack={sp.pack_quantity!r} "
              f"native={sp.pack_quantity_native}")
    print(f"    BOM uses: {len(p.get_used_in())}"
          f"   variant_of={p.variant_of_id}  image={bool(p.image)}")
    print()

print("=" * 72)
print("THE ALREADY-RETIRED PRECEDENT #502 and #448 -- what a retirement looks like")
print("=" * 72)
for pk in (502, 448, 143):
    p = Part.objects.get(pk=pk)
    print(f"#{p.pk}  active={p.active}  qty={p.total_stock:g}  {p.name}")
    print(f"    desc={p.description}")
    if p.notes:
        print(f"    notes={p.notes[:300]}")
    print()

print("=" * 72)
print("CROSS-TREE NAME OVERLAP: every live part in either tree, normalised")
print("=" * 72)
import re  # noqa: E402
def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())
cat69 = PartCategory.objects.get(pk=69)
live2 = list(Part.objects.filter(category=cat2, active=True))
live69 = list(Part.objects.filter(category=cat69, active=True))
for a in live2:
    na = norm(a.name)
    for b in live69:
        nb = norm(b.name)
        # crude containment either way, or shared 12-char run
        if na in nb or nb in na:
            print(f"  OVERLAP  #{a.pk} {a.name[:45]!r}  <->  #{b.pk} {b.name[:45]!r}")
print("  (end of containment matches)")

print()
print("=" * 72)
print("YOKIVE PAIR -- #8 vs #178, the only both-active same-product pair")
print("=" * 72)
for pk in (8, 178):
    p = Part.objects.get(pk=pk)
    print(f"#{p.pk}  active={p.active}  qty={p.total_stock:g}  created={p.creation_date}")
    print(f"    name={p.name}")
    print(f"    desc={p.description}")
    print(f"    IPN={p.IPN!r}  image={bool(p.image)}  "
          f"default_location={p.default_location.pathstring if p.default_location else '-'}")
    print(f"    suppliers={[(sp.supplier.name, sp.SKU) for sp in p.supplier_parts.all()]}")
    if p.notes:
        print(f"    notes={p.notes[:300]}")
    print()
