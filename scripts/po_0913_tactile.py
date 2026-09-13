"""Queue C: Amazon order 113-9688006-8089017 (2026-09-13) -> PO + 6 parts.

Sim-cockpit tactile/audio set: two kinds of Dayton bass shaker, the 4-channel
amp that drives them, speaker wire, speakon plugs and a TRS->dual-TS breakout.

PRICE SOURCE — the order-details page, per item, NOT the confirmation email.
The email carries only "Grand Total: 423.8 USD" and that figure is never a
price on this install (points and gift cards apply invisibly under it). The
per-item figures read off the order-details page are:

    Dayton TT25-8 4-pack            79.88 x 1
    Behringer EPQ304               229.00 x 1
    Sinus Live speaker wire 50ft    19.98 x 1
    Cable Matters TRS->2x TS        12.99 x 2
    Dayton BST-1                    54.98 x 1
    bnafes NL4FC 2-pack              6.99 x 2
                                   -------
                                   423.80

which reconciles EXACTLY to the page's Item(s) Subtotal of $423.80 with
shipping $0.00 and tax $0.00. That arithmetic is the proof the displayed
figure is the UNIT price and not the extended one -- on a two-qty line those
differ, and getting it backwards doubles or halves the book value silently.

PACKS (a pack is a supplier fact, and both counts here are stated verbatim in
the seller's own title, not inferred):
  * TT25-8 title says "4 Pack"  -> pack_quantity 4, so $19.97 per puck
  * NL4FC  title says "2 PCS"   -> pack_quantity 2, ordered 2 packs = 4 plugs
Written through .save(), never .update(): only pack_quantity_native is read at
receive time and a queryset update changes the text field and nothing that
counts.

Reference handling: the vendor order number goes in supplier_reference ONLY.
A raw Amazon number in `reference` clamps reference_int to int32 max and
permanently breaks generate_reference() for the whole instance.

PLACED, never received. Two lines arrive tomorrow and the rest Tuesday; a
human checks the boxes in with receive_po.py.

CATEGORY CALL worth knowing: the two shakers follow the standing precedent of
part #52 (Dayton Audio DMA45-4 driver) into Electromechanical -- they are the
same class of voice-coil device. The EPQ304 does NOT; a rack power amplifier
is a standalone piece of equipment, not a component, so it goes to Equipment
(pk 30) and is the first part filed directly there. Power (pk 13) was the
alternative and was rejected because that category holds supplies and
regulators feeding the bench, not audio gear.
"""
import argparse
import datetime
import os
import sys

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import Company, SupplierPart  # noqa: E402
from order.models import PurchaseOrder, PurchaseOrderLineItem  # noqa: E402
from order.status_codes import PurchaseOrderStatus  # noqa: E402
from part.models import Part, PartCategory  # noqa: E402

ORDER = "113-9688006-8089017"
ISSUE = datetime.date(2026, 9, 13)
SUBTOTAL = 423.80

# asin, category pk, name, keywords, pack, unit price, qty ordered, orig title, notes
ITEMS = [
    dict(
        asin="B08LZW3RQL", cat=20, pack="4", unit="79.88", qty=1,
        name="Dayton Audio TT25-8 Puck Tactile Transducer, 8 ohm",
        orig=("Dayton Audio TT25-8 Puck Tactile Transducer Mini Bass Shaker "
              "8 Ohm 4 Pack"),
        desc=("Miniature puck-style tactile transducer (bass shaker), 8 ohm, "
              "surface-mount to a panel. Sold as a 4-pack. orig: "),
        kw=("tactile transducer, bass shaker, puck shaker, TT25-8, dayton audio, "
            "haptic, seat shaker, simulator rumble, 8 ohm, voice coil"),
        note=("Sold as a 4 Pack -- pack_quantity 4, so the $79.88 pack price "
              "books at $19.97 per puck."),
        pnote=("Four small puck transducers for cockpit panel haptics. 8 OHM, "
               "which is the number that decides how many can share one "
               "amplifier channel -- do not mix these with the 4 ohm BST-1 on "
               "the same channel without working out the combined load first.\n\n"
               "NOT COUNTED. Ordered 2026-09-13, arriving 2026-09-15. No stock "
               "row exists and none should until the box is checked in."),
    ),
    dict(
        asin="B004W4TYMA", cat=30, pack="1", unit="229.00", qty=1,
        name="Behringer EUROPOWER EPQ304 Power Amplifier, 4-channel 300 W",
        orig=("Behringer EUROPOWER EPQ304 Professional 300 Watt Light Weight "
              "4 Channel Power Amplifier with ATR (Accelerated Transient "
              "Response) Technology"),
        desc=("Four-channel rack power amplifier, 300 W total, ATR. Drives the "
              "cockpit tactile transducers. orig: "),
        kw=("power amplifier, 4 channel amplifier, behringer, EPQ304, europower, "
            "rack amp, tactile driver, bass shaker amp, speakon, 300W"),
        note="Sold by Sweetwater Sound via Amazon.",
        pnote=("Drives the tactile transducers -- four channels so each shaker "
               "group can be levelled independently rather than all running off "
               "one send.\n\n"
               "Outputs are SPEAKON (NL4), which is why the NL4FC plugs are on "
               "this same order; there are no binding posts to fall back on.\n\n"
               "NOT COUNTED. Ordered 2026-09-13, arriving 2026-09-15."),
    ),
    dict(
        asin="B0CLXPRY45", cat=19, pack="1", unit="19.98", qty=1,
        name="Speaker Wire 16-18 AWG OFC, 50 ft, purple/black",
        orig=("Sinus Live 16-18AWG OFC(Oxygen Free Copper) Speaker Wire Great "
              "use for Home Theater Speakers and Car Speakers, Purple and Black "
              "(50FT OFC)"),
        desc=("Two-conductor oxygen-free copper speaker wire, 16-18 AWG, "
              "polarity-coded purple/black. 50 ft spool. orig: "),
        kw=("speaker wire, OFC, oxygen free copper, 16 AWG, 18 AWG, two conductor, "
            "zip cord, audio cable, 50ft, polarity coded"),
        note=("One 50 ft spool. 50FT is a LENGTH, not a multipack -- "
              "pack_quantity stays 1."),
        pnote=("Runs amplifier to tactile transducers. Purple/black rather than "
               "the usual copper/silver, so polarity is readable in a dark "
               "cockpit footwell without a torch.\n\n"
               "Stocked as SPOOLS, not feet. NOT COUNTED -- ordered 2026-09-13, "
               "arriving 2026-09-14."),
    ),
    dict(
        asin="B07PHVMTNT", cat=119, pack="1", unit="12.99", qty=2,
        name="Breakout Cable 3.5 mm TRS to dual 6.35 mm TS, 10 ft",
        orig="Cable Matters 3.5mm TRS to Dual 6.35mm TS Breakout Cable, 10ft",
        desc=("Y breakout cable, 3.5 mm stereo TRS plug to two 6.35 mm (1/4 in) "
              "mono TS plugs, 10 ft. orig: "),
        kw=("breakout cable, TRS to TS, 3.5mm to 6.35mm, 1/4 inch, quarter inch, "
            "Y cable, insert cable, stereo to dual mono, cable matters, 10ft"),
        note="Two ordered, each a single cable.",
        pnote=("Feeds the amplifier from a 3.5 mm source: the stereo TRS splits "
               "into two INDEPENDENT MONO channels, left and right, which is why "
               "this and not a stereo-to-stereo lead.\n\n"
               "NOT COUNTED. Ordered 2026-09-13, arriving 2026-09-14."),
    ),
    dict(
        asin="B01CDDPJTI", cat=20, pack="1", unit="54.98", qty=1,
        name="Dayton Audio BST-1 Tactile Bass Shaker, 50 W RMS 4 ohm",
        orig=("Dayton Audio BST-1 High Power Pro Tactile Bass Shaker 50 Watts "
              "RMS, 4 Ohms Impedance - Turn Any Surface into a Speaker System - "
              "Generates Subwoofer Lows"),
        desc=("High-power tactile bass shaker, 50 W RMS, 4 ohm. Bolts to a panel "
              "or seat frame to transmit low frequencies as vibration. orig: "),
        kw=("bass shaker, tactile transducer, BST-1, dayton audio, haptic, "
            "seat shaker, simulator rumble, 4 ohm, 50W, subwoofer"),
        note="Single unit.",
        pnote=("The big shaker -- seat or floor pan, as against the small TT25-8 "
               "pucks for panels.\n\n"
               "4 OHM, and the TT25-8 pucks on this same order are 8 ohm. Work "
               "out the combined load before putting them on one amplifier "
               "channel.\n\n"
               "Needs a RIGID mount to work at all: bolted to a mass that can "
               "move, not to something compliant that absorbs the stroke.\n\n"
               "NOT COUNTED. Ordered 2026-09-13, arriving 2026-09-14."),
    ),
    dict(
        asin="B09231Q2WV", cat=18, pack="2", unit="6.99", qty=2,
        name="Speakon Cable Plug NL4FC-compatible, 4-pole",
        orig=("bnafes NL4FC speakon Cable Amplifier Connector, Audio Speaker "
              "Plug Twist Lock 4 Pole Speaker Plug Compatible with Neutrik "
              "Speakon NL4FC, NL4FX, NLT4X, NL2FC - 2 PCS"),
        desc=("Four-pole twist-lock speaker cable plug, cable end, compatible "
              "with Neutrik NL4FC/NL4FX/NLT4X/NL2FC. Sold in 2-packs. orig: "),
        kw=("speakon, NL4FC, NL4FX, NL2FC, speaker plug, twist lock, 4 pole, "
            "cable connector, amplifier connector, neutrik compatible"),
        note=("Title states 2 PCS -- pack_quantity 2. Two packs ordered = 4 "
              "plugs. CABLE-END plug (male), not a chassis socket."),
        pnote=("Mates the speaker wire to the EPQ304's speakon outputs -- the "
               "amplifier has no binding posts, so without these it cannot be "
               "connected at all.\n\n"
               "These are CABLE-END plugs. A chassis-mount socket (NL4MP) is a "
               "different part and is not covered by this one.\n\n"
               "Third-party, not genuine Neutrik. NOT COUNTED -- ordered "
               "2026-09-13, arriving 2026-09-15."),
    ),
]

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
args = ap.parse_args()

amazon = Company.objects.get(name="Amazon")

# ---------------------------------------------------------------- idempotency
dup_po = PurchaseOrder.objects.filter(
    Q(supplier_reference=ORDER) | Q(reference=ORDER))
if dup_po.exists():
    sys.exit(f"!! PO already exists for {ORDER}: "
             f"{[p.reference for p in dup_po]} — nothing to do")

# the line total must reconcile to the page subtotal before anything is written
total = sum(float(i["unit"]) * i["qty"] for i in ITEMS)
print(f"reconcile: lines sum {total:.2f} vs page subtotal {SUBTOTAL:.2f}")
assert abs(total - SUBTOTAL) < 0.005, "line prices do not reconcile — refusing"

for i in ITEMS:
    sp = SupplierPart.objects.filter(supplier=amazon, SKU=i["asin"])
    pt = Part.objects.filter(Q(name=i["name"])
                             | Q(description__icontains=i["orig"][:40]))
    i["_sp"], i["_pt"] = sp, pt
    cat = PartCategory.objects.get(pk=i["cat"])
    print(f"  {i['asin']}  sp={sp.count()} part={pt.count()}  "
          f"[{cat.pathstring}] qty {i['qty']} x ${i['unit']} pack {i['pack']}")

if not args.commit:
    raise SystemExit("\nDRY RUN — add --commit")

# ---------------------------------------------------------------- PO
po = PurchaseOrder(
    supplier=amazon,
    reference=PurchaseOrder.generate_reference(),
    supplier_reference=ORDER,
    description=f"Amazon order {ORDER} — cockpit tactile transducers + amp",
    issue_date=ISSUE,
    status=PurchaseOrderStatus.PLACED.value,
    notes=("Auto-created from the Amazon order-confirmation email of 2026-09-13 "
           "(queue C daytime sweep, 12:40 run).\n\n"
           "PRICE SOURCE: the order-details page, per item. The confirmation "
           "email carries only 'Grand Total: 423.8 USD' and a grand total is "
           "never a price on this install -- points and gift cards apply "
           "invisibly under it. The six per-item prices reconcile exactly to "
           "the page's Item(s) Subtotal of $423.80, with shipping $0.00 and "
           "tax $0.00, which is also the proof that the displayed figure is the "
           "UNIT price and not the extended one on the two qty-2 lines.\n\n"
           "PLACED, not received. Two lines arrive 2026-09-14 and the rest "
           "2026-09-15; receive with receive_po.py when the boxes are "
           "physically checked in."),
)
po.save()
po.refresh_from_db()
assert po.status == PurchaseOrderStatus.PLACED.value, "PO status did not stick"
assert po.supplier_reference == ORDER, "supplier_reference did not stick"
print(f"\nCREATED {po.reference} supplier_ref={po.supplier_reference}")

for i in ITEMS:
    part = i["_pt"].first()
    if part is None:
        part = Part.objects.create(
            name=i["name"][:250],
            description=(i["desc"] + i["orig"])[:250],
            category=PartCategory.objects.get(pk=i["cat"]),
            purchaseable=True, component=False, active=True,
            keywords=i["kw"][:250],
            link=f"https://www.amazon.com/dp/{i['asin']}",
        )
        Part.objects.filter(pk=part.pk).update(notes=i["pnote"])
        part.refresh_from_db()
        assert part.keywords and part.notes, f"part fields did not stick: {part.pk}"
        print(f"  CREATED part #{part.pk} {part.name}")
    else:
        print(f"  REUSED  part #{part.pk} {part.name}")

    sp = i["_sp"].first()
    if sp is None:
        sp = SupplierPart(supplier=amazon, part=part, SKU=i["asin"],
                          link=f"https://www.amazon.com/dp/{i['asin']}",
                          note=i["note"])
        sp.pack_quantity = i["pack"]
        sp.save()  # .save() not .update(): only pack_quantity_native counts
        sp.refresh_from_db()
        assert float(sp.pack_quantity_native) == float(i["pack"]), \
            f"pack native did not stick on {i['asin']}"
        print(f"    sp #{sp.pk} pack_native={sp.pack_quantity_native}")
    else:
        print(f"    sp #{sp.pk} reused")

    li = PurchaseOrderLineItem(
        order=po, part=sp, quantity=i["qty"],
        purchase_price=i["unit"], purchase_price_currency="USD",
        notes="Per-item price from the Amazon order-details page.")
    li.save()
    li.refresh_from_db()
    # Decimal comes back padded ('79.8800'), so compare numerically
    assert float(li.purchase_price.amount) == float(i["unit"]), \
        f"price did not stick: {li.purchase_price}"
    print(f"    line: qty {li.quantity} @ {li.purchase_price}")

po.refresh_from_db()
booked = sum(float(l.purchase_price.amount) * float(l.quantity)
             for l in po.lines.all())
print(f"\nDONE  {po.reference}  lines={po.lines.count()}  booked=${booked:.2f}"
      f"  (page subtotal ${SUBTOTAL:.2f})")
assert abs(booked - SUBTOTAL) < 0.005, "booked total drifted from the page"
