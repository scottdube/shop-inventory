"""Mark drawers VERIFIED EMPTY.

Not the same state as 'never looked at', and the difference matters twice: an
empty drawer is available space, and a bin check should not keep flagging it.
There is no StockItem to stamp, so the fact goes on the location itself.
"""
import argparse, os, re, sys, django
from datetime import date
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from stock.models import StockLocation, StockItem
from part.models import Part

ap = argparse.ArgumentParser()
ap.add_argument("drawers", nargs="*", help="explicit location names")
ap.add_argument("--cabinet", help="expand to every drawer in a cabinet, e.g. A2")
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

names = list(a.drawers)
if a.cabinet:
    names += sorted(
        StockLocation.objects.filter(name__istartswith=f"{a.cabinet}-R")
        .values_list("name", flat=True))
if not names:
    ap.error("give drawer names or --cabinet")

skipped = marked = 0
for name in names:
    loc = StockLocation.objects.filter(name=name).first()
    if not loc:
        print(f"  {name}: NO SUCH LOCATION")
        continue
    n = StockItem.objects.filter(location=loc).count()
    if n:
        print(f"  {name}: has {n} stock item(s) - NOT marking empty")
        skipped += 1
        continue

    # A parking spot has NO stock rows by design — that is the whole point of a
    # bucket Part carrying a location and no quantity. Without this guard a
    # cabinet-wide sweep would stamp the four pre-sort buckets at A2-R8C5..C8
    # VERIFIED EMPTY, which is wrong twice: they are not empty, and they are a
    # queue somebody is meant to come back to.
    owners = Part.objects.filter(default_location=loc)
    if owners.exists():
        who = owners.first().name[:44]
        print(f"  {name}: PARKING SPOT / home of '{who}' - NOT marking empty")
        skipped += 1
        continue
    if (loc.metadata or {}).get("unsorted"):
        print(f"  {name}: flagged metadata.unsorted - NOT marking empty")
        skipped += 1
        continue

    # A description that names contents reads as RESERVED (README principle 18).
    # B3-R3C2 held ICs with zero stock rows and said so in its own description;
    # "no rows" is not evidence of emptiness, and the description is often the
    # only place the truth was written down.
    desc = (loc.description or "").strip()
    # Every bin-wall drawer carries its dimensions as a bracketed annotation,
    # e.g. "[6 x 2-7/32 x 1-9/16 in, small]". That is metadata, not contents —
    # a first cut of this guard treated it as contents and refused all 64
    # drawers in A2, which would have made the tool useless exactly where it
    # was needed. Strip the size annotation before deciding.
    body = re.sub(r"\[[^\]]*\]", "", desc).strip(" ,;-—")
    if body and not body.upper().startswith(("VERIFIED EMPTY", "PRE-SORT")):
        print(f"  {name}: description names something - CHECK BY EYE, not marking")
        print(f"          \"{body[:88]}\"")
        skipped += 1
        continue
    tag = f"VERIFIED EMPTY {date.today().isoformat()}"
    old = (loc.description or "").strip()
    print(f"  {name}: {tag}" + (f"   (was: {old})" if old else ""))
    marked += 1
    if a.commit:
        loc.description = (tag + (f" — previously labelled: {old}" if old else ""))[:250]
        loc.save()
        again = StockLocation.objects.get(pk=loc.pk)
        if not (again.description or "").upper().startswith("VERIFIED EMPTY"):
            print(f"  {name}: WRITE DID NOT STICK")

print(f"\n  {'marked' if a.commit else 'would mark'} {marked}, skipped {skipped}")
print(f"  {'WROTE' if a.commit else 'DRY RUN — add --commit'}")
