"""Catalogue the six FSD/FSM bare PCBs and their vendor. Provenance from receipts.

Sources, both read from Scott's own mail 2026-08-29:
  2024-06-12  PayPal to FlightSimDIY  $43.67  invoice bdbbd-9569
              FSD G1000 v2 $12.99 · G1000 Blank (4) PCB Set $25.00 · ship $5.68
  2024-06-18  PayPal to FlightSimDIY  $55.61  invoice bdbbd-9581
              FSD GMA1347 $8.99 · GMA-1347 Blank (2) PCB Set $15.00 ·
              G1000 Blank (4) PCB Set $25.00 · ship $6.62

NO PURCHASE ORDERS CREATED, deliberately. Backfilling historical POs is a
designed change queued in OPEN.md — born COMPLETE, no stock rows, marked as
reconstructed, off the live reference sequence. Improvising half of that here
would produce exactly the ambiguous records that design exists to prevent. The
provenance lives on the parts and in docs/G1000.md until then.

NO STOCK ROWS YET: there is no container. A location in this system is a place.
"""
import argparse, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from company.models import Company, SupplierPart                 # noqa: E402
from part.models import Part, PartCategory                       # noqa: E402

VENDOR_DESC = (
 "FlightSimDIY / FlightSimMaker — one company, two brands, mid-rebrand when "
 "Scott bought.\n\n"
 "THE REBRAND IS WHY THE BOARDS LOOK LIKE TWO SUPPLIERS. The project moved from "
 "FlightSimDIY to the FlightSimMaker group. Older boards carry the round FSD "
 "logo; newer ones say FlightSimMaker. The June 2024 receipts show the seam: "
 "PayPal merchant \"FlightSimDIY\", contact address Contact@flightsimmaker.com, "
 "card descriptor PAYPAL *FSM STORE.\n\n"
 "Both brands still trade. flightsimdiy.com still lists an FSD G1000 NXi, so a "
 "board may be findable under either name — search both before concluding "
 "something is discontinued.\n\n"
 "Sold as BARE PCBs plus a paid design/licence line. PayPal checkout; no account "
 "needed. Community support is on Discord rather than a documentation site.")

BOARDS = [
 dict(n="PCB, G1000 NXi v2 Shield + GMA1347 Control (FlightSimMaker, Rev 3)",
      d=("Bare PCB. Carrier/shield for the G1000 NXi v2 panel set, with the "
         "GMA1347 audio-panel controller built in. Designed by Peter Eier, "
         "Revision 3. Panel code 2583209A_Y4_240615."),
      x=("THE MOTHERBOARD OF THE NXi BUILD. Carries TWO MEGA 2560 PRO footprints "
         "— U5 'G1000 NXi' and U4 'GMA1347' — two 74HC4067 16-channel muxes, an "
         "LM2596/HW-411 buck, and R3-R23. Its own silkscreen says \"includes "
         "GMA1347 Control Board\", which is why the standalone GMA1347 board is "
         "NOT needed in an NXi build. Confirmed by working hardware: Scott's "
         "build #2 drives the audio panel from this shield over two ribbons.\n\n"
         "Fabbed 2024-06-15 on a different panel from the v2.3 side boards, "
         "consistent with arriving in the second order.")),
 dict(n="PCB, G1000 NXi v2.3 Left Side (FlightSimDIY)",
      d=("Bare PCB. Left-hand button and encoder panel for the G1000 NXi v2.3. "
         "Panel code 4539410A_Y61_240614."),
      x=("FLC, VS, APR, NAV_BTN, HDG_BTN, AP, NOSE_DN, NOSE_UP, BC, VNAV, "
         "ALT_BTN, FD, plus HDG / NAV / VOL encoders, FLIP_FLOP, backlight "
         "BL_6..BL_9.")),
 dict(n="PCB, G1000 NXi v2.3 Right Side (FlightSimDIY)",
      d=("Bare PCB. Right-hand button and encoder panel for the G1000 NXi v2.3. "
         "Panel code 4539410A_Y60_240614."),
      x=("FMS, CLR, FPL, DIR_T, ENT, PROC, MENU, RANGE_PAN, plus CRS_BARO / COM "
         "/ VOL encoders, FLIP_FLOP, backlight BL_1..BL_5.")),
 dict(n="PCB, G1000 NXi v2.3 Soft Keys (FlightSimDIY)",
      d=("Bare PCB. Bottom softkey strip, 12 keys, for the G1000 NXi v2.3. "
         "Panel code 4539410A_Y62_240614."),
      x="SK_1 through SK_12, with R5, R8 and diodes D6, D7."),
 dict(n="PCB, GMA1347 Control Board v2.2 (FlightSimDIY)",
      d=("Bare PCB. Standalone controller for the GMA1347 audio panel, original "
         "pre-NXi architecture. Panel code 4539410A_Y18_240207."),
      x=("NOT FOR AN NXi BUILD. Takes its own ARDUINO MEGA 2560 MINI PRO and "
         "R1-R21, and belongs to the generation where every function had its own "
         "board. The NXi shield above absorbs this role.\n\n"
         "Pairs with the G1000 Control Board v2.3 — both pre-NXi, both the MINI "
         "PRO footprint, fabbed four months before the NXi set.")),
 dict(n="PCB, G1000 Control Board v2.3 (FlightSimDIY)",
      d=("Bare PCB. Controller for the original (non-NXi) G1000 panel. Takes an "
         "Arduino MEGA 2560 PRO MINI and one 16-channel analog multiplexer."),
      x=("ORIGINAL G1000, NOT NXi. Backlight driver with optional MOSFET, "
         "EXPANSION_CARDS header, softkey/encoder inputs C0..C15 named for the "
         "original layout.\n\n"
         "Scott's build #1 is a hand-wired original G1000 — an UNO on a proto "
         "shield with several hundred point-to-point wires. This board plus the "
         "GMA1347 v2.2 would have been its PCB retrofit. Scott 2026-08-29: he is "
         "not going back to that build, so this pair has no target in this shop.")),
]

COMMON = (
 "\n\nPURCHASED FROM FLIGHTSIMDIY, provenance recovered 2026-08-29 from Scott's "
 "PayPal receipts:\n"
 "  2024-06-12  $43.67  invoice bdbbd-9569 — FSD G1000 v2 $12.99, G1000 Blank "
 "(4) PCB Set $25.00, shipping $5.68\n"
 "  2024-06-18  $55.61  invoice bdbbd-9581 — FSD GMA1347 $8.99, GMA-1347 Blank "
 "(2) PCB Set $15.00, G1000 Blank (4) PCB Set $25.00, shipping $6.62\n"
 "  $99.28 total, 10 bare PCBs paid for.\n\n"
 "SIX ARE ACCOUNTED FOR AND FOUR ARE NOT. He bought the G1000 4-PCB set TWICE, "
 "so a second complete NXi set may still be boxed somewhere. Worth finding "
 "before build #3 — a spare set is a spare set.\n\n"
 "No purchase order in this system covers these; PO backfill is a designed "
 "change still queued. See docs/G1000.md.")

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

for b in BOARDS:
    print(f"  {b['n'][:70]}")
    if Part.objects.filter(name=b["n"]).exists():
        sys.exit(f"!! {b['n']!r} already exists")
if not a.commit:
    raise SystemExit("\nDRY RUN — add --commit")

co = Company.objects.filter(name__icontains="flightsim").first()
if not co:
    co = Company.objects.create(name="FlightSimDIY / FlightSimMaker",
                                is_supplier=True, website="https://flightsimdiy.com")
Company.objects.filter(pk=co.pk).update(description=VENDOR_DESC)
assert "REBRAND" in Company.objects.get(pk=co.pk).description
print(f"OK  supplier #{co.pk} {co.name}")

cat = (PartCategory.objects.filter(name__icontains="prototyping").first()
       or PartCategory.objects.filter(name__icontains="module").first())
for b in BOARDS:
    p = Part.objects.create(name=b["n"], description=b["d"], category=cat,
                            purchaseable=True, component=True, active=True)
    Part.objects.filter(pk=p.pk).update(notes=b["x"] + COMMON)
    assert "FLIGHTSIMDIY" in Part.objects.get(pk=p.pk).notes
    print(f"OK  part #{p.pk} {b['n'][:56]}")
print("\nNO STOCK ROWS — no container yet. Parts exist and are findable; the "
      "boards are not yet placed.")
