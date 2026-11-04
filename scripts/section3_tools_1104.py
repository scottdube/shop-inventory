"""Read-only: the 20 'No' parts of docs/consumable-flag-draft.md section 3. For each, its
category, stock rows (qty, location, note head), purchase lines, and any Equipment/Tools/
Tooling part whose name shares two significant words (a possible existing tool record).
Run: itq run scripts/section3_tools_1104.py"""
import os, sys, re
sys.path.insert(0, os.getcwd()); os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
import django; django.setup()
from part.models import Part
from stock.models import StockItem
from order.models import PurchaseOrderLineItem
from plugins.notes_compat import note_text

NO = [438,445,141,209,314,316,474,364,201,396,353,315,407,311,334,309,421,853,1490,492]
STOP = set("with and for the inch tool tools set kit station digital portable white black large high heat display "
           "automatic temp temperature including 110v 110-240v 1000w adjustable professional magnetic light".split())
toolish = [p for p in Part.objects.filter(active=True).select_related("category")
           if p.category and p.category.pathstring.split("/")[0] in ("Equipment", "Tools", "Tooling", "Shop")]
def words(s): return {w for w in re.findall(r"[a-z0-9][a-z0-9-]{2,}", s.lower()) if w not in STOP}
for pk in NO:
    p = Part.objects.select_related("category").get(pk=pk)
    print(f"\n#{pk} {p.name[:90]}\n   cat={p.category.pathstring if p.category else '-'} active={p.active} "
          f"purchaseable={p.purchaseable} component={p.component} default_loc={p.default_location}")
    for s in StockItem.objects.filter(part=p).select_related("location"):
        print(f"   stock #{s.pk} qty={s.quantity:g} loc={s.location.pathstring if s.location else '-'} "
              f"meta={ {k: v for k, v in (s.metadata or {}).items() if k in ('trip', 'florida')} } note={note_text(s)[:90]!r}")
    for l in PurchaseOrderLineItem.objects.filter(part__part=p).select_related("order"):
        print(f"   PO {l.order.reference} {l.order.supplier.name if l.order.supplier else ''} "
              f"{l.order.issue_date or l.order.creation_date} qty={l.quantity:g} recv={l.received:g}")
    w = words(p.name)
    sib = [(len(w & words(q.name)), q) for q in toolish if q.pk != pk]
    for n, q in sorted(sib, key=lambda x: -x[0])[:3]:
        if n >= 2:
            print(f"   ~ #{q.pk} [{q.category.pathstring}] {q.name[:70]} "
                  f"stock={sum(float(s.quantity) for s in q.stock_items.all()):g}")
