# PO receiving from the phone — design

Date: 2026-11-06. Brainstormed with Scott; approved in chat the same day.

## Problem

Receiving a purchase order needs a laptop and a Claude session, so it waits.
On 2026-11-06 there were 18 PLACED orders, most of them delivered. Returns
have the same shape on the way out: the refund watcher reads the Amazon mail
every morning but was forbidden (2026-09-19) to change a PO's status or touch
stock, so a refunded order sits PLACED until someone opens a session.

Scott's words on what the fix must do: *prefill what it knows, make the
destination easy to choose or put it in a holding area, let me use the app or
my voice, and don't make me look up the PO number.* And on returns: once Amazon
has the return, the system has already seen the email, so it should not need to
be told again.

## Decisions

| Question | Decision | Why |
|---|---|---|
| Door | A BinScan page with a home-screen icon, camera-first, text field for typing or dictation | iMessage was considered and deferred: a text thread has to ask and parse ambiguity in prose; a page shows the choices as buttons. Same engine, so iMessage can be added later. |
| PO lookup | The system finds the PO from a photo of the label, slip or part, or from a few words | Scott will not know the number. Ties are shown as cards, never guessed. |
| Destination | Prefilled from the record; Receiving is always one tap | The holding area is the documented practice ("receive to Receiving, not to a drawer"). |
| Returns | Automatic when the evidence is clean; a pending card otherwise | No reason to involve Scott in every return. The one irreversible step, deleting a stock row, is covered by copying its notes to the PO first. |
| Engine | One module shared by the CLI and the app | Two code paths is how each half of a receive got done wrong once. |

## 1. One engine, two doors

`scripts/receive_po.py` keeps its command line and becomes a thin wrapper over
a new module `plugins/receiving/engine.py` (runs inside InvenTree; see the
amendment below). The module exposes:

- `plan(po_ref, lines)` → what would be booked: per line the pieces (quantity ×
  `pack_quantity_native`), unit price, the stock row it would MERGE into or
  "new row", destination, and every warning the CLI prints today (pack says 1
  while the SKU says pack, no supplier part, line already received).
- `commit(plan_id | plan)` → does it: sets `line.received`, merges or creates
  the row, writes the row and PO notes, completes the order when no line is
  outstanding, returns the stock pks and the undo token.
- `undo(token)` → reverses a commit within the window (see §4).

`scripts/returns.py` has the same shape for the way out (§5).

BinScan calls both over HTTP: the engine is hosted as the InvenTree plugin
`receiving` (`plugins/receiving/`, views under `/plugin/receiving/…`, token
auth). **Amended 2026-11-06** — the subprocess design cannot work because
BinScan is a LaunchAgent and TCC refuses launchd children any execution under
`/Volumes/*` (TRAPS.md). The REST receive endpoint is still not used; the plugin
views run the engine's own `plan`/`commit`.

## 2. The receive page

`GET /receive` in BinScan, added to the iPhone home screen as a web clip so it
opens full-screen with no browser chrome. A Siri Shortcut ("receive a box")
opens the same URL.

The page opens with the camera live and a text field under it. Scott either
shoots (shipping label, packing slip, the part, the Amazon bag tag) or types or
dictates a few words, or both. Submit posts to `/api/receive/match`.

Three outcomes:

- **One confident hit** → the receive card (§4) opens on it.
- **Several hits** → one card per candidate: order date, last 7 digits of the
  order number, supplier, each line's name and quantity, the listing's image
  (the part's thumbnail), ship-to site. Scott taps the one in his hand. The
  same 1x7 header socket is on four open POs today; this is the case.
- **No hit** → the full open-PO list for this site, newest first, with the
  same cards, plus a "no PO for this" button that goes to the existing
  by-hand filepart flow (today's `nopo_receive.py` case).

Second tab: Pending (§6).

## 3. The matcher

Same rule as identify mode: **the model transcribes, Python matches.** Claude
(the Anthropic key already on the Mini for BinScan) is asked for text only:
order numbers, tracking numbers, ASINs, SKUs, and the product words it can
read. It is told to write `?` for an unreadable character and never to
complete a number. Everything the model returns is logged with the photo under
`shots/`, like every other BinScan run.

Scoring, per open PO at this site (both sites if the site is unknown):

| evidence | match | weight |
|---|---|---|
| order number | `supplier_reference` exact, or last 7 digits exact | decisive |
| ASIN / SKU | a line's supplier part `SKU` exact | decisive |
| tracking number | PO note contains it (only where the sweep recorded one; not verified that it does today, so this row is a bonus, not a dependency) | decisive |
| words | IDF-weighted token overlap with line part names + supplier descriptions, the scorer `/api/partsearch` already uses | ranked |

"Confident" = one decisive hit, or the top word score is at least twice the
runner-up and above a floor to be set from the fixture set (§7). Anything else
is "several hits". A decisive hit on an order that is already received or
RETURNED is reported as such, not hidden: that is the duplicate-delivery signal.

## 4. The receive card

Lines prefilled at the ordered quantity (in packs, as the PO carries them; the
pieces that will be booked are shown beside it so a pack error is visible
before commit). Each line's quantity is editable. One big button: **All here**.
A line can be set to 0 to leave it outstanding (partial delivery; the order
stays open, as `--part` does today).

Destination per line, prefilled in this order, with the source named on the
card so Scott knows why it chose that:

1. the part's `default_location` (its home);
2. the location of the part's existing stock at this site, if exactly one;
3. a suggestion: the location holding the most parts of the same category at
   this site, labelled as a suggestion;
4. the site's Receiving.

Receiving is always a one-tap chip regardless. Tapping the location opens the
same picker BinScan uses for assign. The site comes from the PO's ship-to,
which the sweep writes into the description and note ("to The Villages FL"
= LRD, "Dover" = SLN); when neither is present the card asks, once.

Confirm calls `commit`, then shows what was booked: per line the pieces, the
price per piece, the row it merged into or created, with `/web/stock/item/<pk>/`
links, and the PO's new status. An **Undo** button stays for 10 minutes and
calls `undo`, which does what `binscan_undo.py` does today (split the merged
quantity back out or delete the new row, reset `line.received`, reopen the
order). Every receive and undo is journalled to `log.jsonl` with the plan it
was given.

No label is printed. Labels stay on request (standing rule).

## 5. Returns, automatic

The `amazon-refund-watch` task keeps its mail reading and loses its
"notes only" rule. Instead of authoring a one-off script per refund it calls:

    itq run scripts/returns.py <event> --order <no> [--amount X] [--date D] [--commit]

with `event` one of `requested`, `dropoff`, `refunded`, read from the mail
subject exactly as the task's table maps them today.

- **requested** / **dropoff**: find the open PO by `supplier_reference`. Note
  the PO with the event, date and reason. If the line was received, set the
  stock row to Quarantined and prepend `[GOING-BACK]` to its note. The watcher
  already keys on that marker's words; the token makes it exact.
- **refunded**, clean: exactly one PO matches the order number, the amount
  equals one line's purchase price × quantity (or the sum of the lines), and
  if the line was received its row carries `[GOING-BACK]`. Then: copy the
  row's notes into the PO note (so nothing is lost when the row goes), remove
  the row, mark the line returned (received set back to 0, note on the line),
  set the PO to RETURNED when no other line is outstanding, write
  `[REFUND-CONFIRMED]` with amount and date. Push one line to Scott's phone
  saying what was done, with the PO link.
- **refunded**, unclean (amount differs, two matching orders, a received line
  with no quarantined row, partial refund on a multi-line order): write the
  evidence to the PO note and create a pending card (§6) with the choices
  laid out. Nothing else changes.

The task's existing watchlist (`refund_watch.py`) still drives which orders to
search, and `from:return@amazon.com newer_than:30d` still catches returns
InvenTree has not heard about. The daytime sweep does not touch returns.

The "going back" button on the receive card is optional and covers the moment
before Amazon has heard from Scott: it runs the `requested` branch by hand.

## 6. Pending

`/api/pending` returns cards from three sources, each with its choices as
buttons that call the matching engine action:

- matches the matcher could not settle and Scott closed without choosing;
- returns the refunded-unclean branch parked, with the specific question
  ("refund $16.99 against a $33.98 line: one of two returned, or both?");
- open POs past `target_date` by more than 3 days with nothing received, as
  "did this arrive?" cards that open the receive card directly.

**Amended 2026-11-06:** the second and third sources are derived from the
database by the plugin's `/pending/` view (a `[NEEDS-DECISION]` token in the
PO note; PLACED orders > 3 days past `target_date` with nothing received), so
nothing is stored twice. Only the first source (an unsettled match) is
BinScan-local, as a `receive-unsettled` row in `log.jsonl`.

## 7. Error handling

- The matcher's model call failing (no key, timeout) degrades to the text
  field and the open-PO list; the page says so.
- `commit` is all-or-nothing per PO: any line failing rolls the transaction
  back and the card shows the error with nothing booked.
- Every write is re-read before being reported (the silent-save trap).
- Receiving is site-scoped; a PO whose ship-to is the other site shows a
  warning chip rather than refusing, because boxes do get carried.
- `returns.py` refuses to remove a row that is not Quarantined with
  `[GOING-BACK]`; that is the one hard guard, and it is what makes the
  automatic branch safe.

## 8. Testing

- **Engine:** round-trip tests on a test PO against the live database, using
  `binscan_reset.py`-style setup and teardown: plan → commit → re-read →
  undo → re-read, for merge, new row, partial, and a pack of 60.
- **Matcher:** a fixture set of real photos Scott shoots during the first
  week (labels, slips, bags), each tagged with its true PO. Scored like
  identify mode was: definite / several / none per photo, and the confidence
  floor is set from this set, not guessed. Synthetic fixtures are not
  accepted on their own (the `"rod"` in `"product"` lesson).
- **Returns:** the three event branches against a test PO, including the
  unclean cases, each asserting the exact note text and PO status.
- `scripts/unbound_names.py` before every BinScan deploy, as now.

## Out of scope

- iMessage or any chat door (deferred, same engine).
- Receiving at SLN while Scott is at LRD.
- Non-Amazon return mail beyond what the watcher parses today.
- Label printing from the receive card.
- Replacing the sweep that creates POs from order mail.
