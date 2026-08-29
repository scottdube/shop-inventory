"""Print the tail of enrich_progress.md.

Exists because the overnight report lives only in a chat session that scrolls
away; the journal is the durable copy, and reading it needs a fixed-shape
command (itq run) rather than an ad-hoc ssh/cat.

    itq run scripts/show_journal.py [lines]
"""

import sys

PATH = "/Volumes/4TB_Removable/inventree/enrich_progress.md"

n = int(sys.argv[1]) if len(sys.argv) > 1 else 60

with open(PATH) as fh:
    lines = fh.read().splitlines()

print(f"{PATH}: {len(lines)} lines, showing last {min(n, len(lines))}")
print("-" * 60)
for line in lines[-n:]:
    print(line)
