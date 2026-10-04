"""Install a label template's HTML from the repo into InvenTree, keeping a backup.

    itq push labels/travelbag_62mm.html /tmp/travelbag_62mm.html
    itq run scripts/install_label_tpl.py 13 /tmp/travelbag_62mm.html

Overwrites the file behind LabelTemplate.template in place (same stored name,
so nothing that references it moves), after copying the live one to
<path>.bak-<date>. Re-reads the bytes to prove the write landed -- this install
has reported saves that wrote nothing.
"""
import datetime, os, shutil, sys, django
sys.path.insert(0, os.getcwd()); os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings"); django.setup()
from report.models import LabelTemplate
pk, src = int(sys.argv[1]), sys.argv[2]
t = LabelTemplate.objects.get(pk=pk)
dst = t.template.path
new = open(src, "rb").read()
bak = f"{dst}.bak-{datetime.date.today():%Y%m%d}"
if not os.path.exists(bak):
    shutil.copy2(dst, bak)
open(dst, "wb").write(new)
assert open(dst, "rb").read() == new, "template write did not land"
print(f"template {pk} {t.name}: {dst} <- {src} ({len(new)} bytes); backup {bak}")
