"""HOT club swap meet 2026-10-27: Adafruit 3.5in TFT breakout (#2050).

New: part_find on HX8357 / 3.5in / 480x320 / 2050 / touchscreen found only
unrelated displays. Kept boxed (Scott: "Box"), so a large F0 drawer, not F1.
Qty 1 as proposed; the photo shows one board. $0 like the rest of the swap meet.

    itq run scripts/swap_meet_1027_tft35.py [--commit]
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
F1 = "LRD/Akro Bins/F1/"
ITEMS = [
    dict(key="tft35", name="TFT LCD 3.5in 480x320 HX8357D Touchscreen Breakout", cat="Displays",
         loc="LRD/Akro Bins/F0/F0-R1C3", share_ok=[], qty=1, purchaseable=True,
         keywords="Adafruit 2050 HX8357D 3.5 480x320 TFT resistive touchscreen microSD SPI 8080 parallel",
         desc=("Adafruit 3.5in TFT breakout #2050 (P2050, RevB): 480x320, HX8357D driver, 4-wire resistive "
               "touch, microSD slot. SPI (close IM2 jumper) or 8-bit 8080 parallel; power and logic 3.3-5V. "
               "Kept in its Adafruit box, so it lives in a large F0 drawer."),
         src="/tmp/hot-1027-tft35.jpg", crop=None),
]
u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
plan = []
for it in ITEMS:
    loc = StockLocation.objects.get(pathstring=it["loc"])
    cat = PartCategory.objects.get(pathstring=it["cat"])
    assert not Part.objects.filter(name=it["name"]).exists(), it["name"]
    held = [s.part.name for s in StockItem.objects.filter(location=loc)]
    bad = [h for h in held if not any(ok in h for ok in it["share_ok"])]
    assert not bad, f"{it['loc']} holds {bad}"
    src = ImageOps.exif_transpose(Image.open(it["src"])).convert("RGB")
    W, H = src.size
    l, t, r, b = it["crop"] or (0, 0, 1, 1)
    it["photo"] = f"/tmp/crop-hot1027-{it['key']}.jpg"
    src.crop((int(l * W), int(t * H), int(r * W), int(b * H))).save(it["photo"], quality=88)
    plan.append((it, loc, cat))
    print(f"{it['name']} x{it['qty']} -> {loc.pathstring} [{cat.pathstring}]{' shares ' + str(held) if held else ''}")
if not commit:
    raise SystemExit("DRY RUN - add --commit")

bad = []
for it, loc, cat in plan:
    p = Part(name=it["name"], category=cat, component=True, purchaseable=it["purchaseable"],
             description=it["desc"][:250], keywords=it["keywords"], default_location=loc)
    p.save()
    Note.objects.create(content_object=p, title="Source", primary=True, content=f"{it['desc']}\n\n{SRC}")
    s = StockItem(part=p, location=loc, quantity=it["qty"], purchase_price=Money(0, "USD"))
    s.save()
    Note.objects.create(content_object=s, title="Source", primary=True, content=f"Qty {it['qty']} from Scott at put-away. {SRC}")
    s.add_tracking_entry(StockHistoryCode.CREATED, u, deltas={"quantity": float(it["qty"])}, notes=f"Into {loc.name}. {SRC}")
    data = open(it["photo"], "rb").read()
    for mt, pk in (("stockitem", s.pk), ("part", p.pk)):
        a = Attachment(model_type=mt, model_id=pk, comment=f"Swap meet 2026-10-27, {loc.name}", upload_user=u)
        a.attachment.save(f"hot1027-{it['key']}.jpg", ContentFile(data), save=True)
    p.image.save(f"hot1027-{it['key']}.jpg", ContentFile(data), save=True)
    p, s = Part.objects.get(pk=p.pk), StockItem.objects.get(pk=s.pk)
    print(f"part {p.pk} {p.name} img={bool(p.image)} | stock {s.pk} x{s.quantity:g} @ {s.location.pathstring} ${s.purchase_price.amount}")
    if s.quantity != it["qty"] or s.location_id != loc.pk or p.default_location_id != loc.pk or not p.image \
            or s.purchase_price != Money(0, "USD"):
        bad.append(s.pk)
print("ALL VERIFIED" if not bad else f"NOT VERIFIED: {bad}")
