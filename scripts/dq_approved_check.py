"""List [x] APPROVED / DECLINED lines still sitting in the open section of pending_decisions.md.

Read-only. Lets the overnight run confirm the 'execute approved items' step has
nothing to do without a hand-built ssh/grep line.
"""

import pathlib
import re

QUEUE = pathlib.Path("/Volumes/4TB_Removable/inventree/pending_decisions.md")

text = QUEUE.read_text()
m = re.search(r"^## open.*?$(.*?)(?=^## |\Z)", text, re.M | re.S)
section = m.group(1) if m else ""
hits = [ln for ln in section.splitlines()
        if re.match(r"^- \[[xX]\]", ln) or "DECLINED" in ln or "APPROVED" in ln]
print(f"open-section actionable lines: {len(hits)}")
for ln in hits:
    print(f"  {ln[:200]}")
