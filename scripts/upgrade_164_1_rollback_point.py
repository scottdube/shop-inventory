"""Step 1 of 1.6.1 -> 1.6.4: rollback point outside the source tree + a fingerprint of the
data that step 3 compares against. No service is touched.
Patch release on the same line: the 1.6 notes port is already done, so this snapshots
every Note row's content hash rather than legacy note text.
Run: itq run scripts/upgrade_164_1_rollback_point.py"""
import subprocess, os, time, sys, json, hashlib
sys.path.insert(0, os.getcwd()); os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
import django; django.setup()
from django.apps import apps
from InvenTree.version import inventreeVersion
FROM, TAG = "1.6.1", "1.6.4"
ROOT = "/Volumes/4TB_Removable/inventree"; HOME = os.path.expanduser("~")
STAMP = time.strftime("%Y%m%d_%H%M"); RB = f"{ROOT}/backups/pre-{TAG}_{STAMP}"
def sh(c, cwd=f"{ROOT}/src", check=True):
    r = subprocess.run(c, shell=True, capture_output=True, text=True, cwd=cwd)
    out = (r.stdout + r.stderr).strip()
    if check and r.returncode: print("FAILED:", c, "\n", out); sys.exit(1)
    return out
assert inventreeVersion().startswith(FROM), f"running {inventreeVersion()}, expected {FROM}"
os.makedirs(RB, exist_ok=True)
print("rollback dir:", RB)
print("HEAD:", sh("git rev-parse HEAD"), sh("git describe --tags"))
sh(f"git rev-parse HEAD > {RB}/HEAD.txt; git describe --tags >> {RB}/HEAD.txt")
sh(f"git diff -- src/backend/InvenTree/InvenTree/urls.py > {RB}/media_patch.diff")
print("patch bytes:", os.path.getsize(f"{RB}/media_patch.diff"))
print("fetch tags:", sh("git fetch --tags --quiet 2>&1 | tail -2; git tag -l '1.6.*' | tr '\\n' ' '"))
print("urls.py changed upstream 1.6.1..1.6.4 (empty = patch re-applies as is):",
      repr(sh(f"git diff --stat {FROM} {TAG} -- src/backend/InvenTree/InvenTree/urls.py")))
print("migrations added 1.6.1..1.6.4:", sh(f"git diff --name-status {FROM} {TAG} -- '*/migrations/*'") or "NONE")
print("files changed:", sh(f"git diff --stat {FROM} {TAG} | tail -1"))
print("requirements diff:\n", sh(f"git diff {FROM} {TAG} -- src/backend/requirements.txt | grep -E '^[+-][a-zA-Z]'") or "  none")
print("sqlite backup:", sh(f"sqlite3 {ROOT}/data/inventree.sqlite3 \".backup {RB}/inventree.sqlite3\""), os.path.getsize(f"{RB}/inventree.sqlite3"))
print("integrity:", sh(f"sqlite3 {RB}/inventree.sqlite3 'PRAGMA integrity_check;'"))
sh(f"tar czf {RB}/plugins.tgz -C {ROOT}/src/src/backend/InvenTree plugins")
sh(f"cp {ROOT}/config.yaml {RB}/config.yaml")
sh(f"cp {HOME}/binscan/app.py {RB}/binscan_app.py")
sh(f"/opt/homebrew/bin/uv pip freeze --python {ROOT}/env/bin/python > {RB}/requirements_before.txt")
print("env freeze lines:", sh(f"wc -l < {RB}/requirements_before.txt"))
# ---- data fingerprint for step 3
from common.models import Note
from plugins.notes_compat import filter_notes
from part.models import Part; from stock.models import StockItem
from plugin.registry import registry
counts = {lbl: apps.get_model(lbl).objects.count() for lbl in
          ["part.part", "stock.stockitem", "stock.stocklocation", "part.partcategory", "order.purchaseorder",
           "order.purchaseorderlineitem", "company.company", "company.supplierpart", "stock.stockitemtracking",
           "common.note", "common.attachment", "report.labeltemplate"]}
notes = {str(pk): hashlib.md5((c or "").encode()).hexdigest() for pk, c in Note.objects.values_list("pk", "content")}
filters = {"estimate": filter_notes(StockItem.objects.all(), prefix="[ESTIMATE]").count(),
           "counted": filter_notes(StockItem.objects.all(), contains="COUNTED at").count(),
           "tool": filter_notes(StockItem.objects.all(), prefix="TOOL").count(),
           "received": filter_notes(StockItem.objects.all(), contains="RECEIVED").count(),
           "purchase_parts": filter_notes(Part.objects.all(), contains="Purchase history").count()}
sp = registry.get_plugin("shopstatus")
res = {str(x.pk): sp._parse_notes_history(x) for x in filter_notes(Part.objects.all(), contains="Purchase history").order_by("pk")}
fp = hashlib.md5(json.dumps(res, sort_keys=True).encode()).hexdigest()
json.dump({"counts": counts, "notes": notes, "filters": filters, "purchase_fp": fp}, open(f"{RB}/fingerprint.json", "w"))
print("counts:", counts); print("filters:", filters); print("notes hashed:", len(notes), "| purchase fingerprint:", fp)
print("release asset check:", sh(f"curl -s -o /dev/null -w '%{{http_code}}' -m 20 -I -L https://github.com/inventree/InvenTree/releases/download/{TAG}/frontend-build.zip", check=False))
print("rollback contents:\n", sh(f"ls -la {RB}"))
print("ROLLBACK POINT READY:", RB)
