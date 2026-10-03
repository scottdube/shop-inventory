"""Read-only: print decision-queue lines matching any given term (case-insensitive).

decide.py appends but cannot list beyond the head that sweep_date_read.py shows,
so a sweep that wants to know "is this vendor already queued?" needs this.
"""
import sys

PATH = "/Volumes/4TB_Removable/inventree/pending_decisions.md"
terms = [t.lower() for t in sys.argv[1:]]
for n, ln in enumerate(open(PATH), 1):
    low = ln.lower()
    if any(t in low for t in terms):
        print(f"{n}: {ln.rstrip()[:300]}")
