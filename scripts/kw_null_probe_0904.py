"""Is the queue-D closure measuring what it thinks it is? Read-only.

Three consecutive runs (2026-09-01, 09-02, 09-03) reported "0 of 107x active
parts have an empty keywords field" and closed queue D on the strength of it.
Tonight's state read printed BOTH of these, from the same script:

    empty keywords        : 0        <- active.filter(keywords='')
    pk 1172 ... kw=n                 <- bool(p.keywords) is False

Both cannot be true unless the field is NULL rather than '', because Django's
`filter(keywords='')` does not match NULL. So the closure query may have been
blind to an entire class of empty. This separates the two and counts each.

Same failure shape as the 2026-09-03 order__status=10 bug: a wrong question
answered confidently reads exactly like a clean result.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part  # noqa: E402

f = Part._meta.get_field("keywords")
print(f"Part.keywords field: null={f.null} blank={f.blank} max_length={f.max_length}")
print()

active = Part.objects.filter(active=True)
for label, qs in (("ALL parts", Part.objects), ("ACTIVE parts", active)):
    total = qs.count()
    blank = qs.filter(keywords="").count()
    isnull = qs.filter(keywords__isnull=True).count()
    empty = qs.filter(keywords__isnull=True).count() + qs.filter(keywords="").count()
    print(f"{label}: total={total}  keywords=''  -> {blank}   "
          f"keywords IS NULL -> {isnull}   either -> {empty}")

print()
print("-- ACTIVE parts whose keywords are empty by EITHER test --")
qs = (active.filter(keywords__isnull=True) | active.filter(keywords="")).distinct()
rows = list(qs.order_by("pk"))
print(f"count = {len(rows)}")
for p in rows:
    print(f"   pk {p.pk:5d} | {p.name[:58]:<58} | kw={p.keywords!r} | "
          f"cat={p.category.name if p.category else '-'}")

print()
print("-- INACTIVE parts with empty keywords (tombstones; must STAY empty) --")
inact = Part.objects.filter(active=False)
n = (inact.filter(keywords__isnull=True) | inact.filter(keywords="")).distinct().count()
print(f"count = {n}")
