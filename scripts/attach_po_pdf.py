"""Attach a document (vendor invoice PDF) to a purchase order. Idempotent by file name.

Generalises attach_invoice.py, which was hard-wired to PO-0164. Written
2026-10-05 for the Stafford Special Tools invoice, which exists only as the
PDF Scott handed over: the PO cites it, so the PO should carry it.

    itq push <local.pdf> /tmp/<name>.pdf
    itq run scripts/attach_po_pdf.py PO-0221 /tmp/<name>.pdf "comment" [--commit]
"""
import argparse
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.core.files import File  # noqa: E402

from common.models import Attachment  # noqa: E402
from order.models import PurchaseOrder  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("po")
ap.add_argument("src")
ap.add_argument("comment")
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

po = PurchaseOrder.objects.get(reference=a.po)
name = os.path.basename(a.src)
have = [x for x in Attachment.objects.filter(model_type="purchaseorder", model_id=po.pk)
        if x.attachment and os.path.basename(x.attachment.name).startswith(os.path.splitext(name)[0])]
print(f"{po.reference} ({po.supplier.name} {po.supplier_reference}) <- {name} "
      f"{os.path.getsize(a.src)} bytes")
if have:
    print(f"   SKIP: already attached as {have[0].attachment.name}")
elif a.commit:
    att = Attachment(model_type="purchaseorder", model_id=po.pk, comment=a.comment[:250])
    with open(a.src, "rb") as fh:
        att.attachment.save(name, File(fh), save=False)
    att.save()
    att.refresh_from_db()
    assert att.pk and att.attachment.size == os.path.getsize(a.src)
    print(f"   attached: {att.attachment.name}")
print("COMMITTED" if a.commit else "DRY RUN - add --commit")
