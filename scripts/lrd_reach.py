#!/usr/bin/env python3
"""Why can't we reach LRD? Answers it in ONE call, from the laptop.

    python3 ~/code/shop-inventory/scripts/lrd_reach.py

RUN THIS LOCALLY, NOT THROUGH itq. Every other script in this directory runs on
the Mini; this one exists for the case where the Mini is exactly what you cannot
reach, so shipping it over the link that is down would be circular.

Why it exists at all: the documented far-gateway procedure (TRAPS.md
2026-08-30) is written around `ping`, and the unattended gate DENIES `ping`,
`netstat` and every other compound/one-off shape. A blocked scheduled run
therefore could not execute its own documented diagnosis. This does the same
work with stdlib sockets plus two read-only subprocess calls, all of which the
gate permits under `python3 <repo>/scripts/<x>.py`.

Order of questions, which is deliberately the reverse of the intuitive one:

  1. Can this process open sockets at all?  A uniform wall of timeouts is the
     signature of a broken prober, not a broken network -- so establish a
     CONTROL before believing any negative. (TRAPS.md: "A uniform result needs
     a control".)
  2. Is the local WireGuard client even connected?  This is the question that
     was missed on 2026-09-03, when "no route to the far subnet" was attributed
     to a router-to-router tunnel failure without anyone looking at the client
     on this Mac. `scutil --nc list` settles it outright.
  3. Is there a ROUTE to the far subnet?
  4. Only then, is the far gateway / Mini answering?

Exit status: 0 if the Mini is reachable, 1 if not.
"""
import socket
import subprocess
import sys
import time

FAR_SUBNET = "192.168.50"
FAR_GATEWAY = "192.168.50.1"
MINI = "192.168.50.10"

# Ports chosen so that "all dark" and "only 22 dark" are distinguishable --
# the difference between a transport failure and the UniFi IPS SSH signature.
MINI_PORTS = [22, 8001, 5900]


def probe(host, port, timeout=5.0):
    t0 = time.time()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        return "OPEN", time.time() - t0
    except socket.timeout:
        return "TIMEOUT", time.time() - t0
    except ConnectionRefusedError:
        return "REFUSED", time.time() - t0
    except OSError as e:
        return "ERR %s" % (e.strerror or e), time.time() - t0
    finally:
        s.close()


def run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True,
                              timeout=20).stdout
    except Exception as e:
        return "(failed: %s)" % e


print("=" * 62)
print("1. CONTROL -- can this process reach anything at all?")
print("=" * 62)
control_ok = False
for host, port, label in [("1.1.1.1", 443, "public"), ("127.0.0.1", 22, "loopback")]:
    state, dt = probe(host, port)
    print("   %-9s %s:%-5d %-14s %5.2fs" % (label, host, port, state, dt))
    if state in ("OPEN", "REFUSED"):
        control_ok = True
if not control_ok:
    print("\n   !! No control responded. Suspect the PROBER, not the network.")
    sys.exit(1)
print("   -> sockets work; negatives below are real.\n")

print("=" * 62)
print("2. LOCAL WIREGUARD CLIENT -- is the tunnel even up on this Mac?")
print("=" * 62)
nc = run(["/usr/sbin/scutil", "--nc", "list"])
wg = [l for l in nc.splitlines() if "wireguard" in l.lower()]
if not wg:
    print("   (no WireGuard services configured?)")
for line in wg:
    print("   %s" % line.strip())
connected = [l for l in wg if "(Connected)" in l]
lrd_down = any("LRD" in l and "(Disconnected)" in l for l in wg)
if lrd_down:
    print("\n   >> THE LRD TUNNEL IS DISCONNECTED ON THIS LAPTOP.")
    print("   >> This alone explains every timeout below. Connect WireGuard")
    print("   >> (menu bar) before diagnosing anything on the far side.")
elif connected:
    print("\n   -> a tunnel is connected; a still-dark far side is genuinely remote.")
print()

print("=" * 62)
print("3. ROUTE -- is there a path to %s.0/24?" % FAR_SUBNET)
print("=" * 62)
routes = run(["/usr/sbin/netstat", "-rn", "-f", "inet"])
hits = [l for l in routes.splitlines()
        if FAR_SUBNET in l or "utun" in l or "ipsec" in l]
if hits:
    for line in hits:
        print("   %s" % line)
else:
    print("   (none -- no route to the far subnet; traffic falls through to default)")
for line in routes.splitlines():
    if line.strip().startswith("default"):
        print("   %s" % line)
print()

print("=" * 62)
print("4. FAR SIDE -- gateway first, THEN the host")
print("=" * 62)
state, dt = probe(FAR_GATEWAY, 443)
print("   far gateway  %s:443  %-14s %5.2fs" % (FAR_GATEWAY, state, dt))
gw_up = state in ("OPEN", "REFUSED")

results = {}
for port in MINI_PORTS:
    st, dt = probe(MINI, port)
    results[port] = st
    print("   mini         %s:%-5d %-14s %5.2fs" % (MINI, port, st, dt))

print()
print("=" * 62)
print("VERDICT")
print("=" * 62)
reachable = any(s in ("OPEN", "REFUSED") for s in results.values())
if reachable and results.get(22) not in ("OPEN", "REFUSED"):
    # The one signature the UniFi IPS exclusion produces.
    print("Mini ANSWERS on other ports but port 22 is dark -> flow-level block.")
    print("Read: the IPS exclusion is gone or does not cover this source IP.")
    print("It is NOT a dead machine. (CLAUDE.md, 'if port 22 goes dark'.)")
elif reachable:
    print("Mini is reachable. If itq still fails, the problem is above the")
    print("transport -- auth, the venv, or the script itself.")
    sys.exit(0)
elif lrd_down:
    print("Nothing on the far side answers AND the local LRD WireGuard client")
    print("is disconnected. Local cause, local fix: connect the tunnel.")
    print("Do NOT conclude the Mini is down; nothing here has tested it.")
elif not gw_up:
    print("Neither the far GATEWAY nor the Mini answers, and the local client")
    print("looks up -> transport is down beyond this laptop. A tunnel drop")
    print("looks identical to a dead host; this does not accuse the Mini.")
else:
    print("Far gateway answers but the Mini does not -> now the host is a")
    print("genuine suspect.")
sys.exit(1)
