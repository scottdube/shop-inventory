import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()
from stock.models import StockLocation, StockItem

l = StockLocation.objects.get(pk=568)
l.description = (
    "BARRIER TERMINAL BLOCKS & WIRE TERMINALS. Chassis-mount barrier strips "
    "(600 V 15 A, dual row, WEIDU TB-15xx) in 4, 5, 6, 7, 8, 10 and 12 "
    "positions, their pre-insulated jumper bars, and the fork crimp terminals "
    "that land in them. Established 2026-09-16 from the dissolved Glarks kit "
    "#283.\n\n"
    "NOT the PCB terminal blocks. The 2.54 mm and 5.08 mm blocks that SOLDER "
    "INTO A BOARD live in A3-R8C6 and A3-R8C7. Despite sharing the words "
    "'terminal block' these are a different class of thing: chassis-mount, "
    "screw-down, ring-or-fork-terminal. The test is whether it mounts to a "
    "panel or to a PCB.\n\n"
    "THE FORKS AND JUMPERS ARE [ESTIMATE] CARD FIGURES, not counts -- the kit "
    "had already been drawn on when it was catalogued (its 3-position block was "
    "gone). Treat 100 and 16 as upper bounds. [6 x 4-9/16 x 2-3/16 in, large]"
)
l.save(); l.refresh_from_db()
print(f"scope written: {'BARRIER TERMINAL BLOCKS' in l.description}")
print(f"{l.pathstring} holds {StockItem.objects.filter(location=l).count()} rows:")
for si in StockItem.objects.filter(location=l).select_related('part'):
    est = ' [ESTIMATE]' if (si.notes or '').startswith('[ESTIMATE]') else ''
    print(f"   {float(si.quantity):>4g}  {si.part.name[:62]}{est}")
