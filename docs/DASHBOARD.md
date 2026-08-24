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

## Open, and deliberately unanswered

- **Push or pull?** A panel is a pull instrument. The scheduler has now missed
  two nights running and a human noticed both times, not the system. A dashboard
  nobody opens has the same failure mode as the background Chrome nobody looks
  at. At minimum the source tiles need a path off the page.
- **What earns a lamp, and which lamps earn a flash?** A lamp that re-flashes
  every morning because the overnight job is flaky teaches you to press it
  without reading. That is how five settled drawers came to read as "nobody has
  looked" until amber stopped meaning anything.
- **Where does the health data come from** — the API live, or a nightly
  snapshot? A snapshot can go stale invisibly, which is the bug the brief is
  about.
- **Do target changes get dated?** "When did we decide 80 was good enough" is
  the kind of question this project has wanted before.
