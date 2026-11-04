"""Correct the UNLOCATED notes on stock 867 (330R x2) and 868 (470R x1).

Scott, 2026-11-04: "I believe those are part of a project ... the G1000 project."
Right: their own notes say R9/R10 and R15 of the FSD v2.3 board, and the Sim
G1000 BOM (part 1137) carries 330R x2 (ref R300) + 470R x1 (ref R450). They are
G1000 build #3 parts in the Florida kit, which the record has in LRD/Receiving
with the PCBs, LEDs and switches. The "do not re-ask" note was wrong and is
replaced. Stock 1080 (1k x4) is NOT on the G1000 BOM and keeps its note.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from common.models import Note  # noqa: E402
from stock.models import StockItem  # noqa: E402

TXT = ("IDENTIFIED 2026-11-04 (Scott): G1000 build #3 parts (Sim G1000 BOM, part 1137), travelling "
       "with the G1000 Florida kit. Supersedes the UNLOCATED note written the same day. Physical bag "
       "location at LRD to be confirmed with the rest of the G1000 kit.")
for pk in (867, 868):
    s = StockItem.objects.get(pk=pk)
    n = s.notes.filter(title="Unlocated")
    assert n.count() == 1, (pk, n.count())
    n.update(title="Identified", content=TXT)
    print(pk, s.part.name, [(x.title, x.content[:60]) for x in StockItem.objects.get(pk=pk).notes.all()])
print("1080 keeps:", [x.title for x in StockItem.objects.get(pk=1080).notes.all()])
