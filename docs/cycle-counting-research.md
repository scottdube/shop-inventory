# Cycle counting — what the field actually does

Research pass, 2026-08-23, before any of this is designed. Scott: *"we have
time to research/scope/design and build a robust system."* The point of reading
first is to avoid inventing a worse version of a solved problem — and to find
the places where the shop is genuinely unlike a warehouse, so those get designed
rather than inherited.

Scope decisions and their reasoning live in `OPEN.md`. This file holds what the
literature says, what survives contact with a one-person shop, and **what the
research changed about decisions already made.**

## The methods, and which ones matter here

| Method | What it is | Verdict here |
|---|---|---|
| **ABC by value** | Rank by annual consumption value; A counted ~10×/yr, B ~5×, C 1× | **Reframe, don't adopt** — see below |
| **Geographic / area-sequential** | Walk physical areas in order, counting everything in each | **Adopt** — already the chosen design |
| **Control group** | Count a fixed small set repeatedly to test the *process* | **Adopt for the pilot** |
| **Opportunity-based** | Count at natural touchpoints — receiving, picking, being there | **Adopt, and it may matter more than the schedule** |
| **Zero-balance check** | When a bin looks empty, confirm it as a zero count | **Adopt — free accuracy** |
| **Random sampling** | System picks at random | Already requested; keep as one mode |

### ABC by value is the wrong axis for a shop

The standard ranking is annual consumption *value*, and it is wrong here in a
specific way. Inventoryops' practitioner guidance already pushes past it —
frequency should reflect **operational impact**, not dollar value: raw materials
that stop production deserve more attention than expensive slow movers.

In this shop the operational-impact question is *"what halts a build at 9pm on a
Sunday?"* — a 12-cent M3 screw ranks above a $180 toolholder, because the
toolholder is one item you can see at a glance and the screws are the thing you
run out of mid-assembly. **Value ranking would invert the true priority.**

Worth noting: *"stale ABC tiers are the most common silent killer of cycle
counting programmes."* Whatever axis replaces value has to be **recomputed, not
stored** — which matches the derived-enrollment rule already recorded.

### Control group is the pilot method, and it was not on the list

Count the same small set repeatedly and watch the variances. It tests **the
counting process itself** rather than the inventory — it finds miscounts,
ambiguous labels, unit-of-measure confusion, and bad procedure.

This is a strong fit for LRD in February: 12 locations, a system nobody has used
yet, and every unknown is *"does this design work"* rather than *"how much is
there"*. **The pilot's job is to validate the process, and the control group is
the instrument for exactly that.** It was not in the original eight questions.

### Opportunity-based counting may be bigger than the weekly cycle

Count at natural touchpoints, because errors cluster around movement. The
zero-balance variant: when a bin empties, that is a free, unambiguous count —
zero is the one quantity that is never miscounted.

This is a real tension with the decided design, and it should be argued out
rather than merged silently. **The scheduled 20-minute cycle counts places
chosen by an algorithm; opportunity counting counts the place you are already
standing in.** For a shop where the owner is in these drawers constantly, and
already holding the phone that runs BinScan, the marginal cost of *"you're here,
is this right?"* is close to zero, and it self-targets the parts that actually
move — which is precisely what the maintenance-mode ranking is trying to
approximate from data.

It does not replace the schedule: the drawers you never open are exactly the
ones a schedule exists to reach. But a design with only the schedule leaves the
cheapest accuracy on the table.

## What the research CHANGED

**1. Blind counting is a live question, and BinScan already answers it — by
accident.** Mainstream guidance says counters must not see the expected quantity
(anchoring bias: people count to the number they were shown). Inventoryops
dissents, arguing that showing the quantity reduces errors and recounts, with
the caveat that it requires monitoring because *"some counters cheat on items
that are difficult to count."*

Both positions assume an employee. Here the counter is the owner, so fraud is
not the risk — **anchoring is**, and it is worse for the exact case this shop is
full of: a bin of 200 small parts where "looks about right" is indistinguishable
from a count. BinScan's "On record" card currently **shows the quantity**, so
the system has already taken the informed-count position without anyone
choosing it.

**2. The accuracy metric should be a hit rate, not a piece count.** Inventory
record accuracy is judged record by record — a row at a location either matches
or it does not — and is reported as the percentage that matched. Benchmarks:
95–98% acceptable, 99%+ best in class. Notably, CAPS Research found the 2024
average was **~83%, with only ~69% of organisations tracking it at all.**

Inventoryops adds a sharper variant: dividing variance by **consumed** quantity
rather than on-hand is *"far more useful in determining process problems"*,
because a 3-unit error against 500 consumed is noise while the same error
against 6 consumed is a broken process. This shop has consumption data —
`unaccounted.py` and the `CONSUMED BY:` provenance — so the better metric is
available.

**3. Tolerance bands are the answer to "never invent a count", not a violation
of it.** Standard practice sets a variance tolerance: zero for critical items, a
percentage band for the rest. This sounds like it contradicts the invariant, and
it does not. **A tolerance declares the PRECISION of a count; inventing a number
declares a quantity nobody observed.** "247±5, counted by weight" is an
observation. "250, because that is what the bag said" is not. The distinction is
already live in the `[ESTIMATE]` flag; tolerance extends it from a binary to a
stated precision.

That matters practically: counting 250 spring pins one at a time is absurd, and
the alternative is not a guess but a **declared method** — count by weight, by
strip, by full-bag-plus-remainder.

**4. The most common failure mode is already half-solved here.** *"The most
common way a cycle counting program loses its value is through
rubber-stamping"* — a variance appears, someone approves the adjustment, nothing
is investigated, and the same variance returns next cycle. Adjacent failures:
skipping root-cause analysis, and no ownership.

The existing `binscan_undo.py --reconcile` → `unaccounted.py --answer
PART=PROJECT` flow **is** root-cause analysis: it asks where the missing three
went and records the answer as provenance. That is the discipline most
programmes lack. The design should make it a required step on a real variance,
not an optional afterwards.

**5. The literature has NOTHING on the seasonal problem, and that was a wrong
prediction.** `OPEN.md` recorded a guess that established practice would have an
answer for the six-months-empty freshness clock. It does not — warehouses do not
close for half a year, so the case never arises. The closest analogue is
opportunity-based counting's premise that **errors cluster around movement**,
which supports the presence-clock intuition (no movement, no drift) without
validating it.

So the days-present clock and its invalidation events have to be designed from
first principles here. That is worth knowing before the next session spends time
looking for prior art.

## Ruled out — warehouse ceremony that does not apply

Recorded with the reason, so it is not re-proposed:

- **Freezing stock movement during a count.** Assumes concurrent pickers. One
  person cannot pick and count simultaneously.
- **Segregation of duties / independent counters / blind counts for fraud
  control.** Assumes an employee who might cheat. The owner is the counter.
- **Dollar-threshold management review and finance sign-off.** No finance
  function; no one to escalate to.
- **RFID.** Quoted at 99%+ accuracy versus 70–85% manual, and entirely
  disproportionate — the tag cost alone exceeds the value of a drawer of screws.
- **Dedicated trained counting staff.** Repeatedly named a success factor, and
  unavailable at any price here.
- **Daily counting cadence.** Assumes a facility with staff on site every day.
  This one is empty half the year.

## Open questions for the next session

See `OPEN.md` for the eight already decided. These are new or reopened by the
research, in rough order of how much they change the design:

1. **Blind or informed counts?** BinScan shows the quantity today. Anchoring is
   real, and worst on heaps — which is most of this shop. Options: keep
   informed; go blind on the primary pass and reveal after; or
   **directed-blind** (show the bin and the part, hide the quantity), which the
   literature offers as the middle path.
2. **Does opportunity-based counting go in the design at all?** If yes, is it a
   second mode inside BinScan, a prompt shown whenever a drawer is opened for
   any reason, or a background rule that credits any count as a cycle count?
3. **What replaces ABC?** The operational-impact axis needs a definition that
   can be computed. Candidates: consumption frequency from PO history, "would
   stop a build" flagged by hand, physical count cost, or a blend.
4. **Tolerance policy — and does a tolerance count as a count?** Does a
   by-weight estimate set `stocktake_date`, or is it a third state between
   `[ESTIMATE]` and counted? This touches the strongest invariant in the
   project, so it should be decided deliberately.
5. **Which accuracy metric gets built?** Hit rate is simple and standard;
   variance-over-consumed is more diagnostic and the data exists. Possibly both,
   since the dashboard was already chosen over a single number.
6. **Is the control group part of the LRD pilot?** A fixed set counted every
   cycle for the first months, to test whether the process works before trusting
   what it says.
7. **The seasonal clock, still unanswered and now known to be unprecedented.**
   Days-present ageing plus invalidation events (arrival, cross-site transfer,
   delivery) is the standing hypothesis and has no external support.
8. **Is a variance investigation MANDATORY?** Rubber-stamping is the named
   killer, and the machinery already exists. Forcing it is a real cost on a
   Saturday morning; not forcing it is how programmes rot.

## Sources

- [Inventoryops — Cycle Counting and Physical Inventories](https://www.inventoryops.com/articles/cycle-counting-and-physical-inventories.html) — the practitioner source; area-sequential counting, the anti-blind-count position, variance-over-consumed
- [Interlake Mecalux — Inventory record accuracy vs location accuracy](https://www.interlakemecalux.com/blog/inventory-record-accuracy)
- [NetSuite — Inventory Cycle Counting 101](https://www.netsuite.com/portal/resource/articles/inventory-management/using-inventory-control-software-for-cycle-counting.shtml)
- [NetSuite — ABC Analysis in Inventory Management](https://www.netsuite.com/portal/resource/articles/inventory-management/abc-inventory-analysis.shtml)
- [Racklify — Cycle Counting Best Practices and Common Mistakes](https://racklify.com/encyclopedia/cycle-counting-best-practices-and-common-mistakes/)
- [Monarch — Top Pitfalls of Cycle Counting](https://monarch-inv.com/top-pitfalls-of-cycle-counting-and-how-to-fix-them-kansas-city/)
- [Butler Bros — Cycle Counting Done Right in Manufacturing](https://www.butlerbros.com/post/cycle-counting-done-right-in-manufacturing) — the CAPS 83% / 69% figures
- [Shopify — Cycle Counting: Types, Best Practices & Benefits](https://www.shopify.com/blog/cycle-count) — control group, opportunity-based
- [Controlata — Cycle Counting Guide for Manufacturers](https://controlata.com/blog/cycle-counting-guide-for-manufacturers/) — zero-balance check
- [CPCON — How to Run Warehouse Cycle Counts](https://cpcongroup.com/insights/article/how-to-run-warehouse-cycle-counts/) — directed-blind, tolerance thresholds
- [Champion — Blind Counts or Show Quantity On Hand?](https://www.champion-business-solutions.com/post/inventory-counting-blind-counts-or-show-quantity)
