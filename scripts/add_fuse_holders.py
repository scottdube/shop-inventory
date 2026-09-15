#!/usr/bin/env python3
"""Catalogue the inline 5x20 mm fuse holders.

Wire-shelf stock-in, 2026-09-14. Bag label:

    X002OBPIRJ
    10pcs 5x20mm Fuse Holder Inline Screw Type   150pcs
    Quick Blow Glass Tube Fuse   LI0215

THE LABEL DESCRIBES A BUNDLE, and only half of it is in this bag. The ASIN
covers 10 inline holders PLUS 150 glass fuses; what Scott produced is the
holders.

THE OTHER HALF MAY ALREADY BE CATALOGUED, UNCONFIRMED. #1143 is "Fuse Kit,
glass 5x20mm 250V, 15 values, 150 pc (XFFCSEC)" in L2-D2 -- same format, same
count. It was seeded from a PHOTO of that drawer on 2026-08-28 and carries no
ASIN, so nothing links the two records. Against the match: #1143 is branded
XFFCSEC and this bag says LI0215. For it: 150 pieces of 5 x 20 glass fuse in
one purchase is a specific coincidence.

Left as a question for Scott rather than merged. Wrongly linking them would
attach this ASIN to a part whose provenance is a photograph, and wrongly
splitting them puts 300 fuses on the books when 150 were bought.

    itq run scripts/add_fuse_holders.py
    itq run scripts/add_fuse_holders.py --commit
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import Company, SupplierPart  # noqa: E402
from part.models import Part, PartCategory  # noqa: E402

COMMIT = "--commit" in sys.argv
ASIN = "X002OBPIRJ"
NAME = "Fuse Holder, inline 5x20 mm, screw type, pigtail leads"
DESC = ("Inline holder for a 5 x 20 mm glass cartridge fuse. Screw-together "
        "black barrel on red flying leads; the two halves unscrew to change "
        "the fuse. Sold in a bundle of 10 holders plus 150 fuses.")
KEYWORDS = ("fuse holder, inline fuse holder, 5x20, 5 x 20 mm, glass fuse, "
            "cartridge fuse, screw type, pigtail, in-line, LI0215")
NOTES = """Inline 5 x 20 mm fuse holder — a black screw-together barrel on red flying leads. Unscrew the two halves to change the fuse.

**TAKES THE SAME 5 x 20 mm GLASS FUSES AS #1143** (Fuse Kit, 15 values, 150 pc, in L2-D2) and as the PWM controllers' 10 A fuses. Holder and fuse are separate parts on purpose: one is reusable hardware, the other is consumable, and they are drawn on at completely different rates.

**RATING IS NOT MARKED ON THE HOLDER.** Inline holders of this type are typically good for 10 A or so, but nothing on the body says it and the vendor listing does not state it either. The LEAD gauge is the real limit and it is thin — treat these as suitable for small DC loads and low-current mains accessories, not for anything approaching the 30 A the S-360-12 can deliver. If the rating matters for a build, measure the wire and derate rather than trusting the format.

**NOT WEATHERPROOF.** The screw joint is not sealed. Fine inside an enclosure, poor anywhere damp.

## Provenance — and one open question

Bag label: ASIN **X002OBPIRJ**, *"10pcs 5x20mm Fuse Holder Inline Screw Type 150pcs Quick Blow Glass Tube Fuse LI0215"*.

**THAT IS A BUNDLE: 10 holders AND 150 fuses under one ASIN.** Only the holders were in this bag.

**OPEN, 2026-09-14:** whether #1143 — the 150-piece 5 x 20 glass fuse kit in L2-D2 — is the other half of this same purchase. It would fit exactly: same format, same count. But #1143 was seeded from a photograph of that drawer on 2026-08-28, carries no ASIN, and is branded **XFFCSEC** while this bag says **LI0215**. Not merged, because linking them on a guess would attach this ASIN to a part whose only provenance is a photo, and keeping them apart wrongly would put 300 fuses on the books when 150 were bought. Ask Scott."""

cat = PartCategory.objects.filter(pathstring='Electronics/Protection/Fuses').first() \
    or PartCategory.objects.filter(name='Fuses').first()
existing = Part.objects.filter(name=NAME).first()
print(f"category: {cat.pathstring}")
print(f"part:     {'EXISTS' if existing else 'will create'}")

if not COMMIT:
    print("\nDRY RUN — nothing written. Re-run with --commit.")
    sys.exit(0)

p = existing or Part.objects.create(
    name=NAME, description=DESC, category=cat, keywords=KEYWORDS,
    notes=NOTES, active=True, purchaseable=True, component=True)

amazon = Company.objects.filter(name__istartswith="Amazon").first()
if amazon and not SupplierPart.objects.filter(part=p, SKU=ASIN).exists():
    sp = SupplierPart.objects.create(
        part=p, supplier=amazon, SKU=ASIN,
        link=f"https://www.amazon.com/dp/{ASIN}",
        note="BUNDLE: this ASIN is 10 holders PLUS 150 5x20 glass fuses. "
             "pack_quantity 10 counts the HOLDERS only; the fuses are a "
             "separate part and possibly #1143.")
    SupplierPart.objects.filter(pk=sp.pk).update(pack_quantity="10")
    sp.refresh_from_db()
    print(f"supplier part {sp.pk}: {ASIN} pack_quantity={sp.pack_quantity}")

p.refresh_from_db()
print(f"\n#{p.pk} {p.name}")
print(f"   bundle question recorded: {'OPEN, 2026-09-14' in p.notes}")
print(f"   stock rows {p.stock_items.count()}  <- awaiting count + location")
