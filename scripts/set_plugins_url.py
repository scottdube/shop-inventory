"""Turn on the GLOBAL setting that lets plugins register URLs. Measured
2026-11-06: ENABLE_PLUGINS_URL is an InvenTreeSetting row, not config.yaml,
and UrlsMixin only mounts its routes when it is True at server start."""
import os, sys
import django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from common.models import InvenTreeSetting  # noqa: E402

before = InvenTreeSetting.get_setting("ENABLE_PLUGINS_URL")
InvenTreeSetting.set_setting("ENABLE_PLUGINS_URL", True, None)
after = InvenTreeSetting.get_setting("ENABLE_PLUGINS_URL")
print(f"ENABLE_PLUGINS_URL {before} -> {after}")
assert after is True, "setting did not stick"
print("restart the server now: launchctl kickstart -k gui/$(id -u)/com.inventree.server")
