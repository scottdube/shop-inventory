"""Queue C duplicate probe, 22:40 sweep 2026-09-26. Read-only.

One Amazon order placed 2026-09-26, 113-0944289-3125861, two lines:
  30PCS 5.5x2.1mm DC Power Jack, 2Pin Female Panel Mount   B0F7K8GVDF  (WES SHOP)
  Comimark 100Pcs Black Gold Tone PCB Test Point Pin        B07X32N4YJ
The jack is the SAME description as part created last night from PO-0182
(B08CVCJ97Q, 20-pack) -- this probe decides new part vs second supplier part.
Searches name, description, IPN and supplier SKU before anything is created.
"""
import os
import sys

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import SupplierPart  # noqa: E402
from part.models import Part  # noqa: E402

for asin in ("B0F7K8GVDF", "B07X32N4YJ", "B08CVCJ97Q"):
    print(f"\n=== {asin}")
    for sp in SupplierPart.objects.filter(SKU__iexact=asin):
        print(f"  SP #{sp.pk} supplier={sp.supplier.name} part #{sp.part.pk} "
              f"{sp.part.name} pack={sp.pack_quantity_native}")
        print(f"     notes: {(sp.part.notes or '')[:600]}")
    for p in Part.objects.filter(Q(IPN__iexact=asin) | Q(description__icontains=asin)):
        print(f"  PART #{p.pk} {p.name}")

TERMS = {
    "jack": ["DC jack", "DC power jack", "barrel jack", "5.5x2.1", "5.5 x 2.1",
             "5.5mm x 2.1", "DC socket", "DC-022", "DC-099"],
    "testpoint": ["test point", "testpoint", "test pin", "test hook",
                  "Comimark", "TP pin", "probe pin", "loop pin", "turret"],
}
for key, terms in TERMS.items():
    q = Q()
    for t in terms:
        q |= Q(name__icontains=t) | Q(description__icontains=t) | Q(keywords__icontains=t)
    print(f"\n=== {key} term scan")
    for p in Part.objects.filter(q).distinct().order_by("pk"):
        sps = ", ".join(f"{s.supplier.name}:{s.SKU}(pk{s.pk},pack{s.pack_quantity_native})"
                        for s in p.supplier_parts.all())
        print(f"  #{p.pk} active={p.active} stock={p.total_stock} "
              f"cat={p.category.pathstring if p.category else None}\n"
              f"      {p.name}\n      desc={(p.description or '')[:110]}\n      sp=[{sps}]")
