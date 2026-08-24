"""Per-vendor session state, so notifications fire on TRANSITION not on state.

Why this exists. The preflight notification is the job's most valuable signal
and its most fragile one. Fired every run, a session that stays dead for three
days sends three identical alerts, and the channel teaches exactly the blindness
the background Chrome already has. Fired on change, it sends one.

This matters more if the job runs several times a day as a daytime canary: at
4 runs/day a week-long outage is 28 notifications, which nobody reads by day two.

Also records WHEN a vendor was last seen healthy, which is the "last successful
read" the dashboard brief asks for — distinct from when the job last ran. Those
two diverge exactly when something is wrong.

  preflight_state.py --set amazon=OK --set mcmaster=OUT   # record, report changes
  preflight_state.py --report                             # show current state

Prints NOTIFY: lines only for vendors whose state actually changed. A caller
that sends a push for every line, and nothing when there are none, is correct.
"""
import argparse
import datetime
import json
import os

PATH = "/Volumes/4TB_Removable/inventree/preflight_state.json"
VALID = {"OK", "OUT", "UNKNOWN"}

ap = argparse.ArgumentParser()
ap.add_argument("--set", action="append", default=[], metavar="VENDOR=STATE")
ap.add_argument("--report", action="store_true")
a = ap.parse_args()

state = {}
if os.path.exists(PATH):
    try:
        state = json.load(open(PATH))
    except (ValueError, OSError):
        # A corrupt state file must not read as "everything is fine". Treat it
        # as no knowledge, which makes the next observation a transition.
        print("!! state file unreadable — treating all vendors as UNKNOWN")
        state = {}

now = datetime.datetime.now().replace(microsecond=0).isoformat(sep=" ")
changed = []

for item in a.set:
    vendor, _, new = item.partition("=")
    vendor, new = vendor.strip().lower(), new.strip().upper()
    if new not in VALID:
        print(f"?? {vendor}: {new!r} is not one of {sorted(VALID)} — ignored")
        continue

    prev = state.get(vendor, {})
    old = prev.get("state", "UNKNOWN")
    rec = dict(prev)
    rec["state"] = new
    rec["checked"] = now
    if new == "OK":
        rec["last_ok"] = now
    rec.setdefault("last_ok", None)

    if old != new:
        rec["changed"] = now
        changed.append((vendor, old, new, rec.get("last_ok")))
        print(f"CHANGED  {vendor}: {old} -> {new}")
    else:
        print(f"same     {vendor}: {new} (since {prev.get('changed', 'unknown')})")
    state[vendor] = rec

if a.set:
    with open(PATH, "w") as fh:
        json.dump(state, fh, indent=2, sort_keys=True)
    fresh = json.load(open(PATH))          # verify the write stuck
    for vendor, _, new, _ in changed:
        assert fresh[vendor]["state"] == new, f"state write did not stick for {vendor}"

    for vendor, old, new, last_ok in changed:
        if new == "OUT":
            print(f"NOTIFY: {vendor} session went OUT (was {old}; last healthy {last_ok or 'never'})")
        elif new == "OK" and old == "OUT":
            print(f"NOTIFY: {vendor} session is back")
    if not changed:
        print("NOTIFY: none — no vendor changed state, so no push this run")

if a.report or not a.set:
    print(f"\n-- session state ({PATH}) --")
    if not state:
        print("   (empty — nothing recorded yet)")
    for vendor in sorted(state):
        r = state[vendor]
        print(f"   {vendor:12s} {r.get('state','?'):8s} checked={r.get('checked','?')} "
              f"last_ok={r.get('last_ok') or 'never'} since={r.get('changed','?')}")
