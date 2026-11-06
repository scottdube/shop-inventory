"""HOT club swap meet 2026-10-27, entered 2026-11-06: two buzzer-module types into F1-R2C7.

1. Blue MH-FMD buzzer module, "Low level trigger" (back) / 低电平触发 (front), 3-pin
   GND / I/O / VCC, black buzzer, 1k (102) resistor, SOT-23 transistor. Qty 12 (Scott).
2. Green buzzer module, 3-pin + / OUT / -, sealed buzzer ("REMOVE SEAL AFTER WASHING"),
   201 (200R) and 512 (5.1k) SMD resistors, SOT-23 transistor, a capacitor. Qty 4 (Scott).

Two parts, not one: different boards and different pin order (GND-I/O-VCC vs +-OUT--),
so wiring one by the other's pinout swaps the supply. Active vs passive is NOT known for
either (the photo cannot tell; nobody has powered one), so both say "not tested".
F1-R2C7 was empty and sits between the I2S mic/amp (R2C6) and the mini speaker (R2C8);
Scott took the proposal (gave the counts). No buzzer module existed: the only buzzer was
the bare 12 mm piezo #831 (searched buzzer / MH-FMD in name, keywords, description).

    itq push <photo1> /tmp/hot-1106-buzz1.jpg ; itq push <photo2> /tmp/hot-1106-buzz2.jpg
    itq run scripts/swap_meet_1027_buzzers.py [--commit]
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
LOC = "LRD/Akro Bins/F1/F1-R2C7"
NOT_TESTED = " Active or passive not tested: drive I/O low with VCC on; a steady tone = active."

ITEMS = [
    dict(key="mhfmd", src="/tmp/hot-1106-buzz1.jpg", crop=(0.12, 0.46, 0.90, 0.745), qty=12,
         name="Buzzer Module MH-FMD, low-level trigger, 3-pin GND/I/O/VCC (blue)",
         keywords="buzzer module MH-FMD low level trigger active passive beeper alarm Arduino ESP32 3.3V 5V",
         desc=("Blue MH-FMD buzzer board: black 12 mm buzzer driven by an SOT-23 transistor (1k base "
               "resistor), sounds when I/O is pulled LOW. 3-pin 2.54 mm header GND / I/O / VCC, one "
               "mounting hole." + NOT_TESTED)),
    dict(key="green", src="/tmp/hot-1106-buzz2.jpg", crop=(0.20, 0.26, 0.86, 0.485), qty=4,
         name="Buzzer Module, 3-pin +/OUT/-, sealed buzzer (green)",
         keywords="buzzer module beeper alarm sealed active passive 3 pin Arduino ESP32",
         desc=("Green buzzer board: sealed 12 mm buzzer (wash-seal label still on), SOT-23 transistor, "
               "200R and 5.1k SMD resistors, a capacitor. 3-pin 2.54 mm header + / OUT / - (NOT the "
               "MH-FMD order). Back has a small proto-grid area, one mounting hole." + NOT_TESTED)),
]

u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
loc = StockLocation.objects.get(pathstring=LOC)
cat = PartCategory.objects.get(pathstring="Modules/Audio")


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
sheet.save("/tmp/crops-buzzers-sheet.jpg", quality=80)

held = [s.part.name for s in StockItem.objects.filter(location=loc)]
print(f"{LOC} holds now: {held}")
hits = list(Part.objects.filter(Q(name__icontains="buzzer") | Q(keywords__icontains="buzzer")
                                | Q(name__icontains="MH-FMD")).values_list("pk", "name"))
print("buzzer parts now:", hits)
for it in ITEMS:
    dup = list(Part.objects.filter(name=it["name"]))
    it["part"] = dup[0] if dup else None
    print(f"{it['name']} x{it['qty']}{' (part exists)' if dup else ''}")
if not commit:
    raise SystemExit("DRY RUN - look at /tmp/crops-buzzers-sheet.jpg, then --commit")


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
    attach("stockitem", s.pk, it["src"], f"As received (front and back), swap meet 2026-10-27, {loc.name}")
    attach("part", part.pk, it["photo"], "Single board, swap meet 2026-10-27 (thumbnail)")
    attach("part", part.pk, it["src"], "Front and back, swap meet 2026-10-27")
    p = Part.objects.get(pk=part.pk)
    if not p.image:
        p.image.save(os.path.basename(it["photo"]), ContentFile(open(it["photo"], "rb").read()), save=True)
    made.append((it, part.pk, s.pk))

bad = []
for it, ppk, spk in made:
    p, s = Part.objects.get(pk=ppk), StockItem.objects.get(pk=spk)
    na = Attachment.objects.filter(model_type="stockitem", model_id=spk).count()
    npa = Attachment.objects.filter(model_type="part", model_id=ppk).count()
    print(f"part {p.pk} {p.name} | stock {s.pk} x{s.quantity:g} @ {s.location.pathstring} "
          f"${s.purchase_price.amount if s.purchase_price is not None else None} | img={bool(p.image)} "
          f"att stock={na} part={npa}")
    if (s.quantity != it["qty"] or s.location_id != loc.pk or p.default_location_id != loc.pk
            or p.category_id != cat.pk or s.purchase_price != Money(0, "USD") or not p.image
            or na < 1 or npa < 2 or not s.notes.exists() or not p.notes.exists()):
        bad.append(spk)
print("VERDICT:", "SUCCESS" if not bad and len(made) == len(ITEMS) else f"FAILED {bad}")
