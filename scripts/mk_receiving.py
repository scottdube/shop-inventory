import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from stock.models import StockLocation

for site in ("SLN", "LRD"):
    parent = StockLocation.objects.get(name=site, parent__isnull=True)
    loc, created = StockLocation.objects.get_or_create(
        name="Receiving", parent=parent,
        defaults={"description":
            "Staging dock: received but not yet filed to a real location. "
            "Anything here is IN THE BUILDING and awaiting a drawer - file it "
            "during the next drawer session. Should trend toward empty."})
    print(f"  {loc.pathstring:<18} {'created' if created else 'exists'}")
