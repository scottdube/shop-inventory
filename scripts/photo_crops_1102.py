"""Crop the 2026-11-02 LRD put-away group photos to one subject per stock row.

The first pass attached each whole group shot to every row in it, so the
47k-resistor row showed two RF cables as well. Scott asked whether they were
cropped "so they make sense". Boxes are fractions of the frame, read off
thumbnails, and each has a margin.

    itq run scripts/photo_crops_1102.py            # write crops to /tmp/crop-*.jpg for review
    itq run scripts/photo_crops_1102.py --commit   # replace the whole-shot attachments with the crops

The HC-SR04 photo shows only that part and isn't cropped.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from PIL import Image, ImageOps  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from django.core.files.base import ContentFile  # noqa: E402
from common.models import Attachment  # noqa: E402

CROPS = [  # (source, crop name, (l, t, r, b) fractions, stock items, comment)
    ("lrd-1102-47k-rf-pigtails", "47k-resistor", (0.27, 0.00, 0.82, 0.50), [1094], "47k 0.1% resistors as filed, F1-R3C1"),
    ("lrd-1102-47k-rf-pigtails", "sma-ufl-pigtail", (0.06, 0.44, 0.53, 1.00), [1073], "SMA-U.FL pigtails as filed, F1-R5C3"),
    ("lrd-1102-47k-rf-pigtails", "ufl-open-pigtail", (0.44, 0.42, 0.95, 1.00), [1074], "U.FL-open pigtails as filed, F1-R5C3"),
    ("lrd-1102-mmwave-esp32-testpins", "test-point-pins", (0.30, 0.04, 0.80, 0.29), [1088], "Test point pins as filed, F1-R5C1"),
    ("lrd-1102-mmwave-esp32-testpins", "esp32-wroom32", (0.44, 0.22, 1.00, 0.58), [878], "ESP32 WROOM-32 devkit as filed, F1-R1C2"),
    ("lrd-1102-mmwave-esp32-testpins", "xiao-mmwave", (0.00, 0.28, 0.58, 0.78), [64], "XIAO mmWave sensors as filed, F1-R2C2"),
    ("lrd-1102-swapmeet-diodes", "1n4001", (0.10, 0.00, 0.80, 0.56), [1193], "1N4001 swap-meet bag (marked 50), F1-R3C2"),
    ("lrd-1102-swapmeet-diodes", "1n4935", (0.10, 0.54, 0.80, 1.00), [1194], "1N4935 on tape, swap-meet bag, F1-R3C2"),
    ("lrd-1102-usb-ttl", "yp05-ft232rl", (0.00, 0.19, 0.72, 0.49), [1196], "YP-05 FT232RL board (USB-C), F1-R2C4"),
    ("lrd-1102-usb-ttl", "cp2102", (0.08, 0.64, 0.82, 0.88), [1195], "CP2102 board, F1-R2C4"),
    ("lrd-1102-battery-contacts", "battery-series-plates", (0.08, 0.38, 0.50, 0.90), [1197], "Series link plates, 9, F1-R5C4"),
    ("lrd-1102-battery-contacts", "battery-single-contacts", (0.52, 0.35, 0.92, 0.92), [1198, 1199], "Single spring and flat contacts (8 + 7), F1-R5C4"),
]
commit = "--commit" in sys.argv
u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
for src, name, (l, t, r, b), items, comment in CROPS:
    im = ImageOps.exif_transpose(Image.open(f"/tmp/{src}.jpg"))
    W, H = im.size
    out = f"/tmp/crop-{name}.jpg"
    im.crop((int(l * W), int(t * H), int(r * W), int(b * H))).convert("RGB").save(out, quality=88)
    print(f"{out}  {W}x{H}")
    if not commit:
        continue
    data = open(out, "rb").read()
    for pk in items:
        old = Attachment.objects.filter(model_type="stockitem", model_id=pk, attachment__contains=src)
        n = old.count()
        for a in old:
            a.attachment.delete(save=False)
            a.delete()
        a = Attachment(model_type="stockitem", model_id=pk, comment=comment, upload_user=u)
        a.attachment.save(f"{name}.jpg", ContentFile(data), save=True)
        left = Attachment.objects.filter(model_type="stockitem", model_id=pk)
        print(f"   stock {pk}: removed {n} whole shot, now {[x.attachment.name.split('/')[-1] for x in left]}")
print("DRY RUN - review /tmp/crop-*.jpg, then --commit" if not commit else "done")
