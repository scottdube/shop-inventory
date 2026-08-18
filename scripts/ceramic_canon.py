"""Canonical ceramic notation, dedup, then explode the EMGTMS 24-value kit.

Scott's rule: pF below 1 nF, nF from 1 nF to 999 nF, uF at 1 uF and above.
That makes one capacitance produce exactly one name.

The marking CODE comes OUT of the name and into the description. It has to:
the same 10 pF is stamped `100` by SparkFun and `10` by EMGTMS, so a code in
the name reintroduces the very collision the notation rule removes. Codes stay
searchable because InvenTree's search covers description.

Pitch: the EMGTMS card states 5.08 mm for all 24 values. That is applied ONLY to
values unique to that kit. Values ALSO held in the BOJACK kit get no pitch yet —
BOJACK's pitch is unverified (a breadboard go/no-go settles it), and asserting an
unmeasured footprint on a shared value is exactly the failure this project has a
rule against.
"""
import argparse, os, re, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.contenttypes.models import ContentType
from common.models import Parameter, ParameterTemplate
from part.models import Part
from stock.models import StockItem, StockLocation

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

def canon(pf):
    """picofarads -> canonical display string"""
    if pf < 1000:
        v = pf
        unit = "pF"
    elif pf < 1_000_000:
        v = pf / 1000
        unit = "nF"
    else:
        v = pf / 1_000_000
        unit = "uF"
    s = f"{v:.10g}"
    return f"{s}{unit}"

# EMGTMS 24-value card, transcribed: (picofarads, printed code)
EMGTMS = [(10,"10"),(22,"22"),(30,"30"),(47,"47"),(100,"101"),(220,"221"),
          (330,"331"),(470,"471"),(1_000,"102"),(2_200,"222"),(3_300,"332"),
          (4_700,"472"),(6_800,"682"),(10_000,"103"),(22_000,"223"),
          (47_000,"473"),(68_000,"683"),(100_000,"104"),(220_000,"224"),
          (470_000,"474"),(1_000_000,"105"),(2_200_000,"225"),
          (4_700_000,"475"),(10_000_000,"106")]

UNIT = {"pf": 1, "nf": 1000, "uf": 1_000_000}
def parse(name):
    m = re.search(r"Capacitor Ceramic\s+([0-9.]+)\s*(pF|nF|uF)", name, re.I)
    return int(round(float(m.group(1)) * UNIT[m.group(2).lower()])) if m else None

# ---------- 1. rename existing to canonical, code -> description ----------
print("== 1. canonical rename ==")
existing = {}
for p in Part.objects.filter(name__istartswith="Capacitor Ceramic", active=True):
    pf = parse(p.name)
    if pf is None:
        print(f"  #{p.pk}: cannot parse '{p.name}', skipped"); continue
    code = (re.search(r"\(([^)]+)\)", p.name) or [None, None])[1]
    new = f"Capacitor Ceramic {canon(pf)}"
    if new != p.name:
        print(f"  #{p.pk:<4} {p.name:<40} -> {new}   (code {code} -> description)")
    existing.setdefault(pf, []).append((p, code, new))

# ---------- 2. collisions ----------
print("\n== 2. collisions after rename ==")
dupes = {pf: v for pf, v in existing.items() if len(v) > 1}
for pf, items in sorted(dupes.items()):
    keep = items[0][0]
    print(f"  {canon(pf)}: " + " + ".join(f"#{p.pk}" for p, _, _ in items)
          + f"  -> keep #{keep.pk}")

# ---------- 3. what the EMGTMS kit adds ----------
print("\n== 3. EMGTMS 24-value kit ==")
new_vals = [(pf, c) for pf, c in EMGTMS if pf not in existing]
shared = [(pf, c) for pf, c in EMGTMS if pf in existing]
print(f"  values already in catalog: {len(shared)}  -> {', '.join(canon(p) for p,_ in shared)}")
print(f"  NEW values to create:      {len(new_vals)} -> {', '.join(canon(p) for p,_ in new_vals)}")
print(f"\n  Lead Pitch 5.08 will be set on the {len(new_vals)} EMGTMS-only values.")
print(f"  The {len(shared)} shared values get NO pitch — BOJACK's is unverified.")
print(f"\n  ceramic values after this: {len(existing) - len(dupes) + len(new_vals)}")
print(f"\n{'--commit to apply' if not a.commit else 'COMMIT MODE'}")
