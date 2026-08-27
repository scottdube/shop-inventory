"""Did pages actually come out, and is this a DIFFERENT unit than the dead one?

`lpstat -W completed` is not proof: jobs 29-35 'completed' on Aug 24-25 while
the old unit was dead. page_log records pages actually rendered; the IPP
serial/MAC tells us whether the box on the bench is a new one.
"""
import re
import subprocess
import urllib.request

HOST = "192.168.30.252"

print("=== IPP printer-state (live, from the printer itself) ===")
ippt = "/usr/bin/ipptool"
r = subprocess.run(
    [ippt, "-tv", f"ipp://{HOST}/ipp/print", "get-printer-attributes.test"],
    capture_output=True, text=True, cwd="/usr/share/cups/ipptool",
)
out = (r.stdout + r.stderr)
keep = ("printer-state", "printer-state-reasons", "printer-make-and-model",
        "printer-info", "printer-uuid", "printer-device-id", "marker",
        "printer-up-time", "queued-job-count", "printer-alert")
for line in out.splitlines():
    if any(k in line for k in keep):
        print("   " + line.strip())
if not out.strip():
    print("   (ipptool produced nothing)")

print("\n=== web UI identity (serial / firmware) ===")
for path in ("/general/status.html", "/", "/net/net/airprint.html"):
    try:
        with urllib.request.urlopen(f"http://{HOST}{path}", timeout=5) as f:
            body = f.read().decode("utf-8", "replace")
        text = re.sub(r"<[^>]+>", " ", body)
        text = re.sub(r"\s+", " ", text)
        hits = re.findall(
            r"(Serial\s*(?:No\.?|Number)?\s*[:\s]\s*[A-Za-z0-9]+"
            r"|Main Firmware[^|]{0,40}"
            r"|Node Name\s*[:\s]\s*\S+"
            r"|Ethernet Address[^ ]* [0-9a-fA-F:\-]{17})", text)
        print(f"  {path}: {hits if hits else '(no id fields) ' + text[:160]}")
    except Exception as e:
        print(f"  {path}: {type(e).__name__}: {e}")

print("\n=== page_log: pages actually rendered ===")
r = subprocess.run(
    ["grep", "QL810W", "/var/log/cups/page_log"], capture_output=True, text=True)
lines = [l for l in r.stdout.splitlines() if l.strip()]
print(f"  {len(lines)} page_log entries total")
for l in lines[-15:]:
    print("   " + l)
if not lines:
    print("   (page_log empty or unreadable -- may need sudo)")

print("\n=== job states (completed vs aborted vs canceled) ===")
r = subprocess.run(["lpstat", "-l", "-W", "completed", "-o", "QL810W"],
                   capture_output=True, text=True)
txt = (r.stdout + r.stderr)
blocks = re.split(r"\n(?=QL810W-\d+)", txt)
for b in blocks[:12]:
    b = b.strip()
    if not b:
        continue
    first = b.splitlines()[0]
    status = [l.strip() for l in b.splitlines()
              if "Status" in l or "abort" in l.lower() or "cancel" in l.lower()]
    print(f"   {first}")
    for s in status:
        print(f"        {s}")
