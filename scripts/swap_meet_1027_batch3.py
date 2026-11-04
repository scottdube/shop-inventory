"""HOT club swap meet 2026-10-27, batch 3: timer board, L298N x2, SMD polymer caps x25.

All new (part_find: L298, H-bridge, motor driver, K141, multi-mode, timer,
AT89C2051, 470uF 10V, polymer). The 470uF 10V SMD polymer cap is NOT part 668:
that is a through-hole wet electrolytic of the same value, not interchangeable on
a board. Counts and drawers are Scott's ("2", "25", "yes"). Categories sit beside
siblings: L298N with the BTS7960 (ICs/Motor), the timer with the DROK delay relay
(Relays). $0 like the rest of the swap meet.

    itq run scripts/swap_meet_1027_batch3.py [--commit]
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
    dict(key="timer", name="Multi-Mode Timer Board K141 (AT89C2051, 12V relay)", cat="Relays",
         loc=F1 + "F1-R6C3", share_ok=[], qty=1, purchaseable=False,
         keywords="K141 Kitsrus multi-mode timer relay AT89C2051 delay interval",
         desc=("Assembled kit board, silk 'MULTI-MODE TIMER' / 'K141' (looks like a Kitsrus kit number, "
               "unconfirmed). Atmel AT89C2051-24PI MCU, 12.0 MHz crystal, Songle SRD-12VDC-SL-C relay "
               "(10A 250VAC), DIP switches for timer mode, interval (1s/10s/1min/10min) and 8-bit count, "
               "5-way screw terminals each end."),
         src="/tmp/hot-1027-group3.jpg", crop=(0.10, 0.13, 0.79, 0.41)),
    dict(key="l298n", name="L298N Dual H-Bridge Motor Driver Module", cat="ICs/Motor",
         loc=F1 + "F1-R6C2", share_ok=[], qty=2, purchaseable=True,
         keywords="L298N H-bridge motor driver dual stepper DC module",
         desc=("Red L298N dual H-bridge module with heatsink and onboard 5V regulator (78M05) + jumper; "
               "OUT1-4 screw terminals, +12V/GND/+5V power terminal, ENA/ENB jumpers."),
         src="/tmp/hot-1027-group3.jpg", crop=(0.15, 0.51, 0.88, 0.80)),
    dict(key="polycap", name="Capacitor Polymer Aluminium 470uF 10V SMD", cat="Electronics/Passives/Capacitors",
         loc=F1 + "F1-R3C6", share_ok=["Capacitor Electrolytic"], qty=25, purchaseable=True,
         keywords="470uF 10V polymer solid aluminium SMD V-chip FP 38AA low ESR",
         desc=("Conductive-polymer (solid) aluminium SMD can, 470uF 10V, top marking 'FP 38AA 470 10'. "
               "On cut tape. Maker and can size not established. NOT the through-hole 470uF 10V (part 668)."),
         src="/tmp/hot-1027-polycap.jpg", crop=None),
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
