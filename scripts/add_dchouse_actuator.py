#!/usr/bin/env python3
"""Catalogue the DC HOUSE mini linear actuator found on the wire shelves.

2026-09-14 bench session. Scott produced the unit; the label reads
LA-T8-12-50-30/85-20. It was in NO form in InvenTree -- Scott: "should have
been in the amazon import."

IDENTIFICATION. Scott pulled up the listing, ASIN B07ZJ4B272, which says
"Last purchased Jun 22, 2023, Size: 1.2 inch". Every number on the listing
matches the label on the part, so this is an identification and not a guess:

    30 mm stroke   = 1.2 in          50 mm/s = 1.97 in/sec
    85 mm retracted (the /85)        20 N    = 4.5 lbs

A WRONG CLAIM WAS MADE AND CORRECTED ON THE WAY HERE. A mail search surfaced
"DC HOUSE 4 Inch Linear Actuator" and I reported that as a DIFFERENT, second
actuator. It was a MARKETING email's subject line, not a purchase. There is
one actuator, the 1.2 inch. Reading a recommendation subject as an order is
the same error shape as the PPK2 hunt: mail is indexed on what a vendor wants
to sell, not on what was bought.

THE 10% DUTY CYCLE IS THE HEADLINE SPEC. At 50 mm/s a full 30 mm stroke takes
0.6 s, so 10% means roughly one stroke then nine stroke-times idle. Anything
that cycles this continuously will cook it. 20 N is also light -- about 2 kg
of push. Both go in the notes because they are what makes it the wrong part
for a job, and neither is visible on the part itself beyond a cryptic "10%".

    itq run scripts/add_dchouse_actuator.py
    itq run scripts/add_dchouse_actuator.py --commit
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

NAME = "DC HOUSE Mini Linear Actuator, 12V, 30 mm stroke, 20 N (LA-T8)"
ASIN = "B07ZJ4B272"
DESC = ("DC HOUSE mini electric linear actuator. 12 VDC, 30 mm (1.2 in) stroke, "
        "50 mm/s, 20 N (4.5 lb) max load, IP54. Retracted 85 mm, extended 115 mm. "
        "Model LA-T8-12-50-30/85-20.")
KEYWORDS = ("linear actuator, micro actuator, push rod, LA-T8, DC HOUSE, 12V, "
            "30mm stroke, 20N, window opener, damper")
NOTES = """DC HOUSE Mini Electric Linear Actuator, model LA-T8-12-50-30/85-20.

THE MODEL NUMBER DECODES, which is why the unit could be identified from the label alone:

    LA-T8   T8 lead screw       12   12 VDC
    50      50 mm/s             30   30 mm stroke
    85      85 mm retracted     20   20 N thrust

**10% DUTY CYCLE — this is the spec that decides whether it suits a job.** A full 30 mm stroke takes about 0.6 s at 50 mm/s, so 10% duty means roughly one stroke followed by nine stroke-times of rest. It is built to move something occasionally: a damper, a vent, a window. Anything that cycles continuously will overheat it. The part itself says only "10%" and nothing about what that governs.

**20 N is LIGHT — about 2 kg of push.** Extended length 115 mm, retracted 85 mm. Internal limit switches stop it at each end ("free stop" in the listing), so it does not need external end stops, but it also has NO position feedback: it is open-loop, fully-out or fully-in, with no way to command an intermediate position and know it got there.

PROVENANCE. Amazon ASIN B07ZJ4B272, last purchased 2023-06-22 in the 1.2 inch size. Confirmed 2026-09-14 from the listing page, whose spec block matches the physical label on every figure. The listing sells five stroke lengths (0.4 / 0.8 / 1.2 / 2 / 4 in) under ONE ASIN as a size variant, so the ASIN alone does not identify the stroke -- record the size with it or the next person orders the wrong one.

CATALOGUED LATE. It was not in InvenTree in any form; Scott: "should have been in the amazon import." Whether the import has a wider gap is an open question, not a settled one -- see docs/OPEN.md."""

cat = PartCategory.objects.get(pk=20)   # flat Electromechanical, 18 parts
existing = Part.objects.filter(name=NAME).first()
print(f"category: {cat.pathstring}")
print(f"part:     {'EXISTS' if existing else 'will create'}  {NAME}")

if not COMMIT:
    print("\nDRY RUN — nothing written. Re-run with --commit.")
    print("NOTE: no stock row is created here; count and location come from Scott.")
    sys.exit(0)

if existing:
    p = existing
else:
    p = Part.objects.create(name=NAME, description=DESC, category=cat,
                            keywords=KEYWORDS, notes=NOTES, active=True,
                            purchaseable=True, component=True)
    print(f"created part #{p.pk}")

amazon = Company.objects.filter(name__istartswith="Amazon").first()
sp = SupplierPart.objects.filter(part=p, SKU=ASIN).first()
if not sp and amazon:
    sp = SupplierPart.objects.create(
        part=p, supplier=amazon, SKU=ASIN,
        link=f"https://www.amazon.com/dp/{ASIN}",
        note="1.2 inch / 30 mm size variant. The ASIN covers five stroke "
             "lengths; this SKU means the 30 mm one.")
    print(f"created supplier part {sp.pk}  {amazon.name} / {ASIN}")

p.refresh_from_db()
print(f"\n#{p.pk} {p.name}")
print(f"   category  {p.category.pathstring}")
print(f"   notes     {len(p.notes)} chars, duty-cycle warning present: {'10% DUTY CYCLE' in p.notes}")
print(f"   stock rows {p.stock_items.count()}  <- awaiting count + location from Scott")
