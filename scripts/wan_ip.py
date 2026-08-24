"""Record the Mini's public IP, so 'reputation changed' can be told apart from
'the IP changed'.

The Mini has 119 days uptime, but the WAN address is handed out by the ISP to
the router, not held by the Mini. A DHCP lease change would swap in an address
with entirely different reputation and would look exactly like a reputation
recovery. Nothing in this repo has ever recorded the address, so today's
"Amazon stopped blocking us" cannot be attributed. Fix that going forward.
"""
import datetime
import json
import os
import subprocess

PATH = "/Volumes/4TB_Removable/inventree/wan_ip_history.json"


def get(url):
    try:
        return subprocess.run(["curl", "-sS", "--max-time", "20", url],
                              capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception as e:  # noqa: BLE001
        return f"ERR {e}"


ip = get("https://api.ipify.org")
print("public IP :", ip)

info = get(f"https://ipinfo.io/{ip}/json")
try:
    d = json.loads(info)
    print("org       :", d.get("org"))
    print("city      :", d.get("city"), d.get("region"), d.get("postal"))
except ValueError:
    print("geo lookup unparseable:", info[:120])
    d = {}

hist = []
if os.path.exists(PATH):
    try:
        hist = json.load(open(PATH))
    except (ValueError, OSError):
        print("!! history unreadable — starting fresh")

now = datetime.datetime.now().replace(microsecond=0).isoformat(sep=" ")
if hist and hist[-1].get("ip") == ip:
    print(f"\nunchanged since {hist[-1]['first_seen']} ({len(hist)} record(s))")
    hist[-1]["last_seen"] = now
else:
    if hist:
        print(f"\n** IP CHANGED: {hist[-1].get('ip')} -> {ip} "
              f"(previous first seen {hist[-1].get('first_seen')}) **")
    else:
        print("\nfirst record — no prior address on file, so today's reputation "
              "recovery cannot be attributed to IP vs reputation. From now on it can.")
    hist.append({"ip": ip, "org": d.get("org"), "first_seen": now, "last_seen": now})

with open(PATH, "w") as fh:
    json.dump(hist, fh, indent=2)
assert json.load(open(PATH))[-1]["ip"] == ip, "history write did not stick"
print(f"recorded -> {PATH}")
