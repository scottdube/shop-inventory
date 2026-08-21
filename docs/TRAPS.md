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
contents. Trust that sentence, never `count() == 0`. Counting rows says A1 and
A2 are 128/128 empty; their descriptions carry legacy labels like `M3 .5 x20`,
and they are cabinets full of uninventoried hardware.

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

### Most IPNs here are Amazon ASINs
`IPN` is "B017KUC6XQ" for most of the imported catalogue — useless on a label.
Print the default_location instead; where a part lives is what you need
standing at the drawer.
