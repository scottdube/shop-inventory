"""Queue D, 2026-09-04: the single active part with genuinely empty keywords.

pk 1172 is a 2 mOhm SMD current-sense resistor (marking R002) desoldered from an
INA228 breakout. Six months from now Scott will search "shunt" or "current
sense", not "R002" — which is the whole point of the keywords field.

Terms chosen the way section D specifies: the common bench name, abbreviations
AND their expansions (search is substring, so "shunt" does not match
"shunt resistor" the other way round and both are cheap), the marking code, and
the sourcing story, because "salvaged" is how he will remember this one.

NEVER overwrite a non-empty keywords field — it may be Scott's own. Verified by
re-read after save; .save() on this install has reported success and written
nothing before.
"""
import argparse
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part  # noqa: E402

PK = 1172
KW = ("current sense, current sensing, shunt, shunt resistor, sense resistor, "
      "milliohm, mohm, 2 mOhm, 0.002 ohm, R002, low ohm, low value resistor, "
      "SMD resistor, INA228, salvaged")

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

p = Part.objects.filter(pk=PK).first()
if not p:
    sys.exit(f"no part {PK}")
print(f"part {PK}: {p.name}")
print(f"existing keywords: {p.keywords!r}")

if p.keywords:
    sys.exit("=  keywords already set — left alone (may be Scott's own)")

print(f"proposed ({len(KW)} chars of 250): {KW}")
if len(KW) > 250:
    sys.exit("!! over the 250-char field limit")

if not a.commit:
    print("~  DRY RUN, nothing written")
    sys.exit(0)

p.keywords = KW
p.save()

fresh = Part.objects.get(pk=PK)
if fresh.keywords == KW:
    print(f"+  {PK}: keywords written and VERIFIED by re-read")
else:
    sys.exit(f"!! {PK}: save did not stick — row now reads {fresh.keywords!r}")

active = Part.objects.filter(active=True)
empty = (active.filter(keywords__isnull=True) | active.filter(keywords="")).distinct()
print(f"active parts with empty keywords now: {empty.count()}/{active.count()} "
      f"(counting NULL *and* '', which the old closure query did not)")
