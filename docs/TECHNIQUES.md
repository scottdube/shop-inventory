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
