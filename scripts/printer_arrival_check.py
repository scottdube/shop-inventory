"""Commissioning probe for the replacement QL-810W at 192.168.30.252.

All four of ping/631/9100/80 dark + no power LED == power fault.
A latched raster error still answers IPP with `idle` -- that is the distinction.
"""
import socket
import subprocess

HOST = "192.168.30.252"
PORTS = [(631, "IPP"), (9100, "raw/JetDirect"), (80, "web UI")]


def ping():
    r = subprocess.run(
        ["ping", "-c", "3", "-W", "1000", HOST],
        capture_output=True, text=True,
    )
    return r.returncode == 0, r.stdout.strip().splitlines()[-2:]


def port(p):
    s = socket.socket()
    s.settimeout(2.0)
    try:
        s.connect((HOST, p))
        return True
    except Exception as e:
        return f"{type(e).__name__}: {e}"
    finally:
        s.close()


print(f"=== network probe {HOST} ===")
ok, tail = ping()
print(f"ping: {'UP' if ok else 'NO REPLY'}")
for line in tail:
    print(f"      {line}")

results = {}
for p, name in PORTS:
    r = port(p)
    results[p] = r is True
    print(f"port {p:<5} ({name:<14}): {'OPEN' if r is True else 'closed  -- ' + str(r)}")

alive = ok or any(results.values())
print(f"\nverdict: {'something answers' if alive else 'ALL DARK'}")

print("\n=== CUPS queue state ===")
for cmd in (
    ["lpstat", "-p", "QL810W"],
    ["lpstat", "-W", "completed", "-o", "QL810W"],
    ["lpstat", "-W", "not-completed", "-o", "QL810W"],
):
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(f"$ {' '.join(cmd)}")
    out = (r.stdout + r.stderr).strip()
    print(out if out else "(no output)")
    print()
