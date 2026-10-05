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

- **Lakeshore DONE** (2026-10-04 23:xx): whole site history = 6 orders (2024-05-20
  .. 2024-08-20) -> PO-0204..PO-0209, 23 lines, 32 tools received [ESTIMATE] into
  Unfiled. Every SKU already existed (parts 509-527); none had a stock row. The
  part notes' purchase-history tables matched the site line for line.
- **Haas DONE**: site lists 5 orders. 1000486003 -> PO-0210, 1000491501 -> PO-0211,
  both bookkeeping-only: every line's part already held exactly the purchased
  quantity (holders, pull studs counted 08-23), so no stock added. 1000340763 is the
  $10 Winner's Circle membership - deliberately absent, not inventory.
  Haas prints EXTENDED sale prices under a LIST subtotal; hist_import.py takes
  `lines_total` for that case.
- **Tormach bundle tooling DONE** (scripts/bundle_receive_1004.py): seven parts from
  the two machine packages had a catalogue entry but no stock row - stock items
  924-930 in Unfiled, all [ESTIMATE]: End Mill Kit for Aluminum #1, YG-1 V7 kit,
  drill set, gang-riser shim kit (1 each), CCMT 431 / CCGT 432 / VBMT 221 inserts
  (10 pieces each). **No PO and no purchase price**: both packages were paid as
  DIRECTPAY against quotes QT123040 / QT125789, and TRAPS forbids booking those
  as part costs; the quote line is cited in the note instead. Kits count as one
  unit (an assortment is not a multipack). Way oil, coolant and Sikaflex from the
  same quotes were left out - liquids bought in 2024, consumed, not tooling.
- **Amazon tooling DONE** (scripts/amazon_tooling_1004.py): 76 parts, 117 pieces,
  stock items 931-1006 in Unfiled, all [ESTIMATE]. The quantity comes from each
  part's own "Purchase history (Amazon)" table, read by column header. Paid lines
  count; **$0 lines do not**: they are replacements or free swaps (parts 176, 231,
  257, 366), so the first unit went back.
  **No PO**: an Amazon order mixes tooling with everything else. A PO holding only
  the tooling lines under the full order number would also trip the idempotency
  key and block the real import of that order later. Order numbers are in the
  stock notes instead.
  Packs fixed through .save(): 197 (2), 235 (5), 349 (10), 392 (10), 394 (10). All
  were at the importer's default of 1; the counts come from the seller titles.
  Left out on purpose:
  - 391 GBJ TCMT inserts: the title never states the box count.
  - 1268 AMTAST roughness tester: no purchase-history table.
  - INACTIVE 190, 317, 340, 354: merge receipts; their survivor carries the
    history.
  - Consumables: flap discs, abrasive rolls, sandpaper, Scotch-Brite, rust wheel,
    buffing and wire wheels, Tap Magic, Anchorlube, Vactra.
  - Misfiled non-tooling: crimpers, potentiometers, fuse box, polyimide tape,
    iron holder.
  - Hardware: rivet nuts, knurled nuts.
  Kept as tooling or equipment: saw blades, the sandblast cabinet, the shop vise,
  the benchstone.
