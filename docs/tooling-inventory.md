# Tooling inventory — every machine tool ever bought (opened 2026-10-04)

Scott, 2026-10-04: *"inventory all of the machine tools I've bought starting with
tooling — tormach, lake shore carbide, amazon, haas, and others; search email for
indications of others."*

## Rulings

- **Stock basis = purchased quantity, as an estimate.** Scott, 2026-10-04:
  *"put estimated counts from what was purchased, it will have to be inventoried
  as stuff has been damaged or destroyed and disposed of over time."*
  So every historical receive here opens its stock note with `[ESTIMATE]`
  (prefix flag, see TRAPS), names the order it came from, and leaves
  `stocktake_date` null. It is evidence tier "purchase document" — an order
  proves arrival, not survival. A physical walk is expected to correct these
  down; it is the follow-up, not optional.
- Rejected: PO + catalogue only with stock left at 0 (offered; Scott chose
  estimates because a 0 answers "do I own one?" wrongly for nearly everything).
- Location for anything without a known home: `SLN/Machine Shop/Unfiled - Machine
  Shop` (the 08-23 Tormach/MSC precedent).

## Baseline (scripts/tooling_baseline_1004.py, 2026-10-04 evening)

| Vendor | POs | Supplier parts | State |
|---|---|---|---|
| Tormach | 2 | 77 | mostly stocked from the 08-23 receives |
| Lakeshore Carbide | 0 | 19 | all stock 0, no PO |
| Haas Tooling | 2 | 14 | only 09-29 and 10-03 orders have POs |
| Amazon (tooling cats) | — | ~100 | almost all stock 0 |
| Shars | 0 | 7 | |
| Precise Bits | 0 | 7 | all stock 0 |
| MSC | 1 | 3 | |
| McMaster (tooling) | — | 5 | |

## Sources per vendor

- **Lakeshore** — marketing mail only comes from `carl@`; order history via the
  logged-in site in Chrome.
- **Haas Tooling** — haastooling.com account order history (Chrome) + email.
- **Tormach** — 7 itemised `orders@tormach.com` confirmations; 3 are DIRECTPAY
  machine payments that must never become part costs (TRAPS).

## Progress log
