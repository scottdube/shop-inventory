"""Read-only: post-upgrade verification with Django (plugins, UI features, media, static integrity)."""
import os, sys, hashlib, urllib.request, urllib.error, re
sys.path.insert(0, os.getcwd()); os.environ.setdefault("DJANGO_SETTINGS_MODULE","InvenTree.settings")
import django; django.setup()
from django.test import Client
from django.contrib.auth import get_user_model
from plugin.registry import registry; from plugin.models import PluginConfig
from InvenTree.version import inventreeVersion
from common.models import InvenTreeSetting
from part.models import Part
ROOT="/Volumes/4TB_Removable/inventree"; HOST="192.168.50.10:8001"
print("version:", inventreeVersion())
for c in PluginConfig.objects.filter(active=True).order_by("key"):
    p=registry.get_plugin(c.key); print(f"  plugin {c.key:28s} loaded={'yes' if p else 'NO'}")
print("ENABLE_PLUGINS_INTERFACE:", InvenTreeSetting.get_setting("ENABLE_PLUGINS_INTERFACE"))
u=get_user_model().objects.filter(is_superuser=True).order_by("pk").first(); print("test user:", u.username)
c=Client(HTTP_HOST=HOST); c.force_login(u)
r=c.get("/api/plugins/ui/features/dashboard/"); items=r.json() if r.status_code==200 else []
print("dashboard features:", r.status_code, len(items), sorted({i.get("plugin_name") for i in items}))
p=Part.objects.exclude(image="").exclude(image=None).first()
r=c.get(f"/api/plugins/ui/features/panel/?target_model=part&target_id={p.pk}"); items=r.json() if r.status_code==200 else []
print("part panels:", r.status_code, len(items), sorted({i.get("plugin_name") for i in items}))
r=c.get(f"/media/{p.image}"); print(f"logged-in media {p.image}: {r.status_code} {len(b''.join(r.streaming_content)) if r.streaming_content else len(r.content)} bytes")
r=c.get("/api/stock/?limit=1"); print("api stock:", r.status_code, r.json().get("count"))
r=c.get("/api/label/template/?limit=50"); print("label templates:", r.status_code, r.json().get("count") if r.status_code==200 else r.content[:100])
# served static vs disk (the kill -HUP truncation trap)
def http(path):
    try:
        with urllib.request.urlopen(f"http://{HOST}{path}", timeout=8) as r: return r.status, r.read()
    except urllib.error.HTTPError as e: return e.code, e.read()
st,body=http("/web/"); print("/web/ ->", st, len(body))
for a in sorted(set(re.findall(rb'/static/web/assets/([^"\')\s]+)', body)))[:3]:
    a=a.decode(); s,b=http(f"/static/web/assets/{a}"); d=f"{ROOT}/data/static/web/assets/{a}"
    print(f"  asset {a[:45]:45s} served {s} {len(b):>8} disk {os.path.getsize(d) if os.path.exists(d) else 'MISSING':>8}", "md5 match" if os.path.exists(d) and hashlib.md5(b).hexdigest()==hashlib.md5(open(d,'rb').read()).hexdigest() else "MISMATCH")
st,body=http("/api/"); print("api:", body[:160])
