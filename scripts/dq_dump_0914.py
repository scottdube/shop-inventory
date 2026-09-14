#!/usr/bin/env python3
"""Print the full text of named open decision items. Read-only.

Exists so a run can READ an item before acting on it. Closing on a key that
merely looks right is the 'search the requirement, not the part number' trap;
these items must be falsified individually, not matched by name.
"""
import sys

PATH = "/Volumes/4TB_Removable/inventree/pending_decisions.md"
keys = sys.argv[1:]

lines = open(PATH).read().splitlines()
for key in keys:
    hits = [ln for ln in lines if ln.startswith(f"- [ ] {key}")]
    if not hits:
        print(f"\n### {key}\n  (no OPEN line with this key)")
        continue
    for h in hits:
        print(f"\n### {key}\n{h}")
