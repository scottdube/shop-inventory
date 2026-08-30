"""Queue D batch: search keywords for parts pk 661-745 (the Xuansn/15-value
electrolytic trays, the SparkFun beginners kit, the Pololu jumper wires, and
the toggle/tactile switch drawer).

The table is embedded rather than shipped as a TSV because `itq run` copies
exactly one file to the Mini — a separate data file would need a second,
differently-shaped transfer, and an unattended run cannot afford a command
shape that has to be approved.

Guards are lifted verbatim from kw_apply.py and are load-bearing:
  * never overwrite a non-empty keywords field (it may be Scott's own wording)
  * verify by re-reading — .save()/.update() on this install has reported
    success and written nothing (docs/TRAPS.md)

Vocabulary choices worth keeping:
  * every electrolytic carries its BODY SIZE, because footprint is part
    identity here and "47uF" alone matches six different physical parts
  * "mfd" is included on electrolytics — the old microfarad marking, which is
    what is printed on anything salvaged from older gear
  * ceramics carry the three-digit MARKING CODE and the alternate unit
    spelling (100nF / 0.1uF), because the cap on the bench is labelled 104
  * abbreviations AND their expansions, since InvenTree search is substring:
    "LDR" does not match "light dependent resistor"

Two deliberate skips, both tombstones, same reasoning as pk 600 and pk 502 in
earlier batches: a retired duplicate and a part self-described NOT INVENTORY.
Keywording them would put dead rows into live search results.
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

SKIP = {
    662: "retired duplicate of 683 — tombstone, keep it out of search",
    734: "self-described NOT INVENTORY (gifted) — same rule as pk 600/502",
}

ELEC = "electrolytic capacitor, aluminium electrolytic, aluminum electrolytic, radial can, polarised cap, polarized cap, mfd"

KW = {
    # --- Xuansn 270pc tray -------------------------------------------------
    661: f"{ELEC}, 4.7uF, 4u7, 450V, high voltage cap, 8x12, 8x12mm, Xuansn",
    663: f"{ELEC}, 47uF, 25V, 5x11, 5x11mm, Xuansn",
    664: f"{ELEC}, 47uF, 35V, 5x7, 5x7mm, Xuansn",
    665: f"{ELEC}, 47uF, 200V, high voltage cap, 13x21, 13x21mm, Xuansn",
    666: f"{ELEC}, 470uF, 50V, 10x20, 10x20mm, Xuansn",
    667: f"{ELEC}, 47uF, 50V, 6.3x11, 6x11, 6.3x11mm, Xuansn",
    668: f"{ELEC}, 470uF, 10V, 6.3x11, 6x11, 6.3x11mm, Xuansn",
    669: f"{ELEC}, 470uF, 16V, 8x7, 8x7mm, Xuansn",
    670: f"{ELEC}, 470uF, 25V, 8x12, 8x12mm, Xuansn",
    671: f"{ELEC}, 47uF, 250V, high voltage cap, 13x21, 13x21mm, Xuansn",
    672: f"{ELEC}, 470uF, 63V, 13x21, 13x21mm, Xuansn",
    # --- 15-value 200pc tray ----------------------------------------------
    673: f"{ELEC}, 0.1uF, 100nF, 50V, 4x7, 4x7mm",
    674: f"{ELEC}, 0.22uF, 220nF, 50V, 4x7, 4x7mm",
    675: f"{ELEC}, 0.47uF, 470nF, 50V, 4x7, 4x7mm",
    676: f"{ELEC}, 1uF, 1u0, 50V, 4x7, 4x7mm",
    677: f"{ELEC}, 2.2uF, 2u2, 50V, 4x7, 4x7mm",
    678: f"{ELEC}, 3.3uF, 3u3, 50V, 4x7, 4x7mm",
    679: f"{ELEC}, 4.7uF, 4u7, 50V, 4x7, 4x7mm",
    680: f"{ELEC}, 10uF, 25V, 4x7, 4x7mm",
    681: f"{ELEC}, 22uF, 25V, 4x7, 4x7mm",
    682: f"{ELEC}, 33uF, 16V, 4x7, 4x7mm",
    683: f"{ELEC}, 47uF, 16V, 4x7, 4x7mm",
    684: f"{ELEC}, 47uF, 25V, 5x7, 5x7mm",
    685: f"{ELEC}, 100uF, 10V, 4x7, 4x7mm",
    686: f"{ELEC}, 100uF, 25V, 6x7, 6x7mm",
    687: f"{ELEC}, 220uF, 10V, 6x7, 6x7mm",
    # --- ceramics: the bench label is the marking code, not the value ------
    688: "ceramic capacitor, MLCC, multilayer ceramic, disc cap, 10pF, 10 pf, marking 100, code 100, small value cap",
    689: "ceramic capacitor, MLCC, multilayer ceramic, disc cap, 100pF, 0.1nF, marking 101, code 101",
    690: "ceramic capacitor, MLCC, multilayer ceramic, disc cap, 1nF, 1000pF, 0.001uF, marking 102, code 102",
    691: "ceramic capacitor, MLCC, multilayer ceramic, disc cap, 10nF, 0.01uF, marking 103, code 103",
    692: "ceramic capacitor, MLCC, multilayer ceramic, disc cap, 100nF, 0.1uF, marking 104, code 104, decoupling cap, bypass cap",
    # --- SparkFun beginners kit -------------------------------------------
    693: f"{ELEC}, 1uF, 50V, 5x11, 5x11mm, SparkFun kit",
    694: f"{ELEC}, 10uF, 25V, 5x11, 5x11mm, SparkFun kit",
    695: f"{ELEC}, 100uF, 25V, 6x12, 6x12mm, SparkFun kit",
    696: "diode, signal diode, switching diode, small signal diode, 1N4148, 4148, DO-35, general purpose diode",
    697: "diode, rectifier diode, power diode, 1N4001, 4001, DO-41, 1A rectifier, bridge leg",
    698: "female header, socket header, pin socket, header strip, 0.1 inch, 0.1in, 2.54mm, breakaway header, snappable, dupont, 20 pin",
    699: "male header, pin header, header strip, 0.1 inch, 0.1in, 2.54mm, breakaway header, snappable, dupont, berg, 20 pin",
    700: "slide switch, power switch, mini slide switch, on off switch, panel switch, SparkFun kit",
    701: "tact switch, tactile switch, pushbutton, push button, momentary switch, 6x6, 6x6mm, through hole button, breadboard button, 4 pin",
    702: "trimmer potentiometer, trimpot, preset pot, variable resistor, adjustment pot, 10k, 10 kohm, 10K ohm",
    703: "op amp, opamp, operational amplifier, LM358, 358, dual op amp, DIP-8, comparator, analog IC",
    704: "LDO, low dropout regulator, voltage regulator, linear regulator, 3.3V, 3v3, 3.3 volt, LD1117, 1117, TO-220",
    705: "voltage regulator, linear regulator, 5V regulator, 5 volt, 7805, L7805, LM7805, 78xx, TO-220, 1.5A",
    706: "555, NE555, timer IC, timer chip, oscillator, astable, monostable, pulse generator, DIP-8",
    707: "LED, green LED, 5mm LED, indicator LED, through hole LED, T-1 3/4, lamp",
    708: "LED, yellow LED, 5mm LED, indicator LED, through hole LED, T-1 3/4, lamp",
    709: "LED, red LED, 5mm LED, indicator LED, through hole LED, T-1 3/4, lamp",
    710: "seven segment, 7 segment, 7 seg, digit display, numeric display, LED display, single digit, common anode, red display",
    711: "LDR, light dependent resistor, photoresistor, photo resistor, photocell, light sensor, CdS cell, ambient light sensor",
    # --- Pololu jumper wire ribbons ---------------------------------------
    714: "jumper wires, jumper leads, dupont wires, breadboard wires, ribbon cable, male to male, M-M, 3 inch, 3in, premium jumper, Pololu 4562",
    715: "jumper wires, jumper leads, dupont wires, breadboard wires, ribbon cable, male to female, M-F, 3 inch, 3in, premium jumper, Pololu 4561",
    716: "jumper wires, jumper leads, dupont wires, breadboard wires, ribbon cable, male to male, M-M, 6 inch, 6in, premium jumper, Pololu 4565",
    717: "jumper wires, jumper leads, dupont wires, breadboard wires, ribbon cable, male to female, M-F, 6 inch, 6in, premium jumper, Pololu 4564",
    # --- power / panel / modules ------------------------------------------
    719: "wirewound resistor, power resistor, dummy load, load resistor, braking resistor, 10 ohm, 10R, 10W, RX24, aluminium clad, aluminum shell, chassis mount",
    720: "potentiometer, pot, rotary pot, panel pot, 220k, 220 kohm, 220K ohm, linear taper, volume control, with knob, dial",
    721: "trimmer potentiometer, trimpot, multiturn trimmer, preset pot, variable resistor, calibration pot, RM063, assortment kit, 500R to 1M",
    722: "pilot light, indicator lamp, panel indicator, signal light, dash light, LED indicator, 10mm, 12V, red, waterproof, IP67, metal bezel",
    723: "buck boost converter, DC-DC converter, step up step down, adjustable regulator, switching regulator, SMPS, power module, 8A, 5-30V",
    724: "pilot light, indicator lamp, panel indicator, signal light, LED indicator, 8mm, 12V, red, waterproof, metal, no leads",
    726: "HDMI to CSI, CSI-2 bridge, HDMI capture, video input, raspberry pi camera port, TC358743, 15 pin FFC, pi adapter",
    727: "microwave radar, doppler sensor, motion sensor, motion detector, presence sensor, occupancy sensor, radar module, RCWL-0516, RCWL",
    729: "nRF24L01 adapter, NRF24, socket adapter, adapter plate, breakout board, 8 pin socket, radio module base, wireless module adapter",
    730: "arduino uno, uno r3, arduino compatible, clone board, dev board, development board, microcontroller board, ATMEGA328P, CH340, SMD",
    731: "T12 controller, T12 station, soldering station kit, solder station, temperature controller, DIY soldering station, iron controller",
    732: "pigtail, RF cable, antenna cable, coax cable, U.FL, IPEX, IPX, SMA female, RP-SMA, RPSMA, 1.13mm, 15cm",
    733: "binding post, banana jack, banana socket, speaker terminal, amplifier terminal, panel mount terminal, red and black pair, 4mm",
    735: "PZEM-031, PZEM, DC energy meter, watt meter, power meter, volt amp meter, kWh meter, panel meter, battery monitor, 20A, LCD module",
    # --- switch drawer ------------------------------------------------------
    736: f"{ELEC}, 22uF, 16V, 4x7, 4x7mm",
    737: f"{ELEC}, 47uF, 10V, 4x7, 4x7mm",
    738: "tact switch, tactile switch, push button, pushbutton, momentary switch, 6x6, 6x6mm, through hole, SPST, breadboard button",
    739: "power button, push button, pushbutton, momentary button, panel button, red button, 6mm, Adafruit 3104, adafru.it 3104",
    740: "power button, push button, pushbutton, momentary button, panel button, blue button, 6mm, Adafruit 3105, adafru.it 3105",
    741: "tact switch, tactile switch, push button, momentary switch, 6x6, 6x6mm, assortment, mixed, grab bag, salvage, spares",
    742: "toggle switch, sub miniature toggle, subminiature, mini toggle, panel switch, 3A 250V, blue body, bat handle",
    743: "toggle switch, mini toggle, miniature toggle, MTS-101, SPST, on off toggle, 2 pin, 6A 125V, panel mount, blue body",
    744: "toggle switch, mini toggle, miniature toggle, C&K, CK, SPDT, on-on, maintained, latching toggle, 3 pin, 3 leg, vintage",
    745: "toggle switch, mini toggle, miniature toggle, C&K, CK, SPDT, momentary, spring return, momentary toggle, 3 pin, 3 leg, vintage",
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
