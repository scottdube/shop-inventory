"""File counted stock into bin-wall drawers. The workhorse for the B3 pass.

Usage:  file_stock.py [--commit] "B3-R1C1=344:2" "B3-R1C4=141:6" ...
        drawer=partpk:qty[,partpk:qty...]

Counts written here are PHYSICAL counts, so stocktake_date is stamped - that is
what makes a rolling bin check possible later, since staleness only means
something if fresh counts are marked. Existing stock for the same part in the
same drawer is UPDATED, not duplicated, so re-running after a recount is safe.

Also clears the "INFERRED from the drawer label; verify" note where a human has
now verified it.
"""
import argparse, os, re, sys, django
from datetime import date
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model
from part.models import Part
from stock.models import StockLocation, StockItem

ap = argparse.ArgumentParser()
ap.add_argument("entries", nargs="+")
ap.add_argument("--commit", action="store_true")
ap.add_argument("--estimate", action="store_true",
                help="reasoned guess, not a tally: record the quantity but do NOT "
                     "stamp stocktake_date, so the rolling bin check still sees "
                     "this drawer as never truly counted")
a = ap.parse_args()

user = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
today = date.today()
INFERRED = re.compile(r"\s*>?\s*Placed in \*\*[^*]+\*\*[^\n]*INFERRED[^\n]*\n?", re.I)

for entry in a.entries:
    drawer, _, rest = entry.partition("=")
    loc = StockLocation.objects.filter(name=drawer.strip()).first()
    if not loc:
        print(f"  {drawer}: NO SUCH LOCATION")
        continue
    for chunk in rest.split(","):
        if not chunk.strip():
            continue
        pk_s, _, qty_s = chunk.partition(":")
        p = Part.objects.filter(pk=int(pk_s)).first()
        if not p:
            print(f"  {drawer}: no part #{pk_s}")
            continue
        qty = float(qty_s)
        si = StockItem.objects.filter(part=p, location=loc).first()
        verb = "update" if si else "create"
        print(f"  {drawer:<9} {verb:<6} #{p.pk:<4} {p.name[:44]:<44} qty {qty:g}"
      f"{'  [ESTIMATE]' if a.estimate else ''}")
        if not a.commit:
            continue
        if si:
            si.quantity = qty
        else:
            si = StockItem(part=p, location=loc, quantity=qty)
        if a.estimate:
            si.notes = (f"ESTIMATE {today.isoformat()} — reasoned from pack size "
                        "and use, NOT a tally. Not stamped as a stocktake.")
            si.save()
        else:
            si.notes = f"Hand-counted {today.isoformat()}."
            si.save()
            si.stocktake_date, si.stocktake_user = today, user
            si.save()
        changed = False
        if p.default_location_id != loc.pk:
            p.default_location = loc
            changed = True
        if p.notes and INFERRED.search(p.notes):
            p.notes = (INFERRED.sub("", p.notes).rstrip() +
                       f"\n\nLocation **verified by hand** {today.isoformat()}: "
                       f"{loc.pathstring}.").strip()
            changed = True
        if changed:
            p.save()

print(f"\n{'WROTE' if a.commit else 'DRY RUN'}")
tot = StockItem.objects.filter(location__name__regex=r"^[AB][1-3]-R").count()
print(f"stock items in the bin wall: {tot}")
