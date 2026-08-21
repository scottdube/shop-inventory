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
- **Look at the rendered PNG before printing.** Every failure above passed an
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

As of 2026-08-21 — **84 of 474 affixed**, with **240 more printed on Avery
sheets and waiting to be stuck on**. Those two numbers are different things
and only the first is what `labeled` records; see the three-state trap in
`TRAPS.md`. Installing is a slow manual job done a bit at a time, so the gap
between them is normal and is NOT a reason to print anything.

| Location | Done | Total | |
|---|---:|---:|---|
| Laser Area (L1, L2, LW1–3) | 5 | 5 | complete |
| L1, L2 drawers | 14 | 14 | complete |
| B3 | 44 | 44 | complete |
| Assembly & Test (AT-D1..D3) | 3 | 3 | complete |
| A3 | 40 | 64 | rows 4–8 affixed; rows 1–3 printed, not yet stuck on |
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
