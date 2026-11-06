"""HOT club swap meet 2026-10-27, entered 2026-11-06: Weewooday 12-position screw
terminal strips into F0-R2C2.

Label (Amazon FNSKU X002PNLVT5): "Terminal Block White Screw Terminal Connector Dual Row
Electric Barrier Block 12-Position Terminal Strip, 10 Amp 380 V (10)". These are white
polyethylene connector strips ("choc block"), cut-to-length, not the 600V 15A barrier
blocks (#1204-#1210) or PCB screw terminals already on file, so a NEW part.

ONE part, stock counted in STRIPS of any length: 11 = 9 full 12-position + one 6 + one 3
(Scott). Rejected a part per length: these are cut from 12-way strips as needed, so a
6-pin is not a different item, only a shorter piece of the same one; the breakdown lives
in the stock note. Rejected counting positions (117): nobody asks for "positions".
Drawer F0-R2C2 (large drawer; a full strip is ~13 cm): proposed, Scott answered with counts.

    itq push <strips> /tmp/hot-1106-tstrip.jpg ; itq push <label> /tmp/hot-1106-tstrip-label.jpg
    itq run scripts/swap_meet_1027_tstrips.py [--commit]
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
LOC = "LRD/Akro Bins/F0/F0-R2C2"
LABEL = "/tmp/hot-1106-tstrip-label.jpg"

ITEMS = [
    dict(key="tstrip", src="/tmp/hot-1106-tstrip.jpg", crop=(0.155, 0.225, 0.765, 0.375), qty=11,
         name="Terminal Strip, 12-position screw connector, 10A 380V, white (Weewooday)",
         keywords="terminal strip connector strip choc block chocblock screw terminal 12 position 10A 380V cut to length Weewooday X002PNLVT5",
         desc=("White polyethylene screw connector strip (choc block), 12-position, cut to length, rated "
               "10 A 380 V (pack label). Stock counts STRIPS of any length: see the stock note for the "
               "12/6/3 breakdown. Weewooday, Amazon FNSKU X002PNLVT5."),
         stock_note="Qty 11 strips from Scott at put-away: 9 full 12-position, 1 cut to 6-position, 1 cut to 3-position."),
]

u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
loc = StockLocation.objects.get(pathstring=LOC)
cat = PartCategory.objects.get(pathstring="Connectors")


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
sheet.save("/tmp/crops-tstrip-sheet.jpg", quality=80)

held = [s.part.name for s in StockItem.objects.filter(location=loc)]
print(f"{LOC} holds now: {held}")
hits = list(Part.objects.filter(Q(name__icontains="terminal strip") | Q(keywords__icontains="choc")
                                | Q(name__icontains="Weewooday")).values_list("pk", "name"))
print("terminal strip parts now:", hits)
for it in ITEMS:
    dup = list(Part.objects.filter(name=it["name"]))
    it["part"] = dup[0] if dup else None
    print(f"{it['name']} x{it['qty']}{' (part exists)' if dup else ''}")
if not commit:
    raise SystemExit("DRY RUN - look at /tmp/crops-tstrip-sheet.jpg, then --commit")


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
                            content=f"{it['stock_note']} {SRC}")
        s.add_tracking_entry(StockHistoryCode.CREATED, u, deltas={"quantity": float(it["qty"])},
                             notes=f"Into {loc.name}. {SRC}")
    attach("stockitem", s.pk, it["src"], f"As received: 9 x 12-pos, 1 x 6-pos, 1 x 3-pos, swap meet 2026-10-27, {loc.name}")
    attach("stockitem", s.pk, LABEL, "Pack label (Weewooday, FNSKU X002PNLVT5, 10 A 380 V, pack of 10)")
    attach("part", part.pk, it["photo"], "One 12-position strip, swap meet 2026-10-27 (thumbnail)")
    attach("part", part.pk, it["src"], "As received, swap meet 2026-10-27")
    attach("part", part.pk, LABEL, "Pack label: Weewooday 12-position 10 A 380 V, FNSKU X002PNLVT5")
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
            or na < 2 or npa < 3 or not s.notes.exists() or not p.notes.exists()):
        bad.append(spk)
print("VERDICT:", "SUCCESS" if not bad and len(made) == len(ITEMS) else f"FAILED {bad}")
