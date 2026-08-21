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
