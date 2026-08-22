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
