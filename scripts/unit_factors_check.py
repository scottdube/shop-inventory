"""Assert binscan's pinned unit factors still match InvenTree's own pint.

binscan carries a hardcoded UNIT_FACTORS table because it runs in its own venv
with no pint, and adding a runtime dependency to a phone-facing service to
convert eleven well-known constants is a poor trade. The risk that creates is
DRIFT: two sources of truth for what "8 in" means, and nothing noticing when
they diverge.

They cannot drift by accident -- every factor here is an exact rational by
definition, not a measurement -- but "cannot drift" is exactly the kind of claim
this repo has been wrong about before. So check it instead of believing it.

Run after any InvenTree upgrade.

    itq run scripts/unit_factors_check.py
"""
import os
import re
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from InvenTree.conversion import convert_physical_value       # noqa: E402

APP = os.path.expanduser("~/binscan/app.py")

BASE = {"length": "m", "mass": "g"}

src = open(APP).read()
block = re.search(r"UNIT_FACTORS = \{(.*?)\n\}", src, re.S)
dims = re.search(r"UNIT_DIM = \{(.*?)\n\}", src, re.S)
if not block or not dims:
    print("!! could not find UNIT_FACTORS / UNIT_DIM in", APP)
    raise SystemExit(1)

factors = {k: float(v) for k, v in re.findall(r'"(\w+)":\s*([\d.]+)', block.group(1))}
dimof = dict(re.findall(r'"(\w+)":\s*"(\w+)"', dims.group(1)))
print(f"{len(factors)} factors pinned in {APP}\n")

bad = 0
for unit, pinned in sorted(factors.items()):
    dim = dimof.get(unit)
    if dim not in BASE:
        print(f"  ?? {unit}: no dimension recorded")
        bad += 1
        continue
    truth = float(convert_physical_value(f"1 {unit}", BASE[dim]))
    ok = abs(truth - pinned) < 1e-12
    bad += not ok
    print(f"  {'ok  ' if ok else 'DRIFT'} {unit:3} {dim:6} pinned={pinned:<16.12g} "
          f"pint={truth:.12g}")

print()
if bad:
    print(f"!! {bad} factor(s) disagree with InvenTree's pint — binscan would "
          f"store wrong numbers. Fix binscan/app.py.")
    raise SystemExit(1)
print("all factors agree with InvenTree's pint")
