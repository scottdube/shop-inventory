#!/usr/bin/env python3
"""Catalogue the Boat Command 40 A automotive relay.

Scott showed it 2026-09-19, one unit, immediately after the DP-001 panel work
established that the rocker's 4.8 mm tabs might bind below its 20 A contacts.
This relay removes that constraint.

WHY IT IS A NEW CAPABILITY AND NOT A DUPLICATE. The Relays category already
holds eleven parts and not one of them is an automotive ISO mini relay: three
solid-state, two time-delay, two ZigBee/WiFi smart relays, a MY2NJ 24 VAC, a
Churod 10 A 250 VAC, and some board modules. Nothing in the catalogue switches
tens of amps of 12 V DC on a bracket. Searched name + description + keywords
across ALL parts for 'relay', uncapped, before creating this.

NO STOCK ROW HERE. Location comes from Scott. A pre-wired relay with a pigtail
and a steel bracket is a different shape from the board modules in B3-R6C4, and
guessing it fits that drawer is exactly the kind of invented fact that stops
anyone ever re-asking.

WHAT IS READ AND WHAT IS NOT:
  read off the body   'QM', '40A 12VDC', and a contact diagram numbering
                      30 / 85 / 86 / 87 / 87a  -> 5-pin SPDT
  read off the card   boatcommand.com, 'Control Relay (12v)'
  Scott, asked        no additional markings anywhere on it; one unit; FREE
                      STOCK -- the Boat Command system went with the boat when
                      he sold it, so nothing can claim this relay back
  NOT known           the 87a (NC) contact rating, the coil current, and the
                      pigtail colour-to-terminal mapping

    itq run scripts/add_relay_40a.py [--commit]
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part, PartCategory  # noqa: E402
from stock.models import StockItem  # noqa: E402

COMMIT = "--commit" in sys.argv
CATEGORY_PK = 15          # Relays
PREFIX = "Relay 40A 12VDC SPDT 5-pin"

NAME = "Relay 40A 12VDC SPDT 5-pin, pre-wired pigtail"
DESC = ("Automotive ISO mini relay, 5-pin SPDT (30/85/86/87/87a). Contacts 40 A, "
        "coil 12 VDC. Colour-coded pigtail and steel mounting bracket. Body marked "
        "QM; sold by boatcommand.com as 'Control Relay (12v)'.")
KEYWORDS = ("relay automotive ISO mini 5-pin SPDT changeover 30 85 86 87 87a 40A "
            "12V 12VDC coil pigtail bracket QM boat command boatcommand marine "
            "12 volt high current switching")
NOTES = """Automotive **ISO mini relay, 5-pin SPDT**. Read off the body 2026-09-19: `QM`, `40A 12VDC`, and a contact diagram numbering **30 / 85 / 86 / 87 / 87a**. Card reads *boatcommand.com — "Control Relay (12v)"*. Pre-wired colour-coded pigtail, steel mounting bracket.

**⚠ ONLY ONE CONTACT RATING IS MARKED, AND IT ALMOST CERTAINLY IS NOT BOTH CONTACTS.** On 5-pin SPDT automotive relays the headline number is conventionally the **NO contact (87)**; the **NC contact (87a)** is commonly rated lower — 30 A against 40 A is the usual split. **Nothing on this body says so either way.** Scott checked for additional markings 2026-09-19 and there are none.

So: **87a's rating is UNKNOWN, not 30 A.** That is a property of the family, written here as what to check rather than as a fact about this unit — same posture as the S-360-12 mains selector. Do not put 40 A through 87a on the strength of the label. If the NC side is ever going to carry real current, find the datasheet or derate hard.

**THE COIL CURRENT IS NOT MARKED EITHER,** and it is the number that decides whether a given switch can drive this relay directly. ISO mini relays typically draw 150–200 mA at 12 V. **Not verified on this unit** — measure it before sizing the control side, it is one meter reading.

**WHY THIS PART MATTERS HERE: it resolves the DP-001 rocker constraint.** [DP-001 #1232]'s illuminated rocker is rated 20 A but its blades measured **4.8 mm**, and 4.8 mm FASTON is commonly rated well below the 6.35 mm part — so the rocker's *termination* may bind below its *contacts*. With this relay in the panel:

    rocker (coil only, ~0.2 A)  ---> relay coil 85/86
    +12V ---- fuse ---- relay 30 --> 87 ---- fuse 15A ---- 12V socket

the rocker carries a fifth of an amp instead of fifteen. The 4.8 mm tabs stop mattering, the 12 AWG-vs-14 AWG question at the switch disappears, and the heavy current never touches the switch at all.

**That makes the relay layout BETTER than the single-master-switch layout, not a fallback to it.** It was written up as a fallback while the only known constraint was the switch's contact rating; the tab measurement changed which number binds.

**THE PIGTAIL COLOURS ARE NOT RECORDED AND MUST NOT BE ASSUMED.** There is no reliable colour convention across relay makers. Ring out each lead to its terminal number before wiring — getting 85/86 confused with 30/87 on a pre-wired part is easy because the terminals are hidden inside the moulding.

**ORIGIN RESOLVED — FREE STOCK, nothing can claim it back.** Scott, 2026-09-19: *"this is just regular stock. The boat command system went with the boat when I sold it."* The parent system is gone, so there is no install to strand by spending this on the DP-001 build.

**And the missing parent does NOT make it an orphan** in the §2 triage sense. That rule recycles a part when the device is gone **and** the connector is proprietary. This is an ISO mini relay on the standard 30/85/86/87/87a pinout with a generic pigtail — the most interchangeable 12 V part there is. Half the rule is met and the half that matters is not.

**Related, possibly already owned:** an inline ATC/ATO blade fuse holder was in the same photo. [#252 Water-resistant ATC Fuse Holder, 16 Gauge In-Line] is in the catalogue as a 2016 3-pack with **no stock row** — very likely the same item. Count what is actually on hand and fill that row rather than creating a second part. [#239 WATERWICH 6-Way Blade Fuse Box] is in the same state and is the fuse block the DP-001 wiring calls for.

**Nothing else in the catalogue does this job.** The Relays category holds solid-state relays, time-delay relays, ZigBee/WiFi smart relays, a MY2NJ 24 VAC and a Churod 10 A 250 VAC. None of them switches tens of amps of 12 V DC on a bracket.

**Quantity is one, stated by Scott. Location not set — it comes from Scott.** A pigtailed relay with a bracket is a different shape from the board modules in `B3-R6C4`, and assuming it fits that drawer would put a guess in the record that nothing would ever re-ask."""


def check():
    lim = (("name", NAME, 100), ("description", DESC, 250), ("keywords", KEYWORDS, 250))
    bad = [f"{f}: {len(v)} > {n}" for f, v, n in lim if len(v) > n]
    for f, v, n in lim:
        print(f"   {f:12s} {len(v):3d}/{n}")
    if bad:
        print("FIELD TOO LONG — full_clean() would abort:", *bad)
        sys.exit(1)


cat = PartCategory.objects.get(pk=CATEGORY_PK)
existing = Part.objects.filter(name__startswith=PREFIX).first()
print(f"category: {cat.pathstring}\n{NAME}")
check()
print(f"\nexisting: {('#%d' % existing.pk) if existing else 'will create'}")

if not COMMIT:
    print("\nDRY RUN — nothing written. Re-run with --commit.")
    print("No stock row: location comes from Scott. Qty will be 1.")
    sys.exit(0)

if existing is None:
    p = Part.objects.create(name=NAME, description=DESC, category=cat,
                            keywords=KEYWORDS, notes=NOTES, active=True,
                            purchaseable=True, component=True)
else:
    p = existing
    Part.objects.filter(pk=p.pk).update(name=NAME, description=DESC, category=cat,
                                        keywords=KEYWORDS, notes=NOTES)
p.refresh_from_db()

print(f"\n#{p.pk} {p.name}")
print(f"    category          {p.category.pathstring}")
for label, probe in (("87a unknown", "87a's rating is UNKNOWN, not 30 A"),
                     ("coil unmarked", "THE COIL CURRENT IS NOT MARKED"),
                     ("DP-001 link", "#1232"),
                     ("colours unassumed", "PIGTAIL COLOURS ARE NOT RECORDED"),
                     ("origin resolved", "ORIGIN RESOLVED — FREE STOCK"),
                     ("fuse-holder lead", "#252")):
    print(f"    {label:18s} {probe in p.notes}")
print(f"    stock rows        {StockItem.objects.filter(part=p).count()}  <- awaiting location from Scott")
