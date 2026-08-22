"""Record, during a count, that a project already ate some of a part.

Scott's workflow, and it is better than reasoning about history afterwards:
while counting a drawer, ask whether he remembers a project that used any. If
he does, put it through InvenTree's OWN allocation machinery instead of writing
prose around it:

    count says 27 on the shelf
    Scott: "three went into the pool controller"
      -> inflate stock to 30      (you cannot allocate stock you do not have)
      -> allocate 3 to that build
      -> on close, the build CONSUMES 3, stock returns to 27

The count ends correct AND `consumed_by` records the history, which is the
authoritative field that survives completion. The Project column then shows it
as fact rather than as a guess.

    itq run scripts/consumed.py --part 291 --used 3 --project "Pool Controller"
    itq run scripts/consumed.py --list
    itq run scripts/consumed.py --close "Pool Controller" --commit

**The build is left OPEN during the walk, deliberately.** A completed build
locks, exactly like a completed purchase order, and three drawers later another
part will turn out to belong to the same project. Accumulate, close once at the
end. Closing early means fighting a locked record for the rest of the session.
"""
import argparse, os, sys, django
from datetime import date

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part, PartCategory, BomItem
from stock.models import StockItem
from build.models import Build, BuildLine, BuildItem

ap = argparse.ArgumentParser()
ap.add_argument("--part", type=int)
ap.add_argument("--used", type=float)
ap.add_argument("--project")
ap.add_argument("--list", action="store_true", help="show reconstructed projects still open")
ap.add_argument("--close", metavar="PROJECT")
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

TAG = "[RECONSTRUCTED]"


def find_build(name, create=False):
    b = Build.objects.filter(title__iexact=name).first() \
        or Build.objects.filter(title__istartswith=name).first()
    if b or not create:
        return b
    cat = PartCategory.objects.filter(name__icontains="assembl").first() \
        or PartCategory.objects.filter(name="Tooling").first()
    asm = Part.objects.filter(name__iexact=name).first()
    if asm is None:
        asm = Part.objects.create(
            name=name[:100], category=cat, assembly=True, active=True,
            description=f"{TAG} project, created from a count. "
                        f"Not a designed assembly — a container for what it consumed."[:250])
    nxt = max([int(x.split("-")[1]) for x in
               Build.objects.values_list("reference", flat=True)
               if x.startswith("BO-") and x.split("-")[1].isdigit()] + [0]) + 1
    return Build.objects.create(
        reference=f"BO-{nxt:04d}", part=asm, title=name[:100], quantity=1, status=20,
        notes=(f"{TAG} 2026-08-22. Built from answers given during a drawer count: "
               f"Scott recalled which parts this project consumed while holding "
               f"them.\n\n**The PHYSICAL build date is unknown** — this record was "
               f"created long after the work. Do not compare stocktake dates "
               f"against its completion date; that comparison reads the wrong "
               f"event.\n\nLeft OPEN on purpose while the walk continues: a "
               f"completed build locks and more parts will turn up."))


if a.list:
    print("  Reconstructed projects still open:\n")
    n = 0
    for b in Build.objects.filter(status=20).order_by("reference"):
        if TAG not in (b.notes or ""):
            continue
        n += 1
        lines = BuildLine.objects.filter(build=b)
        alloc = BuildItem.objects.filter(build_line__build=b).count()
        print(f"  {b.reference}  {b.title}   {lines.count()} line(s), {alloc} allocated")
        for l in lines:
            print(f"      {l.quantity:g} x {l.bom_item.sub_part.name[:46]}")
    print(f"\n  {n} open. Close one with:  --close \"<title>\" --commit"
          if n else "  none yet")
    sys.exit()

if a.close:
    b = find_build(a.close)
    if not b:
        print(f"  no build titled {a.close!r}"); sys.exit(1)
    unalloc = [l for l in BuildLine.objects.filter(build=b)
               if not BuildItem.objects.filter(build_line=l).exists()]
    print(f"  {b.reference} {b.title}: "
          f"{BuildLine.objects.filter(build=b).count()} lines, "
          f"{len(unalloc)} with nothing allocated")
    for l in unalloc:
        print(f"    ! {l.bom_item.sub_part.name[:50]} — would consume nothing")
    if a.commit:
        Build.objects.filter(pk=b.pk).update(status=40, completion_date=date.today())
        print(f"  closed {b.reference} — allocated stock is now consumed")
        print(f"  consumed_by rows: {StockItem.objects.filter(consumed_by=b).count()}")
    else:
        print("  DRY RUN — add --commit to close")
    sys.exit()

if not (a.part and a.used and a.project):
    ap.error("need --part, --used and --project (or --list / --close)")

part = Part.objects.get(pk=a.part)
build = find_build(a.project, create=a.commit)
rows = StockItem.objects.filter(part=part, belongs_to__isnull=True,
                                consumed_by__isnull=True).order_by("-quantity")
if not rows:
    print(f"  #{part.pk} {part.name[:44]}: no stock row to inflate — count it first")
    sys.exit(1)
row = rows.first()
before = float(row.quantity)

print(f"  part    #{part.pk} {part.name[:52]}")
print(f"  project {a.project}  -> {build.reference if build else '(would create)'}")
print(f"  stock   {before:g} on shelf  ->  inflate to {before + a.used:g}, "
      f"allocate {a.used:g}, closing consumes it back to {before:g}")

if not a.commit:
    print("\n  DRY RUN — add --commit")
    sys.exit()

bom = BomItem.objects.filter(part=build.part, sub_part=part).first()
if bom:
    BomItem.objects.filter(pk=bom.pk).update(quantity=float(bom.quantity) + a.used)
else:
    bom = BomItem.objects.create(part=build.part, sub_part=part, quantity=a.used)
line = BuildLine.objects.filter(build=build, bom_item=bom).first() \
    or BuildLine.objects.create(build=build, bom_item=bom, quantity=a.used)
BuildLine.objects.filter(pk=line.pk).update(quantity=float(bom.quantity))

StockItem.objects.filter(pk=row.pk).update(
    quantity=before + a.used,
    notes=((row.notes or "").rstrip() + f"\n\n{TAG} 2026-08-22: inflated by "
           f"{a.used:g} and allocated to {build.reference} ({a.project}). Scott "
           f"recalled this consumption during a count. Closing that build "
           f"consumes it again, returning the count to the {before:g} actually "
           f"on the shelf — the number is restored and the history is real.").strip())
BuildItem.objects.create(build_line=line, stock_item=StockItem.objects.get(pk=row.pk),
                         quantity=a.used)

r = StockItem.objects.get(pk=row.pk)
ok = (float(r.quantity) == before + a.used
      and BuildItem.objects.filter(build_line=line).exists())
print(f"\n  {'ok  ' if ok else 'FAIL'} stock now {r.quantity:g}, allocated {a.used:g} to {build.reference}")
print(f"  when done walking:  itq run scripts/consumed.py --close \"{a.project}\" --commit")
