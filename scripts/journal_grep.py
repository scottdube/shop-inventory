#!/usr/bin/env python3
"""Read-only: print enrich_progress.md lines matching a term, with the run header.

Exists because journal.py has no search and show_progress.py dumps the whole
decision queue too. Answers "did an earlier sweep already see order X, and what
did it decide?" -- the question a silent skip leaves open. Runs on the Mini via
itq; the journal is not on this laptop.
"""
import sys

PATH = "/Volumes/4TB_Removable/inventree/enrich_progress.md"

term = (sys.argv[1] if len(sys.argv) > 1 else "").lower()
if not term:
    print("usage: journal_grep.py <term>")
    sys.exit(2)

header = ""
hits = 0
with open(PATH) as f:
    for line in f:
        line = line.rstrip("\n")
        if line.startswith("### "):
            header = line
        if term in line.lower():
            hits += 1
            if line == header:
                print(line[:600])
            else:
                print(f"{header}\n    {line[:600]}")
print(f"-- {hits} line(s) matching {term!r}")
