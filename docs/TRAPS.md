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
