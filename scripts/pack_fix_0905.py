#!/usr/bin/env python3
"""Set `pack_quantity` on the 29 supplier parts whose own record states a pack.

Every number below was READ OFF the supplier part — its SKU, its part name, or
its note — and the quoted evidence is in the table. None is inferred from a
price, a stock count or a plausible-looking regex hit. That is the same standard
this project holds purchase prices to ("only cost that appears verbatim in an
order line"), and it is why this can run unattended.

Two of pack_audit's 31 flags were EXCLUDED as regex artifacts, both a digit read
out of the middle of an identifier:

    part 383  B01983R7PK        -> "7PK"    an Amazon ASIN, not a 7-pack
    part 232  XIAO ESP32C6 Pack -> "6 Pack" a chip name, not a 6-pack

pack_audit.py's look-behind was widened to `(?<![\\d.A-Za-z])` the same night so
it stops reading counts out of letter-then-digit tokens.

WHY THIS IS SAFE TO WRITE UNATTENDED:
  * `pack_quantity` changes only how FUTURE receives convert a supplier's unit
    into pieces (multiply qty, divide price). It does not touch existing stock,
    and every stock row here already counts pieces consistently with the pack
    being set (fuses 48 of a 50-pack, U.FL leads 9 of a 10-pack, LEDs 75 of 100).
  * It is idempotent: re-running sets the same values and reports 0 changed.
  * It is reversible: the previous value was InvenTree's default of 1.
  * Nothing is created or deleted.
  * Measured first: 0 of the 10 lines on the 9 OPEN purchase orders is affected
    (openpo_packs_0905.py), so no in-transit box is waiting on this.

WRITE THROUGH .save(), NEVER .update(). The pack is stored twice — the text
field a human types and `pack_quantity_native`, the Decimal that receiving
actually multiplies by. Only clean() derives the second from the first and only
save() calls clean(), so a queryset .update() changes every screen and nothing
that counts. This is the one place the usual advice on this install is reversed.
Each write is then verified by RE-READING the row, because .save() here has
reported success and written nothing before now.

    itq run scripts/pack_fix_0905.py            # dry run, prints the plan
    itq run scripts/pack_fix_0905.py --apply    # write and verify
"""
import argparse
import os
import sys
from decimal import Decimal

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()

from company.models import SupplierPart  # noqa: E402

# part_pk -> (pack, the words in the record that say so)
PLAN = {
    196: (2,   '"Smart Light Dimmer Switch 2-pack" (name)'),
    265: (2,   '"Mini HDMI to HDMI Adapter 2-Pack" (name)'),
    275: (5,   '"Terminal Block Jumper ... Pack of 5" (name)'),
    281: (3,   '"AITRIP 3pcs for Arduino Mini Nano" (name)'),
    363: (2,   '"Smart Light Switch 2-pack" (name)'),
    373: (2,   '"AM FM Antenna Replacement (2-Pack)" (name)'),
    388: (2,   '"Magnetic Base SMA Male MCX Antenna (2-Pack)" (name)'),
    422: (10,  '"yueton Pack of 10 AC 15A 125V ... Fuse Holder" (name)'),
    453: (10,  '"THMOOTHER 10-Pack 3.3FT 1Meter V Shape LED Strip" (name)'),
    459: (25,  '"4.7k Ohm Resistors, 1/4 W, 5% (Pack of 25)" (name)'),
    488: (10,  '"10pcs 275VAC X2 Safety capacitor" (name)'),
    489: (10,  '"10pcs 10D561K Varistor" (name) and "10D561K 10pcs" (SKU)'),
    492: (5,   '".../5PCS" (SKU)'),
    493: (6,   '".../6pcs, 10CC" (SKU) - six 10cc syringes'),
    494: (50,  '"50 PCS Square Fuse 0.5A-10A 250V 392 series" (name)'),
    496: (10,  '"10PCS IPX IPEX U.FL Female Connector" (name)'),
    498: (5,   '".../5PCS-BMP280-5V" (SKU)'),
    502: (100, '"100pcs 1/2W 1% Metal Film Resistor" (name)'),
    503: (2,   '".../with Cable 2PCS" (SKU) and "2PCS with cable, $26.09 total" (note)'),
    543: (10,  '"Carbide Insert ... 10-pack" (name)'),
    580: (10,  '"CCMT 431 Insert, 10-pack" (name)'),
    581: (10,  '"CCGT 432 Insert, 10-pack" (name)'),
    583: (10,  '"Carbide Insert: VBMT 221, 10-pack" (name)'),
    728: (2,   '"Hall Effect Linear Sensor Module for AVR/PIC, 2 pcs" (name)'),
    732: (8,   '".../RPSMA-K, 15cm, 8PCS" (SKU)'),
    760: (100, '"seller colorfulplace888 (Shenzhen) - 100 pcs pack" (note)'),
    788: (5,   '"Brass Tee Compression Fitting 3/16in OD (5 pack)" (name)'),
    791: (2,   '"Screen Printing Squeegee, Silicone Small (2 pc)" (name)'),
    909: (5,   '"5 pcs fabbed on order W2026060711329921" (note)'),
}

ap = argparse.ArgumentParser()
ap.add_argument('--apply', action='store_true', help='write (default is dry run)')
a = ap.parse_args()

changed = already = failed = missing = 0

for pk, (want, why) in sorted(PLAN.items()):
    sps = list(SupplierPart.objects.filter(part__pk=pk))
    if not sps:
        print(f"[MISS ] part {pk}: no supplier part")
        missing += 1
        continue
    if len(sps) > 1:
        # Two supplier rows for one part is a different question (which vendor's
        # pack?) and is not something to guess at 2am. Report, do not write.
        print(f"[SKIP ] part {pk}: {len(sps)} supplier parts, ambiguous — not written")
        missing += 1
        continue
    sp = sps[0]
    have = sp.pack_quantity_native
    if have == Decimal(want):
        print(f"[OK   ] part {pk}: already {want}")
        already += 1
        continue
    print(f"[{'WRITE' if a.apply else 'PLAN '}] part {pk}: {have.normalize():g} -> {want}")
    print(f"         evidence: {why}")
    print(f"         name    : {(sp.part.name if sp.part else '')[:70]}")
    if not a.apply:
        continue

    sp.pack_quantity = str(want)
    sp.save()

    # Verify by RE-READING, not by trusting save(). And check BOTH fields: the
    # text is what every screen shows, native is what receiving multiplies by,
    # and it is entirely possible on this install to end up with one and not
    # the other.
    fresh = SupplierPart.objects.get(pk=sp.pk)
    if fresh.pack_quantity_native == Decimal(want) and \
            Decimal(str(fresh.pack_quantity).strip()) == Decimal(want):
        print(f"         verified: text={fresh.pack_quantity!r} "
              f"native={fresh.pack_quantity_native.normalize():g}")
        changed += 1
    else:
        print(f"         !! FAILED: text={fresh.pack_quantity!r} "
              f"native={fresh.pack_quantity_native}")
        failed += 1

print(f"\n{'APPLIED' if a.apply else 'DRY RUN'}: "
      f"changed {changed}, already correct {already}, "
      f"failed {failed}, skipped {missing}")
if failed:
    sys.exit(1)
