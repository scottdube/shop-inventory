#!/usr/bin/env python3
"""Catalogue the three kept wall-warts and the bin they live in.

Salvage triage 2026-09-19: ten supplies read, three kept, seven recycled. The
full record -- triage rules, bench gate, nameplate transcriptions, the
gauge-pin method for barrel ID -- is in sln-ha-config:
`docs/reference/power-supply-inventory.md`. Only what a person needs standing
at the shelf is duplicated here.

THE BIN IS B-02, NOT "DC SUPPLIES". B-01 (wire & sleeving) set the convention
on this shelf: the bin carries a B-nn address, the ID travels WITH the bin so a
move is a re-parent and not a rename, and LABELLING.md prints the ADDRESS on
the tape, never the contents. An earlier pass drew a bin label reading
"DC SUPPLIES / 12V / 24V bricks - PoE adapters"; that is contents, which is the
one thing these labels deliberately do not carry. Contents go in the
description, where they can change without reprinting tape.

NAMES ARE WRITTEN FOR THE LABEL, NOT FOR THE DATABASE. Each name carries
exactly the five fields docs/reference §6 specifies, in the order they get
read: ID, volts, amps, connector, polarity.

BRAND AND MODEL ARE DELIBERATELY NOT IN THE NAME, and this was got wrong once
here. A name ending "(FULLPOWER SAW30-240-0800U)" is 69 characters, under the
template's truncatechars:75, so nothing truncated -- and it still rendered as
"(FULLPOWER" with the model clipped off, because the real limit is THREE LINES
of about 25 characters at 3.1mm Arial across 42mm, and word wrap wastes the
rest. The character cap and the line budget are different limits; 75 characters
only fits when the words happen to pack. Caught by looking at the render, which
is the whole reason LABELLING.md requires it. Model lives in the description
and keywords, where it is searchable, and on the brick's own sticker, which is
in your hand by the time you care.

BARREL ID IS THE FIELD THAT DECIDES COMPATIBILITY AND THE ONE NEVER PRINTED ON
A WALL WART. 5.5x2.1 and 5.5x2.5 do not interchange in either direction, so it
is in every name. Measured with gauge pins, not read off a label.

No supplier parts, no prices: these are salvage, and a purchase record would be
an invention.

    itq run scripts/add_dc_supplies_bin.py
    itq run scripts/add_dc_supplies_bin.py --commit
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part, PartCategory      # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

COMMIT = "--commit" in sys.argv

SHELF_PK = 455          # SLN/Storage/WS2/WS2-S3 -- with B-01 and the two enclosed PSUs
CATEGORY = "Electronics/Power"

BIN_NAME = "B-02"
BIN_DESC = (
    "DC SUPPLIES. 12V/24V wall-warts kept in the 2026-09-19 salvage triage, plus PoE "
    "adapters. BIN B-02 - 6 qt clear snap-on lid, on WS2-S3 beside B-01. A HOME (things "
    "here get default_location); the ID travels with the bin, so a move is a re-parent."
)

# (name, description, keywords, notes)
SUPPLIES = [
    (
        "PS-002 Power Adapter 24V 0.8A, 5.5x2.1 C+",
        "Salvaged wall-wart. 100-240V in, 24V DC 0.8A (19.2W) out, 5.5x2.1mm "
        "barrel, centre-positive. Regulated switcher, DOE Level VI. Date code "
        "1803 (2018). Origin device unknown.",
        "PS-002 wall wart power adapter supply 24V 0.8A 19W barrel 5.5x2.1 "
        "centre positive center regulated switching Level VI FULLPOWER "
        "SAW30-240-0800U salvage",
        "Kept in the 2026-09-19 salvage triage as the low-draw 24V spare.\n\n"
        "Nameplate: FULLPOWER SAW30-240-0800U, in 100-240V 50/60Hz 0.8A, out 24V "
        "DC 800mA. Date code 1803, so 2018.\n\n"
        "**Centre-positive**, read off the label's own barrel symbol in a "
        "close-up, not inferred.\n\n"
        "**Regulated**, and that is what makes it reusable: a 100-240V input "
        "means a switcher, which holds its rated voltage unloaded. A 120V-only "
        "input would mean an unregulated linear that only reaches its printed "
        "voltage at its printed load -- safe on its origin device and nothing "
        "else.\n\n"
        "**5.5x2.1mm barrel**, so it shares a plug with PS-009 (12V) and NOT "
        "with PS-010 (2.5mm). A 24V brick physically fits the 12V device. "
        "Check the sticker before plugging anything in.\n\n"
        "Full triage record: sln-ha-config docs/reference/power-supply-inventory.md",
    ),
    (
        "PS-009 Power Adapter 12V 1.5A, 5.5x2.1 C+",
        "Salvaged wall-wart. 100-240V in, 12V DC 1.5A (18W) out, 5.5x2.1mm "
        "barrel, centre-positive. Regulated switcher, DOE Level VI, Class II. "
        "Origin device unknown.",
        "PS-009 wall wart power adapter supply 12V 1.5A 18W barrel 5.5x2.1 "
        "centre positive center regulated switching Level VI Class II APD "
        "Asian Power Devices WB-18D12FU salvage",
        "Kept in the 2026-09-19 salvage triage. The first 12V unit found in the "
        "box, after eight supplies had suggested there were none.\n\n"
        "Nameplate: Asian Power Devices (APD) WB-18D12FU, in 100-240V 50/60Hz "
        "0.5A max, out 12V DC 1.5A.\n\n"
        "**Centre-positive**, read off the label's own barrel symbol at "
        "magnification -- confirmed marking, not APD house style. Also legible "
        "there: K&K Co. Ltd as Japanese PSE responsible party, Denan "
        "registration R43017, the PSE diamond, indoor-use mark.\n\n"
        "**Barrel OD measured 5.5mm with calipers; ID settled with gauge pins.** "
        "5.5mm barrels come 2.1 and 2.5 and do not interchange -- a 2.5 bore on "
        "a 2.1 pin has no grip and arcs under load. Method: a 0.090in pin sits "
        "midway, so won't-go means 2.1 and goes-freely means 2.5.\n\n"
        "**Do not feed the DP-001 marine panel from this.** Its 12V socket alone "
        "is rated well past 1.5A.\n\n"
        "Full triage record: sln-ha-config docs/reference/power-supply-inventory.md",
    ),
    (
        "PS-010 Power Adapter 24V 2.5A, 5.5x2.5 C+",
        "Salvaged wall-wart. 100-240V in, 24V DC 2.5A (60W) out, 5.5x2.5mm "
        "barrel, centre-positive. Regulated switcher, DOE Level VI, ETL. Best "
        "supply in the box. From Polk AV gear.",
        "PS-010 wall wart power adapter supply 24V 2.5A 60W barrel 5.5x2.5 "
        "centre positive center regulated switching Level VI ETL Polk "
        "DYS602-240250W soundbar salvage",
        "Kept in the 2026-09-19 salvage triage, and the best supply in the box: "
        "60W of universal-input switching.\n\n"
        "Nameplate: Polk DYS602-240250-15714A / model DYS602-240250W, Dongguan "
        "Dongsong Electronic. In 100-240V 50/60Hz 1.5A max, out 24.0V DC 2.5A. "
        "ETL listed (Intertek 4002961) to ANSI/UL 60065, the audio/video "
        "apparatus standard -- which matches the Polk branding, so a soundbar or "
        "powered-speaker supply. Date code 2416 = week 24 of 2024.\n\n"
        "**2024 date code, and the origin device has not been identified.** "
        "Confirm the Polk gear it came from is actually retired before treating "
        "this as a free spare -- it is the one unit in the bin recent enough to "
        "still have a job somewhere.\n\n"
        "**5.5x2.5mm barrel, the odd one out.** PS-002 and PS-009 are both 2.1, "
        "so this plug will not seat on their devices at all, and theirs will not "
        "grip this one's.\n\n"
        "Full triage record: sln-ha-config docs/reference/power-supply-inventory.md",
    ),
]

STOCK_NOTE = ("One unit, counted by Scott during the 2026-09-19 salvage triage "
              "of the wall-wart box. Tallied, not an estimate. Salvage: no "
              "purchase record, no price.")


def check_limits():
    """Description and keywords are capped at 250 and Part.save() full_cleans,
    so an over-long string aborts the create outright rather than truncating."""
    bad = []
    if len(BIN_DESC) > 250:
        bad.append(f"BIN_DESC {len(BIN_DESC)} > 250")
    for name, desc, kw, _notes in SUPPLIES:
        if len(name) > 100:
            bad.append(f"{name[:12]} name {len(name)} > 100")
        if len(desc) > 250:
            bad.append(f"{name[:6]} description {len(desc)} > 250")
        if len(kw) > 250:
            bad.append(f"{name[:6]} keywords {len(kw)} > 250")
    return bad


shelf = StockLocation.objects.get(pk=SHELF_PK)
cat = PartCategory.objects.get(pathstring=CATEGORY)
print(f"shelf:    [{shelf.pk}] {shelf.pathstring}")
print(f"category: [{cat.pk}] {cat.pathstring}")

bad = check_limits()
for b in bad:
    print(f"  FIELD TOO LONG: {b}")
if bad:
    sys.exit(1)

print(f"\nbin {BIN_NAME}: ", end="")
bin_loc = StockLocation.objects.filter(name=BIN_NAME, parent=shelf).first()
print("EXISTS" if bin_loc else "will create")
for name, desc, kw, _notes in SUPPLIES:
    dup = Part.objects.filter(name__startswith=name.split(" ")[0] + " ").first()
    label_len = len(name)
    state = ("EXISTS" if dup and dup.name == name
             else f"RENAME from {dup.name!r}" if dup else "will create")
    print(f"  {state}\n      ({label_len:2d} chars) {name}")

if not COMMIT:
    print("\nDRY RUN - nothing written. Re-run with --commit.")
    sys.exit(0)

if bin_loc is None:
    bin_loc = StockLocation.objects.create(
        name=BIN_NAME, parent=shelf, description=BIN_DESC)
    bin_loc.refresh_from_db()
    if bin_loc.description != BIN_DESC:      # .save() has reported success and written nothing here
        StockLocation.objects.filter(pk=bin_loc.pk).update(description=BIN_DESC)
        bin_loc.refresh_from_db()
print(f"\nbin [{bin_loc.pk}] {bin_loc.pathstring}")
print(f"    description written: {bin_loc.description == BIN_DESC}")

for name, desc, kw, notes in SUPPLIES:
    # Match on the PS-nnn prefix, not the whole string, so a re-run after a
    # name change renames the existing part instead of creating a twin.
    p = Part.objects.filter(name__startswith=name.split(" ")[0] + " ").first()
    if p is not None and p.name != name:
        Part.objects.filter(pk=p.pk).update(name=name)
        p.refresh_from_db()
        print(f"  renamed #{p.pk} -> {p.name}")
    if p is None:
        p = Part.objects.create(
            name=name, description=desc, category=cat, keywords=kw, notes=notes,
            default_location=bin_loc, active=True, purchaseable=False,
            component=True, salable=False)
    p.refresh_from_db()
    if p.default_location_id != bin_loc.pk:
        Part.objects.filter(pk=p.pk).update(default_location=bin_loc)
        p.refresh_from_db()

    si = p.stock_items.filter(location=bin_loc).first()
    if si is None:
        si = StockItem.objects.create(
            part=p, location=bin_loc, quantity=1, notes=STOCK_NOTE)
        si.refresh_from_db()

    print(f"\n#{p.pk} {p.name}")
    print(f"    category        {p.category.pathstring}")
    print(f"    default_location {p.default_location.pathstring if p.default_location else None}")
    print(f"    notes written   {len(p.notes)} chars, barrel ID present: {'5.5x2.' in p.notes or 'barrel' in p.notes}")
    print(f"    stock [{si.pk}] qty {float(si.quantity):g} @ {si.location.pathstring}")
