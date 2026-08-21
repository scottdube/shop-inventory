"""Attach a datasheet PDF to a Part from a URL.

Datasheets kept coming up one at a time and each one was a fresh download,
scp and Django snippet. This is the same shape as print_part_label.py: one
command, so the work does not need re-deriving.

    itq run scripts/attach_datasheet.py 710 https://.../YSD-160AR4B-8.pdf \
        --comment "Manufacturer datasheet — YSD-160AR4B-8"

Runs on the server, so the download happens there. Refuses anything that is
not actually a PDF: a vendor site behind bot detection returns an HTML error
page with a 200, and attaching that gives a part record a datasheet-shaped
file containing a captcha. Checks the magic bytes, not the URL or the
content-type header.

Idempotent by filename: re-running will not stack duplicates.
"""
import argparse, os, sys, tempfile, urllib.request, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.core.files import File
from django.contrib.auth import get_user_model
from common.models import Attachment
from part.models import Part

ap = argparse.ArgumentParser()
ap.add_argument("part", type=int)
ap.add_argument("url")
ap.add_argument("--comment", default="")
ap.add_argument("--name", default=None, help="stored filename; default from the URL")
a = ap.parse_args()

part = Part.objects.filter(pk=a.part).first()
if part is None:
    print(f"no such part: #{a.part}")
    sys.exit(1)

name = a.name or os.path.basename(a.url.split("?")[0]) or f"datasheet_{a.part}.pdf"
if not name.lower().endswith(".pdf"):
    name += ".pdf"

if Attachment.objects.filter(model_type="part", model_id=a.part,
                             attachment__endswith=name).exists():
    print(f"already attached to #{a.part}: {name}")
    sys.exit(0)

req = urllib.request.Request(a.url, headers={"User-Agent": "Mozilla/5.0"})
try:
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
except Exception as exc:
    print(f"download failed: {exc}")
    sys.exit(1)

# A 200 proves the server answered, not that it answered with a datasheet.
if not data.startswith(b"%PDF"):
    head = data[:80].decode("utf-8", "replace").replace("\n", " ")
    print(f"NOT A PDF ({len(data)} bytes, starts {head!r}) — refusing to attach.")
    print("Vendor sites behind bot detection return an HTML error page with a "
          "200. Drive a browser and save the file, then use itq push.")
    sys.exit(1)

tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
tmp.write(data)
tmp.close()

user = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
with open(tmp.name, "rb") as fh:
    att = Attachment.objects.create(
        model_type="part", model_id=a.part, attachment=File(fh, name=name),
        comment=a.comment or f"Datasheet for {part.name}", upload_user=user)
os.unlink(tmp.name)

got = Attachment.objects.filter(pk=att.pk).first()
ok = got is not None and got.file_size == len(data)
print(f'  {"ok  " if ok else "FAIL"} #{a.part} {part.name[:38]:38} '
      f'-> {got.attachment.name if got else None} ({got.file_size if got else 0} bytes)')
sys.exit(0 if ok else 1)
