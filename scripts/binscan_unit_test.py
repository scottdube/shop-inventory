"""End-to-end test of binscan's unit-of-measure path. Run after any change to it.

    itq run scripts/binscan_unit_test.py

Tests the real HTTP endpoint against a THROWAWAY part.

Written this way because the previous probe ran against real stock rows on the
assumption that a validation failure would return before any write. It did not,
and three false hand-counts landed on the sleeve and a nozzle. A write path is
tested against something disposable, or it is tested in production.

Creates a part + stock row, drives the real HTTP endpoint, asserts, deletes.
"""
import json, os, sys, urllib.parse, urllib.request
import django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part                      # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

BASE = "http://127.0.0.1:8002"
# A throwaway LOCATION too. "Receiving" exists at both sites and the app
# rightly refused to guess between them -- and using any real drawer risks the
# empty-stamp side effect rewriting a description that took a walk to earn.
scratch_name = "__unit-probe-loc__"
loc = StockLocation.objects.create(
    name=scratch_name, description="throwaway for the binscan unit test",
    parent=StockLocation.objects.get(name="Receiving",
                                     parent__name__startswith="SLN"))

part = Part.objects.create(name="__unit probe — delete me__",
                           description="throwaway for the binscan unit test",
                           category=Part.objects.get(pk=790).category,
                           units="m", active=True)
si = StockItem.objects.create(part=part, location=loc, quantity=1,
                              notes="throwaway")
print(f"scratch part #{part.pk}, stock #{si.pk}, units={part.units!r}")

def post(**f):
    data = urllib.parse.urlencode(f).encode()
    req = urllib.request.Request(f"{BASE}/api/assign", data=data)
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())

def qty():
    return float(StockItem.objects.get(pk=si.pk).quantity)

fails = []
try:
    print("\n1. 8 in  -> a part stored in m")
    code, body = post(stock=si.pk, location=scratch_name, quantity="8",
                      unit="in", confirm="yes")
    got = qty()
    print(f"   http {code}  stored={got}")
    print(f"   BODY: {json.dumps(body)[:400]}")
    if not (code == 200 and abs(got - 0.2032) < 1e-9):
        fails.append(f"8 in should store 0.2032, stored {got}")
    if "COUNTED at 0.2032 by hand" not in body.get("note", ""):
        fails.append("note lost the 'COUNTED at <n> by hand' shape "
                     "that sync_stocktake.py matches on")

    print("\n2. 8 g   -> dimensionality mismatch, must REFUSE and not write")
    before = qty()
    code, body = post(stock=si.pk, location=scratch_name, quantity="8",
                      unit="g", confirm="yes")
    print(f"   http {code}  {body}")
    if code != 400:
        fails.append(f"grams for a metre part returned {code}, expected 400")
    if abs(qty() - before) > 1e-12:
        fails.append("REFUSED REQUEST STILL WROTE — quantity changed")

    print("\n3. furlong -> unknown unit, must REFUSE and not write")
    before = qty()
    code, body = post(stock=si.pk, location=scratch_name, quantity="8",
                      unit="furlong", confirm="yes")
    print(f"   http {code}  {body}")
    if code != 400:
        fails.append(f"bogus unit returned {code}, expected 400")
    if abs(qty() - before) > 1e-12:
        fails.append("REFUSED REQUEST STILL WROTE — quantity changed")

    print("\n4. 2 ft  -> 0.6096 m")
    code, body = post(stock=si.pk, location=scratch_name, quantity="2",
                      unit="ft", confirm="yes")
    got = qty()
    print(f"   http {code}  stored={got}")
    print(f"   BODY: {json.dumps(body)[:400]}")
    if not (code == 200 and abs(got - 0.6096) < 1e-9):
        fails.append(f"2 ft should store 0.6096, stored {got}")
finally:
    StockItem.objects.filter(pk=si.pk).delete()
    Part.objects.filter(pk=part.pk).delete()
    StockLocation.objects.filter(pk=loc.pk).delete()
    gone = (not StockItem.objects.filter(pk=si.pk).exists()
            and not Part.objects.filter(pk=part.pk).exists()
            and not StockLocation.objects.filter(pk=loc.pk).exists())
    print(f"\ncleaned up: {gone}")
    assert gone, "throwaway rows survived — clean them by hand"

print()
if fails:
    for f in fails:
        print("  FAIL:", f)
    raise SystemExit(1)
print("all 4 checks passed")
