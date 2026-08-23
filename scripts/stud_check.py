"""Do I need to order pull studs with these tool holders?

Answers ONE question, at the moment a holder order is being put together.
Deliberately not a reorder point: Scott, 2026-08-23 — *"I don't think the
threshold is the right answer, we don't need spares but we need to know if we
need studs when we order toolholders. The studs are cheaper purchased in 10
packs but I never buy that many toolholders at a time except on initial
investment."* A minimum-stock rule would nag to hold ten in reserve forever;
this speaks only when a specific order needs studs added to it.

**The holder decides the stud — it is not a choice.** A shrink-fit holder MUST
get a TSC (drilled) knob. Not for coolant: the 1100MX has no through-spindle
coolant at all. The hole is the passage a welding wire runs up to push a stuck
shank out during heat-shrink removal, and it also vents the blind bore, which is
why the induction machine was allowed to drop its spring hold-down (MR-16 in
shrink-fit/docs/requirements.md). A solid knob undoes both, and you find out
with a hot holder in your hand. See docs/TRAPS.md.

Usage:
  stud_check.py                          audit what is on hand
  stud_check.py --holders 3              3 ordinary BT30 holders proposed
  stud_check.py --shrink 2 --holders 1   mixed proposal
  stud_check.py --po PO-0137             read the holder lines off a PO
  stud_check.py --selftest               run the classifier cases, no database

Read-only. It never writes.

Classification is by NAME, and every BT30 part it cannot classify is LISTED
rather than dropped — a false miss costs a glance, a false match hides a gap.
That is why the operator's kit and the probe kit show up as unclassified: both
plausibly need a knob and neither can be settled from a name.
"""
import argparse
import re
import sys

# --------------------------------------------------------------------------
# Pure classification. No Django here, so --selftest runs anywhere.
# --------------------------------------------------------------------------

STUD = re.compile(r"pull stud|retention knob", re.I)
HOLDER = re.compile(r"holder|chuck|arbor", re.I)
SHRINK = re.compile(r"shrink[ _-]?fit", re.I)
TSC = re.compile(r"\bTSC\b", re.I)
BT30 = re.compile(r"\bBT[ _-]?30\b", re.I)

STUD_TSC = "stud-tsc"
STUD_STD = "stud-standard"
HOLDER_SHRINK = "holder-shrink"
HOLDER_STD = "holder-standard"
UNCLASSIFIED = "bt30-unclassified"


def classify(name: str):
    """Return one of the constants above, or None if not BT30 kit at all.

    Order matters: the shrink-fit holders carry 'TSC' in their own names, so the
    stud test has to run first or a holder would be counted as a stud.
    """
    if STUD.search(name):
        return STUD_TSC if TSC.search(name) else STUD_STD
    if not BT30.search(name):
        return None
    if HOLDER.search(name):
        return HOLDER_SHRINK if SHRINK.search(name) else HOLDER_STD
    return UNCLASSIFIED


def verdict(need, have, label, sku, last_paid, pack=10):
    """One line per stud class. Glyph AND word — never colour alone.

    Quantities arrive as floats from the ORM; they are counts of solid objects
    and print as integers.
    """
    need, have = int(need), int(have)
    if need == 0:
        return f"  --  {label:9s} none needed   ({have} loose on hand)"
    if have >= need:
        return f"  OK  {label:9s} need {need}, have {have} loose"
    short = need - have
    packs = -(-short // pack)          # ceiling division
    return (f"  !!  {label:9s} need {need}, have {have} loose — SHORT {short}\n"
            f"      order {packs} x {pack}-pack: {sku}, last paid ${last_paid}")


def selftest():
    cases = [
        ("BT30 Pull Stud / Retention Knob, Standard (pack of 10)", STUD_STD),
        ("BT30 Pull Stud / Retention Knob, TSC (pack of 10)", STUD_TSC),
        ("Pull Stud, BT30 45-Degree", STUD_STD),
        ("BT30 M12x45 Pull Stud / Retention Knob", STUD_STD),
        # carries TSC in its own name and must NOT read as a stud
        ('BT30 Shrink Fit Holder 1/8" x 2.56in Gage, TSC', HOLDER_SHRINK),
        ('BT30 Shrink Fit Holder 3/8" x 2.56in Gage, TSC', HOLDER_SHRINK),
        ("BT30 Tool Holder, End Mill 1/4 in., 50mm", HOLDER_STD),
        ("BT30 ER20 45mm Collet Chuck Tool Holder (4pc set)", HOLDER_STD),
        ("BT30 Tool Holder, Face Mill Arbor 1/2 in., 35mm", HOLDER_STD),
        ("BT30 Tool Holder, Drill Chuck 8mm, 80mm", HOLDER_STD),
        # BT30 kit that is not obviously a holder — must surface, not vanish
        ("12-Pocket Automatic Tool Changer for 1100MX (BT30)", UNCLASSIFIED),
        ("BT30 Operator's Kit (Inch)", UNCLASSIFIED),
        ("Passive Probe Kit (BT30)", UNCLASSIFIED),
        # not tooling at all
        ("150 ohm Resistor 1% 1/4W", None),
        ("MBR60100PT Schottky Rectifier 60A 100V TO-3P", None),
    ]
    bad = 0
    for name, want in cases:
        got = classify(name)
        mark = "ok " if got == want else "BAD"
        if got != want:
            bad += 1
        print(f"  {mark} {str(got):20s} (want {str(want):20s}) {name[:44]}")

    vcases = [
        ((0, 10), "none needed"),
        ((4, 10), "OK"),
        ((10, 10), "OK"),
        ((11, 10), "SHORT 1"),
        ((11, 10), "order 1 x 10-pack"),
        ((25, 0), "SHORT 25"),
        ((25, 0), "order 3 x 10-pack"),      # ceiling, not 2
    ]
    for (need, have), expect in vcases:
        line = verdict(need, have, "TSC", "04-1420", "83.97")
        mark = "ok " if expect in line else "BAD"
        if expect not in line:
            bad += 1
        print(f"  {mark} need={need:<3} have={have:<3} expect {expect!r}")

    print("\nSELFTEST PASSED" if not bad else f"\n*** {bad} FAILURES ***")
    return 1 if bad else 0


# --------------------------------------------------------------------------

ap = argparse.ArgumentParser()
ap.add_argument("--holders", type=int, default=0, help="ordinary BT30 holders proposed")
ap.add_argument("--shrink", type=int, default=0, help="shrink-fit holders proposed")
ap.add_argument("--po", help="read proposed holder lines off this PO reference")
ap.add_argument("--selftest", action="store_true")
a = ap.parse_args()

if a.selftest:
    sys.exit(selftest())

import os                                        # noqa: E402
import django                                    # noqa: E402

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from order.models import PurchaseOrder           # noqa: E402
from part.models import Part                     # noqa: E402
from stock.models import StockItem               # noqa: E402

# Last prices actually paid, from the Haas orders already in the catalogue —
# historical actuals, not quotes. Verify live before ordering.
PACKS = {
    STUD_TSC: ("Haas 04-1420", "83.97"),
    STUD_STD: ("Haas 04-1421", "71.97"),
}

loose = {STUD_TSC: 0.0, STUD_STD: 0.0}
holders = {HOLDER_SHRINK: 0.0, HOLDER_STD: 0.0}
unclassified = []
stud_parts, holder_parts = [], []

for p in Part.objects.all().only("id", "name"):
    kind = classify(p.name)
    if kind is None:
        continue
    qty = sum(float(i.quantity) for i in StockItem.objects.filter(part=p))
    if kind in loose:
        loose[kind] += qty
        stud_parts.append((p, kind, qty))
    elif kind in holders:
        holders[kind] += qty
        holder_parts.append((p, kind, qty))
    else:
        unclassified.append((p, qty))

print("ON HAND")
print("  pull studs (loose — studs fitted to holders read zero):")
for p, kind, qty in sorted(stud_parts, key=lambda r: -r[2]):
    tag = "TSC" if kind == STUD_TSC else "standard"
    print(f"      {qty:5g}  {tag:9s} [{p.pk}] {p.name[:46]}")
print(f"      {loose[STUD_TSC]:5g}  TSC total")
print(f"      {loose[STUD_STD]:5g}  standard total")

print("\n  BT30 holders:")
for p, kind, qty in sorted(holder_parts, key=lambda r: (r[1], -r[2])):
    tag = "SHRINK" if kind == HOLDER_SHRINK else "ordinary"
    print(f"      {qty:5g}  {tag:9s} [{p.pk}] {p.name[:46]}")

if unclassified:
    print("\n  ?? BT30 parts this could not classify — decide by eye, not by name:")
    for p, qty in unclassified:
        print(f"      {qty:5g}  [{p.pk}] {p.name[:56]}")

# ---- what is being proposed -------------------------------------------------
want_shrink, want_std = a.shrink, a.holders
source = "the numbers you gave"

if a.po:
    po = PurchaseOrder.objects.filter(reference=a.po).first()
    if not po:
        sys.exit(f"no such PO: {a.po}")
    source = f"{po.reference} ({po.get_status_display()})"
    want_shrink = want_std = 0
    for line in po.lines.all():
        part = line.part.part if line.part else None
        if not part:
            continue
        kind = classify(part.name)
        if kind == HOLDER_SHRINK:
            want_shrink += int(float(line.quantity))
        elif kind == HOLDER_STD:
            want_std += int(float(line.quantity))
        elif kind == UNCLASSIFIED:
            print(f"\n  ?? {po.reference} line: {part.name[:52]} — BT30, unclassified. "
                  "May need a knob; not counted.")

if not (want_shrink or want_std):
    print("\nNo holder order proposed — audit only.")
    print("  Rerun with --holders N / --shrink N, or --po <ref>, before buying.")
else:
    print(f"\nPROPOSED ORDER — from {source}")
    print(f"  {want_shrink} shrink-fit holder(s)  -> need TSC (drilled) knobs")
    print(f"  {want_std} ordinary BT30 holder(s)  -> need standard knobs")
    print("\nVERDICT")
    sku, paid = PACKS[STUD_TSC]
    print(verdict(want_shrink, loose[STUD_TSC], "TSC", sku, paid))
    sku, paid = PACKS[STUD_STD]
    print(verdict(want_std, loose[STUD_STD], "standard", sku, paid))

# ---- the standing safety check ---------------------------------------------
print("\nSHRINK-FIT HOLDERS — the check you cannot undo at the bench")
n = holders[HOLDER_SHRINK]
if n:
    print(f"  {n:g} shrink-fit holder(s) on hand. Every one MUST carry a TSC "
          "(drilled) knob:")
    print("    - it is the passage a welding wire runs up to push out a stuck shank")
    print("    - it vents the blind bore, which is why MR-16 dropped the hold-down")
    print(f"  {loose[STUD_TSC]:g} TSC knob(s) are loose.")
    print("  ?? NOTHING RECORDS which holders have knobs fitted. This cannot be "
          "answered from the database — look at them.")
else:
    print("  none on hand")
