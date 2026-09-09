"""Look up POs by vendor order number (supplier_reference) — the idempotency key.

InvenTree forces the visible `reference` to PO-nnnn, so the vendor's own order
number lives in `supplier_reference`. That field, not the reference, is what
tells you whether tonight's sweep has already imported an order. Checking the
wrong one is how the same order gets a second PO.

Read-only. Give it order numbers; it says which already exist.

**Comparison is normalized, not raw** (fixed 2026-09-09, decision
`po-check-hyphen-blind`). A vendor prints one punctuation of its order number
and links another: Walmart shows `Order# 2000151-82176030` on the page while
its own detail URL is `/orders/200015182176030`. Against the same instance in
the same minute, a raw comparison answered `absent 200015182176030` and
`EXISTS 2000151-82176030 -> PO-0142` — so a sweep that scraped the href and
believed `absent` would have created a duplicate PO silently. `supplier_reference`
is the idempotency key this whole job turns on, and an idempotency key that is
punctuation-sensitive is not one. `vendor_triage.py` got this same fix on
2026-08-27; po_check.py, the script the task file actually names as THE key,
did not — which is the gap this closes.

Normalizing is a strict superset of the old behaviour: every raw match still
matches. Matches found ONLY after normalizing are flagged `~norm`, so the
looser comparison is visible rather than silent.
"""
import argparse
import os
import re
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from order.models import PurchaseOrder  # noqa: E402


def _norm(s):
    """Same normalization vendor_triage.py uses — keep the two identical."""
    return re.sub(r"[^A-Za-z0-9]", "", s or "").lower()


ap = argparse.ArgumentParser()
ap.add_argument("orders", nargs="*")
ap.add_argument("--recent", type=int, default=0, help="also list N most recent POs")
a = ap.parse_args()

# Index every PO under the normalized form of BOTH its keys. Values are lists:
# a collision is real information (two POs for one order is the bug we hunt),
# so it must be printed, not silently resolved to one row.
index = {}
for po in PurchaseOrder.objects.all():
    for key in (_norm(po.supplier_reference), _norm(po.reference)):
        if key:
            index.setdefault(key, [])
            if po not in index[key]:
                index[key].append(po)

for o in a.orders:
    exact = PurchaseOrder.objects.filter(supplier_reference=o) | \
            PurchaseOrder.objects.filter(reference=o)
    exact = list(exact.distinct())
    hits = exact or index.get(_norm(o), [])
    if hits:
        how = "" if exact else "  ~norm"
        for po in hits:
            print(f"EXISTS  {o} -> {po.reference} (supplier_ref={po.supplier_reference!r}, "
                  f"status={po.get_status_display()}, supplier={po.supplier}, "
                  f"lines={po.lines.count()}){how}")
        if len(hits) > 1:
            print(f"  !! {o} matches {len(hits)} POs — possible duplicate import")
    else:
        print(f"absent  {o}")

if a.recent:
    print(f"\n--- {a.recent} most recent POs ---")
    for po in PurchaseOrder.objects.order_by("-pk")[: a.recent]:
        n = po.lines.count()
        priced = po.lines.exclude(purchase_price=None).count()
        print(f"{po.reference:12s} supplier_ref={str(po.supplier_reference)[:28]:28s} "
              f"{po.get_status_display():10s} {str(po.supplier)[:18]:18s} "
              f"lines={n} priced={priced} date={po.issue_date}")
