"""Attach FSD's own parts lists - the actual BOMs - to the PCB parts.

The G1000 PDF already archived on #1153 is ASSEMBLY INSTRUCTIONS. Its page 1
says so: "For Parts list ... refer to the Parts list located on the Project
resource page at FlightSimDIY.com." So the archive held a document that pointed
at a web page, and the quantities were never actually ours.

Both lists turned out to be PUBLIC downloads on flightsimdiy.com/fsd-downloads/
- no account, no entitlement, no support ticket. Including the GMA1347's, which
is the one docs/G1000.md records as lost when FSD removed the entitlement.

Archived here rather than bookmarked for the reason this project already
learned once: a link that says "Expires: Never" is a promise about the
entitlement, not about the URL.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.core.files import File
from common.models import Attachment

COMMIT = "--commit" in sys.argv
JOBS = [
    (1153, "/tmp/FSD-G1000-Parts-List.pdf", "FSD_G1000_v2_PARTS_LIST.pdf",
     "FSD G1000 v2 PARTS LIST - the actual BOM, pulled 2026-09-21 from the "
     "PUBLIC downloads page (no account needed). The instructions PDF is not "
     "a parts list and says so on page 1. Confirms 12x150R + 2x300R + 1x450R "
     "and adds 5x 10k, a MOSFET RFP30N06LE and the 10.4in LCD."),
    (1156, "/tmp/FSD-GMA1347-Parts-List.pdf", "FSD_GMA1347_PARTS_LIST.pdf",
     "FSD GMA1347 PARTS LIST, pulled 2026-09-21 from the PUBLIC downloads "
     "page. This is the BOM docs/G1000.md recorded as LOST when FSD removed "
     "the $8.99 entitlement from the account - it was free on the website all "
     "along. 22 tactiles, 21 rectangular LEDs, 28x150R, 1 MEGA, 1 encoder."),
]

for pk, src, name, comment in JOBS:
    dup = Attachment.objects.filter(model_type="part", model_id=pk,
                                    attachment__endswith=name)
    print("#%s <- %s   already present: %s" % (pk, name, dup.count()))
    print("     %s" % comment[:100])

if not COMMIT:
    print("\nDRY RUN - add --commit")
    sys.exit()

for pk, src, name, comment in JOBS:
    if Attachment.objects.filter(model_type="part", model_id=pk,
                                 attachment__endswith=name).exists():
        print("#%s skip, already attached" % pk)
        continue
    with open(src, "rb") as fh:
        a = Attachment(model_type="part", model_id=pk, comment=comment)
        a.attachment.save(name, File(fh), save=True)

print("\n=== re-read ===")
for pk, src, name, comment in JOBS:
    ats = Attachment.objects.filter(model_type="part", model_id=pk)
    print("#%s now has %d attachments:" % (pk, ats.count()))
    for a in ats:
        print("    %s" % a.attachment)
