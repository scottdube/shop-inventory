"""1.5.8 -> 1.6.1 on the Mini. Services are ALWAYS re-bootstrapped in finally.
Differs from upgrade_158_2: requirements DO change (uv pip install, never sync, so the
brother plugin package survives), and the notes migration common.0051 runs inside migrate.
Run: itq run scripts/upgrade_16x_2_switch.py"""
import subprocess, os, sys, time, hashlib, urllib.request, urllib.error, glob
ROOT="/Volumes/4TB_Removable/inventree"; HOME=os.path.expanduser("~"); TAG="1.6.1"
SRC=f"{ROOT}/src"; BE=f"{SRC}/src/backend/InvenTree"; VENV=f"{ROOT}/env/bin"
RB=sorted(glob.glob(f"{ROOT}/backups/pre-1.6.1_*"))[-1]
UID=os.getuid(); LA=f"{HOME}/Library/LaunchAgents"
ENV=dict(os.environ, PATH=f"{VENV}:"+os.environ["PATH"], INVENTREE_CONFIG_FILE=f"{ROOT}/config.yaml", VIRTUAL_ENV=f"{ROOT}/env")
def sh(c, cwd=SRC, check=True, quiet=False):
    r=subprocess.run(c,shell=True,capture_output=True,text=True,cwd=cwd,env=ENV)
    out=(r.stdout+r.stderr).strip()
    if check and r.returncode: raise RuntimeError(f"FAILED ({r.returncode}): {c}\n{out[-3000:]}")
    if not quiet: print(f"$ {c}\n{out[-1500:]}" if out else f"$ {c}")
    return out
def http(path):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:8001{path}", timeout=5) as r: return r.status, r.read()
    except urllib.error.HTTPError as e: return e.code, b""
    except Exception as e: return None, str(e).encode()
def md5(p): return hashlib.md5(open(p,"rb").read()).hexdigest()
print("rollback point:", RB); assert os.path.exists(f"{RB}/inventree.sqlite3") and os.path.exists(f"{RB}/notes_before.json"), "run step 1 first"
idx=f"{BE}/web/static/web/index.html"; print("frontend index md5 before:", md5(idx) if os.path.exists(idx) else "missing")
ok=False; t0=time.time()
try:
    for l in ("com.inventree.worker","com.inventree.server"):
        sh(f"launchctl bootout gui/{UID}/{l}", check=False)
    time.sleep(3)
    print("port 8001 after bootout:", http("/api/")[0])
    sh("git checkout -- src/backend/InvenTree/InvenTree/urls.py")
    tracked=sh("git status --short | grep -v '^??' || true", quiet=True)
    if tracked: raise RuntimeError("tracked changes remain before checkout:\n"+tracked)
    sh(f"git checkout {TAG}")
    assert sh("git describe --tags", quiet=True)==TAG
    sh(f"/opt/homebrew/bin/uv pip install --python {VENV}/python -r src/backend/requirements.txt 2>&1 | tail -3")
    sh(f"{VENV}/python -c 'import inventree_brother, django; print(\"brother ok, django\", django.__version__)'")
    tm=time.time(); sh(f"{VENV}/python3 manage.py migrate --noinput 2>&1 | tail -6", cwd=BE); print(f"migrate took {time.time()-tm:.0f}s")
    sh(f"{VENV}/invoke frontend-download --tag {TAG} 2>&1 | tail -6")
    print("frontend index md5 after:", md5(idx))
    sh(f"{VENV}/python3 manage.py collectstatic --noinput 2>&1 | tail -2", cwd=BE)
    sh(f"git apply {RB}/media_patch.diff")
    sh("git diff --stat -- src/backend/InvenTree/InvenTree/urls.py")
    ok=True
finally:
    for l in ("com.inventree.server","com.inventree.worker"):
        sh(f"launchctl bootstrap gui/{UID} {LA}/{l}.plist", check=False)
    for i in range(60):
        st,_=http("/api/")
        if st: break
        time.sleep(2)
    print(f"server up after ~{i*2}s: /api/ -> {st}; downtime {time.time()-t0:.0f}s")
print("STEP RESULT:", "OK" if ok else "FAILED - services restarted on whatever tree is checked out")
print("tag now:", sh("git describe --tags", quiet=True))
st,body=http("/api/"); print("/api/ ->", st, body[:200])
print("anonymous /media/x ->", http("/media/part_images/x.png")[0], "(401 = patch live, 404 = patch missing)")
st,body=http("/web/"); print("/web/ ->", st, len(body), "bytes")
import re
assets=re.findall(rb'/static/web/assets/([^"\']+)', body)[:2]; print("assets referenced:", assets)
for a in assets:
    on_disk=f"{ROOT}/data/static/web/assets/{a.decode()}"
    s,b=http(f"/static/web/assets/{a.decode()}")
    print(" ", a.decode()[:40], "served", s, len(b), "disk", os.path.getsize(on_disk) if os.path.exists(on_disk) else "MISSING", "md5 match" if os.path.exists(on_disk) and hashlib.md5(b).hexdigest()==md5(on_disk) else "MISMATCH")
print("services:", sh(f"launchctl print gui/{UID} | grep -E 'com.inventree.(server|worker)'", check=False, quiet=True))
chk = r'''
import django,os; django.setup()
from plugin.registry import registry; from plugin.models import PluginConfig
from InvenTree.version import inventreeVersion
print("django-side version:", inventreeVersion())
for c in PluginConfig.objects.filter(active=True).order_by("key"):
    p=registry.get_plugin(c.key); print(f"  {c.key:28s} active loaded={'yes' if p else 'NO'}")
from common.models import Note; print("Note rows:", Note.objects.count())
'''
open("/tmp/itq_plugcheck.py","w").write(chk)
sh(f"{VENV}/python3 /tmp/itq_plugcheck.py 2>&1 | grep -v -E 'INVE-W|WARNING|warnings.warn|RuntimeWarning'", cwd=BE, check=False)
