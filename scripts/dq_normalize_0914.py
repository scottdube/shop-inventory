#!/usr/bin/env python3
"""Idempotent tidy: no closed item may sit under '## open — needs Scott'.

Companion to dq_restructure_0914.py (which re-filed the open items) and to the
close_decision.py fix that makes closing MOVE the line. This handles the ones
closed before that fix landed -- on 2026-09-14 that is 7 lines ticked in place
while still under the open header.

Moves only '- [x] ' lines that are inside the open section, to the top of
'## done', newest-closed first. Touches nothing else. Safe to re-run: with
nothing stranded it reports 0 and rewrites nothing.
"""
import re
import shutil
from collections import Counter
from datetime import datetime

PATH = "/Volumes/4TB_Removable/inventree/pending_decisions.md"

raw = open(PATH).read()
lines = raw.splitlines(keepends=True)
before = Counter(ln for ln in lines if re.match(r"^- \[[ x]\] ", ln))


def section_of(idx):
    for ln in reversed(lines[:idx]):
        if ln.startswith("## "):
            return ln.strip()
    return None


stranded = [i for i, ln in enumerate(lines)
            if ln.startswith("- [x] ") and (section_of(i) or "").startswith("## open")]

if not stranded:
    print("0 stranded closed items under '## open' — nothing to do")
    raise SystemExit(0)

bak = f"{PATH}.{datetime.now().strftime('%Y%m%d-%H%M%S')}.norm.bak"
shutil.copy2(PATH, bak)
print(f"backup: {bak}")
print(f"{len(stranded)} closed items stranded under '## open':")
for i in stranded:
    print(f"  {lines[i][:96].rstrip()}")

moved = [lines[i] for i in stranded]
for i in reversed(stranded):
    del lines[i]

done_idx = next((k for k, ln in enumerate(lines)
                 if ln.rstrip("\n").strip() == "## done"), None)
assert done_idx is not None, "no '## done' section to move into"
for ln in reversed(moved):
    lines.insert(done_idx + 1, ln)

open(PATH, "w").write("".join(lines))

fresh = open(PATH).read().splitlines(keepends=True)
after = Counter(ln for ln in fresh if re.match(r"^- \[[ x]\] ", ln))
assert after == before, "item lines changed — only their section may change"
lines = fresh
still = [i for i, ln in enumerate(lines)
         if ln.startswith("- [x] ") and (section_of(i) or "").startswith("## open")]
assert not still, f"{len(still)} closed items still under '## open'"

n_open = sum(v for k, v in after.items() if k.startswith("- [ ] "))
print(f"\nVERIFIED: moved {len(moved)} to '## done'; "
      f"'## open' now holds {n_open} genuinely open items")
