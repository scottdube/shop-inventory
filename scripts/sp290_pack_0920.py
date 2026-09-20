"""SP290 says pack_quantity=2. That was right when #388 was 'the 2-pack' and
wrong the moment #388 became specifically the MCX antenna: receiving one pack
would book TWO MCX antennas, and only one is in the box.

Rejected: leaving it at 2 and writing a warning. The pack field is read by
receive_po.py, not by a human - a note does not stop it.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()
from company.models import SupplierPart

sp = SupplierPart.objects.get(pk=290)
print(f"before: pack={sp.pack_quantity!r} native={sp.pack_quantity_native}")

sp.pack_quantity = '1'          # .save() -> clean() -> sets native. NEVER .update()
sp.note = ('Amazon B07WFKBR4X ships TWO antennas with DIFFERENT connectors: one SMA '
           'male, one MCX male. Only the MCX one is part #388. pack_quantity set to 1 '
           'on 2026-09-20 so a receive books one MCX antenna, not two. CONSEQUENCE: the '
           'whole pack price lands on the MCX row, because the SMA twin has no part '
           'record - it has never been seen in the shop. Halve it by hand if that ever '
           'matters, or make the SMA part first.')
sp.save()

v = SupplierPart.objects.get(pk=290)
ok = v.pack_quantity_native == 1
print(f"after : pack={v.pack_quantity!r} native={v.pack_quantity_native}  {'OK' if ok else 'BAD - native did not follow'}")
print(f"note  : {len(v.note or '')} chars")
