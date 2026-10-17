"""Read-only: can the Mini reach the QL-810W now on the LRD IoT VLAN (192.168.11.161)?

2026-10-17. Scott moved the label printer to LRD. The queue QL810W is IP-bound
(TRAPS.md "Swapping the label printer..."), so the change is one lpadmin -v
IF the Mini (Servers VLAN) can open IPP to IoT. IoT -> Servers is Block All;
Servers -> IoT is the open question. Changes nothing.
"""
import subprocess

IP = "192.168.11.161"


def sh(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=40)
    print(f"$ {cmd}\n{(r.stdout + r.stderr).strip()}\n")


sh("lpstat -v")
sh("lpstat -p QL810W")
sh(f"ping -c 3 -t 5 {IP}")
sh(f"nc -z -G 5 {IP} 631; echo nc631=$?")
sh(f"nc -z -G 5 {IP} 80; echo nc80=$?")
sh(f"ipptool -T 10 -tv ipp://{IP}/ipp/print get-printer-attributes.test "
   "| grep -E 'printer-state|printer-make|printer-name|media-ready|printer-uuid|status-code' | head -20")
