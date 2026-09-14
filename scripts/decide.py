"""Append items to the decision queue, or record the last PO sweep date.

Scott's rule: decisions get DROPPED TO HIM, never left in a file he has to go
looking for — so the queue file is paired with a PushNotification from the
caller. This script only owns the file half.

One stable command shape, same reason as journal.py: an unattended run cannot
answer a permission prompt, so an ad-hoc ssh/printf line is a dead run, not a
slow one.
"""
import argparse
import os
from datetime import datetime

PATH = "/Volumes/4TB_Removable/inventree/pending_decisions.md"

ap = argparse.ArgumentParser()
ap.add_argument("--add", action="append", default=[],
                help="a full queue line, without the leading '- [ ] '")
ap.add_argument("--sweep-date", help="record the PO sweep date reached")
a = ap.parse_args()

body = open(PATH).read() if os.path.exists(PATH) else "# Pending decisions queue\n"
today = datetime.now().strftime("%Y-%m-%d")
added = []

for item in a.add:
    line = f"- [ ] {item} | {today}\n"
    # Match the key only where a queue line actually starts. A bare substring
    # test fired on 2026-08-23: the key "image queue" matched the words "the
    # image queue" inside an existing note's prose and silently swallowed a new
    # item. A suppressed decision looks exactly like nothing happening, which is
    # the failure mode this whole file exists to prevent.
    key = item.split("|")[0].strip()
    if any(ln.startswith(("- [ ] " + key, "- [x] " + key))
           for ln in body.splitlines()):
        print(f"already queued, not duplicated: {item[:60]}")
        continue
    added.append(line)

if added:
    # Insert into the OPEN section, marked by a sentinel that lives at its end.
    #
    # This used to insert before "\n## declined — never re-ask". That marker sits
    # at the end of the 2026-08-18 "## done — executed interactively" section, so
    # every item queued since then landed under a header reading *done* — 58 of
    # them by 2026-09-14, plus 12 more under "## resolved by reading the order
    # page" from the append-to-EOF fallback below, while "## open" claimed one
    # item and "## held — awaiting Scott" sat empty. A reader trusting the
    # headers saw one open decision; there were 70. An item nobody sees does not
    # get answered — it gets re-measured and re-queued by the next run, which is
    # most of how the backlog got that big.
    #
    # The sentinel is inside the open section, so correctness no longer depends
    # on which header happens to precede "## declined".
    sentinel = "<!-- new items are inserted above this line — see decide.py -->"
    declined = "\n## declined — never re-ask"
    if sentinel in body:
        body = body.replace(sentinel, "".join(added) + sentinel, 1)
    elif declined in body:
        # Pre-2026-09-14 file shape. Kept so this script still works against an
        # un-restructured copy, but it files items wherever that marker lands.
        print("WARNING: no open-section sentinel; falling back to the "
              "## declined marker, which may file these under a 'done' header")
        body = body.replace(declined, "".join(added) + declined, 1)
    else:
        print("WARNING: no marker found; appending at end of file")
        body += "".join(added)

if a.sweep_date:
    tag = "<!-- last-po-sweep:"
    stamp = f"{tag} {a.sweep_date} -->\n"
    lines = [ln for ln in body.splitlines(keepends=True) if not ln.startswith(tag)]
    body = "".join(lines).rstrip("\n") + "\n\n" + stamp

with open(PATH, "w") as fh:
    fh.write(body)

fresh = open(PATH).read()
for line in added:
    assert line in fresh, "decision write did not stick"
if a.sweep_date:
    assert a.sweep_date in fresh, "sweep date write did not stick"

print(f"added {len(added)} decision line(s)"
      + (f"; sweep date -> {a.sweep_date}" if a.sweep_date else ""))
