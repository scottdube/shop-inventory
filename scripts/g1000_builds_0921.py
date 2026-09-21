import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from build.models import Build, BuildItem
from stock.models import StockItem

ST = {10: "Pending", 20: "Production", 30: "Cancelled", 40: "Complete", 50: "OnHold"}
qs = Build.objects.filter(title__icontains="g1000") | Build.objects.filter(title__icontains="pfd") | Build.objects.filter(title__icontains="mfd")
for b in qs.distinct().order_by("reference"):
    print("== %s  %-28s %-11s qty=%s  part=#%s %s" % (
        b.reference, b.title, ST.get(b.status, b.status), b.quantity,
        b.part.pk, b.part.name[:40]))
    print("   created %s  target %s  completed %s" % (
        b.creation_date, b.target_date, b.completion_date))
    if b.notes:
        print("   notes: %s" % " / ".join(b.notes.strip().splitlines())[:300])
    for bl in b.build_lines.all():
        n = BuildItem.objects.filter(build_line=bl).count()
        print("     line  #%-5s %-42s need %-6s allocs %s" % (
            bl.bom_item.sub_part.pk, bl.bom_item.sub_part.name[:42], bl.quantity, n))
