"""pk 1177 "Flat Head Cap Screw M4 x 40mm": keywords (queue D) + a misfiled category.

Two things, both about the same part, done together because the second was found
while doing the first.

CATEGORY. 1177 sits in Tooling/Cutting Tools/End Mills. Measured tonight
(fastener_cat_0907.py) rather than assumed:
  * that category holds 13 genuine end mills and this one screw;
  * 67 of the ~99 fastener-named parts in the catalog are in Hardware, the
    single largest bucket by a wide margin;
  * pk 1178 (Hex Head Screw M8), created the SAME DAY by the same hand, went to
    Hardware.
So the destination is precedent, not taste: Hardware. Re-categorising is
explicitly permitted by the guardrails; this is not a merge and no stock moves.

KEYWORDS. Queue D's rule is to anticipate vocabulary mismatch. Six months on,
Scott searches "countersunk" or "allen screw", not "Flat Head Cap Screw" — and
InvenTree's search is a SUBSTRING match, so the abbreviation and its expansion
both have to be present ("FHCS" does not match "flat head" either way round).

NEVER overwrite a non-empty keywords field, and verify both writes by re-read:
.save() on this install has reported success and written nothing.
"""
import argparse
import os
import sys

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import SupplierPart       # noqa: E402
from part.models import Part, PartCategory    # noqa: E402

PK = 1177
DEST = "Hardware"
KW = ("flat head, flathead, FHCS, countersunk, csk, cap screw, machine screw, "
      "socket head, hex drive, allen, M4, 4mm, 40mm, metric, fastener, screw, bolt")

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

p = Part.objects.filter(pk=PK).first()
if not p:
    sys.exit(f"no part {PK}")

print(f"part {PK}: {p.name}")
print(f"   category  : {p.category.pathstring if p.category else '(none)'}")
print(f"   keywords  : {p.keywords!r}")
print(f"   stock     : {p.total_stock}")

# Provenance — if this came in on a PO, an importer put it in the wrong tree and
# that is worth knowing beyond this one row.
sps = list(SupplierPart.objects.filter(part=p))
if sps:
    for sp in sps:
        print(f"   supplier  : {sp.supplier.name if sp.supplier else '?'}:{sp.SKU}")
else:
    print("   supplier  : (none — hand-created, no importer to blame)")

dest = PartCategory.objects.filter(pathstring=DEST).first()
if not dest:
    sys.exit(f"!! destination category {DEST!r} does not exist — refusing to invent one")
print(f"destination: {dest.pathstring} (pk {dest.pk}, "
      f"{Part.objects.filter(category=dest).count()} parts)")

if len(KW) > 250:
    sys.exit(f"!! keywords {len(KW)} chars, over the 250 limit")
print(f"proposed keywords ({len(KW)} chars): {KW}")

need_cat = p.category_id != dest.pk
need_kw = not p.keywords
if not need_cat and not need_kw:
    sys.exit("=  nothing to do — already in Hardware and keywords already set")
if not need_kw:
    print("=  keywords already set — leaving them alone (may be Scott's own)")

if not a.commit:
    print(f"~  WOULD {'recategorise ' if need_cat else ''}"
          f"{'and ' if need_cat and need_kw else ''}"
          f"{'set keywords' if need_kw else ''} (DRY RUN)")
    sys.exit(0)

if need_cat:
    p.category = dest
if need_kw:
    p.keywords = KW
p.save()

fresh = Part.objects.get(pk=PK)
ok = True
if need_cat:
    if fresh.category_id == dest.pk:
        print(f"+  {PK}: category -> {fresh.category.pathstring}, VERIFIED by re-read")
    else:
        ok = False
        print(f"!! {PK}: category did not stick — still "
              f"{fresh.category.pathstring if fresh.category else '(none)'}")
if need_kw:
    if fresh.keywords == KW:
        print(f"+  {PK}: keywords written and VERIFIED by re-read")
    else:
        ok = False
        print(f"!! {PK}: keywords did not stick — row reads {fresh.keywords!r}")
if not ok:
    sys.exit("!! at least one write did not stick — see above")

active = Part.objects.filter(active=True)
empty = active.filter(Q(keywords__isnull=True) | Q(keywords=""))
print(f"active parts with empty keywords now: {empty.count()}/{active.count()} "
      f"(null-safe count)")
em = PartCategory.objects.filter(pathstring="Tooling/Cutting Tools/End Mills").first()
print(f"End Mills now holds {Part.objects.filter(category=em).count()} parts "
      f"(was 14, of which 13 were actual end mills)")
