#!/usr/bin/env python3
"""Start B-04 on LW3-S1 and move the Ethernet termination stock into it.

Scott, 2026-09-19, looking at B-03 with the keystone bag and the plug jar in
hand: "wont fit in b3 ... could start b4 I guess."

SECOND TIME TODAY A CORRECT CATEGORY MATCH WAS THE WRONG ANSWER. B-03 is the
ETHERNET & PoE bin, these are Ethernet parts, and they were filed there this
morning on exactly that reasoning. They do not fit. B3-R6C4 went the same way
an hour earlier -- right category, right size class, full. **The database has
no volume, only a row count, and a bag of 15 jacks and a jar of 100 plugs are
one row each.** See TECHNIQUES.md.

WHAT MOVES AND WHY THAT SPLIT. B-03 keeps the powered gear, the cables and the
inline adapters -- things you reach for with a run already in mind. B-04 takes
the TERMINATION consumables: the keystone bag, the plug jar, and eventually
the punchdown tool and pass-through crimper that neither of them has. That is
a real distinction and not just an overflow shelf: one bin is "connect two
things that already have plugs", the other is "put a plug on".

The couplers and splitters STAY in B-03 despite being connectors. They are
small, they are inline devices used mid-run, and #1231 carries the passive-PoE
hazard note that wants to sit next to POE-003.

CONTAINER NOT RECORDED. B-02's description names its box ("6 qt clear snap-on
lid") because somebody looked at it. Nobody has told me what B-04 is, so it
says so rather than inheriting B-02's.

    itq run scripts/add_bin_b04.py [--commit]
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

COMMIT = "--commit" in sys.argv
SHELF_PK = 511            # SLN/Laser Area/LW3/LW3-S1
B03_PK = 618
NAME = "B-04"

DESC = ("ETHERNET TERMINATION. Keystone jacks, RJ45 plugs, and the tools to "
        "fit them - as opposed to B-03, which is gear and cables that already "
        "have plugs on. Split off B-03 2026-09-19: bag and jar would not fit. "
        "Container not yet recorded.")

# B-03's description is REPLACED, not appended to - it was already near the
# 250-char ceiling and an append blew past it. Same facts, tighter.
B03_DESC = ("ETHERNET & PoE. Injectors, terminal units, cables, adapters and "
            "their supplies. Termination consumables moved OUT to B-04 "
            "2026-09-19, would not fit; couplers/splitters STAY (small, "
            "inline, and #1231's hazard note belongs beside POE-003).")

MOVE_PARTS = [1234, 1235]   # keystone jacks (has a row), pass-through plugs (none yet)

shelf = StockLocation.objects.get(pk=SHELF_PK)
b03 = StockLocation.objects.get(pk=B03_PK)
existing = StockLocation.objects.filter(parent=shelf, name=NAME).first()

print(f"shelf     [{shelf.pk}] {shelf.pathstring}")
print(f"siblings  {[l.name for l in StockLocation.objects.filter(parent=shelf).order_by('name')]}")
print(f"{NAME}       {('exists #%d' % existing.pk) if existing else 'will create'}")
print(f"desc      {len(DESC)}/250")
print(f"B-03 desc {len(B03_DESC)}/250 (REPLACED, not appended)")
for pk in MOVE_PARTS:
    p = Part.objects.get(pk=pk)
    rows = StockItem.objects.filter(part=p)
    print(f"  move #{pk} {p.name[:44]:44s} rows={rows.count()} "
          f"({', '.join('%g @ %s' % (r.quantity, r.location.name) for r in rows) or 'none'})")
if len(DESC) > 250 or len(B03_DESC) > 250:
    print("\nDESCRIPTION TOO LONG."); sys.exit(1)

if not COMMIT:
    print("\nDRY RUN — nothing written. Re-run with --commit.")
    sys.exit(0)

if existing is None:
    b04 = StockLocation.objects.create(parent=shelf, name=NAME, description=DESC,
                                       metadata={"labeled": False})
else:
    b04 = existing
    StockLocation.objects.filter(pk=b04.pk).update(description=DESC)

StockLocation.objects.rebuild()          # tree fields: instance-then-rebuild, per TRAPS
b04.refresh_from_db()

StockLocation.objects.filter(pk=b03.pk).update(description=B03_DESC)

moved = []
for pk in MOVE_PARTS:
    p = Part.objects.get(pk=pk)
    Part.objects.filter(pk=pk).update(default_location=b04)
    for r in StockItem.objects.filter(part=p, location=b03):
        StockItem.objects.filter(pk=r.pk).update(location=b04)
    p.refresh_from_db()
    moved.append(p)

b03.refresh_from_db()
print(f"\n[{b04.pk}] {b04.pathstring}")
print(f"    lft/rght/level/tree  {b04.lft}/{b04.rght}/{b04.level}/{b04.tree_id}")
print(f"    parent               {b04.parent.pathstring}")
print(f"    pathstring correct   {b04.pathstring == shelf.pathstring + '/' + NAME}")
print(f"    metadata             {b04.metadata}")
print(f"    desc                 {b04.description[:76]}...")
for p in moved:
    rows = StockItem.objects.filter(part=p)
    print(f"\n#{p.pk} {p.name}")
    print(f"    default_location  {p.default_location.pathstring}"
          f"  {'ok' if p.default_location_id == b04.pk else '!! WRONG'}")
    for r in rows:
        print(f"    stock [{r.pk}] qty {r.quantity:g} @ {r.location.pathstring}"
              f"  {'ok' if r.location_id == b04.pk else '!! WRONG'}")
    if not rows:
        print("    NO STOCK ROW  <- still awaiting a count from Scott")
print(f"\nB-03 now holds {StockItem.objects.filter(location=b03).count()} rows, "
      f"B-04 holds {StockItem.objects.filter(location=b04).count()}")
print(f"B-03 note updated  {'moved OUT to B-04' in b03.description}")
print("\nLABEL: NOT printed. B-04 needs a new tape (template 9) — ask Scott first.")
