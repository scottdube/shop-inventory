import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from common.models import Attachment
from part.models import Part
for pk in (1152, 1153, 1154, 1155, 1137, 1255):
    p = Part.objects.get(pk=pk)
    ats = Attachment.objects.filter(model_type="part", model_id=pk)
    print("#%-5s %-44s attachments=%d" % (pk, p.name[:44], ats.count()))
    for a in ats:
        print("      %-60s %s" % (str(a.attachment or a.link)[:60], a.comment[:60]))
