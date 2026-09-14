#!/usr/bin/env python3
"""Print the tail of enrich_progress.md and all of pending_decisions.md.

Read-only. Exists so an unattended run can see prior state without an ad-hoc
ssh/tail one-liner (which is unapprovable -- see the task file).
"""
import os

ROOT = "/Volumes/4TB_Removable/inventree"
N = int(os.environ.get("PROGRESS_TAIL", "80"))

p = os.path.join(ROOT, "enrich_progress.md")
print(f"=== tail -{N} {p} ===")
try:
    with open(p) as f:
        lines = f.read().splitlines()
    for line in lines[-N:]:
        print(line)
except FileNotFoundError:
    print("(missing)")

d = os.path.join(ROOT, "pending_decisions.md")
print(f"\n=== {d} ===")
try:
    with open(d) as f:
        print(f.read())
except FileNotFoundError:
    print("(missing)")
