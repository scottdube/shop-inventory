"""Mirror binscan's counted-marker into InvenTree's real stocktake_date.

binscan records a count in the stock item's NOTES, not in stocktake_date, and
that is forced rather than chosen. Measured 2026-08-22 against this install:

    stocktake_date              read_only on the serializer. PATCH returns
                                HTTP 200 and changes nothing.
    metadata                    same -- 200, silently ignored. The dedicated
                                /api/stock/<pk>/metadata/ endpoint answers 403
                                CSRF for a token client.
    POST /api/stock/count/      does set stocktake_date, but is a NO-OP when
                                the counted figure equals the stored one.

That last one is the trap. B2-R3C8 held 50 from a purchase, Scott counted 50,
and nothing recorded that a count had happened -- the confirming count, which
is the only thing that turns a purchased figure into a verified one, was the
exact case that could not be written.

The ORM is not bound by the serializer, so this script sets the field directly.

    itq run scripts/sync_stocktake.py
    itq run scripts/sync_stocktake.py --commit

Run it after a walk. Nothing depends on it being prompt -- binscan reads its own
marker -- but InvenTree's own never-counted reports read stocktake_date, and
they should agree with the app.
"""
import argparse
import os
import re
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from stock.models import StockItem      # noqa: E402

MARK = re.compile(r"binscan (\d{4}-\d\d-\d\d): filed into \S+ and COUNTED at "
                  r"([\d.]+) by hand", re.I)

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

todo, mismatched = [], []
for s in StockItem.objects.filter(notes__icontains="COUNTED at"):
    m = MARK.search(s.notes or "")
    if not m:
        continue
    when, qty = m.group(1), float(m.group(2))
    if abs(float(s.quantity) - qty) > 1e-6:
        # The row was counted and then changed by something else. Do not stamp
        # a stocktake date onto a quantity nobody counted.
        mismatched.append((s, when, qty))
        continue
    if str(s.stocktake_date) != when:
        todo.append((s, when))

print(f"  {len(todo)} row(s) need stocktake_date set from a binscan count")
for s, when in todo:
    print(f"    stock {s.pk:>5}  {s.location.name if s.location else '-':<10} "
          f"qty {float(s.quantity):>6g}  {str(s.stocktake_date):<12} -> {when}   "
          f"{s.part.name[:40]}")

if mismatched:
    print(f"\n  {len(mismatched)} row(s) SKIPPED — counted once, quantity has moved since:")
    for s, when, qty in mismatched:
        print(f"    stock {s.pk:>5}  counted {qty:g} on {when}, now {float(s.quantity):g}"
              f"   {s.part.name[:40]}")
    print("    Recount these rather than back-dating a stocktake onto a number")
    print("    nobody verified.")

if not a.commit:
    print("\n  DRY RUN — add --commit")
    raise SystemExit

n = 0
for s, when in todo:
    StockItem.objects.filter(pk=s.pk).update(stocktake_date=when)
    if str(StockItem.objects.get(pk=s.pk).stocktake_date) == when:
        n += 1
print(f"\n  {n}/{len(todo)} written and verified")
