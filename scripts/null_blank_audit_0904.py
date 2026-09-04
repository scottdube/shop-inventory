"""Which other text fields can hide an empty behind NULL? Read-only.

Tonight's queue-D defect: Part.keywords is null=True, nothing in it is ever the
empty string, and so `filter(keywords='')` returned 0 by construction for three
consecutive nights while reading as a clean measurement.

That is a property of the FIELD, not of keywords specifically. Any nullable text
field on the models this job reports against can do the same thing to any future
"how many are missing X" count. So: enumerate them, and for each print BOTH
counts side by side. Where the two disagree, an `=''` test is lying.

Read-only. The point is to know which fields need the NULL-aware idiom, not to
write anything.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.db.models import CharField, FileField, TextField, URLField  # noqa: E402

from company.models import Company, SupplierPart  # noqa: E402
from order.models import PurchaseOrder  # noqa: E402
from part.models import Part  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

MODELS = [Part, SupplierPart, Company, PurchaseOrder, StockItem, StockLocation]
# FileField/ImageField included deliberately: Part.image is the field queue A
# counts its backlog with, and it is stored as a path string like any other.
TEXTY = (CharField, TextField, URLField, FileField)

EMPTY_COL = "=''"
print(f"{'model.field':<38} {'null':<5} {EMPTY_COL:>7} {'IS NULL':>8} {'either':>7}  verdict")
print("-" * 92)

risky = []
for model in MODELS:
    qs = model.objects
    for f in model._meta.get_fields():
        if not isinstance(f, TEXTY) or not getattr(f, "concrete", False):
            continue
        if f.choices:
            continue
        name = f"{model.__name__}.{f.name}"
        try:
            blank = qs.filter(**{f.name: ""}).count()
            isnull = qs.filter(**{f"{f.name}__isnull": True}).count()
        except Exception as e:  # noqa: BLE001 - a field we cannot query is not a finding
            print(f"{name:<38} {'?':<5} {'-':>7} {'-':>8} {'-':>7}  skipped: {e}")
            continue
        either = blank + isnull
        if not f.null:
            verdict = "safe: not nullable"
        elif isnull == 0:
            verdict = "nullable but no NULLs today"
        elif blank == 0:
            verdict = "*** ='' IS BLIND — every empty is NULL"
            risky.append((name, isnull))
        else:
            verdict = "*** MIXED — both spellings exist"
            risky.append((name, isnull))
        print(f"{name:<38} {str(f.null):<5} {blank:>7} {isnull:>8} {either:>7}  {verdict}")

print()
print("=== fields where a `filter(x='')` test would UNDER-REPORT ===")
if not risky:
    print("none")
for name, n in sorted(risky, key=lambda r: -r[1]):
    print(f"  {name:<38} {n} rows are NULL and invisible to `=''`")
print()
print("Use: qs.filter(f__isnull=True) | qs.filter(f='')   — never one alone.")
