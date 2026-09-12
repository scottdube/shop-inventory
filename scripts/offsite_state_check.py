import subprocess
def sh(c, t=90):
    try:
        r = subprocess.run(c, shell=True, capture_output=True, text=True, timeout=t, stdin=subprocess.DEVNULL)
        return (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return f"(timed out {t}s)"
print("=== NAS copy still running? ===")
print(sh("pgrep -f 'cp /Users/scottdube/.inventree' >/dev/null && echo YES || echo NO"))
print(sh("cat ~/Library/Logs/inventree/manual_nas_0912.log 2>/dev/null | tail -3") or "(log empty)")
print("\n=== NAS newest 3 ===")
print(sh("ls -lat /Volumes/home/inventree/ 2>&1 | head -4"))
print("\n=== gdrive newest 2 ===")
print(sh("/opt/homebrew/bin/rclone lsl gdrive:InvenTreeBackups/ 2>/dev/null | sort -k2 | tail -2"))
print("\n=== local staged size ===")
print(sh("ls -l ~/.inventree/backup_work/inventree_2026-09-12_0317.tar.gz | awk '{print $5, $9}'"))
