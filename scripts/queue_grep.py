"""Print decision-queue lines containing a term (case-insensitive), read-only.

decide.py dedupes only on the exact key prefix, so a vendor queued earlier
under a different key (order number vs no-order-no-<date>) is invisible to it.
Grep before --add when the key shape may have changed between sweeps.
"""
import sys

PATH = "/Volumes/4TB_Removable/inventree/pending_decisions.md"
terms = [t.lower() for t in sys.argv[1:]]
for n, ln in enumerate(open(PATH), 1):
    if any(t in ln.lower() for t in terms):
        print(f"{n}: {ln.rstrip()[:300]}")
