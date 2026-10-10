"""Attach the 16 photos Scott sent on 2026-10-10 (Florida pack + Metrology Bench
drawers) to their records. Files are pushed first to /tmp/ph1010/ on the Mini.

Same rules as photo_push.py, whose attach() this mirrors: drawer overviews go on
the LOCATION; a photo of one item goes on its part and fills Part.image only if
the slot is empty; a photo of several items is an attachment on each and is
never made anyone's primary image -- a group shot as a thumbnail identifies none
of them.

    itq run scripts/photo_batch_1010.py [--commit]
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from common.models import Attachment  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from django.core.files.base import ContentFile  # noqa: E402
from part.models import Part  # noqa: E402
from stock.models import StockLocation  # noqa: E402

COMMIT = "--commit" in sys.argv
DIR = "/tmp/ph1010"
# file stem -> (location names, group-part pks, single-subject part pk or None, comment)
MAP = {
    "9932df40": ([], [1382, 1383, 1352], None, "LRD gauges as photographed 2026-10-10: Fowler 1-2 mic, Federal C81, Starrett 81-111-630"),
    "b55bb149": ([], [1359, 1364, 1385], None, "Metrology bench items 2026-10-10: Last Word set, test bar, sine bar"),
    "89da09fd": ([], [], 1336, "iGaging combination square set, 2026-10-10"),
    "088352cd": ([], [], 1364, "Test bar in wooden case with tape, 2026-10-10"),
    "571d711d": ([], [], 1385, "Sine bar with tape, rolls visible, 2026-10-10"),
    "721439f3": (["MB-D1"], [], None, "MB-D1 as found 2026-10-10"),
    "2c82ffb7": (["MB-D2"], [], None, "MB-D2 as found 2026-10-10"),
    "7ae86810": (["MB-D3"], [], None, "MB-D3 as found 2026-10-10"),
    "67936cc2": (["MB-D4"], [], None, "MB-D4 as found 2026-10-10"),
    "ab5e624f": ([], [], 1394, "Edge Technology Pro Tram, case open, 2026-10-10"),
    "ffeff2fb": ([], [1398, 1399, 1400], None, "Knipex pliers wrenches, handle prints, 2026-10-10"),
    "cdf35454": (["MB-D1"], [1401, 1405, 1402, 461, 1387], None, "MB-D1 close-up 2026-10-10: 25R points, pitch gauges, Mitutoyo standards + spanners, Angle-izer"),
    "90565edf": ([], [1403, 1404], None, "Feeler gauges, case stamps, 2026-10-10"),
    "56490517": ([], [], 1333, "Adjustable parallels pouch open, slot ranges A-F, 2026-10-10"),
    "c73b5134": ([], [], 1346, "Ring gage stamp PRG6344-202-1 GO / MTG #5, 2026-10-10"),
    "4ccc4d45": ([], [], 1406, "PGN 1 in bearing balls, bag label, 2026-10-10"),
}
user = get_user_model().objects.filter(is_superuser=True).first()


def attach(mt, mid, path, comment):
    data = open(path, "rb").read()
    if Attachment.objects.filter(model_type=mt, model_id=mid, file_size=len(data)).exists():
        print(f"   = already on {mt} {mid}"); return
    if COMMIT:
        a = Attachment(model_type=mt, model_id=mid, comment=comment[:250], upload_user=user)
        a.attachment.save(os.path.basename(path), ContentFile(data), save=True)
        assert Attachment.objects.filter(pk=a.pk).exists()
    print(f"   + {mt} {mid}")


n = 0
for stem, (locs, group, single, comment) in MAP.items():
    path = f"{DIR}/{stem}-image.jpg"
    assert os.path.exists(path), path
    print(f"{stem}: {comment[:70]}")
    for name in locs:
        attach("stocklocation", StockLocation.objects.get(name=name, parent__pk=381).pk, path, comment)
    for pk in group + ([single] if single else []):
        attach("part", pk, path, comment)
    if single:
        p = Part.objects.get(pk=single)
        if p.image:
            print(f"   ! part {single} image slot full - left alone")
        elif COMMIT:
            p.image.save(os.path.basename(path), ContentFile(open(path, "rb").read()), save=True)
            p.refresh_from_db(); assert p.image
            print(f"   * part {single} image set")
        else:
            print(f"   * part {single} image would be set")
    n += 1
print(f"\n{n} photos {'attached' if COMMIT else '(DRY RUN -- add --commit)'}")
