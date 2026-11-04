"""HOT club swap meet 2026-10-27: 3 V 1-channel relay board x4 into F1-R7C4.

Black narrow board, Songle SRD-03VDC-SL-C (3 V coil, 10 A), optocoupler, green
3-way screw terminals at each end. Next drawer in the relay row (F1-R7, one
drawer per type). No 3 V relay part existed (searched SRD-03 / 03VDC / 3V and
3.3V relay). Count is Scott's ("qty 4"). Single-board crop is the thumbnail;
the photo shows only this one board, so there is no group shot to keep.

    itq push <photo> /tmp/hot-1027-relay3v.jpg
    itq run scripts/swap_meet_1027_relay3v.py [--commit]
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
LOC = "LRD/Akro Bins/F1/F1-R7C4"
GROUP2 = "/tmp/hot-1027-relay3v.jpg"

# (part pk, source photo, crop fraction l,t,r,b)
THUMBS = []

ITEMS = [
    dict(key="relay3v", name="Relay Module 1-Channel 3V, opto-isolated, Songle SRD-03VDC-SL-C",
         qty=4, crop=(0.27, 0.15, 0.56, 0.80),
         keywords="relay module 1 channel 3V 3.3V SRD-03VDC-SL-C Songle optocoupler ESP32",
         desc=("Narrow black 1-channel relay board, Songle SRD-03VDC-SL-C relay: 3 V coil, 10 A 250 VAC / "
               "30 VDC. Optocoupler input, jumper header(s), LED. Green 3-way screw terminals at each "
               "end (load NO/COM/NC; input). Suits 3.3 V logic (ESP32) without a 5 V rail.")),
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
            or s.purchase_price != Money(0, "USD") or not p.image or na < 1 or not s.notes.exists()):
        bad.append(spk)
print("ALL VERIFIED" if not bad else f"NOT VERIFIED: {bad}")
