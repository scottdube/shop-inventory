"""Fold #53 into #242 — the ANNIMOS 35KG servo, entered twice.

Textbook import twins: #53 carries the tidy name and the pack/purchase note and
nothing else; #242 carries the verbose vendor title, the ASIN, the SupplierPart
and the image. Neither is right alone, which is why the merge has to happen
BEFORE RB-24's servo gets a stock row — otherwise the count lands on whichever
record was reached first and the other goes on looking like a part nobody owns.

Keeper is #242 by the house rule (ASIN + SupplierPart + history), but it takes
#53's NAME: the verbose one is a truncated Amazon title, and the tidy name is
the better search key and is about to disappear otherwise.
"""
import os, sys, django
from datetime import date
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part
from stock.models import StockItem
from company.models import SupplierPart

COMMIT = "--commit" in sys.argv
TODAY = date.today()
FOLD, KEEP = 53, 242
NEW_NAME = "ANNIMOS 35KG Coreless Digital Servo 7.4V Waterproof 180deg"
WHY = "both are the ANNIMOS 35KG coreless digital servo, ASIN B07SWW9NDR"

f, k = Part.objects.get(pk=FOLD), Part.objects.get(pk=KEEP)
print(f"fold #{f.pk} {f.name}")
print(f"  -> #{k.pk} {k.name[:70]}")
print(f"  keeper renamed to: {NEW_NAME!r} ({len(NEW_NAME)} chars)")
print(f"  stock rows to move: {StockItem.objects.filter(part=f).count()}")
print(f"  supplier parts to move: {SupplierPart.objects.filter(part=f).count()}")
print(f"  keeper default_location: {k.default_location} -> None (bare site root)")

if not COMMIT:
    print("\n  DRY RUN - add --commit")
    sys.exit()

StockItem.objects.filter(part=f).update(part=k)
SupplierPart.objects.filter(part=f).update(part=k)

k_notes = ((k.notes or "").rstrip() +
           f"\n\nMerged with hand-seeded part #{f.pk} on {TODAY} - {WHY}."
           f"\nSeed row recorded: {f.description}"
           f"\nRenamed from the truncated Amazon title to #{f.pk}'s tidier name, "
           f"which was the better search key and would otherwise have been lost."
           f"\ndefault_location was the bare site root and is now empty - there "
           f"is no home for a spare servo yet, and an empty field asks the "
           f"question where a wrong one answers it badly.").strip()
Part.objects.filter(pk=KEEP).update(name=NEW_NAME, notes=k_notes, default_location=None)

f_notes = ((f.notes or "").rstrip() +
           f"\n\n**MERGED** into #{k.pk} on {TODAY} - {WHY}.").strip()
Part.objects.filter(pk=FOLD).update(
    active=False, notes=f_notes,
    description=f"MERGED into part #{k.pk} ({NEW_NAME}). {f.description}"[:250])

f, k = Part.objects.get(pk=FOLD), Part.objects.get(pk=KEEP)
ok = (k.name == NEW_NAME and k.default_location is None and not f.active
      and SupplierPart.objects.filter(part=k).count() == 1
      and f.description.startswith("MERGED into part #242"))
print(f"\n  #{KEEP}: {k.name}  default_loc={k.default_location} "
      f"SPs={SupplierPart.objects.filter(part=k).count()}")
print(f"  #{FOLD}: active={f.active}  {f.description[:60]}")
print("  VERIFIED" if ok else "  MISMATCH - stop and look")
