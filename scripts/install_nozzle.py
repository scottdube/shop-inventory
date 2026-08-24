"""Stock the FR-301 gun, stock the 1.3mm nozzle, and INSTALL the nozzle in it.

Two gaps close at once. The FR-301 (#474) has never had a stock row at all --
the shop's own desoldering gun was in the catalogue as a name with no physical
existence. And the 1.3mm nozzle (#213) is going straight into service rather
than into the drawer.

`belongs_to` is the field that makes "in service" honest. It is the first clause
of StockItem.IN_STOCK_FILTER, so an installed item:

  * still exists, still shows who owns it and what it is inside
  * does NOT count toward get_stock_count(), so minimum_stock=1 fires

which is precisely the distinction between "I own a 1.3mm nozzle" and "I have a
spare 1.3mm nozzle". The drawer A3-R1C2 remains default_location for both --
that is where a spare goes home, and this unit simply is not a spare.

LOCATION CLAIM, stated so it can be challenged: the gun is recorded at
SLN/Electronics Bench because Scott was fitting a nozzle to it there on
2026-08-24. That is an observation of the gun in use, not a drawer somebody
planned for it. No stocktake_date on either row -- nobody has stated a count,
and a tool being obviously singular is not the same as a person counting it.

    itq run scripts/install_nozzle.py
    itq run scripts/install_nozzle.py --commit
"""
import argparse
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part                       # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

GUN_PK, NOZZLE_PK = 474, 213
BENCH = "Electronics Bench"

GUN_NOTE = ("Recorded at the electronics bench 2026-08-24 because Scott was "
            "fitting a nozzle to it there — an observation of the tool in use, "
            "not a planned home. NOT COUNTED: no stocktake_date; a tool being "
            "obviously singular is not the same as somebody counting it.")
NOZ_NOTE = ("IN SERVICE — installed on the FR-301 (belongs_to), not a spare. "
            "Fitted 2026-08-24 straight out of the bag, so it never sat in "
            "A3-R1C2, which remains its home for the NEXT one. Because "
            "belongs_to is set, this unit does not count toward stock, which is "
            "what lets minimum_stock=1 report 'no spare' truthfully.")

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

bench = list(StockLocation.objects.filter(name__iexact=BENCH))
assert len(bench) == 1, f"{BENCH} matched {len(bench)}"
bench = bench[0]

gun, noz = Part.objects.get(pk=GUN_PK), Part.objects.get(pk=NOZZLE_PK)
print(f"gun    #{gun.pk} {gun.name}   stock rows={gun.stock_items.count()}")
print(f"nozzle #{noz.pk} {noz.name[:52]}   stock rows={noz.stock_items.count()}")
print(f"bench  {bench.pathstring}")
print(f"\nnozzle stock now={noz.get_stock_count():g} min={float(noz.minimum_stock):g} "
      f"low={noz.is_part_low_on_stock()}")

if noz.stock_items.exists():
    print("!! nozzle already has stock — refusing to double-create")
    raise SystemExit(1)

if not a.commit:
    print("\nDRY RUN — add --commit")
    raise SystemExit

gsi = gun.stock_items.first()
if gsi is None:
    gsi = StockItem.objects.create(part=gun, location=bench, quantity=1,
                                   notes=GUN_NOTE)
    assert StockItem.objects.get(pk=gsi.pk).location_id == bench.pk
    print(f"\nOK  gun stock #{gsi.pk} qty=1 @ {bench.pathstring}")
else:
    print(f"\n--  gun already stocked as #{gsi.pk}")

nsi = StockItem.objects.create(part=noz, location=bench, quantity=1, notes=NOZ_NOTE)
StockItem.objects.filter(pk=nsi.pk).update(belongs_to=gsi)
chk = StockItem.objects.get(pk=nsi.pk)
assert chk.belongs_to_id == gsi.pk, f"belongs_to did not stick: {chk.belongs_to_id}"
print(f"OK  nozzle stock #{chk.pk} installed into gun stock #{gsi.pk}")

noz.refresh_from_db()
print(f"\nnozzle stock now={noz.get_stock_count():g} min={float(noz.minimum_stock):g} "
      f"low={noz.is_part_low_on_stock()}   <- 'no spare', which is true")
print(f"installed items on the gun: "
      f"{[ (s.pk, s.part.name[:36]) for s in gsi.installed_parts.all() ]}")
