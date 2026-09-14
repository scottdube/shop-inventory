#!/usr/bin/env python3
"""Fold the Amazon listing facts into #1202 and correct a guessed spec.

Scott pulled up ASIN B07TZMMZ66 on 2026-09-14. It settles provenance and
fixes a number I had ESTIMATED and written as though it were typical:

    I wrote:  "usually trimmable ... typically about +/-10%
               (so roughly 10.8-13.2 V here). Not verified."
    Listing:  "regulated by 15%, from 10.2V to 13.8V"

The direction of the error matters. I understated the adjustment range, so
anyone trusting my figure would have believed the supply could not reach a
voltage it can in fact reach. A guessed spec presented with a hedge is still
a guessed spec; the hedge does not make it safe to design against.

Confirms the family guess was right: brand SHNITPWR, sold by SNT-POWER --
the same maker as #1160 S-250-24, and the same 1.96 x 1.96 in cross-section.

    itq run scripts/s360_from_listing.py
    itq run scripts/s360_from_listing.py --commit
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import Company, SupplierPart  # noqa: E402
from part.models import Part  # noqa: E402

COMMIT = "--commit" in sys.argv
ASIN = "B07TZMMZ66"

OLD = """**OUTPUT IS USUALLY TRIMMABLE** on these, via a small pot marked V-ADJ, typically about +/-10% (so roughly 10.8–13.2 V here). Not verified on this unit."""

NEW = """**OUTPUT IS TRIMMABLE +/-15%: 10.2 V to 13.8 V.** Stated by the listing (ASIN B07TZMMZ66), so this is the vendor's figure rather than an inference. THREE sets of output channels on the terminal block, all the same rail.

*Correction, 2026-09-14:* this note first said "typically about +/-10%, roughly 10.8-13.2 V", which was a guess dressed as a typical value and it UNDERSTATED the range. Anyone trusting it would have believed the supply could not reach a voltage it can. A hedge does not make a guessed spec safe to design against."""

ADD = """

## Listing facts (ASIN B07TZMMZ66, read 2026-09-14)

Brand **SHNITPWR**, sold by SNT-POWER — the same maker as #1160 S-250-24, and the same 1.96 x 1.96 in cross-section, so the family guess made from the case label was right.

| | |
|---|---|
| Purchased | **2023-08-07**, size 30 A |
| Dimensions | 1.96 D x 4.41 W x 1.96 H in, surface mount |
| Weight | 1.68 lb |
| Protection | overload, over-voltage, thermal, short-circuit cut-off |
| Certification | FCC, CE, RoHS |

**THE ASIN IS A SIZE VARIANT — it covers 10A / 15A / 20A / 30A under one listing** (this is the 30 A). As with the linear actuator, the ASIN alone will reorder the wrong part; the current rating has to travel with it.

**"NEVER OVERLOAD" is the vendor's own wording.** It supplies anything up to 30 A happily, but a load drawing more than 30 A gets 30 A and, in their words, the supply "will be damaged soon". The protection circuits are a backstop, not a licence to size it tight."""

p = Part.objects.get(pk=1202)
print(f"#{p.pk} {p.name}")
print(f"  correction anchor found: {OLD in (p.notes or '')}")

if not COMMIT:
    print("\nDRY RUN — nothing written. Re-run with --commit.")
    sys.exit(0)

assert OLD in p.notes, "anchor missing — refusing to guess"
Part.objects.filter(pk=1202).update(notes=p.notes.replace(OLD, NEW, 1) + ADD)
p.refresh_from_db()

amazon = Company.objects.filter(name__istartswith="Amazon").first()
if amazon and not SupplierPart.objects.filter(part=p, SKU=ASIN).exists():
    sp = SupplierPart.objects.create(
        part=p, supplier=amazon, SKU=ASIN,
        link=f"https://www.amazon.com/dp/{ASIN}",
        note="Size variant listing: 10A / 15A / 20A / 30A share this ASIN. "
             "This SKU means the 30 A / 360 W unit.")
    print(f"  supplier part {sp.pk}: {ASIN}")

print(f"  trim range corrected: {'10.2 V to 13.8 V' in p.notes}")
print(f"  stale +/-10% claim gone: {'typically about +/-10%, roughly 10.8' not in p.notes}")
print(f"  listing section added: {'Listing facts' in p.notes}")
print(f"  stock rows {p.stock_items.count()}  <- still awaiting count + location")
