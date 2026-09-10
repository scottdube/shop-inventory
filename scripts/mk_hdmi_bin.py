import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()
from stock.models import StockLocation

parent = StockLocation.objects.get(pk=456)   # SLN/Storage/WS2/WS2-S4

NAME = "HDMI Cables & Adapters"
DESC = (
    "HDMI CABLES & ADAPTERS. Full-size, mini and micro HDMI cables, and the "
    "adapters between them -- plus HDMI-to-something conversions (VGA, "
    "DisplayPort, MST hubs). On WS2-S4. A HOME -- things filed here get it as "
    "default_location. The BIN is the location and the name travels WITH the "
    "bin, so moving it to another shelf is a re-parent, not a rename. "
    "Established 2026-09-10 at Scott's request.\n\n"
    "SCOPE IS THE CONNECTOR, NOT THE DEVICE. A cable or a passive adapter "
    "belongs here. A powered thing with an HDMI socket on it -- a display, a "
    "capture card, a microscope -- does not; it is filed as the device it is.\n\n"
    "NOT the only HDMI home, and that is on purpose. B0-R1C1 on the bin wall "
    "holds the micro-HDMI (Type D) to HDMI (Type A) adapter cable #1145, filed "
    "there 2026-09-09 as part of the cable row. Small single cables that earn a "
    "drawer stay on the wall; the loose miscellany and anything bulky lives "
    "here. If you are looking for an HDMI thing and it is not here, look there."
)

existing = StockLocation.objects.filter(parent=parent, name=NAME).first()
if existing:
    print(f"ALREADY EXISTS: {existing.pk} {existing.pathstring}")
else:
    loc = StockLocation.objects.create(
        parent=parent, name=NAME, description=DESC,
        structural=False,
    )
    loc.refresh_from_db()
    print(f"CREATED {loc.pk}  {loc.pathstring}")
    print(f"  desc len={len(loc.description)}")
