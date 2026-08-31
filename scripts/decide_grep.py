#!/usr/bin/env python3
"""Read-only: print decision-queue lines matching a term.

Exists because decide.py has no --list, and a duplicate decision is worse than
no decision — Scott reads the queue by hand. The queue lives on the Mini at
/Volumes/4TB_Removable, so this has to run there via itq, never as a local path.
"""
import os
import sys

PATH = "/Volumes/4TB_Removable/inventree/pending_decisions.md"

term = (sys.argv[1] if len(sys.argv) > 1 else "").lower()

if not os.path.exists(PATH):
    print(f"!! queue file missing: {PATH}")
    sys.exit(1)

lines = open(PATH).read().splitlines()
open_items = [ln for ln in lines if ln.strip().startswith("- [ ]")]
print(f"{len(open_items)} open decisions in {PATH}")

if not term:
    for ln in open_items:
        print(ln)
    sys.exit(0)

hits = [ln for ln in lines if term in ln.lower()]
print(f"-- {len(hits)} line(s) matching {term!r}")
for ln in hits:
    print(ln)
