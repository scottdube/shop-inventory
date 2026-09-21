"""Resolve FSD's GMA1347 parts list against the catalogue. READ ONLY."""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part
from stock.models import StockItem

WANT = [
    (1,  "PCB GMA1347 Control Board",      ["GMA1347"]),
    (1,  "Mega2560 Pro Mini",              ["MEGA 2560", "Mega2560"]),
    (1,  "Dual shaft encoder EC11EBB24C03",["EC11EBB24C03", "dual concentric", "GREEN base"]),
    (22, "White LED tactile 6x6x7",        ["6x6x7"]),
    (21, "2x5x7mm rectangular white LED",  ["2x5x7", "rectangular", "rectangle"]),
    (28, "Resistor 150 ohm",               ["Resistor 150R"]),
    (1,  "Header pins 2.54 male/female",   ["Glarks", "Pin Header"]),
    (1,  "IDC ribbon 24 pin",              ["24 pin", "24-pin", "IDC", "ribbon"]),
    (1,  "IDC ribbon 30 pin",              ["30 pin", "30-pin"]),
    (23, "M2 x 5mm screw",                 ["M2 x 0.4 mm Thread, 5"]),
    (5,  "M2 x 20mm screw",                ["M2 x 0.4 mm Thread, 20"]),
    (2,  "M5 bolt 20mm+",                  ["M5 x 0.8", "M5x"]),
    (2,  "M5 nut",                         ["Hex Nut", "M5"]),
    (2,  "M5 washer",                      ["Washer", "M5"]),
]

def basis(p):
    rows = list(StockItem.objects.filter(part=p))
    if not rows:
        return 0, "NO STOCK ROW"
    onhand = sum(float(r.quantity) for r in rows)
    notes = " ".join((r.notes or "") for r in rows)
    dated = any(r.stocktake_date for r in rows)
    if "[ESTIMATE]" in notes or "NOT COUNTED" in notes.upper():
        return onhand, "ESTIMATE"
    if "COUNTED" in notes.upper() and dated:
        return onhand, "TALLIED"
    return onhand, "UNKNOWN"

for qty, label, terms in WANT:
    hits = []
    for t in terms:
        q = Part.objects.filter(name__icontains=t)
        if len(terms) > 1 and t == terms[-1] and len(q) > 6:
            q = q[:6]
        for p in q:
            if p not in hits:
                hits.append(p)
    print("\nNEED %-3s  %s" % (qty, label))
    if not hits:
        print("      -> NO MATCH")
    for p in hits[:6]:
        oh, b = basis(p)
        print("      #%-5s %-48s on hand %-7.0f %s%s"
              % (p.pk, p.name[:48], oh, b, "" if p.active else "  [INACTIVE]"))
