"""HOT club swap meet 2026-10-27, batch 1: four new parts into the LRD Akro wall.

Scott's first photo (2026-11-04) held four items, none already in InvenTree
(part_find across Maxbotix/EZ1/rangefinder, 220 ohm/220R/2780, Hyland/Mini
Power, ST7735/1.44/128x128/TFT):

- Maxbotix LV-EZ1 (Adafruit #172)  -> F1-R2C5, beside the HC-SR04s (one kind:
  ultrasonic ranging)
- 1.44in 128x128 ST7735 TFT        -> F1-R2C7 (empty)
- 220R 5% 1/4W carbon film x25     -> F1-R3C5 (empty). NOT merged into part 632:
  that is 1% metal film, a different part. Count is Scott's ("qty25").
- Hyland Elec "Mini Power" board   -> F1-R6C1 (empty). Proposed for a large F0
  drawer on a guessed width; Scott: "will fit into a small drawer".

$0, matching the 11-02 swap-meet diodes and headers: they cost nothing, and a
$0 row is the truth (blank price was considered and rejected for that reason).
Categories follow the flat taxonomy where the siblings live (HC-SR04 in
Sensors, LM2596 in Power, GC9A01 waveshare in Displays).

Photos: the group shot is cropped to one subject per row; the TFT has its own
front and back shots (the back carries the driver IC, so it goes on the part).

    itq run scripts/swap_meet_1027_batch1.py            # dry run, writes /tmp/crop-hot1027-*.jpg
    itq run scripts/swap_meet_1027_batch1.py --commit
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
from djmoney.money import Money  # noqa: E402
from common.models import Attachment, Note  # noqa: E402
from InvenTree.status_codes import StockHistoryCode  # noqa: E402
from part.models import Part, PartCategory  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

commit = "--commit" in sys.argv
SRC = "HOT club swap meet 2026-10-27, $0 (Scott, entered 2026-11-04)."
F1 = "LRD/Akro Bins/F1/"
GROUP = "/tmp/hot-1027-group.jpg"

ITEMS = [
    dict(key="maxbotix", name="Maxbotix LV-EZ1 Ultrasonic Rangefinder", cat="Sensors",
         loc=F1 + "F1-R2C5", share_ok=["HC-SR04"], qty=1, purchaseable=True,
         keywords="MaxSonar EZ1 Adafruit 172 ultrasonic sonar distance",
         desc=("MaxBotix LV-MaxSonar-EZ1 ultrasonic rangefinder, 2.5-5.5 V; analog, PWM and serial "
               "outputs. Adafruit #172 (P172), Adafruit bag dated 2016-10-13."),
         crop=(0.05, 0.37, 0.45, 0.83), photos=[]),
    dict(key="tft144", name="TFT LCD 1.44in 128x128 ST7735 SPI Module", cat="Displays",
         loc=F1 + "F1-R2C7", share_ok=[], qty=1, purchaseable=True,
         keywords="ST7735 1.44 128x128 TFT SPI NOMEN_TEC colour LCD",
         desc=("1.44in 128x128 colour TFT, ST7735 driver, 4-wire SPI (silk SCL/SDA = SCK/MOSI), "
               "pins GND VCC SCL SDA RES DC CS BL. 8-pin 2.54 mm header NOT fitted. Board silk "
               "NOMEN_TEC V2.0. Came in an ESD bag labelled 030529 / C24-05-06."),
         crop=None, photos=["/tmp/hot-1027-tft-front.jpg", "/tmp/hot-1027-tft-back.jpg"]),
    dict(key="res220cf", name="Resistor 220R 5% 1/4W carbon film", cat="Electronics/Passives/Resistors",
         loc=F1 + "F1-R3C5", share_ok=[], qty=25, purchaseable=True,
         keywords="220 ohm 220R carbon film axial Adafruit 2780",
         desc=("Carbon film axial resistor, 220 ohm, 5%, 1/4 W. Adafruit #2780 pack. NOT the 1% "
               "metal film 220R (part 632)."),
         crop=(0.42, 0.56, 0.86, 0.90), photos=[]),
    dict(key="hyland", name="Hyland Elec Mini Power Multi-Rail Supply Board", cat="Power",
         loc=F1 + "F1-R6C1", share_ok=[], qty=1, purchaseable=False,
         keywords="Hyland Mini Power multi-output supply 3.3V 5V 12V -5V -12V dual rail",
         desc=("Assembled red board, silk 'MINI POWER' / 'Hyland Elec'. Input DC 5-24 V via 5.5 mm "
               "barrel or mini-USB. Outputs on screw terminals: +3.3, +5, -5, +12, -12 V and GND. "
               "Three switching inductors, LED per rail."),
         crop=(0.49, 0.05, 0.84, 0.56), photos=[]),
]

u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
plan = []
for it in ITEMS:
    loc = StockLocation.objects.get(pathstring=it["loc"])
    cat = PartCategory.objects.get(pathstring=it["cat"])
    dup = list(Part.objects.filter(name=it["name"]))
    assert len(dup) <= 1, dup
    held = [s.part.name for s in StockItem.objects.filter(location=loc) if s.part_id != (dup[0].pk if dup else None)]
    bad = [h for h in held if not any(ok in h for ok in it["share_ok"])]
    assert not bad, f"{it['loc']} already holds {bad}"
    plan.append((it, loc, cat, dup[0] if dup else None))
    print(f"{it['name']} x{it['qty']} -> {loc.pathstring} [{cat.pathstring}]"
          f"{' (part exists, reused)' if dup else ''}{' shares with ' + str(held) if held else ''}")

# Crops (written in both modes so they can be reviewed before --commit)
g = ImageOps.exif_transpose(Image.open(GROUP)).convert("RGB")
W, H = g.size
for it in ITEMS:
    if it["crop"]:
        l, t, r, b = it["crop"]
        out = f"/tmp/crop-hot1027-{it['key']}.jpg"
        g.crop((int(l * W), int(t * H), int(r * W), int(b * H))).save(out, quality=88)
        it["photos"] = [out]
    print(f"  photos {it['key']}: {it['photos']}")
if not commit:
    raise SystemExit("DRY RUN - review /tmp/crop-hot1027-*.jpg, then --commit")


def attach(model_type, pk, path, comment):
    a = Attachment(model_type=model_type, model_id=pk, comment=comment[:250], upload_user=u)
    a.attachment.save(os.path.basename(path), ContentFile(open(path, "rb").read()), save=True)


made = []
for it, loc, cat, part in plan:
    if part is None:
        part = Part(name=it["name"], category=cat, component=True, purchaseable=it["purchaseable"],
                    description=it["desc"][:250], keywords=it["keywords"], default_location=loc)
        part.save()
        Note.objects.create(content_object=part, title="Source", primary=True, content=f"{it['desc']}\n\n{SRC}")
    # notes= in the StockItem constructor raises on 1.6 (TRAPS); Note rows instead.
    s = StockItem(part=part, location=loc, quantity=it["qty"], purchase_price=Money(0, "USD"))
    s.save()
    Note.objects.create(content_object=s, title="Source", primary=True,
                        content=f"Qty {it['qty']} from Scott at put-away. {SRC}")
    s.add_tracking_entry(StockHistoryCode.CREATED, u, deltas={"quantity": float(it["qty"])},
                         notes=f"Into {loc.name}. {SRC}")
    first = it["photos"][0]
    attach("stockitem", s.pk, first, f"As received, swap meet 2026-10-27, {loc.name}")
    for ph in it["photos"]:
        attach("part", part.pk, ph, "Swap meet 2026-10-27 unit")
    p = Part.objects.get(pk=part.pk)
    if not p.image:
        p.image.save(os.path.basename(first), ContentFile(open(first, "rb").read()), save=True)
    made.append((it, part.pk, s.pk, loc))

# Verify by re-read: .save() on this install has reported success and written nothing.
bad = []
for it, ppk, spk, loc in made:
    p, s = Part.objects.get(pk=ppk), StockItem.objects.get(pk=spk)
    na = Attachment.objects.filter(model_type="stockitem", model_id=spk).count()
    print(f"part {p.pk} {p.name} | stock {s.pk} x{s.quantity:g} @ {s.location.pathstring} "
          f"${s.purchase_price.amount if s.purchase_price is not None else None} | img={bool(p.image)} att={na}")
    if (s.quantity != it["qty"] or s.location_id != loc.pk or p.default_location_id != loc.pk
            or s.purchase_price != Money(0, "USD") or not p.image or na < 1 or not s.notes.exists()):
        bad.append(spk)
print("ALL VERIFIED" if not bad else f"NOT VERIFIED: {bad}")
