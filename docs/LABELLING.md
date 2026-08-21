# Labelling

How labels get printed in this shop, why the setup looks the way it does, and
what is still undone. Written 2026-08-20, after an evening that cost far more
than it should have because the obvious approach does not work on this printer.

Related: `docs/TRAPS.md` (the individual gotchas), `docs/TECHNIQUES.md`
(bagging), `plugins/cups_label/` (the plugin), `scripts/mark_labeled.py`.

---

## The printer

**Brother QL-810W, 192.168.30.252 (static), at SLN.** InvenTree runs on the Mac
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
lpadmin -p QL810W -E -v ipp://192.168.30.252/ipp/print -m everywhere
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

## Coverage

Tracked as `metadata.labeled` on each `StockLocation`, beside `metadata.size`,
so a batch print can skip what is done. Managed by `scripts/mark_labeled.py`
(`--report`, `--cabinet X`, `--rows X 4 8`, or bare names).

**"Labelled" means carrying a PRINTED QR label.** Several cabinets have
handwritten paper labels from before this system existed — `1/4-28 NUT`,
`TOGGLE SWITCHES`, `ARDUINOS`. Those must stay flagged false: they carry no QR,
nothing links them to InvenTree, and they are exactly the drawers still to do.

As of 2026-08-20 — **106 of 474**:

| Location | Done | Total | |
|---|---:|---:|---|
| Laser Area (L1, L2, LW1–3) | 5 | 5 | complete |
| L1, L2 drawers | 14 | 14 | complete |
| B3 | 44 | 44 | complete |
| Assembly & Test (AT-D1..D3) | 3 | 3 | complete |
| A3 | 40 | 64 | rows 4–8 only; rows 1–3 are empty and unlabelled |
| A1, A2 | 0 | 128 | |
| B1, B2 | 0 | 88 | |
| Red Bins | 0 | 28 | |
| everything else | 0 | ~100 | |

Only mark what someone has **seen**. A wrongly flagged location is worse than an
unflagged one: the unflagged drawer gets a spare label printed, the wrongly
flagged one stays bare forever because nothing will offer to print it again.

---

## Open items

- **LW1–LW3 shelves** (`LW1-S1`, `LW1-S2`, … six total) — the cabinets are
  labelled; unknown whether the shelves inside are.
- **A stray CUPS queue** `_192_168_30_252` sits on the Mini beside `QL810W`.
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
