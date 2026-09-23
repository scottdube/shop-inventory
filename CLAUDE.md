# shop-inventory

InvenTree instance for the SLN/LRD shop. **Read this before touching anything;
it exists so each session starts where the last one ended.**

## Read first, by task

| Doing this | Read this first |
|---|---|
| Anything at all | `docs/TRAPS.md` — every trap here was paid for once already |
| Printing labels | `docs/LABELLING.md` |
| Working a long session | `docs/CONTEXT.md` |
| Bagging / physical handling | `docs/TECHNIQUES.md` |
| "do we own one?" / buying a tool | `scripts/trip.py where <terms>` — it may be at the other site |
| Moving things between SLN and LRD | `docs/TECHNIQUES.md` — `trip.py` for tools, `florida.py` for consumables |

## How to run things

**One command shape:** `scripts/itq run <local.py>` ships a script to the Mini
and runs it under the venv. Also `itq push`, `itq pull`, `itq sql`. Do not
hand-build ssh/scp/heredoc chains — 243 one-off permission grants accumulated
before this existed, and none of them ever matched twice.

`itq run` does **not** bootstrap Django. Scripts must call `django.setup()`
themselves. Only `itq sql` bootstraps.

Restart InvenTree with `launchctl kickstart -k gui/$(id -u)/com.inventree.server`.
**`kill -HUP` is not a restart** — it returns HTTP 200 and serves *truncated*
static files. Verify by md5 of served vs on-disk, never by grepping for a
new function.

## Invariants

- **Verify every write.** `.save()` on this install has reported success and
  written nothing. Re-read the row; fall back to queryset `.update()`.
- **Never invent a count.** A quantity nobody counted is how a stock system
  starts lying. Record "not counted" and say so.
- **Photographs show identity, not quantity, fullness, or provenance.** Read the
  label from a photo; ask a person for the count. Three misreads in one morning
  produced this rule.
- **Measure, don't model.** When measurement is cheap, go measure. Analysis
  outrunning the build is the recurring failure here.
- **One stock row per part per location.** Once goods are in inventory the shelf
  answers *how many do I have*, in one number — not a line per purchase that has
  to be added up in your head. Buying more of something MERGES into the existing
  row; the purchase orders and the row's notes carry where it came from. Split
  rows are for things that are genuinely not interchangeable: serialised items,
  a different status (damaged, quarantined), a real batch or expiry difference,
  or a different location. Scott, 2026-08-25: *"once they go into inventory they
  should be a combined qty"*.
- **A pack is a supplier fact, not a part.** Stock is counted in PIECES; the
  supplier part carries `pack_quantity`. Get that wrong and the pack price is
  booked against every piece — 19 storage bins read $208.62 instead of $20.86.
  If a part NAME says "10 pack" while its quantity counts pieces, the name is
  the bug.

  **RECEIVE WITH THE SCRIPT — it does both halves:**

  ```
  itq run scripts/receive_po.py PO-0146 --to RB-14           # dry run
  itq run scripts/receive_po.py PO-0146 --to RB-14 --commit
  ```

  It honours `pack_quantity`, merges into the existing row, refuses to run when a
  SKU says "pack" and `pack_quantity` says 1 — and **closes the order**.

  **Both halves matter and each was got wrong once, on the same day.**
  InvenTree's own `receive_line_item()` ignores `pack_quantity` and books the
  whole pack price against one piece. Hand-rolling it avoided that and lost the
  other half: setting `line.received` satisfies the LINE and leaves the ORDER at
  PLACED, so a fully-received order ages into OVERDUE. Scott found three sitting
  like that on the purchasing screen. **Receiving a line is not closing an
  order.**

  Measured 2026-09-01: **688 of 706 supplier parts carried `pack_quantity = 1`**.
  Scott: *"we seem to have this problem every time we buy something that comes in
  a multipack."* He was right, and the cause is not misinterpretation — nothing
  ever asks the question. Importers build supplier parts from order lines that
  read "1 x <seller's title>" whether that is one screw or a bag of fifty, so
  InvenTree's default of 1 sticks and the pack size stays buried in the title.
  It surfaces only when goods land and the price per piece is absurd.

  **An assortment is not a multipack.** A 480-piece capacitor kit of 24 values is
  ONE unit, not 480 interchangeable pieces; `pack_audit.py` separates the two, and
  if a kit's contents must be findable it becomes a LOCATION (see TECHNIQUES.md),
  never a pack.

  **The pack is stored TWICE and only `pack_quantity_native` is read at receive
  time.** `clean()` derives it from the text field and `save()` calls `clean()`,
  so a queryset `.update(pack_quantity='5')` changes what every screen shows and
  nothing that counts — five supplier parts were in that state on 2026-09-03.
  **Write pack sizes through `.save()`, never `.update()`**, which is the one
  place the usual advice on this install is reversed. `pack_audit.py` now
  compares the two fields to each other; `fix_pack_native.py` repairs them.
  Corrected the same day: `receive_line_item` does **not** ignore the pack — it
  multiplies by native and divides the price to match, so a line whose supplier
  part is correct needs no hand repair. See `docs/TRAPS.md`.
- **`default_location` is where a spare goes home** — never a project bin, never
  a staging area.
- **Check for a duplicate before creating a part.** Two importers have already
  entered the same item twice under different names.
- **Installed infrastructure is not an inventory item.** When leftovers turn up
  from an install, record the LEFTOVERS and put the order in their notes; do not
  offer to add the device that is wired into the building. Scott, 2026-09-23, on
  the Emporia Vue 3 whose spare CTs were being filed: *"its not really a
  inventory item."* Shop MACHINES are the separate case and do belong — they get
  moved, lent and consumed against; a panel-mounted monitor never will be.
- Prices not verified live get **+40%** and are marked as estimates.

## Buying tool holders

**Every BT30 holder needs one pull stud, and the HOLDER decides which kind.**
Before a holder goes on any order:

```
itq run scripts/stud_check.py --shrink N --holders N
```

Shrink-fit holders MUST take a TSC (drilled) knob. This is **not** about
coolant — the 1100MX has no through-spindle coolant at all. The hole is the
passage a welding wire runs up to push out a stuck shank during heat-shrink
removal, and it vents the blind bore (which is why `shrink-fit` dropped its
spring hold-down, MR-16). A solid knob undoes both, and you find out with a hot
holder in your hand. See `docs/TRAPS.md`.

Deliberately not a reorder point: studs are bought in 10-packs and holders two
or three at a time, so a minimum-stock rule would nag to hold ten in reserve
forever. The check speaks only when a specific order needs studs added.

## Keep replies short

Scott is usually at the bench while reading. **Lead with the result in a line or
two, then stop.** Reasoning, ruled-out options and trap write-ups go in `docs/`
and the commit message — searchable later, out of the way now. Surface detail
unprompted only when it changes what he should physically do next, or when it
costs money.

## Capture as you go

Write findings down **in the same turn they are learned**, not at session end —
end-of-session capture fails in exactly the case it matters. Corrections and
surprises go in `docs/TRAPS.md`; rulings-out go in the subsystem doc *with what
eliminated them*; physical facts go on the part or location notes.

Scott may say **`checkpoint`** — flush everything not yet on disk.

Commit at every milestone. The message says **why the obvious alternative was
not chosen**; the diff already shows what changed.
