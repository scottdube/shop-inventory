# Open work

One list, because "still to do" sections were accumulating in six separate
docs and a backlog you cannot read in one place is hiding, not parking.

Add here when something is deliberately deferred. Delete when done — this is a
queue, not a log.

## The dead QL-810W has to be de-modified before it ships back — by Nov 19

The first printer is physically still on the electronics bench with **two wires
soldered to the board**: 25 V onto the rear lug of barrel jack J1 and a ground
lead, run out through the case. It is powered from the bench supply.

Before it goes to Staples: **unsolder both jumpers, reinstall the bottom cover.**
Scott's read is that the only remaining evidence will be a dab of solder on the
back of the jack's centre pin, which nobody will open the case to find. The
return window runs to **2026-11-19**, so there is no rush — but a printer that
arrives visibly hacked is a return Amazon can refuse, and that is $129.99.

Send it back with **its own adapter and whatever else was in its box**. The new
unit came with its own.

**Related, and easy to forget: the replacement is ALSO an Amazon Renewed refurb.**
Its guarantee window runs from delivery on **2026-08-26**. The first one died at
28 jobs and five days, so a failure in the next few months is a claim, not a
purchase. Do not let that window pass unnoticed the way the first failure did.

**Liveness checked 2026-09-02** (`lpstat -W completed -o QL810W`): jobs 36–75,
**40 jobs since put-away on 2026-08-26**, most recent 2026-09-01 17:46, queue
idle. The replacement is therefore already past the 28-job point at which unit #1
died. This check is the whole watch — the first failure hid for four days because
nobody read the completed list, and "the queue is accepting" is a claim about
CUPS, not about the printer.

## B2-R3, the 1/4-20 row, has outgrown itself — reorder it

Scott 2026-08-26: *"I think we're gonna have to redo that entire row... park
them somewhere in that wall bin until we can get around to moving a bunch of
stuff around."*

**All eight cells are occupied**, and the family does not fit:

| cell | holds |
|---|---|
| B2-R3C1 | hex nuts, 95 |
| B2-R3C2 | nylon-insert locknuts, 95 |
| B2-R3C3 | flat washers 1/4 x 5/8 stainless, 79 |
| B2-R3C4 | SHCS 3/8 in, 30 |
| B2-R3C5 | SHCS 1/2 in, 84 |
| B2-R3C6 | SHCS 3/4 in, 17 |
| B2-R3C7 | SHCS **1 in**, 40 |
| B2-R3C8 | SHCS 1-1/2 in, 50 |

**The 1-1/4 in length (#959, 50) is homeless** — it sits at B2 cabinet level
with no cell, because there is no cell left. Three cells go to nuts and washers
and five to screws, and the family has six lengths. The row was full before
today.

And now a **Kerr Lakeside box of 1/4-20 x 1 in black-oxide** has surfaced off
the wire shelves — the same part as C7, from a different vendor. Merging it into
C7 would put ~90 screws in one cell of a row that is already over capacity.

**Parked, not merged — done 2026-08-26.** The Kerr box (45 counted, of a box of
50) is now its own row at **B2-R4C7**, a temp cell. Two rows of one part in two
locations is allowed — the invariant is one row per part per *location* — and it
records the truth, which is that #955 is in two places and totals 85.

`default_location` was deliberately NOT moved to B2-R4C7. Policy is that
default_location is where a spare goes home, never a staging area; pointing it
at a temp cell is how a temp cell becomes permanent.

**For the rebuild:** B2-R5, R6 and R7 are entirely empty, 12 large cells. The
question to settle is whether nuts and washers should share a row with screws at
all, or whether 1/4-20 wants a whole row for lengths and its consumables move
elsewhere. Decide that before moving anything, or it gets moved twice.

## B1 metric fastener cabinet — LAY IT OUT FRESH (Scott, 2026-08-27)

**Scott 2026-08-26: "I want to start fresh on that" — tomorrow.** So the
legacy labels are NOT the plan, and the earlier proposal to load parts into
the cells they already name is withdrawn.

That is the right call and B1's own record says why: *"Legacy labels READ FROM
A PHOTO and partial... NOT WALKED."* Those labels are an inherited guess. Filing
into them would cement a layout nobody chose, using a scheme nobody checked, and
make it look deliberate.

**The state to start from, measured 2026-08-26:**

- **27 bags sit at B1 cabinet level with no cell.** That is most of the metric
  fastener stock.
- Only **four cells in the whole cabinet hold anything**: R1C1 (M3 x20 *and*
  x25 together), R1C8 (M3 nuts), R2C1 (M4 nuts), R5C4 (M8 socket head + an M16
  eyebolt).
- 44 cells, 40 empty.
- The legacy labels claim R1C2/C4/C5 are `M3 .5 x25/x35/x40`. All three are
  empty; those screws are in the pile.

**The decision to make first is the SORT KEY, because everything else follows
from it.** The legacy scheme sorts by thread then length — and that is exactly
the scheme that cannot express what is now in the cabinet:

- **Head type.** There are M3 flat heads *and* M3 pan heads. #1131 is M3x10
  flat, #983 is M3x10 pan. Same thread, same length, different screw.
- **Material.** #980 is M3x30 **black-oxide alloy**; #1131 is M3x10
  **stainless**. Alloy is stronger and rusts; stainless is weaker and does not.
- **Head type and material are what get grabbed wrong.** Length is what is easy
  to eyeball. A scheme that sorts by the easy thing and mixes the hard ones is
  backwards.

**Do not write locations from a keyboard.** Filing means somebody carries bags
to cells; a location nobody walked is what stranded the SHT31 rows in August.

Bring: `scripts/b1_state.py` does not exist yet — the equivalent of
`rb_state.py` for this cabinet would make the walk readable instead of
maintained by hand.

## SHT31-D — four owned, location unknown — WRITE OFF 2026-09-02 if not found

Stock [573] and [574], 2 + 2, no location. Created by receiving PO-0028 **on
paper** on 2026-08-23: the receipt allocated them to a drawer by plan, nobody
carried anything there, and Scott searched B3-R4C8 and found nothing. PO-0028
is itself a stub whose line item was *inferred* from an Amazon confirmation
carrying no line items ("1 Hardware item", $16.9x). Amazon reports it
delivered and Scott recalls the order as the SHT31s, so the purchase is
probably real — owned, location unknown, which is a fact. "Two are in B3-R4C8"
was not.

**Scott 2026-08-26: leave one more week; if not located by 2026-09-02, write
them off.** The decision is made. On that date the only question is *found or
not*.

Part 292 currently reads **8 on the books, 4 findable**. The findable four are
stock [688] (RB-12) and [689] (B3-R4C8), received 2026-08-26 against PO-0139
and counted in hand.

**Do not fold 573/574 into 688/689 to make the number tidy.** They are separate
claims; merging hides the open question rather than answering it. If they turn
up, they merge into 689 then — one row per part per location.

## Red Bins — walk and empty out

**Goal, Scott 2026-08-23: get the rack as close to empty as possible.** *"We
should file it in one of the wall bins and get it out of these red bins. Goal
is to get down to zero if you can on red bins. We won't get there, but cleaning
them out."*

The rule that follows, now on the rack's own record: **a red bin is for a
project kit being worked, or for bulk with nowhere better. Loose parts belong
in the wall cabinets, where they have a home and an address.** Anything found
loose in a red bin gets filed to the wall rather than tidied within the rack.

State after the 2026-08-25 walk, 28 bins:

| | |
|---|---|
| walked | **all 25** — the rack is done |
| holds stock | 14 |
| verified empty | 7 (RB-09, 10, 15, 16, 18, 21, 23) |
| declared, not empty | 4 (RB-01/02/05 free storage, RB-08 prototypes, RB-19 VFD salvage) |
| label only, no bin | RB-26, RB-27, RB-28 — marked structural |

**The rack has 25 bins, not 28.** The location tree was built from the label
run; three labels were printed with no container behind them. Counts read off
`scripts/rb_state.py`, not maintained by hand.

**A bin can also be a tool's shelf, and that is a third thing.** RB-13 holds
the FX-951 with its cord run out of the bin and its handpiece on the bench.
That is neither a project kit nor free storage, and it is **not emptiable** —
the walk should stop counting it toward the goal. Read the rack rule as: a kit
being worked, bulk with nowhere better, or a tool in service standing in its
own bin.

- [x] ~~**RB-17**~~ — **done 2026-08-23.** Four displays moved out to B3-R5C1
      (ESP32-S3-LCD-2.8C #1072, waveshare 1.28in round #70, bare panel
      JT280-022-02A0 #1073 measured 72-73 mm, and its jxl+ V1.1 driver board
      #1074 — the last two are a matched pair and their descriptions say so).
      RB-17 now holds exactly one thing: the **MPXV6115VC6U vacuum sensor** for
      the **Vacuum Controller** project, which is the first red bin to end up
      matching the rack's own rule.

      **Two corrections came out of it.** #107's location was wrong — it said
      `Unfiled - Machine Shop` and the sensor was in RB-17 all along; a
      surface-mount part was never plausibly living with the BT30 toolholders.
      And its name says "Pressure Sensor" because that is the vendor's word,
      while the part reads **0 to −115 kPa** and cannot measure positive
      pressure at all. It is the opposite half of the scale from the 1/8 NPT
      gauge transducers in B3-R7C2 and is not interchangeable with them.

- [x] ~~Settle what the bare round panel (#1073) is~~ — **done 2026-08-23,
      by counting.** 40 contacts on the flex: it is the **480x480 ST7701S**
      class, SPI+RGB, so SPI carries only initialisation and pixels go over a
      parallel bus. It **cannot** be driven from plain SPI — it needs an
      ESP32-S3's RGB LCD peripheral — and its natural role is a **spare panel
      for the ESP32-S3-LCD-2.8C (#1072)**, which is that panel plus an S3.
      Standalone use would also need a backlight boost, which nothing in the
      drawer provides.

- [ ] **The jxl+ board (#1074) is ORPHANED.** The 40-pin count disproved the
      pairing rather than leaving it open: an 8-pin SPI header cannot carry an
      RGB bus. Nothing else in the shop obviously matches it — the 1.28in round
      LCD (#70) is a complete module with its own PCB. It stays filed with the
      displays, flagged, until a panel turns up whose flex fits its connector.

      *Method worth reusing:* the question "do these two go together" was
      settled by counting contacts, in seconds, after two rounds of plausible
      reasoning had failed to. The earlier "matched pair" claim came from both
      items being round and sitting in one bin.

- [ ] **#94 is a likely duplicate of #107** — same MPN, MPXV6115VC6U, zero
      stock and never any. Flagged rather than retired, because nobody has
      confirmed the two records came from the same listing.

- [ ] **RB-18 through RB-28 have never been opened.** The largest single block
      of unknown space left in the shop now that the bin wall is at 89%.
- [ ] **RB-12, the RAT GDO kit** — 9 uncounted rows, skipped deliberately on
      2026-08-23. One stop converts nine purchased figures into counts.
- [x] ~~**RB-13, the Hakko FX-951**~~ — **settled 2026-08-25, by photograph.**
      It is the station itself (#311), **in service**, standing in the bin with
      its cord run out and its handpiece in a 599B cleaner on the bench. Not a
      spare, not accessories. One row at qty 1, deliberately **not counted**,
      following the FR-301 precedent. #311's `default_location` was the bare
      site root and is now empty — there is no spare station, so there is no
      place a spare goes home to.

- [ ] **The FX-951 tips are in BL-D1** (Scott, 2026-08-25) — recorded on the
      drawer, **not counted**, and *which* tips is still open: #333 (T15, the
      correct cartridge for the FM-2027 handpiece) and #160 (T12) both sit at
      zero stock with no rows, and "the tips" could be either or both. One stop
      at BL-D1 closes it. **If the T12 set is there, flag it**: Hakko never
      states T12 fits the FM-2027, and the cartridge carries the heater and
      sensor.

- [ ] **RB-14 holds more than its five rows.** A jig labelled *"JIG DONT TOSS
      OUT"*, a white enclosure and a perfboard with a toroid are in there;
      Scott, 2026-08-25: the jig is part of that bin's group. So RB-14 needs
      the rest of its contents catalogued — the five component rows are the AC
      wall adapter allocation, not an inventory of the bin.

      **This is the finding that outlives RB-14**, and it is now in
      `docs/TRAPS.md`: a bin reading *"5 rows, 5 counted"* says the ROWS were
      counted. It says nothing about whether the bin's contents are all on the
      books, and the walk board renders the two identically.

- [x] ~~**READ THE MEANLIN GAUGE'S DIAL**~~ — **done 2026-08-25, by looking.**
      #1097 is a **vacuum gauge: 0 to −30 inHg / 0 to −1 bar, negative only**,
      dual scale. Renamed from "Pressure Gauge", which is the word that would
      have sent the next reader hunting for a positive range it does not have.
      It is the correct half of the scale for the Vacuum Controller and pairs
      with #107. −30 inHg is −101.6 kPa — the full physical vacuum range — so
      the sensor's −115 kPa spec runs past anything a vacuum can reach and the
      gauge is not the narrower instrument in practice.

- [ ] **MEASURE THE GAUGE: face diameter and thread OD (#1097, RB-17).**
      Neither is known and **no digital route can supply them** — checked
      2026-08-25. MEANLIN sells this same −30inHG~0Psi gauge in 2in, 2.5in and
      3in faces and in both 1/8in and 1/4in NPT; ASIN `X002SLRYVX` returns no
      results on Amazon; and the July 2025 order mail truncates the title.
      1/8 NPT is ≈10.3 mm OD and 1/4 NPT ≈13.7 mm — not confusable. Measure the
      **gauge's** thread: a brass compression fitting is made up on the stem.

      **Scott expects BOTH** — the larger thread on the gauge with a bushing
      stepping down to the smaller — and will check next time he is in the lab.
      Recorded as an expectation, not a measurement. Plausible: MEANLIN ships
      at least one gauge in this family *"with Stainless Steel Hex Bushing"*,
      though that variant is the −30inHG~60Psi 1/4in NPT — a different range,
      so it corroborates the practice, not this unit. **If it is a gauge in a
      bushing, record both numbers and say which is which**: what the gauge
      *is* and what it currently *presents to a fitting* are two facts, and a
      single "thread size" field would lose one of them.

      **The "3in dial" recorded earlier today was wrong and is retracted.** It
      was read off the box's elided Amazon label, `MEANLIN MEASURE -3… Gauge`,
      where the `-3` is the head of `-30inHG` — the range. See `docs/TRAPS.md`.

- [x] ~~**FLEX A NEWISHTOOL SQUEEGEE (#791, RB-22)**~~ — **done 2026-08-25.**
      **Silicone**, confirmed by hand. The description was right and the name
      stands; the doubt came from a photograph, where semi-rigid plastic and
      soft silicone look the same. Located, not re-counted: #791 already
      carried the count and the provenance, filed at the **rack** with no bin
      number, and it was the last row at that level — the rack is now clear.

- [x] ~~**The motorized water shutoff valve has no build order**~~ —
      **BO-0014 created 2026-08-25** on Scott's yes, against new assembly part
      #1098 in Projects. BOM carries the servo only.

- [ ] **Add the printed mounting parts to BO-0014's BOM when the geometry
      settles.** Safe to add later *because the build is not complete* —
      completing one freezes its line items, and lines added afterwards never
      appear.

      The prints deliberately carry **no stock row** — a prototype print is the
      state of an experiment, not stock, and a quantity would imply a spare
      that could be reprinted identically. Same treatment as RB-08.

- [ ] **BACKFILL THE eBay ORDER HISTORY — ~201 orders, 1 PO on file.** The
      RB-20 kits were bought 2026-06-16, ~70 days before the walk, against a
      sweep that runs over ~45 days. eBay is on the registry's `known` list, so
      this is **not** the unknown-vendor blind spot and adding it to a list
      fixes nothing — it needs a backfill. eBay mail carries the **full** item
      title, unlike Amazon's truncated bodies, so it can identify unknown items
      rather than only matching known ones. See `docs/TRAPS.md`.

- [x] ~~**RB-21**~~ — **emptied 2026-08-25.** Held the MEANLIN gauge; it moved
      to RB-17 to join the MPXV6115VC6U, on Scott's call. One project, one bin
      — the rack's own rule — and it takes a bin off the board rather than
      leaving the Vacuum Controller spanning two the way the bench PSU does
      across RB-07/RB-08.

- [ ] **RB-20 — three eBay soldering practice kits**, counted at 3 by Scott
      2026-08-25 and created as #1096, because **nothing in the catalogue
      matched**. Two things still open: the **eBay listing title** (the string a
      future duplicate would arrive under), and **whether a practice PCB is in
      the bin** — only the component bag was seen.

## At the bench

- [ ] **Strip the dead VFD — the salvage lives in RB-19.** Located by Scott
      2026-08-25 during the Red Bin walk. This entry previously read
      *"RB-18 area / bench"*, which was a guess written at the bench and
      is now known wrong twice over: RB-18 was verified EMPTY the same
      day. Six parts catalogued
      2026-08-23 with identify-on-the-board and test-before-use notes; nothing
      filed except the fan, which is already tested and in B3-R5C3.

      | # | part | test |
      |---|---|---|
      | 1077 | Heatsink, extruded finned | measure TO-220 hole spacing |
      | 1078 | Fan X6015D12MB 60x15 12V | **done — filed B3-R5C3** |
      | ~~1075~~ | ~~Relay Churod A1-S-112VA~~ | **broke on removal — scrap** |
      | 1076 | Cap 820uF 400V RUC CD293 x2 | **TESTED GOOD** — needs a home |
      | 1079 | Terminal block 7.62mm 4-pos | **filed A3-R7C4** |
      | 1081 | Terminal block 7.62mm 5-pos | **filed A3-R7C4** |
      | ~~1080~~ | ~~IGBT DXG20N65FS x6~~ | **ALL SIX DEAD — scrap** |

      **The failure mode is now known, 2026-08-23.** All six IGBTs tested dead
      out of circuit — every gate destroyed — while the DC bus is NOT shorted.
      Those two facts together rule out the ordinary modes: a shorted device
      shows on the bus, a single failure is one device. Six at once with an
      intact power path means something hit every gate together — a gate-drive
      supply gone overvoltage, or a surge coupling into the gate circuits. The
      power stage did not kill itself.

      **That raises the bar on the rest.** Whatever punched six gate oxides went
      through everything else. **Bin the varistor** — first line of defence,
      likely died doing its job. And treat the bus caps with more suspicion than
      a normal salvage: a surge is exactly the history that leaves an
      electrolytic measuring fine and behaving badly.

      The one good semiconductor on the board was an **MS5N10DS**, the little
      control-supply switcher, which tested clean (N-channel enhancement FET,
      Vt 3.86V). Not catalogued — a generic small MOSFET worth pennies.

      Also grab: the **thermistor** bolted to the heatsink end (over-temp
      sensor) and the **long black bar** across the board — probably a bleed or
      inrush resistor, unread.

      **TOMORROW: file the two bus caps, and pick their drawer.** Both tested
      good on 2026-08-23 — 761 and 737 uF against 820 nominal, ESR 0.21 ohm
      (including clip leads, so lower in reality), Vloss 0.8%, and matching each
      other within 3%. The match is what settles it: two caps with identical
      history should age together, and one lagging its twin would have been the
      fingerprint of surge damage. Neither lagged, so the event that destroyed
      six gate oxides never reached the bus.

      The choice is a size question. The cans are roughly 35mm dia x 50mm tall:

      | drawer | size | fit |
      |---|---|---|
      | **B3-R5C4** | 116 x 152 x 56 mm | stand upright with room — **recommended** |
      | A3-R7C5 | 56 x 152 x 40 mm | must lie on their sides, end to end, and fill it |

      B3-R5C4 is the better home: standing is easier on the leads and the
      markings are readable when the drawer opens. A3-R7C5 would keep them in
      the power row beside the mains-protection set and the terminal blocks,
      which is the only argument for it — and laying two big cans down to fit a
      drawer they do not suit is the wrong reason to choose one.

      **Also still open:** measure the heatsink's TO-220 hole spacing, then it
      joins the fan in B3-R5C3.

      **Before scrapping the board:** discharge the bus caps, and photograph the
      SOLDER side. The component side is already photographed; the solder side
      is the one that cannot be recovered afterwards. It is e-waste, not trash.



- [ ] **TEST the 100 PSI pressure transducer (#1071).** Scott, 2026-08-23: *"I
      have a recollection that there could have been a problem with this one.
      So it does need to be tested."* Its wires are cut and stripped, so it has
      been wired up at least once. Its stock row is **QUARANTINED** until it
      reads correctly — that is the tracking, not a note somebody has to
      remember to read.

      A bench test is minutes: 5 V across red/black, meter on the signal wire,
      and it should sit near 0.5 V at atmosphere and rise smoothly with
      pressure. If it reads rail-high, rail-low, or does not move, it is dead
      and should be marked DAMAGED rather than left QUARANTINED forever.

      **The sibling question is already closed:** #219's pair read **150 PSI**,
      confirmed by Scott the same day, so that part's long-standing "PSI rating
      NOT verified" flag is retired. Two ratings, two parts — 150 in B3-R7C2,
      100 quarantined.


- [ ] **BL-D2 wiring drawer — identify the rest.** Four items filed (depin kit,
      UV solder mask, UV lamp, ACT-232). The photo shows at least four more:
      Klein Tools stripper, Haisstronica, a hex self-adjusting ferrule crimper,
      two ratcheting crimpers. Candidates already in the catalogue: #244
      Ferrules Crimper Pliers Set, #337 SOMELINE ferrule ratchet, #228 IWISS
      Dupont, #456 iCrimp open-barrel. **Do not guess from a photo** — that has
      gone wrong twice. Each one also needs a problem-statement per the tool
      convention in CONTEXT.md.
- [ ] **Inventory the Air System bin.** It is a clear lidded bin on WS2 with 7
      items itemised and the bulk — tubing coils, bagged push-to-connect
      fittings, couplers — declared uncounted. Scott: *"I can pull this off the
      shelf and inventory this in the future rather than get bogged down with it
      right this minute."* Deliberately deferred, not forgotten. Also **contains
      plumbing that needs separating** into the Plumbing box; the WaterPEX P-412
      was the first one pulled out.
- [ ] ~~Ball valve #1053 has no home~~ — **done**, 2 off, 3/8in, in the Air box.
- [x] ~~**A2 walk**~~ — **done.** 53 verified empty, 7 counted, 4 parking
      spots, zero unseen.

## A3-R7C3 is the mains-protection drawer

Created 2026-08-23. Holds the input-protection set from the Hi-Link
application circuit — **44 fuses, 4 varistors, 14 X2 caps, 3 chokes** — because
you reach for all four together when putting something on mains. Sits beside
the LM2596 buck converters at R7C2, which makes row 7 the power row.

`default_location` for all four parts now points here. It previously pointed at
RB-14, which is a **project bin** — and a project bin is never where a spare
goes home. That rule is why this drawer exists.

Four of each fuse / varistor / X2 stayed in RB-14 as the build's allocation,
and **the three chokes are physically in RB-14 too** — all of them are spoken
for by the builds. Only their *home* is A3-R7C3. RB-14's description says so,
since a BOM line vanishing from a project bin with no forwarding note is how a
build stalls at the bench.

**That distinction caused the one mistake here worth recording.** Asked whether
the chokes should go in this drawer, Scott answered about their `default_location`;
I acted as though he had authorised physically moving them, and relocated the
stock row. Corrected the same day. The two fields answer different questions —
`default_location` is *where a spare goes home*, `location` is *where this one
is right now* — and a part out on a build is exactly the case that separates
them.

## Short to build

- [x] ~~**C2 for the AC Wall Adapter**~~ — **RESOLVED 2026-08-23, no purchase
      needed.** Use **#670, 470uF 25V, 8x12**, from the Xuansn kit at
      `L2-D4/Kits`. The board's C2 footprint is **8x12**, measured by Scott at
      the board — which also rules out #687 (220uF 10V, 6x7) permanently. The
      README's BOM names a value and no body, so that constraint is recorded on
      the bin AND on both capacitor parts, findable from either direction.

      Worth keeping from how this went: the catalogue reported zero for a part
      the shop owns, twice in one session, because the Xuansn and 15-value
      electrolytic kits have never been seeded. A near-miss on a purchase is a
      cost, and it belongs on the "counting 600 capacitors is expensive" side
      of the ledger.

- [x] ~~The choke and the HLK module~~ — **on `TO-ORDER-ALI`, 2026-08-23.**
      A sibling shopping list to `TO-ORDER`, because that one is an Amazon PO
      and InvenTree binds line items to the order's supplier. 1 x HLK-5M05B
      (the SKU is a 5-pack) and 5 x choke (1 needed, four spare).

- **The fifth HLK module is not missing.** Bought as a 5-pack; 3 loose in
      RB-14, 1 on the assembled board there, and **1 in service** — Scott built
      a complete unit on this board and it runs the shop temperature/humidity
      sensor under ESPHome. Recorded on #491 so the 5-versus-3 gap does not get
      re-investigated. **That deployed unit is also the proof the design
      works**, which is worth knowing before ordering parts for four more.

      Two assembly warnings from the project README, recorded on the bin
      because both are discovered too late otherwise: **fit the shim and AC
      plug BEFORE soldering the Hi-Link module**, and **if L1 is left
      unpopulated, jumpers must be installed in its place**.

## Containers and dividers

- [ ] **BUY: Sterilite 6 Qt 10-pack, Walmart item 5297809753, $10.98.**
      External 13 1/2 x 8 x 4 5/8; interior bottom 11 1/2 x 6 x 4 1/4. For the
      WIRE SHELVES only — 3 across x 2 deep = 6 per 46x18 shelf, 72 slots across
      both racks for eleven dollars. Newington store, low stock as of
      2026-08-22, so order for pickup rather than driving on spec.
- [ ] **MAKE: cabinet trays, 7 1/2 x 12 x 3.** Nothing off the shelf fits
      3-across in the 24 x 12.75 LW opening — the 6 Qt is 13.5 deep and will not
      go front-to-back, and every common width puts three bins at 24in or over
      with zero clearance. Laser-cut to the exact opening, with the CENTRE tray
      sized deliberately as the pull-out key for the hinges. Buy the commodity,
      make the thing that has to fit exactly.
- [ ] **Design bin dividers — laser or 3D print.** Scott has both. This changes
      the buying decision: with dividers, buy FEWER and LARGER bins and
      subdivide, rather than many small ones. ~4 cable bins by category (USB /
      video / network+audio / power) each split 3 ways beats 12 separate bins —
      you still pull one container per category, which is how you search.

      **Moulded bins taper, and by more than you would guess.** Measured on the
      Sterilite 6 Qt: external 8in wide, interior bottom 6in — a full inch of
      draft per side. A cross-lap divider cut to the 6in bottom has ~1.5in of
      slop at the top. A cross-lap divider cut to the bottom dimension rattles at the
      top; cut to the top, it will not seat. Either make the side panels
      trapezoidal to match the draft, or size to the bottom with a locating foot
      and let the top run loose. **Measure top AND bottom internal width before
      cutting anything.**

      Slot-together cross-lap, no glue — the mix changes as sorting proceeds and
      a re-spaceable divider beats a perfect fixed one. 3mm ply or acrylic on
      the laser for flat dividers; 3D print only where features earn it (finger
      notches, cable slots, moulded label tabs). Printing a full grid is slow
      and filament-hungry for what the laser does in two minutes.

## Cable inventory — greenfield

- [ ] **Sort and catalogue the cables.** `Electronics/Cables` holds **4 parts,
      all jumper wires** — every USB, HDMI, power cord and adapter on the wire
      shelves is uncatalogued. Scott: *"I have no idea what I've got... they
      need to be identified and then cataloged, so I know exactly what I have."*

      **Identity is connector pair + length**, not "cable". The question asked
      is never "do I have a cable" but "do I have a USB-A to micro, about six
      foot" — so a part is `USB-A to Micro-B, 6ft`, and the same principle as
      footprint-is-identity applies: A-to-C and A-to-micro are different parts,
      not one part with a note.

      Sort into ~11-12 bins, one per thing-you-reach-for: USB A-micro, A-C, A-B,
      C-C, Lightning; HDMI (+mini/micro); DisplayPort/VGA/DVI; Ethernet; audio
      3.5mm/RCA; power IEC-C13/figure-8/barrel; adapters and dongles.

      **Sort and catalogue in one pass.** Sorting into piles that do not match
      the search vocabulary means re-sorting later.

      Bin height for cables can be 4-6in, unlike the 3in for small fittings —
      burying is a small-parts problem and a coiled cable is big enough to see.
      Same footprint so they interchange on a shelf.

## Cut stock — decided 2026-08-24, on the fiberglass sleeve

The 15 m sleeve roll (PO-0020, part #790) forced the question, and the answer
sets the precedent for wire, solder, heat-shrink, tubing and filament. **Today
0 of 1071 parts carry a unit and no stock row anywhere is fractional**, so this
is the first one.

**Decision: track length, in metres, seeded from the pack claim and accepted
as correct.** Done 2026-08-24 — stock #657, 15 m at WS2-S3.

- `units='m'` — lowercase, see `TRAPS.md`. Metres because that is what is
  printed on the bag, so the seed figure is transcribed rather than converted;
  there is no rounding to explain later.
- Entry still happens in whatever you are holding a ruler in. The web UI takes
  `8 in` and stores `0.2032`. Resolution is 5 dp — 0.01 mm — so inches are exact.
- The roll carries 15 m **with no `stocktake_date`**. Scott's ruling, and it is
  a cleaner rule than the one first written here: *"we'll assume it's correct
  because we're never gonna measure it... we're not gonna measure it down to
  the one thousandth of an inch."* So no `[ESTIMATE]` marker — the figure is
  accepted, and the note says in plain words that it came off the bag.

**The `stocktake_date` stays null anyway, and that is not hedging the 15.** The
field means *somebody counted this*, and nobody did. Stamping it would put the
roll into the never-counted report as verified. Accepting a number and claiming
it was measured are different acts, and only the second one is a lie.

**Why no `[ESTIMATE]` marker, when 147 other rows carry one.** The marker earns
its place where the figure could be checked and has not been — a sealed kit, a
listing count. Here the quantity is *derived by construction* the moment you cut
once: it is 15 minus what was recorded, and everyone reading it knows that. A
marker that never comes off is decoration, and decoration on a data-health panel
is how people learn to ignore it.

**Ruled out: stock it as `qty 1 roll`.** Honest, and useless the moment you cut
into it — "1 roll" cannot answer *do I have enough for this harness*, which is
the only question anyone ever asks of a consumable. The row stays green while
the fact rots, which is data atrophy in one row. (`units='roll'` is also
rejected outright by the validator — pint has no such unit.)

**The failure mode to design against is remainder drift**: somebody cuts and
does not record, the number stays high, and a job gets planned around sleeve
that is not there. Two defences, and the first is not yet built:

- [x] ~~**Teach BinScan to convert units.**~~ **Built 2026-08-24.** A number
      box plus a unit picker, shown only for a part that carries a unit — the
      other 1070 parts stay plain counts. The client does no arithmetic: it
      sends the number and the unit, and the server converts with factors
      pinned against InvenTree's own pint (`scripts/unit_factors_check.py`
      fails if they ever drift). Covers `/api/assign` and `/api/filepart`;
      `/api/newpart` deliberately stays a plain count, since a part being
      created has no stock unit yet. Verified end to end by
      `scripts/binscan_unit_test.py`.
- [ ] **When it looks low, measure the remainder and stocktake it.** That is
      the move that converts the estimate into a count, and it is cheap exactly
      when it matters — a nearly-empty roll is short enough to measure.

- [ ] **Offcuts long enough to reuse** — undecided. The WS1 wire-offcut
      precedent suggests a separate stock row at the rack rather than pretending
      the roll is still whole. Nobody has cut any yet, so this is not urgent.

## FR-301 bench consumables — A3-R1C2, established 2026-08-24

Cleared off Scott's bench in one pass. The drawer is `SLN/Bin Wall/A3/A3-R1C2`
(A3 had a block VERIFIED EMPTY 2026-08-23; B3 is fully allocated), and it is
`default_location` for all three records below.

| | |
|---|---|
| `#213` 1.3mm N61-06 | **in service** — installed on the gun, stock 0, min 1 → *no spare* |
| `#87` 0.8mm N61-07 | stock 1 @ A3-R1C2, min 1 |
| `#1084` filter set | stock 1 sealed set @ A3-R1C2, min 1 |
| `#474` FR-301 gun | stock 1 @ SLN/Electronics Bench — **it had no stock row at all before this** |

`#86` retired into `#213` — a duplicate the 0.8mm merge pass missed. See
`TRAPS.md` for why the surviving pk went the other way, and for the sweep that
would find any other unmerged twin from that import.

**Still soft, and each is one look away from being hard:**

- [ ] **The 0.8mm quantity is not a count.** 1 comes from the purchase record
      (1 purchase, 1 unit lifetime) plus Scott saying he is filing it. No
      `stocktake_date`. Open the drawer, count it, promote it.
- [ ] **The filter set's contents were read off a photograph** — 2 pads and a
      metal holder — so the row counts 1 SEALED SET and nothing finer. Opening
      the bag settles it.
- [ ] **Hakko's part number for the filter is not recorded**, deliberately.
      Nobody verified it and a confident wrong MPN gets reordered. It is in the
      gun's manual.
- [ ] **The gun's location is an inference from use**, not a put-away: Scott was
      fitting a nozzle to it at the electronics bench. Fine, and worth knowing
      it was never carried anywhere on purpose.

**The pattern is reusable and probably under-used.** Any consumable that lives
fitted to a tool — laser nozzles, collets, filters, mill tooling — wants
`belongs_to` rather than a drawer row, or its minimum-stock rule is decorative.

## Divided drawers — an F/B suffix, and why it is not free

Scott, 2026-08-24, filing nine TCRT5000s into A3-R2C7: *"they will fit in that
tray divided, so half of that tray is still available"* … *"it makes me wonder
if there should be an F/B modifier on these trays?"*

**F/B is the right scheme.** These drawers are 6 in deep and a divider makes a
FRONT and a BACK half. Front/back is fixed by the drawer's own motion — unlike
left/right, which depends on where you are standing, and unlike A/B, which is
arbitrary and has to be looked up. You see the front half first when you pull it.

**Two halves of the problem, and only one is durable.**

- **The divider is durable.** A tray either has one or it does not. Written
  once, stays true. It is on A3-R2C7's description now.
- **Free space decays faster than anything else here.** Every put-away changes
  it, and a rotted space note is worse than none — it sends somebody walking to
  a drawer that is full.

So the rule: **record the divider, never maintain a free-space note, and derive
occupancy from sub-locations when it is actually needed.** Filing something into
the empty half then updates the answer as a side effect, with nobody having to
remember.

**Do NOT rename drawers.** `A3-R2C7` keeps its plain address while one thing
owns it, and gains `-F` / `-B` children only when a second, unrelated thing
shares it. Renaming up front would break every existing address and mint 128
locations for a case that mostly does not exist.

### It needs a BinScan change FIRST — measured, not assumed

Three anchored regexes reject a suffix:

```
app.py:345   DRAWER_RE = ^([A-Z]+\d+)-R(\d+)C(\d+)$        (python)
app.py:3107  /^([A-Z]\d+)-R(\d+)C(\d+)$/                    (grid nav)
app.py:3110  /-R(\d+)C(\d+)$/                                (next/prev drawer)
```

A location named `A3-R2C7-F` fails all three, so `r` and `c` come back `None`
and the drawer **silently drops out of the grid and out of walk navigation**.
No error — it just is not there, which is the worst possible failure to find
mid-walk.

- [ ] **Make the suffix optional in all three regexes** before the first `-F`
      location is created: `(?:-([FB]))?$`. Then decide how the grid renders a
      subdivided cell — probably the parent cell, marked as split, since the
      grid is a picture of the cabinet and the cabinet still has one drawer
      there.
- [ ] **Which half are the TCRTs in?** Not recorded. It is the fact that makes
      the eventual `-F`/`-B` assignment real rather than a coin toss.

**Ruled out, with what eliminated them:**

- **A free-text note** (`PLENTY OF ROOM`, `ROOM REMAINS`) — already the de-facto
  convention on A3-R2C1, R2C4 and R3C1. Maintained rather than derived, and
  nothing forces an update when the space is taken. Treat those existing notes
  as **undated hints, not facts**.
- **Pre-creating halves for all 64 drawers** — cost and noise, for a case most
  drawers will never have.
- **Counting distinct parts as a proxy for compartments used** — two parts can
  share a half and one part can sprawl across both. The proxy is not the thing.

**Proportionality says build it later.** A3 still has dozens of drawers marked
VERIFIED EMPTY, so "where is there room" is answered today by a query that
already works — locations holding no stock. Half-drawers only start to matter
when the whole empty ones run out.

- [ ] **A2's cabinet description already says its drawers are "DIVIDED and
      shared by related small parts"** — so A2 is where this scheme will
      actually earn its keep, and A2 is the cabinet nobody has walked.

## Storage bins — B-01, B-02, … the ID travels with the BIN

Decided 2026-08-24. Ten identical clear Sterilite 6qt bins on one shelf are
indistinguishable by contents. Scott: *"you could get ten of them on one of
these shelves — how would you know where to look? It's gonna have to be more
discriminatory than that, so you can go right to the correct bin rather than
looking at every bin."*

**Each bin gets a permanent ID — `B-01`, `B-02` — that belongs to the BIN, not
to the shelf slot.** Location name carries both: `B-01 Sleeving & Loom`. The
code finds it on the shelf, the words find it in a search.

**Ruled out: shelf-position names like `WS2-S3-B1`.** The reason was already
written on the Air System bin — *the BIN is the location so it can move or
upsize freely*. A shelf-coded name means renaming the bin and every
`default_location` pointing at it the first time it moves shelves.

**A bin in service is a LOCATION, not stock.** #1089 (the 10-pack) drops by one
each time a bin is put to work. Currently 9 in `SLN/Receiving`.

- [x] ~~Label B-01~~ — **printed 2026-08-24 (job QL810W-34).**

      **The label carries the ID and the QR, and NOT the contents.** Scott:
      *"as soon as you do, it'll be out of date... what do we do when we figure
      out what else to put in there, print a whole new label? That doesn't seem
      very productive."* Right — contents change, the container does not. The
      contents live in the description, which is free to edit and is what the
      QR resolves to. Same reason the drawer labels work.

      These bins are also CLEAR, so eyes answer "what is in it" at a glance and
      the label only has to answer "which bin is this".

      **A rendering failure settled it independently.** With the location named
      `B-01 Sleeving & Loom`, the 62x25mm template wrapped to three lines and
      overprinted the WS2-S3 breadcrumb — the WeasyPrint no-overflow trap. The
      location is now named `B-01`, with `SLEEVING & LOOM.` opening the
      description, so location search still finds it by contents.

      **The shelf breadcrumb `WS2-S3` stays on, deliberately.** Scott: *"we can
      just relabel it if we rehomed it."* Yes — and the rule that separates it
      from the contents is worth keeping: **put on a label anything that changes
      less often than reprinting costs.** Contents change every time something
      is added, so they lose. A bin is rehomed rarely, so it wins, and a reprint
      then is fair.
- [ ] **Heat-shrink: in the sleeving bin or not?** Undecided. It lives in the
      bin wall today.

## Cabinets never walked

- [ ] **B1** — 31 rows still at cabinet level, flagged `DRAWER UNKNOWN`. All
      McMaster fasteners with known part numbers and `[ESTIMATE]` quantities.
      Highest-value walk left: turns estimates into counts.
- [ ] **B2** — 17 rows the same. Settles whether A2 and B2 duplicate each other
      on imperial fasteners.

## Machine shop — the walk that settles the PO receives

The 2022–2024 Tormach and MSC orders were received into stock on 2026-08-23 to
clear the PO backlog. Receiving carried the **purchased** quantity onto each
row, which is a document, not a count. None of these rows has a
`stocktake_date` and every one says so in its notes.

- [x] ~~Three BT30 end-mill holders read 2 each and may be 1 each.~~
      **ANSWERED 2026-08-23.** Scott: *"those were all rec as ordered."* The
      orders were right and the deleted placeholders' assumed 1 was wrong. #535,
      #536, #537 and #540 are stocktaken to the confirmed quantities. Evidence
      tier is a person's statement that the shipments arrived complete, not a
      rack tally — recorded as such on each row.
- [ ] **Empty the `Unfiled - Machine Shop` waiting room.** It gained four rows
      on 08-23: 9 BT30 45-degree pull studs (#539), the carbide face-mill insert
      (#543), and the **Tapmatic No.90X tapping head (#927, $2,005.80)** — a
      two-thousand-dollar tool whose location the catalogue records as "somewhere
      in the machine shop". Its description is explicit that it is a waiting
      room and should trend toward empty.
- [x] ~~Four pull-stud parts, 36 units — how many are one thing?~~
      **ANSWERED 2026-08-23.** Scott: *"pull studs are 20 total, 2 diff kinds,
      TSC and normal, 1 pack of 10 each."* Not a duplicate-part problem at all —
      the four parts are four real vendor items. It was a **consumption**
      finding: the Shars (#120, 7) and Tormach (#539, 9) studs bought in
      2024–2025 are screwed into the holders they were bought alongside, and
      only the two Haas packs (#110, #113) are spares. #120 and #539 now read
      zero with the reason on the row; #110 and #113 are counted at 10 each.

      The pack-vs-unit worry was unfounded — both Haas parts already carried
      `pack-corrected: 1 pack(s) of 10 = 10 units` in their notes from the
      08-19 pass. The catalogue had answered it; the sweep had not read it.

## Pull studs — converge to two parts, once the geometry is checked

Scott, 2026-08-23: *"should we be tracking the pull studs as 2 part #'s, 1 for
TSC and another for non TSC regardless of vendor? They are the same things."*

**Agreed in principle, and it is the correct model** — vendor is not part
identity, it belongs on `SupplierPart`. Four records for what is probably two
real items is the import-twins shape.

**Blocked on one physical check, deliberately.** The four records each name a
DIFFERENT attribute, so nothing on file establishes they interchange:

| Part | Name says | Axis it pins |
|---|---|---|
| #110 Haas 04-1421 | "Standard" | TSC: no |
| #113 Haas 04-1420 | "TSC" | TSC: yes |
| #539 Tormach 37553 | "45-Degree" | flange **angle** |
| #120 Shars 202-5921 | "M12x45" | thread x **length** |

Two of them contain "45" meaning different things. A BT30 stud's identity is
**flange angle + thread/length + TSC or not**; TSC is one axis of three.
Merging on "they're all BT30 pull studs" is the false-MATCH direction — a false
miss costs a glance, a false match puts a stud in the drawer that will not hold
in the spindle.

- [ ] **Compare a Haas stud against one screwed into a holder on the rack.**
      Flange angle and thread/length. Five minutes, and it also answers a live
      question: **the only BT30 spindle in the shop is the 1100MX, and all 20
      spares came from Haas Tooling** — a discount storefront, but there is no
      Haas machine here. $156 of studs bought in the last month, fit unverified.
      The 1100MX reference carries **no pull-stud spec**, so this is measurable,
      not researchable.
- [ ] **If they match:** two parts named for what determines fit —
      `Pull Stud, BT30 45°, M12 — TSC` and `— non-TSC` — with Haas 04-1420 /
      04-1421, Tormach 37553 and Shars 202-5921 attached as SupplierParts so all
      four price histories survive. If they do NOT match, the four records stay
      four and each name gains the axis it is missing.
- [ ] **#543 carbide face-mill insert** — same unanswered consumable question as
      the pull studs had. Bought 2024, received 1 on 2026-08-23, no stocktake
      date. An insert that old may be worn out and gone.

## Receipts that were never put away

- [ ] **Find the SHT31-D delivery, or settle what PO-0028 actually was.**
      Scott ordered on 2026-08-20 (Amazon, $16.9x) and recalls it as the
      SHT31s; Amazon reports delivered; the parts are not in B3-R4C8 and not
      in `Receiving`. Both rows (573, 574, two each) now sit at
      `(NOT LOCATED ANYWHERE)` — see `TRAPS.md`. **The Amazon order page is the
      thing that settles it**, since the confirmation email carried no line
      items at all. Until then the shop believes it owns four sensors it
      cannot find.
- [ ] **Reconcile the 23 stub POs.** Their line items were inferred from
      confirmations with no line items. Receiving one mints stock at a planned
      address — which is how the SHT31 claim was born. Worth a pass that flags
      any stub PO already marked received.
- [ ] **Receive to `Receiving`, not to a drawer.** Four rows (570, 571, 572,
      583) carry a drawer and have never been counted, on the same footing as
      the SHT31 rows. Low risk — three are in daily use — but the practice is
      what produced the failure.

## Parts filed away from their home

- [ ] **#107 MPXV6115VC6U pressure sensor is in `Unfiled - Machine Shop`**
      while its `default_location` says B3-R7C2, the pressure-sensor drawer.
      A surface-mount pressure sensor living with the BT30 tooling. Found
      2026-08-23 when Scott looked in B3-R7C2, counted three items, and asked
      why the record implied five.

      **Worth a sweep, not just this one fix:** any row whose location differs
      from its part's `default_location` is either out on a build — legitimate,
      like the chokes in RB-14 — or misplaced. The two look identical in the
      database and only a person can tell them apart, so the useful output is a
      LIST to walk, not an automatic correction.

## Rows that disagree with themselves

- [ ] **Two rows carry a count date AND notes saying they were never counted.**
      Found 2026-08-23 while checking something else; 2 of 336 counted rows, so
      not systemic.
      - **stock 556**, Terminal Removal Tool Set 41pc, BL-D2, counted
        2026-08-22 — notes say *"[ESTIMATE] 41 is the LISTING count, not a
        count of what is in hand. Never used and never opened out."*
      - **stock 482**, M5 cup-point set screws, B1, counted 2026-08-22 —
        notes say *"[ESTIMATE] ... NOT COUNTED, nobody has looked in the
        drawer and tallied it"*, then refer to *"the count above"*.

      `sync_stocktake.py` did not do this — its regex requires the full
      `binscan <date>: filed into <loc> and COUNTED at N by hand`, which
      neither note contains. Most likely the notes were rewritten after a date
      was set, losing the marker and leaving the date.

      **Only Scott can resolve it**, since the question is whether anybody
      actually tallied those two. Left alone rather than guessed: clearing a
      real count and clearing a false one look identical afterwards.

- [ ] **The `[ESTIMATE]` marker is matched as a bare substring**, so prose that
      merely mentions it flags the row. Stock 504's note says it *"graduated
      from [ESTIMATE] to a real count"* — a correct, well-written note that
      makes a counted row read as an estimate. Nearly repeated today when a
      note about superseding an estimate was almost written with the literal
      marker in it. Either the marker needs to be positional (line start) or
      the prose convention is: never write the token unless you mean the flag.

## Imports and enrichment

- [ ] **Bambu Lab** — 12 orders located, parser proven against all three
      template eras, **not imported**. See `bambu-import.md`.
- [x] ~~**The three electrolytic kits**~~ — **all seeded 2026-08-23** from
      photographed lids. 10-value: hand-counted, 95 pcs, 9 values. 15-value:
      200 pcs, 15 values. Xuansn: 267 pcs, 18 values. **All three are now
      COUNTED** — the 10-value by hand tally, the other two verified at factory
      figures on Scott's report that the compartments are undisturbed
      (inspection, not a piece tally, and every row says which). The one
      compartment that had been drawn from, 470uF 25V, tallied at 12 against a
      factory 15.
- [ ] **Datasheets** — 16 candidates unresolved; needs the Mouser path or a
      browser fetch. See `datasheets.md`.
- [ ] **Amazon hardware sweep** — never done. The 2026-08-19 reconcile covered
      electronics only, and hardware orders were never in scope.
- [ ] **#292 purchase-history block is stale** — claims one purchase and one
      unit lifetime, predates two orders, quotes a 4-pack price as a unit
      price. Other parts may carry the same stale auto-generated blocks.

## SQLite gives one writer, and the walker should win

- [ ] **A failed count leaves NO trace.** B3-R1C3, 2026-08-23: Scott's tap hit
      `database is locked` and his 22 vanished — recorded by hand afterwards
      only because the walk was being compared against the database. BinScan
      shows the 500 and then... nothing; the number is not queued, retried, or
      kept. **Worth building: hold the figure and retry**, since a lock clears
      in seconds and the person has already done the counting. See `TRAPS.md`
      for the writer-contention rule this came from.

## BinScan can file a part now — built 2026-08-23

- [x] ~~A part that exists with no stock anywhere is unreachable from the
      phone.~~ **Built and deployed.** `/api/filepart` creates a first stock
      row from the drawer, and identify now matches against the whole
      catalogue by name rather than only the cabinet's unlocated fastener
      rows. Verified end to end against the Shelly photo that failed: #79
      ranks first at 1.387 against 0.655 for the next candidate. See
      `binscan.md`.
- [ ] **Second-order: the catalogue matcher's tail is noisy.** Runners-up
      match on generic tokens — "plus", "switch", "power" — and score around
      0.5-0.65 against the right answer's 1.39. Harmless while the gap is that
      wide and the matched tokens are shown, but a stop-list tuned on real
      readings would sharpen it. Not worth doing from guesses; worth doing
      after a few dozen real identifies.

## Guards that mirror each other, but should not

- [ ] **`scripts/mark_empty.py` still refuses on any description text**, while
      `binscan`'s `/api/empty` now distinguishes a claim of emptiness from a
      naming of contents (fixed 2026-08-23, see `TRAPS.md`). The divergence is
      **deliberate and should stay** until decided otherwise: the phone has a
      person at the open drawer, a `--cabinet` sweep has nobody looking, and
      relaxing the script would stamp 31 unverified A3 claims as verified by
      fiat. If the script ever needs the same behaviour for a single named
      drawer, give it an explicit flag — do not widen the rule.
      The docs say these two mirror exactly; they no longer do, and that is
      recorded here so the next reader does not "fix" the asymmetry.

## Labelling

- [ ] **Print a test address label on the 62mm continuous roll, then decide
      whether DK-11201 is needed at all.** It is currently the only real
      low-stock signal in the shop (#923, min 1, have 0) and it may be
      aspirational rather than operational: **every template in use is authored
      at 62mm continuous**, and the standing rule is *"author at 62 mm, never
      narrower, or CUPS will scale it."*

      Telling detail: **the driver's default `PageSize` is `29x90mm`** — exactly
      the DK-11201 die-cut size, and exactly the setting `LABELLING.md` flags as
      wrong. That is plausibly how a die-cut roll acquired a minimum in the
      first place; the whole 62mm decision was made to get away from that
      default.

      Continuous tape cuts to whatever length the template asks for, so an
      address label needs a 62mm-wide template, not new media. The die-cut roll
      buys only a narrower 29mm label and pre-cut registration.

      **If the test prints acceptably, drop the minimum on #923** rather than
      reordering — otherwise it generates a false low-stock signal forever for
      something never used.


- [x] ~~poppler is not installed on the Mini~~ — **WRONG, corrected same day.**
      It was installed all along; `itq` reports the ssh PATH, not the launchd
      PATH the service runs with. Label PNG rendering works — tested under
      both. See `TRAPS.md`.

- [ ] **Wire shelves have no flat face to take a label.** Scott, 2026-08-22:
      *"gotta figure out how we're gonna mount the label because there's no flat
      surface."* Wire racks are open grid — an adhesive location label has
      nothing to stick to. Needs a mounting answer (zip-tied tag, a clip-on
      card, a strip of flat stock on the front rail) before WS1/WS2 shelves get
      addressed. The BINS on the shelves label fine; it is the shelves
      themselves that are the problem.

- [ ] ~240 locations are **printed but not affixed**. A1 sheet still to install.

## Florida — decided in principle, quantity not yet

- [ ] **Take some RF pigtails / U.FL adapters to LRD.** Scott, 2026-08-23,
      after stowing them: *"we're definitely gonna take some of those to
      Florida... I can't do it right now."* Both rows are in **A3-R6C6**:

      | stock | part | qty here |
      |---|---|---|
      | 603 | SMA Female to U.FL/IPEX Pigtail Cable, 1.13, 15cm (#732) | 8 |
      | 604 | 10PCS IPX IPEX U.FL Female Connector to open single-end | 9 |

      **Deliberately NOT earmarked yet.** `scripts/florida.py add` wants a
      quantity, and the decision so far is *some*. An earmark carrying an
      invented number is worse than no earmark: it reads as a decision that
      was never made, and the packing list is built from those numbers.

      Do it before the **~2026-10-12** departure. One question answers it:
      how many of each. Then `itq run scripts/florida.py add <pk> A3-R6C6 <n>
      "<why>"` for each, and the packing list picks them up.

      Worth asking at the same time: the LRD bench has no RF work set up yet,
      so the honest quantity may depend on what is actually going to be built
      there rather than on splitting the pile evenly.

## Watch

- [ ] **InvenTree update available (noticed 2026-08-23). DO IT IN FLORIDA, not
      from here.** The Mini lives at LRD, so from SLN it is 1,300 miles away and
      an upgrade that goes sideways leaves a broken server nobody can touch.
      This instance also carries a custom `shopstatus` plugin and BinScan
      depends on specific API shapes, so it is not a no-risk upgrade.

      **The window is after the ~2026-10-12 move**, when Scott is beside the
      machine and a failure costs an hour rather than a season. Same reasoning
      that makes LRD the cycle-count pilot site — see [[seasonal-residency]].

      Generalises: **any risky change to the Mini wants to happen while
      co-located with it.** Half the year that is impossible.

- [ ] **INVE-W7: email not configured** — accurate, not spurious. `EMAIL_HOST`
      is unset while the `inventree-email-notification` plugin is ACTIVE, so the
      stack claims a capability it does not have. Costs: no password reset by
      email (irrelevant, there is shell access) and no email notifications. The
      UI notification plugin works and is what shows the bell.

      Either configure SMTP — worth it only if low-stock alerts should reach
      Scott outside the app, which they arguably should since he has minimum
      stock rules — or deactivate the email plugin so the two agree.



- [ ] **CANCEL the $1 Walmart+ trial before ~2026-09-21.** Taken 2026-08-22
      only to get an $11 bin order delivered same-day. Scheduled reminder set
      for 2026-09-17. Then re-enrol via the Amex Platinum credit — **monthly
      plan only**, the annual plan forfeits the $12.95/mo credit entirely.

- [x] ~~Tonight's overnight run is the first test of the permission fix.~~
      **PASSED, 2026-08-23.** RUN STARTED 02:05, RUN COMPLETE 06:57, no human
      awake — the first unattended run to go start-to-finish since the 08-18
      and 08-22 permission stalls. `journal.py`'s fixed invocation is what
      changed. Queue A images + queue D keywords both ran; next run resumes
      queue D at **pk 240** (559 empty keyword rows left, ~8 nights), and
      queue A is down to ~25 scrapeable parts.
- [ ] **Two POs still open, both correctly.** The 2026-08-23 sweep took Placed
      POs from 9 to 2. **PO-0020** uxcell fiberglass sleeve, in transit, ETA
      Aug 25 – Sep 3. **PO-0133** Brother DK-2205 roll, was expected 08-23 and
      Scott says it has not arrived — chase it if it is still absent in a few
      days. Also still resting correctly: `TO-ORDER` (a draft standing list,
      never issued) and **PO-0029** (PET sheet, Returned, nothing received).
      `TO-ORDER`'s SHT31-D line is now **stale** — PO-0028 covered it and has
      been received.
- [ ] **McMaster API request** sent 2026-08-22 to eprocurement@mcmaster.com —
      check for a reply before doing anything else with McMaster data.

## Bin wall expansion — decided reasoning, purchase not yet made

**The scarce class is large drawers, measured physically, not from the
database.** Scott counted 2026-08-22: B1 3 empty of 12, B2 5 of 12, B3 3 of 11.
**11 empty of 35 shop-wide — 68% full.** The A wall contributes zero (three
10164s, all small). Small drawers are 289 at ~22% and will never be the
constraint. Any purchase should therefore be all-large.

- [x] **ORDERED 2026-08-22, arriving Tuesday 2026-08-25: 2x Akro-Mils 10124**, 24 large drawers each, $49.99 (Walmart,
      verified live 2026-08-22, free ship, no same-day). 48 larges takes the
      shop from 35 to 83. Same 20 x 6-3/8 x 15-13/16 shell as the A cabinets;
      two stacked are 31-5/8 in, level with the A row over the B row.
      **The Walmart URL slug says "44-Drawer" and the page is the 24-Drawer** —
      the variant picker offers 16/24/26/64 and has no 44 at all.

### Tuesday, when they arrive

- [ ] **Measure a drawer first.** Confirm it really is the large class
      (6 x 4-9/16 x 2-3/16). The spec came from Walmart's AI-generated block,
      not from Akro-Mils. Free returns for 90 days, so this is the moment.
- The **Thread Detective gauge is NOT in the way** — it hangs off the electrical
  panel itself, not on the wall the cabinets need. Raised as an obstruction from
  a photograph and corrected by Scott; recorded so it is not raised again. The
  22 in is genuinely clear: conduit sits behind the panel face, gauge hangs on
  the panel.
- [ ] **Use A3 as the hole template**, not a tape measure: pull its drawers,
      take it off the wall, hold it in the A0 position, mark through the
      keyholes, remount A3, hang the new one on the marks. Confirm the 10124's
      keyhole pattern matches before drilling — "same shell" is a listing
      claim.
- [ ] **Pull the drawers before lifting anything.** Akro-Mils drawers slide
      free and a loaded cabinet tipped a few degrees empties onto the floor.
- [ ] **Butt them hard against A1/B1, zero clearance.** All six existing
      cabinets touch; the 2 in of slack belongs on the panel side for breaker-
      door swing.
- [ ] `itq run scripts/make_a0b0.py --commit` — creates both cabinets and all
      48 drawers, named and described. **Run it after they are on the wall**,
      not before: locations for cabinets still in a box claim a place exists
      that does not.
- [ ] Then `link_barcodes.py --commit`, then print labels. BinScan picks them up
      with no change — it groups the picker by wall row, so A0/B0 simply make
      those rows four wide.

**Naming: the letter is the ROW, the number is the column left to right, and
the new pair is A0 / B0.**

```
  breaker  [2 in]  A0 A1 A2 A3
                   B0 B1 B2 B3
```

The new cabinets hang to the LEFT of A1/B1, so they are column zero. A0/B0 is
the only scheme that reads left-to-right in order, renumbers nothing, invents no
letter, and touches none of the 324 existing labels. Zero-indexing the first
column is a one-time exception that never has to extend to A-1, because the next
expansion is **downward** — a third row C1/C2/C3 below B, where the plywood
table sits now.

Form factor is NOT what the letter means; that lives in the cabinet description,
where A3 and B3 already record the Akro-Mils model number. A0/B0 being 24-drawer
all-large while A1-A3 are 64-drawer all-small is fine and expected.

**C is NOT burned — it is reserved for the third row.** An earlier version of
this section said to skip C because `C1-R3C2` spends C on both the cabinet and
the column. Scott spotted that, and then his own row plan required C anyway. The
objection was cosmetic: the format is fixed, so the token before the hyphen is
always the cabinet and the R/C after it are always row and column. It parses one
way. Rows reading A, B, C is worth more than avoiding a double-take.

## The move

**Nothing slides. The existing six stay where they are.** An earlier plan here
had the whole wall shifting left to open space on the right; that solved a
problem the shop does not have.

Geometry, Scott 2026-08-22: **the Akro-Mils are on the NORTH wall; the breaker
panel is on the WEST wall.** The usable run is **22 in, measured from the FACE
of the panel** — the conduit transitions between the two walls behind that face
and never enters the 20 in the cabinet needs, so it is not an obstruction. A
10124 is 20 in wide, leaving 2 in.

- [ ] **Butt the new pair hard against A1/B1 — zero clearance.** All six current
      cabinets are mounted touching; a 2 in gap in the middle of the run would
      be the only one on the wall. The 2 in of slack belongs on the panel side,
      where it buys breaker-door swing.
- [ ] **Use A3 as the hole template, not a tape measure.** Pull its drawers,
      take it off the wall, hold it in the A0 position, mark through the
      keyholes, remount A3 where it was, hang the new cabinet on the marks. That
      measures the actual keyhole pattern instead of trusting the listing's
      "same shell" claim. The dry-fit also proves the spot before any hole is
      drilled.
- [ ] **Pull the drawers before lifting anything.** Akro-Mils drawers slide
      free; a loaded cabinet tipped a few degrees empties onto the floor. This
      applies to A3 during the template step.

Rejected: `OS1/OS2` for "oversize" (Scott's, and it solves the left-of-A1
symmetry problem for the right reason — a name outside the A/B series creates no
expectation of ordering). Rejected because the name would be false: 24 of the 35
large drawers are in B1/B2/B3 and stay there, so a reader told that oversize
stock lives in OS would be wrong most of the time. Positional names make no
claim that can go stale.

Also rejected: `D1/D2` and `A4/B4` at the left end — both read out of order on a
wall that runs left to right, which is the objection that produced A0/B0.

**Code debt cleared the same day:** four places hardcoded `^[AB][1-3]-R\d+C\d+$`
(`link_barcodes.py`, `first_stock.py`, `file_stock.py`, `shop_status/__init__.py`)
and would have silently excluded A0/B0 and C-row drawers from every count
without erroring. Widened to `^[A-Z][0-9]+-R\d+C\d+$` and checked against
`A0-R6C4` and `C2-R3C2`.

**Dependency worth stating: row C cannot exist until the plywood table goes.**
That makes the table's removal a prerequisite for wall expansion, not just
tidying.

## LRD layout — decide on site, not from here

Scott photographed the Florida bench wall 2026-08-22: **four upper wall cabinets**
(two doors each) over a base run with a **black worktop** — one tall single-door
cabinet at the left, then **three drawer banks**. Carpeted floor, finished room.

**Built to CABINET level only, 2026-08-22.** `LRD/Bench Wall` now holds
`UCab1`–`UCab4` and `LCab1`–`LCab4`. That much is countable in the photograph —
four uppers, one base door cabinet, three drawer banks — and is structure rather
than quantity. **What is inside them is not built**, because shelf and drawer
counts cannot be read off a picture and Scott does not recall them. Each
cabinet's description says so and names the convention to use on site.

The two arbitrary placeholders (`LRD Storage`, `LRD Bench`) were deleted once a
real structure existed.

Until the shelves and drawers are enumerated, a part can be filed to the cabinet
— the same transitional state B1/B2 are in, where the container is known and the
compartment is not.

**Scott's convention, 2026-08-22 — `Cab` for cabinet, upper and lower:**

```
LRD / Bench Wall
  UCab1 … UCab4          the four upper cabinets, left to right
  UCab1-S1 … UCab1-Sn    shelves within each, numbered from the TOP down
  LCab1                  the single-door base cabinet at the left
  LCab2 … LCab4          the three drawer banks
  LCab2-D1 … LCab2-Dn    drawers, numbered from the top down
```

Numbering from the top matches the bin wall, where `R1` is the top row.

**`Cab` also dodges a collision that `Cabinet 1 → C1` would have caused.** SLN
has `C1 C2 C3` reserved for the third row below B, once the plywood table goes.
Two locations named `C1` would be legal — location names are **not unique** in
InvenTree, and `Receiving` already exists at both sites — but BinScan resolved
locations by name and took the first match, which is a silent write to the wrong
site. It now refuses when a name matches twice and accepts a `site` to
disambiguate. The convention avoids the situation rather than relying on the
guard.

The remaining open question is whether the uppers address by **door** or by
**shelf**. It depends on what gets stored there — shelves if things sit loose on
them, doors if each bay holds one kind of thing — and cannot be answered from a
photograph.

**What is needed before any of it is built:** shelves per upper cabinet, drawers
per bank, and whether the three banks are identical. All three are one walk with
a notebook, and none can be guessed from here.

Once the locations exist, BinScan walks LRD exactly as it walks the bin wall —
the site switcher and the placeholder containers are already in place for it.

## Where the walk stands — 2026-08-23, end of day

**Bin wall**

| cabinet | drawers | counted | uncounted | empty | unseen | parking |
|---|---|---|---|---|---|---|
| A1 | 64 | 0 | 0 | 64 | **0** | 0 |
| A2 | 64 | 7 | 0 | 53 | **0** | 4 |
| A3 | 64 | 24 | 0 | 40 | **0** | 0 |
| B1 | 44 | 4 | 0 | 10 | **30** | 0 |
| B2 | 44 | 14 | 1 | 24 | 5 | 0 |
| B3 | 44 | 39 | 2 | 3 | **0** | 0 |
| **all** | **324** | 88 | 3 | 194 | **35** | 4 |

**289 of 324 accounted, 89%** — from 251 / 77% at the start of the day. A1, A2,
A3 and B3 all at zero unseen. **Every unseen drawer left is in B1 (30) or B2
(5)**, so the B1 walk is the last large piece of the wall.

**Red Bins — first walk, 2026-08-23**

| state | bins |
|---|---|
| counted | 6 |
| part-counted | 1 (RB-12, the RAT GDO kit) |
| verified empty | 2 (RB-09, RB-10) |
| never looked at | **19** |

RB-08 through RB-12 were worked: RB-08 now holds the **cord retraction system**
prototype prints (overflow from the RB-07 bench PSU kit — one project across two
bins, and both descriptions now name the other), RB-09 is empty after that move,
RB-10 is verified empty, RB-11 holds the Vilros Pi 4 kit and a new Kill A Watt
P4400.01 (#1070, created today).

Shop-wide: **313 of 587 rows counted (53%)**, from 268 of 563 this morning.

Still outstanding:

- [ ] **32 McMaster rows** sit at cabinet level in B1/B2 — located to the
      cabinet, not to a drawer. `docs/b1-b2-worksheet.md` is the paper version;
      BinScan's pick-by-hand offers them directly.
- [ ] **41 stock rows have no location at all.** They appear in BinScan's picker
      tagged `(NOT LOCATED ANYWHERE)`.
- [x] ~~**A fourth state: DECLARED.**~~ **BUILT 2026-08-23** — see
      `binscan.md`. A2 went from 4 unseen to 0. Three places today rendered as *nobody has
      looked* when the record was in fact complete and the absence of a count
      deliberate: the **A2 parking spots**, the **A3-R8C5 kit** before it was
      seeded, and **RB-05**, whose description reads *"CONSUMABLE: not
      counted"*. RB-08 just joined them — a real description, no stock
      rows, and so amber forever. RB-08 joined them — prototype prints, real
      description, deliberately no stock. The walk keeps sending Scott to
      places that are already settled, which is how a walk teaches people to
      ignore amber. The state wanted is *the record here is finished; looking
      again changes nothing*.

      **RB-09 is NOT an example and was wrongly listed as one.** It is simply
      empty, which the system already handles. It got hedged into "reported
      free, not yet eyeballed" when Scott had told me plainly it was empty
      while standing at it — a report from the person at the bin IS the
      evidence, and treating it as provisional invented a doubt nobody had.
      Corrected to VERIFIED EMPTY the same day.
- [x] ~~**A2's four unknowns are the pre-sort parking spots**~~ — **resolved
      2026-08-23**: they render as `declared` now, and A2 reports zero unseen.
- [ ] After a walk: `itq run scripts/sync_stocktake.py --commit` mirrors
      confirming counts into `stocktake_date`, then
      `scripts/binscan_undo.py --reconcile` lists the bought-vs-counted gaps to
      work through at a desk.

## After the walk: cycle counts, not a finished inventory

An inventory is never done — it drifts the moment someone takes a screw. Scott,
2026-08-22: *"we talked about doing occasional bin checks on a small number of
bins so that you can keep up with the inventory without doing a complete
inventory all the time. So the tool could assign bins to go check, and then
you'd set it up so it would advance through the bins you want to count."*

That is standard cycle counting, and it settles a question raised the same day.
Auto-advance looked like a walk-only feature that the tool would outgrow. It is
not: **a cycle count is a walk, just a short repeating one over a chosen set.**
Advance is the mechanism; only the source of the list changes.

**Scoping session: 2026-08-23.** The numbers that shape it, measured
2026-08-22 so the conversation starts from facts:

| | |
|---|---|
| stock rows | 563 |
| ever counted | 268 (**47%**) |
| never counted | 295 |
| flagged `[ESTIMATE]` | 149 |
| no location at all | 41 |
| drawers holding something | **87** of 324 |

**Every count on file is from today.** The age histogram is a single bar at
zero months, because counting only began today — which means staleness cannot
yet be used to prioritise anything, and will not be a useful axis for months.
The first cycle has to be driven by *never counted* (295 rows), not by *counted
longest ago* (nothing qualifies).

Counted rows cluster hard: B3 has 104, A3 64, and B1 only 6. That is a record of
where the walk has been, not of where the risk is.

**Measured 2026-08-23, and it inverts the framing above: the bin wall is the
BEST-counted area in the shop, and the never-counted mass is somewhere else.**

| area | rows | counted | never |
|---|---|---|---|
| SLN/Bin Wall | 250 | 198 | **52** |
| SLN/Machine Shop | 84 | 3 | **81** |
| SLN/Laser Area | 73 | 11 | **62** |
| (no location) | 41 | 2 | **39** |
| SLN/Electronics Bench | 41 | 31 | 10 |
| LRD ceramic kit | 24 | 0 | **24** |
| SLN/Assembly & Test | 20 | 6 | 14 |
| everything else | 30 | 17 | 13 |

The bin wall is **79% counted**; the Machine Shop is **4%**. Every earlier
number in this section was a bin-wall number — 87 drawers, 324 drawers, the
per-cabinet walk table — so "47% counted" read as *the wall is half done* when
it actually means *the wall is nearly done and four other areas were never
started*. A cycle count scoped to drawers would repeatedly re-count the one
region that does not need it.

**The never-counted rows are not one kind of thing, and the count cost differs
by an order of magnitude:**

| pocket | rows | what they are | cost to count |
|---|---|---|---|
| Machine Shop unfiled + toolholder rack | 32 | BT30 holders, collets, reamers, gages — nearly all qty 1 | a glance; a 1 is a 1 |
| `AT-D1` heat-set inserts | 12 | all `[ESTIMATE]` 100 / 50 / 20 from pack sizes | a real tally |
| `L2` | 59 | resistor kit values, `[ESTIMATE]` | a real tally, or never |
| Red Bins | 9 | SMD passives and modules, purchased figures | a real tally |
| unlocated | 39 | McMaster springs, pins, taps — `[ESTIMATE]` | needs a HOME first, not a count |

**147 of the 150 `[ESTIMATE]` rows have never been counted** — those figures are
wrong by an unknown amount *right now*, which is a different problem from a real
count going stale, and it argues for estimate-first over stale-first.

**Age is now a 6-day spread (29/48/39/101/23/28 rows at 1-6 days), not a single
bar** — but still nothing that could be called stale, so the first cycles remain
never-counted-driven.

**Scope, decided 2026-08-23 (Scott):** *"it's a whole shop inventory/asset
freshness tool — my goal would be to have all bins all locations in the cycle
with the ability to direct a focus, skip a section, or have randoms assigned by
the system."* So the queue covers every location, not the bin wall, and it is
**steerable three ways**: focus an area, exclude an area, or let the system
choose. Bin-wall-only was rejected on the measurement above — it would
re-count the one region that is already 79% done.

**Enrollment is DERIVED, never a stored list.** Scott, same conversation: it
must *"recognize as new locations are added to the system."* The queue is
computed from the live location tree at selection time, so a location created
after the feature ships is in the cycle without anyone enrolling it. A frozen
snapshot or a hand-maintained roster is ruled out — the shop grows, and the
locations most likely to be forgotten are the newest ones.

Two near-term cases prove it rather than hypothesise it: **48 A0/B0 drawers
land Tuesday 2026-08-25**, and the LRD bench-wall shelves and drawers get built
whenever that walk happens. Both must appear in the cycle on their own.

Open sub-question that touches Tuesday's script: a brand-new drawer arrives
**known empty from the box**, which is not the same state as *nobody has ever
looked*. `make_a0b0.py` could stamp them verified-empty at creation. Otherwise
48 drawers enter the queue as never-checked and the first cycle spends itself
opening drawers that were empty by construction.

**Timeline, Scott 2026-08-23: this is a LONG-TERM project and will not be in
use before the Florida departure, approx 2026-10-12** — *"we'll be lucky to get
thru the first count by then."* That is **~50 days from 2026-08-23**. It sets
the priority order and one hard design constraint:

- The **first count** is the pre-FL job, and it runs on BinScan exactly as it
  stands today. Nothing in the cycle-count design may become a prerequisite for
  finishing it.
- The cycle tool is what keeps the count alive **afterwards**, which is
  precisely when nobody will remember the reasoning. Hence a written spec now,
  built later.
- The departure date is **approx 2026-10-12** (Scott, 2026-08-23). That is the
  deadline the first count runs against.

**The first count is 29 TRIPS, not 295 rows — measured 2026-08-23.** The
never-counted backlog looks enormous stated as rows and is modest stated as
places to stand, which is the unit that costs forty minutes:

| trip | rows | character |
|---|---|---|
| `Machine Shop` | 49 | **all qty <= 2, zero estimates** — one trip, 49 glances |
| `Kit - EAONE Resistor 30-value` | 30 | all `[ESTIMATE]` — 30 real tallies |
| `B1` (cabinet level) | 26 | all `[ESTIMATE]` — needs the drawer walk anyway |
| `Unfiled - Machine Shop` | 25 | 17 of them qty <= 2 |
| `Kit - EMGTMS 24-Value Ceramic` | 24 | all `[ESTIMATE]`, and it is at **LRD** |
| `AT-D1` | 12 | all `[ESTIMATE]` heat-set inserts |
| 23 further trips | 51 | **nine of them are a single row** |

Plus **39 rows with no location at all**, which need a *home*, not a count, and
are desk work rather than a trip.

**116 of the 295 rows are qty <= 2 — a glance, not a tally. Only 56 are qty >=
50.** So the backlog is not uniformly expensive: one Machine Shop trip clears
49 rows in the time one resistor kit clears three.

At 29 trips over ~50 days that is **roughly four trips a week**, and the top six
trips clear 166 of the 256 located rows. The tally-heavy kits are the real cost;
the tooling is nearly free. Worth knowing before the schedule gets planned
around the row count.

**Decided 2026-08-23 — four of the eight scoping questions.** The other four
(time-budget filling, skip semantics, new-location state, readout) are still
open; Scott stopped the survey before them.

**The unit is a LOCATION, and empty ones are in.** You are assigned a place and
the work is whatever is in it, which may be nothing. *"Still empty"* is a real
observation with its own date, which is the only way the 337 empty leaves stay
in a cycle that is supposed to cover all bins and all locations. Row-as-unit was
rejected for exactly that: a row-driven queue can never assign an empty place,
because there is no row to rank. Locations too big for one sitting — `L2` holds
70 rows — get split by a size cap rather than landing whole.

**A cycle is once per week, no more than 20 minutes**, plus a **standing queue**
and **tracked skips**. Not a fixed trip count: the budget is time, and the
system has to fit the week to it.

**Not in use at SLN until NEXT SUMMER — Scott, 2026-08-23.** The shop is empty
of people from the October departure until the return north, so the first SLN
cycle is roughly **ten months out**, not seven weeks. Scott: *"I want to iterate
on this to get it right... we have time to research/scope/design and build a
robust system."*

That is a licence to do this properly, and it changes the method rather than
just the date:

- **Research is in scope.** Cycle counting is an established discipline with
  real literature — ABC classification, control groups, count tolerances,
  hit-rate accuracy rather than piece accuracy. Worth reading before inventing,
  which is not the usual position here.
- **The design is a LIVING document**, revisited across sessions, not a spec
  written once and executed. Sessions will be months apart, so every decision
  needs its *reason* recorded or the next session re-litigates it.
- **Nothing is committed to code yet.** No implementation pressure means
  approaches can be ruled out on paper, cheaply, and the rulings-out are the
  valuable artifact.

**Residency is SEASONAL — approx 6 months at each site per year (Scott,
2026-08-23), and that is a design input, not a scheduling detail.**

**LRD is the pilot, targeted early Feb 2027.** Scott: *"we can implement at LRD
quickly as it has a lot less inventory/complexity... we could definitely be
piloting there by early Feb is my guess."* Measured the same day, the size gap
is not marginal:

| | LRD | SLN |
|---|---|---|
| locations | **12** | 475 |
| leaf locations | 10 | 442 |
| stock rows | **28** | 494 |
| counted | 2 | 264 |

Ten of LRD's twelve locations are the bench-wall cabinets, still unbuilt below
cabinet level, so the pilot site is close to greenfield and gets seeded as it is
built. A system proven on 12 locations before it meets 442 is the right order.

### What seasonality does to a freshness metric — open, and it may be the crux

Each site sits **unoccupied for six months a year**. Under a plain calendar
clock every count at a site is *by construction* at least six months old the day
you walk back in, so the dashboard would open red every single arrival — a
condition that is structural, not a lapse. A metric that always reads bad on
arrival will be ignored by March.

The question that follows, **raised 2026-08-23 and NOT decided**: should the
freshness clock run on **days present at the site** rather than days elapsed? An
empty shop does not drift, because nobody is taking screws out of it. If drift
is a function of presence, then presence is what the clock should count.

The counter-argument, which is why this is not settled: **it is not true that
nothing changes while a site is empty.** Shipments land in `Receiving`, someone
else may be in the building, and this catalogue has an explicit mechanism for
stock crossing between sites — `scripts/florida.py` earmarks parts that then
travel physically in luggage. A **cross-site transfer invalidates counts at both
ends**, and it happens exactly at the seasonal boundary when a days-present
clock would say everything is still fresh.

So the honest shape is probably neither a pure calendar clock nor a pure
presence clock, but presence-based ageing plus **explicit invalidation events**
(arrival, a transfer, a delivery).

**The research pass was run 2026-08-23 and found NO prior art for this** —
warehouses do not close for six months, so the case never arises in the
literature. The prediction recorded here that established practice would have
an answer was wrong. This has to be designed from first principles; the nearest
support is opportunity-based counting's premise that errors cluster around
*movement*, which is consistent with a presence clock without validating it.
See `cycle-counting-research.md`.

**Open question raised 2026-08-23, and now answered: LRD is the first real
user, not SLN.** Original framing kept because the reasoning is what matters — The queue auto-scopes to the current site, and Scott is at LRD
from October until spring. The Florida bench wall is unbuilt below cabinet
level, so it is greenfield — locations get seeded with first counts as they are
created, which is exactly the boundary already drawn, and the winter would then
exercise the system on a small site before it ever meets the 324-drawer wall.
Whether that is desirable or a distraction is Scott's call and is NOT assumed
here.

**The first count is NOT part of the cycle-count system.** Scott, 2026-08-23,
correcting a softer version of this that had been written here: *"the first
count is not included in the cycle count system, that is implimentation."* It is
initial population — getting the catalogue to reflect the shop — and it is
finished by walks, by BinScan as it stands, and by the 29 trips listed above.
The cycle system starts from an already-counted shop and keeps it that way.

That is a scope boundary, not a sequencing note, and it settles several things
at once: the design owes nothing to the backlog, `backlog`-mode ranking is a
convenience for whatever is still uncounted when the tool ships rather than the
tool's purpose, and no readout should be built around a completion bar for a job
the system does not own.

*The arithmetic that made the boundary obvious:* seven weeks to the FL departure
at 20 minutes a week is **~2.3 hours**, while the 29-trip first count is several
times that at any believable per-trip cost. The two were never the same job.

**Ranking is a POLICY THAT CHANGES AS THE SYSTEM MATURES**, not a fixed rule.
Scott: *"this will change as the system matures — initially it might be never
counted and estimates, as those are cleared it will be fast moving parts and
random."* So the selector must be **pluggable, with named modes**, and the
active mode has to be visible in the readout — a queue whose ranking silently
changed is a queue nobody trusts. Two modes are known now: `backlog`
(never-counted + `[ESTIMATE]` first) and `maintenance` (fast-moving + random).
Neither is hardcoded as *the* rule.

**Site auto-scoping: the queue only assigns places at the site you are
currently at.** BinScan already persists *"I have moved to Florida"*, so this
reuses an existing control rather than adding one. The LRD ceramic kit's 24 rows
wait until October instead of showing as overdue work nobody in Dover can do.
A place you cannot stand in front of is not work, and listing it as work teaches
people to ignore the list.

**Decided 2026-08-23 — the remaining four.**

**The week is packed to a COST ESTIMATE, not to a place count.** Each candidate
is scored from what it holds — a qty <= 2 row is a glance, an `[ESTIMATE] 100`
is a real tally — and places are selected until the 20 minutes is filled. So one
week is six tooling drawers and the next is a single resistor kit, which is the
correct behaviour rather than a bug. Actual times get recorded as they
accumulate so the estimate improves; the first version's numbers are a guess and
must be labelled as one.

**Skip defers, counts, and ESCALATES.** A skipped place moves to a later cycle
and increments a counter, and repeated skips *raise* its priority. The failure
this prevents is specific: a place that is awkward to reach gets skipped every
time it comes up and, under any sink-to-the-bottom scheme, is never counted
again while the readout stays green. Escalation makes avoidance visible instead
of silent.

**New locations are SEEDED with first counts — the cycle system never
establishes an initial dataset.** Scott: *"new locations should be seeded with
first counts not rely on cycle count system for initial dataset."* This is the
same boundary as the first count, generalised: whatever creates a location is
responsible for its opening state. For Tuesday that means **`make_a0b0.py`
stamps all 48 A0/B0 drawers verified-empty at creation** — they come out of the
box empty, which is an observation, not a guess. The rule outlives Tuesday: the
LRD bench-wall shelves and drawers get seeded by whatever builds them too.

Stated as a principle, because it is the third time the same line has been
drawn: **the cycle system maintains freshness; it does not create data.** First
count, new locations, and initial population are all implementation.

**The readout is a DASHBOARD, not a single number** — oldest outstanding count,
the freshness distribution by age band, rolling coverage, and what is past its
interval, together. Scott: *"probably all of that in dashboard form."* The
earlier note here arguing for one number was arguing against a *completion bar*,
which is a different objection and still holds.

**Research pass done 2026-08-23 — see `docs/cycle-counting-research.md`.** It
carries the methods catalogue, what was ruled out as warehouse ceremony and why,
five things the research changed about decisions already made, and **eight new
or reopened questions for the next session**. Headlines: ABC-by-value inverts
the true priority in a shop (a 12-cent screw outranks a $180 toolholder);
**opportunity-based counting may matter more than the weekly schedule**; the
control group method is the right instrument for the LRD pilot; and BinScan has
already silently taken the informed-count position by showing quantities.

**Still open:**

**Questions to answer, not assume:**

- What is a **cycle** — a fixed count of drawers, a fixed time, or everything
  older than a threshold? 87 drawers hold stock today; ten a week clears them in
  nine weeks and the wall grows.
- Does a cycle sample **drawers** or **rows**? A drawer with eight rows costs
  eight counts but one trip. The trip is the expensive part.
- Does **never counted** outrank **counted long ago** permanently, or only until
  the backlog clears?
- What makes a row **worth** counting? The 149 `[ESTIMATE]` rows carry purchased
  figures nobody has verified — those are wrong by an unknown amount right now,
  which is different from a real count going stale.
- What does **done** look like? There is no done. The readout has to be a
  freshness statistic, not a completion bar.

**What it needs, none of it built:**

- [ ] **A queue.** A set of drawers to check, and advance stepping through *that
      list* rather than across the grid. A third option beside "across" and
      "down": *"advance through the check list"*.
- [ ] **A way to choose the set.** The obvious axis is staleness — oldest
      `stocktake_date` first, and never-counted before ever-counted. Other axes
      worth considering: rows whose purchased-vs-counted gap is largest, and
      drawers holding parts consumed by recent projects.
- [ ] **A cadence that fits the shop.** Ten drawers a week finishes the bin wall
      in about eight months, which is roughly the right period for fasteners.
- [ ] **Progress that reads as maintenance, not as a walk.** "14 of 324 counted"
      is the wrong frame afterwards; "oldest count: 6 months" is the right one.

The pieces already exist: `stocktake_date` distinguishes counted from carried,
`scripts/sync_stocktake.py` keeps it honest, and the grid already shows counted
and uncounted as different states.

---

## Dashboard redesign — 2026-08-24

Design is settled and written up in **`docs/DASHBOARD.md`**; the mock is at
<https://claude.ai/code/artifact/c35bb33b-0d4d-4308-af59-cbd7ce640b37>.
**Nothing is built yet** — `plugins/shop_status/` still renders the old four
widgets, and the two rendering bugs below are live.

**Ready to build, in order:**

- [ ] **Make the tiles link.** `static/shop_status.js` hides the anchors it has
      (`.ss .rows > a{...color:inherit;text-decoration:none}`) and the top strip
      renders `<div class="stat">` with no anchor at all. Cheapest real
      improvement on the page.
- [ ] **Reachable denominators** on every coverage figure, ruled-out count
      beside it. See `TRAPS.md`.
- [ ] **Four states with an OFF flag** — a missing reading must never render as
      zero, green, or blank.
- [ ] **Three gauges with draggable target bugs**, targets stored as plugin
      settings (`SettingsMixin`), so a goal moves without a deploy.
- [ ] **Korry lamps** — flash until pressed, per-lamp acknowledgement stored
      with a timestamp.
- [ ] **Source tiles** — last read that *proved* something, per vendor.

**Feeding back to the overnight-import project:**

- [x] Their `[ESTIMATE]` assertion queried the wrong field and read zero. Sent,
      corrected and republished by that project 2026-08-24. Measured figure is
      **148**, not the 42 you get by reading the seed scripts.
- [x] ~~`PO-0020` is PLACED with a null issue date~~ — **done 2026-08-24**,
      backfilled to 2026-08-14 from the PO's own note when the sleeve was
      received, and the order is now Complete. Zero open POs carry a null issue
      date today.
- [ ] **Assert it stays that way.** No open PO may have a null issue date. Not
      built — the backfill fixed the instance, not the class.
- [ ] 425 active parts hold no stock and sit on no open PO. Sample ten before
      it becomes a number everyone scrolls past.

**Make the stocktake mirror bidirectional — the real fix, not 2 row edits.**
`scripts/estimate_audit.py` (corrected 2026-08-24, now uses `startswith`): 147
rows carry the marker, **2 also carry a `stocktake_date`** — #482 and #556. Both
notes say in their own words they were never counted, so they are **stamped
without a count** and the never-counted report is *over*-stating progress.

`scripts/sync_stocktake.py` only ever *sets* the date; nothing clears one. A row
counted once, then re-filed without a count, keeps the stale date while binscan
prepends a fresh `[ESTIMATE]`. That sequence will keep producing these.

- [ ] **Clear the date on #482 and #556.** Not the marker — both are genuinely
      uncounted, and stripping the marker would turn a detectable contradiction
      into a silent lie.
- [ ] **Teach `sync_stocktake.py` to clear.** Set the date when the note claims
      a count; clear it when the leading claim is `[ESTIMATE]`. The note marker
      is already authoritative — the date should follow it down as well as up.
- [ ] **Assert it stays zero.** A row claiming both is the integrity check; it
      belongs on the panel as a lamp that should never light.

**The unresolved one:** both the panel and the import brief measure *coverage*,
neither measures *decay* — which is the thing "data atrophy" actually names.
That needle is the cycle-count system's output and the two are not yet wired
together.

## Label printer — PRINTING AGAIN on a bypass feed, 2026-08-24

**No light on the front, will not power up** (Scott). All four ports dark and
the gateway cannot ARP it; see `TRAPS.md` for why that rules out the latched
raster error rather than pointing at it.

- [x] ~~Triage power~~ — **done 2026-08-24.** Meter reads **nothing** at the
      PA-AD-001A barrel jack on a known-good outlet with the plugs reseated.
      The fault is at or upstream of the jack's centre contact; adapter vs jack
      contact spring is still not separated, though the zero reading leans
      adapter. **The printer itself is fine** — mainboard, head, WiFi and the
      CUPS path all run on the injected feed.
- [x] ~~It is dead until the replacement arrives~~ — **no. It PRINTS.** Another
      session brought it back the same afternoon by injecting 25 V onto the rear
      lug of barrel jack J1 through a soldered pigtail. See `TRAPS.md`, both the
      bypass write-up and the correction that follows it.
- [x] ~~Cancel stuck job 29~~ — already gone; it timed out on its own. The
      queue now reports "The printer is not responding" instead of the
      "ready and printing" it claimed while the connection hung.

- [x] ~~**RETURN THE PRINTER**~~ — **replacement confirmed 2026-08-24.**
      Amazon RMA, not a refund, so no re-ordering needed.

      | | |
      |---|---|
      | replacement due | **2026-08-26** |
      | drop off dead unit by | **2026-11-19**, any Staples, no box needed |
      | both units | **(Renewed)** — refurbished, not new |

- [ ] **ON ARRIVAL: run it on AC with the battery OUT, and print one label.**
      This is the whole lesson of the failure — a battery-capable device on a
      dead supply looks perfectly healthy until the pack empties, so the mains
      path has to be proven deliberately. The replacement is also a Renewed
      unit, so its adapter carries the same risk. Do it the day it lands, not
      the day you next need a label.
- [ ] **Tidy up the bypass once the replacement is working.** Scott, 2026-08-24:
      *"when I get the new one, I will clean this up."* One solder joint on the
      board side of the barrel jack, plus the lead out of the case. Tied to the
      replacement landing 2026-08-26 — the bypass has to stay until then,
      because it is the only thing feeding the printer.
      The risk question around the return was raised on 2026-08-24 and decided.
      Closed. Do not re-open it.

- [ ] **The bench supply is consumed** until the replacement lands 2026-08-26.
      If it is needed for something else first, the escape is to cut the barrel
      plug off the PA-AD-001A and wire the brick straight to the pigtail — the
      replacement arrives with its own adapter, so the cut one just goes back in
      the box. (Only worth doing if the brick actually reads ~25 V, which on
      current evidence it does not.)

- [ ] **Carry the dead unit to Staples.** No box required, keep it in its
      original packaging, show the QR return code. Deadline 2026-11-19 — far
      enough away to be forgotten, which is the actual risk.
- [ ] **When it goes, stock #570 follows it out**, and the replacement comes in.
      Quantity stays 1 until then: initiating a return is a decision, not a
      movement. Only the drop-off is a movement.

      *(superseded reasoning, kept: buying a PA-AD-001A separately was rejected
      because the printer's own DC jack and internal power stage were equally
      unproven. The bypass feed has since proven the board good, so that
      reasoning no longer holds — but the replacement is already shipped, and an
      intermittent-or-unknown power fault on a five-day-old refurb is not worth
      keeping. Return still stands.)*

- [ ] **~~Then: stock #570 needs to follow the printer.~~ There is no stock row
      to follow.** Measured 2026-08-25 22:5x: `StockItem` **#570 does not
      exist**, and part **#1057** (QL-810W) holds **0 stock rows**. The claim
      above — "stocked 1 @ SLN/Electronics Bench" — was never true in the
      database, so a session acting on it hunts a phantom row.

      `PO-0134` still reads `received=1.0` and Complete, which is the other half
      of the same lie: the receipt counter advanced and the put-away never
      happened. That combination is this install's documented silent-save trap.

      **What this changes for check-in:** the replacement arrives 2026-08-26.
      There is nothing to correct, transfer or scrap first — check it in as a
      **new** serialised qty-1 row. Do not go looking for #570 to edit.

      Sweep-wide, the gap is isolated, not systemic:
      `itq run scripts/received_no_stock.py` checked all 156 received PO lines
      and `PO-0134` is the **only** one with zero stock. That settles the
      "worth checking whether other Complete POs have the same gap" question on
      the decision queue — answer: no others.

- [ ] **The DK-22205 roll (#922, stock #656 in BR-D3) stays.** Separate
      purchase, `PO-0133`, nothing wrong with it.
- [ ] **Nothing has printed since 2026-08-20 20:42** and nobody noticed for four
      days. The failure date is unknown — do not write one down.
- [ ] **A liveness lamp for the printer**, on the dashboard: last label that
      actually came out, not "queue accepting". Same distinction as the
      overnight job's "last SUCCESSFUL read, not last run".
- [ ] All labelling work is blocked until this is settled. See `LABELLING.md`.

## Sim project structure

**BO-0017 Sim G1000** created 2026-08-27 as a sub-build of BO-0006, mirroring
BO-0015 Sim Rudder Pedals. **No kit bin yet** — BO-0015 has #588 because its
parts were gathered; nothing has been gathered for the G1000. A location here is
a *place*, so the bin gets made when there is something to put in it.

- [ ] Define the G1000's scope. Created so the work has somewhere to hang; what
      it actually covers is Scott's call.
- [ ] Other sub-builds are hiding inside BO-0006 — Scott, 2026-08-27: *"probably
      plenty, its what happens when you try to rebuild history."* **Do not plan
      an audit for these.** The G1000 was not found by reading BO-0006; it was
      found because a physical item needed filing and had nowhere to point. A
      retroactive catalogue cannot enumerate the structure it is missing, by
      definition — you only learn a sub-build was missing when something asks to
      belong to it.

      So the discovery mechanism is the drawer walk, not a review, and the walk
      is quietly doing two jobs. What that costs is a *prompt*: when a part's
      home is "the X part of project Y" and Y has no X, that is the signal.
      Radio stack, yoke, throttle quadrant, instrument panel are the likely
      names — but wait to be asked rather than pre-creating empty builds, for
      the same reason BO-0017 has no kit bin.

## The Amazon sweep has holes — and that is worse than a missing vendor

Chased the wrong gap first. On the 775 motors Scott recalled *"Banggood or
AliExpress"*, so this was queued as an unknown-vendor blind spot. Then he
searched his own order history and found them: **Amazon, ASIN B08NTK8JXZ, brand
Puly, purchased 2024-01-07.** The Amazon-format FNSKU on the carton was right and
the recollection was wrong.

**Amazon is the most heavily swept vendor here — 396 supplier parts.** A
two-year-old order for a $27 item produced no PO and no supplier part until it
was entered by hand on 2026-08-28. That is not a channel nobody looks at; it is a
hole in the channel everyone assumes is covered.

**MEASURED 2026-08-28** with `scripts/import_gap.py`, of the 507 parts carrying a
seeded purchase-history block:

    no PO line     475   94%   the money never became an order
    no stock row   365   72%   bought, never recorded on hand
    all three       25    5%   invisible unless a box turns up  ($467 lifetime)

**The import creates a part and stops.** No purchase order, no stock row. So the
catalogue says a thing exists and nothing says we own one — which is exactly how
the X27 steppers read zero for three years with seven of them in a box.

**And the 775s are a worse mode than any of those.** They were not in the 507:
no part, no history block, nothing. The 2024-01-07 order was never imported at
all.

**That second mode cannot be measured from inside this system.** We can count
parts with no stock; we cannot count orders never seen, because the only record
of them is in the mail. The sole way one surfaces is a box on the bench — which
is structurally why Scott had to go looking, and why no query here would have
found it.

- [ ] **Make the import create stock and a PO, not just a part.** 365 rows say
      it should have been doing this all along. Backfill is a separate question
      from stopping the bleeding.
- [ ] **Reconcile against the order source, not against InvenTree.** Enumerate
      Amazon orders from the mail and subtract what has a supplier part. That is
      the only query that can find mode two, and it has to run from outside.
- [ ] Banggood still has no company record. Keep the question, drop the
      priority: it was a guess, and the guess was wrong.

## Homeless by design — L1-D2

Parked 2026-08-28 at Scott's "L1D2 for now". Both carry **no default_location**
deliberately: `default_location` is where a spare goes home, never a staging
area, so leaving it empty keeps them visible as homeless. A wrong home is
invisible; homelessness is a report.

- [ ] **2020 T-nut assortment** (#1141) — hardware, wrong wall for electronics.
      Its 120 is a pack figure and the box is visibly open, so it is an upper
      bound. `[ESTIMATE]`, no stocktake date.
- [ ] **SAE bearing-ball assortment** (#1142) — 600 pc, six inch sizes.
      `[ESTIMATE]`, no stocktake date.
- [x] ~~XFFCSEC 150 pc 5x20 glass fuses~~ — filed 2026-08-28 into **L2-D2**
      (#1143), one part not fifteen, `[ESTIMATE]`, no stocktake date.
- [ ] **The rest of L2-D2 is uncatalogued — roughly 10 items.** Scott showed the
      open drawer 2026-08-28: *"I don't wanna get into it right now, but just to
      give you an idea."* Contents are written into the location description so
      the knowledge is not stuck in a photo. **It is a themed drawer — wire
      termination and connectors** — not the "assortment kit boxes" first
      assumed, which matters for where future terminations should land.

      Seen: copper lugs; BaaLA 520 pc butt splices; InstallGear 180 pc; ferrule
      assortment; loose heat shrink; innhom 532 pc heat shrink; a box labelled
      "NO"; the fuse kit (#1143, done); a bagged connector; pin headers; PA2.0 /
      XH 2.54 / PH 2.0 connector kits. One compartment empty.

      Note when it is worked: heat shrink already exists as parts #504-#508 at
      zero stock, and JST XH parts #875/#893/#894 live in a *kit* location — so
      several of these will be merges, not new records.
- [ ] Kit boxes are now split across **L2-D2 and L2-D4**, and L2-D4 was already
      described as the assortment-kit-box drawer. Worth settling which is the
      real one before more kits land in whichever is nearer.

## Vacuum table gasket — ANSWERED, and the answer was already on the shelf

The uxcell solid NBR cord (#1149) was bought for vacuum table gasketing and
rejected as **too rigid**. From that failure the requirement was written down:
soft closed-cell sponge, low compression force, not solid rubber, not open-cell.

**Scott had already bought exactly that a year earlier.** Canal Rubber, ordered
2025-07-31, never used, now catalogued:

- **#1150** closed-cell neoprene sponge cord, 1/8 in, 100 ft, $24.84
- **#1151** closed-cell neoprene sponge cord, 3/16 in, 100 ft, $37.26

Nothing connected the requirement to the answer because the purchase had never
reached the catalogue. That is the import gap costing real time, not just tidiness.

**Reorder path recorded on both parts and on the supplier**, at Scott's
insistence: Canal Rubber, 329 Canal St NY, 212-226-7339, contact Marty, **no
online cart** — they cut to length and take a card by phone. Their published web
prices are explicitly not current. **A Canal Rubber purchase can never be found
by a mail sweep**, because there is no confirmation email to find; the catalogue
record is the only record there will be.

- [ ] Vacuum table project is on hold and has no build order — Scott: "don't
      need one yet." When it starts, the gasket question is closed.

## G1000 / BO-0017 — see docs/G1000.md

Six bare PCBs catalogued 2026-08-29 (#1152-#1157) with provenance recovered from
two PayPal receipts. **No stock rows yet — no container.**

- [x] ~~Container~~ — done 2026-08-29. Working set on the mobile cart at MC-T3
      with the Cessna parts; spares in a new bin, WS2-S4/Sim G1000 Spares, on
      the wire shelves. Seven stock rows placed.
- [x] ~~Shields counted~~ — 10 fabbed at JLCPCB, 7 unbuilt + 1 built + 2 sold.
- [x] ~~Missing boards~~ — NOTHING MISSING, Scott counted 2026-08-29. Three
      receipt-derived counts in docs/G1000.md were wrong first. Receipts give
      provenance, not quantity; count the pile.
- [ ] **Next build is the PFD (left)** — Peter's shield plus the left/right/
      softkey daughter boards already on the bench. MFD and GMA1347 are built.
      Six spare shields remain after it.
- [x] ~~Do we own the panel Gerbers~~ — YES, FSD downloads, "Expires: Never".
      Anything can be re-fabbed.
- [x] ~~Design files~~ — retrieved 2026-08-29, attached to part #1153. 195MB
      ZIP: Gerbers, 69 STLs, laser files, 3 instruction PDFs. Folder is named
      **FSD G1000 v2.3**, matching the boards.
- [ ] **Claim the GMA1347 download back.** Checked 2026-08-29: the account's
      Downloads page lists ONLY FSD G1000 v2. The GMA1347 entitlement was
      REMOVED — no fresh link can be minted. Paid $8.99, order #9581, PayPal
      15K42283TC508724N, and FSD's own email says "Expires: Never". Support
      ticket or Dave at shop@flightsimdiy.com.
- [ ] **Check the FSD account for the current version.** Perpetual downloads are
      usually updated in place, so the 2024 entitlement may now hand over a
      NEWER revision than the v2.3 boards on the shelf. FSD publishes no version
      numbers publicly. Free to check, and it decides whether the shelf stock is
      already superseded.
- [ ] **Was the GMA1347 faceplate ever fabbed?** Design already paid for, so it
      is a JLCPCB upload, not a repurchase.
- [ ] **#1156 GMA1347 Control v2.2 and #1157 G1000 Control v2.3 have no target.**
      They are build #1's retrofit and Scott is not going back to it. Current
      products with an active community, so selling or giving them on is a real
      option beside keeping or binning.
- [ ] **Shopping for build #3:** 2x MEGA 2560 PRO (#74) and 2x 74HC4067
      (#21/#436), all at zero stock. LM2596 is covered — 15 at A3-R7C2.
- [ ] #21 and #436 look like the same 4067 breakout twice — fourth duplicate
      pair of that shape found today.

## Bench work still parked

- [ ] **Find the 2x RKJXT1F42001 nav switches** (stock #9). Either in the mobile
      cart or already fitted into the G1000 panel — now **BO-0017 Sim G1000**,
      a sub-build of BO-0006. **The two answers differ in kind**: in the cart they are stock
      (2 on hand, available to another build); in the panel they are consumed
      (quantity 0). Reading 2 in stock when they are soldered in is how a build
      gets planned around parts that do not exist.
- [ ] **Tapmatic No.90X** (stock #586, $2,005) — Mill Cart as a spindle
      accessory, or TC-D1 with the tap wrenches? Left unfiled rather than
      guessed.
- [ ] **Two BT30 pull-stud rows** (#11, #14) — where studs live is a policy call,
      not a tidy-up: CLAUDE.md's rule is that the HOLDER decides the knob.
- [ ] **Four zero-quantity pull-stud rows** (#587-#590), two apparent duplicate
      pairs. Read the notes BEFORE merging — this install deletes a stock row's
      notes when it hits zero.

- [x] ~~File the two bus caps~~ — done 2026-08-28 into **A3-R7C5**, not the
      large B3-R5C4 first proposed. Scott: they fit a smaller drawer. Kept out
      of the A3-R8 capacitor row deliberately: that row is 25-50 V signal parts
      picked up bare-handed, and these are 400 V.
- [ ] Measure the heatsink TO-220 hole spacing, then file to B3-R5C3.
- [ ] RB-26 … RB-28 — never opened. (RB-18 … RB-24 walked 2026-08-25; see the table at the top of this file.)
- [ ] Verify the acrylic is **cast, not extruded** (part #1083, L1-D3). The
      listing says cast but that is seller copy, and it decides whether it
      lasers cleanly. Not urgent — but do it before cutting something that
      matters.
- [ ] Print a test address label → decide whether DK-11201's minimum comes off.
- [ ] InvenTree upgrade — **in Florida, co-located with the Mini**.

## The Jet mill/drill is not in the shop documentation

Found 2026-08-26 while tracing why ten bearing rows had no home. They were
bought through 2022 for an **automated head mover** on a Jet mill/drill —
built, installed, and photographed that day, in service in the shop.

Nineteen machines are documented. This one is not, and neither is the head
mover on it: no drawing, no BOM, no note anywhere. The only reason the story
was recoverable at all is that Scott remembered the phrase "automated head
mover for the Jet Mill Drill" when shown a chain roller.

That is the gap worth closing. Purchases for an undocumented machine look
identical to purchases for nothing, which is exactly how these ten rows read
until this afternoon.

Recorded as [Jet Mill/Drill Automated Head Mover](http://192.168.50.10:8001/web/part/1126).
Wants: the machine itself in the equipment documentation, and enough of the
head mover written down — motor, drive ratio, sprockets, control — that the
next repair does not start from a photograph.

## Cable consolidation — B0-R1 started 2026-08-29, DELIBERATELY UNFINISHED

Scott: *"R1 sounds good, hold off for now on the rest but don't lose track of
it."* So this is parked, not dropped.

**Done:** `B0-R1C1` HDMI / `C2` USB / `C3` video-display-other / `C4` power &
misc, all described. The micro-HDMI adapter (#1145, stock #731) moved out of
B3-R5C1 into `B0-R1C1` and its `default_location` follows.

**NOT done — the sweep.** Assembled cables are still findable in four places,
which is the problem B0-R1 exists to end:

| Item | Currently | Belongs |
|---|---|---|
| IR Emitter Cable IR-TX1-M, dual head | `B3-R4C6` | `B0-R1C4` |
| IR Emitter Cable, Logitech Harmony, single head | `B3-R4C6` | `B0-R1C4` |
| Adafruit STEMMA QT / Qwiic Cable, JST SH 4-pin | `B3-R3C5` | `B0-R1C3` or leave |
| SMA Female to U.FL/IPEX Pigtail | `A3-R6C6` | `B0-R1C3` or leave |
| Ribbon Cable jumper wires x4 | `MC-T1` | LEAVE — mobile cart working set |

**Not free to do**, which is why it is parked: every one of these currently fits
where it is, so the move buys consistency and costs handling. Worth doing when
the next cable arrives and the row has to be walked anyway.

**Also pending:** labels for `B0-R1C1..C4` — created but never printed, so the
drawers are physically blank. Tape is finite; ask before running four.

**B0-R2..R6 remain empty** (20 large drawers) and A0 is a whole untouched
cabinet of 24. Cable expansion has somewhere to go.

## Tormach passive probe is WIRELESS now — learned 2026-08-29

Scott, on the 5-pin DIN cable found at the bench: *"that was from the Tormach
passive probe before I converted it to wireless."*

Nothing in InvenTree recorded the conversion, and nothing would have re-derived
it — the probe kit (#567) still read as a stock item with no hint that its
interface had changed. Now written onto stock #177 and onto the cable's own row.

**CORRECTED 2026-08-30 — it is spare stock, and it IS in the cable row.** Scott:
*"this is a spare cable... the probe lives at the 1100MX, but this has nothing to
do with this. We're putting this into stock for use on a project later on, an
unnamed project so far."*

Filed to **B0-R1C4** (part #1161), renamed `Cable, 5-pin DIN to threaded barrel,
~6 ft (ex-Tormach probe)`, recategorised to Electronics/Connectors to match the
other DIN cable (#786), and relabelled.

**What went wrong is worth keeping.** The original filing came with a confident
argument — an instrument cable must stay with its instrument, separating them is
how the instrument goes dead. The argument was sound. **The premise was
invented:** nobody had said this was the probe's working cable. The probe runs
wireless and needs nothing from it. A good argument on an assumed premise is
harder to catch than a bad argument, because the reasoning survives inspection
and the assumption never gets stated out loud to be checked.

It also broke a rule already written down: `default_location` is where a SPARE
GOES HOME, never where a machine happens to live. "Machine Shop" is a place a
mill is, not a home for a cable.

The name failed the same way — `Tormach Passive Probe` and `SUPERSEDED by
wireless` both described where it came FROM rather than what it IS, and a spare
gets found by its connectors. Provenance moved to the description.

**The battery question was already answered, five days before I asked it.**
Stock #92, `LiPo Battery 3.7V 750mAh 902040`, is recorded 2026-08-25 as
`belongs_to` the probe kit — structurally installed, not merely noted, with
`location: None` as the correct state for a fitted part. Scott, 2026-08-29:
*"there's a lipo recently replaced and the part was actually cycled thru
InvenTree."* Correct, and it is the model for how a consumable inside a tool
should be recorded.

**Search the database before raising an open question.** The battery, the DIN
cable in the standing desk (#786) and the 6-20P plug were all handled the same
careful way in August, and the note on each says so.

**OPEN — a PCB-production probe build has been discussed but does not exist in
InvenTree.** Scott, 2026-08-29: *"there has been discussion of building another
probe to be used for circuit board production, this cable will be helpful."*
**ASKED AND ANSWERED — no project, 2026-08-29.** Scott: *"there is no project at
this point."* It is a conversation, not a build. **Do not re-offer this every
time the DIN cable surfaces** — a BO created before the thing is real is an
empty shell that makes the board look busier than the shop is.

**Revisit when a part is actually bought for it**, which is the point a build
stops being discussion. Until then the cable's earmark note carries the intent,
and that is the right weight for it.

**CLOSED — FIVE pins, counted by Scott 2026-08-29.** The name stands and no
reprint is owed. Worth keeping the entry: it was written from pins counted in a
photograph and happened to be right, which is luck, not method — #786 in this
same shop is a seven-pin DIN, so the coin could have landed either way.

**Decided: `SUPERSEDED by wireless` STAYS in the name.** It is true of the
1100MX, the earmark for the possible PCB probe lives in the stock notes, and
spending a label to soften an accurate warning is the wrong trade. The original
worry — that a reader might bin it on the label alone — is thin when the cable
sits in the Machine Shop beside the probe it belongs to.

**(historic wording of this item)** Part #1161 is named `5-pin DIN`
on the strength of pins counted IN A PHOTOGRAPH, which is the exact inference
this project has a trap about. #786 is a SEVEN-pin DIN, so the two counts are
live in the same shop. Verify by eye and rename #1161 if it is wrong; the label
is already printed and would need reprinting. **Bundle it with the SUPERSEDED
rename** — the name is true of the 1100MX but misleading now the cable has a
build waiting for it, and both fixes want the same single reprint.

## Pull studs — filed 2026-08-31, Unfiled nearly empty

Scott's actual goal, stated after the fact and worth leading with next time:
*"my real goal was to move them from unfiled to tool rack for the installed
parts and tool chest for the unused."*

| | Where | Rows |
|---|---|---|
| **Unused** | `Tool Chest`, no drawer | 10 Haas standard, 6 TSC, 1 Shars M12x45 |
| **Installed** | `Toolholder Rack` | 4 TSC via `belongs_to` the shrink-fit holders; the spent Shars/Tormach rows at zero |

`stud_check` reports **11 standard and 6 TSC unused**, matching Scott's bench
count exactly.

**`Unfiled - Machine Shop` is down from 8 rows to 2** — the RKJXT1F42001
navigation switch (#9) and the Tapmatic No.90X tapping head (#586). Its own
description says it should trend toward empty, and it is.

**The fitted studs carry BOTH `belongs_to` and a location.** `belongs_to` is
what makes them read as spent rather than available; the location is what makes
them show up when you look at the rack. The LiPo precedent left location null,
which is correct for a part sealed inside a device — a stud in a holder on a
rack is visible and worth finding, so it gets both.

## Standing checks — added 2026-08-31/09-01, none of them clean yet

Four rules that existed as prose and were never enforced now have scripts. Each
one found real breakage the moment it ran:

| Check | Now says | What it means |
|---|---|---|
| `pack_audit.py` | **31** supplier parts contradict their own SKU | receiving any of them books a whole pack price against one piece |
| `orphan_stock.py` | **32** rows have no location at all | owned, catalogued, findable by nobody |
| `import_coverage.py` | parts predate the first PO for 4+ suppliers | old orders became parts, never POs |
| `test_stud_alarm.py` | passes | the bare-holder alarm actually fires |

**None of these are urgent and all of them are real.** The 31 pack mismatches
are the most valuable to work: each one is a wrong price and a wrong count
waiting for the next receipt.

## Not mine to fix — the panel's UNFILED lamp

The annunciator reads **2** where the truth is **34**. It counts rows in
locations *named* `Unfiled - *` and cannot see `location IS NULL`. The generator
lives in the overnight-import project, not this repo. The fix is to count both:

    StockItem.objects.filter(location__isnull=True, belongs_to__isnull=True)
      + rows in any location whose name starts with "Unfiled"

The `belongs_to__isnull=True` exclusion is required — an installed part (a stud
in a holder, a LiPo in a probe) legitimately has no location.

## The roller chain's missing 36 inches

Bought as 120 in (10 ft, 320 links) on 2022-02-07; **84 in on the bench.** So 36
in / 96 links are in something, and nothing records what. The kit also shipped a
chain breaker and **5 connecting links**, neither catalogued — and without a
master link a chain cannot be closed into a loop, so those matter more than
their price suggests.
