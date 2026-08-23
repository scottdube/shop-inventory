# Traps — the expensive lessons, catalogued

Everything here cost real time. Each entry: symptom → cause → fix.

## macOS

### launchd + external volumes = silent exit 126
**Symptom:** a backup script that "ran" nightly for its entire life and never
produced a byte. `Operation not permitted`, exit 126.
**Cause:** TCC (macOS privacy) denies launchd-spawned processes access to
`/Volumes/*` — including *executing* scripts that live there. Granting Full
Disk Access to a venv symlink does nothing; TCC resolves the real interpreter.
**Fix:** keep scheduled scripts on the internal disk; grant FDA to the fully
resolved interpreter binary; stage outputs internally so network tools never
touch `/Volumes`. **Verify with `launchctl kickstart -k`, never by waiting for
the schedule** — and never trust a missing log.

### mount_smbfs can't use Finder's keychain entry
Finder's saved SMB credential is access-controlled to Finder's auth agent. A
launchd job falls back to anonymous and gets rejected — but looks healthy as
long as a Finder mount happens to be open. Test unattended paths by
**unmounting first**. Fix: auto-mount via Login Items, or extend the keychain
item's ACL to `/sbin/mount_smbfs`.

## InvenTree

### Nothing serves /media/ in a bare-gunicorn deployment
The media URL route is registered **only when DEBUG is true**; production
expects a reverse proxy. The UI looks perfect (static files come from
WhiteNoise) and images 401 — which reads as an auth problem and isn't.
Durable fix: reverse proxy. Interim: a local urls.py patch — which an upgrade
will silently delete; the symptom to watch for is "images vanished after
upgrade."

### PO references are format-locked
`reference` must match the `PO-{ref:04d}` pattern — a raw vendor order number
is rejected. The vendor number goes in `supplier_reference`, and THAT becomes
your idempotency key for automated PO creation.

### Parameters moved in 1.5
`part.models.PartParameter` is gone; parameters are generic
`common.models.Parameter` / `ParameterTemplate` keyed by
`(model_type, model_id)`. Old scripts fail on import.

### MPTT tree corruption from concurrent writers
**Symptom:** `More than one root node with tree_id N. That's invalid, do a
full rebuild.`
**Cause:** Part/Category/Location are django-mptt models; `tree_id` assignment
is read-max-then-write. Two processes creating parts simultaneously (an
interactive session + an hourly cron) both claim the same id.
**Fix:** schedule automation away from interactive hours. Recovery:
`Part.objects.rebuild()` is non-destructive (tree fields derive from parent
pointers). Verify with a deep check — roots per tree_id, then lft/rght
distinct and contiguous over 1..2n.

### SQLite lock contention with the background worker
Bulk ORM scripts fail with `database is locked` because the django-q worker
polls continuously. Unload the worker agent, run the import, reload.

### `.save()` can report success and write nothing
**Symptom:** a script prints "updated", the in-memory object holds the new
value, the database does not. No exception.
**Cause:** InvenTree overrides `save()` on several models with validation and
lock logic, and the override can return without writing. Confirmed on
`BomItem.quantity`; completed `PurchaseOrder` lines behave the same by design.
**Fix:** after any save that matters, **re-read the row by pk and compare**.
Fall back to `Model.objects.filter(pk=...).update(...)`, which bypasses
`save()`. Build the check into the script — the failure is invisible otherwise.

### `Part.name` caps at 100 characters
Not 200. Appending a suffix (`" [merged]"`) to a long imported title and then
truncating cuts off the suffix itself — losing the only visible marker that the
record is retired. Budget for the suffix *before* truncating.

### Completing a build freezes its line items
**Symptom:** a Complete build shows two lines while the part's BOM has seven.
**Cause:** build lines are generated from the BOM at build time. BOM lines
added later never appear, and completion freezes the set.
**Fix:** reopen → `create_build_line_items()` → re-complete. Move the status
with queryset `.update()`, not `save()`, or completion logic will try to consume
allocations. **Consume nothing** if the counts were taken after the build — the
parts are already outside those numbers, and allocating would deduct twice.

### `default_location` rots silently
**Symptom:** a part whose stock sits in RB-06 suggests B3-R7C1 on every receipt.
**Cause:** the field is a suggestion the UI offers, so a wrong value never
errors. Many were set by an import that inferred a location from a drawer
*label* and wrote "INFERRED … verify" in the notes. The verification never
happened. 55 were wrong in one audit.
**Fix:** audit it against where stock actually is. Rules that survived: the
default is where a **spare** goes back to (a unit on a bench or fitted into a
build is in use, not at home); never point it at a staging area or a bare site
root — that blesses the backlog; and where there is no home yet, **leave it
empty**. An empty field asks a question, a wrong one answers it badly.

### Import twins split stock from provenance
Every duplicate pair follows the same shape: the tidy name holds the **stock**,
the verbose vendor title holds the **supplier link, price history and image**.
Neither record alone is right. Merge by moving the supplier part and image onto
the record with stock, then retire the twin in place with a pointer — deleting
it loses the audit trail. Eighteen pairs surfaced in a single day's walk; assume
more.

### A "Complete" PO can still have `received = 0` on every line
PO-0016's five MBR60100PT diodes were counted in hand on 2026-08-19 and written
as two stock rows correctly tagged to PO-0016 — but the **line** counter was
never advanced. So the header said Complete while a line-level sweep said five
outstanding, and the obvious fix (receive it) would have written a *second*
five and reported ten.

**PO status is not the answer to "has this arrived".** Before receiving
anything, ask the stock instead:

```python
StockItem.objects.filter(purchase_order=po)
```

If rows already exist, the goods are on the books and the job is bookkeeping —
set `received` on the line with a queryset `.update()` and create nothing.

### `receive_line_item` refuses unless the order is PLACED
Which is exactly the state a Complete-but-unreceived PO is not in. There is no
API path back; the line has to be written directly. Corollary in the other
direction: **receiving the last outstanding line auto-completes the PO.** Seven
POs went Placed → Complete on 2026-08-23 with no explicit `complete_order()`
call. Do not add one, and do not read the status flip as a bug.

### Receiving a historical PO double-counts against "confirmed owned" rows
Purchase-history imports create placeholder rows — `[CONFIRMED OWNED — NOT
COUNTED]`, qty 1 assumed, no PO link — for things Scott confirmed he owns.
Receiving the original PO on top of one adds a second row for the same physical
object. Either delete the placeholder in the same transaction as the receive,
or do not receive at all. Doing half of it is how a shop ends up with three
BT30 holders on paper and one on the rack.

The delete must be **guarded on the receive having actually happened** — filter
for a PO-backed row on that part and refuse otherwise, or a failed receive
silently deletes the only record that the thing exists.

### A received quantity is a purchase record, not a count
Closing the 2024 Tormach orders received the **ordered** quantity: 2 each of
three end-mill holders whose placeholders had assumed 1 each. Neither figure was
ever verified by eye. The received rows therefore carried no `stocktake_date`.
Receiving moves provenance onto the row; it does not count anything, and a row
that arrives from a purchase record must not be allowed to read like one that
arrived from a person opening a drawer.

**Both halves of that were then tested the same day, and split.** Scott, asked
directly: *"those were all rec as ordered"* — the holders are 2 each, the
purchase record was right and the placeholder's assumed 1 was wrong. But the
same question about pull studs came back *"20 total, 2 diff kinds"* against 36
on paper. **Ordered-and-arrived is a fact about the past; on-hand is a fact
about now, and only a person can close the gap.** Ask; do not promote one to
the other.

### The receive check that misses: a part CONSUMED INTO another part
The double-count guard before receiving was "does a stock row already exist for
this part". For nine Tormach pull studs it did not, so the receive looked safe —
and wrote nine studs into stock that are screwed into nine tool holders on the
rack. Scott's count caught it, nothing in the data would have.

**A pull stud lives inside a tool holder. An insert lives in a face mill. A
battery lives in the tool it came with.** For anything that gets installed into
something else, "we bought N and no row exists" does not imply "there are N on a
shelf". The tell is in the order itself: PO-0025 carried 7 holders and 8 studs,
PO-0026 carried 1 arbor and 1 stud. **Near 1:1 with a host part on the same
order is the signature of a consumable, and it is visible before you receive
anything.**

Zeroed rows keep the price and the PO link — they are the spent history of a
real purchase, not an error. See #292 for the same shape.

### `stocktake()` does not stamp the date when nothing changes
`StockItem.stocktake(count, user)` stamps `stocktake_date` only if the quantity
changes, or a status/location/reference field changes. **A confirming count
changes nothing by definition** — you counted 2, it says 2 — so the stamp is
silently skipped and the row goes on reading *never counted*, which is the exact
opposite of what just happened.

Eleven rows came back `stocktake_date_set=False` from a run that reported no
error. The verify block is the only reason it was caught. Write the stamp
yourself after the call:

```python
StockItem.objects.filter(pk=it.pk).update(
    stocktake_date=TODAY, stocktake_user=user)
```

### A stale explanation on a zero row is worse than no explanation
Part #292 sat at zero with the note *"Empty bin at RB-12 until PO-0028 lands."*
Once PO-0028 landed, that sentence sent a reader to look for an empty bin with
two sensors in it. The rule that a zero needs a reason has a second half:
**when the condition the reason names resolves, the reason has to be rewritten
in the same pass.**

### Counting a row to zero DELETES it
`STOCK_DELETE_DEPLETED_DEFAULT` is **True** on this install, so every row
created by a receive or an import carries `delete_on_deplete=True`, and
`updateQuantity(0)` — which `stocktake(0, ...)` calls — erases the row. "Count
it down to zero" and "destroy the record that it ever existed" are the same
call.

That takes the price, the PO link and the note explaining the zero with it,
which is the whole value of the #292 pattern. Four pull-stud rows went this way
on 2026-08-23 and had to be recreated by hand. Before zeroing anything you want
to keep:

```python
StockItem.objects.filter(pk=pk).update(delete_on_deplete=False)
```

### A verify over an empty queryset passes every check
The run that deleted those rows **reported success**, because the verify block
asked:

```python
sum(float(i.quantity) for i in items) == 0   # sum([]) == 0      -> True
all(i.stocktake_date for i in items)         # all([]) -> True
all(i.notes for i in items)                  # all([]) -> True
```

Every one of those is vacuously true against zero rows. The check could not
tell *correctly zero* from *gone*, which is precisely the distinction it
existed to make. **Assert the row COUNT first**, then the values. Any `all()`
or `sum()` over a queryset that the operation itself could empty needs a
`len(items) == expected` in front of it.

### `stocktake_date` on a stock row is NOT the Stocktake tab on a part
Two different things, and the UI shows the second:

| | |
|---|---|
| `StockItem.stocktake_date` | per-row, "when did a person last count this row" |
| `PartStocktake` | part-level snapshot table, written by the stocktake **report** task |

Setting the row field does not create a `PartStocktake` entry, so a part whose
rows were all counted today can still show a stale part-level date — this
install has 683 `PartStocktake` rows all stamped 2026-08-16, from one report
run. Do not hand-write `PartStocktake` rows to make the tab agree; they are
generated history. Run `part.stocktake.perform_stocktake(part_id=...)` if a
fresh snapshot is actually wanted.

## Labels & QR

### segno.make() silently produces Micro QR — iPhones won't read it
For a short payload like `A1-R1C1`, `segno.make()` picks Micro QR M3 (15×15).
iPhone cameras don't decode Micro QR — no error, just nothing.
**Fix: `segno.make_qr()`** forces a standard symbol (v1, 21×21). Module size
is the whole game on a ½-inch label: ~0.53 mm/module at 6% padding vs a
~0.5 mm floor for phone cameras. A URL payload needs v3+ and drops below
0.4 mm — plain-text addresses only.

### A QR that reads is not a barcode the system knows
The phone reading `A1-R1C1` ≠ InvenTree resolving it. Each location's own name
must be registered via `assign_barcode(barcode_data=...)` or scans return
"barcode not found."

### The built-in label templates fit no sheet you own
All six shipped templates are 50 × 20 mm. That is not an Avery size, so the
Print Labels dialog produces something plausible and wrong, and the natural
conclusion is "the printer is misaligned." Load templates sized to the stock you
actually buy (44.45 × 12.7 mm for Avery 5167/8167) alongside the built-ins —
don't replace them, an upgrade expects to find them.

### The sheet plugin's column count flips on the margin field
**Symptom:** the same label sheet comes out 4-across one day and 3-across the
next, and a "skip 28" that worked lands everything one row off.
**Cause:** the plugin computes `floor((page − 2×margin) / label_width)`. On US
Letter with a 44.45 mm label, margin 10 mm gives exactly 4 × 20 — the Avery
grid. With a 50 mm label the same margin gives **3** columns, and margin ≤ 5 mm
gives 4. The cliff is invisible in the dialog.
**Fix:** compute the grid before setting *skip*, and print one bordered test
page on plain paper. Also check the printer's own unprintable edge — a 5 mm
margin sits right on it and shaves the outer columns.

### A generated sheet is a PDF, not a print job
`InvenTreeLabelSheet` writes a file and stops; nothing reaches a print queue, so
"Process completed successfully" with no printer activity is correct behaviour,
not a failure. The PDF lands in `data_output/` and is served from `/media/`,
which requires the session cookie — so the link only opens in the browser you
are logged into.

### Browser print settings can walk labels off-register
Headers/footers force the browser to shrink page content — every label drifts
progressively down the sheet. Scale: None, margins: None, headers OFF, feed
label stock one sheet at a time through the bypass (cassette separator pads
lift label edges).

## Data modeling

### Footprint is part identity
Merged two same-value capacitor parts "because search answers the question
anyway." Wrong: with CAD integration a part record is a footprint commitment,
and a 4x7 vs 5x11 radial have different lead pitch. Reverted. Also: never
assert an unmeasured footprint — the honest value of an unknown is blank.
Bonus: for radial electrolytics, **body diameter fixes pitch** (standard
series: Ø5→2.0mm, Ø6.3→2.5, Ø8→3.5, Ø10→5.0), and diameter is the
*trustworthy* measurement — calipers across splayed leads over-read.

### A TSC pull stud on this shop's BT30 has nothing to do with coolant
**The 1100MX does not support through-spindle coolant at all.** Every general
source, and plain reading of the name, therefore says the TSC (drilled)
retention knobs were a mistaken purchase. They were not, and the reason is
invisible from the catalogue:

Scott, 2026-08-23: *"the TSC studs are to allow for a welding wire to be run up
through the holder during heat shrink removal of a tool."*

A drilled knob leaves a clear passage from behind the taper through to the tool
pocket. When a shank will not release from a hot shrink-fit holder, you push it
out from behind with a length of welding wire. A solid knob closes that path and
there is no other way in.

**So the stud type is NOT a free per-holder choice — the holder decides it:**

| Holder | Stud |
|---|---|
| Shrink-fit (#109, #111, #112 — all named TSC) | **TSC / drilled, mandatory** |
| Everything else BT30 | Standard |

There is a **second, independent** reason the same hole matters, already recorded
as `MR-16` in `shrink-fit/docs/requirements.md`: a drilled knob **vents the blind
bore**, which is why the spring-loaded hold-down was downgraded to optional.
Vapor lock — sealed air expanding and pushing the tool out in the seconds before
the steel grips — is moot on a vented holder. MR-16 says to build the hold-down
*only if a solid knob is ever fitted*.

Fitting a standard stud to a shrink-fit holder therefore does two bad things at
once: it re-creates the vapor-lock problem the induction machine was allowed to
ignore, and it removes the only push-out path for a stuck tool. **Neither is
recoverable at the bench** — you find out with a hot holder in your hand.

`scripts/stud_check.py` enforces the pairing at order time, and the rule is on
the `Tooling/Holders`, `Tooling/Toolholders/BT30` and `.../Pull Studs` category
descriptions in InvenTree. **`PartCategory.description` caps at 250 characters
and truncates SILENTLY** — the first attempt lost the command off the end and
only the verify caught it. Assert the length before writing.

### Body size is the envelope; PIN COUNT is the footprint
Two 6x6mm tactile switches were merged on 2026-08-21 because both measured
6x6mm. Scott turned them over: the SparkFun ones have **four legs**, the ones
already in B3-R1C3 have **two**. Same envelope, different PCB footprint, not
the same part. Merge reversed; they now sit in the same drawer as separate
records — a good location with a different description.

Asking for a measurement was right. Stopping at *one* measurement was not.
`6x6mm` describes the plastic body, which is what a caliper reaches easily and
what a vendor title advertises. What a board actually needs is the pin pattern,
and on a tactile switch that is only visible from the underside — the top of a
2-pin and a 4-pin 6x6 are indistinguishable.

Before merging any through-hole part on a size match, ask for the thing the
footprint depends on and not merely the thing that is easy to measure:

| Part | Size names | Footprint needs |
|---|---|---|
| Tactile switch | body envelope | pin count (2 vs 4), pitch |
| Radial electrolytic | body Ø | lead pitch (Ø fixes it — see above) |
| LED | barrel Ø | Ø **and** lead pitch |
| Header | pin count | pitch, row count, gender |

### On a flanged pulley, the FLANGE is what your calipers grab
A 20T timing pulley was measured at 16 mm to settle whether it was GT2 or
HTD-3M. Sixteen matched neither — GT2 20T is 12.2 mm across the tooth tips and
HTD-3M 20T is 18.3 mm — and that mismatch is the only thing that caught it.
The 16 mm was the **flange**, which on this part runs 3–4 mm larger in diameter
than the teeth and is the widest, easiest thing on the pulley to catch. Measured
again on the narrow toothed barrel between the rims: **12.2 mm, GT2, confirmed.**

Same shape as the LED dome below: the feature that names the part is not the
feature the tool naturally lands on. **Say which surface to measure, not just
what dimension.**

The mismatch is also the lesson. Had 16 mm happened to fall near a real value it
would have been accepted. Working out the expected figures for *both* candidates
first meant an out-of-range answer announced itself instead of being written
down — so compute what you expect to see before asking for a measurement.

### An LED's size is its BARREL diameter — measuring the dome under-reads
The SparkFun kit's surviving LEDs were called 3mm on 2026-08-21, against a kit
list that said 5mm. Scott asked the right question before anything was written:
*"where should you measure them? I'm measuring towards the middle of the LED
surface."* Mid-dome is a chord of a hemisphere, not a diameter, so it reads
low — a 5mm LED measured up its dome comes out around 3–4mm, which is exactly
the reading that had been taken.

Measure the straight cylindrical barrel, above the flange at the base and
below where the dome starts. The flange is wider than the barrel and is not
the number either.

| | barrel (names the part) | flange | height |
|---|---|---|---|
| 3mm | 3.0mm | ~3.8mm | ~5.3mm |
| 5mm | 4.9–5.0mm | ~5.8mm | ~8.6mm |

**Height is the easier tell** — 5.3 vs 8.6mm is flat-to-flat and hard to
confuse, where a caliper on a curved body is not. (Re-measured at the barrel,
these were genuinely 3mm.) Footprint is part identity, so a wrong reading here
creates a wrong part, not just a wrong note.

### Same capacitance, two notations = invisible duplicate
`0.1uF (104)` and `100nF (104)` coexisted as separate parts. Pick a canonical
notation by range (pF < 1nF ≤ nF < 1µF ≤ µF) and keep marking codes in the
description — the same 10pF is stamped `100` by one vendor and `10` by
another, so codes in names reintroduce the collision.

### Pack-size detection from vendor titles has two false-positive classes
Numbers followed by units are dimensions ("Plate 20 x 9.5in x 10mm" is not a
10-pack), and assortment kits are not multi-packs (an "850pcs, 30 values" kit
is one box of 30 different parts — a pack_quantity would assert stock that
can't be picked).

## Email mining

### The marketing-subdomain decoy
Every vendor sends daily marketing from a *different* subdomain than its order
mail, and `from:<domain>` searches return newest-first — so the first 50 hits
are 100% marketing and the order sender never appears. Three vendors were
wrongly written off as "no order email" this way. Always constrain:
`(subject:order OR subject:invoice OR subject:shipped)`.

### Extended vs unit price
Several vendors' order emails list **extended** prices (qty × unit). Divide
before recording, and verify against the order total. Others give both
columns. Assume nothing; verify each vendor once and write it down.

### Ordered ≠ received ≠ kept
Orders get held, cancelled after confirmation, refunded after delivery, and
returned. An automated PO pipeline must leave everything in Placed until a
human confirms physical arrival, and a review pass must catch
refunds/returns or they become phantom stock (or phantom open POs).

### Amazon truncates the product title in the email BODY, not just the subject
Chasing the origin of four timing pulleys on 2026-08-21, the order confirmation,
the shipping confirmation and the seller-feedback request all render the item as
`Zeelo GT2 Timing Belt 9mm...` — **with a literal ellipsis in the plaintext
body**, not only in the subject line. Amazon's own emails never carry the full
title. The bodies do carry the order number and the total, and nothing else
useful about *what was bought*.

This bounds what email mining can ever do for Amazon: it can tell you an order
happened, when, and for how much, but **the item is only ever a truncated
prefix**. That is enough to match against a known part and not enough to
identify an unknown one. Contrast JLCPCB, whose shipping notifications list
gerber name and quantity in full — see `docs/jlcpcb-boards.md`.

Practical consequences:
- Do not expect a backfill job to recover full product names from mail.
- A truncated prefix is still a usable search key — `Zeelo GT2 Timing Belt 9mm`
  was enough to establish the shop runs GT2 with 9mm belt.
- The full title lives on the order page, which is behind bot detection. Drive
  a browser if it genuinely matters; do not retune a fetch.

## Scheduled LLM agents

### A hung run looks exactly like a lazy one
Runs died two ways — killed mid-flight, and hung forever on a permission
prompt no one could see — and both left zero trace, which burned a day of
"why is the progress file stale."
**Fixes:** (1) pre-approve every command pattern the agent needs (prefix
rules, not per-command approvals); (2) **journal-first protocol** — append a
RUN STARTED line before doing anything, one line per completed chunk, summary
last. A dying run then loses one chunk of record, not the whole run — and the
next run can *report* that its predecessor died.

### Give the agent's discoveries a path back into its own instructions
The first successful run discovered its instructions were impossible (the PO
reference format) and adapted. If that discovery doesn't get folded back into
the task file, every future run rediscovers it.

## Agent tooling

### Permission rules never match a heredoc or a compound command
**Symptom:** broad allow rules like `Bash(ssh *)` are in place and every command
still prompts. Approving them accumulates hundreds of rules that never fire
again — 243 dead literals in one settings file.
**Cause:** the matcher reads the first token. A command beginning with a
variable assignment (`SP=/tmp/...`) matches nothing, and
`cat <<EOF … && scp … && ssh …` cannot be decomposed into its parts. Each such
command is unique, so each approval is a one-off.
**Fix:** the answer is not more rules — it is **one stable command shape**.
Write the script to a file with the editor tool, then invoke it as a single
simple command through a wrapper directory that one wildcard covers
(`Bash(<repo>/scripts/*)`). See `scripts/itq`.

### Interjected images never reach the transcript
A photo sent while a tool call is running is visible to the agent but is **not**
written to the session JSONL — so it cannot be extracted afterwards. Photos sent
as their own message are. If an image needs to be pushed into a system later,
ask for it as a standalone turn.

## Vendor sites

### Order-detail links do not navigate programmatically
Amazon order *search* pages read fine, and the "View order details" links do
nothing when clicked by automation — no error, no navigation. Order dates and
titles are available from the search results; **prices are not**, and the
product page shows today's listing price, not what was paid. Ask the human for
the figure rather than recording the current price as if it were the receipt.

### 403 with no body means fingerprinting, not authentication
Vendor docs sites (Digilent among them) sit behind bot detection that returns
403 to a plain fetch and a "verifying you are human" interstitial to a driven
browser. Do not work around it. Record what is certain, link the page, and note
*why* the numbers are missing — a plausible spec written from memory is worse
than an absent one, because nobody re-checks it.

### Receiving the last open line auto-completes (and locks) a PurchaseOrder
Creating one line, receiving it, creating the next — the first line is also the
*last outstanding* line at that instant, so InvenTree completes the order, and
a completed order refuses new line items with "The order is locked and cannot
be modified". Create every line while the order is open, then receive, then
complete. Walking `status` back to PLACED via queryset `.update()` unlocks an
order that completed early.

### The Amazon import has gaps
A 460-piece JST XH2.54 kit (2023-07-31, $8.99, order ORDER-REDACTED) had
no part, no supplier record, and no trace in the catalog. It surfaced only in
the order-confirmation email. Treat "not in InvenTree" as weak evidence that
something was never bought — check the mail archive before concluding a part
has no source.

### KiCad footprint names are not part numbers
Three Rat GDO parts were built from footprint library names and all three were
wrong: `Fuse_1206` was a resettable PTC at 500 mA, and two `PhoenixContact`
footprints were fixed-screw KF350 and DB301V blocks that are through-hole, not
SMD. The footprint says what fits the pads. The invoice says what you own.

### A plugin JS change needs a full restart, and HUP fails silently
`kill -HUP` on the gunicorn master recycles workers with zero downtime and the
API answers 200 — it looks like a clean reload. But the static-file layer keeps
its old cache, and what it serves can be a TRUNCATED copy: after pushing a
164-line plugin JS, the server served 6884 of 7804 bytes, cut off mid-function,
with the last exported render function missing entirely. The new function was
present, so grepping for it said "works". The existing widget it silently
dropped would have rendered blank.

Use `launchctl kickstart -k gui/$(id -u)/com.inventree.server`, then verify by
comparing md5 of the served file against the file on disk — not by grepping for
the thing you just added.

### Purchase-history tables have three different column orders
The markdown tables the imports wrote into `Part.notes` are not one format:

    | Date | Qty | Unit | Line total | Order |      Amazon
    | Date | Order | Qty | Unit |                   Lakeshore and friends
    | Date | Quote | Order | Qty | Unit |           Tormach

A regex that assumes Amazon's order reads the QUANTITY as the price — a $69.49
threadmill rendered as "$1" — and silently skips Tormach entirely, because its
order number is not numeric. Parse the header row and read by column NAME.
Also: a $0 row dated after the real purchase must lose to the real one.

### creation_date is when you typed it in, not when you bought it
`PurchaseOrder.creation_date` on a back-filled order is months after the
purchase. Read `issue_date` first and label the fallback. And exclude PENDING
orders from "last bought" — a shopping list is not a purchase, and the TO-ORDER
list will otherwise report itself as the most recent one.

### Amazon's order-confirmation subjects stopped carrying product titles
Around 2026-07-16 the format changed from `Ordered: "<product title>..."` to
`Ordered: 1 Electronics item`. Any sweep that reads subjects goes blind after
that date. Use the order-history search instead — it returns full titles and
works back to at least 2016:

    https://www.amazon.com/your-orders/search?search=<terms>

(Order detail pages DO load programmatically while signed in:
`https://www.amazon.com/gp/css/order-details?orderID=<id>`. An earlier note
here claiming otherwise was written while logged out.)

### Fuzzy title matching fails in the dangerous direction
Reconciling purchases against the catalogue by token overlap produced confident
nonsense: "SHNITPWR 12V Power Supply" matched *DROK Time Delay Relay*,
"Raspberry Pi Zero WH" matched an *HDMI adapter*, "1/4 HP Lathe BandSaw"
matched a *threadmill*. A false MISS costs a glance; a false MATCH hides a real
gap forever. Always re-check the brand token directly before believing a match.

### Loose fasteners pack at roughly HALF what the arithmetic says
Asked whether 100 of a 1/4 x 2in hex-head lag screw would fit a 20.8 cu in
drawer, a solid-volume calculation plus a guessed 55% packing efficiency gave
~21 cu in — "dead on the line, just try it". Scott, holding them: *"The one
hundred is gonna take at least two drawers."* So the real figure is north of
40 cu in, and the estimate was low by about 2x.

Why: hex heads and coarse threads interlock badly and cannot nest. The naive
model treats a screw as a cylinder and then applies a packing factor borrowed
from smooth stock. **For loose headed fasteners, budget ~4x the solid volume**,
not the ~1.8x that 55% implies — and treat even that as a starting guess.

The right move is still what happened: say the number, say it is a model, and
let the person holding the box settle it. Quoting ~21 cu in as though it
decided the question would have put 100 lag screws in a drawer that will not
close.

### `[ESTIMATE]` is a PREFIX flag — test with startswith, not `in`
A verification step reported that a stock item was still flagged `[ESTIMATE]`
after being counted. It was not. The check was `'[ESTIMATE]' not in notes`, and
the new note legitimately *quoted* the marker while explaining its own removal:
"…the first line to graduate from [ESTIMATE] to a real count." The substring
test found the word in the prose describing its absence.

The convention is that `[ESTIMATE]` **opens** the note. Every query that
matters must use `notes__startswith('[ESTIMATE]')` — a companion query in the
same script did, and reported the correct answer at the same moment the other
one cried failure.

Worth its own entry because the failure inverts the usual danger: the write
succeeded and the *verification* lied. A check that can produce a false alarm
trains people to ignore checks, which is worse than having none.

### Line count is not drawer volume
A3-R8C1 showed "2 lines, 5 units" and was recommended as having room for 15
LM2596 modules. It was full. The database counts RECORDS, and says nothing
about how much space three bagged assortments physically occupy. Never propose
a drawer from occupancy figures alone — either check a photo, or offer a
verified-empty drawer, or ask.

### Zero stock items does NOT mean the drawer is empty — read the description
B3-R3C2 was offered as "an empty drawer" for TO-220 regulators on 2026-08-21.
Scott: "B3-R3C2 is definitely not empty. That has ICs in it already." The
drawer has zero `StockItem` rows, so a `filter(location=d).exists()` check
called it empty — but its own `description` field said, in full: *"SMD
components — 8-value bridge rectifier kit (vendor no. 48-13). SMALL drawer: it
takes the kit bag and not much else."* The answer was already in the database,
in the field the query did not look at.

Why the gap exists: a drawer walk records what it finds in the location
description immediately, and stock records are created later — or never, for
things nobody has itemised. So an un-walked or partly-walked drawer and a truly
empty one are indistinguishable by stock count alone.

**Emptiness is a claim someone made, not a row count.** This estate says so
explicitly: the genuinely empty drawers read `VERIFIED EMPTY <date>`, the
unknown ones read `NOT WALKED — contents unknown`, and the rest describe their
contents. Trust that sentence, never `count() == 0`.

**And do not fill the gap with a guess either — that is the same error wearing
a hat.** Having just written the rule above, this file then asserted that A1
and A2 were "cabinets full of uninventoried hardware", reasoning from the
`M3 .5 x20` legacy labels. Those labels are on **B1**. Scott, walking the room
on 2026-08-21: A1 has a few things in it, A2 is *virtually empty*, B1 and B2
hold the hardware and are filling up but are not full. So the correction to
"the database is silent" is to **go and look, or ask** — not to infer contents
from a neighbouring cabinet. An inferred answer is indistinguishable from a
known one once it is written down, which is precisely what makes it expensive.

Cabinet-level reports get recorded on the **cabinet**, not stamped onto its 64
drawers. Writing "virtually empty" onto every A2 drawer would forge 64
per-drawer checks from one glance across a room.

Corollary: a stale physical label is not evidence either. B3-R5C1 is
`VERIFIED EMPTY` but its printed label still reads "Hall effect sensors" —
those moved to B3-R4C4. Reprint on reassignment or the drawer lies to the room
while the database tells the truth.

### Do not read quantities or contents from photographs
Three wrong calls in one morning, all from inferring more than a photo can
carry: an empty bag beside loose caps read as "these came out of that kit" (the
kit is compartmented and bags nothing); one compartment read as depleted when
it just held physically larger parts; and in an earlier session, gull-wing
leads read off a 2D image as SMD when the parts were through-hole.

A photograph reliably shows IDENTITY — printed labels, part numbers, silkscreen,
package shape against a known reference. It does not reliably show COUNT,
FULLNESS, or PROVENANCE. Read the label; ask about the quantity. The person
holding the parts can see all three.

## Networking

### Local DNS across sites
Each site's clients resolve via their own gateway — a record created on one
console does nothing for the other site. Create it on both.

### iOS clings to negative DNS answers
Tried the name seconds after creating the record → phone cached "doesn't
exist" → airplane-mode toggle does NOT flush it. A different (older) record
resolving while the new one fails is the signature. Reboot the phone.
Also: iCloud Private Relay bypasses your gateway DNS for Safari entirely —
per-network "Limit IP Address Tracking" is the surgical fix.

### Rapid SSH loops can trip IDS
An agent hammering ssh in a loop looks like an attack to UniFi IPS — port 22
goes dark for minutes while everything else answers (that's the tell). Batch
remote work into one uploaded script, run once, read the log once.

## Label printing (Brother QL-810W)

### brother_ql raster is dead on this unit — use CUPS/AirPrint
The QL-810W accepts every job on port 9100, prints nothing, latches a blinking
red error, and has NEVER answered a status request — not in P-touch Template
emulation, not after Command Mode was switched to Raster, not with stock
brother_ql CLI defaults against a freshly cleared printer. Reachability is not
the problem: closed ports refuse honestly, HTTP works end-to-end from the Mini,
and the job arrives complete (printer closes its side cleanly).

The SAME printer's AirPrint/IPP stack is healthy — reports `idle`,
`printer-state-reasons: none`, and correctly identifies its own media. So print
through CUPS driverlessly (`-m everywhere`), never brother_ql. The
`inventree-brother-plugin` is installed but useless here; `cups_label` replaces it.

### The error LATCHES — one job per clear cycle
After a failed job the printer ignores everything sent until the error is
cleared (power cycle). Sending three variants in a row to see "which one works"
tests only the first; the rest are no-ops that LOOK like failures. This
invalidated several rounds of testing. Clear → send ONE → observe → clear.

### CUPS silently upscales a label narrower than the tape
The stock 50mm InvenTree template on 62mm tape got scaled 1.24x to fill the
media: QR came out oversized AND the overflow was clipped off the bottom.
`print-scaling=none` / `=fit` do nothing — the option is not in this queue's
`lpoptions -l` list, so CUPS ignores it. The fix is to author the template at
the tape's true width (62mm) so there is no scaling to do.

### A thermal printer cannot mark its unprintable margin
InvenTree's stock location template pins the QR at `left:0/top:0` sized to the
FULL label height, so it touches both edges and gets clipped. A QR missing part
of a finder pattern or its quiet zone does not degrade — it stops decoding.
Inset everything ≥2mm. Measure the render's ink bounding box BEFORE printing
(`pdftoppm` + `getbbox`) rather than judging margins off a photo of tape.

### Queue defaults, not job options, are what InvenTree gets
InvenTree submits through CUPS knowing none of this, so `PageSize`,
`MediaType=Roll` and `CutMedia=EndOfPage` belong on the QUEUE via `lpadmin -o`.
The driver's default PageSize here is `29x90mm` — a die-cut size unrelated to
the continuous roll loaded. `roll_current_62x0mm` from the IPP `media-ready`
attribute is NOT a valid PageSize keyword; use `Custom.62x16mm`.

### Django `{# #}` comments are SINGLE-LINE — multi-line ones PRINT
A multi-line `{# ... #}` inside a `{% block %}` is not a comment. Django only
treats hash-brace as a comment on one line, so the rest renders as visible text
straight across the label — several labels came out carrying this file's own
source comments. Use `{% comment %}...{% endcomment %}` inside blocks. Comments
placed OUTSIDE a block in an `extends` template are discarded and are safe.

### WeasyPrint does not honour `overflow: hidden`
CSS `max-height` + `overflow: hidden` does NOT clip an absolutely-positioned
block in InvenTree's PDF renderer. A long part name silently overprints the
line below it — the label still passes an ink-bbox margin check, because
overlapping text is still ink in the expected region. Truncate in the TEMPLATE
(`|truncatechars:N`), and verify by rendering to PNG and LOOKING at it, not by
measuring margins.

### "Labelled" is THREE states, and `labeled` only models two
A 62mm label was printed for A3-R1C1 on 2026-08-21 because `labeled` read
`None`. Scott: *"All of these labels are already printed for the wall
cabinets... on Avery sheets, so no need to reprint them."* Then, correcting the
over-correction that followed: *"The metadata was right. The label wasn't
actually affixed to the drawer, but the labels are printed."*

Both statements are true, and the flag was accurate the whole time. A drawer is
in one of three states:

| State | `labeled` | Reprint needed? |
|---|---|---|
| Not printed | false | **yes** |
| Printed, sitting on a sheet, not stuck on | false | **no** |
| Printed and affixed | true | no |

`labeled` correctly means **affixed** — that is `LABELLING.md`'s definition and
it never wavered. What nothing recorded is the middle state, which is where most
of the estate actually sits: as of 2026-08-21, **84 drawers affixed and 240
printed and waiting**. Installing them is a slow manual job being done a bit at
a time.

The middle state is the one that decides whether to print. Reading `labeled:
false` as "needs a label" would have queued 240 duplicates — most of a roll of
scarce starter tape. It is now recorded as `metadata.label_printed`.

The trap generalises past labels: **a boolean flattens a workflow that has more
than two stages, and the missing stage is usually the one you need.** Before
acting on any false flag, ask what the field actually asserts and what lies
between its two values. And when a correction arrives, do not swing past it —
the first fix here flipped 23 drawers to `true`, which would have left them
permanently bare because nothing ever offers to label a drawer already marked
done.

### Most IPNs here are Amazon ASINs
`IPN` is "B017KUC6XQ" for most of the imported catalogue — useless on a label.
Print the default_location instead; where a part lives is what you need
standing at the drawer.

## A trailing "X100" in a fastener SKU is the length, not the pack quantity

`F-MSOP1032X100` decodes as Machine Screw Oval Phillips, 10-32, **× 1.00 inch
long**. It says nothing about how many are in the box. The same three digits
read as a pack size are a plausible, wrong quantity — and this box genuinely
does hold 100, which is exactly what makes the coincidence dangerous: the wrong
reading was confirmed by the right answer.

Take the count from the box label or from counting. Never from the part number.
Distributor SKUs encode thread, head style and length in one run of characters,
and every field in them looks like every other field.

## A "no gaps found" sweep only clears the categories it asked about

The 2026-08-19 Amazon reconcile concluded the import was broadly sound: four
gaps in ~330 orders. True, and it was an **electronics** sweep. When hardware
started being inventoried two days later, an uncatalogued Amazon fastener order
turned up immediately — in the readable subject format, never matched because
never sought.

A negative result carries the scope of the question. Write the scope next to
the conclusion, or "we checked" gets remembered without the "for what".

## A staging area cannot tell "not yet filed" from "already used up"

The NEMA 6-20P plug (#784) sat in `SLN/Receiving` marked *"awaiting a home"*
from 2026-08-18. It had no home because it was **already installed** — Scott,
2026-08-21: *"that plug was used in the heat shrink project."* It is terminated
on the shrink-fit controller's power cord and was never coming back.

Those two states look identical in a staging area, and they are opposites. One
is stock you still have; the other is stock you spent. A staging location
reporting "3 items awaiting placement" is really reporting "3 items whose
status nobody has revisited."

- **Anything in Receiving for more than a few days needs asking about, not
  filing.** The question is "where does this go?" *and* "is this still yours to
  place?"
- **Consumed stock moves to where the object physically is** — here
  `SLN/Machine Shop`, on the machine — with a note saying what consumed it.
  Deleting the row loses the fact that the part exists; leaving it in Receiving
  claims it is available. Neither is true.

Corollary to the parking rules: a parking spot's description records what went
in and when, but only a **person** can say whether an item is still waiting.
Age in a staging area is a question, not a fact.

## A push-to-connect fitting has no thread — do not ask for its NPT size

The shop air valve was recorded needing a "port size (1/4 vs 1/2 NPT)" before
it could be used. Wrong question. It is a **1/2in push-to-connect** valve from
the PRIMEFIT nylon air piping kit that runs air to the shop and garage, and
nothing threads into it. PTC fittings are sized by the **tubing OD** they
accept.

The failure is subtler than being wrong: a plausible-sounding spec request
sends someone to the bench hunting for a marking that does not exist, and they
come back with either nothing or a guess. Asking for the wrong dimension costs
more than asking for none, because a question implies the answer is there.

Before requesting a measurement, establish what KIND of interface the thing
has. Threaded, push-to-connect, barbed, compression and flare are all "1/2
inch" in different and incompatible senses.

## "Never re-ask" needs an escape hatch, or a reversed policy fails silently

The overnight agent records declined decisions and never raises them again —
a good rule that stops it pestering Scott about the same consumer order every
night. On 2026-08-18 he declined label stock: *"consumable, not inventoried."*

On 2026-08-21 he reversed that, asking for label tape to be tracked **with a
reorder point**, because it gates every other labelling task. The standing
decline would have quietly binned the very next label order.

Nothing would have gone wrong visibly. The rule would have worked exactly as
designed and produced the wrong outcome, and a **silent skip is
indistinguishable from nothing happening** — no error, no journal line, no
missing-PO alarm. It would have surfaced weeks later as "why isn't my tape in
the system?"

The fix is a distinction the original rule did not draw:

| Declined thing | Lifetime |
|---|---|
| A specific **order number** | settled forever — genuinely never re-ask |
| A **category** ("label stock", "zip bags") | a standing *policy*, and policies change |

A category decline now moves to `## reversed` when overturned, with the date
and the new policy, and sweeping resumes. The reversal also triggers a check
for anything skipped while the decline stood.

**Generally: any rule of the form "remember this answer forever" needs a
defined way to change the answer.** Without one, the memory outlives the
reasoning that produced it, and the system gets more confidently wrong the
longer it runs.

## Diagnose a failed fetch by WHERE it dies, not how fast

`st.com` would not serve a datasheet to curl. First reading: it failed in
43 ms, so something local must be answering — Malwarebytes was the obvious
suspect and was written up as the cause. **Wrong.** Verbose output settles it:

```
*   Trying 23.211.136.6:443...
* Connected to www.st.com (23.211.136.6) port 443
* SSL connection using TLSv1.3 ... SSL certificate verify ok.
* HTTP/2 stream 1 was not closed cleanly: INTERNAL_ERROR (err 2)
```

DNS resolved. TCP connected. **TLS completed and the certificate verified.**
Only then was the stream killed. A local blocker — security product, hosts
file, DNS sinkhole — kills a connection *before* TLS, because it has no
certificate to offer. Getting a verified TLS session and then being dropped
means you reached the real server and **the server chose not to answer you**.

Forcing `--http1.1` does not fix it; it hangs for 25 s instead (exit 28). Two
different symptoms, one cause.

**Read the connection sequence, not the clock:**

| Dies at | Cause | Fix |
|---|---|---|
| DNS resolution | Local sinkhole, hosts file, DNS filter | Whitelist / check resolver |
| TCP connect | Firewall, routing, dead host | Network |
| **After TLS verifies** | **The server is fingerprinting you** | **Drive a browser** |
| 403 / 450 / empty 202 | Same thing, stated politely | Drive a browser |

So `curl exit 92` (HTTP/2 stream error) and `exit 28` (hang) join 403/450/202
as fingerprinting signatures. They look like network faults and are not.

**Latency alone is a trap.** 43 ms says "something answered fast", which is true
of a DNS sinkhole *and* of a server resetting your stream — opposite problems,
opposite fixes. Only the sequence separates them, and `curl -v` prints it for
free. Two wrong diagnoses here came from reading the timing and skipping the
transcript.

## Octopart works in a human browser and challenges an automated one

Octopart is a good route to manufacturer datasheets — Scott: *"by going through
Octopart I could easily get to ST's datasheets."* It is **not** a route for
this project's automation. Plain fetch returns 403; a driven browser gets a
PerimeterX interstitial (*"One more step — please complete the security
check"*) with a client IP and block reference.

Solving that is off the table, permanently. When a mirror throws a CAPTCHA, the
answer is to fix the path to the *source* — see the Malwarebytes entry above —
or to have a human fetch the handful of files by hand. Working around a bot
challenge is how an account or an IP gets burned for a few PDFs.

## A check that can't tell "no" from "couldn't look" is worse than no check

The datasheet verifier greps a PDF's text for the part number and refuses the
file if it is absent. It rejected the HUBER+SUHNER **RG178** sheet — which is
the correct document. Extraction had produced a megabyte of decompressed
*binary* (colour profiles, fonts, images) and **99 readable words**. The marker
was not absent; nothing was legible to look in.

Two states could not express that. "Reject" meant both *this is the wrong
document* and *I could not read this document*, and those need opposite
responses. Worse, the failure is silent and confident: a false negative is
indistinguishable from a true one, so the check gets trusted precisely when it
is wrong.

Now three states — `ok` / `no` / `unknown` — with readability measured by
counting ASCII words of 4+ characters. Under 200 means the extractor failed,
not that the document did. `unknown` needs `--allow-unverified` to attach, and
the attachment comment is stamped **NOT CONTENT-VERIFIED** so the gap travels
with the record instead of being lost at the command line.

**The general rule: any validator needs a way to say "inconclusive".** A binary
pass/fail forces every "I don't know" into one bucket or the other, and
whichever bucket you choose is wrong half the time — silently. Ask of any check:
*what does it return when it cannot run?* If that is the same value as failure,
it will eventually reject something correct and nobody will find out.

## Measure whether your CHECK worked before believing what it says

The datasheet verifier greps a PDF's text for the part number. Tuning its
"could I read this?" test produced two wrong answers in a row, both confident.

**Attempt 1 — word count.** Reject if the marker is missing. It rejected the
correct NXP BC327 sheet: 250 extracted "words", over the 200 floor, so the code
believed extraction had worked and reported *wrong document*. The 250 "words"
were fragments of inflated font data.

**Attempt 2 — the fix that revealed the real signal.** Count datasheet
vocabulary, not words. Measured across five known files:

| File | Words | Datasheet terms | Truth |
|---|---|---|---|
| NE555 | 3030 | 3 | extraction worked, right part |
| MB6F | 2377 | 9 | extraction worked, right part |
| A1015 → LeaderTech | 4827 | 3 | extraction worked, **genuinely wrong part** |
| BC327 | 250 | **0** | extraction FAILED |
| BC337 | 295 | **0** | extraction FAILED |

Word count cannot separate rows 3 and 4; vocabulary separates them cleanly. A
document with thousands of words and zero occurrences of *voltage*, *maximum*,
*typical* or *temperature* is not a datasheet you have read — it is binary you
have inflated.

**Then: when one witness is blind, find another.** Unreadable text does not
mean no evidence. The URL is independent of extraction entirely, and
`MB10S.pdf` served by Diodes Incorporated for part MB10S is strong evidence, as
is `nxp_bc817_bc817w_bc337.pdf` for BC337. It fails safe — a wrong document
rarely carries the right part number in its filename. Adding that single
fallback took verified attachments from 2 to 6, and every attachment records
*which* witness convinced it, so a reader can discount URL-only evidence.

**The general rule: a validator has two failure modes, and only one is
visible.** "The check says no" and "the check could not run" arrive through the
same return value unless you deliberately separate them. Before trusting a
negative, measure whether the check had anything to work with — and prefer a
signal that distinguishes *absent* from *unreadable*, because a count of
anything cannot.

## A note claiming a location is not a location

Stock item #89, a 7-pin DIN extension cable, carried the note *"Received
2026-08-18 to Receiving — awaiting a home"* and had **no location set**. The
prose was right and the data was empty, so the item was invisible to every
location query and did not appear in Receiving's own contents. Anyone standing
at the shelf would not have found it; anyone reading the record would have
sworn it was there.

This is the mirror of the 6-20P plug, where Receiving *claimed* an item that
had already been consumed. Same root cause from opposite directions: **the
narrative and the fields disagreed, and only the narrative was maintained.**

Prose in a note is for the things a field cannot hold — why, when, who said so.
The moment it states something a field exists for (location, quantity, date),
the field must agree, because every query reads the field and every human reads
the note. When they diverge, the record is confidently wrong in two directions
at once.

Cheap audit, worth repeating after any bulk import: list stock with
`location__isnull=True` and grep the notes for a location word. A row whose
note names a place it does not point to is always a defect.

## A COMPLETE build that allocated nothing still shows its parts as on-hand

Found 2026-08-22 from a single cable. All three completed builds consumed
**zero** stock:

| Build | BOM lines | Allocations | Output stock created |
|---|---|---|---|
| BO-0003 Desk controller | 7 | **0** | 1 |
| BO-0008 Rat GDO — three already built | 15 | **0** | 0 |
| BO-0013 Shop Minisplit CN105 Adapter | 5 | **0** | 0 |

Marking a build complete does not consume its BOM unless stock was allocated
first. So parts soldered into three working devices still answer *yes* to "do I
have one?" — the 6-20P plug failure, systemic rather than one row. Two of the
three do not even show the thing that was built.

**But do not "fix" it by subtracting BOM quantities.** That would invent a
consumption figure, and BO-0008 is titled *"three already built"* — it
documents work done before the catalogue existed, so its parts may never have
been stock here at all. Reducing counts on that assumption manufactures exactly
the kind of number this project refuses to manufacture. The honest states are
"consumed, known quantity" and "unknown", and only a person can say which
applies per build.

### The right model for a part inside a finished thing: `belongs_to`

Not deletion, not a zeroed quantity, not a note. InvenTree's `StockItem.belongs_to`
installs one stock item into another, and it is the only option that stays true
on every axis at once:

- the part still **exists**, with its provenance and purchase price intact
- it is **not available**, so it stops answering "do I have one?"
- the assembly **lists what is inside it** (`installed_parts`)
- **uninstalling restores it to stock honestly**, which zeroing cannot

Applied to the 7-pin DIN cable: it had been sitting in Receiving marked
"awaiting a home" while wired into the desk controller. Now `belongs_to` stock
#120, location cleared, quantity untouched.

## A BOM is a plan; an allocation is a record. Do not read one as the other

BO-0003 completed 2026-08-18 with zero allocations — deliberately and correctly,
because the counts for most of its parts were taken *after* the build and
already net out the consumption. Allocating would have deducted them twice.

The problem is what the record then looks like to a reader: seven tidy BOM
lines that appear to describe the contents of a finished box. They do not. They
were **regenerated from a KiCad extract on 08-19, the day after completion** —
a description of the current schematic, not an observation of what left the
drawers. A substitution, a bodge wire, or a different resistor grabbed because
the right value was missing leaves no trace at all.

Evidence per line varied from proof to nothing, with nothing in the record
saying so:

| Evidence | Meaning |
|---|---|
| **Physical** — item installed via `belongs_to` | provable, survives re-reading |
| **Inferred** — a count taken after the build already excludes it | reasonable, unfalsifiable |
| **Design only** — kit estimates; 3 resistors leaving a 28-piece kit is invisible | no evidence at all |

Same shape as the kit-count evidence tiers: the number is not the problem, the
*undeclared confidence* is. A BOM presents all seven lines identically.

**Going forward: allocate before completing a build**, and the record becomes
observed rather than reconstructed. **For builds already finished, `belongs_to`
is the retrofit** — it converts a claim into a fact for the items you can still
identify, and leaves the rest honestly marked as design.

## `completion_date` is when someone typed it in, not when it was built

Deciding whether a completed build should deduct stock looks like a clean
computation. Compare each part's `stocktake_date` against the build's
`completion_date`:

- counted **after** the build → the count already excludes what was used → **do
  not deduct**
- counted **before** → the count still includes it → **deduct**
- never counted → **unknown**, decide nothing

The test is sound. It ran cleanly across all three completed builds and gave a
confident answer. **The answer was wrong**, because all three builds are
retrospective write-ups: created and completed within a day of each other,
recording work done earlier. BO-0008 says so in its own title — *"three already
built"*. For those, `completion_date` is a data-entry date, so the test
compares a count against the wrong event and cheerfully reports "counted before
the build, should deduct" about parts counted long after the soldering.

**The tell is `creation_date == completion_date`** (or within a day). A build
worked in real time is created, sits in production, and completes later. One
created and finished the same day is almost always a record of the past.

Two rules follow:

- **Record the PHYSICAL build date explicitly** when entering a historical
  build, in the notes if nowhere else. Without it the chronology is
  unreconstructable and every derived conclusion inherits the error.
- **When the chronology is unknown, deduct nothing.** An inflated count is
  visible and recoverable — you go to the drawer and find fewer than expected.
  A wrongly-deducted count reads as "I need to buy more" and is never
  questioned.

The wider point: a date field answers the question it was designed for, not the
question you are asking. Before computing on a timestamp, check which *event* it
records — and whether that event is the one in your reasoning.

## Backslash-escaped whitespace forces a permission prompt, whatever the rules say

`settings.json` allows `Bash(ssh *)`. The overnight job's first action is an
`ssh` command. It still prompted — and on 2026-08-22 the 02:05 run sat on that
prompt for **seven hours** and did nothing at all, leaving no journal entry,
which made it look like the run had never fired.

The dialog gave the reason: *"Contains backslash-escaped whitespace."* The
command embedded `date +%Y-%m-%d\ %H:%M`. **Escaped whitespace makes a command
unmatchable against allow rules — it asks regardless of any rule that would
otherwise cover it.** A wildcard as broad as `ssh *` does not help.

A second, independent reason the same command could never be approved: the
queue description was interpolated *into* it, so every run produced a different
string. Even granting it once would not cover the next night.

Both are the `one-stable-command-shape` rule restated. The fix is
`scripts/journal.py`, invoked as `itq run scripts/journal.py --start "…"`,
which matches one standing rule and never varies.

**For any unattended job, an unapprovable command is not a slow step — it is a
dead run that leaves no trace.** Nobody is awake to click Allow, and the job
cannot journal the fact that it is stuck, because the thing it is stuck on *is*
the journal write. Check every command an overnight job issues for:

- backslash-escaped whitespace (quote the argument instead: `date +'%F %H:%M'`)
- interpolated variable text inside the command string
- heredocs and `&&` chains, which never match a rule twice

The symptom is indistinguishable from "the scheduler never fired". `lastRunAt`
said it fired; the journal said nothing happened. Only the app's own Runs panel
showed the truth — a run still marked **Running**, hours later, waiting on a
dialog.

## A zero with no note is a question; a zero with a note is a fact

Stock item #341 (SHT31-D at RB-12) was flagged 2026-08-21 as the single
unexplained row in a sweep — quantity 0, no notes, no other piles. It looked
like a data error worth a trip to the bench.

It was correct. Four were bought 2026-06-28, all four were used, and four more
were reordered on 08-20. Nothing was wrong; the row simply never said why it
was zero.

**Write the reason down when you zero a row.** The number is identical either
way, and the difference is entirely in what it costs the next person: an
unexplained zero gets re-investigated every time somebody audits, and each
audit rediscovers the same nothing.

Same shape as `[ESTIMATE]` versus a counted quantity, and as VERIFIED EMPTY
versus a drawer with no stock rows. The project keeps arriving at one rule from
different directions: **a value without its provenance is not a smaller version
of the truth, it is a different and worse thing** — because it looks identical
and cannot be trusted.

### Corollary: read the description before calling something a duplicate

The same sweep flagged SHT31-D as existing twice, #292 and #54. It does not.
#54 is a **tombstone** — inactive, zero stock, zero suppliers, and its
description says `MERGED into part #292`. A name search found two rows; reading
either one would have closed it.

Exactly the B3-R3C2 mistake again — that drawer was called empty on a row count
while its own description said what was in it. **When a record looks wrong,
read its description before reporting it.**

## A listing title names the marketing category, the box names the polymer

Amazon sold it as *"Art3d Plexiglass Sheets, Clear & Flexible"*. The part was
created from that title as **Acrylic Sheet**. The physical box says **PET
Plexiglass Sheet** — and "plexiglass" is a brand name for *acrylic* (PMMA),
which PET is not.

This is not pedantry in a shop with a laser:

| | Acrylic (PMMA) | PET |
|---|---|---|
| Laser cut | vaporises cleanly, flame-polished edge | **softens and drags**, tacky edge, warps |
| Impact | brittle, shatters | tough, flexes |
| Good for | display panels, anything cut on the laser | guards and windows that must not shatter |

Reaching for this expecting acrylic behaviour wastes the sheet and the setup.
The two are close to opposites for the two things a shop actually does with
clear plastic.

Already recorded once in a different form — *"a photo of a label repeatedly
beat every other source, including the vendor's own listing"* — and this is the
same finding for materials specifically. **A vendor's title describes the
category a shopper searches for; the packaging describes what was made.** When
they disagree, the box wins.

Same family as grade on a fastener and footprint on a component: **the shared
word is not the identity.** "Plexiglass" is the word; the polymer is the part.

## Never attribute a measurement to someone who only quoted you

The M16 eyebolt identification was recorded as: *"Scott had it in hand and
measured the shank at 16 mm."* He never said that. He had pasted back one row
of **my own comparison table** — `Shank Ø 16 mm ≈ 5/8"` — and that restatement
of my text got written down as his independent measurement.

The object was first read as stamped **M6**, matching neither candidate on that
order — which is what exposed the fabrication.

**Postscript: the identification was right anyway.** The stamp is `M16`; it
sits upside down on the eye and the `1` is shallow. Confirmed by photograph,
plus the obvious physical check — an M6 eyebolt has a 6 mm shank, about
pencil-thin, and this is a forged lifting eye you can get two fingers through.

That does not rescue the note, it sharpens the lesson. **Being lucky is not
being careful.** Had the stamp read 3/8", the fabricated attribution would have
been exactly as confident, and it would have outranked every later attempt to
correct it, because "Scott measured it" is the top of the evidence hierarchy
here.

A second, cheaper check went unused: **a reading that contradicts the object's
obvious scale should be re-read, not believed.** M6 was never plausible for
this object, and noticing that would have caught it before any record changed.

**This is the worst failure mode available to this catalogue**, and worse than
simply being wrong. A note reading "Scott measured it" is the strongest
evidence tier there is — it outranks a datasheet, a listing and a purchase
record, and it is specifically the tier that stops a future session
re-checking. Fabricating it does not add a wrong fact; it adds a wrong fact
wearing armour.

The failure is easy to repeat, because a quoted line and a reported measurement
look identical in a chat transcript. Before writing "Scott said / measured /
counted N":

- find the message where he **originated** that number
- if the number first appears in something *you* wrote, it is not his
- when a reply only echoes your own text, it is agreement at most, and often
  just a pointer to the thing being discussed

Write what was actually observed and by whom. **"Consistent with M16" is a
finding. "Scott measured 16 mm" is testimony**, and testimony must have a
witness who spoke.

Related, and it compounded here: the supporting evidence was also oversold.
This row had no location while its twin did, so a homeless record matched a
homeless object — suggestive, presented as corroboration.

## A cabinet is not a location — filing at cabinet level claims a place that doesn't exist

Scott, 2026-08-22, holding an eyebolt the record said lived in B1: *"B1 is an
area, not a storage location. It's not a discrete location. How do I store
something in B1? That doesn't make sense."*

He is right, and 49 rows had the problem — 32 in B1, 17 in B2. Both cabinets
have 44 drawers each and **zero** rows in any actual drawer.

The state came from the McMaster import, which knew the cabinet but not the
drawer and refused to invent one. That decision was correct and should stand: a
guessed drawer reads as knowledge and sends people to the wrong place. The
mistake was leaving the result **indistinguishable from a filed row**. A
cabinet-level location renders exactly like a drawer-level one, so the record
claims the item is put away when nothing physical corresponds to it:

- **Retrieval fails** — "it's in B1" means opening up to 44 drawers
- **Put-away has nowhere to go** — you cannot place an object into a container
  of containers
- **Counting cannot proceed** — there is no drawer to open and verify

All 49 now carry `DRAWER UNKNOWN` in their notes, so one query finds them and
nobody mistakes the state for filing:

    StockItem.objects.filter(notes__contains='DRAWER UNKNOWN')

**The general rule: a location that cannot be physically occupied is not a
location, it is an address prefix.** Filing to one is a legitimate transitional
state — better than inventing a drawer — but it must be *visibly* transitional,
or it silently converts "we haven't looked yet" into "it's put away".

Same shape as the other members of this family: `[ESTIMATE]` versus a count,
VERIFIED EMPTY versus a drawer with no rows, and a zero with no note. Each time,
the value is fine and the **undeclared confidence** is the defect.

## The system's size is not the part's size

A ball valve was recorded as **1/2in** because Scott said it fits the PRIMEFIT
1/2in x 100ft nylon tubing kit. It is **3/8in**.

The inference looked safe and was not. An air system runs more than one tube
size — a 1/2in main feeding 3/8in branches and 1/4in drops is completely
ordinary plumbing. *"It belongs to the 1/2in kit"* never implied *"it is a
1/2in fitting"*, and the kit's headline number is the size of its **tubing**,
not of every fitting sold alongside it.

Same shape as reading a pack quantity off a SKU, or a material off a listing
title: **a number that is nearby and plausible is not the number you were
looking for.** The tell is that the figure came from something *adjacent* to
the object rather than from the object.

This one part collected four corrections, and every single one came from Scott
holding it rather than from any record:

1. Logged from a photo as an "air chuck / ball valve assembly" — no chuck
2. Asked for its NPT port size — push-to-connect has no thread, it is sized by
   tubing OD
3. Recorded 1/2in from the kit — it is 3/8in
4. Recorded as one — there are two

Nothing here was retrievable from a document. Every fix required someone to
pick the thing up, which is the argument for asking during a drawer walk rather
than reconstructing afterwards.

## `pathstring` is a cache — a queryset update moves the row and leaves it lying

Re-parenting the Air System bin onto `WS2-S5` with
`StockLocation.objects.filter(...).update(parent=s5)` **worked** — `parent_id`
was correct immediately. But `pathstring` still read
`SLN/Storage/WS2/Air System`, and `MPTT.rebuild()` did not fix it either.

`pathstring` is a **denormalised cache**, recomputed in `save()`, and the model
exposes `construct_pathstring()` which returns the truth. So after a queryset
update the tree is right and **everything that reads a location is wrong** —
displays, searches, reports, and any script matching on
`location__pathstring__startswith`.

That is a worse failure than the write not landing at all. A failed write is
visible; this one silently splits the record into a correct half and a stale
half, and the stale half is the half people look at.

    # after any queryset update that changes parent:
    for l in StockLocation.objects.all():
        if l.pathstring != l.construct_pathstring():
            StockLocation.objects.filter(pk=l.pk).update(
                pathstring=l.construct_pathstring())

Audited all locations when this surfaced: exactly one was stale, the one just
touched. Worth re-running after any bulk re-parent.

**The general rule, and it is the same one as `.save()` reporting success while
writing nothing: verify the field you will later READ, not the field you
wrote.** Writing `parent` and checking `parent` proves nothing about the
pathstring every query depends on.

Note this is a *different* fault from the false alarm on 2026-08-21, when
pathstrings looked wrong only because of a `[:40]` truncation in debug output.
That one was withdrawn. This one is real, and the difference is that
`construct_pathstring()` disagrees with the stored value.

## Record USABLE dimensions — an exterior figure answers a different question

The NewAge cabinets went in as **28 x 14 in**, straight off the manufacturer's
page. Scott: *"the twenty-eight by fourteen is outside measurements, which are
not useful. It should say usable space."*

Two different questions, and only one of them ever gets asked of an inventory
system:

| Figure | Answers |
|---|---|
| **Exterior** | does the cabinet fit the wall / the truck / the space |
| **Usable** | does my box fit the cabinet |

A storage record exists to answer the second. The first is a purchasing number
and belongs, at most, in a note.

Worse than useless, it is misleading by subtraction: a 28 in cabinet has a
**24 in** clear opening — four inches of side walls, frames and door swing that
no arithmetic on the exterior would have predicted, because the loss depends on
the door style. Anyone sizing a 26 in box to a "28 in cabinet" buys a box that
does not go in.

**Never derive an interior from an exterior.** An estimated `interior_d` sitting
in the same record as a measured `usable_w` reads as though both were measured —
a guess wearing a measurement's clothes, which is the same failure as
attributing a measurement to someone who only quoted you. Record the source per
figure: MEASURED, or UNKNOWN. Not "estimated from the outside".

The bin-wall drawers already do this correctly — `metadata.size` there is
interior capacity, which is why drawer-fit questions can be answered from the
data and cabinet-fit questions could not.

## Dimensions tell you what fits, not what you can get back out

The NewAge wall cabinets measure 24 x 12.75 in usable, so two 11.6 in bins
obviously "fit". They do not work. **Door hinges intrude at both sides of the
opening**, so a bin sitting at the extreme left or right cannot be lifted
straight up and out — and nothing in the width figure says so.

Scott's fix is to use **three** bins rather than two: the centre one has no
hinge near it and comes straight out, leaving a void the side bins can slide
into and angle out through. The middle bin is the key to the other two.

**Packing and access are different problems, and only one of them is
arithmetic.** A layout can be dimensionally perfect and physically unusable:
hinges, door swing, a shelf lip, an overhanging rail, or simply not being able
to get fingers down the side of a snug bin. None of it appears in W x D x H.

So when sizing to a container, ask both questions:

- **Does it fit?** — arithmetic, answerable from the record
- **Can I get it out one-handed, with the others still in place?** — geometry
  of the *opening*, answerable only by trying it

Recorded on LW1-LW3 as `hinge_intrusion` alongside the dimensions, because the
next person sizing bins will read the numbers and reach the wrong answer
otherwise — the numbers are right and the conclusion is wrong.

Related: Scott measured 12 3/4 and said *"I wanna call it thirteen, but I don't
dare."* Recorded as 12.75 with a note that it was rounded DOWN. A dimension
rounded toward caution should say which way it was rounded, or the next person
re-rounds it in the other direction and loses the margin twice.

## The proxy-for-the-thing trap — four instances in one day

A number that is *near* the thing you care about, and plausible, and wrong.
Each of these was individually reasonable and each produced a confident false
answer on 2026-08-22:

| Took | Actually needed | Result |
|---|---|---|
| the 1/2in tubing **kit's** size | the **valve's** size | it is 3/8in |
| the listing title's **"Plexiglass"** | the **box's** material | it is PET, not acrylic |
| the cabinet's **exterior** 28 x 14 | the **usable** opening | 24in, not 28 |
| the **ZIP centroid** 03820 | the **actual address** | Newington, not Somersworth |

Add the pack-count read off a SKU (`X100` was the length) and the shank size
attributed from a quoted table, and it is six.

**The tell is always the same: the figure came from something ADJACENT to the
object rather than from the object.** A kit it belongs to, a listing that sells
it, an enclosure around it, a postcode containing it, a part number describing
it. Adjacency makes the number feel like evidence — it is genuinely *about*
something real, just not the thing being asked about.

Before recording a dimension, quantity or material, ask: **did this come off
the object, or off something near it?** If the latter, mark it derived and name
the source. Two of these were caught only because Scott had the part in his
hand, which is the argument for asking during a walk rather than reconstructing
afterwards — and one was caught because he knew a road better than a geocoder.

## A closed drawer is not an empty drawer

Scott photographed cabinet A2 with ten drawers pulled and said *"only the ten
doors that are pulled out have anything in them, and you should know all about
it."* That is an owner's direct statement about his own shop, and it was still
one short: **A2-R2C1 is occupied** (hex bolts + nyloc nuts) and was closed in
the photo.

The reading of the photo was correct. The inference from it — closed therefore
empty — is what failed. Pulling a drawer is a deliberate act, and the ten pulled
were the ones Scott had opened *for the walk*; an eleventh he had filled the day
before did not get opened, because nothing about it needed showing.

**A photograph plus a sweeping statement is still a photograph.** The existing
rule says photographs show identity, not quantity — this extends it: they do not
show ABSENCE either. Sixty-four closed drawers and one sentence look like total
coverage and are not.

**What caught it:** the stock record disagreed, and the disagreement was
surfaced as a question instead of resolved by picking the more recent claim.
Had "only the ten pulled" been trusted over the record, `A2-R2C1` would have
been marked VERIFIED EMPTY on top of live stock — deleting a true record in
favour of a plausible summary. `mark_empty.py`'s refusal to touch a location
holding stock is the backstop, and it would have held even if the question had
not been asked. Both layers earned their keep; neither should be the only one.

**Practice: when a walk contradicts the database, the walk does not
automatically win.** Recent observation usually beats a stale record, which is
why the temptation is real. But a record was also written by someone looking at
the thing, and the failure modes differ — records go stale, walks miss what is
closed. Ask. Scott's answer here was *"r2c1 is also occupied correct, I'll take
one more trip thru a2 to verify"*, and 53 drawers stayed unmarked until that
trip rather than being marked on a summary.

## The B wall is sorted by thread system, and it WAS written down

B1 holds 31 McMaster rows, **all metric, zero imperial**. B2 holds 17, **all
imperial, zero metric**. Not one part crosses.

**This entry originally said nobody had recorded that. That was false.** B1's
own description reads *"METRIC fastener cabinet (Scott, 2026-08-21)"* and B2's
reads *"IMPERIAL fastener cabinet"* — written the previous day, on the exact
two cabinets under discussion. The fact was not undocumented; it was unread.

Which makes the failure worse, not better. An undiscovered convention is bad
luck. A convention sitting in the `description` field of the record you are
proposing to reorganise is a failure to look.

Three separate layout proposals were argued on 2026-08-22 — hardware to A1+B1,
hardware to A2+A1, hardware to B1+B2 — and **all three would have broken it**,
because none of them knew it was there. The discussion was about cabinets and
drawer sizes; the actual structure was about threads.

**Before proposing a reorganisation, READ THE DESCRIPTION OF EVERY CONTAINER
you propose to change.** Not a query over contents — the container's own note,
which is where the previous session left its reasoning precisely so the next
one would not re-derive it. Three cabinet-level descriptions would have taken
one query and settled the whole argument.

The tell that something was missing: every proposal treated "hardware" as one
undifferentiated category, which is an assumption the shop's owner would never
make. When a proposal needs the domain to be simpler than the person you are
talking to knows it to be, the model is wrong, not the domain.

Consequence worth acting on: A2's eleven hardware drawers are entirely
imperial, so their home is B2, not A1.

## Contents recorded, drawer not — a third state between known and unknown

48 McMaster rows sit at CABINET level in B1/B2 with no drawer assigned. A
drawer-level query sees empty drawers; a cabinet-level query sees 48 stocked
rows. Both are correct and they disagree, which produced the claim that "15
large drawers hold things with no record at all" — wrong, and it made a
matching job sound like a cataloguing job.

**"Unlocated" is not "unknown".** The parts, quantities and McMaster numbers
are all on file; only the drawer is missing, and the drawers carry Brady
labels. That is a worksheet, not a survey. `docs/b1-b2-worksheet.md` is
generated for exactly that pass.

When reporting coverage, say which granularity the number is measured at.
"B2 is empty" meant "no drawer in B2 has stock assigned to it" and was read as
"B2 is empty", which is how a 17-row cabinet disappears.

## Software that lives only on the server falls out of the world

Scott asked whether "our binscan app" could help with the B1/B2 walk. Nothing in
`~/code` matched — not the name, not a deleted file, not a commit message. The
only trace on this laptop was `~/Downloads/httpbinscan.internal.png`, a
screenshot of Safari failing to reach it.

It is real. `/Users/scottdube/binscan` on the Mini, FastAPI under uvicorn on
8002, Caddy in front, `com.binscan.plist` keeping it alive, thirteen logged runs
with measured accuracy. **It has no git repo, no remote and no backup**, and its
version history is three files named `app.py.prelog`, `app.py.prepicker` and
`app.py.prewrite`.

**Anything not in a repo is invisible to the next session, however real it is.**
This project's whole premise is that `CLAUDE.md` and `docs/` let a session start
where the last one ended. A tool that exists only as a running process on
another machine is outside that mechanism entirely — it cannot be greped, it
does not show in `git log`, and it survives only in the memory of whoever built
it.

**The tell was the phrasing.** "Our binscan app" is a possessive about something
built together, and the right response to not finding it is to widen the search
to the whole machine and the network, not to conclude it does not exist. The
first answer given was "no bincheck app exists anywhere" — technically true of
the misheard name, and useless.

**Practice:** when a service is stood up on the Mini, put its source in a repo
the same day, and record host, port, launchd label and state paths in a doc.
`docs/binscan.md` does this retroactively. Check for other unrepo'd services:
`com.shopstatus.plist`, `com.open-webui.server.plist` and the `photo-frame`
agents are all running from LaunchAgents and may have the same problem.

## Three fields, three silent refusals — and the confirming count that vanished

Scott counted 50 washers into B2-R3C8 against a purchased 50, filed it, and the
grid still showed it uncounted. The notes said `COUNTED at 50 by hand`. The
`[ESTIMATE]` flag was correctly off. And `stocktake_date` was `None`.

Three attempts to record "a human counted this", all failing without an error:

| route | what happened |
|---|---|
| `PATCH /api/stock/<pk>/ {"stocktake_date": ...}` | **HTTP 200, field unchanged** — it is `read_only` on the serializer |
| `PATCH /api/stock/<pk>/ {"metadata": ...}` | **HTTP 200, field unchanged** |
| `PATCH /api/stock/<pk>/metadata/` | **403 CSRF** for a token client |
| `POST /api/stock/count/` | works — but is a **NO-OP when the counted figure equals the stored one** |

**A count that CONFIRMS the existing number was the one case that could not be
recorded**, and it is the most valuable kind: it is the only thing that turns a
purchased figure into a verified one. Every count that *changed* something
recorded fine, which is why this survived several drawers before surfacing.

**Two of those routes returned 200 and did nothing.** That is this install's
signature failure — the same shape as `.save()` reporting success and writing
nothing. The rule already in CLAUDE.md is verify every write by re-read, and it
worked here only because the verify step was checking the wrong thing at first:
it confirmed location and quantity, both of which HAD landed.

**Practice: when a write must record a FACT rather than a VALUE, verify the fact
you meant to record, not the fields that happened to change.** `assign` now
re-reads and refuses if counted-ness did not land.

Notes turned out to be the only writable channel, so the marker
`binscan <date>: filed into <drawer> and COUNTED at <n> by hand` is the
authoritative record, and `scripts/sync_stocktake.py` mirrors it into the real
`stocktake_date` through the ORM, which the serializer does not gate.

## A 500 after a partial write leaves the write

`/api/newpart` created the part, then created the stock row, then built its
response — and threw `AttributeError: 'list' object has no attribute 'get'` on
the last step, because `POST /api/stock/` returns a **list** while
`POST /api/part/` returns a dict. The caller saw a 500 and a Safari
`SyntaxError` (an HTML error page where JSON was expected). The part and its
stock row were already in the catalogue.

Scott tried twice and left two orphan parts; a test of mine left a third. All
looked like failures.

**A 500 means the request failed, not that nothing happened.** The endpoint had
verified the part landed, verified the stock row landed, and then died
formatting the answer — the most misleading possible place, because everything
it was supposed to do had succeeded.

Two guards now: `_one()` normalises list-or-dict responses at the boundary, and
both writes are checked for a `pk` rather than assumed. But the durable lesson
is for the CALLER: after a 500 from an endpoint that writes, **go and look**.

Related: this API returns a list from one POST and a dict from another with no
signal which. Normalise at the boundary, never at the point of use.

## Descriptions accumulated a state stamp per state

Marking a mixed drawer empty produced:

```
VERIFIED EMPTY 2026-08-22 — previously labelled: PRE-SORT 2026-08-22 — mixed,
not itemised: 5/16 socket head cap screw [6 x 2-7/32 x 1-9/16 in, small]
```

Each state wrapped the previous one, burying the actual human label and pushing
the size annotation to the end where the guards that parse it would eventually
miss it. **"Previously labelled" must mean the human's label, not the app's own
last opinion.** `_strip_stamp()` removes any prior stamp before writing a new
one, so a description carries at most one state plus the original text.

## A correct reading turned into a confident wrong answer

Scott photographed a Home Depot Everbilt box of stainless hex nuts. The model
read it **perfectly**: *"cardboard box with orange and black retail label
containing stainless hex nuts in plastic packaging"*, legibility "clear", UPC
and product code transcribed. binscan then proposed a **nylon sleeve bearing**,
and had done the same thing an hour earlier, which is why B2-R4C8 needed
reversing.

Nothing was wrong with the vision. Three faults in the matcher, compounding:

**1. It matched on `descriptors`.** That field's own prompt says it is *"the one
place you may say what you see rather than read... treated as a weak hint, never
as proof"* — and `match_reading` then weighted it identically to transcribed
text. Prose about packaging cannot identify a fastener. Descriptors are now
displayed to the user and never scored.

**2. It would propose a match with no thread size.** Type, length and finish are
each shared by dozens of rows; the thread is the only attribute that narrows to
something worth showing. A match now REQUIRES a thread designation or a tag, and
returns `no-thread-read` otherwise — which the UI handles well, because "no
candidate" routes straight to the filter and the create path.

**3. A bearing could not disagree with a nut.** `_kinds()` had no entry for
bearings, so one side of the comparison came back empty and the wrong-type
penalty never fired. **A vocabulary that only knows the right answers cannot
detect a wrong one** — the absence of a term reads as agreement.

The first fix was to add the missing words: bearing, bushing, spacer, o-ring,
clip, rivet, anchor, pin, terminal, connector. **That fixed one case and left
the next one waiting.** Within the hour the same box of hex nuts matched an
`18-8 Stainless Steel Threaded Rod, 3/8"-16` — because "threaded rod" was not in
the list either. Thread agreed, finish agreed, and the type could not object.

**Enumerating the vocabulary is the wrong shape of fix.** The rule now: if the
label names a type and the row's type is UNRECOGNISED, that is a penalty, not a
pass. An unknown type cannot corroborate a known one. A 3/8-16 stainless nut and
a 3/8-16 stainless rod agree on every attribute the matcher can parse and are
not remotely the same object — so the attributes it *cannot* parse have to count
against a match, not for it.

The pattern across all three: **each fault converted "I could not tell" into "I
am fairly sure".** That is the same direction as the missing 13 TPI, where a
part whose thread failed to parse could not disagree with the label. A matcher
must fail toward silence.

## "rod" is inside "product"

The hex-nut box kept matching a threaded rod even after the wrong-type penalty
was fixed twice — once by adding bearings to the vocabulary, once by making an
unrecognised type disagree rather than abstain. Both fixes were correct and both
were firing. They were being outvoted.

The Everbilt label carries the line **"THIS PRODUCT IS APPROVED FOR USE WITH
A.C.Q. WOOD PRODUCTS"**, and `_kinds()` matched terms as plain substrings. `rod`
is inside `product`. So the label was tagged **both** `nut` and `rod`, the kind
sets intersected on `rod`, and a box of hex nuts scored **+3 for agreeing** with
a threaded rod — enough to outweigh the −5 nut/not-nut penalty that was working
exactly as designed.

Now `\brods?\b`, word-bounded, with the trailing `s?` so the label's HEX NUTS
still matches the catalogue's Hex Nut.

**Two lessons, and the second is the expensive one.**

Substring matching on short domain words is unsafe against real-world text. Not
laboratory text — *retail packaging*, which is mostly legal boilerplate,
addresses and warnings. `pin` in `shipping`, `key` in `monkey`, `nut` in
`walnut`: the corpus a label scanner sees is far messier than a part catalogue.

And: **three consecutive fixes to the same symptom, each correct, none
sufficient.** The first two were verified against synthetic test rows that
contained no boilerplate — so they passed, while the real input still failed.
When a fix is verified and the symptom persists, the next move is to reproduce
with the ACTUAL input, not to reason about the code again. `log.jsonl` had the
exact reading recorded from every one of Scott's attempts, and reading it took
one query and found the cause immediately.

## queryset .update(parent=) moves the row and lies about it

Moving `Kit - EMGTMS` back to the LRD root with
`StockLocation.objects.filter(pk=471).update(parent=lrd)` set `parent_id`
correctly — and left the location reporting its OLD path. Worse, it looked
convincing:

```
parent_id = 2          <- LRD, correct
level     = 2          <- stale, should be 1
pathstring = LRD/LRD Storage/Kit - EMGTMS ...
construct_pathstring() = LRD/LRD Storage/Kit - EMGTMS ...
```

**`construct_pathstring()` walks the MPTT ancestors, not `parent_id`**, so it
agreed with the stale tree and the usual repair — recompute the pathstring —
recomputed the wrong answer. Two independent-looking checks both confirmed a
move that had not happened, because both read the same stale source.

`.update()` bypasses `save()`, and MPTT maintains `lft`/`rght`/`level` in
`save()`. The FK moves; the tree does not.

**Move locations with `obj.parent = x; obj.save()`.** Where the FK has already
been corrupted this way, moving it somewhere else and back forces MPTT to run:

```python
k.parent = wrong_place; k.save()   # makes the tree agree with the bad FK
k.parent = right_place; k.save()   # then move it properly
```

Related and previously recorded: after any re-parent, verify with
`pathstring == construct_pathstring()` **and** check `level` against the actual
depth. Agreement between those two alone proves nothing when both derive from
MPTT.

## Location names are not unique, and every lookup took the first match

`Receiving` exists at both SLN and LRD. InvenTree does not enforce unique
location names — no `unique=True`, no `unique_together` — and BinScan resolved
locations with `name=<x>` then took `[0]`, in six places including every write
path.

Nothing had gone wrong yet because the only duplicate was unreachable. It was
about to: Scott's first instinct for the Florida uppers was "Cabinet 1", which
becomes `C1`, and SLN already has `C1 C2 C3` reserved for the row below B. Two
`C1`s, one of them a write target.

**A name that matches twice is not a location.** `resolve_loc()` now refuses
rather than picking, and takes an optional site to disambiguate; the client
sends the current site with every lookup and every write.

The naming convention avoids the situation anyway — `UCab1`, not `C1` — but the
guard matters more than the convention, because the convention only protects the
names somebody thought about.

## Built for the walk, not for the steady state

Scott opened A2-R1C1 knowing the real count and found nowhere to type it. His
verdict: *"That seems like fundamental functionality for a bin scan tool.
Right? We need to be able to adjust counts."*

Correct, and the omission has a shape worth naming. **Every path in BinScan was
built around the WALK** — the one-way journey from *unseen* to *identified* to
*filed*. Identify, pick-by-hand, create-a-part, mark-empty, mark-mixed,
auto-advance: all of them assume the drawer has not been done yet.

A drawer that is already filed and merely has the wrong number is the **steady
state**, and it is what the tool does for years after the walk ends — the walk
is a few weeks. It had no path at all.

**The bias: a tool designed while doing a migration gets built for the
migration.** Every session was spent walking drawers, so every feature answered
a question that comes up while walking. The question that comes up afterwards —
"this says 50 and there are 47" — never arose during construction, and so was
never built.

Fix: every filed row in the "On record" panel now carries a **Count it** /
**Recount** control. Recording the same number again is still a count; it turns
the purchased figure into a verified one, which is the single most valuable
thing the tool can record.

**Worth asking of anything else built here: what does this look like once the
migration is over?**

## Deciding which kind of evidence you were given, instead of asking

The 100 lag screws split across A2-R1C1 and A2-R1C2 were recorded as
`[ESTIMATE]` per drawer, on the reasoning that Scott had *confirmed* a 50/50
split I proposed rather than *reported* one — a weaker tier of evidence, and the
distinction that had gone wrong with the eyebolt the same morning.

He had counted them. *"I counted it. I told you that much earlier today."*

The distinction is sound and worth keeping. Applying it **by inference** is not.
Asked "is that a count or a confirmation?", he would have said count in four
words. Instead the caution was applied silently, two drawers were flagged as
estimates for a day, and the correction cost more than the question would have.

**Guarding against over-claiming can itself become a claim.** Recording
"confirmed, not counted" asserts something about how the number was obtained,
and that assertion needs the same evidence as any other. When the person is
right there, ask; when they are not, record the ambiguity as ambiguity rather
than resolving it toward caution.

## A description that says "empty" is not a description that names contents

The mark-empty guard refuses when the drawer's description names something, on
the sound principle that *"no rows" is not evidence of emptiness* and the
description is often the only place the contents were ever written.

It asked the wrong question. It tested whether there was **any text**, using
that as a proxy for **text that names contents**. Those are different, and the
gap swallowed a third of a cabinet.

Scott, mid-walk on A3, 2026-08-23: *"1.2 wont allow me to mark it empty."*
A3-R1C2's description reads:

> Reported AVAILABLE by Scott 2026-08-21 — "most of A3 is empty; the two bottom
> rows have stuff in them". A cabinet-level statement, not a per-drawer check:
> glance in before filling.

That is a **claim of emptiness**, and the guard read it as evidence of
contents — the exact opposite of what it says. Measured across the cabinet:
**31 of A3's 64 drawers would have refused the same way**, carrying one of two
bulk statements written on 2026-08-21 (`Reported AVAILABLE`, 15 drawers;
`Reported EMPTY ... a bulk statement covering A3-R4C1..R5C8`, 16 drawers).

The irony is the point: **those bulk claims are exactly what a walk exists to
replace.** They are one person's cabinet-level recollection, explicitly labelled
in their own text as *not a per-drawer check*. Standing at the open drawer is
the moment that upgrades them to a verified fact, and the guard blocked the
upgrade because the weaker claim had been written down.

Same failure class as the identify short-circuit already recorded here: **a
guard keyed on a proxy will eventually block the case that shares the proxy and
not the intent.** There, the proxy was "the drawer has stock" standing in for
"you meant to estimate". Here it was "there is text" standing in for "the text
names contents".

`_names_contents()` now distinguishes them: a body matching
`^(REPORTED )?(AVAILABLE|EMPTY|VERIFIED EMPTY|PRE-SORT)` claims emptiness and
does not block.

**A second bug was hiding behind the first, and would have been silent.** The
stamp was built as `VERIFIED EMPTY <date> — previously labelled: <old>`,
truncated by the stamp builder's own `[:250]`. **That 250 is the code's
choice, not a database limit** — measured 2026-08-23, a `StockLocation`
description accepted 308 characters and re-read intact. Those A3 descriptions
plus their bracketed size run past 250, and **truncation falls on the end of
the string, which is exactly where the size annotation lives** — so preserving
the claim would have quietly eaten the dimensions off 31 drawers. `[6 x 2-7/32
x 1-9/16 in, small]` is measured data that nothing else records.

`_empty_description()` now keeps the size annotation explicitly and **retires**
a superseded emptiness claim rather than carrying it forward. Preserving it was
wrong on its own terms too: *"glance in before filling"* is an instruction that
the verified check has just answered, and two statements of different strength
sitting side by side send the next reader to look again.

A real content label is still preserved, unchanged.

**The sibling has NOT been fixed, deliberately.** `scripts/mark_empty.py`
carries the same guard, mirrored on purpose — but it must keep refusing, and
for a reason the phone does not share: **BinScan has a human at the open
drawer; a bulk `--cabinet` sweep has nobody looking.** Relaxing it there would
convert 31 unverified claims into verified ones by fiat, which is precisely the
fabrication the whole guard exists to prevent. If per-drawer use of that script
ever needs it, that wants an explicit flag, not a looser rule.

## A kit lid can be wrong about which VALUES are in the box

The SparkFun kit established that the list loses to the object on counts and
markings. The 10-value 4x7 electrolytic kit extends it: **the lid was wrong
about the value list itself.**

Its printed table names ten rows including `22uF 16V`. Scott opened it and
counted, 2026-08-23: there is no 16V bag. There are **two bags of 22uF 25V**,
8 and 10. So the box holds **nine distinct values, not ten** — "10value" on the
lid counts bags.

Had the lid been trusted, the catalogue would have gained 8 or 10 pieces of a
capacitor that is not in the building, filed at a drawer address, looking
exactly as authoritative as the eight correct rows beside it. Nothing later
would have contradicted it: a wrong quantity gets caught by the next count, but
**a wrong VALUE is never counted, because nobody opens a bag looking for a
value the record does not claim is there.**

Part #736 (`Capacitor Electrolytic 22uF 16V (4x7)`) stays in the catalogue at
zero stock — it may belong to one of the other two electrolytic kits — and now
carries a note saying it is not in this box, so the lid does not re-persuade
the next reader.

**Practical form: a lid photo settles what to ASK, not what to record.** It is
worth taking, because it tells you which bags should be there and which parts
already exist. What goes in the database still comes from the bags.

**And check for a vendor total before assuming a photo unblocks a kit.** The
other two electrolytic kits carry theirs on the location record ("15 values,
200 pcs"; "Xuansn 270 pcs, 18 values"). This one never had one, so the photo
resolved the values and left the counts exactly as unknown as before.

## Do not run write scripts while somebody is walking

InvenTree on this install is **SQLite** — `/Volumes/4TB_Removable/inventree/data/inventree.sqlite3`,
WAL journal, a **10-second** lock timeout. SQLite allows many readers but
**exactly one writer**, so a write from the laptop and a tap on the phone are
in direct competition for the same slot.

2026-08-23, 13:34:54 UTC: Scott pressed *Record count* on B3-R1C3 and got

    transfer failed: 500 OperationalError ... /api/stock/transfer/

with `database is locked` in InvenTree's error log. His count of 22 was
discarded. At that moment this session was running `--commit` scripts against
the same database — kit seeding, `sync_stocktake.py`, description updates.

**The cost is asymmetric and that is what makes it worth a rule.** A blocked
script fails visibly, in front of someone who will rerun it. A blocked tap
fails in a shop, on a phone, to someone with a drawer open and both hands
full — and the natural reading of a 500 is *"the tool is broken"*, not
*"try again in ten seconds"*. Worse, the count is simply gone: it was never a
row, so nothing later surfaces it as missing. Only comparing the walk against
the database found this one.

**Rule: while a walk is in progress, reads only.** Batch the writes and run
them when the walker stops, or ask first. This costs nothing — nothing about
seeding a kit or syncing stocktake dates is urgent — and the alternative is
silently eating counts that somebody physically performed.

Worth knowing for the cycle-count design too: a scheduled count and a
background enrichment job will eventually want the same writer slot, and the
overnight job already writes to this database at 02:05.

## Identify was dead for days, and the error named nothing

Scott, mid-walk 2026-08-23, photographing A3-R6C8:

    SyntaxError: The string did not match the expected pattern.

That is Safari's message for `Response.json()` handed a body that is not JSON.
It names no endpoint, no field and no variable, and it appears in the UI far
from anything that suggests a cause. The server log had the real thing:

    File "app.py", line 1522, in api_identify
        known = drawer_contents(location, site)
    NameError: name 'site' is not defined

`f25e3f0` added a `site` argument to `drawer_contents()` and updated **three of
the four call sites**. The fourth is in `api_identify`, which has no `site`
parameter — so the name was unbound, the endpoint raised, FastAPI returned a
plain-text 500, and Safari turned that into a syntax error about a string.

**The client had been posting `site` the whole time** (`fd.append('site',SITE)`).
Only the signature was missing. One line.

Two things made it survive:

- **It is a guard branch.** The short-circuit exists for a case the UI is
  supposed to prevent, so nothing routine reached it — until Scott
  photographed a drawer with one selected, which is the ordinary path.
- **Python only fails at runtime.** The module imports, the app starts, every
  other endpoint works, and the call is still wrong. A compiler would have
  refused the file.

`scripts/unbound_names.py` now finds this class by AST: names a function reads
but never binds, with enclosing scopes and nested-function parameters handled
properly. Verified both directions — clean on the fixed file, and it flags
`'site' used in api_identify() but never bound` when the fix is removed.

    python3 scripts/unbound_names.py binscan/app.py

**Worth running before any binscan deploy.** It costs a second and covers the
gap left by having no tests.

**And the diagnostic that mattered: read the server log, not the phone.** The
first three theories here — the empty-marking change made minutes earlier, a
failed `repaint()`, a stale grid — were all built from the screenshot, and all
three were wrong. `binscan.err.log` named the function and the variable on the
first read.

## A deploy the walker cannot see is not deployed

binscan's entire client lives inside the page `GET /` returns, so **a cached
page is stale code, not a stale view.** Nothing set a cache header, and iOS
Safari holds a page across ordinary reloads.

2026-08-23: a fix shipped, the md5 on the Mini matched the laptop, the service
restarted, and the endpoint was confirmed by curl. Scott went on hitting the
old behaviour on his phone — and both of us were reading server-side evidence
as proof it was fixed. The md5 check answers "did the file land", which is a
different question from "is the walker running it".

`GET /` now sends `no-store, no-cache, must-revalidate`. Chosen over a version
query string because the page is 85 KB on a LAN and changes on every deploy;
correctness beats the round trip.

**The general form: verify the fix where the SYMPTOM was, not where the change
was.** Every check that day — parse, unbound-name scan, md5, restart, curl —
sat on the server side of the gap that was actually failing.

## The matcher searched for the two most useless strings on the label

`catalogue_matches()` shipped, and returned **nothing** for an SMA pigtail
whose part existed as #732 the whole time.

It built InvenTree `search=` queries from whole label lines, plus the two
LONGEST tokens in the reading. On that bag the longest tokens were
`cn1083961339vudae` and `9375669B5015` — the order id and the batch code, the
two strings guaranteed to match nothing. It never searched for "pigtail" or
"sma".

**Longest is not the same as most distinctive**, and on consumer packaging it
is reliably the opposite: the longest strings are barcodes, order ids and
tracking numbers.

Rewritten to fetch the catalogue once and score locally — 992 parts, the same
approach `/api/fasteners` already used — with **IDF weighting**, so a token's
weight comes from how rare it is across the corpus. "cable" appears on dozens
of parts and says almost nothing; "pigtail" appears on one and says
everything. That separation falls out of the arithmetic rather than a
hand-tuned list.

Same photo, before and after:

| | before | after |
|---|---|---|
| catalogue matches | **0** | 6 |
| #732 SMA/U.FL Pigtail 15cm | absent | **first, 11.137** |
| next candidate | — | 5.761 |

matching on `15cm, pigtail, rpsma, 8pcs, sma, cable`.

**Also: the by-hand picker only ever searched the cabinet's unlocated rows.**
Its own message admitted the hole — *"the part may still exist and already be
filed in another drawer"* — while offering no way to reach it, which is what
Scott hit typing "Sma" and getting nothing. It now searches the catalogue too,
via `/api/partsearch`, and any hit can be filed straight into the drawer.

And it **rendered nothing at all when a cabinet had no unlocated rows** — so
in a cabinet whose backlog was already filed there was no search box in the
UI whatsoever. It always renders now.
