"""HOT club swap meet 2026-10-27, entered 2026-11-06: SFM-27-W panel buzzer x3.

Label: SFM-27-W, 电子蜂鸣器 (electronic buzzer), 连续声 (continuous tone), DC3-24V.
So ACTIVE is label-stated, not bench-tested. Panel mount, two-ear flange, red/black
leads; one of the photographed units has red insulated female quick-disconnects
crimped on, the other bare leads. Same part either way: one row, terminals in the note.
Qty 3 (Scott). Into F1-R2C7 with the two buzzer modules, all buzzers in one small
drawer. First proposed the larger F0-R1C4 on a guess that the flange was too wide
for an F1 (10164) drawer; Scott: they are about 30 mm across and three fit.
No SFM part existed (searched SFM / buzzer: only #831, #1516, #1517).

    itq push <photo> /tmp/hot-1106-sfm27.jpg
    itq run scripts/swap_meet_1027_sfm27.py [--commit]
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
LOC = "LRD/Akro Bins/F1/F1-R2C7"  # moved to F1-R3C8 by move_sfm27_1106.py: R2C7 was full

ITEMS = [
    dict(key="sfm27", src="/tmp/hot-1106-sfm27.jpg", crop=(0.21, 0.59, 0.69, 0.85), qty=3,
         name="Buzzer SFM-27-W, active piezo, continuous tone, DC 3-24 V, panel mount, wire leads",
         keywords="buzzer SFM-27 SFM-27-W active piezo alarm beeper continuous 3-24V 12V 24V panel mount",
         desc=("Active piezo buzzer, continuous tone, DC 3-24 V (label: SFM-27-W 电子蜂鸣器 连续声). About 30 mm "
               "body, two-ear panel flange, red (+) / black (-) leads. One unit has red insulated female "
               "quick-disconnects crimped on.")),
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


sheet = Image.new("RGB", (420, 420), "white")
for i, it in enumerate(ITEMS):
    it["photo"] = crop(it["src"], it["crop"], f"/tmp/crop-hot1106-{it['key']}.jpg")
    th = Image.open(it["photo"])
    th.thumbnail((400, 400))
    sheet.paste(th, (i * 410, 0))
sheet.save("/tmp/crops-sfm27-sheet.jpg", quality=80)

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
    raise SystemExit("DRY RUN - look at /tmp/crops-sfm27-sheet.jpg, then --commit")


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
    attach("stockitem", s.pk, it["src"], f"As received (both sides), swap meet 2026-10-27, {loc.name}")
    attach("part", part.pk, it["photo"], "Single board, swap meet 2026-10-27 (thumbnail)")
    attach("part", part.pk, it["src"], "Both sides, swap meet 2026-10-27")
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
