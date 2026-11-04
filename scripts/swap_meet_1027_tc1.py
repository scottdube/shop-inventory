"""HOT club swap meet 2026-10-27: TC1 multi-function component tester.

New: part_find on TC1 / component tester / transistor tester / LCR-T4 / GM328
found only the FNIRSI LCR-P1 (part 1056), a different instrument. Category beside
it (Equipment/Test Equipment). Cab4-D4 is where Scott keeps test equipment for
now ("temp housed"); it is still the right default_location, since that is where
a spare goes home until the bench exists. Qty 1 as proposed. $0.

    itq run scripts/swap_meet_1027_tc1.py [--commit]
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
    dict(key="tc1", name="Multi-function Tester TC1 (TFT component tester + IR decoder)",
         cat="Equipment/Test Equipment", loc="LRD/Countertop Wall/Cab4/Cab4-D4", share_ok=[], qty=1,
         purchaseable=True,
         keywords="TC1 component tester transistor tester LCR ESR diode IR decoder ZIF GM328 clone",
         desc=("Handheld 'Multi-function Tester - TC1': colour TFT, 14-pin ZIF socket (pin groups 1-2-3), "
               "SMD test pads (KAA1233), IR receiver for remote decoding, single Start button. Tests "
               "transistors, diodes, R/C/L, ESR. Screen protector film still on."),
         src="/tmp/hot-1027-tc1.jpg", crop=None),
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
