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
