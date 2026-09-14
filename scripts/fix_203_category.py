import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()
from part.models import Part, PartCategory

print("=== switch categories ===")
for c in PartCategory.objects.filter(pathstring__icontains='switch').order_by('pathstring'):
    print(f"  {c.pk:5d} {c.pathstring:46s} parts={Part.objects.filter(category=c).count()}")

flat = PartCategory.objects.filter(name='Switches', parent__isnull=True).first()
nested = PartCategory.objects.filter(pk=111).first()
pick = flat if flat and Part.objects.filter(category=flat).count() >= Part.objects.filter(category=nested).count() else nested
p = Part.objects.get(pk=203)
print(f"\n#203 was: {p.category.pathstring}")
p.category = pick
p.save(); p.refresh_from_db()
if p.category_id != pick.pk:
    Part.objects.filter(pk=203).update(category=pick)
    p.refresh_from_db()
print(f"#203 now: {p.category.pathstring}")
