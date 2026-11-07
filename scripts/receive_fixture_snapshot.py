"""Dump every PO of the last 90 days as a receiving card, for local matcher
tests. Real records, not synthetic ones: the "rod" in "product" lesson.
    itq run scripts/receive_fixture_snapshot.py > binscan/fixtures/receive/pos-$(date +%F).json

This repo is PUBLIC. PO notes carry the house's street address, vendor emails
and refund narratives, so the note is cut down to the only two things the
matcher reads from it: tracking-shaped numbers and the bracket sentinels.
Measured 2026-11-06: PO-0289's note had the full LRD street address in it.
"""
import datetime, json, os, re, sys
import django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from order.models import PurchaseOrder  # noqa: E402
from plugins.receiving.engine import po_card  # noqa: E402

TRACK = re.compile(r"\b(TBA\d{12,15}|1Z[A-Z0-9]{16}|\d{20,22})\b")
SENTINEL = re.compile(r"\[[A-Z-]+\]")


def scrub_note(text):
    keep = TRACK.findall(text or "") + SENTINEL.findall(text or "")
    return " ".join(dict.fromkeys(keep))


since = datetime.date.today() - datetime.timedelta(days=90)
cards = []
for po in PurchaseOrder.objects.filter(creation_date__gte=since).order_by("-pk"):
    c = po_card(po)
    c["note"] = scrub_note(c["note"])
    cards.append(c)
print(json.dumps(cards, indent=1, default=str))
