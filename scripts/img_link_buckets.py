"""Bucket every imageless part by the host in its `link` field.

Queue A has always been driven off `SupplierPart.SKU`, which covers only 73 of
the 494 imageless parts. The other 421 have no supplier part at all — they came
from the drawer walk, and the queue has never had a way to see whether any of
them are sourceable.

`Part.link` is the missing handle: it is set at creation for McMaster (derived
from the IPN) and for anything entered from a vendor product page. Bucketing by
host answers "is there a pool here worth a method" in one read, instead of
eyeballing 421 rows.

Read-only.
"""
import os
import sys
from collections import defaultdict
from urllib.parse import urlparse

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part  # noqa: E402

NOIMG = Q(image="") | Q(image__isnull=True)

qs = Part.objects.filter(NOIMG).distinct().order_by("pk")
by_host = defaultdict(list)
no_link_no_sp = 0
no_link_but_sp = 0

for p in qs:
    link = (p.link or "").strip()
    if link:
        host = (urlparse(link).netloc or "?").lower().removeprefix("www.")
        by_host[host].append((p.pk, p.name, p.active))
        continue
    if p.supplier_parts.exists():
        no_link_but_sp += 1
    else:
        no_link_no_sp += 1

print(f"imageless parts: {qs.count()}")
print(f"  with a link      : {sum(len(v) for v in by_host.values())}")
print(f"  no link, has SP  : {no_link_but_sp}")
print(f"  no link, no SP   : {no_link_no_sp}   <- unreachable by any URL method")
print()
for host, rows in sorted(by_host.items(), key=lambda kv: -len(kv[1])):
    live = [r for r in rows if r[2]]
    print(f"{len(rows):>4}  {host}   ({len(live)} active)")

print("\n=== rows, by host ===")
for host, rows in sorted(by_host.items(), key=lambda kv: -len(kv[1])):
    print(f"\n-- {host}")
    for pk, name, active in rows[:40]:
        flag = "" if active else "  [INACTIVE]"
        print(f"  {pk}\t{name[:88]}{flag}")
    if len(rows) > 40:
        print(f"  ... and {len(rows) - 40} more")
