"""Create a label template record in InvenTree from a repo HTML file.

    itq push labels/tooltag_62x38.html /tmp/tooltag_62x38.html
    itq run scripts/new_label_tpl.py /tmp/tooltag_62x38.html "Shop Tool Tag 62x38mm (QR + T number)" stockitem 62 38 "description..."

Templates 9-14 were made in the UI; this is the scripted route so a template's
source, size and description are in git and the create is repeatable. Refuses to
create a second template with the same name (install_label_tpl.py updates an
existing one in place). Re-reads the stored file to prove the write landed.
"""
import os, sys, django
sys.path.insert(0, os.getcwd()); os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings"); django.setup()
from django.core.files.base import ContentFile
from report.models import LabelTemplate
src, name, model, w, h = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]), float(sys.argv[5])
desc = sys.argv[6] if len(sys.argv) > 6 else ""
if LabelTemplate.objects.filter(name=name).exists():
    t = LabelTemplate.objects.get(name=name)
    sys.exit(f"template {t.pk} {name!r} already exists -- use install_label_tpl.py {t.pk} {src} to update it")
data = open(src, "rb").read()
t = LabelTemplate(name=name, description=desc, model_type=model, width=w, height=h, enabled=True,
                  filename_pattern="output.pdf")
t.template.save(os.path.basename(src), ContentFile(data), save=False)
t.save()
t = LabelTemplate.objects.get(pk=t.pk)
assert t.template and open(t.template.path, "rb").read() == data, "template file did not land"
assert (t.width, t.height, t.model_type, t.enabled) == (w, h, model, True), "fields did not land"
print(f"OK template {t.pk} {t.name!r} model={t.model_type} {t.width}x{t.height}mm file={t.template.name} ({len(data)} bytes)")
