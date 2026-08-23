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
    marker = "\n## declined — never re-ask"
    if marker in body:
        body = body.replace(marker, "".join(added) + marker, 1)
    else:
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
