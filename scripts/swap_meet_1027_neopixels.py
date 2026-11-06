"""HOT club swap meet 2026-10-27, entered 2026-11-06: three more NeoPixel parts into F0-R1C4.

1. Adafruit NeoPixel Ring 16 (Adafruit #1463; checked live 2026-11-06: 16 x 5050 RGB,
   WS2812B or SK6812, 44.5 mm OD / 31.7 mm ID, 5 V). Bag label says "Flora NeoPixel
   Ring" (Adafruit's sticker), but the product is the 16-ring. Red + white 26 AWG leads
   already soldered on. 16 LEDs visible in the opened photo.
2. Adafruit NeoPixel Jewel, 7 LEDs, pads Data In / 5V / GND / Data Out. Was INSIDE the
   ring's bag (Scott); its own Amazon FNSKU label X001G4VXK1 "Adafruit NeoPixel
   Jewel...grated Drivers". Adafruit sells RGB (#2226) and RGBW Jewels; recorded as
   "probably RGB, unconfirmed": nothing on the label or board says which.
3. EVU WS2812B ring, bag unopened, label SKU245306-13059152. LED count 12 is Claude's
   ESTIMATE from ring size versus LED size (half the ring is under the label).

Qty 1 each (Scott). F0-R1C4 with the other rings. No NeoPixel / Jewel / 16-ring part
existed (WS2812 / NeoPixel / ring searches found only #328, #1519, #1520).

    itq push <bag photo> /tmp/hot-1106-np-bags.jpg ; itq push <opened photo> /tmp/hot-1106-np-open.jpg
    itq run scripts/swap_meet_1027_neopixels.py [--commit]
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
LOC = "LRD/Akro Bins/F0/F0-R1C4"

BAGS, OPEN = "/tmp/hot-1106-np-bags.jpg", "/tmp/hot-1106-np-open.jpg"
ITEMS = [
    dict(key="ring16", src=OPEN, crop=(0.0, 0.39, 0.60, 0.85), qty=1,
         extra=[(BAGS, "Bag as received (left), Adafruit sticker P1463; the Jewel was inside it")],
         name="Adafruit NeoPixel Ring 16 x 5050 RGB (1463), leads attached",
         keywords="Adafruit 1463 NeoPixel ring 16 WS2812B SK6812 addressable RGB LED 5V",
         desc=("Adafruit #1463: 16 x 5050 RGB addressable LEDs (WS2812B or SK6812), 44.5 mm OD / 31.7 mm ID, "
               "5 V. Red and white 26 AWG leads already soldered on. Bag sticker says \"Flora NeoPixel Ring\".")),
    dict(key="jewel", src=OPEN, crop=(0.38, 0.21, 0.64, 0.39), qty=1,
         extra=[(BAGS, "Bag as received (left): the Jewel was inside the 1463 ring's bag")],
         name="Adafruit NeoPixel Jewel, 7 x 5050 LEDs (probably RGB #2226)",
         keywords="Adafruit NeoPixel Jewel 7 LED WS2812B addressable RGB 2226 5V",
         desc=("Adafruit NeoPixel Jewel: 7 addressable 5050 LEDs on a ~23 mm disc, pads Data In / 5V / GND / "
               "Data Out. Probably the RGB version (#2226), not confirmed: RGBW Jewels exist. Amazon label "
               "X001G4VXK1.")),
    dict(key="ring12", src=BAGS, crop=(0.42, 0.26, 0.97, 0.66), qty=1, extra=[],
         name="WS2812B RGB LED Ring, 12 LEDs [ESTIMATE, bag unopened]",
         keywords="WS2812B WS2812 NeoPixel addressable RGB LED ring 12 LED round 5V EVU",
         desc=("Addressable WS2812B RGB LED ring, 5 V, in its bag (EVU label SKU245306-13059152). 12 LEDs is "
               "an ESTIMATE from ring size versus LED size; half the ring is under the label.")),
]

u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
loc = StockLocation.objects.get(pathstring=LOC)
cat = PartCategory.objects.get(pathstring="Electronics/Optoelectronics/LEDs")


def crop(src, frac, out):
    g = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    W, H = g.size
    l, t, r, b = frac
    g.crop((int(l * W), int(t * H), int(r * W), int(b * H))).save(out, quality=88)
    return out


sheet = Image.new("RGB", (1230, 420), "white")
for i, it in enumerate(ITEMS):
    it["photo"] = crop(it["src"], it["crop"], f"/tmp/crop-hot1106-{it['key']}.jpg")
    th = Image.open(it["photo"])
    th.thumbnail((400, 400))
    sheet.paste(th, (i * 410, 0))
sheet.save("/tmp/crops-np-sheet.jpg", quality=80)

held = [s.part.name for s in StockItem.objects.filter(location=loc)]
print(f"{LOC} holds now: {held}")
hits = list(Part.objects.filter(Q(name__icontains="WS2812") | Q(keywords__icontains="WS2812")
                                | Q(name__icontains="LED ring")).values_list("pk", "name"))
print("ring parts now:", hits)
for it in ITEMS:
    dup = list(Part.objects.filter(name=it["name"]))
    it["part"] = dup[0] if dup else None
    print(f"{it['name']} x{it['qty']}{' (part exists)' if dup else ''}")
if not commit:
    raise SystemExit("DRY RUN - look at /tmp/crops-np-sheet.jpg, then --commit")


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
    attach("part", part.pk, it["photo"], "Single board, swap meet 2026-10-27 (thumbnail)")
    attach("part", part.pk, it["src"], "As received, swap meet 2026-10-27")
    p = Part.objects.get(pk=part.pk)
    if not p.image:
        p.image.save(os.path.basename(it["photo"]), ContentFile(open(it["photo"], "rb").read()), save=True)
    made.append((it, part.pk, s.pk))

bad = []
for it, ppk, spk in made:
    p, s = Part.objects.get(pk=ppk), StockItem.objects.get(pk=spk)
    assert len(it["desc"]) <= 250, (it["key"], len(it["desc"]))
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
