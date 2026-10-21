"""Read-only: post-upgrade verification for 1.6.1 (plugins, UI features, media, static, AND the
notes migration against step 1's text snapshot). Run: itq run scripts/upgrade_16x_3_verify.py"""
import os, sys, hashlib, urllib.request, urllib.error, re, json, glob, collections
sys.path.insert(0, os.getcwd()); os.environ.setdefault("DJANGO_SETTINGS_MODULE","InvenTree.settings")
import django; django.setup()
from django.apps import apps
from django.test import Client
from django.contrib.auth import get_user_model
from django.db.models import Count
from plugin.registry import registry; from plugin.models import PluginConfig
from InvenTree.version import inventreeVersion
from common.models import InvenTreeSetting, Note
from part.models import Part; from stock.models import StockItem
from plugins.notes_compat import is_v16, note_text, filter_notes
ROOT="/Volumes/4TB_Removable/inventree"; HOST="192.168.50.10:8001"
RB=sorted(glob.glob(f"{ROOT}/backups/pre-1.6.1_*"))[-1]
FAIL=[]
def check(name, cond, detail=""):
    print(("  ok   " if cond else "  FAIL ")+name, detail); 
    if not cond: FAIL.append(name)
print("version:", inventreeVersion(), "| is_v16:", is_v16(), "| rollback point:", RB)
check("version is 1.6.1", inventreeVersion().startswith("1.6.1"))
for c in PluginConfig.objects.filter(active=True).order_by("key"):
    p=registry.get_plugin(c.key); check(f"plugin {c.key} loaded", bool(p))
check("registry errors empty", not registry.errors, dict(registry.errors) if registry.errors else "")
print("ENABLE_PLUGINS_INTERFACE:", InvenTreeSetting.get_setting("ENABLE_PLUGINS_INTERFACE"))
u=get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
c=Client(HTTP_HOST=HOST); c.force_login(u)
r=c.get("/api/plugins/ui/features/dashboard/"); items=r.json() if r.status_code==200 else []
check("dashboard features", r.status_code==200 and any(i.get("plugin_name")=="shopstatus" for i in items), f"{r.status_code} {len(items)}")
for i in items:
    if i.get("plugin_name")=="shopstatus":
        ctx=i.get("context") or {}; print("    dash", i.get("key"), json.dumps({k:(v if not isinstance(v,(dict,list)) else "...") for k,v in ctx.items()})[:300])
p=Part.objects.filter(pk=519).first() or Part.objects.first()
r=c.get(f"/api/plugins/ui/features/panel/?target_model=part&target_id={p.pk}"); items=r.json() if r.status_code==200 else []
check("part panel", r.status_code==200 and any(i.get("plugin_name")=="shopstatus" for i in items), f"{r.status_code} {len(items)}")
pi=Part.objects.exclude(image="").exclude(image=None).first()
r=c.get(f"/media/{pi.image}"); check("logged-in media served", r.status_code==200, f"{pi.image} {r.status_code}")
r=c.get("/api/stock/?limit=1"); check("api stock", r.status_code==200, r.json().get("count") if r.status_code==200 else r.status_code)
check("stock serializer has no notes field (1.6)", r.status_code==200 and "notes" not in (r.json().get("results") or [{}])[0])
r=c.get("/api/label/template/?limit=50"); check("label templates", r.status_code==200, r.json().get("count") if r.status_code==200 else r.content[:100])
r=c.get("/api/note/?limit=1"); check("note API", r.status_code==200, r.json().get("count") if r.status_code==200 else r.status_code)
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
# ---- notes migration vs snapshot
snap=json.load(open(f"{RB}/notes_before.json")); counts=json.load(open(f"{RB}/notes_counts.json"))
print("\nnotes migration vs", RB)
dup=Note.objects.filter(primary=True).values("model_type","model_id").annotate(n=Count("pk")).filter(n__gt=1).count()
check("one primary note per object", dup==0, f"{dup} objects with >1 primary")
COUNTED=re.compile(r"binscan (\d{4}-\d\d-\d\d): filed into \S+ and COUNTED at ([\d.]+) by hand", re.I)
LEAD=re.compile(r"^(?:\[ESTIMATE\]\s*)?binscan \d{4}-\d\d-\d\d:[^\n]*\n*")
def f_purchase(notes):
    cols,best=None,None
    for line in notes.splitlines():
        line=line.strip()
        if not line.startswith('|'): continue
        cells=[x.strip() for x in line.strip('|').split('|')]; low=[x.lower() for x in cells]
        if cols is None:
            if 'date' in low: cols={n: low.index(n) for n in ('date','qty','unit') if n in low}
            continue
        if set(''.join(cells)) <= set('-: '): continue
        when=cells[cols['date']] if cols.get('date') is not None and cols['date']<len(cells) else ''
        if re.match(r'^\d{4}-\d{2}-\d{2}$', when): best=(best or [])+[when]
    return tuple(best) if best else None
CHECKS={"estimate prefix": lambda t: t.startswith("[ESTIMATE]"),
        "COUNTED regex": lambda t: (COUNTED.search(t).groups() if COUNTED.search(t) else None),
        "TOOL prefix": lambda t: t.startswith("TOOL"),
        "RECEIVED lines": lambda t: sorted(set(re.findall(r"RECEIVED [\d.]+ on \d{4}-\d\d-\d\d from \S+", t))),
        "CONSUMED BY lines": lambda t: [l.split("CONSUMED BY:",1)[1].strip() for l in t.splitlines() if "CONSUMED BY:" in l],
        "binscan lead": lambda t: (LEAD.match(t).group(0).strip()[:60] if LEAD.match(t) else None),
        "purchase table dates": f_purchase}
def words(t): return re.findall(r"[A-Za-z0-9$.:/-]+", t.lower())
tot=exact=same=missing=0; mism=collections.defaultdict(list)
for label, rows in snap.items():
    M=apps.get_model(label)
    ct_notes=Note.objects.filter(primary=True, model_type__app_label=label.split(".")[0], model_type__model=label.split(".")[1]).count()
    check(f"{label}: Note rows {ct_notes} == legacy non-empty {counts[label]}", ct_notes==counts[label])
    objs=M.objects.in_bulk([int(k) for k in rows])
    for pk, old in rows.items():
        o=objs.get(int(pk))
        if o is None: missing+=1; continue
        tot+=1; new=note_text(o)
        exact+= new==old.strip(); same+= words(new)==words(old)
        for name,f in CHECKS.items():
            if f(old)!=f(new): mism[name].append((label,pk,old[:100],new[:100]))
check("no snapshot object missing", missing==0, f"{missing} missing of {tot}")
print(f"  text: {tot} notes, {exact} byte-identical, {same} same word sequence")
for name in CHECKS:
    check(f"marker survives: {name}", not mism[name], f"{len(mism[name])} mismatches" + (f" e.g. {mism[name][0]}" if mism[name] else ""))
exp=lambda label,f: sum(1 for t in snap[label].values() if f(t))
print("\nfilter_notes counts (expected from the snapshot):")
for name, qs, kw, label, f in [
    ("[ESTIMATE] stock", StockItem.objects.all(), dict(prefix="[ESTIMATE]"), "stock.stockitem", lambda t: t.lower().startswith("[estimate]")),
    ("COUNTED at stock", StockItem.objects.all(), dict(contains="COUNTED at"), "stock.stockitem", lambda t: "counted at" in t.lower()),
    ("TOOL stock", StockItem.objects.all(), dict(prefix="TOOL"), "stock.stockitem", lambda t: t.lower().startswith("tool")),
    ("RECEIVED stock", StockItem.objects.all(), dict(contains="RECEIVED"), "stock.stockitem", lambda t: "received" in t.lower()),
    ("Purchase history parts", Part.objects.all(), dict(contains="Purchase history"), "part.part", lambda t: "purchase history" in t.lower()),
    ("nonempty stock", StockItem.objects.all(), dict(nonempty=True), "stock.stockitem", lambda t: True),
    ("nonempty parts", Part.objects.all(), dict(nonempty=True), "part.part", lambda t: True)]:
    got=filter_notes(qs, **kw).count(); want=exp(label,f); check(f"{name}: {got} == {want}", got==want)
sp=registry.get_plugin("shopstatus")
parts=filter_notes(Part.objects.all(), contains="Purchase history").order_by("pk")
res={str(x.pk): sp._parse_notes_history(x) for x in parts}
fp=hashlib.md5(json.dumps(res, sort_keys=True).encode()).hexdigest()
print(f"  purchase parse: {len(res)} parts, {sum(1 for v in res.values() if v)} parsed, fingerprint {fp}")
check("purchase parse fingerprint unchanged", fp=="0965ee953e3bceeffef13a1d85d00584", "(value measured on live 1.5.8 and scratch 1.6.1, 2026-10-21; moves whenever a purchase table is edited)")
print("\nVERDICT:", "SUCCESS - all checks pass" if not FAIL else f"FAILED - {len(FAIL)} check(s): {FAIL}")
