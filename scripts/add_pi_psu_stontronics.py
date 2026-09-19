#!/usr/bin/env python3
"""Catalogue the Stontronics DSA-13PFC-05 5.1 V 2.5 A micro-USB supply.

This is the supply Scott said comes with [Raspberry Pi 3 Model B #1236], shown
2026-09-19. It resolves the open question on that record: the PSU answer had
come back as "pihole dns" -- the SD-card answer landing in the power-supply
slot -- so the supply was unidentified until the label was photographed.

WHY IT GETS NO PS-### DESIGNATOR, unlike PS-002/009/010/011. Those numbers are
doc-local designators from the sln-ha-config power-supply survey: a numbered
walk through ONE box of unknown wall warts at SLN, where the number is the only
handle a nameless brick has. This brick is not from that box, is not nameless,
and is leaving the state today. Giving it PS-012 would put a row in a survey it
was never part of and imply it sits in the SLN DC SUPPLIES bin, which it does
not. The model number is a better handle than a sequence number ever was.

WHAT IS READ AND WHAT IS NOT:
  read off the label   STONTRONICS Switching Adapter, MODEL DSA-13PFC-05 FCA
                       051250, P/N T5989DV, IN 100-240V~ 50/60Hz 0.5A,
                       OUT +5.1V(DC) 2.5A, micro-USB PIN1 "+" PIN5 "-",
                       Efficiency Level VI, Class II (square-in-square),
                       Dee Van Electronics (Longchuan) Co., Ltd. / DVE,
                       No.5 Pao-Kao Road Hsin-Tien Taipei 231 Taiwan.
                       Marks: RoHS, CE, UL listed, RCM, KC, CCC, GS/TUV, PSE.
  moulded in the case  "0218HB"
  INFERENCE, not read  that 0218 is a Feb-2018 date code, and that Stontronics
                       DSA-13PFC-05 is the Raspberry Pi Foundation's official
                       Pi 2/3 supply. Both are marked as such below.
  NOT known            whether the micro-USB lead is captive or detachable --
                       only the brick is in the photograph -- and the mains
                       plug pattern (US/UK/EU).

LOCATION IS A JUDGEMENT CALL. FL-01, the Florida carry box, because #1236 went
in there an hour ago and a Pi 3B in Florida without a micro-USB supply is a
paperweight. Scott said the supply comes WITH the Pi; he did not say to pack it.

    itq run scripts/add_pi_psu_stontronics.py [--commit]
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part, PartCategory  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

COMMIT = "--commit" in sys.argv
CATEGORY_PK = 54          # Electronics/Power
FL_PK = 504               # SLN/Florida Staging/FL-01
PI_PK = 1236
PREFIX = "Stontronics DSA-13PFC-05"
QTY = 1

NAME = "Stontronics DSA-13PFC-05 PSU, 5.1V 2.5A micro-USB (official Raspberry Pi 2/3)"
DESC = ("Switching adapter, 100-240 V in, +5.1 V DC 2.5 A out (12.75 W) on micro-USB, "
        "PIN1 +, PIN5 -. Class II, Efficiency Level VI. P/N T5989DV, made by DVE / Dee "
        "Van. Ships with Raspberry Pi 3B #1236. Cable captive-or-not unverified.")
KEYWORDS = ("stontronics DSA-13PFC-05 DSA13PFC T5989DV DVE dee van switching adapter "
            "power supply PSU 5.1V 5V 2.5A micro-USB microUSB raspberry pi 2 3 3B "
            "official wall wart level VI class II 051250")

NOTES = """Official-pattern **Raspberry Pi 2/3 power supply**. Read off the label 2026-09-19:

    STONTRONICS  Switching Adapter
    MODEL: DSA-13PFC-05 FCA  051250      P/N: T5989DV
    INPUT:  100-240V ~ 50/60Hz  0.5A
    OUTPUT: +5.1V (DC) 2.5A              micro-USB, PIN1 "+", PIN5 "-"
    EFFICIENCY LEVEL: VI                 Class II (square-in-square)
    Dee Van Electronics (Longchuan) Co., Ltd.  /  DVE
    No.5 Pao-Kao Road Hsin-Tien Taipei 231 Taiwan    Made in China
    Marks: RoHS, CE, UL listed, RCM/C-tick, KC, CCC, GS/TUV, PSE, WEEE, China RoHS 10

Moulded into the case above the label: **`0218HB`**.

**THE 5.1 V IS DELIBERATE AND IS THE WHOLE POINT OF THIS SUPPLY — do not "correct" it to 5.0 V.** A Pi 3B trips its undervoltage detector at **4.63 V at the board**, and the losses that get it there are in the *cable and the micro-USB contacts*, not the brick. Starting 100 mV high is the margin. A nominally-correct 5.00 V supply through a thin lead lands under the trip, and the symptom is not "no power" — it is **random SD-card corruption, dropped USB devices and unexplained reboots**, which reads exactly like a dying card. That misdiagnosis is the reason this note is long.

**⚠ THIS WILL NOT RUN A RASPBERRY PI 4.** The Pi 4 is USB-C and wants 3 A. Two supplies already in the catalogue are the Pi 4 ones and are **not** interchangeable with this: [#189 Smraza 5.1V 3A] and [#350]. Both are USB-C; this is micro-USB. The connector makes the mistake self-preventing in that direction — but a Pi 3B will happily accept a Pi 4 supply, so the pairing only has to be got right once, going the other way.

**2.5 A is the Pi 3B's own rating, not headroom.** The board idles near 0.4 A; the 2.5 A exists for the four USB ports, which share one bus. Hanging a spinning hard disk or a hungry USB device off the Pi and blaming the supply is the usual next step — the ports are the load, and a powered hub is the fix, not a bigger brick.

**NOT VERIFIED: whether the micro-USB lead is captive or a separate cable.** Only the brick is in the photograph. It matters: the official supply has a **captive** lead precisely so nobody substitutes a charging cable, and a thin detachable micro-USB cable is the single most common cause of Pi undervoltage. If it turns out to be detachable, keep *this* cable with *this* brick.

**NOT VERIFIED: the mains plug pattern.** US/UK/EU not established from this face.

**`0218HB` is INFERRED to be a February 2018 date code, NOT READ AS ONE.** It is moulded case text in the position makers usually put one, and a 2018 date sits naturally with the Pi 3B it came with. Nothing on the part says "date". Treated as a hypothesis, which is all it is, and it changes nothing — warranty on a hand-me-down supply is not live.

**Stontronics as the Raspberry Pi Foundation's official supply partner, and DSA-13PFC-05 as the official Pi 2/3 unit, is BACKGROUND KNOWLEDGE — not verified against a live vendor page this session.** The label text is what was read. The claim is here because it explains why the 5.1 V and 2.5 A are exactly the Pi's published figures, and it is marked so nobody later cites this row as a source.

**PAIRED WITH [Raspberry Pi 3 Model B #1236].** Scott, 2026-09-19: the Pi comes *"with Raspberry Pi power supply"*. This is that supply, and it closes the open question on #1236's notes — the PSU answer there had come back as *"pihole dns"*, which was the SD-card answer landing in the power-supply slot.

**Location is a judgement call: FL-01, the Florida carry box, with the Pi.** #1236 was packed there earlier today. Scott said the supply comes with the Pi; he did not say to pack it. Splitting them is the failure mode worth avoiding — a micro-USB Pi supply is not something the Florida shop can improvise from a drawer.

**`default_location` is deliberately EMPTY.** FL-01 is a staging area, not a home, and the LRD home gets recorded on arrival rather than planned from here.

**No PS-### designator, on purpose.** Those are doc-local numbers from the `sln-ha-config` survey of one box of unknown wall warts at SLN. This brick is not from that box, is not unknown, and is leaving the state. See the script docstring."""


def check():
    lim = (("name", NAME, 100), ("description", DESC, 250), ("keywords", KEYWORDS, 250))
    bad = [f"{f}: {len(v)} > {n}" for f, v, n in lim if len(v) > n]
    for f, v, n in lim:
        print(f"   {f:12s} {len(v):3d}/{n}")
    if bad:
        print("FIELD TOO LONG — full_clean() would abort:", *bad)
        sys.exit(1)


cat = PartCategory.objects.get(pk=CATEGORY_PK)
fl = StockLocation.objects.get(pk=FL_PK)
existing = Part.objects.filter(name__startswith=PREFIX).first()
print(f"category: {cat.pathstring}\nlocation: {fl.pathstring}\n{NAME}")
check()
print(f"\nexisting: {('#%d' % existing.pk) if existing else 'will create'}")

if not COMMIT:
    print(f"\nDRY RUN — nothing written. Would create qty {QTY} @ {fl.pathstring}.")
    sys.exit(0)

if existing is None:
    p = Part.objects.create(name=NAME, description=DESC, category=cat,
                            keywords=KEYWORDS, notes=NOTES, active=True,
                            purchaseable=True, component=True)
else:
    p = existing
    Part.objects.filter(pk=p.pk).update(name=NAME, description=DESC, category=cat,
                                        keywords=KEYWORDS, notes=NOTES,
                                        default_location=None)
p.refresh_from_db()

si = StockItem.objects.filter(part=p).first()
if si is None:
    si = StockItem.objects.create(part=p, location=fl, quantity=QTY)
else:
    StockItem.objects.filter(pk=si.pk).update(location=fl)
si.refresh_from_db()

# close the open PSU question on the Pi's record
pi = Part.objects.get(pk=PI_PK)
OLD = "**NO POWER SUPPLY ON THIS RECORD.**"
NEW = ("**POWER SUPPLY RESOLVED 2026-09-19 — [Stontronics DSA-13PFC-05, 5.1V 2.5A "
       "micro-USB #%d], packed into FL-01 alongside this board.** Label photographed; "
       "it is the official-pattern Pi 2/3 supply. **Superseded text follows.** "
       "**NO POWER SUPPLY ON THIS RECORD.**" % p.pk)
if OLD not in pi.notes:
    print(f"\nANCHOR MISSING on #{PI_PK} — refusing a half edit.")
    sys.exit(1)
Part.objects.filter(pk=PI_PK).update(notes=pi.notes.replace(OLD, NEW, 1))
pi.refresh_from_db()

print(f"\n#{p.pk} {p.name}")
print(f"    category          {p.category.pathstring}")
print(f"    default_location  {p.default_location.pathstring if p.default_location else 'NONE  <- staging is not a home'}")
print(f"    stock [{si.pk}] qty {si.quantity:g} @ {si.location.pathstring}"
      f"  {'ok' if si.location_id == FL_PK and float(si.quantity) == QTY else '!! WRONG'}")
for label, probe in (("5.1V explained", "THE 5.1 V IS DELIBERATE"),
                     ("not-a-Pi-4 warning", "WILL NOT RUN A RASPBERRY PI 4"),
                     ("cable unverified", "captive or a separate cable"),
                     ("date code hedged", "INFERRED to be a February 2018 date code"),
                     ("official claim hedged", "BACKGROUND KNOWLEDGE"),
                     ("paired with Pi", "#1236")):
    print(f"    {label:22s} {probe in p.notes}")
print(f"\n#{PI_PK} PSU question closed: {('#%d' % p.pk) in pi.notes}")
print(f"    florida metadata: {pi.notes.count('POWER SUPPLY RESOLVED')} marker(s)")
print(f"\nFL-01 now holds {StockItem.objects.filter(location=fl).count()} stock rows")
