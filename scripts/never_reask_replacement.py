"""Stop a future sweep from re-creating the PO we just decided not to create.

Closing the decision is not enough. Section 3 keys idempotency on
`po_check <order-no>`, and for 113-8789992-1384241 that will keep saying
`absent` forever — because absent is the intended end state. The next run
inside the window would read that as "not yet imported" and create the PO,
undoing the decision silently.

The `declined — never re-ask` list is the existing mechanism for exactly this.
"""
import sys

QUEUE = "/Volumes/4TB_Removable/inventree/pending_decisions.md"
HEADER = "## declined — never re-ask"
LINE = ("- DECLINED | Brother QL-810W, $0.00 warranty replacement | 113-8789992-1384241 | "
        "swap against PO-0134, not a purchase. po_check will say `absent` for this order "
        "number permanently — that is the DECIDED state, not a gap. Do not create a PO.")

src = open(QUEUE).read()
if "113-8789992-1384241 | swap against PO-0134" in src:
    print("already listed — nothing changed")
    sys.exit(0)

i = src.index(HEADER) + len(HEADER)
out = src[:i] + "\n" + LINE + src[i:]
open(QUEUE, "w").write(out)

fresh = open(QUEUE).read()                      # verify
assert LINE in fresh, "declined-list write did not stick"
start = fresh.index(HEADER)
print("declined list now:\n" + fresh[start:start + 900].split("\n\n")[0])
