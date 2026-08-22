# binscan — photograph a drawer, get a fill estimate

**It is not in this repo, and that is why it went missing.** Recovered
2026-08-22 after Scott referred to it and nothing in `~/code` matched; the only
trace on this laptop was a screenshot in `~/Downloads` of Safari failing to
resolve the hostname.

## Where it lives

| | |
|---|---|
| host | the LRD Mac Mini — `binscan.internal` resolves to `192.168.50.10` |
| code | `binscan/` in this repo as of 2026-08-22; deployed to `/Users/scottdube/binscan` |
| process | `uvicorn app:app --host 0.0.0.0 --port 8002`, LaunchAgent `com.binscan.plist` |
| public port | 80, via Caddy (`com.caddy.proxy.plist`) |
| state | `log.jsonl` (run history), `shots/` (submitted photos), `env` (API keys, mode 600) |
| versioning | `app.py.prelog`, `app.py.prepicker`, `app.py.prewrite` — copies, by hand |

**Phone access works.** A screenshot dated 2026-08-18 shows Safari failing to
resolve the hostname, and that was taken as the current state — wrongly. Scott,
2026-08-22: *"that photo must have been before we resolved the problem because
I'm on binscan right now."* A dated screenshot records the moment it was taken,
not the state of the world; treat one as evidence about the past only.

## What it does, and what it deliberately does not

Pick a drawer, photograph it, pick a vision provider, get a fullness estimate.
**Read-only to InvenTree** — it reads locations and parts and writes no stock,
on the stated grounds that a bin-check tool which silently writes bad numbers is
worse than no tool. Every run is logged for comparison at `/log`.

From its docstring: *the model is NOT asked to identify the part — the drawer
address already determines that, so its only job is "how full is this", which is
the thing vision is actually good at.* It is told to report LOW confidence on
heaps, *because occlusion makes 200 small parts look like 150 and prompting
can't fix physics.*

Providers configured: `anthropic` (claude-sonnet-5) **available**; `ollama`
(qwen2.5vl:7b) and `openai` (gpt-4o) present but not configured.

## Measured accuracy — 13 runs 2026-08-16, six with ground truth

| actual | anthropic | haiku-4.5 | sonnet-5 |
|---|---|---|---|
| 4 | off by 0 | off by 1 | off by 0 |
| 4 | off by 1 | **off by 41** | off by 0 |
| 5 | off by 0 | off by 5 | off by 0 |
| 20 | off by 15 | off by 5 | off by 5 |
| 65 | off by 15 | off by 5 | off by 25 |

**Usable below about five. Unreliable above about twenty**, where the error runs
25-40% and does not degrade predictably — the 41-off case was a four-piece
drawer read as forty-five. This is the measurement behind "photographs show
identity, not quantity": the rule is not superstition, it has a shape, and the
shape is that occlusion beats the model as soon as parts overlap.

## The identify mode — added 2026-08-22

**The record is consulted before the camera.** Picking a drawer calls
`/api/drawer`, which is free and instant and reports what InvenTree already
holds for it — counting stock in the drawer *or any descendant*, so a drawer
holding an assortment kit does not read as empty. Scott: *"look to see if the
bin has something assigned already before you have AI go look for it."*

The drawer's state then picks the mode, so there is no toggle to set wrongly:

| drawer state | job | what runs |
|---|---|---|
| already assigned | how many are there | the original estimate flow |
| nothing on record | which part is this | `/api/identify` |

`/api/identify` asks the model to **read text, not to identify the part** — the
McMaster bag tag, any Brady or handwritten label, any stamping. Matching against
the 48 unlocated rows happens in Python in `match_reading()`, because a model
asked to choose from a candidate list always chooses, while a number either
matches a SKU or does not. Results are graded `definite` (tag matches one SKU
exactly), `probable`, or `ambiguous`, and the basis is reported — `tag`,
`partial-tag`, `label-text`, `tag-no-match`, `nothing-legible`.

The model is told to transcribe rather than correct, and to write `?` for a
character it cannot read. A plausible completion of a part number is worse than
a short answer, because a wrong McMaster number matches a real and different
part.

**Still read-only.** It proposes; nothing is written. Seven matcher cases pass,
including the one that caught a real bug: a drawer label reading `M3 .5 x20`
matched an *M6* x 20 socket head, because the thread regex expected McMaster's
`M6 x` spelling and found no thread at all in the label's, leaving length as the
only evidence.

## Auto-advance

After a submit the drawer selector moves on by itself — **across** the row,
**down** the column, or **stay**. Scott, 2026-08-22: re-finding your place in a
324-entry select every time was *"one of the things that was a problem in
binscan as it was originally put together."*

**The next drawer comes from the option list, not from incrementing a number,**
because the grid is irregular. B rows 1-4 are eight wide and rows 5-7 are four,
so C5 has no neighbour below it: `R4C5` going down is `R1C6`, skipping
R5C5/R6C5/R7C5, which do not exist. Incrementing would land on a drawer that is
not there. Walking the real list also means the last drawer differs by
direction — across ends at `R7C4`, down ends at `R4C8`. Ten ordering cases pass,
including both ends and both crossings between the small and large row bands.

Advancing clears the photo and disables the button, so the next drawer cannot
be submitted with the previous drawer's picture. The result of the last read
stays on screen. For an estimate, the drawer address is captured when the
"record actual" card is built rather than read at click time — otherwise the
actual count would be filed against whichever drawer had been advanced to.

## The picker

A 478-entry select was the wrong control on a phone. Scott, 2026-08-22: reaching
B3 meant scrolling past everything *"and b three is not even at the end."*

Two stages now. `/api/areas` returns places you can stand — the six bin-wall
cabinets as chips, the other 21 behind an "elsewhere" toggle. A drawer that
holds an assortment kit has a child location and so looked like an area;
`A3-R8C5` and `B3-R3C2` were listed alongside the cabinets until drawer-shaped
names were filtered out.

Picking one calls `/api/grid`, which returns every drawer in the area with
enough state to colour it, in one request. **The grid mirrors the cabinet** —
eight-wide rows 1-4, four-wide large rows 5-7 — so you tap the drawer where it
physically sits, and the picker doubles as a progress view: filled / unknown /
verified empty, with a tally.

That colouring found its own bug. The first version matched stock to drawers by
pathstring text, but the stock endpoint does not return `location_detail` unless
asked, so every match was against an empty string and B3 — 41 stocked drawers —
reported as entirely unfilled. Resolved by primary key now, walking parents up
to the cabinet's direct child, which also handles kits.

## Filing: the first thing binscan writes

`/api/assign` moves a stock row into a drawer. Added 2026-08-22 after a field
test: Scott photographed a B2 drawer whose tag was only a description, and the
label-text path identified the part correctly — *"it actually figured it out
exactly what they were, minus the quantities."*

**Two facts, deliberately kept apart:**

| | established by | recorded |
|---|---|---|
| the DRAWER | a person looking in it | always |
| the COUNT | a person typing a number | only if they did |

The count box is **blank on purpose**. The quantity already on the row came from
a purchase order — a real record of what was BOUGHT, not of what is there.
Leaving it blank moves the row and says so in the note; typing a number records
a count. Promoting the first silently into the second is how a stock system
starts lying.

Guards: writes must be enabled, `confirm` must be explicit, the location and
stock item must resolve, the quantity must parse and be non-negative — and the
result is **verified by re-reading the row**, returning 500 if location or
quantity did not land. Round-trip tested against stock 473 with a rollback.

**No model output reaches this endpoint.** The match is a proposal; a person
confirms it with the drawer open. The drawer name is bound when the card is
rendered, not when the button is clicked, because auto-advance changes the
current drawer immediately after — otherwise the second drawer of a walk
collects the first drawer's contents.

## Imperial matching was broken, and a field test found it

Scott photographed a B2 drawer on 2026-08-22. The read was perfect —
`10/32 NF X 3/4 · PHILLIPS FILLISTER M/S`, legibility "clear" — and the matcher
said no row fitted. B2 holds `91737A210`, a 10-32 fillister head. Two bugs, both
in `_facts()`:

1. **The imperial thread regex demanded a fraction before the dash.** It read
   `1/4-20` and never `10-32`, so machine-screw sizes failed on the label AND on
   the part name. Since B2 *is* the imperial cabinet, nothing in it could match.
2. **There was no imperial length extractor at all** — only `N mm Long`. `3/4"`
   was invisible.

Then two more found while fixing those: McMaster spells it `1/4"-20`, and the
inch mark between diameter and dash blocked the match; and once the thread was
found, the length search read the thread's own `1/4"` as the length, making
every quarter-inch screw look a quarter-inch long. The thread's span is now
excluded from the length search.

A vendor label may also write the number form with a slash — `10/32` — which
collides with fraction notation. Resolved by plausibility: the second number
must be a real TPI and the first a screw number 4-14. Nobody writes a fraction
as 10/32 when 5/16 exists, and 1/32 and 3/32 stay fractions.

## "No match" is an advisory, not a dead end

The old wording — *"No row in this cabinet fits what was read"* — was ambiguous
about whether it meant the drawer or the database, and it left nowhere to go.
Scott, standing at a drawer of fifty fillister screws: *"I don't see any place
to put in the quantity, and I don't know that no row fits should be a blocker,
perhaps an advisory."*

Now every result — match or no match — carries a **pick it by hand** card
listing every row still unlocated in the cabinet, with the same count box and
file button. The message says explicitly that it describes the catalogue's
unlocated list and says nothing about what is in the drawer.

## Filing must retire the notes it makes false

B2-R1C1 was taken all the way through on 2026-08-22 — read, matched to
`91737A210`, counted at 47, filed. The write was correct: quantity 47, stocktake
dated, `[ESTIMATE]` flag off. The **notes** were not:

```
 0 | binscan 2026-08-22: filed into B2-R1C1 and COUNTED at 47 by hand.
 2 | [ESTIMATE] Quantity is what was PURCHASED ... not a count
 4 | **DRAWER UNKNOWN — this row is filed at CABINET level, which is not a place.**
 8 | Resolve it by ... Until then treat this as UNFILED
```

Line 0 and line 8 contradict each other, and both look authored. The import had
written a careful description of a transitional state; filing *resolved* that
state and left the description behind.

**An action that resolves a condition has to retire the note describing it.**
Filing now drops the DRAWER UNKNOWN / TRANSITIONAL / "resolve it by" paragraphs,
and — when a count is recorded — rewrites the purchase paragraph from an
`[ESTIMATE]` claim about the current quantity into `PURCHASE HISTORY
(superseded by the count above)`. The purchase line is kept deliberately: it is
what makes **50 bought, 47 counted** visible at all, and that gap is the input
to `unaccounted.py`. The count line now states the delta rather than leaving
someone to diff two paragraphs.

## The footer was lying

It read *"Read-only to InvenTree"* — true when written, false the moment
`/api/assign` shipped, and it sat directly under a button that had just moved a
row. Now: *"Reading is free; writing needs you."* A safety claim that has gone
stale is worse than none, because it is trusted.

## The drawer's own label is a record too

Scott at B2-R2C1, mid-walk 2026-08-22: no bag tag inside, but *"the label on the
front of the box is quarter twenty eight. So I took a picture of the nuts. It
properly identified them as nuts. Obviously, didn't figure out the size."*

No photograph of a nut shows its thread pitch. But the drawer's description
already read `1/4-28 nut` — those legacy labels were read off a wall photo the
day before. **The record knew and nobody asked it.**

Selecting an unassigned drawer now matches its own description against the
cabinet's unlocated rows and offers the result immediately, before any camera.
Fifteen B1/B2 drawers carry such a label.

Three matcher bugs fell out of testing that, each one making a wrong answer look
like a right one:

- **`M6-20` matched nothing.** The imperial parser read the `6-20` inside a
  metric designation as a 6-20 thread — 20 is a real TPI — and the cross-system
  penalty then rejected every metric row. A metric designation now wins
  outright; nothing here is both.
- **`1/4-20 nyloc` proposed a socket head screw.** Fastener-TYPE scoring had been
  dropped in an earlier rewrite, so the thread matched a dozen rows and nothing
  distinguished a locknut from a cap screw.
- **`5/16-18 lock nut` proposed a `1/2"-13` cap nut.** 13 was missing from the
  TPI set, so the part's thread did not parse at all — and **a row with no
  thread cannot disagree with the label**. A parse failure read as agreement,
  which is the dangerous direction for a matcher to fail in.

Widening the TPI set then made `18-8` — the stainless grade, printed on half
these labels — parse as an 18-8 thread. The diameter must now be a fraction or
a screw number of 14 or less, which 18 is not.

## Saying a drawer is empty

Most of a walk is empty drawers, and until 2026-08-22 the UI could not say so.
Scott, having advanced to B2-R1C2: *"there's nothing in one point two. How do I
tell the system that that is empty from this UI?"* The only options were file
something or skip, and **skipping records nothing** — so the drawer stays
unknown and gets opened again on the next pass. Saying "empty" is a finding, not
the absence of one.

`/api/empty` stamps the drawer `VERIFIED EMPTY <date> — previously labelled:
<the old description>`, the same string `scripts/mark_empty.py` writes, so a
drawer marked from the phone is indistinguishable from one marked in bulk.

Its guards mirror that script's exactly, because the same four mistakes are
available here and one has already been made once:

| refuses when | why |
|---|---|
| stock present **in the drawer or any descendant** | a drawer holding an assortment kit keeps its stock one level down; that is what made B3 read 41 drawers emptier than it was |
| a Part calls it `default_location` | a parking spot has no stock **by design** — stamping it empty is wrong twice, it is a queue someone means to return to |
| the description names something | "no rows" is not evidence of emptiness, and the description is often the only place the contents were ever written |
| — but the bracketed size annotation is stripped first | it is metadata, not contents; treating it as contents refused all 64 A2 drawers the first time |

Verified on re-read, journalled for undo, and idempotent — marking an
already-empty drawer changes nothing and says so.

## Filed is not counted, and the UI has to say so

Scott mid-walk 2026-08-22, looking at B2-R2C1: *"it doesn't tell you anywhere
that that's an estimate... it just looks the same as one point one, which has in
fact been counted."*

He was right, and it undercut the whole design. Filing without a count is a
deliberate, flagged state in the database — `[ESTIMATE]` prefix, no stocktake
date — and the UI was rendering it as a bare number identical to a real count.
A distinction that only exists in storage is not a distinction anyone acts on.

Now three fill states, not two:

| grid | meaning |
|---|---|
| green | filed and **counted** — a person tallied it |
| blue | filed, **never counted** — the quantity is the purchased figure |
| amber | nobody has looked |
| grey | verified empty |

and the "On record" card marks each row `✓ counted 2026-08-22` or **NOT
COUNTED — this is the purchased figure**. A drawer counts as counted only if
every row in it does.

Blue is deliberately not a shade of green. Filed-uncounted is a different
*claim*, not a weaker version of the same one: it says we know WHERE the stock
is and not HOW MANY. Green would say both questions were settled.

## Colour is never the only channel

Scott, 2026-08-22: *"I am mildly colourblind. So subtle colours are difficult
for me to deal with. I can definitely deal with primary colours, but subtleties
make it difficult."*

Every grid state therefore carries a **glyph** as well as a colour, and the
glyph is what carries the meaning:

| | | |
|---|---|---|
| `✓` | green `#4ade80` | filed and counted |
| `~` | blue `#38bdf8` | filed, quantity never counted |
| `?` | yellow `#fde047` | nobody has looked |
| `·` | grey | verified empty |

Hues are pushed toward primaries and the old amber replaced with a bright
yellow. **A grid that needs hue discrimination to read is a grid that fails at
arm's length, in a garage, for this user.** Any future state gets a glyph before
it gets a colour.

## The write journal — undo and reconciliation from one record

Every `/api/assign` write records the row's full **before** state: location,
quantity, stocktake date and **notes**. Two things need it.

**Undo.** InvenTree's tracking records quantity and location changes but not the
notes field, and notes are where this catalogue keeps its provenance — the
`[ESTIMATE]` flag, the purchase date, why a figure is what it is. Stock 514's
original notes were lost on 2026-08-22 because a write happened with nothing
capturing them first; they had to be reconstructed from a sibling row. The
journal exists so that cannot recur. `scripts/binscan_undo.py --undo <pk>
--commit` restores a row exactly and verifies the restore.

**Reconciliation.** Scott: *"if you had purchased fifty and there's only
forty-seven left, any idea where the other three went? ... Trying to do it from
the phone at the time you're doing the bin check, I don't think that's
realistic."* Right — so nothing asks at the drawer. `--reconcile` reports every
counted filing whose count differs from what the record held, afterwards, in a
batch. Answers feed `unaccounted.py --answer PART=PROJECT`, which is where the
"CONSUMED BY:" provenance already lives.

A filing with a blank count is deliberately **not** reconciled: the purchased
figure was carried forward, so there is no second number to compare against.
Only a real count creates a gap worth chasing.

`scripts/binscan_reset.py` puts a drawer back to its pre-filing state so the
same known-good case can be tested repeatedly — filing is a real write, so
testing the walk on a real drawer otherwise consumes the drawer.

**The journal is `~/binscan/log.jsonl`, not in git and not backed up.** That is
acceptable for an undo log, which is only useful while the writes are recent.
It is not an archive.

## Why the original design did not solve the B1/B2 walk

The walk needs the drawer address to be an OUTPUT. binscan assumes it is an
INPUT — *"the drawer address already determines that"* — which is true for every
cabinet except the two where the assignment is missing. Asking it what a B1
drawer holds asks the one question it was built not to answer.

**The extension that would work** is reading the McMaster bag tag Scott kept
inside most drawers. That is text on a printed label, which is the case
photographs ARE reliable for, and the number matches exactly one of the 48
unlocated rows. It would need a second prompt and endpoint, stay read-only, and
propose matches for confirmation rather than writing them — same discipline as
`docs/b1-b2-worksheet.md`. Not built.

## Risks worth acting on

- **No version control and no backup.** One `rm` loses it, and it took a
  screenshot and a DNS lookup to find it at all.
- **`env` holds API keys** on a machine whose backups have silently broken
  before. Not in this repo, correctly — but not anywhere else either.
- Runs from the internal disk deliberately: anything under `/Volumes` needs a
  TCC grant to run from launchd, which is what silently broke the InvenTree
  backup for weeks.
