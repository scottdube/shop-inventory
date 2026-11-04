"""Read-only: post-upgrade verification for 1.6.1 -> 1.6.4. Same live checks as
upgrade_16x_3_verify.py (plugins, UI features, media, static, APIs), plus a comparison of
counts, every Note's content hash, the notes filters and the purchase-parse fingerprint
against step 1's fingerprint.json. Run: itq run scripts/upgrade_164_3_verify.py"""
import os, sys, hashlib, urllib.request, urllib.error, re, json, glob
sys.path.insert(0, os.getcwd()); os.environ.setdefault("DJANGO_SETTINGS_MODULE","InvenTree.settings")
import django; django.setup()
from django.apps import apps
from django.test import Client
from django.contrib.auth import get_user_model
from plugin.registry import registry; from plugin.models import PluginConfig
from InvenTree.version import inventreeVersion
from common.models import Note
from part.models import Part; from stock.models import StockItem
from plugins.notes_compat import filter_notes
TAG="1.6.4"; ROOT="/Volumes/4TB_Removable/inventree"; HOST="192.168.50.10:8001"
RB=sorted(glob.glob(f"{ROOT}/backups/pre-{TAG}_*"))[-1]
before=json.load(open(f"{RB}/fingerprint.json"))
FAIL=[]
def check(name, cond, detail=""):
    print(("  ok   " if cond else "  FAIL ")+name, detail)
    if not cond: FAIL.append(name)
print("version:", inventreeVersion(), "| rollback point:", RB)
check(f"version is {TAG}", inventreeVersion().startswith(TAG))
for c in PluginConfig.objects.filter(active=True).order_by("key"):
    check(f"plugin {c.key} loaded", bool(registry.get_plugin(c.key)))
check("registry errors empty", not registry.errors, dict(registry.errors) if registry.errors else "")
u=get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
c=Client(HTTP_HOST=HOST); c.force_login(u)
r=c.get("/api/plugins/ui/features/dashboard/"); items=r.json() if r.status_code==200 else []
check("dashboard features", r.status_code==200 and any(i.get("plugin_name")=="shopstatus" for i in items), f"{r.status_code} {len(items)}")
p=Part.objects.filter(pk=519).first() or Part.objects.first()
r=c.get(f"/api/plugins/ui/features/panel/?target_model=part&target_id={p.pk}"); items=r.json() if r.status_code==200 else []
check("part panel", r.status_code==200 and any(i.get("plugin_name")=="shopstatus" for i in items), f"{r.status_code} {len(items)}")
pi=Part.objects.exclude(image="").exclude(image=None).first()
r=c.get(f"/media/{pi.image}"); check("logged-in media served", r.status_code==200, f"{pi.image} {r.status_code}")
for path in ("/api/stock/?limit=1", "/api/part/?limit=1", "/api/label/template/?limit=50", "/api/note/?limit=1", "/api/order/po/?limit=1"):
    r=c.get(path); check(f"api {path}", r.status_code==200, r.json().get("count") if r.status_code==200 else r.content[:100])
r=c.get(f"/api/part/{p.pk}/"); check("part detail exposes consumable field", r.status_code==200 and "consumable" in r.json())
def http(path):
    try:
        with urllib.request.urlopen(f"http://{HOST}{path}", timeout=8) as r: return r.status, r.read()
    except urllib.error.HTTPError as e: return e.code, e.read()
    except Exception as e: return None, str(e).encode()
st,body=http("/web/"); check("/web/ via site host", st==200, f"{st} {len(body)} bytes")
check("anonymous /media/ blocked", http("/media/part_images/x.png")[0]==401, "(401 = media patch live)")
for a in sorted(set(re.findall(rb'/static/web/assets/([^"\')\s]+)', body)))[:3]:
    a=a.decode(); s,b=http(f"/static/web/assets/{a}"); d=f"{ROOT}/data/static/web/assets/{a}"
    check(f"asset {a[:40]}", s==200 and os.path.exists(d) and hashlib.md5(b).hexdigest()==hashlib.md5(open(d,'rb').read()).hexdigest(), f"served {s} {len(b)}")
st,body=http("/api/"); check("binscan-facing /api/ root", st==200, body[:80])
print("\ndata vs", RB)
for lbl, n in before["counts"].items():
    now=apps.get_model(lbl).objects.count(); check(f"{lbl} count {now} == {n}", now==n)
notes={str(pk): hashlib.md5((c or "").encode()).hexdigest() for pk, c in Note.objects.values_list("pk","content")}
diff=[k for k in set(notes)|set(before["notes"]) if notes.get(k)!=before["notes"].get(k)]
check(f"all {len(before['notes'])} Note contents byte-identical", not diff, f"{len(diff)} differ e.g. {diff[:5]}")
filters={"estimate": filter_notes(StockItem.objects.all(), prefix="[ESTIMATE]").count(),
         "counted": filter_notes(StockItem.objects.all(), contains="COUNTED at").count(),
         "tool": filter_notes(StockItem.objects.all(), prefix="TOOL").count(),
         "received": filter_notes(StockItem.objects.all(), contains="RECEIVED").count(),
         "purchase_parts": filter_notes(Part.objects.all(), contains="Purchase history").count()}
for k, v in before["filters"].items(): check(f"filter {k} {filters[k]} == {v}", filters[k]==v)
sp=registry.get_plugin("shopstatus")
res={str(x.pk): sp._parse_notes_history(x) for x in filter_notes(Part.objects.all(), contains="Purchase history").order_by("pk")}
fp=hashlib.md5(json.dumps(res, sort_keys=True).encode()).hexdigest()
check(f"purchase parse fingerprint {fp[:8]} == {before['purchase_fp'][:8]}", fp==before["purchase_fp"])
print("\nVERDICT:", "SUCCESS - all checks pass" if not FAIL else f"FAILED - {len(FAIL)} check(s): {FAIL}")
