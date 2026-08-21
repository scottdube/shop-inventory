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
- **`default_location` is where a spare goes home** — never a project bin, never
  a staging area.
- **Check for a duplicate before creating a part.** Two importers have already
  entered the same item twice under different names.
- Prices not verified live get **+40%** and are marked as estimates.

## Capture as you go

Write findings down **in the same turn they are learned**, not at session end —
end-of-session capture fails in exactly the case it matters. Corrections and
surprises go in `docs/TRAPS.md`; rulings-out go in the subsystem doc *with what
eliminated them*; physical facts go on the part or location notes.

Scott may say **`checkpoint`** — flush everything not yet on disk.

Commit at every milestone. The message says **why the obvious alternative was
not chosen**; the diff already shows what changed.
