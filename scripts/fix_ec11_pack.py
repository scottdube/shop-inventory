"""2026-09-23  Set the real pack size on the Taiss EC11 supplier part before receiving PO-0179.

pack_quantity and pack_quantity_native BOTH read 1, so fix_pack_native.py would
not touch this one - that script repairs disagreements, and these two agree.
They are simply both wrong, which is the importer default CLAUDE.md records:
the order line said "1 x <seller's title>" and nothing ever asked the question.

Verified live on the listing 2026-09-23, not inferred from the stored title:
"Package content: 5 x rotary Encoder switch + 5 x Black knob cap", $9.99.
Scott independently said 5. Two stored tokens already agreed - part 50's
description carries "pack: 5" and part 200's name carries "Taiss 5PCS" - but
a stored title is what was wrong in the first place, so the listing decided it.

Written through .save() so clean() derives native. A queryset .update() here
would change every screen and nothing that counts.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()

from company.models import SupplierPart
from order.models import PurchaseOrderLineItem

COMMIT = "--commit" in sys.argv
SKU = "B07F24TRYG"
PACK = "5"

sp = SupplierPart.objects.get(SKU=SKU)
print("supplier part %s  %s  %s" % (sp.pk, sp.supplier.name, sp.SKU))
print("  part        : %s [%s]" % (sp.part.name[:60], sp.part.pk))
print("  BEFORE      : pack_quantity=%r  native=%s" % (sp.pack_quantity, sp.pack_quantity_native))
for li in PurchaseOrderLineItem.objects.filter(part=sp):
    print("  PO line     : %s %s qty=%s price=%s -> at pack %s that is %s pieces at %s each"
          % (li.order.reference, li.order.get_status_display(), li.quantity, li.purchase_price,
             PACK, li.quantity * int(PACK),
             (li.purchase_price / int(PACK)) if li.purchase_price else "-"))

if not COMMIT:
    print("\nDRY RUN — would set pack_quantity = %r through .save()" % PACK)
    sys.exit(0)

sp.pack_quantity = PACK
sp.save()

sp.refresh_from_db()
print("  AFTER       : pack_quantity=%r  native=%s" % (sp.pack_quantity, sp.pack_quantity_native))
ok = str(sp.pack_quantity).strip() == PACK and str(sp.pack_quantity_native).startswith(PACK)
print("  VERDICT     : %s" % ("OK — both fields agree and both read %s" % PACK if ok
                              else "FAILED — text and native disagree, do NOT receive"))
sys.exit(0 if ok else 1)
