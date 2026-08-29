"""Close one item on the decision queue — the half decide.py never had.

decide.py only appends. The queue's own dedupe test already understands
"- [x] " as closed, so the format was always there; nothing could write it.
That is most of why the queue reached 30 open items, several of them settled
weeks ago: a resolved item nobody can tick reads exactly like an open one, and
the next run re-finds it and re-reasons about it.

Deliberately narrow, because an unattended run holding a closer is a way for
Scott's queue to be tidied by something he cannot see:

  - closes exactly ONE key per call, named in full; no globbing, no sweep
  - refuses unless that key matches exactly one OPEN line
  - requires --resolution, appended to the line as the reason and the date
  - re-reads and asserts, per the repo's verify-every-write invariant

Usage:
  itq run scripts/close_decision.py <key> --resolution "what settled it"
"""
import argparse
import os
import sys
from datetime import datetime

PATH = "/Volumes/4TB_Removable/inventree/pending_decisions.md"

ap = argparse.ArgumentParser()
ap.add_argument("key", help="the item's key — the text before the first '|'")
ap.add_argument("--resolution", required=True,
                help="what settled it; recorded on the line")
a = ap.parse_args()

if not os.path.exists(PATH):
    sys.exit(f"ABORT: {PATH} not found")

body = open(PATH).read()
lines = body.splitlines(keepends=True)
open_prefix = "- [ ] " + a.key
hits = [i for i, ln in enumerate(lines) if ln.startswith(open_prefix)]

if not hits:
    already = [ln for ln in lines if ln.startswith("- [x] " + a.key)]
    if already:
        sys.exit(f"already closed, nothing to do: {a.key}")
    sys.exit(f"ABORT: no OPEN line starts with key {a.key!r}")
if len(hits) > 1:
    sys.exit(f"ABORT: key {a.key!r} matches {len(hits)} open lines; "
             "refusing to guess which one")

i = hits[0]
today = datetime.now().strftime("%Y-%m-%d")
before = lines[i]
lines[i] = ("- [x] " + before[len("- [ ] "):].rstrip("\n")
            + f" | CLOSED {today}: {a.resolution}\n")

with open(PATH, "w") as fh:
    fh.write("".join(lines))

fresh = open(PATH).read()
assert lines[i] in fresh, "close did not stick"
assert not any(ln.startswith(open_prefix)
               for ln in fresh.splitlines()), "open line survived the close"

print(f"closed: {a.key}")
print(f"  was:  {before[:110].rstrip()}")
print(f"  now:  {lines[i][:110].rstrip()}")
