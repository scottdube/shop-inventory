# McMaster-Carr import — scope and rules

Scoped 2026-08-21, not yet built. McMaster-Carr was missed in the original
supplier import; most of the hardware in cabinets **A2 and B2 came from them**,
so this is the single biggest quality win available to the fastener catalogue.

**Nothing here is built yet.** This records what was established while scoping,
so the work does not have to be re-derived.

## Why it is worth doing

A McMaster receipt email carries, per line: **part number, full description,
thread size, length, material, finish, grade, pack quantity and per-pack
price.** Everything this shop keeps leaving blank on fasteners.

Their part numbers are also **canonical** — `91251A542` fixes material, finish,
thread and length, is stable for years, and can be typed back into their site
to get the identical item. That makes them real IPNs, against the ~370 Amazon
ASINs currently in that field which identify a *listing*, not a part.

Contrast Amazon, whose emails truncate the product title even in the body (see
`TRAPS.md`). McMaster is the good case.

## Scope

| | |
|---|---|
| Receipt emails from their invoicing address | **19** |
| Of those, shop orders | **18** |
| Excluded | **1** — a dealership order, see below |
| Range | Jan 2021 – Jul 2025 |
| Approx. line items | 100–150 |

Sender to search: their invoicing address. Each order generates three mails —
Confirmation, Shipped, Receipt — and **only the Receipt carries line items**.
The other two are noise for this purpose.

## Rule 1 — the shop/dealership filter is the PAYMENT METHOD

Some McMaster orders in this mailbox belong to the family car dealership, not
the shop, and their contents are plausible enough to slip through: the one
excluded order is a drum dolly, oil sorbent pads and gallon jugs — real
workshop-shaped items that went to a service bay.

**Do not filter on the billing address.** It says who paid, not where the parts
went. Filter on **card and cardholder**: the shop's orders go on one personal
card, the dealership's on a business card in the business name, and the
shipping address agrees. Every receipt states both.

The concrete card and address values are **deliberately not in this repo** —
they belong in a gitignored config the importer reads at runtime, per the
data-in-code rule in `CONTEXT.md`.

## Rule 2 — CREATE, never reconcile

**Grade is part identity for a fastener** (README principle 19). McMaster
hardware is graded and specified; the cabinet-pack hardware already filed in A2
is unmarked and of unknown grade. A 1/4-20 nyloc from each shares a thread and
nothing else that matters.

So the importer must **never merge a McMaster line into an existing ungraded
part**. Merging silently promotes unmarked hardware to a strength nobody tested
it to — the one error here with a physical consequence. Create new parts and
let a human decide about any duplicates afterwards.

## Rule 3 — packs are not units

McMaster prices per pack: *"Packs of 50, 12.36 Per Pack"*. Principle 2 says
`pack_quantity` is always 1 and price is always per item, so that is **50 units
at $0.2472 each**, with "Packs of 50" recorded in the notes. Getting this wrong
reproduces the pack-vs-unit errors that principle exists to prevent.

## Rule 4 — key on the invoice, not the PO

The PO trap in `TRAPS.md` says `supplier_reference` is the idempotency key for
automated PO creation. **That breaks here:** one order in this set was split
across two shipments and produced two receipts sharing a single PO number.
Key on the **invoice number**, which is unique per receipt.

## Quirks found while scoping

- **Line numbers are not contiguous.** One receipt starts at line 2 — line 1
  was presumably cancelled or backordered. Do not infer a count from the
  highest line number.
- **POs are sometimes named after the project**, e.g. one reads as a Z-axis
  oiler modification rather than a date code. That is free provenance: it ties
  an order to a machine project and should be preserved in the PO notes.
- Their regional sales office changes over the years (three different ones
  appear across this date range). It is cosmetic; ignore it.
