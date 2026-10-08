#!/usr/bin/env python3
"""File the shop-made soldering fume fan and mark it a commuting tool.

Scott, 2026-10-08: "mark soldering fan as a commuter, its not in inv was shop
made so create a record for it". No purchase, no vendor, no price: the record
is the thing, not a receipt. Filed at SLN/Florida Staging with a Florida
earmark (it is going south this trip - that is what today's session is) and a
commute marker with the SLN home UNKNOWN; whether it rides in FL-01 or loose,
and where it lives at SLN, are Scott's to say.

    itq run scripts/soldering_fan_1008.py [--commit]
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.utils import timezone  # noqa: E402
from part.models import Part, PartCategory  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

COMMIT = "--commit" in sys.argv
NAME = "Soldering Fume Fan, shop-made"
cat = PartCategory.objects.get(pk=39); assert cat.pathstring == "Equipment/Soldering"
staging = StockLocation.objects.get(pathstring="SLN/Florida Staging")
if Part.objects.filter(name__istartswith="Soldering Fume Fan").exists():
    print("already filed:", list(Part.objects.filter(name__istartswith="Soldering Fume Fan").values_list("pk", "name"))); sys.exit(1)
print(f"create part {NAME!r} in {cat.pathstring}; stock 1 @ {staging.pathstring}; earmark + commutes, home UNKNOWN")
if not COMMIT:
    print("\nDRY RUN - nothing written. Re-run with --commit."); sys.exit(0)
today = str(timezone.now().date())
p = Part(name=NAME, category=cat, purchaseable=False, component=False, trackable=True,
         description="Bench fume-extraction fan for soldering, built in the shop. One unit, travels between SLN and LRD.",
         keywords="fume extractor, solder fume, fan, smoke absorber, bench, shop-made",
         notes=f"Shop-made; no purchase record, vendor or price. Filed {today} on Scott's word "
               "when it was packed for Florida ('mark soldering fan as a commuter, its not in inv "
               "was shop made so create a record for it'). Build details, motor and filter not "
               "recorded - add them with the fan in hand.\n\nCommuting tool. SLN home NOT recorded.")
p.save(); p.refresh_from_db(); assert p.pk and p.name == NAME
s = StockItem.objects.create(part=p, location=staging, quantity=1,
                             notes=f"Bound for Florida {today}; box or loose not stated.")
meta = {"florida": {"qty": 1.0, "why": "Soldering fan going south (Scott 2026-10-08); box or loose not stated", "added": today},
        "commutes": {"home": None, "home_path": "UNKNOWN - SLN home not recorded",
                     "since": today, "note": "shop-made soldering fume fan, one only, carry both ways (Scott 2026-10-08)", "trips": []}}
StockItem.objects.filter(pk=s.pk).update(metadata=meta)
s.refresh_from_db(); s.tags.add("commutes"); s.tags.add("florida")
ok = set((s.metadata or {}).keys()) == {"florida", "commutes"}
print(f"\npart {p.pk}  stock {s.pk} @ {s.location.pathstring}  meta persisted: {ok}")
print(f"http://192.168.50.10:8001/web/part/{p.pk}/")
