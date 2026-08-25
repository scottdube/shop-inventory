"""Set a StockLocation description, and prove it landed.

Every bin the walk touches needs its description rewritten, and the walk had
been doing that with a fresh one-off script per bin. `.save()` on this install
has reported success and written nothing, so the re-read is not optional.

Name only, not pathstring: location names are NOT unique here, so this refuses
rather than guessing when a name matches more than one location.
"""
import argparse, os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from stock.models import StockLocation

ap = argparse.ArgumentParser()
ap.add_argument("name", help="location name, e.g. RB-19")
ap.add_argument("description")
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

matches = list(StockLocation.objects.filter(name=a.name))
if len(matches) != 1:
    sys.exit(f"{a.name}: {len(matches)} locations match - refusing to guess")
loc = matches[0]

print(f"{loc.pathstring}  #{loc.pk}")
print(f"  was ({len(loc.description or '')}): {loc.description}")
print(f"  now ({len(a.description)}): {a.description}")

if not a.commit:
    print("\n  DRY RUN - add --commit")
    sys.exit()

loc.description = a.description
loc.save()
again = StockLocation.objects.get(pk=loc.pk)
if again.description != a.description:
    print("  save() did not stick - falling back to queryset update()")
    StockLocation.objects.filter(pk=loc.pk).update(description=a.description)
    again = StockLocation.objects.get(pk=loc.pk)
print("  VERIFIED" if again.description == a.description else "  STILL WRONG - stop and look")
