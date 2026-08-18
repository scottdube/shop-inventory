"""Record Scott's caliper measurements on the three SparkFun-sourced electrolytics.

These are the loose-bag caps: the values match the SparkFun kit list exactly, and
all three measure a different body from the kit parts of the same value - which
is why they would not fit the kit compartments. Measured, so the UNVERIFIED flag
comes off and the footprint goes into the name.
"""
import argparse, os, re, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part

MEASURED = {693: "5x11", 694: "5x11", 695: "6x12"}

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

for pk, size in MEASURED.items():
    p = Part.objects.filter(pk=pk).first()
    if not p:
        print(f"  #{pk}: missing")
        continue
    if "(" in p.name:
        print(f"  #{pk}: already sized as {p.name}")
        continue
    new = f"{p.name} ({size})"
    print(f"  #{pk}  {p.name:<36} -> {new}")
    if a.commit:
        notes = re.sub(r"\n*\*\*BODY SIZE UNVERIFIED\.\*\*.*$", "", p.notes or "",
                       flags=re.S).strip()
        p.notes = (notes + f"\n\nBody measured {size} mm with calipers 2026-08-17. "
                   "Differs from the kit part of the same value — these would not "
                   "fit the kit compartment, which is how the difference surfaced.")
        p.name = new[:100]
        p.save()

print(f"\n{'WROTE' if a.commit else 'DRY RUN'}")
