"""Which category do video signal-conversion devices actually live in?

Two candidate homes turned up in the duplicate probe: flat `Modules` (#477
BENFEI HDMI->VGA, an active converter) and `Electronics/Modules/Video` (#726
HDMI->CSI-2 bridge). This is the shadow-root problem, so count both sides
before picking rather than guessing from one precedent.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import PartCategory  # noqa: E402

for path in ("Modules", "Electronics/Modules/Video", "Electronics/Modules",
             "Electronics/Cables", "Electrical", "Electronics"):
    c = PartCategory.objects.filter(pathstring=path).first()
    if not c:
        print(f"{path:30} MISSING")
        continue
    direct = c.parts.filter(active=True).count()
    print(f"{path:30} pk={c.pk:<5} direct-active={direct}")

print("\n--- every category with 'video' or 'cable' in the path ---")
for c in PartCategory.objects.all().order_by("pathstring"):
    low = c.pathstring.lower()
    if "video" in low or "cable" in low or "adapter" in low:
        print(f"  pk={c.pk:<5} {c.pathstring:45} direct-active={c.parts.filter(active=True).count()}")

print("\n--- contents of Electronics/Modules/Video ---")
c = PartCategory.objects.filter(pathstring="Electronics/Modules/Video").first()
if c:
    for p in c.parts.filter(active=True):
        print(f"  #{p.pk:5} {p.name[:70]}")
