"""Apply canonical ceramic notation, merge the collision, explode EMGTMS 24-value."""
import argparse, os, re, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.contenttypes.models import ContentType
from common.models import Parameter, ParameterTemplate
from part.models import Part, PartCategory
from stock.models import StockItem, StockLocation
from company.models import SupplierPart

ap = argparse.ArgumentParser(); ap.add_argument("--commit", action="store_true")
a = ap.parse_args()
ct = ContentType.objects.get_for_model(Part)
pitch_t = ParameterTemplate.objects.get(name="Lead Pitch")

def canon(pf):
    if pf < 1000: v, u = pf, "pF"
    elif pf < 1_000_000: v, u = pf/1000, "nF"
    else: v, u = pf/1_000_000, "uF"
    return f"{v:.10g}{u}"

EMGTMS = [(10,"10"),(22,"22"),(30,"30"),(47,"47"),(100,"101"),(220,"221"),
          (330,"331"),(470,"471"),(1_000,"102"),(2_200,"222"),(3_300,"332"),
          (4_700,"472"),(6_800,"682"),(10_000,"103"),(22_000,"223"),
          (47_000,"473"),(68_000,"683"),(100_000,"104"),(220_000,"224"),
          (470_000,"474"),(1_000_000,"105"),(2_200_000,"225"),
          (4_700_000,"475"),(10_000_000,"106")]
UNIT = {"pf":1, "nf":1000, "uf":1_000_000}
def parse(n):
    m = re.search(r"Capacitor Ceramic\s+([0-9.]+)\s*(pF|nF|uF)", n, re.I)
    return int(round(float(m.group(1))*UNIT[m.group(2).lower()])) if m else None

by_val = {}
for p in Part.objects.filter(name__istartswith="Capacitor Ceramic", active=True):
    pf = parse(p.name)
    if pf is not None:
        by_val.setdefault(pf, []).append(p)

# ---- rename + move code into description ----
for pf, items in by_val.items():
    for p in items:
        code = (re.search(r"\(([^)]+)\)", p.name) or [None, None])[1]
        new = f"Capacitor Ceramic {canon(pf)}"
        if a.commit:
            if code and f"marking {code}" not in (p.notes or ""):
                p.notes = ((p.notes or "").rstrip() +
                           f"\n\nMarking code **{code}**.").strip()
            p.description = (f"Multilayer ceramic capacitor, {canon(pf)}"
                             + (f", marking {code}" if code else ""))[:250]
            p.name = new[:100]
            p.save()

# ---- merge collisions ----
merged = 0
for pf, items in by_val.items():
    if len(items) < 2: continue
    items.sort(key=lambda p: p.pk)
    keep, rest = items[0], items[1:]
    for f in rest:
        print(f"  merge #{f.pk} -> #{keep.pk}  ({canon(pf)})")
        merged += 1
        if a.commit:
            StockItem.objects.filter(part=f).update(part=keep)
            SupplierPart.objects.filter(part=f).update(part=keep)
            keep.notes = ((keep.notes or "").rstrip() +
                f"\n\nAlso supplied in the SparkFun Beginners Parts Kit "
                f"(was separate part #{f.pk}, merged 2026-08-18 — the catalog "
                "held this value as both 0.1uF and 100nF).").strip()
            keep.save()
            f.active = False
            f.notes = ((f.notes or "").rstrip() +
                f"\n\n**MERGED** into #{keep.pk} {keep.name} — same capacitance "
                "recorded in two notations.").strip()
            f.name = f"{f.name} [merged {f.pk}]"[:100]
            f.save()
    by_val[pf] = [keep]

# ---- explode EMGTMS under LRD ----
lrd = StockLocation.objects.get(name="LRD")
KITN = "Kit - EMGTMS 24-Value Ceramic"
kit = StockLocation.objects.filter(name=KITN).first()
if not kit and a.commit:
    kit = StockLocation.objects.create(name=KITN, parent=lrd,
        description="EMGTMS Y&Z 24 Values 480pcs MLCC kit, 20 pcs per value, "
                    "50V, foot pitch 5.08mm. ASIN B0D2GVNDHY."[:250])
cat = PartCategory.objects.filter(name="Capacitors").first()

created = 0
for pf, code in EMGTMS:
    if pf in by_val:
        if a.commit:
            p = by_val[pf][0]
            p.notes = ((p.notes or "").rstrip() +
                f"\n\nAlso in the EMGTMS 24-value kit at LRD (marking {code}, "
                "20 pcs when new, foot pitch 5.08mm stated). **Lead pitch not "
                "set on this part** — it is also held in the BOJACK kit, whose "
                "pitch is unverified. Check one BOJACK cap against a breadboard "
                "(0.1in holes) before assuming they match.").strip()
            p.save()
        continue
    created += 1
    print(f"  CREATE {canon(pf):<8} (code {code})")
    if a.commit:
        p = Part.objects.create(
            name=f"Capacitor Ceramic {canon(pf)}"[:100], category=cat,
            description=f"Multilayer ceramic capacitor, {canon(pf)}, marking {code}, 50V"[:250],
            notes=(f"Multilayer monolithic ceramic capacitor, **{canon(pf)}**, "
                   f"marking code **{code}**, 50 V.\n\nFrom the EMGTMS Y&Z "
                   "24-value 480pcs kit at LRD — **20 pcs when new**. Card states "
                   "**foot pitch 5.08 mm** for all 24 values. ASIN B0D2GVNDHY."),
            default_location=kit, active=True, component=True, purchaseable=True)
        Parameter.objects.update_or_create(
            model_type=ct, model_id=p.pk, template=pitch_t,
            defaults={"data": "5.08",
                      "note": "Stated on the EMGTMS kit card for all 24 values."})

total = Part.objects.filter(name__istartswith="Capacitor Ceramic", active=True).count()
print(f"\nmerged {merged}, created {created}, ceramic parts now {total}")
print("WROTE" if a.commit else "DRY RUN")
