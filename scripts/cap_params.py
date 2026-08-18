"""Body size and lead pitch as real Parameters, not text buried in a name.

Lead pitch is what decides whether a part drops into the board, so KiCad and any
BOM check need it as structured, filterable data. Body size is backfilled from
the name for every sized electrolytic; LEAD PITCH IS SET ONLY WHERE SCOTT
MEASURED IT. Kit parts keep it blank - an assumed pitch is exactly the failure
this whole exercise is about, and blank is honest where a guess is not.

InvenTree 1.5 note: parameters live in common.models as generic
Parameter / ParameterTemplate keyed by (model_type, model_id). The old
part.models.PartParameter is gone.
"""
import argparse, os, re, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.contenttypes.models import ContentType
from common.models import Parameter, ParameterTemplate
from part.models import Part

MEASURED_PITCH = {693: "2", 694: "2", 695: "3"}
SIZED = re.compile(r"\(([0-9.]+ ?x ?[0-9.]+)\s*(?:mm)?\)\s*$")

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

ct = ContentType.objects.get_for_model(Part)


def template(name, units, desc):
    t = ParameterTemplate.objects.filter(name=name).first()
    if t:
        print(f"  template exists  {name}")
        return t
    print(f"  template CREATE  {name} ({units})")
    if not a.commit:
        return None
    return ParameterTemplate.objects.create(name=name, units=units,
                                            description=desc, model_type=ct)


def setp(part, tmpl, value):
    if not tmpl or not a.commit:
        return
    Parameter.objects.update_or_create(
        model_type=ct, model_id=part.pk, template=tmpl,
        defaults={"data": value})


body = template("Body Size", "mm", "Radial can diameter x height")
pitch = template("Lead Pitch", "mm",
                 "Centre-to-centre lead spacing - the dimension that fixes the "
                 "PCB footprint. Blank means NOT MEASURED; do not assume.")

nb = np = 0
for p in Part.objects.filter(name__icontains="Capacitor Electrolytic", active=True):
    m = SIZED.search(p.name)
    if m:
        setp(p, body, m.group(1).replace(" ", ""))
        nb += 1
    if p.pk in MEASURED_PITCH:
        print(f"  pitch  #{p.pk}  {p.name:<40} = {MEASURED_PITCH[p.pk]} mm  (measured)")
        setp(p, pitch, MEASURED_PITCH[p.pk])
        np += 1

print(f"\n{'WROTE' if a.commit else 'DRY RUN'}")
print(f"  Body Size set on:  {nb}")
print(f"  Lead Pitch set on: {np}  (measured only - kit parts deliberately blank)")
