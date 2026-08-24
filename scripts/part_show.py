"""Show parts by pk — the '#970' numbers the overnight reports quote.

part_find.py searches by text; this one takes the bare numbers directly, because
that is the form the enrich reports and the journal actually cite. Prints the
web URL too, so the number in a report is one click from the real record.

Read-only. Accepts '970', '#970' or 'part 970'.
"""
import argparse
import os
import re
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part  # noqa: E402

BASE = "http://192.168.50.10:8001/web/part"

ap = argparse.ArgumentParser()
ap.add_argument("pks", nargs="+", help="part numbers, e.g. 970 #227 1082")
a = ap.parse_args()

for raw in a.pks:
    m = re.search(r"\d+", raw)
    if not m:
        print(f"?? {raw}: no number in that")
        continue
    pk = int(m.group())
    p = Part.objects.filter(pk=pk).first()
    if not p:
        print(f"?? #{pk}: no such part")
        continue

    stock = p.total_stock
    sup = list(p.supplier_parts.all()[:4])
    print(f"#{p.pk}  {p.name}")
    print(f"   {BASE}/{p.pk}/")
    print(f"   category = {p.category.pathstring if p.category else '-'}"
          f"   active={p.active}   IPN={p.IPN or '-'}")
    print(f"   in stock = {stock}"
          f"   image={'yes' if p.image else 'NO'}"
          f"   keywords={'yes' if (p.keywords or '').strip() else 'NO'}")
    if p.description:
        print(f"   desc: {p.description[:150]}")
    for sp in sup:
        print(f"   supplier: {sp.supplier} : {sp.SKU}")
    print()
