"""Append a line to the overnight progress journal. One stable command shape.

The task file told each run to write its RUN STARTED marker with a bespoke
ssh + printf one-liner. That is unapprovable by construction:

  * it contains backslash-escaped whitespace (`date +%Y-%m-%d\\ %H:%M`), which
    the permission layer flags on sight; and
  * the queue description is interpolated INTO the command, so every run emits
    a different string and no allow rule can ever match twice.

Result: the 02:05 run on 2026-08-22 sat on a permission prompt for seven hours
and did nothing. The task file's own notes record the same hang on 08-18.
Nights when it worked were nights somebody happened to be awake to click.

This is the documented fix — a script with a fixed invocation, so one rule
covers it forever:

    itq run scripts/journal.py --start "queue: A images, then D keywords"
    itq run scripts/journal.py --line  "images: 34 attached"
    itq run scripts/journal.py --end   "34 images, 2 POs, preflight OK"
    itq run scripts/journal.py --check          # did the last run finish?

Writes on the Mini, where the journal lives, and prints what it wrote so the
caller can confirm rather than assume.
"""
import argparse, os, sys
from datetime import datetime

PATH = "/Volumes/4TB_Removable/inventree/enrich_progress.md"

ap = argparse.ArgumentParser()
ap.add_argument("--start")
ap.add_argument("--line")
ap.add_argument("--end")
ap.add_argument("--check", action="store_true")
a = ap.parse_args()

now = datetime.now().strftime("%Y-%m-%d %H:%M")

if a.check:
    body = open(PATH).read() if os.path.exists(PATH) else ""
    i = body.rfind("RUN STARTED")
    if i < 0:
        print("no RUN STARTED found")
        sys.exit(0)
    tail = body[i:]
    died = "RUN COMPLETE" not in tail
    print(f"last RUN STARTED: {body[max(0,i-20):i+70].strip()[:90]}")
    print("PREVIOUS RUN DIED — no completion after it" if died
          else "previous run completed cleanly")
    sys.exit(0)

if a.start:
    text = f"\n### {now} — RUN STARTED ({a.start})\n"
elif a.end:
    text = f"\n### {now} — RUN COMPLETE — {a.end}\n"
elif a.line:
    text = f"- {now}  {a.line}\n"
else:
    ap.error("need --start, --line, --end or --check")

with open(PATH, "a") as fh:
    fh.write(text)

# Confirm by re-reading rather than trusting the write.
assert open(PATH).read().endswith(text), "journal write did not stick"
print(f"wrote: {text.strip()}")
