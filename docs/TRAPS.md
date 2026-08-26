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

## A paper receipt is not a put-away

Scott, at B3-R4C8 on 2026-08-23: *"I cannot seem to find these, we marked them
as here and Amazon shows them delivered but right now theyre MIA."*

The record said two SHT31-D sensors were in that drawer. Nobody had ever put
them there. Marking **PO-0028 received** created two stock rows at their
**planned** destinations — 2 to RB-12 for the RAT GDO Florida pair, 2 to
B3-R4C8 as spares — and a plan written at receipt is indistinguishable, in the
database, from a person carrying parts to a drawer.

Both rows were `NOT COUNTED`, which is the system telling the truth in a voice
nobody hears: **the drawer was a claim, not an observation.** The colour said
"filed", and filed is not counted.

**And the line item under it was itself a guess.** PO-0028's own note:

> STUB PURCHASE ORDER — needs manual reconciliation. Amazon order confirmation
> of 2026-08-20 carries NO line items: only the order number, the category
> hint "1 Hardware item", and a grand total of $16.9…

So `SHT31-D × 4` was attributed to an order that never said what it contained,
flagged for reconciliation, and then **receiving it turned that inference into
stock at an address.** Two soft facts stacked into one hard-looking one.
Scott's recollection supports the attribution, and it remains a recollection.

**23 stub POs exist.** Receiving any of them does this.

Corrected by retracting the location rather than deleting the rows: the
purchase is probably real, so the honest state is `(NOT LOCATED ANYWHERE)` —
owned, location unknown — which 41 other rows already occupy and BinScan's
picker surfaces by name. Quantities untouched; nobody has counted these.

**The general rule: a receipt records that something ARRIVED, never where it
ended up.** Those are two events, usually minutes to weeks apart, and only the
second one is a location. Four other rows currently rest on the same footing
(PO-0134 label printer, PO-0136 Avery sheets, PO-0030 LCR tester, PO-0026
carbide insert) — all low risk, since three are in daily use, but all
unverified in exactly the same way.

**What would prevent it:** receive to `Receiving`, and let the walk move it
to a drawer. `Receiving` already exists at both sites and already holds two
items *"awaiting a home"*, which is the pattern working correctly.


## An attachment lives on the PART, and a stock item shows none

Scott, 2026-08-23, right after a datasheet was attached: *"When I look at the
part, I get the data sheet. When I look at the part in stock as a stock item,
there's no attachment, no data sheet attached. It seems like a trap."*

It is. InvenTree attachments are keyed by model — the row carries
`model_type='part'` and `model_id=<part pk>`. A StockItem has its own
attachment list, which is empty, and **nothing on that screen says the
document exists one level up.**

That matters here more than in a normal InvenTree install, because **this
shop's whole physical workflow arrives at stock and locations, not at parts.**
Scan a drawer barcode, open BinScan, follow a stock row — every one of those
paths lands somewhere the datasheet is invisible. Someone holding the part,
at the bench, in the exact moment they need the pinout, is looking at the one
screen guaranteed not to show it.

**Do not fix it by duplicating the file onto stock items.** The same document
on four rows of the same part is four things to update and three chances to
read a stale one. Documents belong to the part, which is the thing that has a
datasheet; a stock item is a quantity in a place.

**Practical rule: look up the part, not the stock row, for anything that is
about the OBJECT rather than the amount.** Datasheets, footprints, pinouts and
supplier links are part-level. Quantity, location and count date are
stock-level.

Worth considering later: BinScan already renders part names on its cards and
could surface a "has datasheet" marker with a link, since it is the screen the
walker is actually holding.

## poppler was there all along — I checked the wrong environment

Recorded as a correction, because the first version of this note was wrong and
was committed.

InvenTree's error log carried `PDFInfoNotInstalledError` from
`plugin/base/label/mixins.py render_to_png`, dated 2026-08-20. A check through
`itq` reported no `pdfinfo`, `pdftoppm` or `pdftotext`, and the conclusion
written down was *"poppler is not installed on the Mini"*.

Poppler was installed the whole time, at `/opt/homebrew/bin/pdfinfo`. **What
`itq` reports is the ssh session's PATH** — `/Users/scottdube/.local/bin:
/usr/bin:/bin:/usr/sbin:/sbin` — which has no Homebrew in it. The InvenTree
service is launched by launchd with its own PATH from the plist, and that one
**does** include `/opt/homebrew/bin`.

Tested rather than argued, by running `pdf2image` under both:

| PATH | result |
|---|---|
| the ssh PATH `itq` gets | `PDFInfoNotInstalledError` |
| the server PATH from the plist | **OK — 1 page rendered** |

So label PNG rendering works, and the 2026-08-20 errors are stale.

**The general trap: `itq` is not the server.** It runs the server's Python, in
the server's directory, against the server's database — which makes it feel
like the server and hides that the *environment* is a different one. Anything
about PATH, environment variables, or subprocesses answers a question about
the ssh session unless it is explicitly given the launchd environment.

Same shape as the deploy verified by md5 while Scott kept hitting old code:
**check the thing where it actually runs.**

## A duplicate made a day apart, and the ordering machinery chose the new one

`Brother DK-2205` label roll, resolved 2026-08-23:

- **2026-08-20** — #922 created as a placeholder: *"Stored in BR-D3.
  minimum_stock 1 so it shows on Low Stock before the last roll is in the
  printer. Quantity not counted — set it when the rolls are put away."*
- **2026-08-21** — #1054 created as *"the first tracked consumable in the shop,
  with a real reorder point"*, without matching the record made the day before.
- The supplier part and **PO-0133 then attached themselves to #1054**.

So #922 sat at zero with no purchase history while the roll it described was
on order against its twin. Scott's question was the right one: *"why is there
no PO?"* — and the answer was not "the order went untracked" but "the order
found the other record."

Brother sells the same 62 mm continuous tape as **DK-2205 and DK-22205**
depending on region, which is what let two records look like two products.

**Moving a SupplierPart's `part` FK carries its PO lines with it**, because a
line item points at the supplier part rather than at the part. That makes this
kind of merge one write rather than a hunt through orders.

## Stock that cannot be bought is not stock

#1054's only stock row was the **5 m starter roll that shipped in the printer's
box** — partially used, mounted in the machine. It had been counted honestly:
*"Counted 1 because one roll is present, not because a full roll is present."*

It still did damage. **The shop read as having label stock while owning no
usable roll**, and the minimum-stock rule on the other record was the only
thing saying otherwise. Scott, deciding it: *"I dont think so, it cant be
bought."*

That is the test worth keeping. **If it cannot be purchased, it is not a stock
item** — it is a property of the machine it came with, and it belongs on that
machine's record. The fact now lives on the printer #1057, where somebody
wondering what tape is loaded will actually find it.

## An integrity assertion can be pointed at the wrong field

The *Inventory Health Signals* brief (overnight-import project, 2026-08-24)
reports **zero records carrying `[ESTIMATE]`** and asks whether the +40%
convention is being applied at all.

It is. The marker is written to **`StockItem.notes`**, not `Part.description`.
Measured 2026-08-24 with `scripts/estimate_audit.py`: **147 rows carry it, 0 in
the field the brief queried.** (148 by substring — see below; one row mentions
the marker without carrying it.)

Note the figure. Reading the seed scripts (`seed_xuansn.py`, `seed_elec_4x7.py`,
`seed_15value.py`) gives **42** — those three kits only. The population is 148.
Inference from source would have been wrong in the same direction as the
original query, just less so; only the query got it right.

So the assertion reads zero and the reader concludes "the convention is dead",
when the convention is alive and the *check* is broken. This is the same shape
as the failure that brief exists to catch, one level up: **a query against the
wrong field returns a confident, plausible, wrong number.**

Rule: an assertion that returns zero must name the field it queried, so a zero
can be told apart from a miss. `[ESTIMATE]` lives in stock notes.

### And the correction found something worse than the error — twice

Querying the right *field* surfaced rows carrying both `[ESTIMATE]` and a
`stocktake_date`. The audit script that found them then used **`icontains`**,
which is not a marker test, and reported **3**. It is **2**.

    notes STARTS WITH [ESTIMATE]: 147      <- the marker test
    notes CONTAINS   [ESTIMATE]: 148       <- not a marker test

`#504` merely *mentions* the marker in a note recording that it was physically
counted. **This trap was already in this file** (see "the substring test found
the word in the prose describing its absence", above) and
`binscan_reset.py`/`mcmaster_import.py` already used `startswith`. The audit
was written anyway with `icontains`. Recording a trap does not prevent it; the
query has to be read.

**The two real rows point the OPPOSITE way from the guess.** The dashboard reply
read them as real counts wearing a stale label — understating progress. Their
own notes say the reverse:

    #482  "Quantity 3 is the PURCHASED figure carried in with the row -
           NOT COUNTED, nobody has looked in the drawer and tallied it."
    #556  "41 is the LISTING count, not a count of what is in hand."

They are **stamped without a count**, so the never-counted report is *over*-
stating progress and the fix is to **clear the date, not the marker**. Getting
the direction wrong would have deleted the marker on two rows nobody has ever
counted — turning a detectable contradiction into a silent lie.

### The mechanism: the stocktake mirror is one-directional

Not two bad rows. `scripts/sync_stocktake.py` mirrors binscan's COUNTED marker
into `stocktake_date` and **only ever sets it — nothing clears one.** Its regex
matches `filed into X and COUNTED at N`, so a file-*without*-count is invisible
to it.

So: a row is counted (date stamped), then later re-filed without being counted.
`binscan/app.py` prepends a fresh `[ESTIMATE]` note — it rewrites the marker on
the *prior* note only when a count is supplied — and the stale date survives.
Both #482 and #556 carry a `PURCHASE HISTORY (superseded by the count above)`
fragment underneath, which is the fingerprint of exactly that sequence.

The fix is to make the mirror **reconcile in both directions**: set the date
when the note claims a count, clear it when the leading claim is `[ESTIMATE]`.
The note marker is already the authoritative record — `sync_stocktake.py` says
so in its own docstring — so the date should follow it down as well as up.
The script already refuses to stamp a date onto a quantity nobody counted; this
is the same conservatism pointed the other way.

## Coverage percentages need the reachable denominator

Image coverage read 563/1071 = 52% and looked like two years of work. Roughly
483 of the missing are delisted, login-gated, or carry synthetic SKUs; only
~25 are actually obtainable. Against the moveable denominator the same shelf is
563/588 = **96%**, and the remaining work is about a week.

Both numbers are true. Only the second one supports a decision. Any completeness
figure on a dashboard shows reachable, and shows the ruled-out count next to it
so the exclusion can be audited.

## The `[ESTIMATE]` count is 148, not 42 — and 3 of them contradict themselves

Measured 2026-08-24, confirming and extending the note above. The correction
about the field is right: `[ESTIMATE]` lives in **`StockItem.notes`**, and my
health-stats query hit `Part.description`, which reads 0. That query is fixed
in `scripts/health_stats.py`, and it now **prints the field it queried** so a
zero can be told apart from a miss.

Two things the earlier note understates:

**The real count is 148 stock rows**, not the 42 seeded by the three
electrolytic scripts. The convention is applied far more widely than a scan of
those seed scripts suggests — it reaches the resistor kits and much else. Do
not size this from the scripts you happen to know about; query it.

**3 of the 148 carry BOTH `[ESTIMATE]` and a `stocktake_date`**, which the
convention says is impossible: a counted figure carries the stamp, a reasoned
guess does not. Either the count happened and the marker was left behind, or
the stamp was applied to a guess.

```
stock #482  92015A122 18-8 Stainless Cup-Point Set Screw   qty 3   stamped 2026-08-22
stock #504  93412A423 Viton Fluoroelastomer Seal           qty 10  stamped 2026-08-21
stock #556  Terminal Removal Tool Set, 41pc                qty 41  stamped 2026-08-22
```

All three were stamped during the 08-21/08-22 drawer sessions, so the likely
story is that they *were* counted and the marker was never cleared — which
means three real counts are being reported as guesses. Worth resolving by hand:
if counted, drop the marker; if not, drop the stamp.

**The generalisable rule** — and it is the same shape as the failure the
*Inventory Health Signals* brief is about, one level up: an assertion that
returns zero must name the field it queried. A wrong field returns a confident,
plausible, wrong number, and zero is the most convincing wrong number there is.

## Shop (shop.app) is the missing itemised source — verified endpoint, unfinished parser

Measured 2026-08-24. Scott asked whether the Shop app has an API worth using.
It effectively does, and it is a better source than vendor email.

**Verified, end to end:**

- The automation Chrome is **already signed in** as Scott Dube — no login step.
- `shop.app/account/order-history` is the route (`/orders` is a 404).
- **`shop.app/account/order-history.data`** is a session-authenticated
  structured endpoint — Remix single-fetch, `turbo-stream` encoded, ~10 KB.
- Its keys include exactly what a PO line needs: **`lineItems`,
  `productTitle`, `sellerName`, `effectiveTotalPrice`, `totalItemCount`,
  `currency`, `status`, `date`**.
- It **aggregates every vendor, not just Shopify merchants** — Amazon,
  AliExpress and carrier-tracked shipments all appear in one list.
- Confirmed real content pulled from it: a `productTitle` of
  *"Hi-Link 5W 5V 1A Low Cost Sol…"* — an AC-DC power module, i.e. exactly the
  kind of part the email sweep cannot itemise.
- MFC Machining & Design Services appears under **Installments** ($94.98, 3
  payments remaining), which is why it was not in the order-history list view.

**Two constraints on how to use it:**

1. **Parse in the page and return only extracted fields.** A bulk fetch of the
   raw payload is refused by the browser tool as cookie/query-string data — and
   that is the right shape anyway: never move session material to the Mini.
2. **The turbo-stream decode is NOT finished.** The format is a flat array
   where `{"_1":2}` means *key = flat[1], value = flat[2]*, and deferred data
   arrives on a later line prefixed `P<n>:`. That much is confirmed. A naive
   resolver still mis-pairs keys to values (it produced
   `formattedEtaDateAndTime: "Hi-Link 5W…"`), so **do not trust a regex or a
   half-working resolver against this** — a mis-paired field would write a
   delivery date into a product title and look plausible. Use a real
   turbo-stream decoder.

**Why this matters.** `vendor_triage.py` solves *discovery* — it finds that a
purchase happened and who from. It does not solve *itemisation*, so an unknown
vendor still yields a stub PO. This endpoint is the itemisation half, for every
vendor at once.

**Rule 3 still applies.** The order list contains medical items. Any harvester
must redact them by seller before anything is written or logged.

## It is 2 contradictions, not 3 — and they point the OTHER way

Fourth wrong number about this one field in 48 hours, and the same root each
time: **a check that did not name what it queried.**

`notes__icontains("[ESTIMATE]")` returns 148. `notes__startswith("[ESTIMATE]")`
returns 147. The extra row is **#504**, whose notes read *"Counted 10 on
2026-08-21 — a physical tally, not the pack claim"* and merely **mention** the
word later in the sentence. A substring match on a marker is not a marker test.
`binscan_reset.py` and `mcmaster_import.py` already use `startswith`; the audit
and the health brief both used `icontains`. Use `startswith`.

**The two real ones point the opposite way from the guess.** The dashboard reply
read them as "probably real counts still wearing an estimate label", which would
mean the never-counted report *under*-states progress. Their own notes say
otherwise:

```
#482  stamped 2026-08-22  "[ESTIMATE] binscan ... Quantity 3 is the PURCHASED
                           figure carried in with the row - NOT COUNTED"
#556  stamped 2026-08-22  "[ESTIMATE] 41 is the LISTING count, not a count of
                           what is in hand. Never used and never opened out"
```

Both are **stamped without a count** — the worse direction. The never-counted
report is **over**-stating progress by two rows, and the fix is to clear the
`stocktake_date`, not the marker.

**Mechanism, precisely.** "Nothing in the count path strips the marker" is not
quite right. `file_stock.py` *replaces* notes wholesale on a real count
(`"Hand-counted <date>."`), so that path is clean. `sync_stocktake.py:82` does
`update(stocktake_date=...)` and **never touches notes** — that is the path that
can stamp a row while leaving an estimate marker standing. Zero rows currently
carry a binscan `COUNTED at` marker alongside `[ESTIMATE]`, so this has not
fired yet at scale; it is a live hazard, not a live outage.

## The Mini is no longer bot-challenged — the laptop-fetch-then-scp dance is obsolete

**Contradicts the "Amazon image trap (verified)" section of the overnight task
file**, which states that Amazon challenges the LRD network but not the laptop,
and that image bytes must therefore be fetched on the laptop and `scp`'d over.
That was true when measured. It is not true now.

Measured from the Mini, 2026-08-24, plain `curl`, no browser:

```
amazon.com/dp/B09YHWKKTR   870,256 bytes, gzip
title                      "PATIKIL FR4 Single Side Copper Clad Laminate PCB..."
challenge wording          none
"hiRes" image URL          present
m.media-amazon.com fetch   200, 56,467 bytes, real JPEG
mcmaster.com               200, 78,418 bytes
```

**Test the content, never the status code.** The first probe returned
`200 text/html` and looked conclusive — but that is exactly what Mouser's
*defended* image host returns. What settles it is the product title and the
`hiRes` key being present, plus `file(1)` on the downloaded bytes.

**One gotcha:** Amazon serves gzip whether or not you ask. Without
`curl --compressed`, Python's `text=True` dies on `UnicodeDecodeError: 0x8b`.
That is the gzip magic byte, not a challenge.

**Consequence.** Unauthenticated image and page fetching can run *on the Mini*,
where the data already lives — no laptop round-trip, no tarball, no `scp`. The
laptop is still required for anything needing a **logged-in session** (Amazon
order pages, McMaster order history, Shop), because the session cookies live in
the browser there.

**Do not read this as "the IP is permanently fine."** Reputation is not a
setting; it drifts. The rule that survives is the one that caught it both ways:
check the content, and check what instrument you used.

## Why the Mini stopped being blocked — three candidates, and we recorded nothing

Scott's hypothesis, 2026-08-24: during the months nobody is in Florida, the only
traffic leaving that IP is this job's automated traffic. With no organic human
browsing mixed in, the shape looks purely scripted, and Amazon shut it down.

**Plausible, and a real feature of these systems** — residential IPs earn their
good reputation partly by carrying mixed human traffic, and an address whose
entire footprint is automated loses that benefit.

**But it does not explain the recovery.** Nobody is in Orlando today either. If
"no organic traffic" were the cause, it would still be the cause. The hypothesis
accounts for the block and not the unblock.

Two competing explanations that do account for both:

- **Reputation decay after we stopped.** Queue A was written off as dead for
  several days, so the hammering stopped — which is the task file's own rule
  ("repeated retries make the reputation worse, not better") read forwards.
  Defenders age out negative signals.
- **The IP simply changed.** Comcast residential DHCP. The Mini's 119-day uptime
  is irrelevant; the WAN address lives on the router.

**We cannot distinguish them, because nothing ever recorded the address.**
`scripts/wan_ip.py` now does, to `wan_ip_history.json`. First record:
`174.58.246.115`, AS7922 Comcast, Orlando FL, 2026-08-24.

**The policy is the same under all three**, so this does not need resolving to
act on: keep Mini-originated automated traffic low, paced, and monitored. But
the hypotheses diverge under load — organic-mix predicts degradation whatever
the pacing, abuse-decay predicts low paced volume stays clean. The daytime sweep
generates exactly that data, so the next block (or its absence) is evidence
rather than another guess.

## "Nothing happened overnight" has at least three causes that look identical

Scott's reading of the 2026-08-24 miss was a permission stall. Reasonable — the
2026-08-22 miss WAS exactly that, seven hours parked on a prompt. But the
transcript for 08-24 says otherwise:

```
02:05:34  scheduled task fired
02:09:01  API Error: 529 Overloaded        <- died here
08:12     Scott typed "Try again"
tool_use records before the error : 0      <- nothing to approve
records in the 6-hour gap         : 0
```

Zero tool calls means no prompt was ever raised. The run died on its first model
call.

**Three causes, one symptom.** A morning with no journal entry can mean:

1. **Permission stall** — a tool call parked awaiting approval (08-22).
2. **Transient API failure** — 529/500 on the first call, no retry (08-24).
3. **Never fired** — app closed or Mac asleep, so the task deferred to next
   launch.

They are indistinguishable from the outside, and each needs a different fix
(approvable command shapes / retry / keepalive). Ruled out for 08-24 by
measurement, so nobody re-litigates: uptime 21 days, zero sleep events since
08-20 in a log that covers today, and the app running continuously since 08-21
18:05. So (3) is out, and (1) is out on the tool_use count.

**How to tell them apart:** read the run's own transcript at
`~/.claude/projects/-Users-scottdube-code/<session>.jsonl`. The first ten
records distinguish all three in seconds — a stall shows a `tool_use` with no
result, an API failure shows an `assistant` record containing the error, and a
deferred run has a first timestamp that is not the scheduled time.

**The real gap this exposes is that nothing notices.** A 529 at 02:09 cost the
whole night and went unremarked for six hours. The dashboard brief's
"last SUCCESSFUL read, not last run" tile is exactly this, one level up: the
scheduler said the task ran, and it did — it just accomplished nothing.

## The unit string is validated, but `M` is molar and passes

Asked whether a 15 m roll could be stocked by the foot, the install said yes —
`convert_physical_value` is live on InvenTree 1.5.0 and measured correct:

```
8 in   -> 0.2032 m        2 ft -> 0.6096 m
15 m   -> 49.2126 ft      600 mm -> 0.6 m
StockItem.quantity  max_digits=15  decimal_places=5   (0.01 mm; inches exact)
```

**Case is not cosmetic and the validator will not catch it.** `Part.units`
carries a real `validate_physical_units` validator — `'roll'` and `'banana'` are
rejected — but pint is case-sensitive in the worst possible way:

| string | what pint reads | passes validation |
|---|---|---|
| `m` | meter | yes |
| `M` | **molar** | **yes** |
| `mm` | millimeter | yes |
| `MM` | **megamolar** | **yes** |
| `IN`, `FT` | undefined | no |

So `units='M'` saves cleanly and then every conversion afterwards dies with
`Could not convert 8 in to M` — a length typed into a concentration. The
failure surfaces at the bench, weeks later, on the first cut. **Lowercase, and
verify a conversion right after setting the field**, not just that it saved.

**Correction on how this was found.** The first probe called `Model.clean()`
and reported `'banana'` accepted — which would have meant the field was
unvalidated, and would have gone into this file as fact. `Model.clean()` does
not run field validators; `full_clean()` does. Same shape as the `[ESTIMATE]`
miscounts: **an integrity claim tested with the wrong instrument returns a
confident wrong answer.** Before writing down "X is not validated", check that
the thing you called is the thing that validates.

## BinScan takes fractions but not units

`float(quantity)` throughout `binscan/app.py` — never `int()` — so a fractional
quantity records fine. But it is `float()` and nothing else, so `"8 in"` comes
back as `quantity '8 in' is not a number`.

The consequence is entirely about the person at the bench: with `units='m'`, a
BinScan user holding a tape measure has to type `0.2032` for eight inches. The
InvenTree web UI converts and BinScan does not, so **the same shop has two
entry paths that disagree about what a quantity is** — which is how a cut goes
unrecorded, and an unrecorded cut is the whole failure mode of bulk stock.

Not yet fixed. The fix is small — route the string through
`convert_physical_value` when the part carries units — and it is worth doing
once, because it is the same fix for wire, solder, heat-shrink, tubing and
filament.

## A location description written as INTENT reads as fact

The two storage racks describe themselves:

```
WS1   Wire rack 1 - cable, wire, adhesives, consumables
WS2   Wire rack 2 - tubing, ducting, tape, spray bottles, bulk
```

Asked where a coil of wire sleeving should go, both were plausible — WS1 by
function, WS2 by form — so the question went to Scott. **"Most of the wire
currently resides on WS2 S3."**

So WS1's description is a *plan*. It was written when the racks were addressed
and nobody has moved the wire to match it. Anyone reading the catalogue — or
any future me picking a home for a spool — would have filed to WS1 and been
wrong, and the record would then have said the spool was somewhere it was not.

**This is the SHT31 failure one level up.** There it was a receive location: a
destination written at receipt is indistinguishable, in the database, from a
person carrying parts to a drawer. Here it is a location's own self-description:
*what this shelf is for* and *what is actually on it* look identical once
written, and only one of them can be walked up to and checked.

Recorded as an observation appended to WS2-S3 rather than by rewriting WS1,
because the split may still be what Scott wants eventually and deleting the
intent would lose that. But the general form is worth a sweep: **a location
description should say what is ON the shelf, and mark separately anything that
is merely intended for it.** The catalogue currently has no way to tell those
apart, which means every rack description is an unverified claim.

Cheap detector, not yet built: a shelf whose description names a category, with
zero stock rows of that category anywhere under it. WS1 named "wire" and holds
no wire — that would have lit up.

## McMaster login detection: the test could never have said "signed in"

**2026-08-24, measured.** Every previous "McMaster is signed out" reading was
wrong, including the one this run sent a notification about. Scott has said so
repeatedly; this is the mechanism.

McMaster's masthead ships a **static, cached shell**. On a cold page load the
account control renders the literal text `Log in` and
`localStorage.VSTR_USR_NM` is **empty — whether or not you are signed in.**
Account state is not fetched at load time at all. Measured on a genuinely
signed-in session:

| after cold load | header text | `VSTR_USR_NM` |
|---|---|---|
| 0 s | `Log in` | empty |
| 3, 6, 9, 12, 15, 18, 21 s | `Log in` | empty |

Twenty-one seconds of idle, no change. **So the sanctioned test — load the home
page and look for the account name — is not flaky. It is structurally incapable
of ever returning "signed in."** Waiting longer cannot fix it. Neither can
warming the page, which is what the previous correction ("only a positive
account-name check on a warmed page has held") assumed, and that correction is
now itself superseded.

### What actually reveals it

A **trusted** click on the masthead account control:

```
#LoginUsrCtrlWebPart_LoginLnk        (inside #ShellLayout_MastheadLogin_Cntnr)
```

That fires `UserDataLoader`, which populates `localStorage.VSTR_USR_NM` with
the account name. Then, and only then, is the answer readable.

**A synthetic `el.click()` does NOT work** — measured, no effect after 9 s. The
handler requires a real pointer event, so this must go through the `computer`
tool, not `javascript_tool`.

**Read the answer from `VSTR_USR_NM`, not from the screen.** After the real
click the key was populated (10 chars, matches `/scott/i`) while the visible
header *still read* `Log in`. The repaint is unreliable; the storage key is not.

### The corrected procedure

1. Load `mcmaster.com`.
2. Real click via `computer` on `#LoginUsrCtrlWebPart_LoginLnk`.
3. Signed in ⇔ `localStorage.VSTR_USR_NM` is non-empty **and** matches the
   expected account name.

### Why every guessed endpoint also lied

`/api/user`, `/Account/GetUserInfo`, `/order-history/api/orders` and
`/WebPartsRoot/Login/GetUserInfo` **all return HTTP 200 with the SPA shell.**
This site returns 200 + shell for *any* unknown route. That generalises the
already-documented `/order-history/` pre-auth-shell trap: on mcmaster.com,
**neither status code nor route content can ever indicate auth state.** Do not
add another route-based probe — the failure is the site's routing, not the
route chosen.

### Not verified

Whether `VSTR_USR_NM` stays empty when genuinely signed **out** — confirming
that needs a logout, which is Scott's to perform, not the job's. So the check
requires a *name match*, not merely a non-empty key: a stale or foreign value
should read as "unknown", never as "signed in".

## minimum_stock counts TOTAL stock, not spares — unless you use `belongs_to`

Scott, 2026-08-24: *"Do we wanna set minimum stocking quantity on those to
one?"* Yes — but the obvious implementation silently never fires.

`Part.is_part_low_on_stock()` compares `get_stock_count()` to `minimum_stock`,
and that count runs through `StockItem.IN_STOCK_FILTER`, measured on this
install:

```
belongs_to=None AND consumed_by=None AND customer=None
AND is_building=False AND quantity>0 AND sales_order=None
AND status__in=[10, 50, 55, 85]
```

**`belongs_to=None` is the load-bearing clause.** A stock item INSTALLED into
another stock item stops counting as stock, while still existing and still
showing what it is inside.

So for a consumable that lives fitted to a tool — desoldering nozzle, laser
nozzle, mill collet, filter — there are two models with the same number in the
same field and opposite behaviour:

| model | stock count | `minimum_stock=1` |
|---|---|---|
| nozzle row sits in its drawer while physically on the gun | 1 forever | **never fires** — and the record is a lie about location |
| nozzle row `belongs_to` the gun's stock item | 0 | fires correctly: *no spare* |

The second is also the honest one. "I own a 1.3mm nozzle" and "I have a spare
1.3mm nozzle" are different claims, and only `belongs_to` distinguishes them.
`default_location` still points at the drawer — that is where the NEXT one goes
home, and this unit simply is not a spare.

Worked example: `scripts/install_nozzle.py`. It also closed a gap nobody had
noticed — the shop's own FR-301 was a catalogue entry with **no stock row at
all**, so the gun did not physically exist as far as the data was concerned.
Installing something into a tool forces the tool to be stocked first, which is
a useful side effect.

## Part.description is 250 chars; the trigger has to fit in it

`Part.objects.create()` threw `ValidationError: Ensure this value has at most
250 characters (it has 476)` — caught, and nothing partial was written, but only
because the description was the first write in the script.

This collides with the "**write the symptom, not the specification**" rule for
tool records. That rule wants a sentence saying when you would reach for the
thing and what goes wrong without it, and there is not room for both that and
the identity in 250 characters.

`Part.notes` is an `InvenTreeNotesField` with `max_length=50000` and takes
markdown. So the split is:

- **description** — identity plus the ONE trigger phrase. This is the field that
  shows in search results, so the trigger has to be here or it never surfaces.
- **notes** — provenance, the failure mode, what is deliberately not known.

`#1084` (the FR-301 filter set) is the worked example.

## A merge pass cleaned one of a matched pair and left the twin

The 1.3mm desoldering nozzle existed **twice**, both active, both zero stock:

```
#86    good name, good keywords, and nothing else
#213   IPN B07DMWBRB9, a SupplierPart, an image, purchase history — raw name
```

The **0.8mm sibling had the identical pair** and was merged on import day:
`#214` retired into `#87`. Same product family, same Amazon order, same day —
and the 1.3mm twin was missed in that same pass.

**Which record survives is decided by evidence, not by pk order or by the nicer
name**, and here that inverts the direction of the earlier merge: `#213`
survived and took `#86`'s name. A name is one string to retype; an image, a
supplier link and a purchase history are attachments and relations, and moving
those is where a merge goes wrong. Expect a future reader to notice the
asymmetry — it is deliberate.

**The general worry is bigger than this pair.** One import produced twins, one
pass merged some of them, and nothing recorded which ones it had done. Any
other survivor from that batch is still sitting there with a live duplicate.
Cheap detector, not yet built: active parts sharing a normalised name or a
near-identical description prefix, where one has an IPN and the other does not.

## The QL-810W stopped powering up — and nothing noticed for four days

Scott, 2026-08-24: *"the label printer appears to be dead... There's no light on
the front of it. I can't get it to power up."*

Measured from the Mini before that message arrived, which is worth keeping
because it shows what the instruments say for a printer that is simply OFF:

```
ping 192.168.30.252   Destination Host Unreachable (from gateway 192.168.5.1)
631  IPP              shut
9100 raster           shut
80   web UI           shut
161  SNMP             shut
lpstat                "QL810W is ready and printing"      <- CUPS lying
```

**This is the one case the latched-error rule does NOT cover.** The recorded
trap says a red-LED latch still answers IPP with `idle` — that is how you tell a
sulking printer from a dead one. Here *nothing* answers, and all four ports are
dark together. Four dark ports plus no power LED is a power fault, not a
firmware sulk, and no amount of clearing or re-queuing touches it.

**CUPS reports the queue as printing while the printer is absent.** Job 29 sat
`active` because the connection was hanging, and `lpstat -a` cheerfully said
"accepting requests since 13:11". A queue that says *printing* is reporting on
itself, not on the printer.

**It was never a new printer — it is an Amazon *Renewed* unit, and that reframes
the whole failure.** The listing reads "Brother RQL-810W- (QL-810W) Ultra-Fast
Label Printer with Wireless Networking White **(Renewed)**". A five-day death
looks like terrible luck on a new machine and looks entirely ordinary on a
refurb, and the difference changes what you do next: you stop hunting for a
shop-side cause and you claim the guarantee.

**PO-0134 recorded the price and not the condition.** $129.99 from Amazon reads
as a new-unit price right up until you notice the word Renewed, and nothing in
the part record, the stock item, or the PO said otherwise until 2026-08-24.
**Condition is part of what a purchase record is for** — a refurb and a new unit
are different things at the same price and they fail at different rates.

The replacement, initiated 2026-08-24 and due 2026-08-26, is **also Renewed**.
Same risk, so keep the guarantee window in view rather than assuming the problem
is now behind us.

**The 90 W adapter is correct — do not "fix" it.** The genuine brick is Brother
**PA-AD-001A**, P/N **S01776A**, `100-240V 1.5A in / 25.0V 3.6A 90.0W out`,
shared across the QL-810W, QL-820NWB and the TD-2020/2120/2130 family. Ninety
watts looks absurd for a desktop label printer and reads like a mismatched
supply grabbed off the bench — it isn't. **25.0 V is the number to meter at the
barrel**, not the 12 V or 24 V you'd guess. Checked against the label and
Brother's own part listing on 2026-08-24 rather than assumed.

**But `lpstat -p <queue>` does tell the truth — read its second line.** It
prints the misleading header and then the real state:

```
printer QL810W now printing QL810W-29.  enabled since Mon Aug 24 13:11:51 2026
        The printer is not responding.          <- this line is the answer
```

So the rule is not "CUPS lies", it is **`-a` and the header line describe the
queue; the indented status line and `error_log` describe the printer.** Job 29
retries every ~37 s forever, which is why the error count climbs on its own.

**CORRECTED, same day — there was no four-day silence, and the earlier reading
of the job history was wrong.** The first pass concluded "completed jobs run
1–15, all on the setup evening; jobs 16–28 exist in neither the completed list
nor the queue." `lpstat -W completed -o` shows all 28:

```
QL810W-28   Sat Aug 22 12:39:42     <- last job the printer ever ACKed
QL810W-18..27                        Fri Aug 21, 09:56 -> 12:45
QL810W-16..17                        Thu Aug 20, 20:54 and 21:02
QL810W-1..15                         Thu Aug 20, 20:07 -> 20:42 (setup)
```

**Whatever produced the 1–15 list truncated it.** Trust `lpstat -W completed -o`
and read the whole thing; a job list that stops exactly at a round number and
exactly at the end of a session is a tell that you are looking at a page, not a
history.

**The error log dates the failure far more tightly than the job list does.**
`/var/log/cups/error_log` contains 26 error lines in its entire life and every
one of them is Job 29, starting `24/Aug/2026:13:12:13`. Nothing failed before
today. So:

- the printer served **28 jobs over two days** and was answering at Aug 22 12:39
- the death window is **Sat Aug 22 12:39 → Mon Aug 24 13:12**, ~48 h, a weekend
- it is **not** DOA, not a raster sulk, not the network — it worked, then stopped

A CUPS job going `completed` on a driverless IPP queue means the printer
accepted and acknowledged it, so it *is* a liveness signal about the printer —
unlike "the queue is accepting", which is not. It still is not proof a label came
out; **measuring an outcome is not measuring a cause**, and the monitoring gap
below stands regardless of the corrected dates.

What that *does* establish is a monitoring gap, and it is the same one the 02:09
API error exposed: **the dashboard's "last read that PROVED something" tile
belongs on the printer too.** "The queue is accepting" is a liveness claim about
CUPS. "A label came out" is a claim about the printer, and only the second one
is worth a lamp.

## The QL-810W runs on a bypass feed — what that rig is and what it is not

2026-08-24. The dead printer below was brought back the same afternoon by
**injecting 25 V onto the rear lug of the barrel jack J1**, with a soldered
pigtail and ground to a board ground point, fed from the bench supply. Back on
the network within the hour: 631, 9100 and 80 open, jobs 30-33 completed, the
`lpstat -p` "not responding" line gone.

**What this proves and what it does not.** The mainboard, printhead, WiFi stack
and CUPS path are all good — every one of them ran on the injected feed. The
break is **at or upstream of the jack's centre contact**. It was never
established whether the fault is the jack's contact spring or the adapter
itself, because the brick was never metered open-circuit. That distinction stopped
mattering once the replacement was ordered, but the record should not claim more
than was measured.

**The unit is modified, not repaired.** Case opened, two wires soldered to the
board, lead exiting the case. That has to be reversed before it goes back to
Amazon — the return runs to 2026-11-19, so there is time, but a printer that
arrives visibly hacked is a return they can refuse, and that is $129.99.

**The bench supply is now consumed** until the replacement lands 2026-08-26. If
it is needed for something else, the escape is to meter the Brother PA-AD-001A
open-circuit: at ~25 V, cut the barrel plug off and wire the brick straight to
the pigtail. The replacement arrives with its own adapter, so the cut one just
goes back in the box.

## Depleting a stock item to zero DELETES it — notes and tracking go too

2026-08-24. Asked to deplete the QL-810W's stock item ahead of the warranty
return, `take_stock(qty, user, notes=...)` took it to zero and InvenTree removed
the row outright. Not a zero-quantity record — **gone**, and the item's
`StockItemTracking` history went with it. The `notes=` argument passed to
`take_stock` describes an entry on a record that no longer exists.

The failure history survived only because it had *also* been written onto the
part earlier in the session. That was luck, not design.

**Rule: anything you want to keep about a stock item must live on the PART before
you deplete it.** Serial numbers, failure history, why it left — a stock item is
a container for a quantity, and it evaporates when the quantity does.

Also: don't trust a post-deplete re-read to confirm the write. The verification
pattern for a silent save is `objects.get(pk=...)`, and here that raises
`DoesNotExist` — which looks like a failure and is actually the success case.

## Red output on DK black/red tape is an ammeter, not a colour bug

2026-08-24, same session as the dead QL-810W below. Running the printer on a
bench supply through a bypass pigtail, the first label came out with the text and
the QR **mottled between black and red** — some QR modules black, some red, no
pattern to it. Scott: *"I had the power supply amperage limit turned way down to,
like, half an amp. As soon as I saw it print, I knew what the problem was."*

**Brother's two-colour DK tape selects colour by energy, not by ink.** Lower
energy develops the red layer, higher energy develops black. So a head that
cannot draw enough current does not print faint black — **it prints red**, and it
prints a *mix* when the burn is sitting right on the threshold and falling across
it dot by dot. Dense regions pull hardest and go red first.

**The trap is that it does not look like a power fault.** A starved head still
marks the tape and still feeds, so the failure presents as a colour or template
or driver-colour-separation problem, and that is where the hours go. Nothing in
the CUPS output complains; the job completes normally.

The rule: **on black/red tape, unexpected red is a current measurement.** Check
the supply before touching the template. Limit was 0.5 A against a head that
peaks toward 3.6 A; raising it fixed it outright.

Two corollaries worth keeping:

- **Voltage is not the thing to check first — current limit is.** The supply read
  its full 25 V the whole time. A bench supply in constant-current mode is
  perfectly happy and says nothing.
- **On a bypass or extension feed, measure at the board *while printing*.** Thin
  leads at 3.5 A of burst drop real volts, and the head sees what arrives.

A red QR is also a scanning problem in its own right: laser and CCD readers
illuminate near 660 nm and read red-on-white as blank paper. Phone cameras cope.
So a red label can pass a phone check and still be invisible to a hand scanner —
which makes "it scanned on my phone" a weaker test than it feels.

## A put-away done by a person IS a count — a PO receipt never is

Scott, 2026-08-24, on the 0.8mm nozzle: *"It's now a count. I physically counted
it. Seems like that's implied when you received something and say they're all
there and you're putting them away."*

Right, and this **sharpens the SHT31 rule rather than retracting it**. The two
events look identical in the database and are completely different acts:

| | who does it | what it proves |
|---|---|---|
| **Receiving a PO** | whoever closes the order, often off an email | an order arrived. Not a count. Not a location. |
| **A person putting it away** | somebody holding the thing | how many there are, and which drawer. Both observations. |

The SHT31 failure was the first *impersonating* the second — two sensors
recorded into a drawer nobody had carried them to. The fix was never "distrust
put-aways", it was "do not let a receipt pose as one".

**So: a put-away performed by a person who confirms the contents carries a
`stocktake_date`.** Requiring a separate counting ceremony afterwards is how a
system trains people to skip the ceremony, and then nothing is ever stamped.

This also means the earlier caution on stock #659 was wrong in the safe
direction but still wrong: it recorded "quantity 1 from the purchase record" for
a nozzle Scott had physically in his hand. Corrected — the note now says
hand-counted, and says why a put-away qualifies.

## Two functions, one identical block — and `replace(…, 1)` patched the wrong one

Adding unit conversion to binscan, the quantity-parsing block

```python
    counted = None
    if str(quantity).strip():
        try:
            counted = float(quantity)
```

appears **verbatim in both `api_newpart` and `api_assign`**. A patch script using
`s.replace(old, new, 1)` asserted `old in s` — true — and silently rewrote the
first match, which was the wrong function.

**The half-applied result was far worse than a total miss.** The *note* edit
landed in `api_assign` correctly, while the *conversion* edit went to
`api_newpart`. So `/api/assign` wrote:

```
COUNTED at 8 by hand. Entered as 8 g, converted to m.
```

for a raw, unconverted `8`. A record that says a conversion happened when it did
not is not a bug that shows up as an error — it is a **lie with a paper trail**,
and it would have read as authoritative six months later.

It also left `api_newpart` referencing `unit` and `punits`, neither of which
exists in its scope: a live `NameError` on the create-a-part-at-the-drawer path.

**Rule: assert the occurrence COUNT, not just presence.** `assert s.count(old)
== 1` would have failed loudly and immediately. Where a block genuinely appears
twice, anchor on surrounding lines that differ.

## A probe that "returns before any write" is a claim, not a fact

Verifying the above, three requests were fired at the RUNNING service against
**real stock rows**, on my stated reasoning that a validation failure returns
before anything is written. It does not. All three returned `200` and wrote:

```
stock #657  sleeve      15 m -> 8      stamped COUNTED, note "Entered as 8 furlong"
stock #659  0.8mm nozzle   1 -> 2      stamped COUNTED, note "Entered as 2 in"
```

Three invented hand-counts, on rows whose whole point was that they carried
honest provenance. Restored from the notes, which is only possible because the
notes said where every number came from — the discipline paid for itself inside
an hour.

**A write path is tested against something disposable, or it is tested in
production.** `scripts/binscan_unit_test.py` now creates a throwaway part,
stock row *and location*, drives the real endpoint, asserts, and deletes. It
also asserts the negative case actually wrote nothing, rather than assuming it.

The throwaway LOCATION matters too: the first attempt aimed at `Receiving` and
got `409 — 2 locations are called 'Receiving'`, which is the location-ambiguity
guard working. Any real drawer also risks the empty-stamp side effect rewriting
a description that took a walk to earn.

## A battery hides a dead mains supply for the whole life of the device

> **Status 2026-08-24: the general lesson stands, the specific story does not.**
> This was written from the hypothesis that the AC side never worked and the
> printer ran on battery from new. The corrected timeline — 28 jobs over two
> days, answering until Aug 22 12:39 — does not establish that, and the fault is
> now localised to at-or-upstream-of the barrel jack's centre contact. Treat the
> commissioning practice below as the takeaway; treat "that is what happened
> here" as unconfirmed.

The QL-810W printed 15 jobs on 2026-08-20 and never printed again. The AC
adapter measures **nothing**, and Scott's reading is that it never worked: the
printer ran on its internal battery from new, and died when the pack went flat.

**Nothing in that sequence ever presents as an AC fault.** The printer works,
prints, joins wifi and answers IPP — right up until it doesn't. There is no
error, no warning, no degraded mode. A battery-capable device on a dead supply
is indistinguishable from a healthy one until the battery is empty, and by then
the failure looks like "it died", not "it was never charging".

**So commissioning a battery-capable tool means proving the MAINS path
specifically.** On arrival, before anything else:

1. **Run it on AC with the battery out**, or not yet installed. If it works, the
   mains path is proven. If the battery is in, nothing is proven.
2. Only then fit the battery.

That is the entire lesson, and it costs a minute. Doing it on 08-20 would have
caught this the same evening instead of four days later.

**Two aggravating factors here, both worth carrying forward.** The unit is
**Renewed** (refurbished) — a returned item whose adapter is exactly the sort of
thing that gets swapped, lost or substituted before resale — and the replacement
Amazon is sending is **also Renewed**, so the same risk applies to it. And the
four-day gap happened because nobody tried to print; labelling was parked on the
open list, so the failure had no observer. See the "last read that PROVED
something" gap recorded above.

## Two directories named `scripts/`, and the one itq resolves against is not the one you are in

`itq run scripts/foo.py` resolves a bare relative path against
**`~/code/shop-inventory`**, always, regardless of the shell's cwd. That is the
whole point of the command shape and it is not the trap.

The trap is that **`~/code/scripts/` also exists**, holds `itq` itself, and is
tracked. So a script written to `~/code/scripts/foo.py` and invoked as
`itq run scripts/foo.py` **runs correctly** — itq goes and finds the
shop-inventory copy, or if there is none, the operator retypes the path and
moves on. The command working is not evidence the file is in the right repo.
There is no error at any point.

**FOUR occurrences now, all the same week:**

- `project_column.py` (9f1a52d, 2026-08-22) — written after the shell cwd
  silently reset, landed in `~/code/scripts/`, and was then swept into a commit
  in that repo. The documentation commit over in shop-inventory referenced the
  script while the script lived in a different repository, so the docs pointed
  at a file that was not there.
- `close_po0020.py` and `receive_sleeve.py` (2026-08-24) — same landing, caught
  as untracked before being committed, moved here.

**The `!scripts/**` allowance in `~/code/.gitignore` is not a safety net and was
never a fix.** It exists so `itq` is tracked at `~/code` level, and it is
byte-identical to when it was written in 892f4a2 — before any of these. It has
the side effect of making a misfiled script show as untracked rather than
ignored, which is what caught the second and third. It did not catch the first,
because untracked is one `git add -A` away from committed. Nothing in the
tooling distinguishes "misfiled script" from "file that belongs at ~/code
level", so do not expect the marker to hold.

**What actually catches it: read the imports.** A file that does
`django.setup()` under `InvenTree.settings` and imports from `order.models` /
`part.models` / `stock.models` belongs in `shop-inventory/scripts/`, full stop.
That test is mechanical and does not depend on remembering which cwd you were
in when you wrote it.

Worth noting how long this went unwritten: after the first occurrence it was
fixed but **not recorded** — not here, not in `~/code/CLAUDE.md`, not in the
`itq` header (whose comment block covers the permissions rationale and says
nothing about the second directory). Two days later it happened twice more.
A trap that is fixed but not written down is a trap that is scheduled to recur.

## CORRECTED — "the printer came back and the cause is unknown" was wrong

Written 2026-08-24 by a session that measured the printer alive again (ping 3/3,
631/9100/80 open, `printer-state: idle`, the 62 mm roll ready) and concluded the
mechanism was unrecorded. **It was recorded** — earlier the same afternoon, in
this same file, by the session that actually did it: *"The QL-810W runs on a
bypass feed"* above. 25 V injected onto the rear lug of barrel jack J1 through a
soldered pigtail, fed from the bench supply.

**The failure was appending to TRAPS.md without re-reading its end.** Two
sessions worked the same fault in the same afternoon and the later one wrote a
confident "cause unknown" section directly beneath the answer — the accretion
failure this file exists to catch, committed inside this file.

Practical rule: **before writing a finding here, grep this file for the
subject.** `grep -in "printer\|QL-810" docs/TRAPS.md | tail` costs a second.

Two claims from the withdrawn section:

- *"nothing has printed since 2026-08-20 20:42"* — **wrong.** The bypass
  write-up establishes 28 jobs over two days and the printer answering at Aug 22
  12:39, so the death window is Sat Aug 22 12:39 → Mon Aug 24 13:12. The 08-20
  figure came from `lpstat -W completed` alone, which listed only jobs 1-15.
- *"it may be running on the battery again"* — **ruled out.** Bench supply,
  through the pigtail.

**One new measurement to fold IN**, which the bypass write-up correctly flagged
as missing. It notes the adapter *"was never metered open-circuit"*. It has been
since: Scott metered the PA-AD-001A on a known-good outlet with the plugs
reseated and read **nothing**. That shifts "jack contact spring vs adapter"
toward the adapter — with the caveat that the meter itself was never checked
against a known source, so a wrong range or a probe missing the recessed centre
pin is not excluded. A regulated switcher does show its rated ~25 V unloaded, so
a zero is evidence, not an artifact of measuring without load.


## The two-`scripts/` trap caught a session that had already read the trap

2026-08-24, hours after the trap above was written: `move_tcrt_r2c7.py` was
created with `cat > scripts/move_tcrt_r2c7.py` while the shell cwd had silently
reset to `~/code`. It landed in `~/code/scripts/`, `itq run` executed it
correctly anyway — because itq resolves against the shop-inventory repo — and
`git add -A && git commit` then swept it into a `~/code` commit whose message
described a `docs/OPEN.md` edit that had failed with `FileNotFoundError` in the
same command.

**Knowing the trap did not prevent the trap**, because the mechanism is a silent
cwd reset between tool calls and nothing in the failing path announces itself:
the script runs, the commit succeeds, and the only symptom is a commit message
that does not match its diff.

**The countermeasure is not vigilance, it is absolute paths.** Write scripts and
edit docs by full path — `/Users/scottdube/code/shop-inventory/scripts/foo.py` —
so cwd cannot participate. A relative path is a bet on shell state that this
session lost four times.

Second-order lesson: **`git add -A` after a failed edit in the same command is
how a misleading commit gets made.** The python heredoc raised, the `&&` chain
continued to git because they were separate commands, and the commit went in
carrying a message about work that had not happened. Recovered by moving the
file to the right repo and resetting `~/code` (no remote, unpushed) — but the
message was already wrong before anyone looked.


## A counter purchase has no digital trace at all — mark it or it reads as an orphan

2026-08-24. A Walmart delivery of storage bins ran late, so Scott bought a
second set in the store and then kept the delivery too. Twenty bins, from two
purchases, and **only one of them exists anywhere outside the shop**: no email,
no portal entry, no order-details page. The vendor sweep will never see it.

This is the unknown-vendor blind spot in its hardest form. That one is *"the
sweep only finds senders it knows"* — solvable by searching for shape and
subtracting. A counter purchase has **no sender at all**, so no amount of
searching will ever surface it.

**Do not invent a purchase order for it.** A PO asserts that an order existed,
and this catalogue has already been damaged twice by POs that were really
inferences — the 23 stubs, and the SHT31 rows minted by receiving one. The
money is recordable without one: `StockItem.purchase_price` stands on its own.

**Mark it instead.** `[COUNTER PURCHASE]` opens the note, so one query finds
every such row — the same mechanism as `[ESTIMATE]`. Without the marker these
rows look like unexplained stock to any future reconciliation, and somebody
eventually "fixes" them.

Two details worth carrying:

- **Keep the lots as separate stock rows.** One is evidenced by an order page,
  the other by somebody's memory. Merging them into a single quantity destroys
  the only thing that tells them apart.
- **The +40% estimate rule does NOT apply to a price already paid.** That rule
  exists to stop under-budgeting a future purchase. Inflating money already
  spent is a different lie. The unverified figure is recorded as-is and
  labelled unverified.

Side effect worth noting: the delivery had been sitting on the shelf while
PO-0141 stayed `Placed`, because the stock row's note never named the PO. Goods
on a shelf and an order still open is the reverse of the SHT31 failure — there
the record ran ahead of the parts, here the parts ran ahead of the record.

## Renaming a location with `.update()` leaves a stale `pathstring`

`StockLocation.pathstring` is a CACHED field, rebuilt in `save()`. Renaming
through the queryset — which is the house habit, because `.save()` on this
install has silently written nothing — updates `name` and leaves `pathstring`
holding the old value.

Measured 2026-08-24 after renaming `B-01 Sleeving & Loom` to `B-01`:

```
before: SLN/Storage/WS2/WS2-S3/B-01 Sleeving & Loom     <- pathstring
after : SLN/Storage/WS2/WS2-S3/B-01                     <- after l.save()
```

The name was correct the whole time. Every *display* of the location was wrong,
including the label-render breadcrumb and anything reading `pathstring` to
report where a part lives — so a location can be simultaneously renamed and not
renamed, depending on which field you read.

**After renaming or re-parenting a location, call `save()` on the instance and
re-read `pathstring`.** Verifying the rename by checking `name` is checking the
field that was never in doubt.


## Cable jackets carry sequential footage marks — read them before weighing anything

2026-08-24, on an Allied 8126 22/4: the jacket prints `#4626 FT.` as part of a
sequence the manufacturer lays down at one-foot intervals. **Subtract the mark
at one end from the mark at the other and you have the length**, exactly, for
nothing.

That beats every other method considered for the wire in B-01:

| method | cost | needs |
|---|---|---|
| **footage marks** | free | the marks to exist, and both ends |
| unwind and measure | slow | floor space |
| weigh | one minute | g/ft, from a coil of known length |
| eyeball | free | nothing, and it shows |

It also outranks them on evidence: the number is printed by the maker and does
not depend on anyone's judgement, so it is a **tally**, not an estimate — it
gets a `stocktake_date` and no `[ESTIMATE]` marker.

**The trap is that it is invisible unless you know to look.** The print is small,
low-contrast, and reads as boilerplate alongside the AWG and UL markings. Every
route we discussed — weighing, tare, cutting a sample to find g/ft — was
unnecessary for this coil and nobody would have found that out by reasoning.
Check the jacket first.

Not all cable carries it: the four Amazon cables in the same bin are still
recorded at their purchased lengths. Worth checking each of them.

## CORRECTED — `VSTR_USR_NM` is persistent storage, so a non-empty key proves nothing

**2026-08-24 16:46, measured.** The McMaster procedure two sections up says the
key is empty at cold load "whether or not you are signed in", and that a real
click is what populates it. **On this run the key already read `Scott Dube` at
cold load, before any click at all.**

The earlier table is not wrong about what it saw; it is wrong about what the
key *means*. `localStorage` **persists across page loads, tabs and restarts**.
Once any earlier visit clicked the control, the value stays until something
clears it. The 21-second table was measured on a profile where nothing had
clicked yet — a first-visit condition, not the general one.

**So the sanctioned test has a false-pass path.** "Non-empty and matches the
account name" is satisfied by residue from a visit that may be days old and a
session that may have expired since. The test that could never say "signed in"
was replaced by one that can never say "signed *out*".

### The second trap: which coordinate frame

`getBoundingClientRect()` returns **page** coordinates. The `computer` tool
takes **screenshot** coordinates. On this run those were x=1679 and x=1508 for
the same control — a 171 px gap, wide enough to land on nothing.

The miss is silent: the click reports success, no error appears, and the test
then reads the *stale* `VSTR_USR_NM` and calls it a pass. **The two traps
compound** — a missed click plus persistent storage produces a confident
"signed in" with no evidence behind it whatsoever.

Take the coordinate from a `screenshot` first, never from the rect.

### What is actually load-bearing

The post-click **UI transition**, which cannot be faked by stale storage:

| signal | signed out | signed in |
|---|---|---|
| masthead control | `Log in` | account name + `▾` |
| dropdown contents | login form | `Settings` / `Log Out` |
| contact number | `(630) 833-0300` (generic) | `(609) 689-3000` (account rep) |

The rep phone number is the cheapest independent confirmation — it is rendered
from account data, so a generic number means the session is not live regardless
of what the storage key says.

**This does not restore any route-based probe.** Everything in "Why every
guessed endpoint also lied" still holds; the fix is to read the post-click UI,
not to go looking for an endpoint again.

## AliExpress falls between the two sweep sections and is captured by neither

**2026-08-24 16:46, measured.** Two AliExpress orders confirmed 2026-08-23 —
`8213410090415753` (HLK-5M05B AC-DC module, 5-pack, $16.96) and
`8213410090395753` (15 mH 4 A annular common-mode choke ×2, $7.37) — were
absent from InvenTree and had been missed by the 08:40 and 12:40 runs.

Neither section is at fault on its own; the gap is between them:

- **Section 3** sweeps an *itemised vendor list* — Amazon, Tormach, MSC, Shars,
  Mouser, Pololu, eBay, Haas, McMaster, DigiKey, Seeed, Walmart. AliExpress is
  not on it, so the sender-based pass never looks.
- **Section 4** is the shape-based net meant to catch exactly that. But
  `vendor_triage.py` buckets `notice.aliexpress.com` as **known → "already
  swept"** and drops it before it can reach the decision queue.

`po_check` on both order numbers said `absent` at the same moment triage said
"already swept". **Triage answers "do we recognise this sender", and that was
read as "has this order been imported".** Those are different questions and the
words do not distinguish them.

This is the [unknown vendor blind spot] one turn further out: the earlier
finding was that the sweep only finds senders it knows. The variant here is
worse, because a *recognised* sender is actively marked handled — a known
vendor is more invisible than an unknown one, not less.

**Fix is one of two, and it is Scott's call** (on the decision queue as
`procedure-gap-aliexpress`): add AliExpress to the Section 3 itemised list, or
make triage's "already swept" test the order number via `po_check` instead of
the sender domain. The second is the general repair — it would close this hole
for every future vendor that gets added to the registry but not to Section 3.

**Do not read "already swept" as proof of anything** until that lands. It is a
statement about the registry, not about the database.

## `/Volumes/4TB_Removable` is on the MINI — two sessions in one day read it as local

**2026-08-24, twice.** The 16:46 and 22:46 daytime sweeps each stopped to
diagnose a "missing volume" that was never missing. Both ran `ls /Volumes/` on
the **laptop**, found no `4TB_Removable`, and started reasoning about an
unmounted drive.

The path is the Mini's. `scripts/itq` sets it explicitly:

```
HOST="${ITQ_HOST:-mini}"
ROOT="/Volumes/4TB_Removable/inventree"
```

Everything under it — the venv, `enrich_progress.md`, `pending_decisions.md` —
lives there and is reachable **only** through `itq`:

```
itq pull /Volumes/4TB_Removable/inventree/pending_decisions.md ./local.md
```

### Why it catches a careful reader

`journal.py` and `decide.py` both open the path as a plain local file, because
they are *written to run on the Mini* — `itq run` ships them there. So the
source reads local, and the sweep instructions cite the path bare, with no host
attached. Nothing on the page says "remote" until you read `itq` itself.

The tell is that **`itq run scripts/journal.py --start` succeeds in the same
session where `ls /Volumes/4TB_Removable` fails.** If a script can write the
file but the shell cannot see it, the file is not local — stop diagnosing the
volume and reach for `itq pull`.

A `ls /Volumes/` on the laptop is evidence about the laptop and nothing else.
On 2026-08-24 it returned two *different* listings six hours apart (`Bambu
Studio, pulseview NIGHTLY` at 16:46; a NAS share set at 22:46) and neither had
any bearing on whether the Mini's disk was mounted.

**Cheapest fix is in the wording**: cite it as `mini:/Volumes/4TB_Removable/...`
wherever the sweep instructions name it.

## KiwiCo is filed `mixed_use`, but it is a child's monthly crate subscription

Measured 2026-08-24 22:5x during the daytime sweep. The shape-based unknown-vendor
search surfaced `hello@kiwico.com` "Your KiwiCo Order has been delivered!". Triage
handled it correctly — `kiwico.com` is in `mixed_use`, and the subject matched the
`has been delivered` lifecycle filter, so it produced zero decisions.

It only came out right because the lifecycle filter caught it. The classification
underneath is wrong: `from:kiwico.com newer_than:30d` returns four messages, two of
which are `customercare@kiwico.com` "Important message about your subscription:
credit card payment error … this month's crate for Gabriella". That is a recurring
children's STEM crate subscription, which Rule 7 puts OUT — the same bucket as
`anthropic.com`, not the same bucket as `homedepot.com`.

Why it matters: `mixed_use` means "classify per order from the item titles", so the
FIRST KiwiCo email whose subject is not a lifecycle stage — an order confirmation, a
renewal, a "your crate is ready" — surfaces as a decision for Scott about a
household subscription. `mixed_use` is not a safe default for a subscription; it is
a deferred false positive waiting on a subject line nobody has seen yet.

Not changed here: moving a domain between registry buckets is a policy edit, not a
sweep action, and no order was missed. Flagged for Scott to move `kiwico.com` from
`mixed_use` to `suppress.subscription` in `scripts/vendor_registry.json`.

## mcmaster.com and walmart.com are SLOW to become scriptable, not unreadable

**2026-08-25. First written as "can wedge the Chrome extension entirely."
That was wrong and is corrected here rather than left standing.**

At 08:50–09:05 neither site could be read. Every extension entry point failed:

| call | failure |
|---|---|
| `get_page_text` / `read_page` | `executeScript waited 45000ms for document_idle` |
| `javascript_tool` | `Runtime.evaluate timed out after 45000ms` |
| `computer:screenshot` | `Script injection timed out after 5000ms` |

At 09:55 — same browser, same profile, same session, no intervention — the
McMaster tab that had been left sitting read instantly, and both sites proved
**signed in**: McMaster's masthead showed `Scott Dube` with Settings/Log Out
and the phone switched to the account-rep line (609) 689-3000; Walmart showed
`Hi, Scott D` and rendered purchase history. Scott confirmed McMaster
independently at the same time.

**So the observation was real and the conclusion was not.** These pages take
minutes, not seconds, to reach `document_idle`, and every extension entry point
blocks on it. Nothing is wedged; it has not finished.

**What made it look permanent:** Amazon and shop.app were read on the same
browser in the same run, both instant. That contrast reads as "per-site and
fatal" when the truth is "per-site and slow", and it was the contrast, not the
timeouts, that produced the wrong write-up.

**Recording `UNKNOWN` rather than `OUT` was still right** — a test that cannot
execute has observed nothing, and `OUT` would have fired a NOTIFY for a
transition nobody measured. The error was treating `UNKNOWN` as *final* after
one round of timeouts inside a few minutes.

**Procedure:** when a vendor page times out, leave the tab loading, go do other
queue work, and retest before recording state. One round of timeouts is not a
reading. Budget minutes for these two.

**Additionally, and separately from the above:** a cold deep route renders a
blank content pane for roughly another 25 s *after* the page is already
scriptable — `/order-history/` returned `No text content found` and a
screenshot showing only the masthead, then filled in completely on the next
look. The account-rep phone number was visible in the masthead the whole time,
which is the tell that the blank pane is not a signed-out page. This is the
same pre-auth-SPA-shell effect documented above; it is not a second bug.

## `itq` was never on PATH — the unattended job's first command always failed

Measured 2026-08-25, after a third consecutive night of "not running unattended
due to a permission issue".

The scheduled task file instructs every run to begin with, literally:

    itq run scripts/run_gap_check.py

`itq` lived only at `~/code/scripts/itq` and **no directory containing it was
ever on `PATH`**. So that command did not stall — it exited **127,
command-not-found**, instantly, on every run that has ever executed it.

**Why this read as a permission problem.** The permission rules were never the
fault; `Bash(itq run *)` exists and matched fine. What happened is downstream:

1. The documented command returns 127.
2. The agent, unattended and with no instruction covering this, starts
   *diagnosing* — `ls -la ~/code/scripts/ && echo $PATH`, `command -v itq`,
   and so on.
3. Those improvised diagnostics are **compound `&&` commands, unique every
   time**. Per `settings.json`'s own note, the matcher cannot decompose them,
   so each one is a fresh one-off that no wildcard rule can cover.
4. Prompt. Nobody is awake. The run hangs.

So the visible symptom (a permission prompt) was two steps removed from the
cause (a missing symlink), which is why it survived several rounds of adding
permission rules — none of which could ever have helped.

**The tell that separates the two:** a permissions stall produces *no* output;
this produces `command not found` and *then* stalls. Exit 127 in the first
command of a run means PATH, not policy.

**Fix applied:** `~/.local/bin/itq -> ~/code/scripts/itq`. That directory is
exported by **both** `.zprofile` and `.zshrc`, so it is present in login and
interactive shells alike.

**`~/bin` was the wrong target and is a trap of its own.** It appears in this
session's `PATH` but is set by *neither* shell file — it is injected by
something outside the user's dotfiles, so a symlink there would work when
tested by hand and vanish under a differently-initialised unattended shell.
That is the same class of bug, one layer deeper. Verified the fix with
`zsh -lc 'command -v itq'` — a *fresh login shell*, not the warm one that was
already broken-but-working-by-accident.

`itq run` resolves a bare relative script path against `$ITQ_REPO`
(`~/code/shop-inventory`), not against `$0`, so invoking it through a symlink
changes nothing about where scripts are found.

**Two junk rules in `settings.local.json`** are now visible as fossils of this:
`Bash(../scripts/itq run *)` and `Bash(../scripts/itq push *)`. From the
working directory `~/code`, `../scripts` is `/Users/scottdube/scripts`, which
does not exist. Those rules can never have matched anything real. Left in
place — that file is rewritten by the app and must not be hand-edited.


## Two sessions writing TRAPS.md at once: the commit message stops describing the diff

**2026-08-25 09:38:37, observed.** The daytime sweep appended the McMaster/
Walmart wedge section above and left it staged-but-uncommitted for a few
minutes. Another live session committed in that gap with `git add -A`, so
commit `6785558` — whose message is entirely about `itq` never being on PATH —
carries 96 insertions, of which only about half are its own subject.

Nothing was lost and nothing conflicted; both sections are intact. What was
lost is the *message*, and on this repo the message is the load-bearing part:
the working rules say the diff shows what changed and only the message says
what was ruled out. A reader running `git log -S` on the wedge trap lands on a
commit about PATH and has no reason to trust it.

**Cheapest fix: append and commit in the same breath**, never `git add -A` from
a repo root you are sharing. `git add <specific-file> && git commit` would have
made the collision impossible in both directions.

Not fixed retroactively here: rewriting a commit another session had just
written is a worse race than the one it repairs.

## The 2026-08-25 NEVER_STARTED was idle sleep, not permissions and not the API

**Measured from `pmset -g log`.** The Mac entered `Idle Sleep` at **01:52:19**,
thirteen minutes before the 02:05 enrich, and spent the rest of the night
cycling Sleep -> DarkWake roughly every 90 seconds. All three attempts
(02:05/03:00/04:00) deferred to Scott's 08:46 morning wake, which is why the
journal window 01:00-06:00 held zero events.

**This is the third distinct cause behind an identical symptom**, which is the
whole point of writing it down:

| night | symptom | actual cause |
|---|---|---|
| 08-23 and before | "permission stall" | `itq` was not on PATH — exit 127 |
| 08-24 | ran, did nothing | `API Error: 529` at 02:09 |
| 08-25 | no events at all | machine idle-slept at 01:52 |

None of the three is distinguishable from the others by looking at the
scheduler, which reports all of them as "the task ran".

**Fixed the same morning, by another session:** `com.sln.overnight-caffeinate`
(holds from 01:45 for 12300 s) plus `pmset repeat wakepoweron 01:55`. Neither
existed last night. Verified today by `launchctl kickstart` that caffeinate
does take both `PreventSystemSleep` and `PreventUserIdleSystemSleep` when
launchd starts it — not merely that it works from a shell, which is a
different test and has already lied once in this repo.

**The RTC wake at 01:55 is the single point of failure and nothing guards it.**
`caffeinate` cannot promote a dark wake to a full wake, so if the repeat wake
is ever lost — a macOS update, an NVRAM reset, a restore — the caffeinate hold
will faithfully pin the machine in DarkWake, where the app's scheduler is
throttled. That failure looks exactly like a healthy hold. Check it with
`pmset -g sched`; it must list a `wakepoweron` at 1:55AM.

**Instrument added:** `com.sln.overnight-witness` writes one line at 01:44,
02:00, 03:00, 04:00 and 05:00 to `~/.claude/overnight-witness.log`. Its own
lateness is the measurement — lines at their scheduled times mean the Mac was
awake and the fault lies with the app or the job; lines clustered at a single
morning timestamp mean it slept. Read it FIRST on any NEVER_STARTED, before
touching `pmset -g log`.

## Dashboard widget selection lives on the SERVER, not in localStorage

2026-08-25, piloting the instrument panel. A new plugin dashboard item does not
appear on the dashboard by itself — InvenTree stores a per-user *selection*, and
a widget the API offers is simply not shown until it is in that list.

The list looks like it lives in `localStorage['session-settings']`, and it does
appear there: `state.widgets` and `state.layouts`. **It is a mirror, not the
source.** `LocalState.setWidgets()` calls `patchUser('widgets', …)`, which PATCHes
`/api/user/profile/`, and the profile copy is pulled back over the local one on
load. Editing localStorage and reloading therefore "works" for a fraction of a
second and then silently reverts — three attempts read as "the widget is broken"
when the widget was fine.

Add one from the console like this (the label is
`identifierString('p-' + plugin_name + '-' + key)`, lowercased, non-alphanumerics
to `-`):

```js
const p = await (await fetch('/api/user/profile/',{credentials:'include'})).json();
p.widgets.widgets.unshift('p-shopstatus-shop-status-panel');
p.widgets.layouts.lg.unshift({i:'p-shopstatus-shop-status-panel',x:0,y:0,w:12,h:10,minW:12,minH:10});
await fetch('/api/user/profile/',{method:'PATCH',credentials:'include',
  headers:{'Content-Type':'application/json',
           'X-CSRFToken':document.cookie.match(/csrftoken=([^;]+)/)[1]},
  body:JSON.stringify({widgets:p.widgets})});
```

In the UI the same thing is done from ⋮ → Add Widget — but **the control is the
small green icon in the left column, not the widget's name**. Clicking the name
does nothing and closes nothing, which reads exactly like a failed add.

## Tombstone markers do not share a severity

The panel's first tombstone lamp counted all four markers — `NOT INVENTORY`,
`MERGED into`, `REFUNDED`, `POSSIBLE RETURN` — and lit **red on 14 parts**. Then
the 14 were read: 13 were `POSSIBLE RETURN — an order containing this was
refunded; verify`, which is a deliberate to-do queue, and exactly one was a real
fault (part 71, Arduino Nano, `MERGED into` another part while still `active` —
so it can be counted twice).

A red warning over a to-do list is the cry-wolf failure `DASHBOARD.md` is written
to avoid, and it would have trained the lamp to be pressed unread within a week.
Split by the rule already in that file — *does this failure make another check
lie?*

| marker | on an active part | lamp |
|---|---|---|
| `MERGED into`, `NOT INVENTORY` | double-counts, and sits in every coverage denominator | red |
| `REFUNDED`, `POSSIBLE RETURN` | nothing is wrong yet; someone has to look | yellow |

The general form: **a marker family is not a severity class.** Group markers by
what breaks if they are ignored, not by which importer wrote them.


## A supplier pack quantity of 1 on a multipack silently divides the shelf

PO-0138 ordered **1** Outus acrylic sheet. The box holds **4** — the listing is
a 4-pack, and the part description already said so in prose. `SupplierPart.
pack_quantity` was `'1'`.

Receiving on the order line alone would have put **1 sheet** in L1-D3 with three
more physically in the drawer and invisible. Not a wrong number that announces
itself: it reads as a perfectly ordinary receipt.

`pack_quantity` is what future receives of that SKU multiply by, so the error
is durable and repeats every reorder. Corrected to `4` at the same time as the
receipt — a fix to one row that is really a fix to every future one.

**Check the pack figure against the description before receiving a multipack,
and ask for the count.** Scott counted 4 out of the box, so this row carries a
real `stocktake_date` — receiving is not counting, but a tally at receipt is.

## A client that rewrites a whole stored map must seed it from the server

The panel stores lamp acknowledgements as one JSON blob in a plugin setting, and
the browser rewrites the entire blob every time a lamp is pressed. It seeded that
blob from the lamps it had just rendered — which carry `ack: true/false` but did
not, at first, carry the *time* of the ack. Every unpressed lamp was therefore
written back as `{n: 43, at: null}`.

Nothing looked wrong: the lamps stayed silenced, the counts stayed right. What
was quietly destroyed was the only part of the record that was a *signal* — a
lamp acknowledged six weeks ago says something a lamp acknowledged this morning
does not, and `DASHBOARD.md` calls that "an atrophy detector hiding inside the
mechanism".

**The general shape, worth watching for anywhere else in this project:** when a
client PATCHes a whole document rather than a field, every attribute the client
does not render is a field it is silently deleting. Either round-trip the full
record, or patch the one key. Here the server now hands `ack_at` back out with
each lamp so the client can put it back unchanged.

## An unknown table filter is ignored, not rejected — so a bad link shows everything

2026-08-25. The panel's lamps linked to `/web/stock/` and `/web/part/`, and every
one of them opened the entire table. Two separate causes, and the second is the
dangerous one.

**`/web/stock/` and `/web/part/` are not table routes.** Both are redirects:
`/web/stock/` → `/web/stock/location/index/sublocations`, `/web/part/` →
`/web/part/category/index/`. The redirect **drops the query string**, so filters
attached to them vanish without a trace. The tables actually live at:

| want | route |
|---|---|
| stock items | `/web/stock/location/index/stock-items` |
| one location's items | `/web/stock/location/<pk>/stock-items` |
| parts | `/web/part/category/index/parts` |
| purchase orders | `/web/purchasing/index/purchaseorders/` |

**Query parameters on a table route are passed straight through to the API, and
the API ignores filters it does not know.** Not a 400 — a 200 with the whole
table. Measured against this instance:

| link | expected | actually returns |
|---|---|---|
| `stock?location=null` | 43 | **650** — `cascade` defaults true and swallows it |
| `stock?location=null&cascade=false` | 43 | 43 ✓ |
| `part?has_image=false` | 478 | **1010** — no such filter |
| `po?has_issue_date=false` | 0 | **65** — no such filter |
| `stock?id=1` / `?pk=1` / `?id__in=1,2` | 1 | **650** — no such filter |
| `stock?has_stocktake=false` | 281 | 281 ✓ |
| `stock?max_stock=-0.0001` | 0 | 0 ✓ (and `max_stock=5` → 312, so it is live) |
| `part?active=true&search=REFUNDED` | 13 | 13 ✓ |

A filter that does not exist is indistinguishable from a filter that matches
everything, which is the same shape as the `[ESTIMATE]` error: **a check that did
not name what it queried**. The link looked right, the page looked plausible, and
the number was the whole database.

**So the panel refuses to ship an unproven link.** Each lamp carries a candidate
URL *and the row count that URL would return*; the link is used only when that
count equals the lamp's own. When it does not, the lamp keeps the plain table and
says `open list →` instead of `open 43 →`, and the tooltip says no API filter
matches. Seven of ten lamps earn an exact link today; `Row contradicts itself`
and `PO has no issue date` cannot (there is no filter for a notes prefix, nor for
a null issue date) and they say so.

Verified in the browser, not just against the API: 43/43, 13/13, 3/3, 4/4.

## Spent stock still answers "yes" to a lamp — and a lamp that cannot clear stops being read

2026-08-25. Scott, looking at the panel: *"this DIN cable, how will it ever get
out of stock?"*

Stock #89, a 7-Pin DIN extension cable, is **wired into the Standing Desk
Controller** (stock #120, built by BO-0003). Its notes say so. InvenTree already
handles it correctly — `belongs_to=120`, `in_stock` is `False`, and the part's
total stock reads 0. It is *not* in stock.

But the panel's `Stock with no location` lamp was counting rows where
`location IS NULL`, and **installing a part is precisely what removes its
location**. So the cable was being reported as lost, forever: it cannot be given
a location without uninstalling it from a finished device. Same for the ESP32
in the same controller, and for rows consumed by a build.

**The failure is not the wrong count, it is the lamp that can never reach zero.**
Four rows out of 43 could never be cleared by any amount of work, so the lamp
would have stayed lit permanently — and a warning that is always on is a warning
nobody reads. This is the same shape as the tombstone lamp lighting red over a
to-do queue, and the same shape as the 6-20P plug: **stock that was SPENT still
answering yes to "do I have one?"**

**The rule: anything meaning "stock I have" uses `StockItem.IN_STOCK_FILTER`,
never `location__isnull` or a bare row count.** That filter is
`quantity > 0, sales_order=None, belongs_to=None, customer=None,
consumed_by=None, is_building=False, status in AVAILABLE_CODES` — and the API
exposes it as `in_stock=true`, so a filtered link can say the same thing.

Measured on this instance: 650 stock rows, **638 actually in stock** — 3
installed, 2 consumed by a build, 7 run down to zero. What that changed:

| readout | was | now |
|---|---|---|
| `Stock with no location` lamp | 43 | **39** |
| COUNTED gauge | 369 / 650 = 57% | **360 / 638 = 56%** |
| Catalog Health "stock items" | 650 | **638** |

The COUNTED correction matters more over time than the 1% suggests: with spent
rows in the denominator the gauge falls a little **every time something gets
built**, which is coverage decaying for the healthiest possible reason.

## Received, then installed the same week — and Receiving never hears about it

2026-08-25, third instance. Scott, looking at stock #92: *"this part is not in
rec it was installed in the work probe on the 1100MX."*

A LiPo 750mAh battery, received 2026-08-18 against PO-0023, filed to
`SLN/Receiving`, and fitted into the Passive Probe Kit (BT30) at the mill almost
immediately. The record never moved. For a week it read **in stock, quantity 1,
awaiting a drawer** — an answer of "yes" to *do I have one?* for a battery that
is inside a tool in service.

The list so far, all the same shape:

| item | where it really was | how it read |
|---|---|---|
| 6-20P plug | wired into an appliance cord | available |
| 7-Pin DIN cable (#89) | inside the Standing Desk Controller | available |
| LiPo 750mAh (#92) | inside the 1100MX probe | in Receiving, awaiting a drawer |

**Receiving is the blind spot, not the drawers.** Something filed to a real
location gets looked at again when somebody opens that drawer. Something in
Receiving that gets *used* on the way past is never opened again — the physical
item leaves the staging dock and the row stays behind. The location's own
description says it "should trend toward empty", and nothing measures whether it
does.

**Recorded the same way each time: `belongs_to`, not a delete and not a zero.**
The part physically exists and its provenance still matters; what changed is that
it is no longer free. Taking the row to zero on this install *deletes the row and
its notes* — see the trap above — which discards exactly the record being made.
Uninstalling later restores it to stock honestly.

**Order mattered, by luck.** The `IN_STOCK_FILTER` fix landed an hour before this
one. Without it, installing the battery would have moved it out of the Receiving
queue and straight into `Stock with no location`, where it could never have been
cleared — trading a wrong queue for a permanently lit lamp. Measured after the
write: Receiving 3 → 2, lost unchanged at 39.

**Built the same day: the `In Receiving over Nd` lamp.** A row that has sat on
the staging dock past the threshold is either not filed or not there, and both
are worth a look.

**The threshold is 7 days, not the 14 first proposed, and the difference is
measured rather than chosen.** The DIN cable and the LiPo were both received
2026-08-18; the LiPo was **7 days old** when Scott caught it by eye. At 14 days
the lamp would have been dark through exactly the week it was needed. It is a
plugin setting (`RECEIVING_STALE_DAYS`) so it can be retuned, but the default
has to be shorter than the interval at which a human notices, or the instrument
is decorative.

Age is measured from `creation_date`, not `updated` — the question is how long
ago it landed, and `updated` is bumped by any edit, including editing the note
that says nobody has filed it. Known limit: a row *moved into* Receiving from
elsewhere reads older than it has been on the dock. Receiving is where things
are created, so that is the rare case, not the normal one.

## The survivor of a merge talks about the merge — so a substring test lights the wrong side

2026-08-25. The red `Merged part still active` lamp pointed at **part #71,
Arduino Nano V3.0** — a record that is supposed to be active. Nothing was wrong
with it. The lamp was.

The tombstone convention here is a **prefix**: all 28 merged-away records begin
`MERGED into part #N`, and every one of them is `active=False`. Part #71 is the
*surviving* record, and its description explains the merge in prose —
*"part #381 (AYWHP 5-pack) was merged into this record"*. Tested with
`description__icontains='MERGED into'`, that prose matches, and the survivor gets
reported as a tombstone that failed to be retired.

**This is the `[ESTIMATE]` error again, three files apart.** Same shape: a marker
that is a *prefix* tested as a *substring*, returning a confident, plausible,
wrong row. It has now cost a false red lamp, and the earlier version cost a wrong
`[ESTIMATE]` count twice.

| marker | active rows, `icontains` | active rows, `istartswith` |
|---|---|---|
| `MERGED into` | 1 (the survivor) | **0** ✓ |
| `NOT INVENTORY` | 0 | 0 |
| `POSSIBLE RETURN` | 13 | **13** ✓ |
| `REFUNDED` | 13 | 0 — it is prose *inside* the POSSIBLE RETURN sentence, never the marker |

The last row is the one to remember when writing the next check: **`REFUNDED` is
not a marker at all.** It reads like one, it matches 13 rows, and it agrees with
the right answer today purely by coincidence of wording.

### And the warning nobody could read

Part #71's description ended `…this merge conflated two CONNECTOR variants —
verify before tru`. Not a typo: **`Part.description` is capped at 250
characters**, and the warning was silently truncated mid-word when it was
written. A caveat that cannot be read is not a caveat. Long-form findings belong
in `Part.notes`, which has no such limit; the description gets the verdict only.

**Resolved, from the records themselves:** #71's `orig:` says *USB-C*, #381's
says *(USB C Port)*, and both carry the same Amazon order `113-2421163-1104249`,
same date, same $18.99. One purchase imported twice under two vendor titles — not
two connector variants, so the merge was correct and there is nothing to unpick.
Total stock is 0 on both sides, so no boards existed to inspect even if it had
mattered. Written into the part's notes with the evidence.


## A pack is a supplier fact — get pack_quantity wrong and every piece wears the pack price

2026-08-25. Scott: *"the pricing of those bins are wrong they were 10.98 for a
10 pack not per piece."*

`SupplierPart` 5297809753 (Walmart, Sterilite 6-quart bins) carried
**`pack_quantity='1'`**. PO-0141 bought one ten-pack for $10.98, so the receipt
created stock priced at **$10.98 per bin**. Nineteen bins read **$208.62** of
storage bins on a $21.96 spend — an order of magnitude, in the direction that
flatters.

**Fixed at the root, not just on the rows:** `pack_quantity` is now 10, so the
next receipt of that SKU prices itself. Existing rows repriced to $1.098.

**And `.update()` is not enough for this field.** `pack_quantity` is a string;
`pack_quantity_native` is the number InvenTree actually calculates with, and it
is recomputed in `save()`. A queryset `.update()` writes the string and leaves
the native value stale — it read `1.0000000000` next to a `pack_quantity` of
`'10'`, which is a record that contradicts itself. Only the re-read caught it.
Use `.save()` for this field and verify BOTH.

**The smell to watch for:** a part whose NAME says "10 pack" while its quantity
counts pieces. That mismatch is what makes the wrong price look reasonable —
19 of something called a "10 pack" at $10.98 each is not obviously absurd until
you notice the quantity is bins.

## One row per part per location, and what the merge costs

Same conversation. Scott: *"if I follow that logic any time we buy more of
anything it becomes its own stock? so each time we get new ESP32-C6s I have to
contend with another line and add those in my head to know how many I have?"*

He is right, and the earlier answer here (keep the bins as two rows, one per
purchase) optimised for provenance while ignoring the question the shelf is
actually asked. **The rule is now in `CLAUDE.md`:** one stock row per part per
location; buying more merges. Purchase history lives on the purchase orders and
in the row's notes.

**What the merge actually costs, so it is chosen and not discovered:**
`merge_stock_items` **deletes the other row and its tracking history**, and
computes a weighted-average unit price. So anything the merged-away row knew has
to be written into the surviving note FIRST. Here that was the counter purchase —
ten bins bought in store because the delivery was late, with no email and no
portal entry, so there is no PO to point at and never will be. That story would
have died in the merge.

**Reprice before merging, not after.** The average is weighted by quantity, so
merging two wrong prices gives a confidently wrong average.

**Exceptions that stay split:** serialised items, mixed status, real batch or
expiry differences, different locations. Measured across the whole instance the
day the rule was written: only 3 (part, location) pairs held more than one row —
the bins (merged), two SHT31-D rows with no location at all, and two BT30 collet
chuck rows at different prices, which is a judgement call rather than a
duplicate.


## The price was 10x out on screen and the panel had nothing to say about it

2026-08-25. Scott, after the bins: *"I would have thought you would have caught
the price being so wildly out of line?"* Fair. The stock table showed
`$98.82` and `$109.80`, the part name said **10 pack**, and the row's own note
said **"$10.98 for the 10-pack"** — all on one screen — and the reading went to
"are these two rows duplicates?" without ever asking whether $208 of plastic
storage bins was a plausible number.

**Nothing on the panel was watching either**, which is the more useful half. So:
`Pack price may be per piece` — priced stock whose part states a pack size that
no supplier part records. **9 rows today.**

It deliberately does NOT claim a price is wrong, because it cannot know:

| row | reading | verdict |
|---|---|---|
| ER20 Collet Set 10pc | 1 @ $152.85 | **fine** — stocked as one set, priced per set |
| Clamp Kit, 58 pcs | 1 @ $89.95 | **fine** — same shape |
| Avery 8167, 2000 labels | 1 @ $11.99 | **fine** |
| BT30 pull studs, pack of 10 | 10 @ $8.40 | **unsettled** — Tormach studs really can be $8.40 each |
| 4in coolant nozzle (10-pack) | 10 @ $4.50 | **unsettled** |
| Copper clad 7x10, pack of 10 | 9 @ $1.00 | **unsettled** |
| KF301 terminal blocks, 50 | 27 @ $0.15 | **unsettled** |

The pattern that separates them: **quantity 1 of a stated pack is a kit and is
priced correctly; quantity N of a stated pack of N is the shape that was wrong
on the bins.** Only the invoice settles it, so the lamp asks rather than
asserts — and the fix, once settled, is `pack_quantity` on the supplier part so
the next receipt prices itself.

**Worth stating plainly:** the check exists because a human caught what the
instrument missed. That is the right order for this panel — every lamp on it so
far was earned by something going wrong first — but it is also the reason the
panel is not yet trustworthy on its own.

### Settled the same hour, and the lesson underneath

Scott, on being asked which way the pull studs went: *"84 but couldnt you do a
quick inet search if you were unsure? Thats what I would do."* Correct, and it
took two searches:

| SKU | vendor says | ours | verdict |
|---|---|---|---|
| Haas `04-1420` BT30 TSC stud | **pack of 10**, $93.97 sale / $103.95 list | 10 @ $8.40 = $83.97 | correct |
| Haas `04-1421` BT30 standard stud | **pack of 10** | 10 @ $7.20 = $71.97 | correct |
| Tormach `35724` 4in coolant nozzle | **10-pack, $44.95** | 10 @ $4.50 = $44.95 | correct — the importer divided |
| Amazon `B07DJXQK54` copper clad | — | PO-0003 line reads qty 10 @ $1.00, already per piece | correct |

**Every one was right. The bins were the only real error** — and asking Scott to
adjudicate four rows that a web search settles in a minute is the wrong division
of labour. *Live price is checkable; check it.* The `+40%` rule in `CLAUDE.md`
exists precisely because an unverified price is a guess, and the same logic
applies to verifying one that is already on the books.

`pack_quantity` is now recorded on all four supplier parts, which is what the
lamp was really asking for — not "is this price wrong" but "does the record say
what a pack contains". With that, and with single-unit kits skipped, the lamp
falls from 9 to **2**: the two KF301 terminal-block rows (27 and 18 pieces at
$0.15, stated pack of 50), which no vendor page settles because the listing is a
generic multi-vendor part.

One caveat recorded on the copper-clad row: PO-0003's line predates the pack size
being recorded and is expressed in PIECES. It must not later be re-read as ten
packs.


## "No filter matches" was true of the query, not of the rows

2026-08-25. Scott, on the new pack-price lamp: *"When you go to open the list, it
gives you the same unfiltered stuff the other one did before, not just the two
results that you need."*

The verified-link rule said: ship a filtered link only if it provably shows the
lamp's rows, otherwise fall back to the plain table and say `open list`. That
rule is right, and it was hiding a lazy conclusion. **The lamp already knows the
exact rows** — it computed them. What was missing was a way to *express* a set of
primary keys as a URL, because the API ignores `id`, `pk` and `id__in` outright.

But `search` is a real filter, and the rows have words in common. So: take the
words every flagged row's part name shares, mirror `StockList.search_fields` in
the ORM, and use the link only if that search returns exactly the lamp's count.
A word like `TERMINAL` that also catches other terminal blocks fails the count
and is thrown away; `5.08MM` passes and returns the two rows and nothing else.
A single row skips all of it and links straight to the item page.

Verified in the browser: `?search=5.08MM&in_stock=true` → **1 - 2 / 2**.

**The lesson is about the fallback, not the filter.** "No API filter matches
this set" is easy to say and easy to stop at. It was a statement about the one
query shape being tried, not about the rows — and the honest fallback made it
comfortable to stop. Say what cannot be done, then check whether something else
can.

## `vendor_triage` emits a decision for an order that already has a PO

2026-08-25, 16:40 sweep. The classifier reported `=> 1 distinct purchases need a
decision` and emitted a `decide.py --add` line for `walmart.com`, subject
`Arrived: Your Akro-Mils 24 Drawer Pl... +1 item`. That order is
`2000151-82176030` and **already has PO-0142**. Adding the decision would have
put a resolved item on Scott's queue.

**Why.** `order_no()` reads only `subject + snippet`. Walmart's *Arrived* mail
puts the order number in neither — it lives in the body. So `_order_no` is
`None`, and the dedupe key falls back to `(domain, subject)`:

```python
key = r["_order_no"] or (r["_domain"], r.get("subject"))
```

The two *Shipped* mails for the same order **do** carry the number in the
snippet, so they dedupe to `2000151-82176030` while the *Arrived* mail dedupes to
a tuple. Two different keys for one order, so it survives as "distinct".

**The deeper point:** the dedupe is only against the other emails in the batch.
Nothing in this path ever asks InvenTree whether the order was already imported —
`po_check` is Section 3's idempotency key and Section 4 never calls it. So the
guard against double-work is spelling, not state.

**Procedure until fixed:** run `po_check` on every order number the triage
surfaces before passing it to `decide.py`. A bucket line is a candidate, not a
finding. The fix is for `vendor_triage` to take the same idempotency check —
key on the order number *and* test it against existing `supplier_reference`
values — but that is a code change, not something to do mid-sweep.
## The default description a location was CREATED with is not a description

RB-18 was reported empty by Scott standing at the rack, 2026-08-25. Two
separate tools refused to record it, both for the same reason and neither with
an error that said so.

All 28 red bins were created carrying one sentence:

> Red bin. Holds ONE project's kit OR free storage - never both.

That is the **rack's house rule, stamped onto every child**. It names no
contents, describes no bin, and distinguishes nothing — but it is text, and
both tools test for text.

- A walk board written the same morning classed a bin with a description and no
  stock rows as **DECLARED** — the state that means *the record here is
  finished, looking again changes nothing*. Twelve never-opened bins rendered
  as finished. That is the DECLARED state pointed at its own negation.
- `scripts/mark_empty.py` refused RB-18 with *"description names something -
  CHECK BY EYE"*, having been told by eye.

This is the third pass through the same guard — first "any text" as a proxy for
"names contents", then bulk emptiness claims reading as contents, now
boilerplate. The rule that generalises: **a guard that reads a description must
first ask where the text came from.** Contents written by a person, a bulk
claim, and a template stamped on creation are three different things wearing
one field.

Both tools now match the boilerplate string exactly and treat it as blank.
Exact-match, not a fuzzy test — a bin whose description is boilerplate *plus*
something someone typed still refuses, which is correct.

**The carry-forward was wrong too.** `mark_empty.py` appends the old text as
`— previously labelled: <old>`, and RB-18 would have read *"VERIFIED EMPTY
2026-08-25 — previously labelled: Red bin. Holds ONE project's kit OR free
storage - never both."* — asserting the bin was once labelled as holding a kit.
It never was. Boilerplate is dropped rather than retired, because there is no
superseded claim to retire.

**The `--cabinet` sweep objection does not reach here**, and it was checked
before relaxing anything: the sibling guard must keep refusing bulk claims
because *"a bulk `--cabinet` sweep has nobody looking"*. `--cabinet` expands
`{name}-R…`, which no `RB-nn` bin matches, so there is no sweep path onto the
red bins at all. Every red bin has to be named explicitly, one at a time, by
somebody standing at it.

`--note` was added in the same pass so the stamp carries its provenance
("Scott confirmed by eye during the Red Bin walk.") instead of a bare date —
matching what RB-09, RB-10, RB-15 and RB-16 already say.

## "5 rows, 5 counted" is a fact about the rows, not about the bin

RB-14 renders on every report as finished: five stock rows, all five counted
2026-08-23, no estimates. It is the best-looking bin on the rack.

Scott, 2026-08-25: *"in RB-14, that uncatalogued jig is part of the other
contents of that fourteen. So if you look at fourteen, you're gonna see a bunch
of contents. A jig is part of that group."*

The five rows are the **AC wall adapter build's allocation** — fuses,
varistors, chokes, X2 caps, HLK modules. They were never an inventory of the
bin. The bin also holds a jig labelled *"JIG DONT TOSS OUT"*, a white
enclosure, and a perfboard with a toroid, none of which are on the books.

**Counting is per-row, and completeness is per-container, and no amount of the
first produces the second.** `stocktake_date` answers *is this number right*.
Nothing in the schema answers *is this list the whole list*, and every report
built so far — the walk board, the per-cabinet tables, the "313 of 587 counted"
figure — silently treats the first as the second.

The cost is specific: a fully-counted bin is exactly the bin nobody re-opens.
RB-14 would have stayed "done" indefinitely, and the jig would have surfaced
the day somebody threw it out — which is why it has that label written on it in
the first place.

**Do not read a green bin as a complete bin.** Completeness is a claim only a
person standing at the open container can make, and until somebody makes it,
the honest rendering of RB-14 is *five rows counted, contents not attested*.
The walk board now says so in its legend rather than implying otherwise; a
real per-container `contents_complete` flag is the durable fix and is not built
— see `docs/OPEN.md`.

Sibling of the DECLARED trap two entries up. There, boilerplate made unopened
bins look finished. Here, a genuine count makes an under-recorded bin look
finished. Both are the same mistake: **a report showing the strongest thing it
knows, with no way to say what it does not know.**

## CORRECTED — the eBay gap is the LOOKBACK WINDOW, not the vendor list

Written earlier the same day, and wrong: RB-20's practice kits were recorded as
*"the unknown-vendor blind spot arriving as a missing PART rather than a
missing order."* They are not. **ebay.com is on the registry's `known` list**
and is swept per-order; the sweep was never blind to the vendor.

Scott supplied the listing, and the mail settles it: the order was confirmed
**2026-06-16** and delivered **2026-06-27** — about **70 days** before the
walk, against a sweep measured over a **45-day** window. The order was in
range of every query the job knows how to ask, and out of range of the only
window it asks them over.

The scale of what that hides, measured 2026-08-25:

| | |
|---|---|
| eBay order confirmations in the mailbox | **~201**, back to 2022 |
| eBay purchase orders in InvenTree | **1** |

**Two different failures wear the same symptom — "we own it and the catalogue
has never heard of it" — and they have opposite fixes.** An unknown vendor
needs a registry entry; a known vendor outside the window needs a *backfill*,
and adding it to the registry again does nothing. Diagnose by asking whether
the sender is on a list **before** reaching for the blind-spot explanation,
because the blind-spot story is the more interesting one and will be reached
for first.

eBay is a better backfill target than Amazon, and for a reason already
recorded here: **Amazon truncates the product title in the email body**, so
mail can only ever yield a prefix. eBay's order mail carries the item title in
full — *"Order confirmed: Starrett Radius Gage Set S167C"* — which is enough to
identify an unknown item, not merely match a known one.


## A photograph cannot tell silicone from plastic — and it queried a record that was right

#791's description said *soft silicone squeegee*. In a photograph the two
orange NEWISHTOOL cards read as semi-rigid plastic, which would have made the
part name wrong too — a stiff card is a stencil/vinyl applicator, not a screen
printing squeegee. That doubt went to Scott as a one-second test.

Scott, 2026-08-25: *"Silicone."*

The record was right. The doubt was manufactured by the photograph, and the
existing rule — **photographs show identity, not quantity, fullness, or
provenance** — now has a fourth item: **not material.** Colour, gloss and edge
sharpness do not separate soft silicone from rigid PP at any resolution. Nor
would a better photograph have helped, which is the tell that this is a
property of the medium and not of the picture.

Worth keeping because it points the opposite way from most entries here. The
usual failure is a record asserting more than anyone verified. This was a
record that had it right, questioned from weaker evidence than the record was
built on. **A written material claim outranks a look at a picture**, and the
right move when they disagree is the cheap physical test — not a rewrite in
either direction. Nothing was changed until a hand touched it.

### Third instance, same session — and the trap being written down did not stop it

The two-`scripts/` trap fired again on 2026-08-25, during the walk that
produced the entry above. The shell's cwd reset to `~/code` between commands,
`cat > scripts/rb22_confirm.py` wrote into `~/code/scripts`, `cat >>
docs/TRAPS.md` **created a brand-new `~/code/docs/TRAPS.md`** holding one
orphaned entry, and `git add -A && git commit` committed all of it to the
parent repo. `itq run scripts/...` then found the script anyway — it falls back
to `$PWD` — so the database work succeeded and nothing looked wrong.

Two earlier entries in this file describe this exact failure, and one of them
records a session that had *already read the trap* and hit it anyway. That is
now three. **Reading a trap does not prevent it; the trap is about a state the
shell changes without telling anyone.**

What actually works, and what this session should have done from the first
command: **absolute paths in every write and every `git -C`.** `cd X && cmd`
does not survive to the next call. A redirect is the dangerous form, because
`>` and `>>` create the file rather than failing — a wrong path is silent by
construction, where a read of a missing file at least errors.

## A label is not a bin — three of the rack's "unopened" bins were never bought

The Red Bins location tree was built from the **labels**, and 28 labels were
printed. The rack holds **25 bins**. RB-26, RB-27 and RB-28 existed only as
locations with a label behind them and no container, and every report since has
counted them as unopened bins — the last three on the walk's list, sending
somebody to look for a thing that was never bought.

Scott, 2026-08-25: *"26, 27, 28 do not exist except as labels."*

**Marked `structural=True`, not deleted.** A structural location cannot hold
stock, so the phantom can never receive a part by mistake, and the fact that
three labels were made survives for whoever buys three more bins. Deleting
would have destroyed the only record of that. `scripts/rb_state.py` now counts
structural children separately and reports "25 bins (+3 label-only)".

The general form, and it applies anywhere a location tree is generated:
**making the label is not the same act as owning the container**, and a tree
seeded from a label run will always run ahead of the shelf. The tell is a block
of never-opened locations at the END of a numbered range — the same shape as a
real unwalked block, which is why it survived a whole walk.

## `reference_int` can diverge from the reference it belongs to

Creating the water-valve build on 2026-08-25 produced **BO-0026**, skipping
twelve numbers, when the highest existing build was BO-0013.

The new build was not the problem. `generate_reference()` takes the next number
from `MAX(reference_int)`, and **BO-0013 carried `reference_int = 25`** against
a reference reading 0013. The two fields had diverged at some earlier point, so
every future build would have inherited the jump — and the gap grows, because
each new record writes its own inflated integer back.

Same family as the PO `reference_int` trap already recorded here, and milder
only by luck: there a raw vendor order number clamped the field to int32 max and
broke `generate_reference()` permanently. **This one was recoverable precisely
because 25 is a small wrong number.**

Fixed by putting `reference_int` back in agreement with its own reference
(13), then renumbering the new build into the gap it should have had (BO-0014,
`reference_int` 14). Both writes via queryset `.update()` — `reference` is
format-validated on the model, and `save()` on this install has reported
success and written nothing.

**Worth a periodic check, because nothing surfaces it:** every reference should
satisfy `reference == f"BO-{reference_int:04d}"`. A mismatch is silent, costs
nothing until the next record is created, and then shows up as a number that
merely looks odd.

## An elided vendor title read as a spec — "-3" was the range, not the dial size

#1097 was recorded on 2026-08-25 as a **3-inch dial**. Nobody measured it. The
figure came from the shipping label on the box:

> MEANLIN MEASURE -3… Gauge , Lower Mount

Amazon elides the title on those labels, and the surviving `-3` is the head of
**`-30inHG`**. It is the **range**. The same write-up that invented the face
size went on to say — in bold, twice, as the thing that mattered — that *the box
does not give the pressure range*. **The invented spec was manufactured out of
the exact characters carrying the fact it claimed was missing.**

Nothing about the truncation was hidden. The `…` was right there, and the
Amazon-truncation trap is already in this file. What made it invisible is that
`-3` **parses cleanly as a plausible value** for a real property of the object.
A truncated string does not announce itself when its prefix is well-formed.

**The rule this earns: a spec is measured or quoted from a full source. A
fragment is not a source.** When a vendor string ends in an ellipsis, treat
every field it seems to give as absent, not partial — including the ones that
look complete.

The listing could not settle it either, which is the second half of why the
guess survived a whole session. MEANLIN sells the same −30inHG~0Psi gauge in
**2in, 2.5in and 3in faces and in both 1/8in and 1/4in NPT**; ASIN
`X002SLRYVX` returns no results on Amazon today; and Amazon's order mail
truncates the title as well, so the July 2025 order does not carry it. Every
digital route is closed, and both numbers are **one caliper away** — face
across the bezel, thread OD (1/8 NPT ≈ 10.3 mm, 1/4 NPT ≈ 13.7 mm, not
confusable). Measure the gauge's own thread: a brass compression fitting is
made up on the stem.

---

## Searching for the answer instead of the requirement

Asked "check inventory for the Phase 1 parts," a stock check reported **no
low-current MOSFETs** and offered a 1 k **0805 SMD** resistor for a breadboard.
Both wrong. The drawer at `L2-D4` held 24× 2N3904 and 28× 1 k 1/4 W THT the
whole time.

Neither miss was a search-engine failure. The queries ran were `2N7000`,
`AO3400A`, `RFP30N06LE` — **the parts already chosen**, not the function they
were chosen for. Nothing named `2N3904` was ever asked for, so nothing named
`2N3904` came back. The resistor was worse: the query was right, and the first
hit was taken without reading the other 32 rows in the same category.

**Search the requirement, not the conclusion.** "Small NPN switch" and
"1 k through-hole" are the queries. A part number is a query only when the part
number is itself the requirement.

**And read the whole result set.** These records are decomposed from kits, so
one value legitimately exists in several packages. The first row is not the
answer; the set is.

### Why the wrong answer looked authoritative: two category trees

| Tree | Parts | State |
|---|---|---|
| `Passives/Resistors` | 9 | kit-level records, **all qty 0**, sited at LRD/SLN |
| `Electronics/Passives/Resistors` | 33 | decomposed, real counts, sited to a drawer |

The same split exists for transistors — `#169 Transistor kit, BC337 …` sits at
qty 0 while its ten decomposed children carry 20–24 each. A search that lands in
the legacy tree returns **zeroes that read as "you don't own this."** The kit
record going to zero is correct — it was consumed into its children — but the
two trees make absence and decomposition indistinguishable at a glance.

**Check the category path on every zero before reporting it as a shortage.**

## `allocation_count()` counts the build you are asking about

A coverage check for BO-0002 reported four lines SHORT — SSR, heat sink, tubing,
mains plug — all of them on-hand qty 1. `Part.allocation_count()` returns stock
committed *anywhere*, and those four were committed **to BO-0002 itself**. Stock
reserved for a build is the opposite of stock unavailable to it, so the report
inverted the truth on exactly the lines that were most securely covered.

Subtract this build's own `BuildItem` quantities back out:

```python
BuildItem.objects.filter(build_line__build=bo, stock_item__part=sp
                         ).aggregate(t=Sum("quantity"))["t"]
```

`scripts/canbuild.py` in `~/code` does this and prints `else` (committed to other
work) beside `mine` (reserved for this build) so the two can never merge again.
`Part.can_build` has the same blind spot — it read **0** for an assembly with
every line covered — so do not quote it as the answer for a build order.

## Adding BOM lines after a build order exists

Build lines are snapshotted when the BO is created. New `BomItem` rows do **not**
appear on an existing build order — BO-0003 was completed with 2 of its eventual
7 lines for this reason. After editing an assembly's BOM, call
`build.create_build_line_items()` on every open BO for that part and re-read the
count to confirm.

## `itq run` script arguments are paths on the MINI, not on the laptop

`itq run` ships the *script* to the Mini and runs it there. Everything after the
script name is passed through verbatim and resolved **in the Mini's filesystem**,
which the laptop does not share. So a data file written locally and handed over
as an argument fails with a bare `FileNotFoundError` naming a path that plainly
exists — on the wrong machine.

Measured 2026-08-25 22:5x on the daytime sweep's Section 4:

```
itq run scripts/vendor_triage.py --candidates /tmp/…/scratchpad/cands.json
  -> FileNotFoundError: '/tmp/…/scratchpad/cands.json'
```

Push first, then pass the **remote** path:

```
itq push <local>/cands.json /tmp/cands.json
itq run scripts/vendor_triage.py --candidates /tmp/cands.json
```

This is the same boundary as the `/Volumes/4TB_Removable` rule, in the direction
nobody expects: that rule warns against reading a Mini path locally, and this is
a local path being read on the Mini. The task file's `--candidates /tmp/cands.json`
reads like a scratch path on this laptop and is not — it is the Mini's `/tmp`,
and it only ever worked because an earlier run had pushed something there.

## WRONG — "the overnight window is lost to the browser PREFLIGHT, not to sleep"

> **Superseded 2026-08-26 13:2x by "Every lost window so far is ONE unapproved
> Bash call" at the end of this file.** The preflight was never the cost. The
> browser call this section blames was issued in the same turn as a Bash
> permission prompt and simply waited behind it. Everything below is a correct
> account of *ruling out the clock* and is kept for that; its conclusion about
> where the time went is wrong. Do not act on it.

The wake chain works. `pmset` wakepoweron, the caffeinate agent and the keepalive
all did their job on 2026-08-26: the scheduled session was born at **02:05:07**,
exactly on time. It then reached its first line of real work at **06:54** —
**4 h 49 m** gone, essentially all of it inside the browser preflight, with
McMaster the dominant cost.

**Rule out the clock first, because the symptom looks exactly like a clock jump.**
The journal recorded `RUN STARTED 02:05` and then a `--line` at `06:54` minutes
later by subjective reckoning, which reads as the Mini's clock lurching forward.
It had not. Two independent measurements settle it:

```
stat -f "%SB" ~/.claude/projects/<proj>/<session-uuid>.jsonl   # 2026-08-26 02:05:07
itq run scripts/clock_check.py                                 # Mini  06:58:55 EDT
date                                                           # laptop 06:58:55 EDT
```

The transcript's **birth time on the laptop** is the load-bearing measurement:
it is recorded by a different machine than the one journal.py stamps, so agreement
between the two rules out drift on either. `clock_check.py` exists for exactly
this check.

**2026-08-23 has the identical signature** — `02:05 RUN STARTED` →
`06:57 RUN COMPLETE`, and that run also reported McMaster trouble. Two nights,
same shape, same vendor. It was read as "a long run" both times.

What each site cost, measured:

| site | result |
|---|---|
| Amazon `/gp/css/order-history` | answered promptly; `Hello, Scott`, no sign-in form |
| McMaster home | 1657-char shell, **no** account name, literal `Log in` |
| McMaster `/order-history/` | 714-char pre-auth shell, unchanged across 38 s of polling, after warming the home page; both same-origin iframes empty |

Consequences, in order of how much they cost:

1. **A queue that needs no network must run BEFORE any browser call.** Queue D
   (keywords) is pure Mini-side and finishes in under a minute. Run it first and
   a wedged preflight costs a chunk, not a night.
2. **A slow preflight is invisible.** Nothing times it, nothing reports it, and
   the journal only shows two timestamps that a reader charitably explains away.
3. **"Ran to completion" and "ran in the window" are different claims.** The
   stand-down guard checks only that a `RUN COMPLETE` exists inside the window,
   so a run that starts at 02:05 and finishes at 06:5x satisfies it and reports
   `NOTIFY: none` — while every useful hour was spent on a hung SPA.

Related, and why tonight is journalled `mcmaster=UNKNOWN` rather than `OK`:
`localStorage.VSTR_USR_NM` read `Scott Dube` throughout. That is **not** proof
of a live session — localStorage persists, so it only proves someone signed in
at some point. The open decision item `mcmaster-preflight-false-pass` already
says so. Every absence-based *and* every storage-based test for this vendor has
now failed; the only signal that has held is post-click UI.

## RESOLVED — McMaster auth has a reliable UI signal after all: wait ~30 s, then read the login control's own text

**2026-08-26 08:50, measured, daytime sweep.** The two earlier sections above
(`the test could never have said "signed in"` and the `VSTR_USR_NM` correction)
left the procedure in a bad place: the localStorage key is persistent and so
can only ever produce a false pass, and the recommended fallback — a real click
on `#LoginUsrCtrlWebPart_LoginLnk` — needs a screenshot-frame coordinate that
is easy to get wrong silently. Today's run found a third signal that needs
neither.

**The masthead is a cached shell, but it is not permanently cached — it
resolves on its own.** Two independent things flip once account state lands:

| | cold load (t≈3 s) | after ~30 s |
|---|---|---|
| `#LoginUsrCtrlWebPart_LoginLnk` text | `Log in` | **`Scott Dube`** |
| masthead phone | **(630) 833-0300** — Elmhurst IL, generic | **(609) 689-3000** — Robbinsville NJ, the account rep line |
| `VSTR_USR_NM` | `Scott Dube` (stale, proves nothing) | `Scott Dube` |

Measured sequence today: at t≈3 s the link read `Log in` and the screenshot
masthead showed (630) 833-0300; a click was attempted at the
`getBoundingClientRect` x (1679) which — exactly as the open decision item
predicted — did nothing, since the screenshot frame is only 1416 px wide
against `innerWidth` 1728. By the next read the link text was `Scott Dube` and
the phone was (609) 689-3000 **without any successful click**. Time, not the
click, is what populates it.

**The test to use, in this order:**

1. Load `mcmaster.com`, wait ~30 s (or poll the link text).
2. Signed in ⇔ `document.querySelector('#LoginUsrCtrlWebPart_LoginLnk').innerText`
   is **not** `Log in` and matches the account name.
3. Corroborate with the phone: generic (630) 833-0300 = signed out, an account
   rep line = signed in. Two independent signals, neither of them storage.

`VSTR_USR_NM` is now a **corroborating** read only, never the deciding one.
Note `hasLogOut` was false in the DOM text — the Settings/Log Out items live
behind a dropdown, so do not test for `Log out` in `body.innerText`; test the
link text.

**Why this matters beyond the daytime sweep:** the open decision item
`preflight-eats-the-window` blames the McMaster preflight for 4h49m of a lost
night. A test that is a fixed ~30 s wait plus one DOM read has a bounded cost
and cannot hang the way polling `/order-history/` for a shell that never
renders did. This does not by itself fix the overnight budget problem — the
recommendation there (network-free work first, hard preflight budget) still
stands — but it removes the reason the preflight was slow in the first place.

## vendor_triage keys on the SENDER DOMAIN — a synthetic sender always comes back "unknown"

**2026-08-26 09:0x, measured, daytime sweep.** Section 4's discovery step found
a genuine non-email purchase on `shop.app` (MFC Machining & Design Services,
order #MFCMD1086, ArmorGuard Tormach way covers, $349.95 + $29.95 shipping,
paid over Affirm installments). Since there was no email, the candidate was fed
to `vendor_triage.py` with an invented sender string, `shop.app-installments`.

Triage bucketed it **unknown — "needs a call"** and emitted a `decide.py` line.
That was wrong twice over:

1. MFC **is** in `vendor_registry.json` (by Shopify store id `70819512477`).
2. MFC **is** already a Company in InvenTree, and the order was **already
   imported as PO-0140**.

The classifier buckets on the sender's **domain**. An invented sender matches
nothing, so it is guaranteed to fall through to `unknown` no matter how well
known the vendor actually is. Feeding it one manufactures a false decision-queue
item for a vendor that is fully handled.

**Rule: never invent a sender to get a non-email purchase through triage.**
Non-email purchases (Shop Pay installments, Walmart in-store, anything found by
reading an account page rather than a mailbox) are outside what triage can
classify. Take them straight to `po_check <order-no>` — that is the idempotency
key and it answers the only question that matters. Only if `po_check` says
`absent` does the purchase need a decision line.

This is the mirror image of the open item `vendor-triage-no-idempotency-check`:
that one is triage surfacing an order InvenTree already has because triage never
asks InvenTree. Both fixes are the same one — **ask `po_check` first, and let
triage classify only things that genuinely arrived as email.**

## The pack price arrives on the LINE too — and by then pack_quantity is the wrong lever

2026-08-26, receiving PO-0139 (Amazon 113-5011479-9313006, SHT31-D breakouts).

The confirmation sweep auto-creates a PO line from what the order page states,
and an Amazon order page states a **grand total against one "item"**. So the
line was written **`qty=1 @ $16.99`** for an ASIN that ships **four pieces**.
Supplier part 193 carried `pack_quantity=1`, so receiving it unrepaired would
have created **one** stock row of **one** sensor at **$16.99** — the $208.62 bin
error again, reached through a different door. The previous purchase of the
identical ASIN (PO-0028) had been entered `qty=4 @ $4.25`, so the same SKU had
two contradictory shapes on file and only the *unreceived* one was wrong.

**The sweep cannot tell a 1-piece order from an N-piece pack**, because the
order page does not say. Every auto-created line is therefore *suspect on
quantity* until a human has the box. Check the line against the pack size at
**receiving time** — that is the one moment the truth is in the room.

**Which lever to pull depends on whether the SKU has already been received.**
The bins fix above raised `pack_quantity` at the root, correctly: no receipt had
happened yet. Here PO-0028 was already **Complete** with 4 pieces booked against
a 4-unit line. `pack_quantity` is read at receive time and is not versioned, so
raising it to 4 would have made that finished receipt reread as **16 pieces**.

- **No completed receipt for the SKU** → fix `pack_quantity` on the supplier
  part. It is the durable fact and it fixes every future receive.
- **A completed receipt already exists** → fix the **line** (`quantity` and
  per-piece `purchase_price`) and leave `pack_quantity` alone. Say in the line
  notes why, or the next session will "helpfully" fix the root and silently
  quadruple history.

**A per-piece price with more than two decimals is not a rounding bug.**
$16.99 / 4 = **$4.2475**. The UI renders `$4.25` and the instinct is to store
$4.25 — which turns the order into $17.00. `purchase_price` has
`decimal_places=6`; store the exact quotient and let the display round. Verified:
stored `Decimal('4.247500')`, line total `16.99000000000`.

## Every lost window so far is ONE unapproved Bash call, waiting for a click

Three separate write-ups blamed three different subsystems for the same
symptom — a run that starts on time and reaches real work hours later. All
three were wrong, and each cost a night before the next one replaced it:

| Blamed | Written | Actually |
|---|---|---|
| Idle sleep | 2026-08-25 | Fixed, and the symptom continued |
| The browser preflight (McMaster) | 2026-08-26 07:05 | A casualty, not the cause |
| Gmail call size / browser round trips | 2026-08-26 13:07 | Never measured, just plausible |

**Measured 2026-08-26 from the run transcripts.** Both of that day's lost
windows are a single Bash tool call whose result arrived hours later with
`is_error: False` — the signature of a permission prompt that a human
eventually clicked, not of anything slow:

| Run | Call | Stalled |
|---|---|---|
| 02:05 overnight `46785ba4` | `~/code/scripts/itq pull …` | **286.8 min** |
| 08:46 daytime `75e20072` | `for o in …; do itq run po_check.py; done` | **250.7 min** |

Two different ways to miss the allow list, one outcome:

* **Path form.** The rule was `Bash(/Users/scottdube/code/scripts/*)`. `~/code/…`
  is a different literal string, so nothing matched. Approving it at 06:52 is
  what put `Bash(~/code/scripts/itq pull *)` into `settings.local.json` — the
  rule's own existence is the fossil of the four hours it cost.
* **Compound shape.** A `for … do … done` loop can never match a rule. This is
  the documented `one stable command shape` failure, and the loop was not even
  necessary: `po_check.py` takes `nargs="*"`, so one call with four order
  numbers returns exactly what the loop returned.

**How to tell this apart from a slow subsystem, in one measurement.** Do not
reason about which subsystem "feels" slow — diff the timestamps of adjacent
records in the session `.jsonl` and look at the *distribution*. A slow
subsystem spreads its cost over many calls. A permission stall is one gap
holding essentially the whole window:

    gaps >=2min: 2, total 4.26h of 4.43h      <- 08:46 daytime
    gaps >=2min: 2, total 4.83h of 5.01h      <- 02:05 overnight

The tell is the ratio of tool calls to wall time. The 08:46 run made **60 tool
calls in 4 h 26 m**; the 13:14 run made **51 tool calls in 12 minutes** doing
strictly more work (it created two POs; the 08:46 run created none). Same
procedure, same sites, same vendors. Nothing was slow.

**The browser error is downstream, and it is what sent the last diagnosis
wrong.** The overnight `navigate` was issued in the same turn as the stalled
`itq pull`. When the prompt finally cleared 4 h 47 m later, the tab it named
was long gone and it returned `Tab 1602223450 no longer exists`. A browser
failure at the end of a browser-shaped delay is extremely convincing and was
entirely an artefact.

**Corollary worth stating plainly.** The 13:14 run that found all this had
itself written `for o in …; do itq …; done` twice, and got away with it only
because Scott happened to be at the keyboard. Knowing the rule is not the same
as following it; the shape has to be impossible to reach for, not merely
discouraged.

## The location label's name field silently overprinted the breadcrumb at 11 characters

2026-08-26, printing the new LINEAR MOTION bin.

`Shop Location 62mm (QR + Text)` (template 9) pinned the name at `top: 4mm`,
`font-size: 6mm`, and the breadcrumb at `top: 11mm`. **"Adhesives" fit on one
line. "Linear Motion" did not** — it wrapped, and the second line printed
straight through `WS2-S4`. The render is legible-looking ink in exactly the
right place, which is why nothing automated could have caught it.

This is LABELLING.md's own WeasyPrint rule firing for the first time on a
location: `overflow: hidden` is ignored on an absolutely-positioned block, so
the overflow does not clip, it overprints.

**Why it had never bitten before:** every location labelled up to now was a
DRAWER CODE — `BR-D3`, `A3-R8C6`, `WS2-S4`. Four to seven characters. The
template was authored against that and the assumption was never written down.
Bins broke it because a bin is named for what is in it, and topic names are
words. `Electrical`, `Plumbing`, `Air System` were all already in the tree and
would each have failed the same way the moment anyone printed one.

**Fixed by sizing the name to the name.** WeasyPrint has no auto-fit, so the
template picks a font size from `location.name|length` and sets
`white-space: nowrap` so a miss can never hide itself in a wrap again:

| chars | size | fits ~35 mm of usable width |
|---|---|---|
| ≤ 10 | 6.0 mm | `Adhesives`, `Plumbing` |
| ≤ 13 | 4.6 mm | `Linear Motion`, `Air System` |
| ≤ 17 | 3.6 mm | |
| more | 2.9 mm | plus `truncatechars:22` as a backstop |

**Renaming the bin was the wrong fix and was considered first.** "Motion" would
have printed cleanly and left the template broken for the next word-named bin —
and the bin wall is going to accumulate them, because that is what the bin
pattern is for.

**The template lives in the DATABASE, not in the repo.** `labels/` holds the
source; the file InvenTree actually renders is
`<MEDIA_ROOT>/report/label/location_62mm.html` on the Mini. Editing the repo
copy alone changes nothing. Push it:

```
itq push labels/location_62mm.html /Volumes/4TB_Removable/inventree/data/media/report/label/location_62mm.html
```

No restart needed — the template is read per render.

## Renaming a location with `.update()` leaves `pathstring` telling the old name

2026-08-26, renaming the bin from "Linear Motion" to "Bearings & Motion".

`StockLocation.objects.filter(pk=587).update(name=...)` wrote the name and
returned success. The very next read showed:

```
name       = 'Bearings & Motion'
pathstring = 'SLN/Storage/WS2/WS2-S4/Linear Motion'
```

**`pathstring` is denormalised and rebuilt in `save()`.** A queryset `.update()`
goes straight to SQL and never runs it, so the row contradicts itself — and
`pathstring` is what the UI breadcrumb, the location picker and every
`pathstring__icontains` search actually read. The rename would have looked done
and been invisible to search.

This is the **same shape** as `pack_quantity` / `pack_quantity_native` earlier
in this file, and the general rule is worth stating once: on this install,
`.update()` is the right tool when a plain column is being written and the WRONG
tool whenever `save()` derives something from that column. The two known cases
are both names-and-caches; assume there are more.

Fix is `.save()` on the instance, then verify the derived field, not the one
you set:

```python
l = StockLocation.objects.get(pk=587)
l.name = "Bearings & Motion"
l.save()
l.refresh_from_db()
assert "Linear Motion" not in l.pathstring
assert not StockLocation.objects.filter(pathstring__icontains="Linear Motion").exists()
```

The second assert is the one that matters — children carry the parent's path in
their own `pathstring`, so a rename with descendants can leave a whole subtree
stale even after the renamed row itself looks right.

## `stocktake()` is a no-op when the count matches — so the DATE never lands

2026-08-26, confirming the MGN9 rails at 2.

```python
si.stocktake(2, user, notes="Counted in hand by Scott.")
# quantity 2 -> 2, stocktake_date: None -> None
```

InvenTree's `stocktake()` short-circuits when the counted number equals the
stored one. Nothing is written, nothing errors — the same silent-success shape
as `.save()` elsewhere in this file.

**The bug is that quantity and `stocktake_date` are two different claims.**
The number says *how many*; the date says *somebody looked*. Confirming a
quantity that was already right is a real stocktake and is exactly the case
where the date is most valuable — it converts an estimate into a count without
changing a digit. The no-op throws that away and the row keeps reading
never-counted.

The LM8UU row the same afternoon went 12 → 10 and got its date automatically,
which is why this is easy to miss: **the method works whenever it changes
something, and silently fails to record precisely the confirmations.** Those
are the majority of stocktakes on a shelf that is basically correct.

Set the date explicitly after any confirming count:

```python
StockItem.objects.filter(pk=pk).update(stocktake_date=datetime.date(Y, M, D))
```

And verify the DATE, not the quantity — the quantity was never going to be
wrong, which is the whole reason the failure hides.

## The McMaster import booked four years of ORDER HISTORY as if it were stock

2026-08-26. Scott, on four unlocated rows: *"used on repair projects."*

Those four were the two needle-roller thrust bearing sets — and the purchase
record says exactly what happened:

| PO | issued | contents |
|---|---|---|
| PO-0126 | **2022-08-01** | 5909K25 bearing + 2× 5909K251 washers (3/8") |
| PO-0125 | **2022-10-04** | 5909K35 bearing + 2× 5909K48 washers (7/8") |

Single quantities, bearing and washers on one order, four years ago. **That is
the shape of a repair, not of stock.** They were never lost — they were fitted,
and the catalogue has been carrying them as owned ever since.

**The import equated "you ordered this" with "you have this."** It read
McMaster order history and created a stock row per line, at the ordered
quantity, with no location. That is a defensible way to seed a *parts
catalogue* and an indefensible way to seed *stock*, because a purchase four
years old says nothing about what is on the shelf today.

**Scale, measured 2026-08-26:** 47 unlocated rows carry stock > 0. Aged by the
issue date of their earliest PO:

| ordered | rows | |
|---|---|---|
| 2021 | 1 | |
| **2022** | **19** | four years old |
| 2023 | 7 | |
| 2024 | 6 | |
| 2026 | 4 | the SHT31s and friends — a different problem |
| no PO | 10 | ZVS induction kit, supplied-with-kit items |

**33 of them predate 2025.** Every one asserts a quantity nobody has seen.

**What survives the doubt and what does not.** Consumables bought by the
hundred (100 washers, 250 spring pins, 100 steel balls) are probably still
largely there — nobody uses 100 M5 washers on one job. **One-off single
quantities bought alongside their own mating parts are the suspect class**, and
that is precisely what the thrust bearings were. Triage that way rather than
row by row.

**The fix is not to delete them.** A part record with a McMaster number is worth
having even at zero. Zero them *with the reason*, per stock 341's rule: a zero
with an explanation is a fact; a zero without one is a question that costs
somebody a trip to the bench.

## Taking stock to zero DELETES the row, explanation and all

Same afternoon, zeroing those four:

```python
si.take_stock(si.quantity, user, notes="Consumed on a repair project.")
si.refresh_from_db()   # StockItem.DoesNotExist
```

`delete_on_deplete` defaults **True**, so InvenTree removes a stock item the
moment it hits zero. Stock 522 was destroyed that way — along with the note
explaining why it was zero, which was the entire point of zeroing it rather
than deleting it.

The two rules collide head-on: *keep a zero with its explanation* cannot be
carried out with `take_stock` alone. Clear the flag first, and on a row you are
creating at zero, set it at creation:

```python
StockItem.objects.filter(pk=pk).update(delete_on_deplete=False)
si.refresh_from_db()
si.take_stock(si.quantity, user, notes=...)
assert StockItem.objects.filter(pk=pk).exists()      # verify the ROW, not the qty

StockItem.objects.create(part_id=ppk, quantity=0, delete_on_deplete=False)
```

Assert on the row's existence. Reading the quantity back cannot detect this —
there is nothing left to read it from.

## shop-inventory is a NESTED git repo, and the shell's cwd resets to ~/code

2026-08-26. Eight commits of inventory work — the bearing scripts, three new
traps — landed in **`~/code`** instead of here, and two earlier ones carried
inventory commit messages over completely unrelated files.

Two known hazards combined into a third that neither one predicts:

1. `~/code/CLAUDE.md` already warns that **the shell's cwd resets to `~/code`
   without warning**, which is why `itq run` resolves a bare relative path
   against the repo rather than `$PWD`.
2. **`shop-inventory/` is its own git repo inside `~/code`**, not a submodule.

So `cat > scripts/foo.py` written after a cwd reset creates
`~/code/scripts/foo.py`, and `git add -A` from `~/code` commits it there
happily. Neither command errors. And `~/code/docs/` exists too, so
`cat >> docs/TRAPS.md` silently **created a second TRAPS.md** in the wrong repo
rather than failing.

`itq run scripts/foo.py` then still WORKS — it falls back to `$PWD` — so the
script runs, the write to InvenTree succeeds, and nothing looks wrong until
somebody goes looking for the script in this repo and it is not here.

**Use absolute paths for both halves.** Not `cd` — `cd` is what fails:

```bash
cat > /Users/scottdube/code/shop-inventory/scripts/foo.py <<'EOF'
...
EOF
git -C /Users/scottdube/code/shop-inventory add -A
git -C /Users/scottdube/code/shop-inventory commit -m "..."
```

`git -C <path>` is the important half. A `cd X && git commit` chain reads as
atomic and is not: the `cd` is one command's worth of state that the next tool
call may not inherit.

**The tell that something has gone wrong is a commit whose message does not
match its diff.** `git show --stat HEAD` after committing costs nothing and is
the only cheap check — a message about receiving a PO sitting on top of a
one-line settings change is the signature.

## Order history shows a TRUNCATED listing title — never take a quantity from it

2026-08-26. The 30203 tapered rollers went in as **2** and are **5**.

Three sources, and the two I used were both the same second-hand one:

| source | says |
|---|---|
| bag label | "2 Sets 30203 Tapered Roller Bearing 17x40x12mm" |
| Amazon **order history** | "2 Sets 30203 Tapered Roller Bearing 17x40x12mm" |
| the **listing** (ASIN B077KFZL1K) | "…**2-Sets** of Metal Bearings **- 5 pcs**", and "INCLUDES: **5 pc**" |
| Scott, counting boxes | **5** |

**The seller's title contradicts itself**, and order history had truncated away
the half that was right. The order details page compounded it: one line, no
quantity multiplier, `$19.99` — which reads as "one unit" and *is*, because the
one unit contains five.

**A quantity from order history is second-hand and truncated.** It is fine for
answering *did we buy this and when*. It is not a count and it is not even a
reliable pack figure — the pack figure lives in the listing's contents bullet,
which is the only field on Amazon that is trying to state contents rather than
attract a click.

Scott caught it by counting boxes on the bench. That is the third time in one
afternoon that a bench count has beaten a printed number:

- LM8UU: bag said 12, bench said **10**
- 30203: label and order said 2 sets, bench said **5**
- MGN9 carriages: I could not tell from a photo, bench said **2**

**Where this leaves the tiers.** "Card-stated" was already `[ESTIMATE]`; this
adds that a *seller's* stated figure can be internally inconsistent, not merely
stale. When the label and the listing disagree, neither is evidence — go and
count. And when only the label is available, say which one it came from, so the
next person knows there is a second source worth opening.
