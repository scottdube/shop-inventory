"""Give the FR-301 filter set a reorder identity.

Scott, 2026-08-24: *"we need to come up with a part number for it... there's no
part number because it was part of the gun set, but we need to be able to recall
it and reorder it after we use these up."*

Researched from Hakko's own catalogue (hakko.co.uk FR-301 replacement parts):

    A1033   Ceramic paper filter-L, 10-pack   -- DISCONTINUED
    A5044   Ceramic paper filter-L, 10-pack   -- the current replacement for A1033
    A5031   Filter holder                     -- CANDIDATE for the metal cup, UNCONFIRMED
    B5104   Pre-filter
    B5194   Filter pipe

**What is confident and what is not, kept separate on purpose.** The white discs
being the ceramic paper filter is solid -- it is the only consumable of that
shape in the tool. Which of A1033/A5044 to order is solid: A5044 supersedes.
The METAL CUP is not identified. A5031 "filter holder" is the best candidate on
the parts list and nobody has checked it against the object, so it is recorded
as a candidate and not as the answer. A confident wrong MPN gets reordered and
arrives looking correct.

IPN convention note: every other IPN in this catalogue is an Amazon ASIN,
because the importer seeded them. This part has no ASIN -- it was never
separately ordered -- so its IPN is the MANUFACTURER's number, which is the
thing you would actually reorder by. Deliberate deviation, recorded here so the
next person does not "fix" it.

hakkousa.com answered 403 to a plain fetch, which is the documented
fingerprinting behaviour, not an outage. Not chased: the UK catalogue is
authoritative and a browser session is disproportionate for a part number.

    itq run scripts/filter_partnumber.py
    itq run scripts/filter_partnumber.py --commit
"""
import argparse
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part            # noqa: E402
from stock.models import StockItem      # noqa: E402

PK = 1084
IPN = "A5044"
DESC = ("Ceramic paper filters + holder for the FR-301 desoldering gun. Reach "
        "for it when the gun stops pulling solder — a clogged filter looks "
        "exactly like a dead pump. Reorder as Hakko A5044 (10-pack), which "
        "supersedes A1033.")
KW = ("fr-301, fr301, fr-4101, filter, ceramic paper filter, filter pad, "
      "A5044, A1033, A5031, desoldering filter, hakko, no suction, clogged, "
      "lost suction, spare")
NOTES = """## Reorder

**Hakko A5044** — Ceramic paper filter-L, sold in **10-packs**. Supersedes
**A1033**, which is discontinued. Note the reorder unit: one order buys ten
filters, while this stock row counts one SET that came with the gun.

Sourced from Hakko's own FR-301 replacement-parts catalogue on 2026-08-24, not
from a reseller listing. `hakkousa.com` returned 403 to a plain fetch — the
documented fingerprinting behaviour, not an outage — and was not chased,
because the manufacturer's own catalogue already answers the question.

## What is NOT confirmed

The **metal cup** in the bag is not identified. `A5031` (filter holder) is the
best candidate on Hakko's FR-301 parts list and **nobody has checked it against
the object**. It is recorded as a candidate, never as the answer — a confident
wrong MPN gets reordered and arrives looking correct.

Cheap way to settle it, and worth doing before any reorder: **measure the white
disc's diameter** and compare against the A5044 spec, and compare the metal cup
against Hakko's A5031 image. Both are a ruler and a minute, which beats
reasoning about it.

## Provenance

Came in the box with the **FR-301 gun (#474)**. Never separately ordered, so it
sits on no purchase order *by design* — a sweep reconciling parts against
orders should find this unmatched and must not read that as a fabricated record.

## When you reach for it

The gun losing suction reads as a dead pump. It is usually the filter. Swap the
pad first, not last — running it clogged drives solder residue further into the
barrel, which is the expensive version of this problem.
"""

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

p = Part.objects.get(pk=PK)
print(f"#{p.pk} {p.name[:60]}")
print(f"   IPN  {p.IPN!r} -> {IPN!r}")
print(f"   desc {len(DESC)} chars (limit 250)")
assert len(DESC) <= 250, f"description is {len(DESC)} chars"

clash = Part.objects.filter(IPN=IPN).exclude(pk=PK)
if clash.exists():
    print(f"!! IPN {IPN} already used by {[x.pk for x in clash]}")
    raise SystemExit(1)

if not a.commit:
    print("\nDRY RUN — add --commit")
    raise SystemExit

Part.objects.filter(pk=PK).update(IPN=IPN, description=DESC, keywords=KW,
                                  notes=NOTES)
f = Part.objects.get(pk=PK)
assert f.IPN == IPN and f.description == DESC and f.keywords == KW
assert "A5044" in f.notes and "not identified" in f.notes
print(f"\nOK  #{PK} IPN={f.IPN}  desc/keywords/notes written and verified")
for s in f.stock_items.all():
    print(f"    stock #{s.pk} qty={float(s.quantity):g} @ {s.location.name} "
          f"stocktake={s.stocktake_date}")
