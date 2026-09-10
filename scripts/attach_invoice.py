"""Attach the JLCPCB invoice to PO-0164, and re-allocate a board to BO-0016."""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.core.files import File
from common.models import Attachment
from order.models import PurchaseOrder
from build.models import Build, BuildLine, BuildItem
from stock.models import StockItem
from part.models import Part

po = PurchaseOrder.objects.get(reference="PO-0164")
src = "/tmp/jlc_invoice_2026-09-02.pdf"
comment = "JLCPCB invoice 2583209A2026082923398500 - 10 @ $0.97 + $8.90 shipping = $18.60 ($1.86/board landed)"

if Attachment.objects.filter(model_type="purchaseorder", model_id=po.pk).exists():
    print("   attachment already present - not duplicating")
else:
    a = Attachment(model_type="purchaseorder", model_id=po.pk, comment=comment)
    with open(src, "rb") as fh:
        a.attachment.save("jlc_invoice_2026-09-02.pdf", File(fh), save=False)
    a.save()
    print("   attached")

b = Build.objects.get(reference="BO-0016")
pcb = Part.objects.get(name="HoT Info Orbs PCB v1.1")
line = BuildLine.objects.filter(build=b, bom_item__sub_part=pcb).first()
if line and not BuildItem.objects.filter(build_line=line).exists():
    si = StockItem.objects.filter(part=pcb).order_by("pk").first()
    BuildItem.objects.create(build_line=line, stock_item=si, quantity=1)
    print(f"   re-allocated 1 PCB from stock {si.pk}")

print("\n   verify (re-read):")
for a in Attachment.objects.filter(model_type="purchaseorder", model_id=po.pk):
    size = a.attachment.size if a.attachment else 0
    print(f"      {a.attachment.name}  {size} bytes")
for l in BuildLine.objects.filter(build=b):
    al = sum(i.quantity for i in BuildItem.objects.filter(build_line=l))
    need = l.bom_item.quantity
    flag = "" if al >= need else f"   << short {need-al:g}"
    print(f"      {need:g}x {l.bom_item.sub_part.name[:40]:40} allocated={al:g}{flag}")
