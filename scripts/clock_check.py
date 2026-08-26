"""Report the Mini's clock, timezone, and NTP sync state.

Written 2026-08-26 after the overnight journal recorded two impossible
timestamps minutes apart: run_gap_check.py printed "now 2026-08-26 02:05"
and journal.py --line printed "2026-08-26 06:54" a few minutes later, while
the laptop read 06:55 EDT throughout.

Every guard in this job is time-keyed -- the stand-down window, the
STARTED/COMPLETE pairing, the sweep-date arithmetic in queue C. A clock that
silently jumps four hours does not make those checks fail loudly; it makes
them return confident wrong answers, which is worse.

Read-only.
"""
import subprocess
from datetime import datetime, timezone


def sh(cmd):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True,
                              text=True, timeout=15).stdout.strip()
    except Exception as e:                      # noqa: BLE001
        return f"ERR: {e}"


print(f"python now (local) : {datetime.now():%Y-%m-%d %H:%M:%S}")
print(f"python now (utc)   : {datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S} UTC")
print(f"date(1)            : {sh('date')}")
print(f"timezone           : {sh('systemsetup -gettimezone 2>/dev/null')}")
print(f"network time       : {sh('systemsetup -getusingnetworktime 2>/dev/null')}")
print(f"time server        : {sh('systemsetup -getnetworktimeserver 2>/dev/null')}")
print(f"uptime             : {sh('uptime')}")
print(f"boot time          : {sh('sysctl -n kern.boottime')}")
