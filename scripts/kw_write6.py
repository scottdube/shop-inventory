"""Queue D final batch: search keywords for every remaining part with an empty
`keywords` field that is NOT a tombstone.

The 2026-08-31 run left a note that the resume point was pk 139, not 1078 —
this backfill had only ever walked upward from 489, so most of what remained
sat *below* the batches already done. That note is why this batch starts at
the bottom instead of continuing from 1078.

Sweeping from pk 0 turned up 93 empty rows, of which **38 are tombstones**:
rows whose description opens MERGED / DUPLICATE / REFUNDED / NOT INVENTORY /
RETIRED. They are listed explicitly in SKIP with the phrase that classifies
each one, rather than pattern-matched, so the decision is auditable and a
later description edit cannot silently change what this script did.

Keywording a tombstone is not harmless: it is the one thing that would put a
dead row back into live search results, which is the whole reason merges were
done by hand in the first place. Same ruling as pk 600/502/662/734 in earlier
batches.

That leaves 55 real parts, which is the entire rest of the backlog — so this
batch closes queue D's original ~780-part backfill.

Vocabulary choices worth keeping:
  * every bearing carries BOTH its designation and its bore x OD x width,
    because the drawer label is the size and the invoice is the designation
  * inch-series bearings (R4/R6/R8) carry "inch" and "imperial" spelled out;
    six months from now the memory is "the imperial one", not "R6"
  * abbreviations AND expansions, since InvenTree search is substring:
    "RTV" does not match "room temperature vulcanising", "CA" does not
    match "cyanoacrylate"
  * the flight-sim PCBs carry their panel codes (Y60/Y61/Y62/Y18) — four bare
    green boards are otherwise indistinguishable, and the code is silkscreened
  * consumables carry what a person calls them at the bench ("popsicle stick",
    "flux brush", "superglue activator"), not the catalogue noun
"""
import argparse
import os
import sys

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part  # noqa: E402

LIMIT = 250

# Every one of these self-describes as dead in its own description field.
SKIP = {
    139: "REFUNDED (sole item on order) — not inventory",
    143: "REFUNDED (sole item on order) — not inventory",
    150: "REFUNDED (sole item on order) — not inventory",
    153: "MERGED into part #26",
    168: "MERGED into part #58",
    182: "MERGED into part #59",
    191: "MERGED into part #18",
    205: "MERGED into part #92",
    214: "MERGED into part #87",
    216: "MERGED into part #42",
    221: "MERGED into part #800",
    227: "NOT INVENTORY — medical supply, excluded by rule 3",
    237: "MERGED into part #789",
    259: "REFUNDED (sole item on order) — not inventory",
    270: "REFUNDED (sole item on order) — not inventory",
    299: "MERGED into part #17",
    317: "REFUNDED (sole item on order) — not inventory",
    318: "MERGED into part #65",
    319: "REFUNDED (sole item on order) — not inventory",
    325: "MERGED into part #56",
    327: "name carries [merged] — tombstone of the LM2596 buck converter",
    354: "NOT INVENTORY — personal-care/medical, excluded by rule 3",
    365: "REFUNDED (sole item on order) — not inventory",
    370: "DUPLICATE of #4",
    371: "DUPLICATE of #6",
    378: "NOT INVENTORY — consumer item",
    381: "MERGED into part #71",
    398: "MERGED into part #76",
    413: "MERGED into part #40",
    420: "MERGED into part #67",
    448: "DUPLICATE of #1",
    463: "REFUNDED (sole item on order) — not inventory",
    485: "MERGED into part #77",
    502: "RETIRED — an assortment kit is a LOCATION, not a part",
    600: "NOT INVENTORY — consumer item",
    662: "retired duplicate of 683 — tombstone, keep it out of search",
    734: "self-described NOT INVENTORY (gifted)",
}

BALL = "ball bearing, deep groove bearing, radial bearing, bearing"
INCH = "inch bearing, imperial bearing, inch series"
PCB = "PCB, bare board, bare PCB, circuit board, flight sim, flight simulator"
CEMENT = "acrylic cement, solvent cement, plastic weld, acrylic glue, plexiglass glue"
CORD = "seal cord, gasket cord, round cord, rubber cord, cord stock"

KW = {
    # --- displays ---------------------------------------------------------
    470: "round LCD, round display, circular display, GC9A01, 240x240, SPI display, TFT, waveshare, 1.28 inch, 1.28in, gauge display, smartwatch display",
    1144: "HDMI display, LCD display, touchscreen, touch screen, resistive touch, XPT2046, 800x480, IPS, 4 inch, 4inch, waveshare, Display-C, Raspberry Pi display",

    # --- VFD salvage ------------------------------------------------------
    1078: "fan, cooling fan, axial fan, brushless fan, DC fan, 60mm fan, 6015, 60x60x15, 12V fan, XQF, X6015D12MB, salvage",
    1079: "terminal block, barrier strip, barrier terminal, screw terminal, 4 position, 4 pole, 7.62mm pitch, mains terminal, RST, PE, salvage",
    1080: "IGBT, insulated gate bipolar transistor, DXG20N65FS, 650V, 20A, TO-220, field stop, power switch, salvage, tested dead",
    1081: "terminal block, barrier strip, barrier terminal, screw terminal, 5 position, 5 pole, 7.62mm pitch, mains terminal, salvage",
    1140: "terminal block, PCB terminal block, screw terminal, 3.5mm pitch, 18 position, 2x9, dual row, control terminal, VFD, salvage",

    # --- bench / test -----------------------------------------------------
    1096: "soldering practice, practice kit, SMD practice, solder training, learn to solder, 0805, SOT23, LL34, eBay kit, trainer board",
    1097: "vacuum gauge, vac gauge, negative pressure gauge, manometer, dial gauge, inHg, 30 inHg, -1 bar, -100 kPa, lower mount, MEANLIN, XJ-087",

    # --- projects ---------------------------------------------------------
    1098: "water shutoff, water valve, shut off valve, automatic shutoff, leak protection, servo valve, 35KG servo, coreless servo, prototype, project",
    1126: "head mover, mill head lift, power head raise, head raise, Jet mill drill, mill drill, chain drive, thrust bearing, project",
    1130: "rudder pedals, rudder, sim pedals, flight sim, flight simulator, Cessna, sub build, project",
    1134: "Info Orbs, orbs, ESP32, GC9A01, round display, desk widget, five displays, SPI bus, project",
    1137: "G1000, Garmin G1000, glass cockpit, avionics, avionics panel, flight sim, flight simulator, Cessna, sub build, project",

    # --- adhesives --------------------------------------------------------
    1109: "contact adhesive, contact cement, glue, clear glue, flexible adhesive, waterproof adhesive, Gorilla, Clear Grip, squeeze tube",
    1110: f"{CEMENT}, Weld-On 16, WeldOn 16, IPS 10315, medium bodied, polycarbonate, styrene, butyrate, tube",
    1111: f"{CEMENT}, Weld-On 4, WeldOn 4, water thin, capillary cement, polycarbonate, 1 pint, 16 oz can",
    1112: "CA accelerator, cyanoacrylate accelerator, superglue activator, super glue accelerator, kicker, CA kicker, aerosol, Adhesive Guru",
    1113: "gasket maker, RTV, RTV silicone, room temperature vulcanising, silicone sealant, sensor safe, grey RTV, 999, form a gasket, Yonglian",
    1114: "applicator bottle, needle bottle, squeeze bottle, needle tip, dispensing bottle, cement applicator, capillary applicator, LDPE",
    1115: "spreader stick, popsicle stick, craft stick, mixing stick, wooden stick, glue spreader, applicator, disposable",
    1116: "acid brush, flux brush, horsehair brush, solder brush, glue brush, metal handle brush, disposable brush",

    # --- linear motion ----------------------------------------------------
    1117: "linear rail, linear guide, linear motion, MGN9, MGN9H, MGN9C, 9mm rail, 200mm, miniature rail, ball carriage, 3D printer rail",
    1118: "linear bearing, linear bushing, ball bushing, linear motion, LM8UU, 8mm bore, 8mm rod, 8x15x24, 3D printer bearing",

    # --- bearings ---------------------------------------------------------
    1119: f"{BALL}, 608, 608-2RS, 608RS, 8x22x7, 8mm bore, skate bearing, sealed bearing, rubber sealed",
    1120: f"{BALL}, 608, 608ZZ, 608-2Z, 8x22x7, 8mm bore, skate bearing, shielded bearing, metal shield",
    1121: f"{BALL}, 6203, 6203-2RS, 6203RS, 17x40x12, 17mm bore, sealed bearing, rubber sealed",
    1122: f"{BALL}, thin section bearing, 6803, 6803-2RS, 6803RS, 17x26x5, 17mm bore, sealed bearing",
    1123: f"{BALL}, {INCH}, R6, R6-2RS, R6RS, 3/8 bore, 7/8 OD, sealed bearing",
    1124: "tapered roller bearing, taper bearing, roller bearing, 30203, 17x40x12, 17mm bore, cone and cup, matched set, thrust and radial",
    1125: f"{BALL}, {INCH}, R4, R4-2RS, R4RS, 1/4 bore, 5/8 OD, sealed bearing",
    1127: f"{BALL}, {INCH}, R8, R8-2RS, R8RS, 1/2 bore, 1-1/8 OD, sealed bearing",
    1135: "needle bearing, needle roller bearing, drawn cup bearing, HK2512, HK25x32x12, 25x32x12, 25mm bore, caged needle, no inner ring",

    # --- mechanical -------------------------------------------------------
    1128: "chain roller, chain guide, chain tensioner, tensioner wheel, idler wheel, roller, 10mm bore, sealed bearing, swingarm, pit bike",
    1129: "steering damper, steering stabilizer, damper, adjustable damper, motorcycle damper, 10 inch, rudder pedals, flight sim",
    1132: "extension spring, tension spring, spring, loop end spring, 4-1/2 inch, 4.5 in, 15/32 OD, .041 wire, zinc plated",
    1133: "extension spring, tension spring, spring, loop end spring, Prime-Line, SP 9602, 7/16 OD, 1-1/2 inch, .047 wire, nickel plated",

    # --- hardware ---------------------------------------------------------
    1131: "screw, flat head screw, countersunk screw, flathead, socket head, hex socket, allen screw, machine screw, M3, M3x10, 10mm, stainless",
    1141: "T-nut, tee nut, T nut, drop in nut, slide in nut, 2020 extrusion, aluminium extrusion, aluminum extrusion, V-slot, assortment, 120pc",
    1142: "bearing balls, steel balls, loose balls, chrome steel balls, SAE, imperial, 3/32, 1/8, 5/32, 3/16, 7/32, 1/4, assortment, Breezliy",
    1146: "foam tape, weatherstrip, weather stripping, weatherstripping, neoprene foam, CR foam, seal tape, adhesive foam, door seal, Yotache",
    1147: "foam gasket, gasket strip, foam strip, adhesive foam, self adhesive, sealing strip, 34 inch, 7/8 wide",
    1149: f"{CORD}, O-ring cord, nitrile cord, NBR cord, solid cord, 3mm, 1/8 inch, uxcell, 8m",
    1150: f"{CORD}, sponge cord, foam cord, neoprene cord, closed cell, 1/8 inch, 3mm, Canal Rubber",
    1151: f"{CORD}, sponge cord, foam cord, neoprene cord, closed cell, 3/16 inch, 4.8mm, Canal Rubber",

    # --- power / motors ---------------------------------------------------
    1138: "motor speed controller, PWM controller, DC motor controller, speed control, reversing, forward reverse, LM324, STP75NF75, 10A, potentiometer",
    1139: "DC motor, brushed motor, 775 motor, RS-775, 12V motor, 5mm shaft, high torque motor, mounting bracket, X002PW3B7B",
    1143: "fuse, glass fuse, cartridge fuse, 5x20mm, 5x20, 250V, fuse kit, fuse assortment, 15 values, XFFCSEC",

    # --- modules / cables -------------------------------------------------
    1145: "micro HDMI, microHDMI, Type D, HDMI adapter, HDMI cable, adapter cable, pigtail, Type A female, 150mm, Raspberry Pi",
    1148: "QT Py, QTPy, RP2040, Adafruit 4900, PID 4900, microcontroller, dev board, development board, USB-C, STEMMA QT, Qwiic, NeoPixel, XIAO",

    # --- bare PCBs (panel codes are the only thing telling them apart) -----
    1152: f"{PCB}, G1000, NXi, GMA1347, shield, Peter Eier, littlehelpers, MEGA 2560, Rev 3",
    1153: f"{PCB}, G1000, NXi, v2.3, left side, left panel, button panel, encoder panel, FlightSimDIY, Y61, 4539410A",
    1154: f"{PCB}, G1000, NXi, v2.3, right side, right panel, button panel, encoder panel, FlightSimDIY, Y60, 4539410A",
    1155: f"{PCB}, G1000, NXi, v2.3, softkeys, soft keys, softkey strip, 12 keys, bottom strip, FlightSimDIY, Y62, 4539410A",
    1156: f"{PCB}, GMA1347, audio panel, control board, v2.2, pre-NXi, FlightSimDIY, Y18, 4539410A",
    1157: f"{PCB}, G1000, control board, v2.3, non-NXi, MEGA 2560 PRO MINI, multiplexer, 16 channel, FlightSimDIY",
}


def trim(s):
    s = s.strip()
    if len(s) <= LIMIT:
        return s
    cut = s[:LIMIT]
    if "," in cut:
        cut = cut[: cut.rfind(",")]
    return cut.strip()


ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

for pk, why in sorted(SKIP.items()):
    print(f"-  {pk}: SKIPPED on purpose — {why}")

overlap = set(SKIP) & set(KW)
if overlap:
    print(f"!! pk in BOTH skip and write lists: {sorted(overlap)} — aborting")
    sys.exit(1)

wrote = skipped_nonempty = missing = failed = trimmed = 0
for pk in sorted(KW):
    kw = trim(KW[pk])
    if len(KW[pk].strip()) > LIMIT:
        trimmed += 1
    p = Part.objects.filter(pk=pk).first()
    if not p:
        print(f"?? {pk}: no such part")
        missing += 1
        continue
    if (p.keywords or "").strip():
        print(f"=  {pk}: keywords already set — left alone ({p.keywords[:45]})")
        skipped_nonempty += 1
        continue
    if not a.commit:
        print(f"~  {pk}: WOULD set [{kw}]")
        continue

    Part.objects.filter(pk=pk).update(keywords=kw)
    fresh = Part.objects.get(pk=pk)
    if (fresh.keywords or "").strip() == kw:
        print(f"+  {pk}: {kw[:70]}")
        wrote += 1
    else:
        print(f"!! {pk}: write did not stick (row reads {fresh.keywords!r})")
        failed += 1

EMPTY = Q(keywords="") | Q(keywords__isnull=True)
print(f"\nwrote={wrote} skipped_nonempty={skipped_nonempty} missing={missing} "
      f"failed_verify={failed} trimmed_to_250={trimmed} "
      f"{'(DRY RUN)' if not a.commit else ''}")
print(f"keywords still empty: {Part.objects.filter(EMPTY).count()} / {Part.objects.count()}")
print(f"  of which deliberate tombstones: {len(SKIP)}")
