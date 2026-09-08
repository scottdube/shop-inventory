"""Collapse the legacy [1] Passives root into Electronics/Passives.

Approved by Scott 2026-09-08 ("All of Passives"), target tree
`Electronics/Passives`, after docs/resistor-trees-2026-09-08.md.

Dry run by default. --commit writes. Every write is re-read and compared,
because .save() on this install has reported success and written nothing
(docs/TRAPS.md). Categories are deleted only after proving they are empty.
"""
import argparse
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part, PartCategory  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()
DRY = not a.commit
tag = "DRY " if DRY else ""

# legacy pk -> destination pathstring
MOVES = {
    2: "Electronics/Passives/Resistors",
    3: "Electronics/Passives/Capacitors",
    4: "Electronics/Passives/Potentiometers",
}
# individual parts that go somewhere other than their category's destination
OVERRIDE = {
    444: "Electronics/Passives/Potentiometers",   # a pot filed under Resistors
}
DELETE_AFTER = [2, 3, 4, 1]

failures = []


def resolve(path):
    return PartCategory.objects.get(pathstring=path)


print("=" * 72)
print(f"{tag}COLLAPSE [1] Passives -> Electronics/Passives")
print("=" * 72)

# ---------------------------------------------------------------- 1. moves
moved = []
for src_pk, dest_path in MOVES.items():
    src = PartCategory.objects.get(pk=src_pk)
    dest = resolve(dest_path)
    parts = list(Part.objects.filter(category=src).order_by("pk"))
    print(f"\n[{src_pk}] {src.pathstring}  ->  [{dest.pk}] {dest.pathstring}"
          f"   ({len(parts)} parts)")
    dest_names = {p.name.lower() for p in Part.objects.filter(category=dest)}
    for p in parts:
        target = resolve(OVERRIDE[p.pk]) if p.pk in OVERRIDE else dest
        note = "  <- OVERRIDE" if p.pk in OVERRIDE else ""
        clash = "  !! same name already in destination !!" if p.name.lower() in dest_names else ""
        print(f"    #{p.pk:5d} active={str(p.active):5s} -> [{target.pk}] "
              f"{p.name[:52]}{note}{clash}")
        if not DRY:
            Part.objects.filter(pk=p.pk).update(category=target)
            fresh = Part.objects.get(pk=p.pk)
            if fresh.category_id != target.pk:
                failures.append(f"#{p.pk} category still {fresh.category_id}")
            else:
                moved.append(p.pk)

# ------------------------------------------------------- 2. retire the kit
print("\n" + "=" * 72)
print(f"{tag}RETIRE #211 EAONE kit -- decomposed, same shape as #502")
print("=" * 72)
p211 = Part.objects.get(pk=211)

MAXDESC = Part._meta.get_field("description").max_length


def mark(orig, marker):
    """Original first, marker last -- and the MARKER is what must survive.

    docs/TRAPS.md: appending a suffix then truncating cuts off the suffix
    itself, losing the only visible sign the record is retired. Budget for it.
    """
    room = MAXDESC - len(marker) - 1
    head = (orig or "")[:max(room, 0)].rstrip()
    return (head + " " + marker).strip()


RETIRE_211 = ("[RETIRED as a part 2026-09-08 — an assortment kit is a LOCATION, "
              "not a part; 30 values counted in Kit - EAONE Resistor 30-value, "
              "839 pcs]")
RETIRE_DESC = mark(p211.description, RETIRE_211)
NOTE_211 = (
    "\n\n> **Retired as a part 2026-09-08.** The kit is on hand and correctly "
    "counted — its thirty values are parts #605–#634, all sited in "
    "`SLN/Laser Area/L2/L2-D4/Kits/Kit - EAONE Resistor 30-value`, 839 pcs "
    "across 30 stock rows. A quantity on THIS row would double-count them. "
    "Same treatment as #502. Purchase history above is preserved.\n")
print(f"    was: active={p211.active}  qty={p211.total_stock:g}")
print(f"    description ({len(RETIRE_DESC)}/{MAXDESC}) = {RETIRE_DESC!r}")
if not DRY:
    Part.objects.filter(pk=211).update(
        active=False, description=RETIRE_DESC,
        notes=(p211.notes or "") + NOTE_211)
    f = Part.objects.get(pk=211)
    if f.active or RETIRE_211 not in f.description:
        failures.append(f"#211 not retired: active={f.active}")

# ---------------------------------------------------- 3. YOKIVE twin merge
print("\n" + "=" * 72)
print(f"{tag}MERGE #8 -> #178 (YOKIVE 100R 500W). Survivor keeps evidence, takes name.")
print("=" * 72)
loser, keeper = Part.objects.get(pk=8), Part.objects.get(pk=178)
assert loser.total_stock == 0 and keeper.total_stock == 0, "stock appeared - stop"
KEEPER_NAME = loser.name  # tidy short name
MERGE_8 = ("[MERGED into part #178 on 2026-09-08 — import twin; #178 holds the "
           "IPN, supplier part, image and purchase history. No stock on either.]")
LOSER_DESC = mark(loser.description, MERGE_8)
print(f"    keeper #178 name: {keeper.name[:60]!r}")
print(f"                  ->  {KEEPER_NAME[:60]!r}")
print(f"    loser  #8 -> active=False, pointer in description")
if not DRY:
    Part.objects.filter(pk=178).update(name=KEEPER_NAME[:100])
    Part.objects.filter(pk=8).update(active=False, description=LOSER_DESC)
    k, l = Part.objects.get(pk=178), Part.objects.get(pk=8)
    if k.name != KEEPER_NAME[:100]:
        failures.append("#178 name not written")
    if l.active or MERGE_8 not in l.description:
        failures.append("#8 not retired")

# -------------------------------------------------- 4. delete empty cats
print("\n" + "=" * 72)
print(f"{tag}DELETE emptied categories (only if provably empty)")
print("=" * 72)
for pk in DELETE_AFTER:
    try:
        c = PartCategory.objects.get(pk=pk)
    except PartCategory.DoesNotExist:
        print(f"    [{pk}] already gone")
        continue
    n_parts = Part.objects.filter(category=c).count()
    n_kids = c.children.count()
    if DRY:
        # in a dry run nothing moved, so predict instead of measure
        predicted_parts = 0
        predicted_kids = 0 if pk == 1 else n_kids
        print(f"    [{pk}] {c.pathstring!r}  now parts={n_parts} children={n_kids}"
              f"  -> after moves would be parts={predicted_parts} "
              f"children={predicted_kids}  DELETE")
        continue
    if n_parts or n_kids:
        failures.append(f"[{pk}] {c.pathstring} NOT empty: "
                        f"parts={n_parts} children={n_kids} — left in place")
        print(f"    [{pk}] {c.pathstring!r} NOT EMPTY (parts={n_parts} "
              f"children={n_kids}) — REFUSING to delete")
        continue
    c.delete()
    if PartCategory.objects.filter(pk=pk).exists():
        failures.append(f"[{pk}] delete reported success, row still there")
    else:
        print(f"    [{pk}] {c.pathstring!r} deleted")

# ------------------------------------------------------------ 5. verdict
print("\n" + "=" * 72)
print("VERIFY")
print("=" * 72)
if not DRY:
    from collections import Counter  # noqa: E402
    roots = Counter(PartCategory.objects.filter(parent__isnull=True)
                    .values_list("tree_id", flat=True))
    bad = {t: n for t, n in roots.items() if n > 1}
    stale = [c.pk for c in PartCategory.objects.all()
             if c.pathstring != c.construct_pathstring()]
    print(f"    MPTT: tree_ids with >1 root = {bad or 'none'}; "
          f"stale pathstrings = {stale or 'none'}")
    if bad or stale:
        failures.append("MPTT damaged — run PartCategory.objects.rebuild()")
    for path in ("Electronics/Passives/Resistors",
                 "Electronics/Passives/Capacitors",
                 "Electronics/Passives/Potentiometers"):
        c = resolve(path)
        live = Part.objects.filter(category=c, active=True).count()
        dead = Part.objects.filter(category=c, active=False).count()
        print(f"    {path}: live={live} tombstones={dead}")
    print(f"    parts moved and confirmed: {len(moved)}")

print()
if failures:
    print("✗ FAILED")
    for f in failures:
        print(f"    {f}")
    sys.exit(1)
print("✓ DRY RUN OK — rerun with --commit" if DRY else "✓ SUCCESS")
