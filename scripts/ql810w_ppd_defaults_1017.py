"""Read-only: show the QL810W queue's PPD defaults (the starred value) for roll/cut/quality."""
import subprocess
r = subprocess.run("lpoptions -p QL810W -l | grep -iE 'MediaType|CutMedia|cupsPrintQuality|PageSize' | cut -c1-200",
                   shell=True, capture_output=True, text=True)
print(r.stdout + r.stderr)
