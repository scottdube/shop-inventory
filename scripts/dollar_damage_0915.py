"""Read-only: how many journal lines lost a dollar amount to local shell
expansion of $1..$99 before it ever reached itq?

Signature: a bare '.dd' with no digit before the decimal point. '$12.99' loses
'$12' (empty positional parameter 12) and leaves '.99'.

Prints the MATCHED SPAN with surrounding words, not the head of the line — the
first version truncated at 200 chars and showed none of the actual evidence,
which is how a measurement reports six hits and proves nothing.
"""
import re

PATH = "/Volumes/4TB_Removable/inventree/enrich_progress.md"

PAT = re.compile(r"(?<![\d])(?<![\w])\.\d{2}(?![\d])")

lines = open(PATH).read().splitlines()

print("journal lines total :", len(lines))
n_hits = 0
for i, l in enumerate(lines):
    for m in PAT.finditer(l):
        n_hits += 1
        a, b = max(0, m.start() - 70), min(len(l), m.end() + 40)
        print(f"\nline {i+1}  (date: {l[:20].strip()})")
        print(f"    ...{l[a:b]}...")
print(f"\ntotal matched spans: {n_hits}")
