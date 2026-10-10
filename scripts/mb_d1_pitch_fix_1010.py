"""Undo the D1 pitch-gauge match from mb_d1_closeup_1010.py.

The triangular "U.S. 60deg 4-84" gauge in MB-D1 was matched to SI #1048
(Starrett 472, eBay order 21-08894-80002) because 472 is the 4-84 / 51-leaf
gauge and it was the only US pitch gauge on file. Scott, 2026-10-10: maker
unknown, he believes it was an Amazon purchase. The face carries no Starrett
stamp, which Starrett puts on its cases -- so the D1 gauge is a separate
unbranded gauge and the eBay Starrett 472 is somewhere not yet located.

  - SI #1048 goes back to Unfiled - Machine Shop, home cleared (it had none
    before this session).
  - New part for the D1 gauge, no maker in the name; no Amazon PO is cited
    because none was found on file and "believe" is Scott's own hedge.

    itq run scripts/mb_d1_pitch_fix_1010.py [--commit]
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
UNF = StockLocation.objects.get(name="Unfiled - Machine Shop")
NAME = "Screw Pitch Gage, US 60 deg, 4-84 TPI (maker unknown)"

s = StockItem.objects.get(pk=1048); assert s.part_id == 1361
print(f"SI #1048 Starrett 472 @ {s.location.name} -> {UNF.name}; create {NAME!r} in {D1.name}")
if not COMMIT:
    sys.exit("DRY RUN -- add --commit")

StockItem.objects.filter(pk=1048).update(location=UNF)
p472 = Part.objects.get(pk=1361)
LINE = ("\n\n**Not the gauge in MB-D1** (2026-10-10): that one is unbranded, Scott believes "
        "Amazon. This eBay Starrett 472 has not been located -- left in Unfiled.")
Part.objects.filter(pk=1361).update(default_location=None,
                                    notes=p472.notes + ("" if "Not the gauge in MB-D1" in p472.notes else LINE))
assert StockItem.objects.get(pk=1048).location_id == UNF.pk
assert Part.objects.get(pk=1361).default_location_id is None

p = Part.objects.filter(name=NAME).first()
if not p:
    p = Part(name=NAME, description="Screw pitch gauge, 60 deg US threads, 4-84 TPI, triangular case, brass rivets",
             keywords="pitch gauge, pitch gage, screw pitch, thread gauge, 4-84 TPI, 60 deg, UNC, UNF",
             category=MEAS, component=False, purchaseable=True, assembly=False, default_location=D1,
             notes=("Filed 2026-10-10 from Scott's close-up photo of Metrology Bench drawer 1. "
                    "Case reads 'U.S. 60deg 4-84', no maker stamp. Scott: maker unknown, believes "
                    "it was an Amazon purchase (no PO found on file).\n\nNo price."))
    p.save(); p.refresh_from_db()
    assert p.default_location_id == D1.pk
if not StockItem.objects.filter(part=p).exists():
    n = StockItem(part=p, location=D1, quantity=1, notes="Seen in the 2026-10-10 D1 close-up. One seen.")
    n.save(); n.refresh_from_db(); assert n.location_id == D1.pk
    print(f"CREATED part #{p.pk} SI #{n.pk}: {NAME}")
