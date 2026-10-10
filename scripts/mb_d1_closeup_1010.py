"""MB-D1 close-up photo, 2026-10-10, settles three of the open D1 items, plus
Scott's answers on D4 block counts and the CR2032 card.

  - aluminium ring stamped "NO. 25R THE L.S. STARRETT CO. ATHOL MASS" = Starrett
    25R contact point set (14 points, #4-48, AGD; confirmed on starrett.com).
    Nothing on file -> CREATE in MB-D1.
  - triangular leaf gauge "U.S. 60deg 4-84" = Starrett 472 (4-84 TPI, 51 leaves,
    locks at both ends -- distributor listings). The face shows no maker; it
    matches the only US pitch gauge on file, SI #1048 in Unfiled, so MOVE it.
  - straight leaf gauge "METRISCH 60" = metric screw pitch gauge, maker and
    range not visible. Nothing on file -> CREATE without a range.
  - two green-handled rods (1" and 2", "No. 167-...") are the Mitutoyo
    micrometer standards and the hook spanners belong with the 103-922 set
    (part #461, sold "with Standards"). Not separate parts -- noted on #461.
  - D4 blocks: Scott confirmed 2 x 2-4-6 and 4 x 1-2-3; [ESTIMATE] dropped.
  - CR2032 card: Scott said no, not recorded.

    itq run scripts/mb_d1_closeup_1010.py [--commit]
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part, PartCategory  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

COMMIT = "--commit" in sys.argv
MEAS = PartCategory.objects.get(pk=47); assert MEAS.pathstring == "Tooling/Measuring"
D1 = StockLocation.objects.get(name="MB-D1", parent__pk=381)
SRC = "Filed 2026-10-10 from Scott's close-up photo of Metrology Bench drawer 1."
NEW = [
    ("Starrett 25R Contact Point Set, 14 pc",
     "Dial indicator contact points on an aluminium ring: 1/4 in standard, 9 special forms, "
     "shock-absorbing anvil, 1/2, 3/4, 1 in long points; #4-48 thread, AGD",
     "Starrett, 25R, contact point, indicator point, dial indicator, #4-48, AGD",
     "Ring stamped 'NO. 25R THE L.S. STARRETT CO. ATHOL MASS U.S.A.'. Contents per "
     "starrett.com 25R listing; the photo does not show all 14 present."),
    ("Metric Screw Pitch Gage, 60 deg (maker not read)",
     "Metric 60 deg thread pitch gauge, straight leaf case",
     "pitch gauge, pitch gage, screw pitch, thread gauge, metric, metrisch",
     "Case reads 'METRISCH 60' only; maker and pitch range not visible. Rename once read."),
]

s1048 = StockItem.objects.select_related("part", "location").get(pk=1048)
assert s1048.part_id == 1361, s1048.part_id
print(f"MOVE SI #1048 {s1048.part.name} {s1048.location.name} -> {D1.name}")
for name, *_ in NEW:
    ex = Part.objects.filter(name=name).first()
    print(f"{'EXISTS' if ex else 'CREATE'} {name}" + (f" (#{ex.pk})" if ex else ""))
for si in (1120, 1121):
    print(f"CONFIRM SI #{si}: {StockItem.objects.get(pk=si).notes}")
if not COMMIT:
    sys.exit("\nDRY RUN -- add --commit")

StockItem.objects.filter(pk=1048).update(location=D1)
Part.objects.filter(pk=1361).update(default_location=D1)
p472 = Part.objects.get(pk=1361)
if "4-84" not in (p472.description or ""):
    Part.objects.filter(pk=1361).update(
        description="Screw pitch gage, 4-84 TPI, 51 leaves, 60 deg, locks at both ends",
        keywords=((p472.keywords or "") + ", pitch gauge, screw pitch, thread gauge, 4-84 TPI, 60 deg").strip(", "))
assert StockItem.objects.get(pk=1048).location_id == D1.pk
assert Part.objects.get(pk=1361).default_location_id == D1.pk

for name, desc, kw, note in NEW:
    p = Part.objects.filter(name=name).first()
    if not p:
        assert len(name) <= 100 and len(desc) <= 250 and len(kw) <= 250
        p = Part(name=name, description=desc, keywords=kw, category=MEAS, component=False,
                 purchaseable=True, assembly=False, default_location=D1,
                 notes=f"{SRC} {note}\n\nPurchase history unknown; no PO, no price.")
        p.save(); p.refresh_from_db()
        assert p.category_id == MEAS.pk and p.default_location_id == D1.pk
    if not StockItem.objects.filter(part=p).exists():
        s = StockItem(part=p, location=D1, quantity=1, notes=SRC + " One seen.")
        s.save(); s.refresh_from_db()
        assert s.location_id == D1.pk
        print(f"CREATED part #{p.pk} SI #{s.pk}: {name}")

m = Part.objects.get(pk=461)
LINE = ("\n\n**Stored with it in MB-D1 (2026-10-10 photo):** green-handled 1 in and 2 in "
        "micrometer standards and the hook spanners -- part of this set, not separate parts.")
if "micrometer standards" not in (m.notes or ""):
    Part.objects.filter(pk=461).update(notes=(m.notes or "") + LINE)
assert "micrometer standards" in Part.objects.get(pk=461).notes

CONF = "Filed 2026-10-10 from Scott's photo of Metrology Bench drawer 4. Count confirmed by Scott the same day."
StockItem.objects.filter(pk__in=(1120, 1121)).update(notes=CONF)
assert all("[ESTIMATE]" not in s.notes for s in StockItem.objects.filter(pk__in=(1120, 1121)))

print(f"\n{D1.pathstring}:")
for s in StockItem.objects.filter(location=D1).select_related("part").order_by("part__name"):
    print(f"  SI #{s.pk} {float(s.quantity):g} x {s.part.name[:70]}")
