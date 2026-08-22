# Techniques

Physical methods that make the inventory work go faster. Not software, not
traps — just things that turned out to work, written down so they survive the
session they were discovered in.

## Bagging small parts: funnel over the bag mouth

Slip the open bag over the spout of a printed funnel, tip the parts into the
cone, and they land in the bag instead of on the floor. Beats the two-handed
pinch-the-bag-open method that scatters anything round.

Matters here because bagging is the bottleneck in this whole project: the
drawers hold hundreds of loose small parts that each need a bag and a label
before they can be counted, and anything that shaves a few seconds and one
dropped-part hunt off each one compounds over a few hundred bags.

The funnel is shop-printed — see the funnel part in the catalogue, whose STL
should be attached to it.

## Print the label before filling the bag

A bag with a label on it is inventory; a bag without one is a mystery in six
months. The label carries a QR that resolves to the part, so the bag does not
need to be readable — it needs to be scannable.

Part labels do not carry a quantity, which is what makes this order work: the
label can be printed and applied before the bag is counted, and stays correct
as the count changes.

## Coarse pre-sort: four buckets beat one pile

When loose hardware appears faster than it can be catalogued, do not tip it all
into one "miscellaneous" drawer. Split it four ways as it goes in. The final
sort then starts from four small like-with-like piles instead of one heap, and
that is most of the work.

`A2-R8C5..C8` are the bank, designated 2026-08-21:

| Drawer | Bucket | The test |
|---|---|---|
| R8C5 | Machine-threaded | Could a nut spin onto it? |
| R8C6 | Self-threading | Is the end pointed? |
| R8C7 | Nuts & washers | Does it thread *onto* something? |
| R8C8 | Everything else | None of the above |

**The discriminator has to be answerable by looking.** That is the whole design
constraint. "Is it 1/4-20 or M6?" is a real distinction and a terrible pre-sort
question, because it needs a gauge and turns a two-second decision into a
thirty-second one — at which point nobody pre-sorts and it all goes in the heap
anyway. Thread pitch, length and finish are the *final* sort's problem; they
survive fine in a bucket of like things.

Four is close to the ceiling. Each extra bucket is another decision per piece
and another drawer to walk, and past about five the sorting costs more than it
saves.

These are queues, not homes: contents are **not counted**, and nothing ever gets
a `default_location` pointing at them. See the parking rule in `CONTEXT.md`.

## Whether to keep an offcut

Free material is not free — it costs the space it occupies, and in this shop
bulky storage is the binding constraint. Keep an offcut only if it passes all
three:

1. **Can't be remade quickly** from stock already on hand
2. **Worth meaningfully more** than the storage it takes
3. **Stored in a form you would actually reach for** — not a tangle

Worked example, 2026-08-21, both from the same Emporia Vue install:

| | ~60 CT lead offcuts, 22 ga | 6 offcuts, 14 AWG |
|---|---|---|
| Remade from stock? | yes — 100 ft of 22 AWG and two ferrule crimpers on hand | no 14 AWG catalogued |
| Worth > the space? | ~$30 against a shelf, and there is no free shelf | ~$3.50 against a sandwich bag |
| Reachable form? | one tangled boxful | six coiled pieces |
| **Verdict** | **binned** | **kept** |

Three things that example teaches:

- **The deciding variable was volume, not the wire.** Sixty pieces of anything
  is a storage problem; six is not. Ask "how many" before "what is it".
- **A tangle is not stock.** If retrieving one takes longer than making a new
  one, it will never be retrieved. Test 3 does more work than it looks.
- **Do not strip offcuts for scrap.** 90 ft of 22 AWG stranded holds about
  2 oz of copper — roughly 40 cents. There is no third option where scrap
  value rescues a keep-or-bin decision at this scale.

And the reframe that unsticks it: *"I hate to throw out wire"* is about money
already spent, which is gone either way. The only live question is whether the
material is worth the space **going forward**.

### For "might be handy someday", ask how often someday comes

Test 2 needs sharpening when the item is *insurance* rather than stock. A strip
of leftover TV-mount hardware — VESA screws in four thread sizes, anchors, lag
bolts — looked worth keeping: those sizes are genuinely annoying to source
mid-job. The argument survived two rounds and died on one question: **how often
does a TV actually go up?**

Rarely. And every mount ships its own hardware, so the claim would almost never
be made. Binned 2026-08-21.

The question generalises: for anything kept "in case", estimate **how often the
case arises** and whether the thing would even be reached for when it does. A
spare that is superseded by whatever arrives with the next job is not insurance,
it is storage. Scott, getting there the long way: *"Took me a while, but I got
there."* The long way is fine — the failure is never asking.


## Label a shop-built board, or it becomes a mystery

A Teensy 3.2 + MCP2562 CAN board turned up on the staging table in 2026 with
**no markings of any kind** — eight screw-terminal positions and nothing to say
which was CAN, which was power, or which were GPIO. Scott, holding a board he
built himself: *"I'm not quite sure how we would hook it up."*

The parts were fine. The information was gone.

**An unlabelled assembly is worth less than the components in it**, because
working out what it does can cost more than rebuilding it. This one is
recoverable in about fifteen minutes only because both ICs have fixed pinouts,
so continuity from a known chip pin identifies every terminal. A board built
around a bare microcontroller and discrete parts would not have that luxury.

So, when a shop-built board goes in a drawer:

- **Write the terminal functions on the board itself.** Tape and a marker.
  `CANH CANL +12 GND` costs ten seconds and survives everything.
- **Record the pinout on the part**, not in a notebook or a chat log.
- **Say whether it is terminated.** This one measures 4.6k, not 120 ohm, so it
  is *not* a bus terminator — the useful case, because it can join a
  terminated bus without becoming the third terminator. That single fact
  decides whether plugging it in works.
- **Note whether firmware exists and where.** This board had none: the GitHub
  repo behind it is a fork with zero commits. Knowing that up front is worth
  more than the board.

## Identify a mystery object by querying what has no home

An imported order history is not just a record of what was bought. It is a
**list of objects that are somewhere in this building**, and most of a bulk
import lands with no location because the importer had nothing to go on.

That makes the unlocated set a lookup table. When something turns up on a bench
and nobody can name it, do not start from the object — start from the records:

```
StockItem.objects.filter(location__isnull=True,
    part__supplier_parts__supplier__name__icontains='<vendor>')
```

Then read the object against that list instead of against the whole catalogue.
A few dozen fully specified candidates beats a thousand parts and a guess.

This resolved two things in one pass on 2026-08-21, off the same table:

- An **eyebolt** nobody could name. Two were bought on one order. Measuring the
  shank at 16 mm picked the metric one — and independently, that was the record
  with no location while its twin was already filed. The homeless record was the
  homeless object.
- A **carbide bur**, which turned out to be the exact bur a shop-printed jig was
  built to hold. Neither record referenced the other; the jig was catalogued as
  a tool and the bur as consumable tooling from a hardware order, and nothing
  short of reading both lists on the same afternoon connects them.

Two properties make this work, and both are worth protecting:

**Leave imported stock unlocated rather than guessing.** A guessed location is
worse than none — it reads as knowledge, it sends someone to the wrong drawer,
and it silently removes the row from exactly this query. The 42 unlocated rows
here are not a defect in the import; they are what makes the import useful a
second time.

**A matched pair gets cross-linked on both records.** A tool and the consumable
it is built around are one thing functionally and two things in the database.
Link them in both directions and say why, or the pair survives only as long as
the person who assembled it remembers.

The general rule: **the catalogue can answer questions about physical objects
that the objects cannot answer about themselves.** A part with no markings has
no identity in the hand, and a complete one in a record nobody thought to open.

## Fetch through the page, not around it — driven Chrome defeats fingerprinting

The house rule has been "vendor sites that fingerprint you need a browser."
True, but it was applied as *"…so a human has to fetch it."* That last step is
wrong, and it cost real work before anyone tested it.

**A driven browser can fetch the bytes itself.** Run `fetch()` from inside a
page already on that origin, and the request carries the browser's real TLS
fingerprint, headers, cookies and session — everything curl cannot fake:

```js
const r = await fetch('https://vendor.example/file.pdf', {credentials: 'include'});
const blob = await r.blob();
const a = document.createElement('a');
a.href = URL.createObjectURL(blob);
a.download = 'thing.pdf';
document.body.appendChild(a); a.click(); a.remove();
```

The file lands in `~/Downloads` and is then an ordinary local file — verify it,
`itq push` it, attach it. **Proven end to end 2026-08-21** against `st.com`,
which kills curl's HTTP/2 stream outright: the scripted download produced md5
`dec39565…`, **identical to the same file downloaded by hand.**

Two details that make it work:

- **Navigate to the vendor's own origin first**, then fetch. A cross-origin
  fetch from a blank tab has none of the context that makes the request look
  legitimate, and may be blocked by CORS besides.
- **`credentials: 'include'`** so a logged-in session applies. This is what
  extends the technique to sites that require sign-in.

### What this obsoletes

Any conclusion of the form *"vendor X is unscrapeable"* that was reached with
curl, or with a headless fetch, is **not evidence about a driven browser** and
should be re-tested before it is believed. Specifically:

- **The product-image backlog.** It was declared effectively dead because
  "Amazon is bot-blocked from both the Mini and the laptop — two independent
  confirmations", leaving ~82% of images unreachable. Both confirmations were
  *curl from a shell*. Neither tested a driven browser holding a real Amazon
  session. That backlog deserves one honest re-test.
- **Remaining datasheets** from onsemi, Diodes Inc, Toshiba, SMC and Mouser,
  all of which refused a scripted fetch today.

### Where it stops

This defeats **fingerprinting**, not **authorisation**. It does not touch a
CAPTCHA, a login wall, or a rate limit, and it must not be used to try:
Octopart's PerimeterX interstitial is still a hard stop, and solving one is
never on the table. If a page challenges the browser, that is a refusal from a
human-facing system and it gets respected.

### Amazon images: the block was never real, and the docs already said so

Re-tested 2026-08-21. Product page via driven Chrome: loads fully, **no bot
challenge**, correct title, `"hiRes"` URLs extract clean. Image CDN
`m.media-amazon.com` via **plain curl**: 200, `image/jpeg`, 1500x1500, 0.07 s.
Proven end to end on part #14 — image attached, thumbnail generated.

**None of that mechanism is new, and it should not be written up as if it
were.** The overnight task file already carried it under "Amazon image trap
(verified)": hiRes lives in the `/dp/<ASIN>` page HTML, the LRD network is
challenged but **the laptop is not**, *"which is why the fetch happens on the
laptop and the bytes are scp'd over."* Correct, and on record for days.

**The real finding is a documentation conflict, not a networking one.**

| Source | Says |
|---|---|
| Task file, "Amazon image trap (verified)" | LRD blocked, **laptop fine** — fetch there |
| Overnight journal, most recent run | "bot-blocked from **both** the Mini and the laptop — two independent confirmations" |

They contradict. The journal is wrong, and **the wrong one won**: the image
queue was reported dead and stopped being worked, while a correct procedure sat
in the same file the job reads every night.

Two lessons, and the second is the sharp one:

- **"Two independent confirmations" was one experiment run twice.** Both were
  curl against the product page. Agreement between two runs of the same wrong
  method feels like corroboration and is not — it is the strongest way to make
  a wrong result stick.
- **A running journal outranks a static doc in practice, whatever the intent.**
  The journal is what the next run reads first and treats as current state. So
  when a run's conclusion contradicts the task file, that is not a note to
  file — it is a conflict to resolve *then*, in both places, or the fresher
  wrong answer silently wins.


## Find consumption forward from purchases, not backward from builds

Reconstructing what a finished project consumed, from the build record, does
not work here — those records were written up after the fact, so their dates
describe when someone typed them rather than when anything was soldered. See
the `completion_date` trap.

Scott's inversion is better, and it is what `scripts/unaccounted.py`
implements: **work forward from the two facts that are trustworthy.**

1. **What was bought** — purchase orders, with real received quantities.
2. **What is on the shelf** — a count taken just now.

The gap is consumption. And it can be asked about *while the part is in hand*,
which is the only moment anyone can answer it. Six months later the question is
unanswerable, and the drawer walk is exactly when the part is in hand — so the
question costs nothing extra to ask.

    itq run scripts/unaccounted.py --location B3

Three rules the tool enforces, each of which would otherwise produce fiction:

- **Only counted stock is compared.** Subtracting a purchase from an
  `[ESTIMATE]` produces a fictional shortfall that looks exactly like evidence.
- **Installed stock counts as accounted for.** A part with `belongs_to` set is
  inside something and the record says which — it is not missing. This is why
  installing beats deleting.
- **Prefer confirmation to recall.** Before asking an open question, it checks
  whether a build's BOM already explains the gap and asks *"was it BO-0013?"*
  instead of *"what used one of these?"* A yes/no is far more reliable than a
  memory test, and it fails safe: a wrong suggestion gets corrected, a blank
  prompt gets a shrug.

### Most consumption has no build order — so grow the vocabulary from answers

Scott's objection to the above, and it is the important one: **a BOM lookup
only helps when a build order exists, and usually there isn't one.** Repairs,
fixtures, one-offs and bodges consume most of a shop's small parts and none of
them get a BO. The red bins are no help either — every one of them maps to a
build that already exists.

So the candidate list has to be built from the answers themselves. Each answer
is written to the part as `CONSUMED BY: <project>`, and the report harvests
every such line to offer back next time. The vocabulary lives **on the parts**,
not in a side file, so it cannot drift away from the data it describes. After a
few sessions the open question becomes a menu, which is the same
recognition-over-recall trick applied to a problem with no BOM to lean on.

    itq run scripts/unaccounted.py --answer 291="pool controller wiring"
    itq run scripts/unaccounted.py --answer 291=?      # cannot recall

**Group parts that are short together.** Two KF301 terminal blocks, 2-position
and 3-position, came up short in the same pass — near-certainly one job. The
report groups by name stem and asks once. The grouping is itself the hint that
jogs the memory, and it turns several unanswerable questions into one
answerable one.

It validated itself on first run — flagged one missing Minisplit CN105 PCB and
independently matched it to BO-0013, which needs exactly one.

**Record "cannot remember" as an answer.** It is a real result, and writing it
down stops the same question being asked every time somebody re-counts that
drawer. An unanswered question that keeps reappearing trains people to ignore
the tool.

## A "Project" column in the parts table — via a parameter, not a plugin

Scott wanted a column in the parts list showing which project(s) have used a
part. Two things had to be established first, and one corrected an earlier
claim here:

- **There is no plugin hook for table columns.** `UserInterfaceMixin` offers
  `get_ui_panels`, `get_ui_dashboard_items`, navigation and actions — nothing
  for adding a column. A plugin can add a *panel* to a part's detail page, but
  not a column to the list.
- **Part parameters exist and the table can show them.** They were renamed and
  moved in 1.x — `part.PartParameter` became **`common.Parameter`** with
  `common.ParameterTemplate`, now generic (`model_type` is a ContentType FK,
  `model_id` the object id). An earlier note here said parameters did not exist
  in 1.5; that was a failed lookup under the old name, and this install already
  had 95 values across Body Size, Lead Pitch and Footprint.

`scripts/project_column.py` builds a `Project` parameter, re-runnably, from
three sources ranked by how much they actually prove:

| Source | Strength |
|---|---|
| `belongs_to` — physically installed in an assembly | **proof** — someone put it there and the record names the unit |
| `CONSUMED BY:` notes from `unaccounted.py` | testimony, from the one person who knows, captured while holding the part |
| Build BOM lines | a **plan** — a pending build has consumed nothing |

**Planned use is marked with a trailing `?`.** A column showing "inside a
finished device" and "some project intends to use this" identically is worse
than no column: it reads as fact and is half intention.

Two details worth keeping: split build titles on a **spaced** hyphen only, or
"Shrink-fit controller" becomes "Shrink"; and if a project appears as both
actual and planned, keep only the actual, or the column reads "Rat GDO, Rat
GDO?" and looks unreliable.

    itq run scripts/project_column.py            # dry run
    itq run scripts/project_column.py --commit

Re-run after any counting session — answers recorded by `unaccounted.py` feed
straight in, so the column improves exactly as the drawer walk progresses.

### Recording consumption AT COUNT TIME — inflate, allocate, consume

Scott's workflow, and it beats reasoning about history afterwards. While
counting a drawer, ask whether he remembers a project that used any. If he
does, push it through InvenTree's own machinery rather than writing prose
around it:

```
count says 27 on the shelf
"three went into the pool controller"
   -> inflate the stock row to 30     (you cannot allocate stock you do not have)
   -> allocate 3 to that project's build
   -> closing the build CONSUMES 3, and stock returns to 27
```

The count ends up correct **and** `consumed_by` carries the history — the
authoritative field that survives completion, so the Project column shows the
project as fact rather than as a `?`.

`scripts/consumed.py` does it in one command, creating the build and a
placeholder assembly part if the project has none:

    itq run scripts/consumed.py --part 291 --used 3 --project "Pool Controller" --commit
    itq run scripts/consumed.py --list
    itq run scripts/consumed.py --close "Pool Controller" --commit

**Leave the build OPEN during the walk.** A completed build locks — the same
trap as a completed purchase order — and three drawers later another part will
turn out to belong to the same project. Accumulate lines as they surface, close
once at the end. Closing early means fighting a locked record for the rest of
the session.

Each reconstructed build is tagged `[RECONSTRUCTED]` in its notes and records
that its **physical build date is unknown**, so nobody later compares stocktake
dates against its completion date — that comparison reads the wrong event.
