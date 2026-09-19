# Labelling

How labels get printed in this shop, why the setup looks the way it does, and
what is still undone. Written 2026-08-20, after an evening that cost far more
than it should have because the obvious approach does not work on this printer.

Related: `docs/TRAPS.md` (the individual gotchas), `docs/TECHNIQUES.md`
(bagging), `plugins/cups_label/` (the plugin), `scripts/mark_labeled.py`.

---

## The printer

**Brother QL-810W, PRINTER_IP (static), at SLN.** InvenTree runs on the Mac
Mini at LRD, so every print job crosses the site-to-site VPN — roughly 120 ms
RTT. That is fine; latency was investigated and is not a problem.

Media is **62 mm × 5 m continuous DK tape**. The printer reports it as
`62mm / 2.4"` and IPP reports `roll_current_62x0mm`.

### Power — and the 2026-08-24 dead-printer diagnosis

From Brother's own spec page, recorded because this doc had no electrical
detail at all until the unit would not switch on:

| | |
|---|---|
| AC adapter | **PA-AD-001A** — `INPUT AC 100-240 V 50/60 Hz`, `OUTPUT DC 25 V - 3.6 A` |
| Optional battery | **PA-BU-001** Li-ion, `14.4 V` |

**Measuring the adapter is valid — a regulated switching supply shows its rated
voltage unloaded.** Needing a minimum load to start is a property of
unregulated or current-limited supplies, not a standard barrel-jack wall wart,
so a reading of zero here is evidence and not an artifact. Two things that fake
a zero and should be ruled out first: the meter left on the **AC** range, and
the probe bottoming out on plastic without reaching the recessed **centre pin**.

Expect ~24-26 V DC, centre positive.

**Scott's hypothesis, 2026-08-24: the AC side never worked and the printer ran
on battery until it went flat.** It fits the record — 15 jobs on the setup
evening of 08-20, nothing completed since, and the unit was only a few days old.

What makes it decisive rather than merely plausible:

- **A working adapter charges the battery**, so a flat pack should be impossible
  after days on mains. A flat pack is therefore evidence *about the adapter*.
- **Good AC takes over from a flat battery.** If the adapter were healthy, a
  dead pack would not stop the printer.
- **But a failed Li-ion pack CAN pull the rail down even on good AC**, which is
  why removing it is a real test and not just elimination. If the pack is
  swollen, warm, or deformed, take it out regardless and do not recharge it.

Order of work, cheapest discriminator first:

1. Meter on **DC volts** across the barrel jack, centre pin. ~25 V means the
   adapter is fine and the fault is downstream; 0 V means the adapter is dead
   and nothing else needs testing.
2. Pull the **PA-BU-001** and try on AC alone.
3. Only then suspect the printer itself.

### brother_ql does not work on this unit — do not try again

The obvious path — `brother_ql` raster over port 9100, which is what the
`inventree-brother-plugin` uses — **fails completely on this printer**, and
fails silently. It accepts every job, prints nothing, latches a blinking red
error, and has never once answered a status request.

Ruled out, each by direct test rather than reasoning:

| Suspected cause | How it was eliminated |
|---|---|
| Network path | Closed ports refuse honestly, open ports open, HTTP fetch works end-to-end from the Mini. No middlebox. |
| Truncated job | Printer accepts every byte and closes its side cleanly; `close()` does not block. |
| Wrong media setting | `62` (endless) was correct all along; the roll is confirmed 62 mm × 5 m. |
| P-touch Template emulation | Changed to `Raster` in the web UI and verified by reading it back. Still fails. |
| My `convert()` arguments | Stock `brother_ql` CLI defaults against a freshly cleared printer. Still fails. |
| Editor Lite mode | Confirmed off. |

The printer's own configuration report prints perfectly, so the hardware, the
roll, the loading and the cutter are all fine. **The fault is in the raster
subsystem specifically**, and no software change on our side reaches it.

### What works: CUPS / AirPrint

The same printer's **IPP stack is healthy** — it reports `printer-state: idle`,
`printer-state-reasons: none`, and correctly identifies its own loaded media,
*even while the status LED is red from a failed raster job*. It accepts
`image/urf` (Apple Raster), which CUPS generates from a PDF with no vendor
driver at all.

```bash
lpadmin -p QL810W -E -v ipp://PRINTER_IP/ipp/print -m everywhere
lpadmin -p QL810W -o MediaType=Roll -o CutMedia=EndOfPage -o cupsPrintQuality=High
```

Queue defaults matter more than they look: **InvenTree submits through CUPS
knowing none of this**, so whatever the queue defaults to is what InvenTree
gets. The driver's own default `PageSize` is `29x90mm` — a die-cut size
unrelated to the roll loaded — and `CutMedia` defaults to `None`, which is why
early tests ran tape forever without cutting.

### The plugin

`plugins/cups_label/` implements `LabelPrintingMixin` and shells out to `lp`.
It deliberately does **not** use `pycups`: that needs CUPS dev headers and is a
build headache on macOS, and `lp` is the command already verified by hand.

Settings: `QUEUE` (default `QL810W`), `SET_PAGE_SIZE`, `EXTRA_OPTIONS`.
`print_label()` receives `pdf_data` plus the template's `width`/`height` in mm
and turns them into `PageSize=Custom.WxHmm`.

---

## Templates

InvenTree's stock templates are 50 × 20 mm and **cannot be used on this roll**.
Two independent problems, both fixed by authoring at the tape's real width:

1. **CUPS silently upscales a page narrower than the media.** A 50 mm page on
   62 mm tape is scaled 1.24×, which enlarges the QR and pushes the overflow
   off the bottom. `print-scaling=none` and `=fit` do nothing — the option is
   not in this queue's `lpoptions -l` list, so CUPS ignores it.
2. **A thermal printer cannot mark its unprintable margin.** The stock template
   pins the QR at `left:0/top:0` sized to the *full* label height, so it touches
   both edges and gets clipped. A QR that loses part of a finder pattern or its
   quiet zone does not degrade — it stops decoding.

| Template | Size | QR | Notes |
|---|---|---|---|
| `Shop Location 62mm (QR + Text)` | 62 × 25 mm | ~19 mm | |
| `Shop Location 62mm Compact (QR + Text)` | 62 × 16 mm | ~12 mm | **default** — matches the Avery 5167 scale already in use |
| `Shop Part 62mm (QR + Text)` | 62 × 18 mm | ~14 mm | name (3 lines) + location · category |
| `Shop Stock Item 62mm (QR + Text)` | 62 × 18 mm | ~14 mm | name + quantity · location + serial/batch |

## Printing an Avery sheet — the Chrome route

The 62 mm roll goes through CUPS (below). **Avery sheets go through Chrome**, and
the settings matter more than the file does: a die-cut sheet is unforgiving, and
every one of these failures prints a whole sheet of scrap.

**Open the `.html`, never the `.svg`.** `make_labels_avery.py` writes both. Chrome
treats a bare SVG as an *image* and fits it to the printable area, which shifts
every label a few millimetres off its die-cut — the sheet looks fine on screen and
is unusable on the page. The HTML wrapper pins it: `@page { size: 8.5in 11in;
margin: 0 }` with the sheet held at exactly 816 x 1056 px = 8.5 x 11 in at 96 dpi.

    itq run scripts/make_labels_avery.py --set col0     # top | bottom | col0 | all
    itq pull <BACKEND>/avery5167_col0_p1.html ~/Desktop/
    open -a "Google Chrome" ~/Desktop/avery5167_col0_p1.html

Then **Cmd-P**, and set all four:

| setting | value | why |
|---|---|---|
| Paper size | **Letter** | the sheet is authored at 8.5 x 11 exactly |
| Margins | **None** | any margin re-centres the grid |
| Scale | **100%** — Custom, *not* "Fit to printable area" | Fit is the default and it silently shrinks by a few percent |
| Headers and footers | **off** | the header pushes the whole grid down |

**Then print one on plain paper and hold it against a blank Avery sheet before
committing a real one.** Every label failure in this shop passed an automated
check and was caught by eye; a sheet costs more than the thirty seconds.

The label carries the ADDRESS only — a place, not contents — plus a QR of the
same plain text, so any phone reads it and BinScan takes it directly.

Sources live in `labels/`. Rules any new template must follow:

- **Author at 62 mm.** Never narrower, or CUPS will scale it.
- **Inset everything ≥ 2 mm.** Verify by rendering to PNG and measuring the ink
  bounding box, not by looking at printed tape.
- **Truncate in the template** (`|truncatechars:N`), never with CSS
  `overflow: hidden` — WeasyPrint ignores overflow on absolutely-positioned
  blocks, and a long name silently overprints the line below it. A margin check
  cannot catch that, because overlapping text is still ink in the right place.
- **Use `{% comment %}`, not `{# #}`,** inside a block. Django's hash-brace
  comment is single-line only; a multi-line one renders as visible text across
  the label. This actually happened, on real tape.
- **Look at the rendered PNG before printing A NEW OR CHANGED TEMPLATE.** Every
  failure above passed an
  automated check and was caught only by looking.

### Why the stock item template exists

InvenTree ships **exactly one** stock item template and it is a bare QR with no
text — a printed stock label could not be identified without scanning it.

### Why part labels show location, not IPN

370 of the existing IPNs are **Amazon ASINs** (`B017KUC6XQ`). Standing at a
drawer, where the part lives is the useful fact; the ASIN is noise.

---

## Tape is finite — printing is opt-in, never automatic

**As of 2026-08-21 the shop is still on the starter tape that came with the
printer, and no replacement DK rolls have been ordered.** Scott, when a
per-part label print was being made routine: *"we don't have that much label
stock... we gotta be careful."* Remaining length is **not known** — nobody has
measured what is left on the roll, and this doc will not guess.

So: **never print as a side effect of filing a part.** `print_part_label.py`
defaults to render-only and requires an explicit `--print` for exactly this
reason. Ask before printing a batch.

What a roll buys, for planning. A full 62mm × 5m continuous roll is 5,000mm of
tape, and continuous DK tape is consumed by label *length*, so:

| Template | Length | Labels per full roll |
|---|---:|---:|
| Location 62mm Compact | 16mm | ~310 |
| Part / Stock Item 62mm | 18mm | ~275 |
| Location 62mm | 25mm | ~200 |

Those are ceilings — they ignore the feed the cutter eats between jobs, which
is per-job, so **one batch of 20 wastes far less than 20 separate prints.**
Batch the work.

Against that: 368 of 474 locations are still unlabelled, which is already more
than one full roll before a single part label is printed. Locations earn the
tape first — a drawer with no label cannot be found at all, whereas an unlabelled
bag inside a labelled drawer is merely slower.

## How labels actually get installed

The sheets are printed; sticking them on is the slow part, and it is done two
ways rather than as a project:

1. **On demand** — whenever something goes into a drawer, that drawer's label
   goes on first. Filing and labelling happen together, so a drawer that holds
   something is always findable.
2. **Opportunistically** — a few at a time during downtime, e.g. while a long
   tool run is going. Scott, 2026-08-21: *"That way, they get on as straight as
   possible, and I'm not just rushing through it."*

Neither is a backlog to be cleared in one sitting, and the gap between
*printed* and *affixed* is therefore expected, not a defect. **Do not treat
unaffixed drawers as work outstanding** — no batch print is needed, and
nagging about them optimises the wrong thing. A crooked label on all 324
drawers is worse than a straight one on the 100 that hold something.

Mark them as they go on: `itq run scripts/mark_labeled.py --rows A3 1 1`.

## Coverage

Tracked as `metadata.labeled` on each `StockLocation`, beside `metadata.size`,
so a batch print can skip what is done. Managed by `scripts/mark_labeled.py`
(`--report`, `--cabinet X`, `--rows X 4 8`, or bare names).

**"Labelled" means carrying a PRINTED QR label.** Several cabinets have
handwritten paper labels from before this system existed — `1/4-28 NUT`,
`TOGGLE SWITCHES`, `ARDUINOS`. Those must stay flagged false: they carry no QR,
nothing links them to InvenTree, and they are exactly the drawers still to do.

As of 2026-08-21 — **131 of 475 affixed**, with **216 more printed on Avery
sheets and waiting to be stuck on**. A3 and B3 are complete; A1, A2, B1 and
B2 are printed throughout and awaiting install. Those two numbers are different things
and only the first is what `labeled` records; see the three-state trap in
`TRAPS.md`. Installing is a slow manual job done a bit at a time, so the gap
between them is normal and is NOT a reason to print anything.

| Location | Done | Total | |
|---|---:|---:|---|
| Laser Area (L1, L2, LW1–3) | 5 | 5 | complete |
| L1, L2 drawers | 14 | 14 | complete |
| B3 | 44 | 44 | complete |
| Assembly & Test (AT-D1..D3) | 3 | 3 | complete |
| A3 | 64 | 64 | complete 2026-08-21 |
| A1, A2 | 0 | 128 | all 128 printed on Avery sheets, awaiting install |
| B1, B2 | 0 | 88 | all 88 printed on Avery sheets, awaiting install |
| Red Bins | 0 | 28 | |
| everything else | 0 | ~100 | |

Only mark what someone has **seen**. A wrongly flagged location is worse than an
unflagged one: the unflagged drawer gets a spare label printed, the wrongly
flagged one stays bare forever because nothing will offer to print it again.

**Reassigning a drawer does NOT invalidate its printed label.** This was got
wrong on 2026-08-21: B3-R5C2 was given TO-220 regulators and `labeled` was
flipped to false on the theory that its label had gone stale. It had not.
Principle 1 is that **locations are addresses, never contents** — a printed
label says `B3-R5C2` and a QR of the same string, and an address does not go
stale when the contents change. That is the entire reason the scheme is
addresses.

What *does* go stale is the **legacy handwritten tag** from before this system:
B3-R5C2 still carries a paper "PCB terminals" label, and those went to
A3-R8C6/R8C7 long ago. Those tags were never tracked by `labeled` (see the rule
above — they carry no QR and are flagged false by definition), so contents
changing cannot make the flag wrong.

So on reassignment: rewrite the `description`, and leave `labeled` alone.
Flipping it to false would queue a reprint of a label that is already correct —
spending tape that, per the section above, the shop does not have.

---

## Open items

- **LW1–LW3 shelves** (`LW1-S1`, `LW1-S2`, … six total) — the cabinets are
  labelled; unknown whether the shelves inside are.
- **A stray CUPS queue** `_PRINTER_IP_` sits on the Mini beside `QL810W`.
  Harmless but should be removed so there is one obvious queue.
- **Shop-made parts have no IPN scheme.** [925] tie wrap hold-down and [926]
  bagging funnel are the first parts the shop *makes* rather than buys. There is
  no internal part-number convention at all, and no category fits. Both are
  deliberately left blank with notes explaining why, because whatever they get
  sets the precedent.
- **CAD sources not attached.** Both shop-made parts carry a TODO to attach the
  STL / Fusion file. This is the entire reason they were catalogued: reprinting
  should be a download, not an archaeology expedition.
- **41 parts are homed to a site** (`SLN`, `LRD`) rather than a drawer.
- **AT drawers have no `metadata.size`** — they are outside the Akro-Mils
  cabinets and were not part of the 324 measured, so capacity there is guesswork.

## Buying replacement tape — one full roll is the whole shop

The starter roll is 62 mm × **5 m**. A standard DK-2205 replacement is 62 mm ×
**30.48 m** (100 ft) — **6.1× the starter**. That ratio is the buying decision,
because the starter roll is the only tape anyone here has ever seen and it
badly understates what a real roll holds.

| Template | Length | Labels per full 30.48 m roll |
|---|---|---|
| Location 62mm Compact | 16 mm | ~1,905 |
| Part / Stock Item 62mm | 18 mm | ~1,693 |
| Location 62mm | 25 mm | ~1,219 |

Against the actual shop: 324 drawers at 16 mm plus ~1,050 catalogue parts at
18 mm is **24.1 m**. One roll does all of it with 21% spare. **Never buy a
multi-pack** — a 12-pack is roughly a decade of tape, and thermal stock does
not improve with age.

### Third-party DK-2205 is fine; the spool is the thing to check

The QL-810W identifies media from a **pattern on the black plastic spool
end-cap**, not from a chip — there is no cryptographic lockout on DK rolls for
this model, which is why compatible DK-2205 is a routine substitution at about
half the genuine price. `DK-2205` and `DK-22205` are the same tape under US and
EU part numbers.

Two rules that make the substitution safe:

- **Keep the Brother starter spool forever.** If a third-party end-cap
  misreads, transfer the roll onto the genuine spool. Preserving it costs
  nothing and is the entire fallback.
- **Test a new roll the day it arrives, on a throwaway label.** Media errors on
  this printer *latch* — a misread is not a soft retry, it has to be cleared.
  Discovering that mid-run, at night, is how an evening disappears.

### Do not "upgrade" to wider tape

4in × 100ft is often a dollar or two more for 65% more tape, and it would break
every template in the shop. **CUPS silently upscales a page narrower than the
media** — the documented failure that enlarged the QR and pushed text off the
edge. 62 mm is not a preference, it is what the whole pipeline is authored
around. Width is a compatibility spec; only length is a quantity.


## When to preview, and when to just print

The look-before-you-print rule is scoped, and it was being applied too widely on
2026-08-22 — a routine part label turned into render, pull, rasterise, read,
print, verify. Scott: *"we cant do this dance every time we print a label."*
Correct, and the friction is the danger: a check that costs six steps is a check
that gets skipped on the day it would have caught something.

**Preview when the RENDERING could be wrong:**
- a template that is new, edited, or has never printed on this stock
- a different label size or a different tape
- the first label of a batch — then print the rest without re-looking
- any label whose text length is unusual (very long part names wrap or clip)

**Just print when only the DATA could be wrong:**
- a proven template (9, 10, 11, 12 are all in daily use) with ordinary content

The reason is that these two failure modes are caught in different places. A
rendering fault — clipping, upscaling, a blank QR — is invisible in the database
and only the eye catches it. A data fault — wrong part, stale location line — is
visible in the record *before* you print and is better caught by reading the row
than by squinting at 62 mm of tape.

**One-step preview:** `itq png /tmp/label_part_1058.pdf` pulls the PDF and
rasterises it with `qlmanage` in a single command. That exists so that when a
preview IS warranted it costs one step instead of three. poppler is not
installed on this laptop; `qlmanage` is macOS built-in and needs nothing.

---

## Did it actually print? — the check from the Mini

Submitting is not printing. This printer's entire failure history is *accepting a
job and doing nothing*, so `lp` returning a request id proves only that CUPS took
it. Two readings, one either side, are what turn a submission into evidence.

**Before — the error state LATCHES,** so a job sent into a sulking printer is a
no-op that reads as a failure and sends you chasing the wrong thing. Clear, then
send ONE:

```
lpstat -p QL810W     expect "is idle.  enabled since ..."
lpstat -o            expect nothing pending
lpoptions -p QL810W | tr ' ' '\n' | grep printer-state
                     expect printer-state=3, printer-state-reasons=none
```

**After** — the job leaves the queue within seconds and the printer returns to
`printer-state=3` / `reasons=none`. A job stuck at `printing` with an indented
"The printer is not responding" line is the dead-printer signature; any
`reasons` other than `none` is a latch. Both are in `TRAPS.md`.

**`lpstat -W completed -o` lists NEWEST FIRST.** `tail` reads the *oldest* end of
the history, so a job that completed seconds ago looks missing — the same mistake
as the truncated 1-15 job list in `TRAPS.md`, in the other direction. Use `head`,
or grep for the job id rather than eyeballing a window.

**What this proves and what it does not.** A `completed` job on a driverless IPP
queue means the printer accepted and acknowledged it — a genuine liveness signal
about the *printer*, unlike "the queue is accepting", which is only a claim about
CUPS. It is still not proof a label came out, and nothing readable from the Mini
is. Walk over, or ask.

Verified end to end 2026-09-08 on the bypass-fed replacement unit: job
`QL810W-103`, the stock item label for the CAN terminators (part 1179) — idle
beforehand, gone from the queue in ~10 s, idle with `reasons=none` after.

---

## Do not print unless Scott asks

**Standing instruction, 2026-08-26.** Create the part, file the stock, render the
label if it is worth looking at — then stop. Printing happens when Scott calls
for it.

The session that produced this rule printed fourteen labels as parts were
entered, and Scott was applying each one to its bag as it came off the printer.
**Four had to be peeled off and replaced.** Three because reading the actual
Amazon listings *afterwards* showed the bearings were double-sealed — `608RS` →
`608-2RS`, `6803RS` → `6803-2RS`, `R6RS` → `R6-2RS`, the last also 9/32 wide and
not the 7/32 taken from an open-bearing table — and one because a bin was
renamed an hour after it was created.

Nothing about those labels was wrong when printed. They were printed *before the
facts settled*, which is a different failure and not one a render check can
catch: the tape was correct and the record behind it was not.

**Entering a part and labelling it are two separate acts.** `print_part_label.py`
already defaults to render-only for the visual check this file demands. Treat
that default as the END of the job rather than a step on the way to `--print`,
and batch the labelling when it is called for — by which time names, counts and
locations have stopped moving.

---

## A location label carries its PARENT, so a move makes the tape wrong

**Paid for 2026-09-19.** B-02 moved from `WS2-S3` to `LW3-S1`. I told Scott no
reprint was needed, reasoning that the `B-nn` id is global and travels with the
physical bin — so the move is a re-parent, not a rename. Scott: *"actually need
a new label for BO2. as well."*

He was right. Template 9 prints **two** lines:

    B-02        <- the global id. Travels. Unchanged by a move.
    WS2-S3      <- the PARENT SHELF. This is precisely what a move changes.

The premise was true and the conclusion did not follow from it. "The id is
stable" says nothing about the rest of the tape.

**The rule for any location move:**

1. Re-parent in InvenTree (`obj.parent = new; obj.save()`; see `TRAPS.md`).
2. **Reprint the location label.**
3. **Peel the old tape before sticking the new one.**

Step 3 is not tidiness. A bin carrying a confidently printed *wrong* address is
worse than a bare bin: the bare one gets picked up by the next batch print, the
wrong one reads as done forever and will never be offered again. Same reasoning
as `mark_labeled.py`'s rule about handwritten labels.

Set `metadata.labeled = False` on the moved location until the new tape is
physically on it, and keep the superseded CUPS job id in `label_printed` — once
two same-day labels are cut off the roll, the job id is the only thing that
tells them apart.

**This applies to every bin in the WS → laser-wall migration**, not just B-02.

## B-04 — created 2026-09-19, label NOT printed

`SLN/Laser Area/LW3/LW3-S1/B-04`, ETHERNET TERMINATION. Split off B-03 the same
day because the keystone bag and the plug jar would not fit in it.

It has `metadata.labeled: False` and **no `label_printed` key at all** — the
three-state convention, where an absent key means the tape has never been sent
to the printer. **PRINTED 2026-09-19, job `QL810W-114`**, template 9, on Scott's explicit
request ("b04 label only"). Rendered, pulled, and looked at first — it reads
`B-04` / `LW3-S1` with the QR, which is correct.

Its line 2 will read `LW3-S1`, which is the parent-on-the-tape trap recorded
above: B-04 was born on that shelf, so the tape is correct as long as the bin
stays there.
