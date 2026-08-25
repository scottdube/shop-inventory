"""Close two unknowns from the 2026-08-25 walk.

#1097: the dial was read. 0 to -30 inHg / 0 to -1 bar, NEGATIVE ONLY. It is a
vacuum gauge, so the name changes from "Pressure Gauge" -- the word that would
have sent someone looking for a positive range it does not have.

#1096: Scott supplied the eBay listing. It is a CIRCUIT BOARD kit, which
settles the open question of whether a practice PCB ships with it.
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

G_NAME = "Vacuum Gauge, 3in dial, 0 to -30 inHg / -1 bar, MEANLIN XJ-087"
G_DESC = ("MEANLIN MEASURE 3in dial VACUUM gauge. Dual scale 0 to -30 inHg and "
          "0 to -1 bar (-100 kPa). NEGATIVE ONLY - no positive range. Lower "
          "mount, accuracy +/-3-2-3%. Media water/oil/air, 32-131F. SKU "
          "XJ-087, ASIN X002SLRYVX. Dial read 2026-08-25.")
G_NOTE_ADD = (
    f"\n\n--- RANGE READ {TODAY} ---\n"
    "Dial photographed in hand: black scale 0 to -30 inHg, red scale 0 to -1 "
    "bar, marked 'bar 100xkPa' and 'inHg'. NEGATIVE ONLY. It is a vacuum gauge, "
    "not a general-service pressure gauge, and it is the correct half of the "
    "scale for the Vacuum Controller - it pairs with #107 (MPXV6115VC6U, 0 to "
    "-115 kPa) rather than with the positive 1/8 NPT transducers in B3-R7C2.\n\n"
    "-30 inHg is -101.6 kPa, i.e. the full physical vacuum range; the sensor's "
    "-115 kPa spec runs past what any vacuum can actually reach, so the gauge "
    "is not the narrower instrument in practice.\n\n"
    "A BRASS FITTING IS ALREADY MADE UP ON THE STEM (a compression fitting on "
    "the male thread). Thread size still unread.")

K_NAME = "Soldering Practice Kit, SMD components + PCB (eBay)"
K_DESC = ("SMD soldering practice kit: PCB plus cut-tape 0805/SOT23/LL34 parts "
          "and a 16-line BOM card. eBay item 146596207902, seller Czb "
          "Electronic (ShenZhen). orig: Soldering Practice SMD Circuit Board "
          "kit LED Electronics Project DIY kit SMT PCB")
K_NOTE_ADD = (
    f"\n\n--- LISTING SUPPLIED BY SCOTT {TODAY} ---\n"
    "ebay.com/itm/146596207902 - 'Soldering Practice SMD Circuit Board kit LED "
    "Electronics Project DIY kit SMT PCB', seller Czb Electronic, ShenZhen. "
    "THE KIT INCLUDES THE PCB - the open question of whether a practice board "
    "ships with it is closed, and it is a board, not a bag of parts.\n\n"
    "Listed today at US $3.82 each (was $4.11), tiered to $3.51 at 4+. That is "
    "TODAY'S price, NOT what was paid - the order was 2026-06-16 and the "
    "purchase price is in that mail, unread.\n\n"
    "Variant selector on the listing includes 'Ordinary+Batterry Box 2slot'; "
    "which variant these three are is unknown.\n\n"
    "WHY THE IMPORT MISSED IT - and it is NOT the unknown-vendor blind spot. "
    "ebay.com is on the registry's KNOWN list and is swept per-order. The "
    "order was placed 2026-06-16 and delivered 2026-06-27, about 70 days ago, "
    "and the sweep runs over a ~45-day window. The mailbox holds ~201 eBay "
    "order confirmations going back to 2022; the instance holds ONE eBay PO. "
    "The gap is the LOOKBACK, not the vendor list.")

for pk, name, desc in [(1097, G_NAME, G_DESC), (1096, K_NAME, K_DESC)]:
    p = Part.objects.get(pk=pk)
    print(f"#{pk}\n  name: {p.name!r}\n     -> {name!r} ({len(name)})")
    print(f"  desc: {len(desc)} chars")

if not COMMIT:
    print("\n  DRY RUN - add --commit")
    sys.exit()

for pk, name, desc, note_add in [(1097, G_NAME, G_DESC, G_NOTE_ADD),
                                 (1096, K_NAME, K_DESC, K_NOTE_ADD)]:
    Part.objects.filter(pk=pk).update(name=name, description=desc)
    si = StockItem.objects.filter(part_id=pk).first()
    StockItem.objects.filter(pk=si.pk).update(notes=si.notes + note_add)
    p = Part.objects.get(pk=pk)
    si = StockItem.objects.get(pk=si.pk)
    ok = p.name == name and p.description == desc and si.notes.endswith(note_add)
    print(f"#{pk} {'OK' if ok else 'MISMATCH'}  {p.name}")

RB17 = ("VACUUM CONTROLLER project - the whole kit, both halves in one bin, and "
        "both read the NEGATIVE side. (1) MPXV6115VC6U sensor #107, 0 to -115 "
        "kPa, ported SOP-8, anti-static. (2) MEANLIN 3in vacuum gauge #1097, 0 "
        "to -30 inHg / -1 bar, lower mount, brass compression fitting already "
        "made up on the stem, thread size unread. Neither is interchangeable "
        "with the positive-pressure 1/8 NPT transducers in B3-R7C2. Gauge moved "
        "in from RB-21 2026-08-25: one project, one bin, and it freed RB-21.")
StockLocation.objects.filter(name="RB-17").update(description=RB17)
print("RB-17:", "OK" if StockLocation.objects.get(name="RB-17").description == RB17 else "MISMATCH")
