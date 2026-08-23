"""Restart BinScan on the Mini and prove it came back.

Exists so a binscan deploy is two stable commands rather than an ad-hoc ssh:

    itq push binscan/app.py /Users/scottdube/binscan/app.py
    itq run  scripts/binscan_restart.py

Reports the md5 of what is on disk. A deploy that silently did not land looks
exactly like a deploy that did until someone checks the hash -- the same
lesson the InvenTree kill -HUP trap taught, where a restart returned HTTP 200
and served stale content.

Does NOT import django: binscan is a separate service and this only needs
launchctl and a socket.
"""
import hashlib, os, subprocess, sys, time, urllib.request

APP = "/Users/scottdube/binscan/app.py"
LABEL = "com.binscan"
URL = "http://127.0.0.1:8002/api/providers"

print("on disk:", hashlib.md5(open(APP, "rb").read()).hexdigest(), APP)

uid = os.getuid()
r = subprocess.run(["launchctl", "kickstart", "-k", f"gui/{uid}/{LABEL}"],
                   capture_output=True, text=True)
if r.returncode:
    print("kickstart FAILED:", r.returncode, r.stderr.strip() or r.stdout.strip())
    sys.exit(1)
print("kickstart ok")

# Poll rather than sleep a guessed interval -- uvicorn's startup time is not a
# constant and a fixed sleep either wastes time or reports a false failure.
for attempt in range(30):
    time.sleep(0.5)
    try:
        with urllib.request.urlopen(URL, timeout=2) as f:
            print(f"back up after {(attempt + 1) * 0.5:.1f}s — {f.status} {f.read(120).decode()}")
            sys.exit(0)
    except Exception as e:
        last = e
print("did NOT come back within 15s:", type(last).__name__, last)
sys.exit(1)
