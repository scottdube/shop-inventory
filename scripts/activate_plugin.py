"""Activate a PluginConfig by key and prove the registry sees it.
Usage: itq run scripts/activate_plugin.py receiving"""
import os, sys
import django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from plugin.models import PluginConfig  # noqa: E402
from plugin.registry import registry  # noqa: E402

key = sys.argv[1]
cfg = PluginConfig.objects.filter(key=key).first()
if cfg is None:
    raise SystemExit(f"no PluginConfig {key!r}: the server has not loaded the directory yet "
                     f"(push it, restart, re-run). Known: {sorted(PluginConfig.objects.values_list('key', flat=True))}")
if not cfg.active:
    PluginConfig.objects.filter(pk=cfg.pk).update(active=True)
    cfg.refresh_from_db()
assert cfg.active, "active did not stick"
print(f"PluginConfig {key} active={cfg.active}; registry sees it: {registry.get_plugin(key) is not None}")
print("if registry says False, restart the server again and re-run this to confirm")
