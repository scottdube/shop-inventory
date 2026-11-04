"""HOT club swap meet 2026-10-27: relay modules, first two types, into F1-R7.

Scott has ~15 relay boards of several kinds (1/2-channel, high-amp, 5 V and
3 V) and wants them in ONE row, one small drawer per type. F1-R7 was the only
F1 row with nothing recorded in any of its 8 drawers, and it sits under the R6
module row (K141 timer, L298N, Mini Power). C1 and C2 now; C3-C8 for the rest.

- 1-channel, 5 V, opto, H/L jumper, Tongling JQC-3FF-S-Z  x4 -> F1-R7C1
- 2-channel, same family                                 x3 -> F1-R7C2
  Two boards carry Tongling JQC-3FF-S-Z relays, one (silk CW-026) Songle
  SRD-05VDC-SL-C. ONE part, not two: same coil, contact rating, trigger
  jumper and pinout - interchangeable, and one row per part per location.

Not merged into existing parts: 147 (XCSOURCE 1-ch) is a blue Songle board with
no trigger jumper; 303 (MCIGICM 2-ch) is low-trigger only; 460 is SainSmart's
own board. All three are at SLN B3-R6C4.

Counts are Scott's ("4 and 3"). Photos are uncropped: each shows only one part.

    itq run scripts/swap_meet_1027_relays.py            # dry run
    itq run scripts/swap_meet_1027_relays.py --commit
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

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
    dict(key="relay1ch", name="Relay Module 1-Channel 5V, opto-isolated, high/low trigger", cat="Relays",
         loc=F1 + "F1-R7C1", share_ok=[], qty=4, purchaseable=True,
         keywords="relay module 1 channel 5V optocoupler high low trigger JQC-3FF-S-Z Tongling arduino",
         desc=("Red 1-channel relay board, 5 V coil, Tongling JQC-3FF-S-Z SPDT relay (10 A 250 VAC / "
               "15 A 125 VAC). Optocoupler input, yellow H/L jumper selects high- or low-level trigger. "
               "Terminals NO/COM/NC and DC+/DC-/IN; PWR LED. Silk '1 Relay Module High/Low Level Trigger'."),
         crop=None, photos=["/tmp/hot-1027-relay1ch.jpg"]),
    dict(key="relay2ch", name="Relay Module 2-Channel 5V, opto-isolated, high/low trigger", cat="Relays",
         loc=F1 + "F1-R7C2", share_ok=[], qty=3, purchaseable=True,
         keywords="relay module 2 channel 5V optocoupler high low trigger JQC-3FF-S-Z Tongling SRD-05VDC-SL-C Songle CW-026",
         desc=("Red 2-channel relay board, 5 V coils, 10 A SPDT per channel. Optocoupler inputs, H/L "
               "jumpers select high- or low-level trigger; 4-way input terminal (DC+/DC-/IN1/IN2). "
               "Mixed lot: boards with Tongling JQC-3FF-S-Z relays (silk '2 Relay Module High/Low Level "
               "Trigger') and with Songle SRD-05VDC-SL-C relays (silk CW-026) - interchangeable."),
         crop=None, photos=["/tmp/hot-1027-relay2ch.jpg"]),
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

# Photos must already be on the Mini (itq push)
for it in ITEMS:
    assert all(os.path.exists(p) for p in it["photos"]), it["photos"]
    print(f"  photos {it['key']}: {it['photos']}")
if not commit:
    raise SystemExit("DRY RUN - re-run with --commit")


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
