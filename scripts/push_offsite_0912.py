import subprocess, os
STAGED = os.path.expanduser("~/.inventree/backup_work/inventree_2026-09-12_0317.tar.gz")
LOG = os.path.expanduser("~/Library/Logs/inventree/manual_offsite_0912.log")
assert os.path.isfile(STAGED), f"missing {STAGED}"
print(f"staged: {STAGED}  {os.path.getsize(STAGED)/1e6:.1f} MB")

# detach so this returns immediately; rclone's own retries handle flaky upstream
cmd = (f"nohup /opt/homebrew/bin/rclone copy {STAGED} gdrive:InvenTreeBackups/ "
       f"--retries 5 --low-level-retries 20 --stats 60s --stats-one-line "
       f"> {LOG} 2>&1 &")
subprocess.run(["/bin/zsh", "-c", cmd], check=True)
print(f"launched detached; log -> {LOG}")
print(subprocess.run(["/bin/zsh","-c","sleep 3; pgrep -fl 'rclone copy' | head -3"],
                     capture_output=True, text=True).stdout.strip() or "(no rclone process seen yet)")
