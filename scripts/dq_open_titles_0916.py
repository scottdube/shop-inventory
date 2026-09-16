#!/usr/bin/env python3
"""Print every OPEN decision-queue line under '## open', newest last. Read-only.

Exists because dq_shape_0914.py counts the open items and dq_dump_0914.py needs
a key you already know; neither one will tell a morning brief WHICH items are
waiting. Prints the full line so an item can be read and decided, not just
tallied -- a category and a date is not a decidable item.
"""
PATH = "/Volumes/4TB_Removable/inventree/pending_decisions.md"

lines = open(PATH).read().splitlines()
inopen = False
n = 0
for ln in lines:
    if ln.startswith("## "):
        inopen = ln.startswith("## open")
        continue
    if inopen and ln.startswith("- [ ] "):
        n += 1
        print(f"{n:3d}. {ln[6:]}")
print(f"\nTOTAL OPEN: {n}")
