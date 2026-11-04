"""HOT club swap meet 2026-10-27: a bag of 50 V electrolytics, counts from Scott.

- 10uF 50V x5 -> merge into the ALLECIN kit's 10uF 50V compartment (part 1421, stock 1140)
- 1uF 50V x1  -> merge into the kit's 1uF 50V compartment (part 693, stock 1135)
- 100uF 50V x5 -> NEW part, F1-R3C6. The ALLECIN kit stops at 25 V for 100uF and
  no 100uF 50V part existed in any size.
Scott chose the kit for the first two ("the caps might go with the kits"), and
said ok to the split. Merged, not a second row, because one row per part per
location. Body size was NOT measured: the kit parts are 5x11 and the swap-meet
caps are taken as the same; the 100uF 50V part name carries no size for that reason.

    itq run scripts/swap_meet_1027_caps.py [--commit]
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
from part.models import Part, PartCategory  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

commit = "--commit" in sys.argv
SRC = "HOT club swap meet 2026-10-27, $0 (Scott, entered 2026-11-04)."
KIT = "LRD/Countertop Wall/Cab2/Cab2-D3/Kit - ALLECIN 24-Value Electrolytic"
NEW = "Capacitor Electrolytic 100uF 50V"
f1 = StockLocation.objects.get(pathstring="LRD/Akro Bins/F1/F1-R3C6")
merges = [(1140, 1421, 5, "10uF 50V"), (1135, 693, 1, "1uF 50V")]
for spk, ppk, add, val in merges:
    s = StockItem.objects.get(pk=spk)
    assert s.part_id == ppk and s.location.pathstring == KIT and val in s.part.name, (spk, s.part.name)
    print(f"stock {spk} {s.part.name}: {s.quantity:g} -> {s.quantity + add:g}")
assert not StockItem.objects.filter(location=f1).exists()
assert not Part.objects.filter(name__icontains="100uF 50V").exists()
print(f"new part '{NEW}' x5 @ {f1.pathstring}")
im = ImageOps.exif_transpose(Image.open("/tmp/hot-1027-group2.jpg")).convert("RGB")
W, H = im.size
crop = "/tmp/crop-hot1027-caps.jpg"
im.crop((int(0.56 * W), int(0.43 * H), W, int(0.81 * H))).save(crop, quality=88)
if not commit:
    raise SystemExit("DRY RUN - add --commit")

u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
for spk, ppk, add, val in merges:
    s = StockItem.objects.get(pk=spk)
    s.add_stock(add, u, notes=f"+{add} loose {val} from the swap meet, into the kit compartment. {SRC}")
cat = Part.objects.get(pk=1421).category
p = Part(name=NEW, category=cat, component=True, purchaseable=True, default_location=f1,
         keywords="100uF 100 uF 50V electrolytic radial",
         description="Aluminium electrolytic capacitor, 100uF 50V, radial. Body size not measured.")
p.save()
Note.objects.create(content_object=p, title="Source", primary=True, content=(
    f"{SRC} No ALLECIN compartment for this value (the kit stops at 25 V for 100uF), so it got its own drawer."))
s = StockItem(part=p, location=f1, quantity=5, purchase_price=Money(0, "USD"))
s.save()
Note.objects.create(content_object=s, title="Source", primary=True, content=f"Qty 5 from Scott at put-away. {SRC}")
s.add_tracking_entry(StockHistoryCode.CREATED, u, deltas={"quantity": 5.0}, notes=f"Into F1-R3C6. {SRC}")
data = open(crop, "rb").read()
for mt, pk in (("stockitem", s.pk), ("part", p.pk)):
    a = Attachment(model_type=mt, model_id=pk, comment="Swap meet 2026-10-27 cap bag (10uF, 100uF, 1uF 50V mixed)", upload_user=u)
    a.attachment.save("hot1027-caps.jpg", ContentFile(data), save=True)
p.image.save("hot1027-caps.jpg", ContentFile(data), save=True)

bad = []
for spk, ppk, add, val in merges:
    r = StockItem.objects.get(pk=spk)
    print(f"stock {spk} {r.part.name} x{r.quantity:g} @ kit")
for spk, want in ((1140, 15), (1135, 11)):
    if StockItem.objects.get(pk=spk).quantity != want:
        bad.append(spk)
p, s = Part.objects.get(pk=p.pk), StockItem.objects.get(pk=s.pk)
print(f"part {p.pk} {p.name} img={bool(p.image)} | stock {s.pk} x{s.quantity:g} @ {s.location.pathstring} ${s.purchase_price.amount}")
if s.quantity != 5 or s.location_id != f1.pk or p.default_location_id != f1.pk or not p.image:
    bad.append(s.pk)
print("ALL VERIFIED" if not bad else f"NOT VERIFIED: {bad}")
