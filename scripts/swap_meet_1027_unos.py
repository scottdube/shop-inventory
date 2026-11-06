"""HOT club swap meet 2026-10-27, entered 2026-11-06: two UNO boards into F0-R2C1.

1. Cytron Maker UNO Rev1.1 (purple, board print "MAKER UNO Rev1.1"): ATmega328P (TQFP),
   CH340 USB on micro-USB, LED on every digital pin, piezo buzzer, user button. One in
   its box with the pin-label sticker. NEW part, qty 2 (Scott).
2. Blue UNO R3 clone, SMD ATmega328P, CH340 (12 MHz crystal), USB-B, DC jack, 3x4
   SCL/SDA/5V/3.3V header block. NOT a new part: it matches #730's photo board for
   board (same 3x4 block, same layout), so it is a second stock row on #730 at LRD.
   #730's default_location stays at SLN B3-R6C2, where its 3 bought boards live.

F0-R2C1 = the LRD UNO drawer, as SLN keeps its UNOs together in B3-R6C2 (Scott: "Okay").
Maker UNO filed beside #730 in Electronics/Modules/Dev Boards.

    itq push <photo> /tmp/hot-1106-unos.jpg
    itq run scripts/swap_meet_1027_unos.py [--commit]
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from PIL import Image, ImageOps  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from django.core.files.base import ContentFile  # noqa: E402
from django.db.models import Q  # noqa: E402
from djmoney.money import Money  # noqa: E402
from common.models import Attachment, Note  # noqa: E402
from InvenTree.status_codes import StockHistoryCode  # noqa: E402
from part.models import Part, PartCategory  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

commit = "--commit" in sys.argv
SRC = "HOT club swap meet 2026-10-27, $0 (Scott, entered 2026-11-06)."
LOC = "LRD/Akro Bins/F0/F0-R2C1"

PHOTO = "/tmp/hot-1106-unos.jpg"
ITEMS = [
    dict(key="makeruno", src=PHOTO, crop=(0.23, 0.29, 0.69, 0.58), qty=2, extra=[],
         name="Cytron Maker UNO Rev1.1 (ATmega328P, CH340, micro-USB)",
         keywords="Cytron Maker UNO Arduino UNO compatible ATmega328P CH340 micro USB buzzer LEDs education",
         desc=("Cytron Maker UNO Rev1.1, Arduino UNO compatible: ATmega328P, CH340 USB on micro-USB, an LED "
               "on every digital pin, piezo buzzer, user button. One unit in its box with the pin-label "
               "sticker.")),
    dict(key="uno730", src=PHOTO, crop=(0.13, 0.63, 0.72, 0.96), qty=1, extra=[], existing=730),
]

u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
loc = StockLocation.objects.get(pathstring=LOC)
cat = PartCategory.objects.get(pathstring="Electronics/Modules/Dev Boards")


def crop(src, frac, out):
    g = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    W, H = g.size
    l, t, r, b = frac
    g.crop((int(l * W), int(t * H), int(r * W), int(b * H))).save(out, quality=88)
    return out


sheet = Image.new("RGB", (820, 420), "white")
for i, it in enumerate(ITEMS):
    it["photo"] = crop(it["src"], it["crop"], f"/tmp/crop-hot1106-{it['key']}.jpg")
    th = Image.open(it["photo"])
    th.thumbnail((400, 400))
    sheet.paste(th, (i * 410, 0))
sheet.save("/tmp/crops-unos-sheet.jpg", quality=80)

held = [s.part.name for s in StockItem.objects.filter(location=loc)]
print(f"{LOC} holds now: {held}")
hits = list(Part.objects.filter(Q(name__icontains="UNO") | Q(keywords__icontains="UNO")
                                | Q(name__icontains="328")).values_list("pk", "name"))
print("UNO/328 parts now:", hits)
for it in ITEMS:
    if it.get("existing"):
        it["part"] = Part.objects.get(pk=it["existing"])
        assert it["part"].active and it["part"].name.startswith("UNO R3 Development Board"), it["part"].name
        it["name"] = it["part"].name
        print(f"#{it['existing']} {it['name']} x{it['qty']} (existing part, new LRD row)")
        continue
    dup = list(Part.objects.filter(name=it["name"]))
    it["part"] = dup[0] if dup else None
    print(f"{it['name']} x{it['qty']}{' (part exists)' if dup else ''}")
if not commit:
    raise SystemExit("DRY RUN - look at /tmp/crops-unos-sheet.jpg, then --commit")


def attach(model_type, pk, path, comment):
    data = open(path, "rb").read()
    if Attachment.objects.filter(model_type=model_type, model_id=pk, file_size=len(data)).exists():
        return
    a = Attachment(model_type=model_type, model_id=pk, comment=comment[:250], upload_user=u)
    a.attachment.save(os.path.basename(path), ContentFile(data), save=True)


made = []
for it in ITEMS:
    part = it["part"]
    if part is None:
        part = Part(name=it["name"], category=cat, component=True, purchaseable=True,
                    description=it["desc"][:250], keywords=it["keywords"], default_location=loc)
        part.save()
        Note.objects.create(content_object=part, title="Source", primary=True, content=f"{it['desc']}\n\n{SRC}")
    s = StockItem.objects.filter(part=part, location=loc).first()
    if s is None:
        s = StockItem(part=part, location=loc, quantity=it["qty"], purchase_price=Money(0, "USD"))
        s.save()
        Note.objects.create(content_object=s, title="Source", primary=True,
                            content=f"Qty {it['qty']} from Scott at put-away. {SRC}")
        s.add_tracking_entry(StockHistoryCode.CREATED, u, deltas={"quantity": float(it["qty"])},
                             notes=f"Into {loc.name}. {SRC}")
    attach("stockitem", s.pk, it["src"], f"As received, swap meet 2026-10-27, {loc.name}")
    for path, comment in it["extra"]:
        attach("stockitem", s.pk, path, comment)
    attach("part", part.pk, it["photo"], "Single board, swap meet 2026-10-27" + ("" if it.get("existing") else " (thumbnail)"))
    attach("part", part.pk, it["src"], "As received, swap meet 2026-10-27")
    p = Part.objects.get(pk=part.pk)
    if not p.image:
        p.image.save(os.path.basename(it["photo"]), ContentFile(open(it["photo"], "rb").read()), save=True)
    made.append((it, part.pk, s.pk))

bad = []
for it, ppk, spk in made:
    p, s = Part.objects.get(pk=ppk), StockItem.objects.get(pk=spk)
    assert it.get("existing") or len(it["desc"]) <= 250, it["key"]
    na = Attachment.objects.filter(model_type="stockitem", model_id=spk).count()
    npa = Attachment.objects.filter(model_type="part", model_id=ppk).count()
    print(f"part {p.pk} {p.name} | stock {s.pk} x{s.quantity:g} @ {s.location.pathstring} "
          f"${s.purchase_price.amount if s.purchase_price is not None else None} | img={bool(p.image)} "
          f"att stock={na} part={npa}")
    if (s.quantity != it["qty"] or s.location_id != loc.pk or (not it.get("existing") and p.default_location_id != loc.pk)
            or (not it.get("existing") and p.category_id != cat.pk) or s.purchase_price != Money(0, "USD") or not p.image
            or na < 1 or npa < 2 or not s.notes.exists() or not p.notes.exists()):
        bad.append(spk)
print("VERDICT:", "SUCCESS" if not bad and len(made) == len(ITEMS) else f"FAILED {bad}")
