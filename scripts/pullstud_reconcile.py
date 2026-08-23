"""Two corrections from Scott, 2026-08-23, both to the previous receive pass.

1. "those were all rec as ordered" — the historical Tormach and MSC orders
   arrived complete. The 2-vs-1 DISCREPANCY warnings written onto #535, #536,
   #537 and #540 are wrong: the orders say 2, the deleted placeholders assumed
   1, and the orders were right. Those notes are rewritten and the durable
   tooling is stocktaken to Scott's confirmation.

2. "pull studs are 20 total 2 diff kinds TSC and normal 1 pack of 10 each" —
   the catalogue carried FOUR pull-stud parts totalling 36 units. Scott counted
   20, in two Haas packs.

   The four parts are all genuinely different vendor items, so this is not a
   duplicate-part merge. It is a CONSUMPTION finding, and an obvious one in
   hindsight: **a pull stud lives screwed into a tool holder.** The Shars studs
   (7, bought 2024–2025) and the Tormach studs (9, bought 2024-02 alongside the
   2024 holders) are installed in holders on the rack. They are not spares and
   never were. The 20 Haas studs bought in the last month are the actual spares.

   So #120 and #539 go to zero WITH THE REASON ON THE ROW, and keep their PO
   links and prices. They are the spent history of two purchases, exactly like
   #292's zero row.

WHAT THIS PASS GOT WRONG, and it is worth stating: receiving PO-0025/PO-0026 on
2026-08-23 wrote 9 pull studs into stock as if they were on a shelf. The check
run beforehand asked "does a stock row already exist for this part" — it did
not, so the receive looked safe. The right question was "is this part the kind
of thing that gets CONSUMED into another part", and nothing in the data answers
it. Only Scott's count caught it.

Not touched: #543, the carbide face-mill insert. Same consumable logic applies —
an insert bought in 2024 may well be worn out and gone — and nobody has said.
It keeps its received quantity and no stocktake_date, and OPEN.md carries the
question.
"""
import argparse
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from stock.models import StockItem              # noqa: E402

TODAY = "2026-08-23"

CONFIRMED = (
    "Received as ordered — Scott confirmed {TODAY}, when asked directly about the "
    "quantity. The order says {q} and the [CONFIRMED OWNED] placeholder deleted on "
    "{TODAY} assumed 1; the order was right.\n\n"
    "EVIDENCE TIER: a person's statement that the shipment arrived complete, NOT a "
    "tally of the rack. Good enough to count for a tool holder, which nothing "
    "consumes. It would NOT be good enough for a consumable — see the pull studs, "
    "where 'received as ordered' and 'on the shelf' turned out to be different "
    "numbers by 16."
).replace("{TODAY}", TODAY)

SPENT = (
    "COUNTED 0 by implication, {TODAY}. Scott counted the pull studs: 20 total, two "
    "kinds, one 10-pack each — the Haas Standard (#110) and Haas TSC (#113) packs "
    "bought in the last month. These {q} are not among them.\n\n"
    "A pull stud lives screwed into a tool holder. {why} They are installed, not "
    "missing, and this row is the spent history of that purchase — it keeps the "
    "price and the order link and stays at zero.\n\n"
    "NOT independently verified: nobody has unscrewed a holder to look. If a holder "
    "ever turns up bare, this is the row that says where its stud went."
).replace("{TODAY}", TODAY)

WHY_SHARS = ("Bought loose from Shars across 2024 and 2025, in the same period the "
             "rack filled up.")
WHY_TORMACH = ("Bought from Tormach in February 2024 on the SAME two orders as the "
               "BT30 holders they screw into: PO-0025 carried 7 holders and 8 studs, "
               "PO-0026 carried 1 arbor and 1 stud. Eight holders, nine studs, bought "
               "together — near 1:1 is what installing them looks like.")

# (part_pk, new_qty, kind, extra) — kind drives which note template is used
PLAN = [
    # --- durable tooling, quantity confirmed by Scott ------------------------
    (535, 2, "CONFIRMED", None),
    (536, 2, "CONFIRMED", None),
    (537, 2, "CONFIRMED", None),
    (538, 1, "CONFIRMED", None),
    (540, 2, "CONFIRMED", None),
    (541, 1, "CONFIRMED", None),
    (542, 1, "CONFIRMED", None),
    (544, 1, "CONFIRMED", None),
    (927, 1, "CONFIRMED", None),
    # --- the two Haas packs: these ARE the 20 -------------------------------
    (110, 10, "PACK", "Standard"),
    (113, 10, "PACK", "TSC"),
    # --- installed studs, to zero -------------------------------------------
    (120, 0, "SPENT", WHY_SHARS),
    (539, 0, "SPENT", WHY_TORMACH),
]

PACK = (
    "COUNTED {TODAY} — Scott: \"pull studs are 20 total, 2 diff kinds, TSC and "
    "normal, 1 pack of 10 each.\" This is the {kind} pack, unopened count 10.\n\n"
    "These two Haas packs are the shop's ONLY spare pull studs. The older Shars "
    "(#120) and Tormach (#539) purchases are installed in holders and read zero.\n\n"
    "EVIDENCE TIER: counted by a person as whole packs, not tallied stud by stud. "
    "The part counts individual studs, not packs — 10 here means ten studs."
).replace("{TODAY}", TODAY)

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

user = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()

for part_pk, target, kind, extra in PLAN:
    items = list(StockItem.objects.filter(part_id=part_pk).order_by("pk"))
    if not items:
        print(f"  !! part {part_pk}: no stock rows")
        continue
    name = items[0].part.name[:52]
    have = sum(float(i.quantity) for i in items)
    print(f"\n[{part_pk}] {name}")
    print(f"    {have:g} on {len(items)} row(s) -> target {target:g}")

    for it in items:
        q = float(it.quantity)
        if kind == "CONFIRMED":
            note = CONFIRMED.format(q=f"{q:g}")
            newq = q                      # quantity unchanged; this only confirms it
        elif kind == "PACK":
            note = PACK.format(kind=extra)
            newq = q
        else:
            note = SPENT.format(q=f"{q:g}", why=extra)
            newq = 0

        po = it.purchase_order.reference if it.purchase_order else "-"
        print(f"      item {it.pk}: {q:g} -> {newq:g}  (po={po})  stocktake -> {TODAY}")
        if a.commit:
            it.stocktake(newq, user, notes=f"Reconciled {TODAY}")
            # StockItem.stocktake() stamps stocktake_date ONLY when something
            # actually changes. A CONFIRMING count changes nothing by definition,
            # so the stamp is silently skipped and the row still reads "never
            # counted" — the exact opposite of what just happened. Write it.
            StockItem.objects.filter(pk=it.pk).update(
                notes=note, stocktake_date=TODAY, stocktake_user=user)

if a.commit:
    print("\n" + "=" * 74)
    print("VERIFY — re-read from the database")
    print("=" * 74)
    ok = True
    for part_pk, target, kind, extra in PLAN:
        items = StockItem.objects.filter(part_id=part_pk)
        tot = sum(float(i.quantity) for i in items)
        dated = all(i.stocktake_date is not None for i in items)
        noted = all(i.notes and "2026-08-23" in i.notes for i in items)
        flag = "ok " if (tot == target and dated and noted) else "BAD"
        if flag == "BAD":
            ok = False
        print(f"  {flag} [{part_pk}] total={tot:g} (want {target:g}) "
              f"stocktake_date_set={dated} notes_written={noted}")
    print("\nALL VERIFIED" if ok else "\n*** MISMATCH — investigate ***")

print("\n" + ("WROTE" if a.commit else "DRY RUN — add --commit"))
