"""2026-09-20  Stock the ADS-B magnetic-mount antenna into B0-R2C4.

Rejected: creating a new part. #388 already exists as an import stub with the
same description, zero stock and no home. Creating a second would be the
duplicate this shop has been bitten by twice.

Rejected: recording it as qty 2 of a "2-Pack". The pack ships an SMA-male
antenna and an MCX-male antenna - DIFFERENT CONNECTORS, not interchangeable
pieces. Scott has only the MCX one. A pack is a supplier fact; the row counts
what is on the shelf, which is one.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()
from part.models import Part
from stock.models import StockItem, StockLocation
from company.models import SupplierPart
from order.models import PurchaseOrderLineItem

p = Part.objects.get(pk=388)
loc = StockLocation.objects.get(pk=569)

print("=== BEFORE ===")
print(f"[388] {p.name!r}")
print(f"      desc={p.description!r}")
print(f"      active={p.active} defloc={p.default_location} units={p.units!r}")
print(f"      stock rows: {list(StockItem.objects.filter(part=p).values_list('pk','quantity'))}")
for sp in SupplierPart.objects.filter(part=p):
    print(f"      SP{sp.pk} {sp.supplier.name} SKU={sp.SKU} "
          f"pack={sp.pack_quantity!r}/native={sp.pack_quantity_native}")
    for li in PurchaseOrderLineItem.objects.filter(part=sp):
        print(f"        PO {li.order.reference} qty={li.quantity} recvd={li.received} "
              f"price={li.purchase_price} target={li.target_date}")
print(f"loc 569 {loc.pathstring}  desc={loc.description!r}")

# ---------------- writes ----------------
NEWNAME = 'Antenna Mag-Mount 978/1090MHz MCX male'
NEWDESC = ('Bingfu dual-band 978/1090 MHz ADS-B magnetic-base whip, 5dBi, MCX male '
           'plug on captive coax. Mast 15 cm, connector 3.2 mm OD (Scott, measured). '
           'Mates the NooElec NESDR Mini SDR, part #261. Black.')
assert len(NEWNAME) <= 48, len(NEWNAME)
assert len(NEWDESC) <= 250, len(NEWDESC)
print(f"\nname {len(NEWNAME)} chars / desc {len(NEWDESC)} chars - both inside limits")

NOTES = """2026-09-20 FIRST PHYSICAL CATALOGUING. This part existed only as an
import stub from the Amazon order - zero stock, no home - until Scott put the
antenna on the bench.

WHAT WAS MEASURED (Scott, at the bench): connector 3.2 mm OD, mast height
15 cm. Magnetic base, black, captive coax lead.

IDENTIFICATION IS AN INFERENCE, NOT A MARKING. Nothing is printed on the part.
It is tied to this record by three things: (1) 3.2 mm RULES OUT SMA, whose
thread is 6.35 mm, leaving MCX as the fit; (2) the shop owns exactly one
magnetic-base 978/1090 antenna record, this one, and its pack is specified
SMA male + MCX; (3) a 15 cm mast is CONSISTENT with a 978/1090 design -
consistent only, it confirms nothing on its own. If a marking is ever found
that contradicts this, the marking wins.

THE SMA TWIN IS NOT HERE. Scott, asked directly: "no sma one". The order was
a 2-pack, so one antenna is unaccounted for - used, lost, or the order line
was misread. NOT catalogued as missing stock, because nobody has established
it ever arrived. Open question, not a discrepancy.

NOT SPLIT INTO TWO PARTS. If the SMA twin turns up it needs its OWN part
record - a different connector is not an interchangeable piece, and this row
must never become qty 2.

ITS RECEIVER IS UNCATALOGUED. #261 NooElec NESDR Mini (RTL2832U/R820T, MCX
input) is the thing this plugs into and is itself a zero-stock stub. If the
SDR is physically in the shop it has never been counted."""

p.name = NEWNAME
p.description = NEWDESC
p.default_location = loc
p.notes = NOTES
p.save()

r = Part.objects.get(pk=388)
print("\n=== AFTER (re-read) ===")
print(f"name   : {r.name!r}  {'OK' if r.name == NEWNAME else 'BAD'}")
print(f"desc   : {r.description!r}  {'OK' if r.description == NEWDESC else 'BAD'}")
print(f"defloc : {r.default_location}  {'OK' if r.default_location_id == 569 else 'BAD'}")
print(f"notes  : {len(r.notes or '')} chars  {'OK' if 'no sma one' in (r.notes or '') else 'BAD'}")

existing = StockItem.objects.filter(part=r, location=loc)
if existing.exists():
    print(f"!! row already exists: {list(existing.values_list('pk','quantity'))} - NOT creating")
    si = existing.first()
else:
    si = StockItem.objects.create(
        part=r, location=loc, quantity=1,
        notes=("2026-09-20 Counted by Scott at the bench: ONE antenna, the MCX one. "
               "The SMA half of the 2-pack is not here - see the part notes; it is an "
               "open question, not a shortage. Connector 3.2 mm OD and mast 15 cm are "
               "MEASURED values, not catalogue figures."))
    print(f"created stock row {si.pk}")

v = StockItem.objects.get(pk=si.pk)
print(f"stock {v.pk}: part={v.part.pk} qty={v.quantity} loc={v.location.pathstring} "
      f"{'OK' if v.quantity == 1 and v.location_id == 569 else 'BAD'}")

loc.description = ("RF / ANTENNA & COAX. Antennas, feedline, coax jumpers and the adapters "
                   "between connector families - MCX, SMA, U.FL/IPEX, BNC. Opened 2026-09-20 "
                   "for the ADS-B mag-mount antenna, which needs a LARGE drawer: a magnetic "
                   "base and a coiled lead do not fit the small bins. Grouped by FUNCTION, "
                   "which is how this wall sorts. NOT the radio modules - nRF24L01+, 433MHz "
                   "FS1000A/XY-MK-5V and Heltec LoRa boards stay in A3-R2C2/R2C3 and RB-03; "
                   "the split is feedline versus the radio behind it. The tiny U.FL/IPEX "
                   "pigtails (#496, #732) remain at A3-R6C6 with the dev boards for now - "
                   "consolidate here only if someone is hunting for them.")
loc.save()
lr = StockLocation.objects.get(pk=569)
print(f"\nloc 569 desc: {len(lr.description)} chars  "
      f"{'OK' if 'RF / ANTENNA & COAX' in lr.description else 'BAD'}")
print(lr.description)
