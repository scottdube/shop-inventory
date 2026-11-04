"""Read-only survey for the consumable-flag item (OPEN.md, 2026-11-04).
Prints the category tree with part counts, then every active part whose category path or
name matches a consumable-ish keyword, as JSON lines for local sorting.
Run: itq run scripts/consumable_survey_1104.py > /tmp/... (writes nothing on the Mini)"""
import os, sys, json, re
sys.path.insert(0, os.getcwd()); os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
import django; django.setup()
from django.db.models import Count, Sum
from part.models import Part, PartCategory
from stock.models import StockItem

cats = PartCategory.objects.annotate(n=Count("parts")).order_by("tree_id", "lft")
print("### CATEGORIES")
for c in cats:
    total = Part.objects.filter(category__in=c.get_descendants(include_self=True), active=True).count()
    print(f"CAT\t{c.pk}\t{c.pathstring}\t{c.n}\t{total}")

KW = re.compile(r"consumab|solder|flux|wick|braid|tape|glue|epoxy|adhesive|ca glue|loctite|threadlock|"
                r"filament|resin|sandpaper|abrasive|flap disc|grinding|cut[- ]?off|scotch|wheel|"
                r"insert|nozzle|tip\b|tips\b|blade|bit\b|bits\b|burr?\b|end ?mill|drill|v-?bit|"
                r"zip ?tie|cable tie|heat ?shrink|shrink tub|wax|label|lubric|grease|oil|cutting fluid|coolant|"
                r"wipe|glove|rag|paper towel|alcohol|ipa|cleaner|polish|fuse|battery|batteries|"
                r"electrode|wire\b|mig|tungsten|plasma|consumable|filter|bag|tie wrap|sleeve|ferrule|crimp", re.I)
print("### PARTS")
stock = {r["part"]: (r["q"], r["n"]) for r in StockItem.objects.values("part").annotate(q=Sum("quantity"), n=Count("pk"))}
for p in Part.objects.filter(active=True).select_related("category").order_by("category__tree_id", "category__lft", "name"):
    path = p.category.pathstring if p.category else ""
    hit = KW.findall(f"{p.name} {p.description or ''}")
    incat = "consumab" in path.lower()
    if not (hit or incat): continue
    q, n = stock.get(p.pk, (0, 0))
    print("PART\t" + json.dumps({"pk": p.pk, "name": p.name, "desc": (p.description or "")[:90], "cat": path,
          "kw": sorted({h.lower() for h in hit}), "incat": incat, "qty": float(q or 0), "rows": n,
          "trackable": p.trackable, "assembly": p.assembly, "component": p.component, "virtual": p.virtual}))
