#!/usr/bin/env python3
"""Verify B-02's re-parent after a queryset .update(parent=...), and rebuild.

WHAT WAS OBSERVED, and it is not the same as what caused it.
make_b03_ethernet.py moved B-02 with StockLocation.objects.update(parent=...).
Immediately after, a FRESH .get() printed the OLD pathstring
(SLN/Storage/WS2/WS2-S3/B-02) while the new parent's get_children() already
listed B-02. By the time this script read the row, pathstring was CORRECT with
no write in between that I made.

**The cause is NOT established.** Candidates not tested: an InvenTree
background task rebuilding location paths, a cached object in the first
script's process, or something in the ORM layer. Do not write any of them down
as the reason. What IS established: pathstring is denormalised on this model
and .update() does not call save(), so a re-parent by queryset is at minimum
not guaranteed to refresh it -- and MPTT's lft/rght/level are in the same
position.

So the standing advice stands on its own merits without needing that cause:
**re-parent a location through the INSTANCE (.save()), not the queryset.** This
is the .save()-vs-.update() rule running the other way round. Elsewhere on this
install .save() has silently written nothing and .update() is the safe choice;
for a TREE model with a denormalised path it is the unsafe one.

This script re-asserts the parent through the instance, runs a full MPTT
rebuild (cheap at this tree size), and then checks EVERY location's pathstring
against its parent's, so the verdict is about the whole tree and not just B-02.

    itq run scripts/fix_b02_reparent.py [--commit]
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from stock.models import StockLocation  # noqa: E402

COMMIT = "--commit" in sys.argv
B02_PK, SHELF_PK, B03_PK = 617, 511, 618

b = StockLocation.objects.get(pk=B02_PK)
print("BEFORE")
print(f"  pathstring : {b.pathstring}")
print(f"  parent_id  : {b.parent_id}   (expected {SHELF_PK})")
print(f"  mptt       : tree={b.tree_id} lft={b.lft} rght={b.rght} level={b.level}")
sib = StockLocation.objects.get(pk=B03_PK)
print(f"  B-03 mptt  : tree={sib.tree_id} lft={sib.lft} rght={sib.rght} level={sib.level}")
print(f"  stale?     : {'LW3' not in b.pathstring}")

if not COMMIT:
    print("\nDRY RUN — nothing written. Re-run with --commit.")
    sys.exit(0)

# Re-set the parent through the INSTANCE so MPTT moves the node properly and
# save() regenerates pathstring.
shelf = StockLocation.objects.get(pk=SHELF_PK)
b.parent = shelf
b.save()

# A full rebuild is cheap at this tree size and is the only way to be sure the
# nested set is coherent after a raw .update() touched it.
StockLocation.objects.rebuild()

b = StockLocation.objects.get(pk=B02_PK)
sib = StockLocation.objects.get(pk=B03_PK)
shelf = StockLocation.objects.get(pk=SHELF_PK)
print("\nAFTER")
print(f"  pathstring : {b.pathstring}")
print(f"  parent_id  : {b.parent_id}")
print(f"  mptt       : tree={b.tree_id} lft={b.lft} rght={b.rght} level={b.level}")
print(f"  B-03 path  : {sib.pathstring}")
print(f"  shelf kids : {[c.name for c in shelf.get_children()]}")
print(f"  ancestors  : {[a.name for a in b.get_ancestors()]}")

ok = (b.pathstring == "SLN/Laser Area/LW3/LW3-S1/B-02"
      and b.parent_id == SHELF_PK
      and sib.pathstring == "SLN/Laser Area/LW3/LW3-S1/B-03"
      and {c.name for c in shelf.get_children()} == {"B-02", "B-03"})
print(f"\n  REPAIRED: {ok}")

# Anything else the raw update may have left stale, tree-wide.
bad = [l for l in StockLocation.objects.all()
       if l.parent_id and not l.pathstring.startswith(
           StockLocation.objects.get(pk=l.parent_id).pathstring + "/")]
print(f"  other locations with a pathstring inconsistent with their parent: {len(bad)}")
for l in bad[:10]:
    print(f"     pk {l.pk}  {l.pathstring}   parent={l.parent.pathstring}")
sys.exit(0 if ok else 1)
