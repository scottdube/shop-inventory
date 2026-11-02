"""Rename part 427 to the short form so its label shows the values, 2026-11-02.

The Amazon title ("...5 Wire for Compatible with New Tech 4.5uf+5uf+6uf...")
wraps off a 62 mm label before the capacitance, the one thing that matters at
the drawer. Takes the name the retired duplicate (7) used; the full vendor title
stays in the description as "orig:".

    itq run scripts/fan_cap_rename_1102.py [--commit]
"""
import argparse
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part  # noqa: E402

NEW = "Podoy Ceiling Fan Capacitor CBB61 5-Wire 4.5+5+6uF 250VAC"
ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()
p = Part.objects.get(pk=427)
assert p.name.startswith("Podoy Ceiling Fan Capacitor CBB61 5 Wire"), p.name
assert p.description.startswith("orig: Podoy"), p.description
print(f"{p.name!r} -> {NEW!r}")
if not a.commit:
    raise SystemExit("DRY RUN - add --commit")
Part.objects.filter(pk=427).update(name=NEW)
p.refresh_from_db()
print("ALL VERIFIED" if p.name == NEW else f"NOT VERIFIED: {p.name!r}")
