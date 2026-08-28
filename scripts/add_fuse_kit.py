"""XFFCSEC 150 pc 5x20 glass fuse kit into L2-D2.

Scott 2026-08-28: "fuses L2D2". A real home, not a parking spot — no "for now"
attached, so default_location is set, unlike the L1-D2 hardware kits.

ONE PART, NOT FIFTEEN. The electrolytic kits in this catalogue were seeded as a
part per value because values get consumed one at a time and a kit row cannot
tell you the 470uF bag is empty. The same argument applies to fuses and this is
NOT doing it — deliberately, because splitting by division is what put wrong
values on the shelf twice before. If a value gets drawn on, split it then, from
a count of that compartment.

    itq run scripts/add_fuse_kit.py            # dry run
    itq run scripts/add_fuse_kit.py --commit
"""
import argparse, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part, PartCategory                       # noqa: E402
from stock.models import StockItem, StockLocation               # noqa: E402

BIN, QTY = "L2-D2", 150
NAME = "Fuse Kit, glass 5x20mm 250V, 15 values, 150 pc (XFFCSEC)"
DESC = ("XFFCSEC assortment of 5 x 20 mm glass cartridge fuses, 250 V, 15 "
        "values at 10 pieces each: 0.25 0.5 1 1.5 2 2.5 3 4 5 6 6.3 7 8 10 20 A.")
NOTES = (
 "[ESTIMATE] 150 is the PRINTED PACK FIGURE off the box lid — 15 values at 10 "
 "each. Nobody counted it and no stocktake_date is set, so it stays on the "
 "never-counted report.\n\n"
 "VALUES: 0.25, 0.5, 1, 1.5, 2, 2.5, 3, 4, 5, 6, 6.3, 7, 8, 10, 20 A. All 250 V, "
 "all 5 x 20 mm.\n\n"
 "SEEDED AS ONE PART, NOT FIFTEEN, AND THAT IS A DEFERRAL NOT A DECISION. The "
 "electrolytic kits here were split into a part per value, because a single kit "
 "row cannot tell you one compartment is empty. Fuses have the same problem. It "
 "is not split now because splitting by DIVISION — assuming ten of each because "
 "the lid says so — is exactly what put wrong values on the shelf twice before. "
 "Split a value when it is actually drawn on, from a count of that compartment.\n\n"
 "BLOW CHARACTERISTIC IS UNSTATED. The box says nothing about fast-blow versus "
 "slow-blow (T versus F), and it matters: a slow-blow where a fast-blow belongs "
 "will let a fault run, and a fast-blow in a motor or transformer circuit will "
 "nuisance-trip on inrush. Read the end cap of the individual fuse before "
 "fitting one to anything that matters.\n\n"
 "COVERS THE PWM CONTROLLERS. #1138 (B3-R5C4) is fused at 10 A in this exact "
 "5 x 20 format, so those boards now have an in-house spare. Note the caveat on "
 "that part: 10 A is a THERMAL figure set by small heatsinks, not a silicon one. "
 "Do not reach into this box for a 20 A to 'fix' a board that keeps blowing.\n\n"
 "Distinct from #494, the 392-series SQUARE fuses in A3-R7C3 — different form "
 "factor entirely, they do not interchange.")

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

loc = StockLocation.objects.get(name__iexact=BIN)
if Part.objects.filter(name=NAME).exists():
    sys.exit("!! already exists")
cat = (PartCategory.objects.filter(name__iexact="Power").first()
       or PartCategory.objects.filter(name__icontains="power").first())
print(f"{NAME}\n  -> {loc.pathstring}, qty {QTY} [ESTIMATE], no stocktake, cat {cat}")
if not a.commit:
    raise SystemExit("\nDRY RUN — add --commit")

p = Part.objects.create(name=NAME, description=DESC, category=cat,
                        purchaseable=True, component=True, active=True)
s = StockItem.objects.create(part=p, location=loc, quantity=QTY, notes=NOTES)
Part.objects.filter(pk=p.pk).update(notes=NOTES, default_location=loc)
f = StockItem.objects.get(pk=s.pk)
assert float(f.quantity) == QTY and f.location_id == loc.pk, "row did not stick"
assert f.stocktake_date is None, "something stamped a stocktake date"
assert Part.objects.get(pk=p.pk).default_location_id == loc.pk, "home did not stick"
if not (loc.description or "").strip():
    StockLocation.objects.filter(pk=loc.pk).update(
        description="FUSES — glass cartridge assortment kits. Currently the "
        "XFFCSEC 5 x 20 mm 250 V box, 15 values. Not the 392-series square fuses, "
        "which live with the mains-side protection in A3-R7C3.")
    assert "FUSES" in StockLocation.objects.get(pk=loc.pk).description
print(f"\nOK  part #{p.pk}, stock #{f.pk} qty={float(f.quantity):g} in {loc.name}, "
      f"no stocktake")
