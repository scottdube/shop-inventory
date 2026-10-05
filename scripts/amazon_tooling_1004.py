"""Amazon tooling with no stock row -> [ESTIMATE] stock from the part's own
purchase-history table. No PO. 2026-10-04, docs/tooling-inventory.md.

    itq run scripts/amazon_tooling_1004.py            # dry run: the plan, per part
    itq run scripts/amazon_tooling_1004.py --commit

Source of quantity: the "## Purchase history (Amazon)" table the Amazon importer
wrote into each part's notes (Date | Qty | Unit | Line total | Order; columns
read by header name). Paid lines count. $0 lines do NOT: on Amazon a $0 line is
a replacement or a free swap, so the first unit went back; counting both would
book two where one was ever kept.

Why no PO: an Amazon order mixes tooling with everything else, and a PO holding
only its tooling lines would be a partial order wearing the full order number
-- which is also the idempotency key, so the real import of that order would
later be skipped as "already done". The order numbers go in the stock note.

Qty is in SELLER UNITS times the supplier part's pack_quantity_native. Sets and
kits are one unit. Parts in PACKS (below) are refused unless the pack is set.

Scope = PLAN pks, chosen by hand from the baseline; everything else in Amazon's
tooling-ish categories is in SKIP with the reason.
"""
import argparse
import os
import re
import sys
from decimal import Decimal

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.db.models import Sum  # noqa: E402

from company.models import Company, SupplierPart  # noqa: E402
from part.models import Part  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
ap.add_argument("--only", default="")
a = ap.parse_args()

AMZ = Company.objects.get(name="Amazon")
dest = StockLocation.objects.get(pathstring="SLN/Machine Shop/Unfiled - Machine Shop")

PLAN = [131, 133, 135, 158, 166, 167, 171, 173, 176, 183, 184, 187, 194, 197, 198,
        204, 220, 224, 231, 233, 235, 240, 241, 243, 250, 251, 254, 257, 268, 271,
        273, 280, 282, 286, 287, 288, 289, 297, 298, 306, 307, 324, 335, 338, 343,
        348, 349, 356, 358, 359, 366, 377, 380, 382, 392, 393, 394, 404, 406,
        409, 414, 415, 416, 417, 424, 430, 433, 461, 462, 465, 466, 467, 473, 482,
        486, 487]
# Multipacks the importer left at pack_quantity 1; count read off the seller
# title kept in the part description ("2pcs", "5 Pieces", "10 PCS", "10-Pack").
# Written through .save() (TRAPS: only pack_quantity_native is read on receive).
PACKS = {197: 2, 235: 5, 349: 10, 392: 10, 394: 10}
# Left out: 1268 roughness tester has no purchase-history table; 391 GBJ TCMT
# inserts -- the title never states the count, and a box booked as 1 piece is
# wrong by 10x either way.
only = {int(x) for x in a.only.split(",") if x.strip()}


def history(notes):
    m = re.search(r"## Purchase history \(Amazon\)(.*?)(?:\n## |\Z)", notes or "", re.S)
    if not m:
        return None
    rows, hdr = [], None
    for ln in m.group(1).splitlines():
        if not ln.startswith("|"):
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if hdr is None:
            hdr = [c.lower() for c in cells]
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        r = dict(zip(hdr, cells))
        money = lambda s: Decimal(re.sub(r"[^0-9.]", "", s) or "0")
        rows.append({"date": r["date"], "qty": int(r["qty"]), "unit": money(r["unit"]),
                     "line": money(r["line total"]), "order": r["order"]})
    return rows


tot_rows = tot_pcs = 0
for pk in PLAN:
    if only and pk not in only:
        continue
    p = Part.objects.get(pk=pk)
    held = float(StockItem.objects.filter(part=p).aggregate(q=Sum("quantity"))["q"] or 0)
    sps = list(SupplierPart.objects.filter(part=p, supplier=AMZ))
    h = history(p.notes)
    flag = ""
    if not p.active:
        flag = "INACTIVE"
    elif held:
        flag = f"HOLDS {held:g}"
    elif not h:
        flag = "NO HISTORY TABLE"
    paid = [r for r in (h or []) if r["line"] > 0]
    free = [r for r in (h or []) if r["line"] <= 0]
    if pk in PACKS and a.commit and not flag:
        for sp in sps:
            if float(sp.pack_quantity_native or 1) != PACKS[pk]:
                sp.pack_quantity = str(PACKS[pk])
                sp.save()
                sp.refresh_from_db()
                assert float(sp.pack_quantity_native) == PACKS[pk], (sp.pk, sp.pack_quantity_native)
                print(f"      pack {sp.SKU} -> {PACKS[pk]}")
    packs = {float(PACKS.get(pk) or sp.pack_quantity_native or 1) for sp in sps}
    if len(packs) > 1:
        flag = f"MIXED PACKS {packs}"
    pack = packs.pop() if packs else 1.0
    units = sum(r["qty"] for r in paid)
    pcs = units * pack
    if not flag and not pcs:
        flag = "NO PAID LINE"
    print(f"{pk:5d} {'['+flag+'] ' if flag else ''}{p.name[:70]}")
    print(f"      units={units} pack={pack:g} -> {pcs:g} pcs; paid "
          + "; ".join(f"{r['date']} {r['qty']}x${r['unit']} {r['order']}" for r in paid)
          + (("  | $0: " + "; ".join(f"{r['date']} {r['order']}" for r in free)) if free else ""))
    if flag or not a.commit:
        continue
    sp = max(sps, key=lambda s: s.pk) if sps else None
    each = (sum(r["line"] for r in paid) / Decimal(str(pcs))).quantize(Decimal("0.0001"))
    lines = "; ".join(f"{r['date']} {r['qty']} x ${r['unit']} (order {r['order']})" for r in paid)
    extra = (" $0 lines NOT counted (replacement/free swap - the first unit went back): "
             + "; ".join(f"{r['date']} order {r['order']}" for r in free) + ".") if free else ""
    row = StockItem.objects.create(
        part=p, location=dest, quantity=pcs, supplier_part=sp,
        purchase_price=each, purchase_price_currency="USD",
        notes=(f"[ESTIMATE] PURCHASED QUANTITY, NOT A COUNT. Amazon purchases from this "
               f"part's purchase-history table: {lines}.{extra} No PO: Amazon orders mix "
               "tooling with everything else, and a partial PO under the full order number "
               "would block the real import of that order later. Tooling gets broken, worn "
               "out and thrown away; Scott 2026-10-04 chose purchase-based estimates "
               "pending a physical walk. No stocktake_date by design."))
    row.refresh_from_db()
    assert float(row.quantity) == pcs and row.notes.startswith("[ESTIMATE]")
    tot_rows += 1
    tot_pcs += pcs
    print(f"      WROTE stock item {row.pk}")

print(f"\nrows={tot_rows} pieces={tot_pcs:g}  " + ("COMMITTED" if a.commit else "DRY RUN - add --commit"))
