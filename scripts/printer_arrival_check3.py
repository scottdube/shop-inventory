"""Battery vs mains, and the current InvenTree state of stock #570."""
import re
import subprocess
import urllib.request

HOST = "192.168.30.252"

print("=== full status page text (looking for battery / power fields) ===")
try:
    with urllib.request.urlopen(f"http://{HOST}/general/status.html", timeout=8) as f:
        body = f.read().decode("utf-8", "replace")
    text = re.sub(r"<[^>]+>", " ", body)
    text = text.replace("&#32;", " ")
    text = re.sub(r"\s+", " ", text).strip()
    print("  " + text[:1200])
    for kw in ("Batter", "batter", "Power", "AC ", "Charge", "charge"):
        for m in re.finditer(kw, text):
            print(f"  >> ...{text[max(0, m.start()-60):m.start()+90]}...")
except Exception as e:
    print(f"  {type(e).__name__}: {e}")

print("\n=== page_log via sudo -n (non-interactive; fine if it refuses) ===")
r = subprocess.run(["sudo", "-n", "grep", "-c", "QL810W", "/var/log/cups/page_log"],
                   capture_output=True, text=True)
print(f"  rc={r.returncode} out={r.stdout.strip()!r} err={r.stderr.strip()[:120]!r}")

print("\n=== InvenTree: stock #570 / part #1057 ===")
import django  # noqa: E402
django.setup()
from stock.models import StockItem  # noqa: E402

try:
    si = StockItem.objects.get(pk=570)
    print(f"  stock #570: {si.part.name} (part #{si.part.pk})")
    print(f"  quantity : {si.quantity}")
    print(f"  location : {si.location}")
    print(f"  status   : {si.status_label if hasattr(si, 'status_label') else si.status}")
    print(f"  serial   : {si.serial!r}")
    print(f"  notes    : {si.notes!r}")
    print(f"  url      : /web/stock/item/570/")
except StockItem.DoesNotExist:
    print("  stock #570 does not exist")

others = StockItem.objects.filter(part__pk=1057)
print(f"\n  all stock rows for part #1057: {others.count()}")
for o in others:
    print(f"    #{o.pk}  qty={o.quantity}  loc={o.location}  notes={str(o.notes)[:70]!r}")
