#!/usr/bin/env python3
"""Strip the item count out of the '## open' header.

dq_restructure_0914.py wrote '## open — needs Scott  (70 items)'. decide.py then
added one and close_decision.py moved six out, and the header still said 70 --
a count that no writer updates is the same defect the restructure existed to
fix, just smaller: a header asserting something about its contents that nothing
keeps true. The old header said '(1 item)' over 58 of them for 27 days.

So the header carries no count. dq_shape_0914.py counts, on demand, from the
file. Idempotent.
"""
import re

PATH = "/Volumes/4TB_Removable/inventree/pending_decisions.md"
WANT = "## open — needs Scott"

lines = open(PATH).read().splitlines(keepends=True)
changed = False
for i, ln in enumerate(lines):
    if re.match(r"^## open\b", ln) and ln.rstrip("\n").rstrip() != WANT:
        print(f"was: {ln.rstrip()}")
        lines[i] = WANT + "\n"
        changed = True
        break

if not changed:
    print("header already countless — nothing to do")
    raise SystemExit(0)

open(PATH, "w").write("".join(lines))
fresh = open(PATH).read().splitlines()
assert WANT in fresh, "header rewrite did not stick"
assert not any(re.match(r"^## open\b", l) and l != WANT for l in fresh), \
    "a counted open header survived"
print(f"now: {WANT}")
