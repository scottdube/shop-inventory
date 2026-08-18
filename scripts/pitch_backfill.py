"""Derive Lead Pitch for every electrolytic from its recorded body diameter.

Radial electrolytics follow a standard series: diameter fixes pitch. Body
diameter is also the RELIABLE measurement — loose caps have splayed leads, so a
caliper across the leads over-reads. That is what happened with the 6x12
(measured 3 mm, standard says 2.5).

Every derived value carries a Parameter.note saying so, so a derived figure is
never mistaken for a measured one. Scott's two good caliper readings (5x11 at
2 mm) agree with the series exactly, which is the check that it applies here.
"""
import argparse, os, re, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.contenttypes.models import ContentType
from common.models import Parameter, ParameterTemplate
from part.models import Part

# nominal body diameter -> standard lead pitch, mm
SERIES = [(4.0, "1.5"), (5.0, "2.0"), (6.3, "2.5"), (8.0, "3.5"),
          (10.0, "5.0"), (13.0, "5.0"), (18.0, "7.5")]
DERIVED = ("Derived from the standard radial series (body diameter fixes pitch). "
           "NOT measured. Body diameter is the reliable dimension; a caliper "
           "across loose leads over-reads because they splay.")
MEASURED = "Measured with calipers 2026-08-17."

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

ct = ContentType.objects.get_for_model(Part)
body_t = ParameterTemplate.objects.get(name="Body Size")
pitch_t = ParameterTemplate.objects.get(name="Lead Pitch")
CALIPER = {693, 694}          # 5x11 readings that agree with the series
SUPERSEDED = {695}            # 6x12 read as 3 mm; series says 2.5

def pitch_for(dia):
    for d, p in SERIES:
        if dia <= d + 0.4:
            return p
    return "7.5"

rows = []
for p in Part.objects.filter(name__icontains="Capacitor Electrolytic", active=True):
    bp = Parameter.objects.filter(model_type=ct, model_id=p.pk, template=body_t).first()
    if not bp:
        print(f"  #{p.pk}: no body size, skipped"); continue
    m = re.match(r"([0-9.]+)", bp.data)
    if not m:
        print(f"  #{p.pk}: unparseable body '{bp.data}', skipped"); continue
    dia = float(m.group(1))
    val = pitch_for(dia)
    kind = "measured" if p.pk in CALIPER else "derived"
    flag = ""
    if p.pk in SUPERSEDED:
        flag = "  <- was 3 (caliper); superseded by series"
    rows.append((p, bp.data, val, kind, flag))

for p, body, val, kind, flag in sorted(rows, key=lambda r: r[0].pk):
    print(f"  #{p.pk:<4} {p.name[:44]:<44} body {body:<10} pitch {val:<4} {kind}{flag}")
    if a.commit:
        Parameter.objects.update_or_create(
            model_type=ct, model_id=p.pk, template=pitch_t,
            defaults={"data": val,
                      "note": (MEASURED if kind == "measured" else DERIVED)[:250]})

print(f"\n{len(rows)} parts | {'WROTE' if a.commit else 'DRY RUN'}")
