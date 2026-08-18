"""Body size out of electrolytic part NAMES, into notes -- merging where two
kits hold the same value in different bodies.

Identity is value + voltage. That is the question actually asked ("do I have a
1uF 50V?"), never "do I have a 4x7 1uF 50V". Body size is an attribute of a
particular batch, so it belongs in notes and on the stock, not in the name.

Consequence, which the first version of this script missed: two kits holding the
same value in different bodies collapse to ONE part with two homes. That is a
merge, not a rename, and it is reported as such below.
"""
import argparse, os, re, sys, django
from collections import defaultdict
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part
from stock.models import StockItem

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

SIZED = re.compile(r"^(Capacitor Electrolytic .+?) \(([^)]+)\)$")

groups = defaultdict(list)
for p in Part.objects.filter(name__icontains="Capacitor Electrolytic", active=True):
    m = SIZED.match(p.name)
    if m:
        groups[m.group(1)].append((p, m.group(2)))

plain = merges = 0
for bare, members in sorted(groups.items()):
    members.sort(key=lambda t: t[0].pk)
    keep, keep_size = members[0]
    sizes = [s for _, s in members]
    homes = [m[0].default_location.name if m[0].default_location else "?" for m in members]

    if len(members) == 1:
        plain += 1
        print(f"  rename  {keep.name}")
    else:
        merges += 1
        print(f"  MERGE   {bare}")
        for p, s in members:
            home = p.default_location.name if p.default_location else "no home"
            mark = "keep " if p.pk == keep.pk else "fold "
            print(f"            {mark} #{p.pk:<4} {s:<10} {home}")

    if a.commit:
        for p, s in members[1:]:
            StockItem.objects.filter(part=p).update(part=keep)
            p.active = False
            p.notes = ((p.notes or "").rstrip() +
                       f"\n\n**MERGED** into #{keep.pk} {bare} on 2026-08-17 — "
                       "same value and voltage; body size is not part identity.").strip()
            p.name = f"{bare} [{s} merged]"[:100]
            p.save()
        keep.notes = ((keep.notes or "").rstrip() +
                      f"\n\nBody sizes held: {', '.join(sizes)}. "
                      f"Kit homes: {', '.join(homes)}. Other sizes of the same "
                      "value may sit elsewhere — check stock locations.").strip()
        keep.name = bare[:100]
        keep.save()

print(f"\n{'WROTE' if a.commit else 'DRY RUN - nothing written'}")
print(f"  straight renames: {plain}")
print(f"  merges:           {merges}")
print(f"  parts after:      {plain + merges}  (from {sum(len(v) for v in groups.values())})")
if not a.commit:
    print("\nre-run with --commit to apply")
