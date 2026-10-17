"""Repoint the QL810W CUPS queue on the Mini at the printer's LRD address.

2026-10-17. Scott moved the QL-810W to LRD, IoT VLAN, 192.168.11.161.
probe_ql810w_lrd_1017.py showed the Mini (Servers) reaches it on 631 and the
printer reports idle / reasons none / roll_current_62x0mm.

Only the device URI changes: `lpadmin -v` keeps the queue name, the generated
PPD and the MediaType/CutMedia/quality defaults, so the cups_label plugin and
every template carry over. Recreating with -m everywhere was rejected — it
would throw those queue defaults away (LABELLING.md: InvenTree knows none of
them). Prints nothing.
"""
import subprocess

URI = "ipp://192.168.11.161/ipp/print"


def sh(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=40)
    print(f"$ {cmd}\n{(r.stdout + r.stderr).strip()}\nrc={r.returncode}\n")


sh("lpoptions -p QL810W | tr ' ' '\\n' | grep -E 'MediaType|CutMedia|cupsPrintQuality|PageSize'")
sh(f"lpadmin -p QL810W -v {URI}")
sh("lpstat -v QL810W")
sh("lpstat -p QL810W")
sh("lpoptions -p QL810W | tr ' ' '\\n' | grep -E 'printer-state|MediaType|CutMedia|cupsPrintQuality|PageSize|device-uri'")
