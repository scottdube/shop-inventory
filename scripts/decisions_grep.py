"""Read-only: print decision-queue lines matching a term (case-insensitive).

Exists because decide.py dedupes on the exact key only, and the triage key
carries a date, so a vendor already queued under an earlier date would be
queued again. Check by vendor before --add.

    itq run scripts/decisions_grep.py godaddy
"""
import sys

PATH = "/Volumes/4TB_Removable/inventree/pending_decisions.md"
terms = [t.lower() for t in sys.argv[1:]]
n = 0
for ln in open(PATH):
    low = ln.lower()
    if any(t in low for t in terms):
        print(ln.rstrip()[:400])
        n += 1
print(f"{n} matching line(s) for {terms}")
