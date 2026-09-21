"""Attach FSD's X-PLANE MobiFlight configs.

docs/G1000.md records Peter Eier's shield as "only tested in combination with
MSFS and MobiFlight !!" - his emphasis - and Scott's sim is X-Plane. These are
a DIFFERENT thing and the distinction matters: they are FSD's configs for
FSD's own control board, not Peter's for Peter's shield. They do not overturn
Peter's warning; they are a second source to adapt from.

The G1000 zip ships SEPARATE MFD and PFD configs (FSD_G1000_MFD.mfmc /
FSD_G1000_PFD.mfmc, XP-MFD.mcc / XP-PFD.mcc), which is independent evidence
that the two panels are distinct configurations, not one build twice.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.core.files import File
from common.models import Attachment

COMMIT = "--commit" in sys.argv
JOBS = [
    (1153, "/tmp/XPLANE-G1000-MF-Config.zip", "FSD_XPLANE_G1000_MF_Config.zip",
     "FSD X-PLANE MobiFlight configs for the G1000, public download, pulled "
     "2026-09-21. Contains SEPARATE MFD and PFD configs: FSD_G1000_MFD.mfmc, "
     "FSD_G1000_PFD.mfmc, XP-MFD.mcc, XP-PFD.mcc. NOTE these are for FSD's "
     "OWN control board - Peter Eier's shield (#1152) is documented as tested "
     "only with MSFS, so treat these as a source to adapt, not a drop-in."),
    (1156, "/tmp/XPLANE-GMA1347-MF-Config.zip", "FSD_XPLANE_GMA1347_MF_Config.zip",
     "FSD X-PLANE MobiFlight config for the GMA1347, public download, pulled "
     "2026-09-21. GMA1347.mcc + FSD_GMA1347.mfmc. Same caveat: FSD's control "
     "board, not Peter's shield."),
]
for pk, src, name, c in JOBS:
    print("#%s <- %s  present already: %d" % (
        pk, name, Attachment.objects.filter(
            model_type="part", model_id=pk, attachment__endswith=name).count()))
if not COMMIT:
    print("\nDRY RUN - add --commit"); sys.exit()
for pk, src, name, c in JOBS:
    if Attachment.objects.filter(model_type="part", model_id=pk,
                                 attachment__endswith=name).exists():
        print("#%s skip" % pk); continue
    with open(src, "rb") as fh:
        a = Attachment(model_type="part", model_id=pk, comment=c)
        a.attachment.save(name, File(fh), save=True)
print("\n=== re-read ===")
for pk, src, name, c in JOBS:
    ok = Attachment.objects.filter(model_type="part", model_id=pk,
                                   attachment__endswith=name).exists()
    print("#%s %s -> %s" % (pk, name, "OK" if ok else "MISSING"))
