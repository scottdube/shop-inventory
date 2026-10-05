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
  - 391 GBJ TCMT inserts: the title never states the box count. Scott
    2026-10-05: "not sure, have to look into it". Stays open until he reads
    the box.
  - 1268 AMTAST roughness tester: it had no history table because it was
    still in transit. Scott 2026-10-05: it arrived 10-04 (delivered to Dover).
    PO-0188 was received through receive_po.py -> stock item 1019, a REAL
    receive, not [ESTIMATE].
  - INACTIVE 190, 317, 340, 354: merge receipts; their survivor carries the
    history.
  - Consumables: flap discs, abrasive rolls, sandpaper, Scotch-Brite, rust wheel,
    buffing and wire wheels, Tap Magic, Anchorlube, Vactra.
  - Misfiled non-tooling: crimpers, potentiometers, fuse box, polyimide tape,
    iron holder.
  - Hardware: rivet nuts, knurled nuts.
  Kept as tooling or equipment: saw blades, the sandblast cabinet, the shop vise,
  the benchstone.
- **Precise Bits DONE**: orders 20261474 and 20261480 (both 2026-07-28, from the
  cartsales@ confirmations) -> PO-0212 and PO-0213. 13 pieces [ESTIMATE] across
  parts 528-534, stock items 1007-1013. PreciseBits rounds line totals from an
  unrounded unit price, so qty x unit runs 1 cent over the subtotal. The Heart
  drill sets are assortments: one unit each.
- **Shars DONE**: five orders in email.
  - 200031028, 200061342 and 200064959 -> PO-0214..0216. All bookkeeping only:
    every part already held a counted quantity, e.g. 8 ER20 holders = two
    4-packs. Pull studs: 7 bought, 1 loose; the rest are presumably in holders.
    Shars' Price column is the LINE total, not the unit.
  - 100215875 (2022-12-15, D1-4 adapter plate, part 545): email has only the
    shipping notice, so the order's other contents are unknown. Booked with
    scripts/nopo_receive.py, no PO (stock item 1014).
  - 200063527, the 18x24 granite plate: on freight hold and never paid ($300
    R+L quote). Part 118 is inactive with no notes and no survivor - read as
    not bought; left alone.
- **MSC / McMaster tooling**: already stocked; nothing to do.
- **Email sweep for other vendors** (a from:(vendor list) search; the broad
  tooling-term search drowned in golf promos):
  - **Saunders Machine Works DONE**: Company #37 created (scripts/add_tooling_vendors_1004.py).
    Scott's request to search email for other vendors is the approval
    vendor_triage.py waits for.
    - #12858 -> PO-0217: 5 pairs of Gen2 aluminum soft jaws (part 1329).
    - #12891 -> PO-0218: Gen2 Modular Vise System 1/2in (part 1330) and 2
      reversible jaw inserts (part 1331).
    - Stock items 1015-1017, [ESTIMATE].
    - **#12840 (Gen3 jaws) deliberately not a PO**: returned and refunded
      2024-08-08. Invoices D1236 (the same order as #12858) and D1257 (exchange
      shipping) are not separate goods.
    - Saunders prints no SKU, so the supplier SKUs are descriptive handles
      (MODVISE-G2-...), not vendor part numbers.
    - Soft jaws are counted in PAIRS: that is how they are sold and used.
    - Part 560, the Saunders tooling plate, came in the Tormach bundle and was
      already stocked.
  - **Zoro DONE**: Company #38.
    - SO29365201 -> PO-0219: webbed slotted angle plate (part 1332, stock item
      1018), booked at the $22.06 actually paid after the promo.
    - SO25543893, the 19in louvered panel ($73.81, 2022-02-20): storage, not
      tooling. Left out.
  - **LittleMachineShop DONE** (2026-10-05): order 22010514 (2022-01-05).
    Neither email listed the items (an unfilled `%OrderDetails%` template).
    Scott guessed "a drill set", then sent a screenshot of the order page from
    his account, and it was NOT a drill set: adjustable parallel set,
    BoltSize-It checker, Starrett automatic center punch, 12in 4R combination
    square. Company #39 -> PO-0220, stock items 1020-1023, [ESTIMATE].
    Descriptive SKUs (LMS-...): the page shows no LMS part numbers.
    **Lesson: when a vendor email is a template shell, the account order page
    has the lines. Ask Scott for it before guessing.**
  - **Stafford Special Tools DONE** (2026-10-05): invoice 71490 (2025-09-23,
    S.O. 50731), from a PDF Scott handed over with *"here's one you won't find
    easily"*. A Gmail search for stafford/knurl/71490 returned only noise.
    Company #40 -> PO-0221, with the PDF ATTACHED to the PO
    (scripts/attach_po_pdf.py). Contents: SKP12D straddle knurl holder ($375)
    plus 8 KP knurls in 25 and 35 TPI (2 straight, 1 RH, 1 LH of each). Parts
    1337-1343, [ESTIMATE].
    **Blind spot this exposes**: the email sweep only finds vendors that EMAIL
    a confirmation. Vendors who send only a PDF invoice (rep-handled,
    credit-card-terms shops) leave nothing a sender search can match, so they
    surface only when Scott remembers them. The PDF filename names the parent
    company (Form Roll Die Corp), not the letterhead.
  - **Kennametal**: only a tech-support thread about CNMG432 inserts that came
    with a used mill. Not a purchase.
  - **eBay DONE** (2026-10-05; 31 orders booked in all, PO-0222..PO-0251): a sweep of every eBay order mail in Gmail found
    162 purchase rows. 36 were tooling and 17 borderline. The sweep's searches:
    `from:ebay@ebay.com` (stopped at 2023-11-18, drowned in saved-search alerts,
    so it was re-run from 2023-11-18 back with alerts filtered out, to 2016),
    order/won/shipped/paid/refund subjects before 2016, seller messages,
    "Order number", refund/return/cancel, "Order confirmed", "eBay purchase" and
    "eBay order". All of them ran to the end. The rows sit in the session
    scratchpad, not the repo; data/tooling/ebay.json holds what was booked.
    - **25 orders booked** -> PO-0222..PO-0246, parts 1344-1368, 61 pieces
      [ESTIMATE] in Unfiled. scripts/ebay_dupcheck_1005.py found no existing
      part for any of them. The near-misses are different items: the Amazon
      Starrett 93-series tap wrenches, the Tormach lathe test piece kit, the
      Amazon round 5C collet set, and the passive probe (which is not the ETS).
      SKU = eBay item number, the existing eBay supplier-part convention.
      Pieces: the toe clamps (4), the Federal indicators (a lot of 4) and the
      Hardinge 5C collets (a lot of 31) count pieces. Sets of gages and blocks
      count as one.
    - **Refunded, not booked**: the 1in Accusize roughing end mill (canceled)
      and the ALSGS power feed (refunded).
    - **Held for Scott, resolved 2026-10-05**:
      - The Clough42 ELS kit: *"still have the els kit"*. Booked -> PO-0247, Unfiled.
      - The Starrett 257D surface gage: *"257d is here in sln at the MB"*, i.e.
        the Metrology Bench. Booked -> PO-0248, stock row on SLN/Metrology Bench.
        The "Christopher" greeting and card x-7953 do not change whose it is.
      - The DROs: *"2 separate dro set ups one for the mill drill I still have
        and the other for an enco lathe I sold"*, then *"3 axis on the mill,
        power feed is on it too scale guess is right"*. The Jet mill/drill
        carries the 3-axis head, the 550 + 200 mm scales and the X power feed:
        PO-0249..0251, parts 1371-1374, all on the Jet Mill/Drill Stand (the
        precedent set by the head mover). The 2-axis head and the 900 + 200 mm
        scales went with the Enco and are not booked. Variation SKUs: see TRAPS.
      - Non-machine-tool items, left out by default: the welding helmet and
        jacket, plasma consumables, the Milwaukee ratchet and batteries, the
        Ryobi battery, the Bosch laser measure, and aluminum/steel bar stock.
    - **Already in InvenTree**: the 3000W induction heater (the shrink-fit
      project) and the 41-piece terminal removal set (already carries its eBay
      SKU).
    - **CORRECTION to the earlier note here**: the 6in Super Spacer rotary table
      is NOT an eBay purchase. Scott SOLD one on eBay, "NEVER USED", listed
      2025-07-14 and paid 2025-07-21; the buyer collected it. InvenTree
      showed one at SLN/Machine Shop as [CONFIRMED OWNED], from Scott's
      2026-08-19 confirmation. Asked; Scott 2026-10-05: *"sold it"*. The row
      was zeroed and kept (scripts/super_spacer_sold_1005.py). **Lesson: a
      'confirmed owned' from memory can predate a sale; the seller-side mail
      (You made the sale / You got paid) is a source too.**
  - **tormach.com account DONE** (2026-10-05): My Orders lists exactly 8 orders,
    every one already known from email. Nothing was missing.
    - 3000048323, 3000059655 and 3000059656 are the DIRECTPAY machine payments
      (quotes QT123040 and QT125789), never part costs.
    - 3000048956 and 3000053997 = PO-0026 and PO-0025.
    - 3000069522 (microARC 4 4th axis, subplate, driver kit), 3000069852 (three
      thread mills) and 3000070065 (turret coolant nozzles, 3 fixture plates)
      were stocked by the 2026-09 cost mining but had no PO. They now have
      bookkeeping-only POs, PO-0252..0254, with no stock added.
    - The 2 Tormach T-shirts on 3000070065 were left off as apparel; the PO notes
      say so.

## Still open (checkpoint 2026-10-05)

- The GBJ TCMT inserts (Amazon B07B7GF4F2): Scott has to read the box count.
- The non-machine-tool eBay buys are left out by default (welding, plasma,
  cordless batteries, laser measure, bar stock). Not asked.
