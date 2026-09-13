"""Read-only: sweep EVERY supplier part for the pack-size defect.

Why a full sweep and not another four-part probe. pack_probe_0911.py checked the
four supplier parts that happened to get images that night, found them correct,
and stopped. That answered "did the 09-10 sweep get packs right?" — it did not
answer "how many pack sizes in the catalogue are wrong?", which is the question
the open decision item `pack-hygiene-as-standing-queue` is actually asking. A
sample that was selected by which parts got images is not a measurement of the
population.

Two independent defects are reported separately, because they have different
causes and different fixes:

  DEFECT  pack_quantity and pack_quantity_native disagree. Only the native
          field is read at receive time (see the pack-quantity trap), so the
          human-readable text can say "5" while receiving books 1. A queryset
          .update() on the text field produces exactly this.

  FLAG    the listing title carries a pack count > 1 ("4 Pack", "10Pcs",
          "Pack of 3") while pack_quantity is 1. That is the importer defect:
          an order line reads "1 x <seller title>" whether it is one cable or a
          bag of five, InvenTree's default of 1 sticks, and the pack size stays
          buried in the title until the goods land and the per-piece price is
          absurd. A FLAG is a candidate, not a verdict — some titles say "1
          Pack", and some counts in a title are not the pack ("2-Port hub").

Nothing is written. Pack sizes must go through .save(), never .update(), and on
an open PO the fix changes what receiving will book — so this reports and the
call stays Scott's.
"""
import os
import re
import sys
from decimal import Decimal, InvalidOperation

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import SupplierPart          # noqa: E402
from order.models import PurchaseOrderLineItem    # noqa: E402
from order.status_codes import PurchaseOrderStatus  # noqa: E402

OPEN = [PurchaseOrderStatus.PENDING.value, PurchaseOrderStatus.PLACED.value]

# Pack-count patterns. Only ever match an explicit pack/piece word, so that
# "USB 2.0", "3 Foot" and "2-Port" cannot be read as a pack size.
PACK_RE = [
    re.compile(r"(?<![\d.])(\d{1,4})\s*[- ]?\s*(?:pack|packs|pcs|pieces|piece|count|ct)\b", re.I),
    re.compile(r"pack\s+of\s+(\d{1,4})\b", re.I),
    re.compile(r"(?<![\d.])(\d{1,4})\s*[- ]?\s*p[cs]s?\b", re.I),
]


def pack_from_title(text):
    """Largest explicit pack count in the text, or None."""
    found = []
    for rx in PACK_RE:
        for m in rx.finditer(text or ""):
            try:
                n = int(m.group(1))
            except ValueError:
                continue
            if 1 < n <= 5000:
                found.append(n)
    return max(found) if found else None


def as_dec(v):
    if v in (None, ""):
        return None
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError):
        return None


open_line_sp = set(
    PurchaseOrderLineItem.objects.filter(order__status__in=OPEN)
    .exclude(part=None)
    .values_list("part_id", flat=True)
)

sps = SupplierPart.objects.select_related("part", "supplier").order_by("pk")

defects, flags = [], []
checked = 0

for sp in sps:
    checked += 1
    native = as_dec(sp.pack_quantity_native)
    text_q = as_dec(sp.pack_quantity)
    where = "OPEN-PO" if sp.pk in open_line_sp else "-"

    # DEFECT: the two stored copies disagree.
    if native is not None and text_q is not None and native != text_q:
        defects.append((sp, text_q, native, where))

    # FLAG: title says a pack, the stored pack size says one.
    title = " | ".join(
        str(x) for x in (sp.part.name, sp.part.description, sp.note, sp.SKU) if x
    )
    n = pack_from_title(title)
    if n and (native is None or native == 1):
        flags.append((sp, n, native, where))

print(f"supplier parts checked : {checked}")
print(f"  DEFECT (stored copies disagree) : {len(defects)}")
print(f"  FLAG   (title pack > 1, stored pack 1) : {len(flags)}")
print(f"  supplier parts on OPEN POs : {len(open_line_sp)}")

print("\n-- DEFECT: pack_quantity != pack_quantity_native (receive reads native) --")
if not defects:
    print("   none")
for sp, t, n, where in defects:
    print(f"   SP {sp.pk:4d} | {where:7s} | text={t} native={n} | {sp.supplier.name} {sp.SKU} | part #{sp.part.pk} {sp.part.name[:44]}")

print("\n-- FLAG: listing title carries a pack count, stored pack size is 1 --")
if not flags:
    print("   none")
for sp, n, native, where in flags:
    print(f"   SP {sp.pk:4d} | {where:7s} | title says {n:4d}, stored {native} | {sp.supplier.name} {sp.SKU}")
    print(f"            part #{sp.part.pk} {sp.part.name[:60]}")
    print(f"            desc: {(sp.part.description or '')[:110]}")
