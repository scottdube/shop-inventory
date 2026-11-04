"""HOT club swap meet 2026-10-27: relays, second photo set, plus single-board thumbnails.

1. Parts 1503/1504 (swap_meet_1027_relays.py) got the whole group photo as the
   part image because each photo showed only one part. Scott, 2026-11-04: "I like
   the single board as a thumbnail" - so one board is cropped out and becomes the
   part image. The whole photo stays attached (part + stock), nothing is lost.
2. Two new boards, one of each (Scott: "both of these boards ... go into 7C3"):
   - 30 A 1-channel 5 V board, Songle SLA-05VDC-SL-C. Not part 426 (KNACRO):
     that is a 12 V coil, 2-channel board.
   - FC-19 2-channel relay controller (STC 8-pin MCU, two buttons). Described
     only from what is printed on it; its function was not confirmed.
   Both share F1-R7C3, the relay row (F1-R7, one drawer per type where possible).

    itq push <photo> /tmp/hot-1027-relay-30a-fc19.jpg
    itq run scripts/swap_meet_1027_relays2.py            # dry run: writes crops + /tmp/crops-relays-sheet.jpg
    itq run scripts/swap_meet_1027_relays2.py --commit
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
LOC = "LRD/Akro Bins/F1/F1-R7C3"
GROUP2 = "/tmp/hot-1027-relay-30a-fc19.jpg"

# (part pk, source photo, crop fraction l,t,r,b)
THUMBS = [
    (1503, "/tmp/hot-1027-relay1ch.jpg", (0.23, 0.0, 0.76, 0.26)),
    (1504, "/tmp/hot-1027-relay2ch.jpg", (0.27, 0.07, 0.71, 0.385)),
]

ITEMS = [
    dict(key="relay30a", name="Relay Module 1-Channel 5V 30A, opto-isolated, Songle SLA-05VDC-SL-C",
         qty=1, crop=(0.03, 0.06, 0.77, 0.42),
         keywords="relay module 30A high current 1 channel 5V SLA-05VDC-SL-C Songle optocoupler",
         desc=("Green 1-channel relay board, Songle SLA-05VDC-SL-C relay: 5 V coil, 30 A 250 VAC / "
               "30 VDC, 1 HP 120 VAC. Load on a covered 3-way barrier terminal; 3-way input terminal, "
               "optocoupler, trigger-select jumper, LED. Silk 'YYG-' (rest cut off in the photo). "
               "NOT part 426 (KNACRO 12 V 2-channel 30 A).")),
    dict(key="fc19", name="Relay Board FC-19 2-Channel 5V, STC MCU, two buttons",
         qty=1, crop=(0.10, 0.50, 0.75, 0.91),
         keywords="FC-19 relay board 2 channel STC microcontroller button latching self-lock SRD-05VDC-SL-C",
         desc=("Blue 2-channel relay board, silk FC-19. Two Songle SRD-05VDC-SL-C relays (10 A), 8-pin "
               "STC microcontroller, two tactile buttons, 3-pin JST-style input header, 78M05 regulator, "
               "2-way power terminal, three LEDs (two channel, one power). Likely a button-controlled "
               "latching/self-lock board - function NOT confirmed; input voltage not marked.")),
]

u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
loc = StockLocation.objects.get(pathstring=LOC)
cat = PartCategory.objects.get(pathstring="Relays")


def crop(src, frac, out):
    g = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    W, H = g.size
    l, t, r, b = frac
    g.crop((int(l * W), int(t * H), int(r * W), int(b * H))).save(out, quality=88)
    return out


crops = []
for pk, src, frac in THUMBS:
    crops.append(crop(src, frac, f"/tmp/crop-hot1027-thumb{pk}.jpg"))
for it in ITEMS:
    it["photo"] = crop(GROUP2, it["crop"], f"/tmp/crop-hot1027-{it['key']}.jpg")
    crops.append(it["photo"])

sheet = Image.new("RGB", (820, 820), "white")
for i, p in enumerate(crops):
    th = Image.open(p)
    th.thumbnail((400, 400))
    sheet.paste(th, ((i % 2) * 410, (i // 2) * 410))
sheet.save("/tmp/crops-relays-sheet.jpg", quality=80)

held = [s.part.name for s in StockItem.objects.filter(location=loc)]
print(f"{LOC} holds now: {held}")
for it in ITEMS:
    dup = list(Part.objects.filter(name=it["name"]))
    it["part"] = dup[0] if dup else None
    print(f"{it['name']} x{it['qty']}{' (part exists)' if dup else ''}")
if not commit:
    raise SystemExit("DRY RUN - look at /tmp/crops-relays-sheet.jpg, then --commit")


def attach(model_type, pk, path, comment):
    data = open(path, "rb").read()
    if Attachment.objects.filter(model_type=model_type, model_id=pk, file_size=len(data)).exists():
        return
    a = Attachment(model_type=model_type, model_id=pk, comment=comment[:250], upload_user=u)
    a.attachment.save(os.path.basename(path), ContentFile(data), save=True)


# 1. thumbnails: replace the group image (it stays attached) with the single-board crop
for (pk, src, frac), path in zip(THUMBS, crops):
    p = Part.objects.get(pk=pk)
    attach("part", pk, path, "Single board, swap meet 2026-10-27 (thumbnail)")
    if "thumb" not in (p.image.name or ""):
        p.image.save(os.path.basename(path), ContentFile(open(path, "rb").read()), save=True)

# 2. new parts, idempotent: skip any whose stock row is already in the drawer
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
    attach("stockitem", s.pk, it["photo"], f"As received, swap meet 2026-10-27, {loc.name}")
    attach("stockitem", s.pk, GROUP2, "Group photo with the other board from the same lot")
    attach("part", part.pk, it["photo"], "Swap meet 2026-10-27 unit")
    p = Part.objects.get(pk=part.pk)
    if not p.image:
        p.image.save(os.path.basename(it["photo"]), ContentFile(open(it["photo"], "rb").read()), save=True)
    made.append((it, part.pk, s.pk))

# Verify by re-read
bad = []
for pk, _, _ in THUMBS:
    p = Part.objects.get(pk=pk)
    na = Attachment.objects.filter(model_type="part", model_id=pk).count()
    print(f"part {pk} image={p.image.name} part-attachments={na}")
    if "thumb" not in p.image.name or na < 2:
        bad.append(f"thumb{pk}")
for it, ppk, spk in made:
    p, s = Part.objects.get(pk=ppk), StockItem.objects.get(pk=spk)
    na = Attachment.objects.filter(model_type="stockitem", model_id=spk).count()
    print(f"part {p.pk} {p.name} | stock {s.pk} x{s.quantity:g} @ {s.location.pathstring} "
          f"${s.purchase_price.amount if s.purchase_price is not None else None} | img={bool(p.image)} att={na}")
    if (s.quantity != it["qty"] or s.location_id != loc.pk or p.default_location_id != loc.pk
            or s.purchase_price != Money(0, "USD") or not p.image or na < 2 or not s.notes.exists()):
        bad.append(spk)
print("ALL VERIFIED" if not bad else f"NOT VERIFIED: {bad}")
