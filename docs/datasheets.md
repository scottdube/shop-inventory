# Datasheets

## Scope: it is ~33 parts, not 1,047

Triaged 2026-08-21. The instinct is "fetch datasheets for the catalogue"; the
catalogue mostly cannot use one.

| | |
|---|---|
| Catalogue total | 1,047 |
| In `Electronics/*` | 217 |
| — of those, already carry an attachment | 17 |
| — **capacitors, resistors, LEDs** | **128** |
| Kits and assortments (no datasheet exists at any price) | 135 |
| **Real candidates: an identifiable MPN, no attachment** | **33** |

The 128 passives are the point. A generic ceramic capacitor out of a 24-value
kit has no manufacturer and therefore no datasheet — and its useful facts
(value, voltage, body size, lead pitch) are already in the record. Fetching
would add nothing and would report as 128 failures.

A datasheet answers exactly three questions — **pinout, absolute maximums,
package**. Those are asked about ICs, regulators, sensors and transistors. They
are not asked about a resistor.

## Measured hit rate: 5 of 8 on first guess

Probed 2026-08-21 with headers only, nothing downloaded. Manufacturer-direct
URLs, guessed from the part number:

| Part | Source | Result |
|---|---|---|
| NE555 | TI | **PDF** |
| LM358 | TI | **PDF** |
| TCRT5000 | Vishay | **PDF** |
| BME280 | Bosch Sensortec | **PDF** |
| ATtiny85 | Microchip | **PDF** |
| L7805CV | ST | host unreachable |
| LD1117V33 | ST | host unreachable |
| DB107S | Diodes Inc | 403 |

**The two ST misses are not URL failures.** `st.com` refuses in 0.04 s — an
instant refusal, not a timeout, so it is a network-level block from this host
rather than a wrong guess. Another vantage point (the Mini, or a browser) would
likely succeed. Diodes Inc returns 403, the familiar fingerprinting signature:
browser beats curl.

So the realistic rate is **60–85%**, against the **18%** the product-image sweep
managed. That difference is structural and worth stating: images were sourced
from **retail listings**, and Amazon bot-blocks everything. Datasheets come from
**manufacturers**, who publish them deliberately and want them found. Same
shape of task, opposite incentives.

## Design that follows from the measurement

- **Manufacturer-direct, per-vendor URL patterns.** No API key, no scraping, no
  account. TI, Vishay, Bosch and Microchip all served clean PDFs unauthenticated.
- **Skip the 128 passives outright.** Not "try and fail" — never queue them.
- **House-numbered generics are the real weak spot**, not the big vendors. For
  `MB10S`, `DB107S`, `S8050` there is no single canonical datasheet, because
  several makers produce the part to the same numbering. Take one and record
  *which manufacturer's* sheet it is; do not imply it is authoritative for the
  part in the drawer.
- `attach_datasheet.py` already rejects anything whose magic bytes are not
  `%PDF`, which is what stops a vendor's HTML error page being filed as a
  datasheet. That guard is why a 403 is harmless rather than corrupting.

## The McMaster half is separate

Hardware specs and CAD would come from the McMaster Product Information API
(`/v1/datasheets/*`, `/v1/cad/*`) if access is granted — see
`docs/mcmaster-import.md`. Unrelated sources, unrelated failure modes; do not
build one pipeline for both.

## Ki-nTree — evaluated 2026-08-21, declined, and what was taken from it

[Ki-nTree](https://github.com/sparkmicro/Ki-nTree) automates part creation for
KiCad + InvenTree from distributor APIs (Digi-Key, Mouser, LCSC, Element14,
TME), including datasheet download and upload. It is the obvious thing to reach
for here. It is the wrong fit, and the reason is one number.

**Ki-nTree's supported distributors cover 11 of this catalogue's 670
supplier-linked parts — about 1.6%.** Digi-Key 2, LCSC 7, Mouser 2. This
catalogue came from Amazon, eBay, McMaster, Tormach and physical drawer walks.
Ki-nTree assumes a catalogue sourced *from* distributors, and it is a
**part-creation** tool driven by a part number — not an enrichment tool for
1,046 records that already exist.

Three further blockers, any one of which would matter on its own:

- **GUI-only** (Flet). No headless mode. It cannot be driven by `itq` or by the
  overnight job, which is the entire operating model here.
- **GPL-3.0** against this repo's MIT scripts. The ideas are free; the code is
  not compatible.
- **Version risk.** It targets InvenTree 0.11 / 0.12.6+; this instance is
  **1.5.0, API 530**. A "newest InvenTree not supported" issue was closed in
  March 2026, but 1.5 postdates it. Corroborating churn: `PartParameter` does
  not exist under that name in 1.5 — model introspection finds zero matches.

### What was worth stealing

1. **Mouser's Search API is key-only — no OAuth.** This corrects an earlier
   assumption here that distributor datasheet APIs meant heavy registration.
   Given an MPN it returns a datasheet URL, parameters and pricing. Free key
   from mouser.com/api-hub. This is the real unblock for the parts that defeat
   URL-guessing, and it is now wired into `scripts/datasheets.py`.
2. **Element14 is also key-only** (covers Farnell and Newark) if a second source
   is ever wanted.
3. **`supplier_parameters.yaml`** — mapping supplier attributes into structured
   InvenTree *parameters*. This catalogue has 137 manufacturer parts and
   essentially no parameters: everything is prose in `description` and `notes`,
   which cannot be filtered or compared. That is a real gap, recorded here
   rather than acted on.

### Tested and rejected: LCSC / EasyEDA as a datasheet source

Worth writing down because it looks promising and is not. LCSC would be the
ideal source for the house-numbered generics (`MB10S`, `DB107S`, `S8050`,
`A1015`) that have no canonical manufacturer sheet.

- `wmsc.lcsc.com` search and product-detail endpoints return **HTTP 200 with a
  404 body** (`"The static resource is unavailable"`) — their bot guard.
- The **EasyEDA API works unauthenticated** —
  `easyeda.com/api/products/<LCSC>/components` returns 200 with real data: title,
  manufacturer part number, price, stock, and a product **image** URL. Useful.
- But it carries **no datasheet field**. Searched the entire response body for
  any `.pdf` URL: zero.

So EasyEDA is a viable *image* and MPN source and a dead end for datasheets.

## `scripts/datasheets.py`

    itq run scripts/datasheets.py --list
    itq run scripts/datasheets.py --fetch [--commit]
    itq run scripts/datasheets.py --from-dir /tmp/ds --commit

Three sources in order: exact URLs for known family sheets, manufacturer URL
patterns (TI, Vishay — the ones measured to work), then the Mouser API if a key
is present. `--from-dir` attaches PDFs already pulled by hand or by a driven
browser, which is how st.com sheets get in at all.

**The API key never enters this repo.** It is read from
`~/.config/shop-inventory/keys.json`, outside the tree — a `.gitignore` entry is
one `git add -f` from failing, and this repo is public.

**The part worth keeping is the verification.** `attach_datasheet.py` checks
magic bytes, which catches an HTML error page saved as PDF but not a *real PDF
about the wrong part*. This tool also extracts the PDF text and requires the
part number to appear in it. Tested against the TI NE555 sheet: accepts NE555,
rejects LM358, MB10S and VL53L1X, rejects HTML. A datasheet filed against the
wrong part is worse than none, because it reads as authoritative.

Candidates are 23 — passives and kits are excluded by category, not attempted
and failed.
