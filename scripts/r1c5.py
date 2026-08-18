"""B3-R1C5: ALCO MTL-series miniature toggles.

Also corrects R1C4: I wrote that the C&K records covered 'red and mint bodies'.
The mint bodies are ALCO, not C&K - this drawer makes that obvious. Correcting
the note rather than leaving a wrong brand attribution sitting in the catalog.
"""
import argparse, os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

cat = Part.objects.get(pk=98).category

name = "ALCO MTL-106D Miniature Toggle Switch"
note = ("**ALCO** (Alcoswitch, later TE Connectivity) MTL-series miniature "
        "toggle. Mint-green body, metal bat handle, gold-plated terminals.\n\n"
        "Body stamped `MTL 106D ALCO` - the final character is D or 0 depending "
        "on the light; ALCO's catalogue part is **MTL-106D**, so that is the "
        "reading used here.\n\n"
        "Some bodies also carry **7903** / **7904**. Read as DATE CODES "
        "(1979, weeks 3-4), not part numbers - which would make these vintage "
        "US-made stock. Not verified against an ALCO date-code table.\n\n"
        "Mounting hardware is loose in the drawer with them: hex nuts, flat and "
        "internal-tooth lock washers, keyed washers, and black rubber boots. "
        "Not catalogued separately - they belong with the switches.")

p = Part.objects.filter(name=name).first()
if p:
    print(f"  exists  #{p.pk}  {name}")
else:
    print(f"  CREATE          {name}")
    if a.commit:
        p = Part.objects.create(
            name=name, category=cat,
            description="ALCO MTL-106D miniature toggle, mint body, gold terminals"[:250],
            notes=note, active=True, component=True, purchaseable=True)
        print(f"          -> #{p.pk}")

# --- correct the R1C4 brand attribution ---
for pk in (744, 745):
    q = Part.objects.filter(pk=pk).first()
    if not q or "red and mint bodies" not in (q.notes or ""):
        print(f"  #{pk}: nothing to correct")
        continue
    print(f"  correct #{pk}  {q.name}  — mint bodies are ALCO, not C&K")
    if a.commit:
        q.notes = q.notes.replace(
            "red and mint bodies",
            "**red** bodies (the mint-green ones in that drawer are ALCO "
            "MTL-series, not C&K - see B3-R1C5)")
        q.save()

print(f"\n{'WROTE' if a.commit else 'DRY RUN'}")
