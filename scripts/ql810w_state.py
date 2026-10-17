"""Read-only: QL810W before/after check from LABELLING.md "Did it actually print?".

Queue state, anything pending, the printer's own IPP state, and the newest
completed jobs (newest FIRST — head, never tail)."""
import subprocess


def sh(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=40)
    print(f"$ {cmd}\n{(r.stdout + r.stderr).strip()}\n")


sh("lpstat -p QL810W")
sh("lpstat -o QL810W; echo pending_rc=$?")
sh("lpoptions -p QL810W | tr ' ' '\\n' | grep -E 'printer-state=|printer-state-reasons'")
sh("ipptool -T 10 -tv \"$(lpstat -v QL810W | sed 's/.*: //')\" get-printer-attributes.test "
   "| grep -E 'printer-state |printer-state-reasons|media-ready'")
sh("lpstat -W completed -o QL810W | head -3")
