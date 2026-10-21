"""Step 1 of 1.5.8 -> 1.6.1: rollback point outside the source tree + a text snapshot of
every note, so step 3 can prove the notes migration (common.0051) lost nothing.
No service is touched. Run: itq run scripts/upgrade_16x_1_rollback_point.py"""
import subprocess, os, time, sys, json
sys.path.insert(0, os.getcwd()); os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
import django; django.setup()
from django.apps import apps
ROOT = "/Volumes/4TB_Removable/inventree"; HOME = os.path.expanduser("~")
STAMP = time.strftime("%Y%m%d_%H%M"); RB = f"{ROOT}/backups/pre-1.6.1_{STAMP}"
NOTED = ["part.part", "stock.stockitem", "order.purchaseorder", "company.company", "build.build",
         "company.manufacturerpart", "company.supplierpart", "order.returnorder",
         "order.salesorder", "order.salesordershipment"]
def sh(c, cwd=f"{ROOT}/src", check=True):
    r = subprocess.run(c, shell=True, capture_output=True, text=True, cwd=cwd)
    out = (r.stdout + r.stderr).strip()
    if check and r.returncode: print("FAILED:", c, "\n", out); sys.exit(1)
    return out
os.makedirs(RB, exist_ok=True)
print("rollback dir:", RB)
print("HEAD:", sh("git rev-parse HEAD"), sh("git describe --tags"))
sh(f"git rev-parse HEAD > {RB}/HEAD.txt; git describe --tags >> {RB}/HEAD.txt")
sh(f"git diff -- src/backend/InvenTree/InvenTree/urls.py > {RB}/media_patch.diff")
print("patch bytes:", os.path.getsize(f"{RB}/media_patch.diff"))
print("patch applies to 1.6.1:", sh(f"git -C {ROOT}/src16 apply --check {RB}/media_patch.diff && echo yes || echo NO", check=False))
print("sqlite backup:", sh(f"sqlite3 {ROOT}/data/inventree.sqlite3 \".backup {RB}/inventree.sqlite3\""), os.path.getsize(f"{RB}/inventree.sqlite3"))
print("integrity:", sh(f"sqlite3 {RB}/inventree.sqlite3 'PRAGMA integrity_check;'"))
print("tables:", sh(f"sqlite3 {RB}/inventree.sqlite3 'select count(*) from part_part; select count(*) from stock_stockitem;'").replace("\n", " parts / ") + " stock rows")
sh(f"tar czf {RB}/plugins.tgz -C {ROOT}/src/src/backend/InvenTree plugins")
sh(f"cp {ROOT}/config.yaml {RB}/config.yaml")
sh(f"cp {HOME}/binscan/app.py {RB}/binscan_app.py")
sh(f"/opt/homebrew/bin/uv pip freeze --python {ROOT}/env/bin/python > {RB}/requirements_before.txt")
print("env freeze lines:", sh(f"wc -l < {RB}/requirements_before.txt"))
# text snapshot of every non-empty note, per model, keyed by pk
snap, counts = {}, {}
for label in NOTED:
    M = apps.get_model(label)
    rows = {str(pk): n for pk, n in M.objects.exclude(notes="").exclude(notes__isnull=True).values_list("pk", "notes")}
    snap[label] = rows; counts[label] = len(rows)
json.dump(snap, open(f"{RB}/notes_before.json", "w"))
json.dump(counts, open(f"{RB}/notes_counts.json", "w"), indent=1)
print("notes snapshot:", sum(counts.values()), "non-empty notes", counts, "->", os.path.getsize(f"{RB}/notes_before.json"), "bytes")
print("rollback contents:", sh(f"ls -la {RB}"))
print("\nrequirements changes 1.5.8..1.6.1 (dry run into the live env):")
print(sh(f"/opt/homebrew/bin/uv pip install --python {ROOT}/env/bin/python --dry-run -r {ROOT}/src16/src/backend/requirements.txt 2>&1 | grep -c '^ [+-] '", check=False), "package changes")
print("brother plugin in env:", sh(f"{ROOT}/env/bin/python -c 'import inventree_brother; print(\"ok\")'", check=False))
print("files changed 1.5.8..1.6.1:", sh("git diff --stat 1.5.8 1.6.1 | tail -1"))
print("release asset check:", sh("curl -s -o /dev/null -w '%{http_code}' -m 20 -I -L https://github.com/inventree/InvenTree/releases/download/1.6.1/frontend-build.zip", check=False))
print("ROLLBACK POINT READY:", RB)
