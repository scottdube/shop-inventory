"""#1097 never had a dial size. I read one out of a truncated string.

The box's Amazon label reads "MEANLIN MEASURE -3... Gauge , Lower Mount" -- an
ELIDED title. I read the "-3" as a 3-inch face. It is the head of "-30inHG",
which is the RANGE, and the range was the one thing the box did not otherwise
state. So the guess was wrong twice: wrong fact, and invented from the very
character sequence that was carrying the fact I said was missing.

MEANLIN sells this same -30inHG~0Psi gauge in 2in, 2.5in and 3in faces and in
both 1/8in and 1/4in NPT, so the listing family pins neither. The ASIN
X002SLRYVX returns no results on Amazon today.
"""
import os, sys, django
from datetime import date
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part
from stock.models import StockItem, StockLocation

COMMIT = "--commit" in sys.argv
TODAY = date.today()

NAME = "Vacuum Gauge, 0 to -30 inHg / -1 bar, lower mount, MEANLIN XJ-087"
DESC = ("MEANLIN MEASURE dial VACUUM gauge. 0 to -30 inHg and 0 to -1 bar "
        "(-100 kPa), dual scale, NEGATIVE ONLY. Lower mount, accuracy "
        "+/-3-2-3%, media water/oil/air, 32-131F. SKU XJ-087, ASIN "
        "X002SLRYVX. DIAL SIZE AND THREAD BOTH UNMEASURED.")
ADD = (f"\n\n--- CORRECTION {TODAY} ---\n"
       "This part was recorded earlier today as a '3in dial'. IT WAS NEVER "
       "MEASURED. The figure came from the box's Amazon label, which reads "
       "'MEANLIN MEASURE -3... Gauge , Lower Mount' - an elided title, where "
       "the '-3' is the head of '-30inHG', the RANGE. Reading it as a face "
       "size invented a spec out of the characters carrying the one fact the "
       "box was said to be missing.\n\n"
       "DIAL SIZE AND THREAD ARE BOTH UNKNOWN and the listing cannot settle "
       "either: MEANLIN sells this same -30inHG~0Psi gauge in 2in, 2.5in and "
       "3in faces and in both 1/8in and 1/4in NPT, and ASIN X002SLRYVX returns "
       "no results on Amazon today. Amazon's mail truncates the title too, so "
       "the July 2025 order (114-8365953-..., bought with a VEVOR 7 CFM vacuum "
       "pump) does not carry it either.\n\n"
       "BOTH ARE A CALIPER AWAY. Face diameter across the bezel, and the thread "
       "OD - 1/8 NPT is about 10.3 mm, 1/4 NPT about 13.7 mm, which no one can "
       "confuse. Note a brass compression fitting is made up on the stem, so "
       "measure the GAUGE thread, not the fitting's.")

p = Part.objects.get(pk=1097)
print(f"#{p.pk}\n  was: {p.name}\n  now: {NAME} ({len(NAME)})")
print(f"  desc {len(DESC)} chars")
if not COMMIT:
    print("\n  DRY RUN - add --commit"); sys.exit()

Part.objects.filter(pk=1097).update(name=NAME, description=DESC)
si = StockItem.objects.filter(part_id=1097).first()
StockItem.objects.filter(pk=si.pk).update(notes=si.notes + ADD)

RB17 = ("VACUUM CONTROLLER project - the whole kit, both halves in one bin, and "
        "both read the NEGATIVE side. (1) MPXV6115VC6U sensor #107, 0 to -115 "
        "kPa, ported SOP-8, anti-static. (2) MEANLIN vacuum gauge #1097, 0 to "
        "-30 inHg / -1 bar, lower mount - DIAL SIZE AND THREAD BOTH UNMEASURED, "
        "and a brass compression fitting is already made up on the stem, so "
        "measure the gauge thread and not the fitting's. Neither instrument is "
        "interchangeable with the positive-pressure 1/8 NPT transducers in "
        "B3-R7C2. Gauge moved in from RB-21 2026-08-25.")
StockLocation.objects.filter(name="RB-17").update(description=RB17)

p = Part.objects.get(pk=1097)
si = StockItem.objects.get(pk=si.pk)
ok = p.name == NAME and p.description == DESC and si.notes.endswith(ADD)
print(f"\n  {p.name}")
print("  VERIFIED" if ok else "  MISMATCH")
print("  RB-17:", "OK" if StockLocation.objects.get(name='RB-17').description == RB17 else "MISMATCH")
