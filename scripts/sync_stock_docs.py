"""Put a part's datasheet URL on its STOCK rows, where people actually look.

InvenTree keys attachments by model. A datasheet attached to a Part is
invisible from a StockItem -- the stock screen shows an empty attachment list,
not a pointer. Scott, 2026-08-23:

    "When I look at the part, I get the data sheet. When I look at the part in
    stock as a stock item, there's no attachment, no data sheet attached. It
    seems like a trap."

    "You're gonna go in through stock ninety nine percent of the time because
    you wanna know if you have it. So having to go in through parts doesn't
    really help you, because you got parts showing up in there that you don't
    have in stock."

That is the whole argument. Stock answers *do I have it*, which is the question
being asked at a bench; Parts answers *does it exist*, which is not.

This sets `StockItem.link` -- InvenTree renders it as an external link on the
stock detail page -- to the part's first attachment. binscan covers the same
gap on the phone with its own document chips; this covers the web UI.

**A link, deliberately, and not a copy.** Duplicating the file onto every stock
row would be four copies to update and three chances to read a stale one. A URL
goes stale only if the attachment is deleted, and it is derived, so re-running
this fixes it.

**Never overwrites a link somebody else set.** Only fills an empty one, or
refreshes one this script previously wrote (recognised by the /media/attachments
prefix). A hand-entered link to a vendor page is a human's work and outranks
this.

    itq run scripts/sync_stock_docs.py            # dry run
    itq run scripts/sync_stock_docs.py --commit
"""
import argparse
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.apps import apps                                      # noqa: E402
from stock.models import StockItem                                # noqa: E402

Attachment = apps.get_model("common", "Attachment")

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
ap.add_argument("--base", default="",
                help="URL prefix for media, e.g. http://192.168.50.10:8001 . "
                     "Without it the link is stored site-relative, which the "
                     "InvenTree web UI resolves against its own host.")
a = ap.parse_args()

# Documents only. Several parts carry detail PHOTOS as attachments, and a
# field the UI labels "External Link" pointing at a jpg of the thing you are
# already holding is noise -- worse, it teaches you the link is not worth
# tapping. Images stay on the part, where they render as images.
DOCS = (".pdf", ".txt", ".htm", ".html", ".doc", ".docx", ".md")

docs = {}
photos = 0
for att in Attachment.objects.filter(model_type="part").order_by("pk"):
    f = str(att.attachment or "")
    if not f:
        continue
    if not f.lower().endswith(DOCS):
        photos += 1
        continue
    if att.model_id not in docs:
        docs[att.model_id] = f
print(f"parts with a DOCUMENT attachment: {len(docs)}  "
      f"(skipped {photos} image attachment(s))")

MINE = "/media/attachments"
changed = skipped = kept = 0
for si in StockItem.objects.select_related("part", "location").all():
    f = docs.get(si.part_id)
    if not f:
        continue
    url = f"{a.base.rstrip('/')}/media/{f.lstrip('/')}"
    cur = (si.link or "").strip()
    if cur == url:
        kept += 1
        continue
    if cur and MINE not in cur:
        # somebody's own link. Not ours to overwrite.
        print(f"  stock {si.pk}: has a hand-set link, leaving it - {cur[:52]}")
        skipped += 1
        continue
    where = si.location.name if si.location else "(unlocated)"
    print(f"  stock {si.pk:4} {where:14} {si.part.name[:40]:42} -> {url[-52:]}")
    changed += 1
    if a.commit:
        StockItem.objects.filter(pk=si.pk).update(link=url)
        if (StockItem.objects.get(pk=si.pk).link or "") != url:
            print(f"       DID NOT VERIFY on re-read")
            sys.exit(1)

print(f"\n{'WROTE' if a.commit else 'DRY RUN'}: {changed} set, {kept} already "
      f"correct, {skipped} left alone")
