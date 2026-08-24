"""Finish the PO-0020 receive: close the order, set a home, record the shelf.

Three loose ends the receive deliberately left, because each is a different
kind of claim:

  1. PO-0020 has 0 lines outstanding and is still PLACED. An order that is
     fully received but still open sits in the open-PO list forever and every
     aging rule keeps counting it. Close it.

  2. part #790 has no default_location. The rule is that default_location is
     where a SPARE goes home -- WS2-S3 is a real shelf, not a staging area, so
     it qualifies.

  3. WS2-S3's description does not say wire lives there. Scott, 2026-08-24:
     "most of the wire currently resides on WS2 S3". That contradicts both
     racks' own descriptions -- WS1 claims cable/wire/adhesives and WS2 claims
     tubing/ducting/tape/bulk. Those were written as INTENT and are being read
     as fact, which is the same failure as a planned receive location: a plan
     and an observation look identical once they are in the field.

     Recording the observation, not rewriting the plan -- the split may still
     be what Scott wants eventually, and deleting the intent would lose that.

    itq run scripts/close_po0020.py
    itq run scripts/close_po0020.py --commit
"""
import argparse
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from order.models import PurchaseOrder            # noqa: E402
from order.status_codes import PurchaseOrderStatus  # noqa: E402
from part.models import Part                      # noqa: E402
from stock.models import StockLocation            # noqa: E402

OBS = ("  OBSERVED 2026-08-24 (Scott): most of the WIRE actually lives on this "
       "shelf, not on WS1 — WS1's description says cable/wire/adhesives and "
       "WS2's says tubing/ducting/bulk, and both were written as intent before "
       "anyone checked. Fiberglass sleeve #790 filed here to sit with the wire.")

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

po = PurchaseOrder.objects.get(reference="PO-0020")
part = Part.objects.get(pk=790)
locs = list(StockLocation.objects.filter(name__iexact="WS2-S3"))
assert len(locs) == 1, f"WS2-S3 matched {len(locs)}"
loc = locs[0]

outstanding = [l for l in po.lines.all() if l.received < l.quantity]
print(f"PO-0020 status={po.get_status_display()} outstanding_lines={len(outstanding)}")
print(f"#790 default_location={part.default_location}  -> {loc.pathstring}")
print(f"WS2-S3 description already mentions wire: "
      f"{'wire' in (loc.description or '').lower()}")

if outstanding:
    print("!! lines still outstanding — not closing")
    raise SystemExit(1)

if not a.commit:
    print("\nDRY RUN — add --commit")
    raise SystemExit

PurchaseOrder.objects.filter(pk=po.pk).update(status=PurchaseOrderStatus.COMPLETE.value)
fresh = PurchaseOrder.objects.get(pk=po.pk)
assert fresh.get_status_display() == "Complete", fresh.get_status_display()
print(f"\nOK  PO-0020 -> {fresh.get_status_display()}")

Part.objects.filter(pk=part.pk).update(default_location=loc)
assert Part.objects.get(pk=part.pk).default_location_id == loc.pk
print(f"OK  #790 default_location -> {loc.pathstring}")

if "OBSERVED 2026-08-24" not in (loc.description or ""):
    newdesc = (loc.description or "").rstrip() + OBS
    StockLocation.objects.filter(pk=loc.pk).update(description=newdesc)
    got = StockLocation.objects.get(pk=loc.pk).description
    assert "OBSERVED 2026-08-24" in got, "description did not stick"
    print(f"OK  WS2-S3 description updated ({len(got)} chars)")
else:
    print("--  WS2-S3 already carries the observation")
