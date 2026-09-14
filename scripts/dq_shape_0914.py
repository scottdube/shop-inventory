#!/usr/bin/env python3
"""Measure the SHAPE of pending_decisions.md: per-section open/closed counts.

Read-only. Written because the file's own headers and its contents disagree --
'## open - needs Scott (1 item)' while 71 lines are checkbox-open. Before
proposing any restructure, establish exactly which sections hold open items and
whether open and closed lines are interleaved inside a section.
"""
import re

PATH = "/Volumes/4TB_Removable/inventree/pending_decisions.md"

with open(PATH) as f:
    lines = f.read().splitlines()

sections = []          # (header_lineno, header_text, [(lineno, state, id)])
cur = (0, "(preamble)", [])
sections.append(cur)

for i, line in enumerate(lines, 1):
    if line.startswith("## "):
        cur = (i, line[3:].strip(), [])
        sections.append(cur)
        continue
    m = re.match(r"^- \[( |x)\] (.+)$", line)
    if m:
        state, rest = m.groups()
        pid = rest.split("|")[0].strip()
        cur[2].append((i, state, pid))

print(f"{PATH}\n{len(lines)} lines\n")
total_open = total_closed = 0
for ln, header, items in sections:
    if not items:
        print(f"L{ln:<5} ## {header[:70]}   (no items)")
        continue
    op = [x for x in items if x[1] == " "]
    cl = [x for x in items if x[1] == "x"]
    total_open += len(op)
    total_closed += len(cl)
    # interleaving: does an open line appear AFTER a closed line in this section?
    states = "".join(x[1] for x in items).replace(" ", "o")
    interleaved = "xo" in states and "ox" in states
    print(f"L{ln:<5} ## {header[:70]}")
    print(f"        items={len(items):3d}  open={len(op):3d}  closed={len(cl):3d}  "
          f"pattern={states[:60]}{'...' if len(states) > 60 else ''}"
          f"{'  <-- INTERLEAVED' if interleaved else ''}")
    if op:
        print(f"        open ids: {', '.join(x[2][:34] for x in op[:4])}"
              f"{' ...' if len(op) > 4 else ''}")

print(f"\nTOTAL open={total_open} closed={total_closed}")

tail = [l for l in lines[-5:] if l.strip()]
print("\nlast non-blank lines:")
for t in tail:
    print(f"  {t[:120]}")
