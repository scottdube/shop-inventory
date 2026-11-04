"""HOT club swap meet 2026-10-27: 470R carbon-film pack + five 1N4007 diodes.

Scott's photo 2026-11-04; counts are his ("25 and 5"). Neither part existed
(searched 4007/1N400/470R/470 ohm/carbon film/2781/rectifier):

- Adafruit #2781 CF axial 470R x25 -> F1-R3C5 beside the 220R (#2780) and
  4.7k carbon-film packs. NOT merged into part 612: that is 1% metal film.
- 1N4007 x5 on tape -> F1-R3C2 with the 1N4001 / 1N4935 rectifiers. Number
  read across the five bodies ("N4", "N40", "07", second line "M"); no one
  body shows it whole, so the Source note says so.

$0 like the rest of the swap meet. Pattern and verify are batch1's.

    itq run scripts/swap_meet_1027_470r_1n4007.py [--commit]
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
GROUP = "/tmp/hot-1027-470r-1n4007.jpg"

ITEMS = [
    dict(key="470rcf", name="Resistor 470R 5% 1/4W carbon film", cat="Electronics/Passives/Resistors",
         loc=F1 + "F1-R3C5", share_ok=["carbon film"], qty=25, purchaseable=True,
         keywords="470 ohm 470R carbon film axial Adafruit 2781",
         desc=("Carbon film axial resistor, 470 ohm, 5%, 1/4 W (yellow-violet-brown-gold). Adafruit "
               "#2781 pack (P2781). NOT the 1% metal film 470R (part 612)."),
         crop=(0.0, 0.27, 0.62, 0.92), photos=[]),
    dict(key="1n4007", name="Diode 1N4007", cat="Electronics/Semiconductors/Diodes",
         loc=F1 + "F1-R3C2", share_ok=["1N4001", "1N4935"], qty=5, purchaseable=True,
         keywords="1N4007 rectifier 1A 1000V DO-41 axial",
         desc=("General-purpose rectifier, 1 A, 1000 V PIV, DO-41 axial, black body with grey cathode band. "
               "Swap-meet units on tape; number read across five bodies (N4 / N40 / 07, 2nd line 'M'), "
               "no single body shows it whole."),
         crop=(0.57, 0.26, 0.88, 0.82), photos=["/tmp/hot-1027-1n4007-close.jpg"]),
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
        it["photos"] = [out] + it["photos"]
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
