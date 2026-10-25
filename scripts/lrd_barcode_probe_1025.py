"""Read-only: show assign_barcode's duplicate check and which unlinked LRD names trip it."""
import inspect, os, re, sys
import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from stock.models import StockLocation  # noqa: E402

src = inspect.getsource(StockLocation.assign_barcode)
print(src)
for name in ("barcode_model_type", "lookup_barcode", "generate_barcode_hash"):
    fn = getattr(StockLocation, name, None)
    if fn and callable(fn):
        try:
            print(inspect.getsource(fn))
        except (TypeError, OSError):
            pass

PRINTED = re.compile(r"^(Cab[1-8](-[DS][1-5])?|F[0-2](-R\d+C\d+)?)$")
lrd = StockLocation.objects.get(name="LRD", parent=None)
todo = [l for l in lrd.get_descendants() if PRINTED.match(l.name) and l.barcode_data != l.name]
print(f"unlinked: {len(todo)}; first 5 in pk order:",
      [l.name for l in sorted(todo, key=lambda l: l.pk)[:5]])

from InvenTree.helpers import hash_barcode  # noqa: E402
own = [l for l in todo if l.barcode_hash == hash_barcode(l.name)]
other = [l for l in todo if l.barcode_hash and l.barcode_hash != hash_barcode(l.name)]
print(f"unlinked holding their OWN name's hash: {len(own)} {[l.name for l in own][:8]}")
print(f"unlinked holding some OTHER hash: {len(other)} "
      f"{[(l.name, l.barcode_data) for l in other][:8]}")
print("barcode_data on those:", sorted({repr(l.barcode_data) for l in own})[:5])

hits = [(l.name, StockLocation.lookup_barcode(hash_barcode(l.name))) for l in todo]
hits = [(n, o) for n, o in hits if o is not None]
print(f"lookup_barcode hits: {len(hits)}")
for n, o in hits[:10]:
    print(f"  {n!r} -> pk {o.pk} {o.pathstring} data={o.barcode_data!r}")
linked = [l for l in lrd.get_descendants() if PRINTED.match(l.name) and l.barcode_data == l.name]
print("linked:", [l.name for l in sorted(linked, key=lambda l: l.pk)])
print("sample hashes:", hash_barcode("F1-R3C6"), hash_barcode("f1-r3c6"))
