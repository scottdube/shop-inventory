# McMaster-Carr import — scope and rules

**Built and run 2026-08-21.** Scoped, then executed the same day. McMaster-Carr was missed in the original
supplier import; most of the hardware in cabinets **A2 and B2 came from them**,
so this is the single biggest quality win available to the fastener catalogue.

Run by `scripts/mcmaster_import.py`, which is idempotent on the invoice
number and safe to re-run. Result: **92 parts, 92 supplier parts with per-unit
prices, 18 purchase orders, 92 [ESTIMATE] stock items**.

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

## Rule 1 — the shop/dealership filter is SHIPPING ADDRESS + who placed it

Some McMaster orders in this mailbox belong to the family car dealership, not
the shop, and their contents are plausible enough to slip through: the one
excluded order is a drum dolly, oil sorbent pads and gallon jugs — real
workshop-shaped items that went to a service bay.

**Do not filter on the billing address** — it says who paid, not where the
parts went. **And do not filter on the card brand either.** That rule was
written from two receipts and was falsified by the third: a 2025 order shipped
to the shop was paid on a Visa, not the Mastercard. The shop uses both cards.

Two things ARE reliable, and both appear in every receipt:

1. **Shipping address** — the shop's home address vs the dealership's.
2. **A literal sentence naming who placed it** — `<person> placed this order`
   for the shop, `Parts Department placed this order` for the dealership.

Use the shipping address as the primary filter and the placed-by line to
confirm. The card *brand* does not separate them at all — **three different
cards appear across the shop's own orders**, two Visa and two Mastercard.

**And the cardholder name has three spellings for one person.** Scott's full
name is Christopher Scott Dube, so receipts show the personal name as any of
three variants across the years. An importer matching one spelling would
silently drop orders — which is the worst failure mode here, because a missing
order looks exactly like an order that never happened. Match on the *business*
name to EXCLUDE, rather than on a personal name to include.

The concrete address and name values are **deliberately not in this repo** —
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

## First test case: the Cannon Gasket bag

A sealed bag of dark rings turned up on the staging table 2026-08-21, branded
**Cannon Gasket, Inc.** with their own part number `CVTN-812355062M`. Scott
believes it came in on a McMaster order, so it was deliberately **not**
catalogued — the import should supply both the identity and the count.

That makes it a **falsifiable check on this whole scope**:

- If `CVTN-812355062M` appears in one of the 18 shop receipts, the McMaster
  provenance holds and the pack quantity arrives with it.
- If it appears in **none** of them, it came from somewhere else, and **Cannon
  Gasket needs its own supplier record** — it is not currently in the list, the
  same gap McMaster itself had.

Run this check first. It costs nothing and it tests the assumption the rest of
the import rests on.

**Note on the count.** The bag is unopened, so the invoice line will state the
pack quantity. Under the evidence tiers in README principle 5 that is a
**stated** number, not a tally — strong, since a factory-sealed bag is unlikely
to be short, but still **no stocktake date** until someone counts it. Let the
never-counted report keep surfacing it.


## What the run actually produced

| | |
|---|---|
| Parts created | 92 — every one a distinct McMaster number, no repeats in five years |
| Supplier parts | 92, `pack_quantity` 1 throughout, linked to their product page |
| Purchase orders | 18, all Complete, each keyed on its invoice |
| Stock items | 92, all `[ESTIMATE]`, **none** with a stocktake date |
| Units recorded | 4,072 — as PURCHASED, not counted |

Category routing came out Hardware 55, Mechanical 20, Materials 8, Tooling 5,
Pneumatic 4, with **nothing unrouted**.

Stock location: 31 metric fastener lines to **B1**, 17 imperial to **B2**, and
44 left with **no location** — the tooling, raw stock and bearings that do not
belong in either cabinet, plus threadless items like dowel pins and steel
balls. Cabinet level only; the drawer is unknown until the walk.

## Traps hit while building it

**A Complete purchase order is LOCKED.** Creating one with `status=30` and then
calling `save()` to attach notes raises *"This order is locked and cannot be
modified"*, and lines cannot be added either. Create the order **Placed**, add
every line, and only then move it to Complete with queryset `.update()` —
never `save()`, which tries to consume allocations that deliberately do not
exist. The first run died on this after creating one empty locked PO, which had
to be deleted before re-running.

**The Cannon Gasket bag resolved on the first pass.** `93412A423` — *Viton
Fluoroelastomer Rubber Sealing Washer, 3/8" Screw Size, 0.355" ID, 0.812" OD,
Packs of 10* — bought 2023-01. The bag's own number, `CVTN-812355062M`, encodes
**812** OD / **355** ID / **062** thick. Cannon Gasket is McMaster's
manufacturer for that washer and it shipped in the maker's packaging. The
falsifiable check written into this file before the run answered itself.

## Links are derived, not stored — but the CONTENT behind them is the fragile part

Every McMaster part now carries `https://www.mcmaster.com/<IPN>/`, written onto
both `Part.link` and the `SupplierPart`. 92 of 92, no network calls: the URL is
a pure function of the catalogue number, so there was nothing to scrape and
nothing to verify.

Scott raised the obvious objection — **durability**. It is the right question
and it splits into two very different risks:

**The URL scheme changing is a non-event.** These links are *computed*, not
transcribed. If McMaster reorganises tomorrow, one script regenerates all 92
from the IPNs we already hold. That is the whole reason to derive a link rather
than paste one: a hand-pasted URL rots irreversibly, because nobody remembers
how to rebuild it. **Never hand-edit these** — a hand-edited link is
indistinguishable from a derived one and quietly breaks that guarantee.

**The page disappearing is the real risk.** When McMaster discontinues a part,
the specs go with the page, and no amount of link maintenance recovers them.

So the failure mode of a dead link here is "the click does nothing" — not "the
data is gone." The IPN and the full McMaster spec text already live in the
description locally. Anything beyond that (dimensioned drawings, STEP models,
material certs) exists **only** on their server, and that is where local
capture is worth paying for.

**Scope any CAD pull to parts that need it.** A STEP model earns its storage
when the part goes into an assembly model; for a washer nobody will ever model,
it is bytes. The catalogue number plus the spec line is sufficient for
re-ordering, which is what 90% of these records are for.

McMaster fingerprints clients hard — CAD downloads need a logged-in browser
session, not curl. See the browser-beats-curl rule.

### The CAD link is NOT derivable — the whole product page is behind a login

Tested 2026-08-21 in a real browser rather than argued. `mcmaster.com/93412A423/`
resolves, renders the site shell, and then says **"Log in to view Product
Detail"** with a login modal. Not a bot challenge — a plain authentication
wall, served to a normal logged-out Chrome.

That settles the CAD question without ever clicking a download button. If the
*product page itself* requires a session, everything downstream of it is
session-bound by construction. There is no public, derivable URL of the form
`.../<part>/cad.step`, and searching for one would have been effort spent
proving a negative.

Consequences for how these 92 links should be understood:

- **The link is still correct and still worth storing.** For Scott, logged in,
  it lands on the exact part. Derivation cost nothing and repairs in one line.
- **The link is worthless to anyone without a McMaster account** — including any
  unattended job. Do not build automation that assumes it can read these pages.
- **Local capture matters more than first thought.** The spec text in each
  part's description is not a convenience copy, it is the *only* copy anyone can
  read without credentials.

**The sanctioned path is McMaster's own API**, advertised in their site footer
(`mcmaster.com` → API). It requires an approved account and a client
certificate, granted to established customers. For a shop already ordering
regularly, asking a rep for API access is a far better route to CAD and specs
than any amount of browser driving — and it is the only version of this that
would survive being run unattended.

**Not attempted: logging in on Scott's behalf.** Credentials are his to enter.
