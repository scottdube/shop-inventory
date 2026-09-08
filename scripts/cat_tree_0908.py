"""Read-only: shape of the two overlapping passives trees, plus MPTT health.

Not a part lister -- part_find.py --category is that, and it prints active and
stock (docs/TRAPS.md, "An inactive part with 0 stock is a RECEIPT"). This
prints CATEGORY structure: parents, children, direct vs descendant part counts
split live/tombstone, and whether anything else points at these categories.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part, PartCategory  # noqa: E402
from stock.models import StockItem  # noqa: E402

def counts(cat):
    direct = Part.objects.filter(category=cat)
    desc_cats = cat.get_descendants(include_self=True)
    desc = Part.objects.filter(category__in=desc_cats)
    return (direct.filter(active=True).count(), direct.filter(active=False).count(),
            desc.filter(active=True).count(), desc.filter(active=False).count())

print("=" * 70)
print("EVERY ROOT CATEGORY (parent is null)")
print("=" * 70)
for c in PartCategory.objects.filter(parent__isnull=True).order_by("pk"):
    la, li, da, di = counts(c)
    print(f"[{c.pk}] {c.name!r}  direct live={la} dead={li} | subtree live={da} dead={di}"
          f"  children={c.children.count()}  tree_id={c.tree_id} lvl={c.level}")

print()
print("=" * 70)
print("FULL SUBTREE OF EVERY ROOT THAT CONTAINS 'passive' ANYWHERE")
print("=" * 70)
roots = set()
for c in PartCategory.objects.all():
    if "passive" in c.pathstring.lower():
        roots.add(c.get_root().pk)
for rpk in sorted(roots):
    r = PartCategory.objects.get(pk=rpk)
    for c in r.get_descendants(include_self=True).order_by("lft"):
        la, li, da, di = counts(c)
        pad = "  " * c.level
        flag = ""
        if c.pathstring != c.construct_pathstring():
            flag += "  !!PATHSTRING STALE!!"
        if c.level != len(c.pathstring.split("/")) - 1:
            flag += "  !!LEVEL MISMATCH!!"
        print(f"{pad}[{c.pk}] {c.name}  live={la} dead={li} (subtree {da}/{di})"
              f"  parent={c.parent_id}  structural={c.structural}"
              f"  default_loc={c.default_location or '-'}{flag}")
        if c.description:
            print(f"{pad}     desc={c.description[:90]!r}")

print()
print("=" * 70)
print("MPTT HEALTH -- PartCategory")
print("=" * 70)
from collections import Counter  # noqa: E402
roots_per_tree = Counter(PartCategory.objects.filter(parent__isnull=True)
                         .values_list("tree_id", flat=True))
bad = {t: n for t, n in roots_per_tree.items() if n > 1}
print("tree_ids with >1 root:", bad or "none")
stale = [c.pk for c in PartCategory.objects.all()
         if c.pathstring != c.construct_pathstring()]
print("categories with stale pathstring:", stale or "none")

print()
print("=" * 70)
print("ANYTHING ELSE POINTING AT [1] [2] [49] [50] [69]")
print("=" * 70)
for pk in (1, 2, 49, 50, 69):
    try:
        c = PartCategory.objects.get(pk=pk)
    except PartCategory.DoesNotExist:
        print(f"[{pk}] MISSING"); continue
    refs = []
    n = Part.objects.filter(default_location__isnull=False, category=c).count()
    kids = list(c.children.values_list("pk", "name"))
    # parameter templates attached to the category
    try:
        pt = c.parameter_templates.count()
    except Exception:
        pt = "n/a"
    print(f"[{pk}] {c.pathstring!r}  children={kids}  category_parameter_templates={pt}"
          f"  starred_by={c.get_starred_users().count() if hasattr(c,'get_starred_users') else 'n/a'}")

print()
print("=" * 70)
print("STOCK SITTING UNDER EITHER RESISTOR CATEGORY (by part category)")
print("=" * 70)
for pk in (2, 69):
    c = PartCategory.objects.get(pk=pk)
    items = StockItem.objects.filter(part__category__in=c.get_descendants(include_self=True))
    print(f"[{pk}] {c.pathstring}: {items.count()} stock rows, "
          f"total qty {sum(i.quantity for i in items):g}")
