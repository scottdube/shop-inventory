"""Read-only: do the eBay tooling purchases already have a part?

2026-10-05, docs/tooling-inventory.md eBay pass. One line per eBay row: the
search terms tried and every ACTIVE part whose name/description/keywords match
all terms of any one probe, with its total stock. Read the whole hit list; a
name search is a lead, not a verdict (memory: inventory-search-the-requirement).

    itq run scripts/ebay_dupcheck_1005.py
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.db.models import Q, Sum  # noqa: E402

from company.models import Company  # noqa: E402
from part.models import Part  # noqa: E402

ROWS = [
    ("Starrett 257D surface gage", ["surface gage", "surface gauge", "257"]),
    ("Tormach ETS tool-length probe", ["tool setter", "ETS", "electronic tool", "tool length"]),
    ("SolidClamp toe clamp x4", ["toe clamp", "solidclamp"]),
    ("Mid Tech 1.5540 ring gage", ["ring gage", "ring gauge", "plug gage", "1.554"]),
    ("Starrett tap drill chart", ["tap drill chart", "drill chart"]),
    ("Starrett S829EZ small hole gages", ["small hole", "S829", "hole gage"]),
    ("Micrometer stand", ["micrometer stand", "mic stand"]),
    ("Starrett S167C radius gages", ["radius gage", "radius gauge", "S167", "fillet"]),
    ("Lead hammer mold 4 lb", ["hammer mold", "lead hammer"]),
    ("Starrett 81-111-630 dial indicator", ["81-111", "dial indicator"]),
    ("Lot of 4 Federal test indicators", ["federal", "test indicator"]),
    ("Tapmatic 30XB", ["tapmatic", "tapping head", "30XB"]),
    ("6x18 magnetic chuck", ["magnetic chuck", "mag chuck"]),
    ("5C cutter grinder", ["cutter grinder", "grinder"]),
    ("31 Hardinge 5C collets", ["5C", "collet"]),
    ("Starrett 91-D tap handle", ["tap handle", "91-D", "91D"]),
    ("Starrett 711GCS test indicator", ["711", "last word", "test indicator"]),
    ("Starrett 25-441J dial indicator", ["25-441", "dial indicator"]),
    ("Starrett 472 screw pitch gage", ["pitch gage", "pitch gauge", "thread gage", "472"]),
    ("Tapmatic 50X", ["tapmatic", "50X", "tapping head"]),
    ("Starrett millwright level", ["level", "millwright"]),
    ("Lathe alignment test bar", ["test bar", "alignment bar", "alignment"]),
    ("X-axis power feed", ["power feed"]),
    ("Starrett 91C tap wrench", ["tap wrench", "91C", "91-C"]),
    ("Accusize 87-piece gauge blocks", ["gauge block", "gage block", "accusize"]),
    ("DRO 2-axis", ["DRO", "readout"]),
    ("V block 2-1/4", ["v block", "v-block", "vee block"]),
    ("DRO 3-axis", ["DRO", "readout"]),
    ("DRO scales 550+200", ["scale", "glass scale", "linear scale"]),
    ("DRO scales 900+200", ["scale", "linear scale"]),
    ("Clough42 ELS kit", ["clough", "electronic leadscrew", "ELS"]),
    # tooling? - checked too so the question to Scott is informed
    ("3000W induction heater module", ["induction"]),
    ("Bosch GLM400C laser measure", ["GLM", "laser measure", "bosch"]),
    ("Milwaukee 2457-80", ["milwaukee", "2457"]),
    ("Plasma starter kit", ["plasma"]),
    ("Firepower helmet", ["helmet", "firepower"]),
    ("Revco welding jacket", ["welding jacket", "revco"]),
    ("20 mm shaft and blocks", ["20mm shaft", "linear shaft", "shaft support"]),
    ("41-piece terminal removal tool", ["terminal removal", "pin removal", "depinning"]),
]


def probe(term):
    q = Q(name__icontains=term) | Q(description__icontains=term) | Q(keywords__icontains=term)
    return Part.objects.filter(q, active=True)


for label, terms in ROWS:
    seen = {}
    for t in terms:
        hits = probe(t)
        if hits.count() > 15:
            seen.setdefault("__wide__", []).append(f"{t}={hits.count()}")
            continue
        for p in hits:
            seen.setdefault(p.pk, p)
    wide = seen.pop("__wide__", [])
    print(f"\n## {label}   terms={terms}" + (f"  TOO WIDE (skipped): {wide}" if wide else ""))
    if not seen:
        print("    (no active part)")
    for pk, p in seen.items():
        q = p.stock_items.aggregate(s=Sum("quantity"))["s"] or 0
        print(f"    #{pk:<5} stock={float(q):<5g} {p.category.pathstring if p.category else '-'} :: {p.name[:70]}")

print("\nEBAY COMPANY:", [(c.pk, c.name, c.is_supplier) for c in Company.objects.filter(name__icontains="ebay")])
