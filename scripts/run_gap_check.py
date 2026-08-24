"""Did a run actually COMPLETE in the expected window? One primitive, two callers.

The 2026-08-24 miss cost a whole night and nobody noticed for six hours. The
scheduler reported the task as having run, and it had -- it died on a 529 at
02:09 having accomplished nothing. "The job ran" and "the job worked" are
different claims and only the journal knows the second one.

Two callers, deliberately the same code so they cannot disagree:

  * The OVERNIGHT job runs this FIRST as a stand-down guard. It is scheduled
    more than once now; if an earlier attempt already completed, later attempts
    exit immediately. That is what makes retry safe to schedule.
  * The DAYTIME sweep runs it as an alarm. If no completed run exists by
    morning, all three attempts failed and a human needs to know.

Verdicts, printed as a token the caller can branch on:
    COMPLETE                a run started AND completed inside the window
    STARTED_NOT_COMPLETE    started but never finished -- stall, crash, or 529
    NEVER_STARTED           nothing fired at all -- app closed, Mac asleep

Read-only.
"""
import argparse
import os
import re
from datetime import datetime, timedelta

PATH = "/Volumes/4TB_Removable/inventree/enrich_progress.md"

# "### 2026-08-24 08:12 — RUN STARTED (...)"   /   "... — RUN COMPLETE — ..."
HDR = re.compile(r"^###\s+(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})\s*[—-]+\s*RUN\s+(STARTED|COMPLETE)",
                 re.M)

ap = argparse.ArgumentParser()
ap.add_argument("--since", help="ISO 'YYYY-MM-DD HH:MM'. Default: 01:00 today.")
ap.add_argument("--hours", type=float, help="alternatively, look back this many hours")
ap.add_argument("--until", help="upper bound, ISO 'YYYY-MM-DD HH:MM'. Default: now.")
a = ap.parse_args()

now = datetime.strptime(a.until, "%Y-%m-%d %H:%M") if a.until else datetime.now()
if a.hours:
    cutoff = now - timedelta(hours=a.hours)
elif a.since:
    cutoff = datetime.strptime(a.since, "%Y-%m-%d %H:%M")
else:
    cutoff = now.replace(hour=1, minute=0, second=0, microsecond=0)
    if cutoff > now:                      # before 01:00, judge last night
        cutoff -= timedelta(days=1)

body = open(PATH).read() if os.path.exists(PATH) else ""
events = []
for m in HDR.finditer(body):
    when = datetime.strptime(f"{m.group(1)} {m.group(2)}", "%Y-%m-%d %H:%M")
    if cutoff <= when <= now:
        events.append((when, m.group(3)))
events.sort()

print(f"window   : since {cutoff:%Y-%m-%d %H:%M} (now {now:%Y-%m-%d %H:%M})")
print(f"events   : {len(events)}")
for when, kind in events:
    print(f"           {when:%Y-%m-%d %H:%M}  RUN {kind}")

kinds = [k for _, k in events]
if "COMPLETE" in kinds:
    verdict = "COMPLETE"
elif "STARTED" in kinds:
    verdict = "STARTED_NOT_COMPLETE"
else:
    verdict = "NEVER_STARTED"

print(f"\nVERDICT: {verdict}")

# For the overnight job: may a later attempt stand down?
print(f"STAND_DOWN: {'yes' if verdict == 'COMPLETE' else 'no'}")

# For the daytime sweep: is this worth waking a human for?
if verdict == "COMPLETE":
    print("NOTIFY: none")
elif verdict == "STARTED_NOT_COMPLETE":
    last = max(w for w, k in events if k == "STARTED")
    print(f"NOTIFY: overnight run started {last:%H:%M} but never completed — "
          f"stalled, crashed, or hit an API error mid-run")
else:
    print("NOTIFY: NO overnight run in the window at all — every scheduled "
          "attempt failed, or the app was closed")
