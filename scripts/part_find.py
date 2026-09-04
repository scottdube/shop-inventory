"""Search parts across every field a duplicate could be hiding in.

Rule 2 of the enrich job: parts were renamed to canonical form, so a vendor
title will NOT match by name. A duplicate has to be hunted across name,
description (which stores the vendor title as `orig: ...`), IPN, keywords and
supplier SKU — checking only one of those is how the PWM servo driver and the
logic level converter each got entered twice.

Read-only. Give it terms; it ORs them across all of the above.

    part_find.py PCF8574 B0GF1Q1GNG "I/O expander"
    part_find.py --category Electronics/Semiconductors/ICs
    part_find.py --category ICs --all      # include the tombstones

ALWAYS PRINTS active AND stock, and hides inactive parts unless you ask.
Added 2026-09-03 after a listing that showed neither burned most of a session:
a category dump printed `created=` but not `active=`, so three long-dead
tombstones read as live duplicates of NE555, ADUM1201 and PC817. All three had
been merged weeks earlier — one is literally named "[merged 16]". A part with
active=False and 0 stock is the RECEIPT FOR A MERGE THAT ALREADY HAPPENED, not
a problem to report. Those two columns are the whole difference and they are
not optional, which is why --category lives here instead of in yet another
one-off script.
"""
import argparse
import os
import sys

import django
from django.db.models import Q, Sum

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part, PartCategory  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("terms", nargs="*", help="OR'd across name/description/IPN/keywords/SKU")
ap.add_argument("--category", help="pathstring, e.g. Electronics/Semiconductors/ICs")
ap.add_argument("--all", action="store_true",
                help="include inactive parts (hidden by default — they are usually "
                     "merge tombstones, not findings)")
a = ap.parse_args()

if not a.terms and not a.category:
    ap.error("give search terms, --category, or both")

hits = Part.objects.all()

if a.category:
    try:
        cat = PartCategory.objects.get(pathstring=a.category)
    except PartCategory.DoesNotExist:
        near = [c.pathstring for c in PartCategory.objects.all()
                if a.category.lower() in c.pathstring.lower()]
        raise SystemExit(f"no category {a.category!r}."
                         + (f" did you mean: {near}" if near else ""))
    hits = hits.filter(category=cat)

if a.terms:
    q = Q()
    for t in a.terms:
        q |= (Q(name__icontains=t) | Q(description__icontains=t) | Q(IPN__icontains=t)
              | Q(keywords__icontains=t) | Q(supplier_parts__SKU__icontains=t))
    hits = hits.filter(q)

hidden = 0
if not a.all:
    hidden = hits.filter(active=False).distinct().count()
    hits = hits.filter(active=True)

hits = hits.annotate(qty=Sum("stock_items__quantity")).distinct().order_by("pk")

what = " ".join(filter(None, [f"{a.terms}" if a.terms else "",
                              f"in {a.category}" if a.category else ""]))
print(f"{hits.count()} hit(s) {what}")

for p in hits:
    sk = ", ".join(f"{sp.supplier}:{sp.SKU}" for sp in p.supplier_parts.all()[:3])
    qty = p.qty or 0
    print(f"#{p.pk}  active={p.active}  stock={qty:g}  {p.name[:60]}")
    print(f"      cat={p.category.pathstring if p.category else '-'}  IPN={p.IPN!r}")
    print(f"      desc={(p.description or '')[:110]}")
    if sk:
        print(f"      suppliers={sk}")

if hidden:
    print(f"\n{hidden} inactive part(s) hidden. These are almost always merge "
          f"tombstones — an inactive part with 0 stock is a merge that already "
          f"happened. Use --all only if you specifically need to see them.")
