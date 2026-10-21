"""Step 1 of 1.5.5 -> 1.5.8: rollback point outside the source tree. No service is touched."""
import subprocess, os, time, sys
ROOT="/Volumes/4TB_Removable/inventree"; HOME=os.path.expanduser("~")
STAMP=time.strftime("%Y%m%d_%H%M"); RB=f"{ROOT}/backups/pre-1.5.8_{STAMP}"
def sh(c, cwd=f"{ROOT}/src", check=True):
    r=subprocess.run(c,shell=True,capture_output=True,text=True,cwd=cwd)
    out=(r.stdout+r.stderr).strip()
    if check and r.returncode: print("FAILED:", c, "\n", out); sys.exit(1)
    return out
os.makedirs(RB, exist_ok=True)
print("rollback dir:", RB)
print("HEAD:", sh("git rev-parse HEAD"), sh("git describe --tags"))
sh(f"git rev-parse HEAD > {RB}/HEAD.txt; git describe --tags >> {RB}/HEAD.txt")
sh(f"git diff -- src/backend/InvenTree/InvenTree/urls.py > {RB}/media_patch.diff")
print("patch bytes:", os.path.getsize(f"{RB}/media_patch.diff"))
print("sqlite backup:", sh(f"sqlite3 {ROOT}/data/inventree.sqlite3 \".backup {RB}/inventree.sqlite3\""), os.path.getsize(f"{RB}/inventree.sqlite3"))
print("integrity:", sh(f"sqlite3 {RB}/inventree.sqlite3 'PRAGMA integrity_check;'"))
print("tables:", sh(f"sqlite3 {RB}/inventree.sqlite3 'select count(*) from part_part; select count(*) from stock_stockitem;'").replace("\n"," parts / ")+" stock rows")
sh(f"tar czf {RB}/plugins.tgz -C {ROOT}/src/src/backend/InvenTree plugins")
sh(f"cp {ROOT}/config.yaml {RB}/config.yaml")
print("rollback contents:", sh(f"ls -la {RB}"))
print("\nplists:", sh(f"ls {HOME}/Library/LaunchAgents | grep -i inventree", cwd=HOME))
print("plist cmd:", sh(f"grep -A6 ProgramArguments {HOME}/Library/LaunchAgents/com.inventree.server.plist | grep string", cwd=HOME, check=False))
print("\nrequirements diff 1.5.5..1.5.8:"); print(sh("git diff 1.5.5 1.5.8 -- src/backend/requirements.txt | grep '^[-+][^-+]' | grep -v hash | grep -v '^[-+] *#' | grep -v '^[-+] *$' || echo '(none)'", check=False))
print("files changed 1.5.5..1.5.8:", sh("git diff --stat 1.5.5 1.5.8 | tail -1"))
print("pip:", sh(f"{ROOT}/env/bin/python3 -m pip --version", check=False))
print("release asset check:", sh("curl -s -o /dev/null -w '%{http_code}' -m 20 -I -L https://github.com/inventree/InvenTree/releases/download/1.5.8/frontend-build.zip", check=False))
