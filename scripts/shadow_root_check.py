"""Flag categories that exist twice — once as a flat root, once nested.

Why this exists: on 2026-09-08 the two resistor trees turned out to be one
instance of a database-wide pattern. Sixteen flat legacy roots ("seeded from
purchase history") shadow an `Electronics/...` branch, so browsing one tree
silently misses the other — a confident false negative and then a duplicate
purchase. `[1] Passives` was collapsed that day; the rest were left standing
because THE HEAVIER SIDE FLIPS BY FAMILY (flat wins for Modules, Connectors,
ICs, Sensors, Switches, Power; nested won only for Passives), so each needs its
own precedent check rather than one blanket rule.

Consolidating without routing new parts just refills the loser: #1173 and #1174
were created minutes apart into `Electronics/Interface` and `Modules/Interface`.
Nothing in InvenTree routes a new part, and `structural=True` — the obvious
guard — is refused on a category that still holds parts, which is all of them.
So this is a detector, not a lock. Run it in the nightly sweep.

Read-only.

    itq run scripts/shadow_root_check.py            # all shadow pairs
    itq run scripts/shadow_root_check.py --days 14  # recent arrivals only
"""
import argparse
import os
import sys
from collections import defaultdict
from datetime import timedelta

import django
from django.utils import timezone

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part, PartCategory  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--days", type=int, default=7,
                help="window for the 'landed in a shadow root recently' list. "
                     "Kept short on purpose: the whole database was imported "
                     "2026-08-15, so a 30-day window returns 313 rows and "
                     "tells you nothing about routing going forward.")
a = ap.parse_args()


def live(cat):
    return Part.objects.filter(
        category__in=cat.get_descendants(include_self=True), active=True).count()


by_name = defaultdict(list)
for c in PartCategory.objects.all():
    by_name[c.name.strip().lower()].append(c)

pairs = []
for name, cats in by_name.items():
    if len(cats) < 2:
        continue
    roots = [c for c in cats if c.parent_id is None]
    nested = [c for c in cats if c.parent_id is not None]
    if roots and nested:
        pairs.append((roots, nested))

print("=" * 74)
print("SHADOW PAIRS — the same category name as a flat root AND nested")
print("=" * 74)
if not pairs:
    print("  none")
shadow_root_pks = set()
for roots, nested in sorted(pairs, key=lambda p: -max(live(c) for c in p[0])):
    for r in roots:
        shadow_root_pks.add(r.pk)
        n_desc = "  ".join(f"[{c.pk}] {c.pathstring} ({live(c)})" for c in nested)
        heavier = "FLAT" if live(r) >= max(live(c) for c in nested) else "NESTED"
        print(f"  [{r.pk}] {r.name} ({live(r)} live)   vs   {n_desc}"
              f"    heavier={heavier}")

print()
print("=" * 74)
print(f"PARTS FILED INTO A SHADOW ROOT IN THE LAST {a.days} DAYS")
print("=" * 74)
since = timezone.now().date() - timedelta(days=a.days)
recent = Part.objects.filter(
    creation_date__gte=since,
    category__in=PartCategory.objects.filter(pk__in=shadow_root_pks),
).order_by("-pk")
if not recent.exists():
    print("  none — nothing new landed in a shadowed flat root")
for p in recent:
    print(f"  #{p.pk}  {p.creation_date}  [{p.category.pathstring}]  {p.name[:52]}")

print()
print("=" * 74)
print("UNCATEGORISED PARTS")
print("=" * 74)
orphans = Part.objects.filter(category__isnull=True).order_by("-pk")
if not orphans.exists():
    print("  none")
for p in orphans:
    print(f"  #{p.pk}  {p.creation_date}  active={p.active}  {p.name[:60]}")

print()
n = len(shadow_root_pks)
print(f"{'⚠' if n else '✓'} {n} shadowed flat root(s), "
      f"{recent.count()} recent arrival(s), {orphans.count()} uncategorised")
