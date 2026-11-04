"""HOT club swap meet 2026-10-27: Adafruit 2783 4.7k carbon film x25 into LRD F1-R3C5.

Not a new part: part 459 (E-Projects 25EP5144K70, 4.7k 1/4W 5%, 0 stock) is the
same carbon-film 5% resistor. It is renamed to the canonical form matching the
220R carbon film (part 1493) it now shares a drawer with, the vendor title kept in
the description. Its default_location was the bare site root "SLN", which the
location policy forbids; it becomes F1-R3C5, where these spares live.
Not merged into 618 (4.7k 1% metal film): different part. Count 25 is Scott's.

    itq run scripts/swap_meet_1027_res4k7.py [--commit]
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from PIL import Image, ImageOps  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from django.core.files.base import ContentFile  # noqa: E402
from djmoney.money import Money  # noqa: E402
from common.models import Attachment, Note  # noqa: E402
from InvenTree.status_codes import StockHistoryCode  # noqa: E402
from part.models import Part  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

commit = "--commit" in sys.argv
SRC = "HOT club swap meet 2026-10-27, $0 (Scott, entered 2026-11-04)."
NAME = "Resistor 4.7k 5% 1/4W carbon film"
loc = StockLocation.objects.get(pathstring="LRD/Akro Bins/F1/F1-R3C5")
p = Part.objects.get(pk=459)
assert "4.7k" in p.name and "5%" in p.name, p.name
assert not StockItem.objects.filter(part=p).exists()
held = [s.part.name for s in StockItem.objects.filter(location=loc)]
assert held == ["Resistor 220R 5% 1/4W carbon film"], held
im = ImageOps.exif_transpose(Image.open("/tmp/hot-1027-group2.jpg")).convert("RGB")
W, H = im.size
crop = "/tmp/crop-hot1027-res4k7.jpg"
im.crop((0, int(0.37 * H), int(0.54 * W), int(0.95 * H))).save(crop, quality=88)
print(f"459 '{p.name}' -> '{NAME}', default {p.default_location} -> {loc.pathstring}; +25 @ F1-R3C5 (shares with {held}); image blank={not p.image}")
if not commit:
    raise SystemExit("DRY RUN - add --commit")

u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
old = p.name
p.name = NAME
p.description = f"Carbon film axial resistor, 4.7k ohm, 5%, 1/4 W. orig: {old}"
p.keywords = ((p.keywords or "") + " 4k7 4.7k carbon film Adafruit 2783").strip()
p.default_location = loc
p.save()
s = StockItem(part=p, location=loc, quantity=25, purchase_price=Money(0, "USD"))
s.save()
Note.objects.create(content_object=s, title="Source", primary=True,
                    content=f"Qty 25 from Scott at put-away. Adafruit #2783 pack. {SRC}")
s.add_tracking_entry(StockHistoryCode.CREATED, u, deltas={"quantity": 25.0}, notes=f"Into F1-R3C5. {SRC}")
for mt, pk in (("stockitem", s.pk), ("part", p.pk)):
    a = Attachment(model_type=mt, model_id=pk, comment="Swap meet 2026-10-27, Adafruit 2783 bag", upload_user=u)
    a.attachment.save("hot1027-res4k7.jpg", ContentFile(open(crop, "rb").read()), save=True)
if not p.image:
    p.image.save("hot1027-res4k7.jpg", ContentFile(open(crop, "rb").read()), save=True)

p, s = Part.objects.get(pk=459), StockItem.objects.get(pk=s.pk)
print(f"part {p.pk} {p.name} def={p.default_location} img={bool(p.image)} | stock {s.pk} x{s.quantity:g} @ {s.location.pathstring} ${s.purchase_price.amount}")
ok = p.name == NAME and p.default_location_id == loc.pk and s.quantity == 25 and s.location_id == loc.pk and s.purchase_price == Money(0, "USD")
print("ALL VERIFIED" if ok else "NOT VERIFIED")
