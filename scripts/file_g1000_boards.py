"""Put the G1000 boards away. Scott's plan, 2026-08-29.

  MOBILE CART MC-T3 — the working set for the PFD build. Already the Cessna
  tray ("Connectors and ribbon cable staged for the CESSNA FL..."), so the
  boards join the parts they will be built with. Scott: "that'll all be in one
  place and easy to locate."
      3 daughter boards (soft keys, left, right) + 1 NXi shield

  NEW BIN ON WS2-S4 — spares, off the working set deliberately. WS2-S4 already
  holds the Sim Rudder Pedals kit for BO-0015, so sim material stays together.
      FSD G1000 control board, GMA1347 control board, 6 spare NXi shields

WHY SPLIT AT ALL: what you reach for and what you keep are different questions.
Mixing six spares into the working tray means counting past them every time.
"""
import argparse, datetime, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part                                     # noqa: E402
from stock.models import StockItem, StockLocation                # noqa: E402

TODAY = datetime.date.today()
SHELF, CART = 456, 432          # WS2-S4, MC-T3
SPARES = "Sim G1000 Spares"
SPARES_DESC = (
 "SIM G1000 SPARES — bare PCBs held back from the build. Established "
 "2026-08-29.\n\n"
 "NOT the working set. The boards for the next build (PFD) live on the mobile "
 "cart at MC-T3 with the connectors and ribbon cable staged for that job. This "
 "bin is what is left over after it: six spare Peter Eier NXi shields, plus the "
 "two FlightSimDIY control boards that Peter's shield made redundant.\n\n"
 "THE TWO FSD CONTROL BOARDS HAVE NO ROLE IN AN NXi BUILD and are here because "
 "they are worth something to somebody, not because they are needed. Peter's "
 "shield carries both MEGAs — G1000 NXi and GMA1347 — so it replaces both of "
 "them at once. See docs/G1000.md.")

# part pk -> (destination, qty)
PLAN = {
    1155: (CART, 1),    # soft keys
    1153: (CART, 1),    # left side
    1154: (CART, 1),    # right side
    1152: (CART, 1),    # NXi shield — the one for the PFD build
    1157: ("SPARES", 1),  # FSD G1000 control board
    1156: ("SPARES", 1),  # GMA1347 control board
}
SHIELD_SPARES = 6

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

cart = StockLocation.objects.get(pk=CART)
shelf = StockLocation.objects.get(pk=SHELF)
print(f"cart   {cart.pathstring}")
print(f"       {(cart.description or '')[:70]}")
print(f"shelf  {shelf.pathstring} -> new container {SPARES!r}")
for pk, (dest, q) in PLAN.items():
    p = Part.objects.get(pk=pk)
    print(f"  #{pk} {p.name[:52]:54} x{q} -> {'SPARES' if dest=='SPARES' else cart.name}")
print(f"  #1152 x{SHIELD_SPARES} more -> SPARES  (the leftover shields)")
if not a.commit:
    raise SystemExit("\nDRY RUN — add --commit")

spares = StockLocation.objects.filter(name=SPARES, parent=shelf).first()
if not spares:
    spares = StockLocation.objects.create(name=SPARES, parent=shelf,
                                          description=SPARES_DESC)
    assert StockLocation.objects.get(pk=spares.pk).parent_id == SHELF
    print(f"\nOK  location #{spares.pk} {spares.pathstring}")

def place(pk, loc, qty, note):
    p = Part.objects.get(pk=pk)
    s = StockItem.objects.create(part=p, location=loc, quantity=qty, notes=note)
    StockItem.objects.filter(pk=s.pk).update(stocktake_date=TODAY)
    if p.default_location_id is None:
        Part.objects.filter(pk=pk).update(default_location=loc)
    f = StockItem.objects.get(pk=s.pk)
    assert float(f.quantity) == qty and f.location_id == loc.pk, f"#{pk} did not stick"
    assert f.stocktake_date == TODAY, f"#{pk} stocktake did not stick"
    print(f"OK  #{pk} stock #{f.pk} x{qty:g} in {loc.name}")

for pk, (dest, q) in PLAN.items():
    loc = spares if dest == "SPARES" else cart
    why = ("Held as a spare — no role in an NXi build; Peter's shield replaces it."
           if dest == "SPARES" else
           "Working set for the PFD build, staged with the Cessna parts on the cart.")
    place(pk, loc, q, f"COUNTED {TODAY} by Scott. {why}")

place(1152, spares, SHIELD_SPARES,
      f"COUNTED {TODAY} by Scott. Six spare shields — 10 fabbed at JLCPCB, one "
      "in the built MFD, one on the cart for the PFD, two sold.")

print(f"\ncart  {StockItem.objects.filter(location=cart).count()} rows")
print(f"spares {StockItem.objects.filter(location=spares).count()} rows")
