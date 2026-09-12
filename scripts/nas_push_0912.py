import subprocess, os
SRC = os.path.expanduser("~/.inventree/backup_work/inventree_2026-09-12_0317.tar.gz")
DST = "/Volumes/home/inventree/"
LOG = os.path.expanduser("~/Library/Logs/inventree/manual_nas_0912.log")
assert os.path.isfile(SRC), SRC
assert os.path.isdir(DST), f"{DST} not mounted"
if os.path.exists(os.path.join(DST, os.path.basename(SRC))):
    print("already on the NAS — nothing to do"); raise SystemExit(0)
# .part then rename, so a truncated copy can never look like a good backup
cmd = (f"nohup /bin/zsh -c 'cp {SRC} {DST}.tmp_0912 && mv {DST}.tmp_0912 "
       f"{DST}inventree_2026-09-12_0317.tar.gz && echo DONE' > {LOG} 2>&1 &")
subprocess.run(["/bin/zsh", "-c", cmd], check=True)
print(f"launched; log -> {LOG}")
print(subprocess.run(["/bin/zsh","-c","sleep 2; pgrep -fl 'cp /Users' | head -2"],
                     capture_output=True, text=True).stdout.strip() or "(cp not seen yet)")
