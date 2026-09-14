#!/usr/bin/env python3
"""Move every OPEN decision-queue item into a real '## open' section.

WHY (measured 2026-09-14 by dq_shape_0914.py, live file):

  ## open - needs Scott  (1 item)                       open=1
  ## done — executed interactively 2026-08-18: ...      open=58  closed=16
  ## resolved by reading the order page (Chrome) ...    open=12  closed=0
  ## held — awaiting Scott                              EMPTY

70 unresolved items are filed under headers that say 'done' and 'resolved by
reading the order page', while the section actually headed 'open' claims one
item and the section headed 'held — awaiting Scott' is empty. A reader who
trusts the headers concludes there is one open decision. There are 70.

MECHANISM, and it is one line of decide.py, not drift: decide.py inserts each
new item immediately before the marker '## declined — never re-ask'. That
marker happens to sit at the end of the 2026-08-18 'done — executed
interactively' section, so every item the nightly run has queued since then has
landed inside a section headed 'done'. The 12 under 'resolved by reading the
order page' predate that marker logic and hit the append-to-EOF fallback, which
puts them under whatever header is last in the file.

So the queue has had no working open section since 2026-08-18, which is most of
the explanation for a 71-item backlog: an item nobody sees is an item that gets
re-reasoned about and re-queued instead of answered.

WHAT THIS DOES, and deliberately nothing more. It MOVES lines. It does not
change any item's text, its checkbox state, or its meaning:

  - every '- [ ] ' line in the file is collected and re-filed under a single
    '## open — needs Scott' section, ordered oldest date first
  - every '- [x] ' line stays exactly where it is, under the header that
    describes how it was closed -- that history is the point of those sections
  - a sentinel comment is left at the end of the open section so decide.py can
    insert into it (see the companion edit to decide.py; without that edit the
    defect regenerates on the next queued item)
  - the file is copied to a timestamped .bak first, and the multiset of item
    lines is asserted identical before and after

Rejected alternative: leave the data alone and only relabel the headers. That
reads as 'this section is both done and open', and the next append still lands
in the wrong place -- it fixes the appearance and leaves the mechanism.
"""
import re
import shutil
from collections import Counter
from datetime import datetime

PATH = "/Volumes/4TB_Removable/inventree/pending_decisions.md"
SENTINEL = "<!-- new items are inserted above this line — see decide.py -->"
OPEN_HEADER = "## open — needs Scott"

raw = open(PATH).read()
bak = f"{PATH}.{datetime.now().strftime('%Y%m%d-%H%M%S')}.bak"
shutil.copy2(PATH, bak)
print(f"backup: {bak}")

lines = raw.splitlines()
before_items = Counter(ln for ln in lines if re.match(r"^- \[[ x]\] ", ln))
n_open_before = sum(v for k, v in before_items.items() if k.startswith("- [ ] "))
print(f"before: {sum(before_items.values())} item lines, {n_open_before} open")

# ---- split into (header, [body lines]) blocks -------------------------------
blocks = []            # [header_or_None, [lines]]
cur = [None, []]
blocks.append(cur)
for ln in lines:
    if ln.startswith("## "):
        cur = [ln, []]
        blocks.append(cur)
    else:
        cur[1].append(ln)

# ---- pull every open item out of every block --------------------------------
opens = []
for header, body in blocks:
    keep = []
    for ln in body:
        if ln.startswith("- [ ] "):
            opens.append(ln)
        else:
            keep.append(ln)
    body[:] = keep

assert len(opens) == n_open_before, f"lost items: {len(opens)} != {n_open_before}"


def sort_key(ln):
    """Oldest first, by the item's own trailing date field. Undated last."""
    dates = re.findall(r"\b(20\d\d-\d\d-\d\d)\b", ln)
    return (0, dates[-1]) if dates else (1, "")


opens.sort(key=sort_key)

# ---- rebuild ----------------------------------------------------------------
out = []
placed = False
sweep_marker = None

for header, body in blocks:
    if header and header.startswith("## open"):
        # Replace the stale '(1 item)' header, keep its explanatory comments.
        # NO count in the header: nothing updates it. This script first wrote
        # '(70 items)', decide.py added one and close_decision.py moved six out
        # within the same run, and the header was wrong by seven immediately.
        # A count that no writer maintains is the defect this restructure
        # exists to fix, in miniature -- the old header said '(1 item)' over 58
        # of them for 27 days. dq_shape_0914.py counts from the file instead.
        out.append(OPEN_HEADER)
        out.extend(l for l in body if l.startswith("#") or not l.strip())
        out.append("")
        out.extend(opens)
        out.append("")
        out.append(SENTINEL)
        out.append("")
        placed = True
        continue
    if header:
        out.append(header)
    out.extend(body)

assert placed, "no '## open' header found to re-file into"

# Keep the sweep marker as the last line, where decide.py --sweep-date puts it.
body_lines = [l for l in out if not l.startswith("<!-- last-po-sweep:")]
marker = [l for l in out if l.startswith("<!-- last-po-sweep:")]
text = "\n".join(body_lines).rstrip("\n") + "\n"
if marker:
    text += "\n" + marker[-1] + "\n"

open(PATH, "w").write(text)

# ---- verify: re-read, compare the multiset of item lines --------------------
fresh = open(PATH).read().splitlines()
after_items = Counter(ln for ln in fresh if re.match(r"^- \[[ x]\] ", ln))
assert after_items == before_items, (
    "item lines changed!\n"
    f"  only before: {[k[:60] for k in (before_items - after_items)]}\n"
    f"  only after:  {[k[:60] for k in (after_items - before_items)]}"
)
assert SENTINEL in "\n".join(fresh), "sentinel missing"
if marker:
    assert fresh[-1].startswith("<!-- last-po-sweep:"), "sweep marker not last"

print(f"after:  {sum(after_items.values())} item lines, "
      f"{sum(v for k, v in after_items.items() if k.startswith('- [ ] '))} open")
print("VERIFIED: every item line identical, only its section changed")
for ln in fresh:
    if ln.startswith("## "):
        print(f"  {ln}")
