# The dashboard

Design decisions for the InvenTree dashboard, settled 2026-08-23/24. The
`shop_status` plugin renders it; this file says **why it looks the way it does**,
so the next session does not re-derive the argument or undo a deliberate choice.

Working mock (all layouts, real numbers):
<https://claude.ai/code/artifact/c35bb33b-0d4d-4308-af59-cbd7ce640b37>

Companion brief from the overnight-import project, *Inventory Health Signals*:
<https://claude.ai/code/artifact/1dba2bc5-5810-4b11-89b4-9ee255fe413e>

## What the dashboard is for

Scott, 2026-08-23: **"data atrophy will be the death of it."**

That is the whole brief. This is not an inventory-statistics page — "you have
1,071 parts" is trivia that only ever goes up, and rewards creating records
rather than verifying them. It is an instrument for noticing that the data is
drifting away from the shelf.

## The governing principle

Scott flew the **Boeing 727**, and corrected an earlier draft built on Airbus
dark-cockpit philosophy:

> "I flew the B727 — all info all the time!"

That correction produced the principle the whole layout now rests on:

> **Make normal look uniform, so abnormal breaks the pattern.**

On a 727 the crew reads the engines without reading any number — normal is
needles at the same angle, and the eye finds the odd one out. Values are there
for when you want them, not to be scanned.

**Why dark cockpit was rejected, and it matters here specifically:** an
exception-only panel shows nothing when nothing has tripped a threshold. Drift
never trips a threshold. A catalogue slowly becoming less true would keep the
panel dark right up until something broke — which is *exactly* the failure this
page exists to catch. Dark cockpit is structurally blind to the one thing we
care about.

## Settled decisions

**Three gauges, round, always visible.** Coverage per subsystem, drawn so a
healthy set forms a uniform pattern. 270° sweep, graduated scale, range arcs
(red 0–40, yellow 40–80, green 80–100), drum counter in the bottom dead zone.

**A draggable bug marks the target.** A gauge alone says *how much*; a gauge
with a bug says *how far short*, which is the actual question. The bug is also
the settings UI — drag it and the value writes to a plugin setting. Rejected:
a number in a settings form. You set the goal on the instrument you read it
from, so you can see the gap while you are choosing the target. Keyboard
accessible (`role="slider"`, arrow keys) because drag-only is unusable.

**Lamps are Korry pushbuttons and flash until pressed.** Red = warning,
yellow = caution, per Boeing convention.

**Silencing is not clearing.** Pressing stops the flash; the lamp stays lit
while the condition is true. This settles the fight between *don't let me miss
this* and *stop nagging me about what I already know*. Three paper receipts
waiting on a look should stop flashing and should absolutely not disappear.
Acknowledgement is per-lamp, never global — a master-silence button was built
and removed, because it silenced lamps that had not been read yet.

**Acknowledgement is state worth storing.** Which lamps were silenced and when.
A lamp acknowledged for six weeks is itself a signal — that is an atrophy
detector hiding inside the mechanism.

**Four states, never two.** Good / needs action / blocked / **not measured**.
The fourth gets an **OFF flag**, never a zero, never green, never blank. This
came from the import brief and aviation had already solved it: an instrument
that has lost its signal drops a flag rather than parking the needle at zero.
McMaster carries the flag today because its login test cannot tell signed-in
from signed-out — three such tests have now been wrong.

**Coverage always uses the reachable denominator**, with the ruled-out count
shown beside it. See `TRAPS.md`. A hidden exclusion is a rule nobody can check.

**Sources show the last read that proved something**, not the last time a job
ran. Those diverge exactly when something is wrong.

**Colour is never the only encoding.** Every state carries a glyph (`■ ▲ ·`)
and a word. Red lamps take white text, yellow lamps near-black — a luminance
difference that survives any hue confusion. Caution is deliberately *yellow*
(`#F2C800`), not amber, to open the gap from red in the compromised channel.

**Everything is a link and looks like one.** The current live dashboard's middle
rows *are* anchors with `color:inherit; text-decoration:none` hiding it, and the
top strip renders as `<div>` with no links at all. Both are bugs.

**Gee Whiz stays.** Total part count is on the import brief's do-not list, and
that objection is right for an *instrument*. This is not one: it is below the
fold, labelled trivia, and exists because Scott asked for it by name.

## The gap neither document closes

Both this panel and the import brief measure **coverage** — a static snapshot of
how complete things are. **Neither measures decay.**

Redefining a denominator moved image coverage from 52% to 96% without saying
anything about whether counted rows are going stale. Stale-over-time is
precisely what "data atrophy" names. The panel has no needle for the thing it
was built to catch.

That needle is the cycle-count system's output (`cycle-counting-research.md`),
and the two are not yet connected. The right readout is a **freshness
statistic** — "oldest count: 6 months" — not a completion bar.

## Answered — reply brief, 2026-08-24

The overnight-import project closed its brief with three questions "for the
dashboard team". Answers below; full argument in the reply brief at
<https://claude.ai/code/artifact/286a37fc-6090-4c8f-9c2d-2880ed80ceb2>.

**Push or pull? Both — split on failure mode, not on urgency.** Drift cannot be
pushed: there is no moment at which a catalogue becomes stale, so there is
nothing to fire on. That is the entire argument for an always-on instrument.
Silent failures are the opposite shape — their failure mode *is* that nobody
looks — so the push set is anything that can render **OFF**, plus vendor-session
staleness. Everything else stays pull.

And: **push on transitions, not on state.** A session dead three days notifies
once. This is the same rule the lamps follow — otherwise the notification
channel trains exactly the blindness the background Chrome already has, and the
problem has moved rather than been solved.

**Live from the API — except the one thing that cannot be.** A snapshot going
stale invisibly is the bug the brief is about; a dashboard built on one inherits
it. But the reachable/ruled-out split is accumulated sweep evidence, not a
query, so it is a snapshot by nature. Timestamp it and **let it go OFF when it
ages out** rather than quietly continuing to report 483 ruled out. A stale
exclusion set is worse than none, because it is what makes 96% look true.

**Loud when the failure disables another check. Advisory otherwise.** `PO-0020`
supplies a better test than severity: a null issue date did not produce a wrong
aging number, it removed the row from aging entirely. The alarm did not misfire
— it stopped existing. So: *does this failure make another check lie?* Nulls in
fields an alarm depends on, tombstones reaching a worklist, probes that cannot
distinguish their two outcomes — loud. Ordinary threshold breaches — advisory.
Deliberately a small set; loud has to stay rare or it stops being loud.

## Asked of them, outstanding

**The reachable/ruled-out split, as data** — with a timestamp and a reason
breakdown (delisted / login-gated / synthetic SKU). The panel cannot compute it;
it is their sweep's accumulated evidence. Without the breakdown the exclusion is
a hidden rule, which their own tombstone tile argues against better than we can.

## Built — side-by-side pilot, 2026-08-25

Shipped as a **fifth dashboard widget**, `Instrument Panel`, with the four
existing widgets left exactly where they were. Side-by-side rather than a
replacement, because the gauges' *numbers* are new even where the queries are
old, and a panel that reads wrong should be comparable against the widgets that
have been right for weeks — not the only thing left on the page.

`plugins/shop_status/` `v1.3.0`. `renderPanel` in the plugin JS; `_panel()`,
`_gauges()`, `_lamps()`, `_sources()` server-side. Everything is computed live
per render, so there is no snapshot to go stale — the one thing that is a
snapshot by nature is called out below.

**What the three needles read, measured 2026-08-25:**

| gauge | reading | denominator |
|---|---|---|
| IMAGES | **OFF** | reachable denominator not supplied — see below |
| COUNTED | 57% | 368 of 649 stock rows carry a stocktake date |
| BIN WALL | 88% | 284 of 324 drawers hold stock or were verified empty by eye |

**IMAGES carries the OFF flag, and that is the honest output.** Coverage is
defined against the *reachable* denominator, and the reachable/ruled-out split is
the sweep's accumulated evidence — not a query this panel can run. The two
alternatives were both rejected: rendering the raw 532/1010 = 53% is the
misleading number the whole redesign threw out, and hard-coding the remembered
"483 ruled out → 96%" is worse, because nothing on this instrument could then
tell whether that exclusion set still holds. So the gauge drops its flag and the
sub-line says what is missing. The first thing the panel does is demonstrate its
own fourth state.

**The freshness statistic exists now, in a small way.** Under COUNTED:
*oldest count 8d old*, straight off `stocktake_date`. It is not the decay needle
this document says is missing, but it is the first number on the panel that can
get worse while nothing else changes.

**Lamps, and the severity split that had to be corrected on the first run.**
Red where the failure makes another check lie, yellow where it is work waiting.
The tombstone lamp got this wrong initially and lit red over a to-do queue; see
`TRAPS.md`, "Tombstone markers do not share a severity". Live at first light:
one red (a merged part still active — a genuine double-count), five yellow.

**Both interactions write to plugin settings, and both were verified against the
live instance.** Dragging or arrow-keying a bug PATCHes `TARGET_IMAGES` /
`TARGET_COUNTED` / `TARGET_BINWALL`; pressing a lamp writes `ACK_STATE`. The ack
records the *count* as well as the time, which is what makes a silenced lamp
flash again when the condition changes rather than every morning. A failed write
says so on the instrument — a bug that moves but does not stick is worse than one
that will not move.

**Sources come from the sweep's own session file** (`PREFLIGHT_PATH`, default
`/Volumes/4TB_Removable/inventree/preflight_state.json`) — the vendor state the
overnight job already writes on transition. `last_ok` is the reading, not
`checked`. A vendor goes **OFF** when its state is `UNKNOWN` or its last check is
older than 24 h; `OUT` is *not* OFF, because a probe that says "signed out" is a
working probe with bad news. All four read live today; McMaster now proves its
session rather than guessing at it, so it no longer carries the flag it carries
in the mock.

**Not built in the pilot:** the worklist screen (layout B) and Gee Whiz. The
panel is layout A only.

## Still open

- **What earns a lamp, and which lamps earn a flash?** A lamp that re-flashes
  every morning because the overnight job is flaky teaches you to press it
  without reading. That is how five settled drawers came to read as "nobody has
  looked" until amber stopped meaning anything.
- **Do target changes get dated?** "When did we decide 80 was good enough" is
  the kind of question this project has wanted before. The bug writes a bare
  integer to a plugin setting today, so the answer is still no.
- **Nothing pushes yet.** The push/pull answer above is argued and unbuilt: the
  panel is pull-only, so a source going OFF at 03:00 waits for somebody to open
  the page. The transition data is already there — `preflight_state.json` records
  `changed` — so this is wiring, not design.
- **The pilot has no end condition.** Side-by-side is only worth something if
  the comparison is actually made; the four old widgets should either be retired
  or explicitly kept once the gauges have been read for a week.

## A note on the corrections rate

Their P2 "corrections rate" tile is the one worth building first, and this
week supplied its definition as well as its first data points. Four wrong
numbers about the `[ESTIMATE]` field in 48 hours — their 0, our 42, the panel's
lamp reading 1, the audit's 3 — plus **a wrong direction**, which was the one
that would have destroyed data and which is not a number at all.

So the tile cannot just count numeric retractions. And the root of all five was
the same: **a check that did not name what it queried.** See `TRAPS.md`.
