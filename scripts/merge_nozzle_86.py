"""Merge #86 into #213 — the 1.3mm N61-06 nozzle, duplicated at import.

The 0.8mm sibling had the identical pair and was cleaned up on import day:
#214 (raw) retired into #87 (rich). The 1.3mm twin was missed in that same
pass — same product family, same order, same day.

**The surviving pk goes the OTHER way here, and that is deliberate.** The rule
is keep the record carrying the EVIDENCE, not the prettier name and not the
lower pk:

    #86    good name, good keywords, and nothing else.
           No IPN, no supplier part, no image, no purchase history.
    #213   IPN B07DMWBRB9, a SupplierPart, an image, and the Amazon purchase
           history ($14.25, 2026-07-13) — under a name the importer wrote.

A name is one string to retype. An image, a supplier link and a purchase
record are attachments and relations, and moving those is where a merge goes
wrong. So #213 survives and takes #86's name; #86 retires.

Neither part holds stock and neither appears on a PO line, so nothing points at
the retiring pk. Verified in the dry run before anything is written.

Retirement follows the #214 form exactly so one query finds every merge:
active=False, and the description PREFIXED "MERGED into part #N (name)."

    itq run scripts/merge_nozzle_86.py
    itq run scripts/merge_nozzle_86.py --commit
"""
import argparse
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part                        # noqa: E402

DEAD, LIVE = 86, 213
NEW_NAME = "Hakko Desoldering Nozzle 1.3mm N61-06 S-Type (FR-301/FR-4101)"

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

dead = Part.objects.get(pk=DEAD)
live = Part.objects.get(pk=LIVE)

# Nothing may point at the part being retired. A merge that strands stock or a
# PO line is how the "PO attached to the twin" failure happened on 08-21.
problems = []
for label, qs in (("stock rows", dead.stock_items.all()),
                  ("supplier parts", dead.supplier_parts.all())):
    if qs.exists():
        problems.append(f"#{DEAD} still has {qs.count()} {label}")
for sp in dead.supplier_parts.all():
    if sp.purchase_order_line_items.exists():
        problems.append(f"#{DEAD} supplier part {sp.SKU} is on a PO line")
if dead.get_descendants().exists():
    problems.append(f"#{DEAD} has variant children")

print(f"RETIRE  #{DEAD}  {dead.name}")
print(f"        active={dead.active} IPN={dead.IPN!r} image={'yes' if dead.image else 'NO'}")
print(f"        stock={dead.stock_items.count()} suppliers={dead.supplier_parts.count()}")
print(f"KEEP    #{LIVE}  {live.name}")
print(f"        active={live.active} IPN={live.IPN!r} image={'yes' if live.image else 'NO'}")
print(f"        stock={live.stock_items.count()} suppliers={live.supplier_parts.count()}")
print(f"\nrename  #{LIVE} -> {NEW_NAME!r}")

# Union the keyword sets rather than overwriting: #86 carries '1.3mm' and
# #213 carries 'solder sucker', and a search should keep finding both.
# Case-insensitive dedupe, first spelling wins. A raw union keeps both
# 'FR-301' and 'fr-301', which is not two search terms -- it is one term and a
# typo, and a keyword list that looks careless stops being trusted.
seen, kws = {}, []
for src in (live.keywords or "", dead.keywords or ""):
    for k in (x.strip() for x in src.split(",")):
        if k and k.lower() not in seen:
            seen[k.lower()] = k
            kws.append(k)
NEW_KW = ", ".join(kws)
print(f"keywords -> {NEW_KW}")

if problems:
    print("\n!! REFUSING:")
    for p in problems:
        print("   " + p)
    raise SystemExit(1)

if not a.commit:
    print("\nDRY RUN — add --commit")
    raise SystemExit

# .save() has reported success and written nothing on this install. Queryset
# update, then re-read every field from a fresh fetch.
Part.objects.filter(pk=LIVE).update(name=NEW_NAME, keywords=NEW_KW)
fresh = Part.objects.get(pk=LIVE)
assert fresh.name == NEW_NAME, f"name did not stick: {fresh.name!r}"
assert fresh.keywords == NEW_KW, "keywords did not stick"
print(f"\nOK  #{LIVE} renamed and keywords merged")

marker = f"MERGED into part #{LIVE} ({NEW_NAME}). "
if not (dead.description or "").startswith("MERGED into"):
    Part.objects.filter(pk=DEAD).update(active=False,
                                        description=marker + (dead.description or ""))
    fresh_dead = Part.objects.get(pk=DEAD)
    assert fresh_dead.active is False, "still active"
    assert fresh_dead.description.startswith(marker), "marker did not stick"
    print(f"OK  #{DEAD} retired: active=False, description marked")
else:
    print(f"--  #{DEAD} already carries a MERGED marker")
