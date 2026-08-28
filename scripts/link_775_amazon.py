"""Attach the 775 motors to their real Amazon supplier part, and correct the record.

Scott found it in his order history 2026-08-28, which this side could not do:
Amazon order history needs his logged-in session.

    ASIN B08NTK8JXZ, brand Puly, sold by Pulyyds
    "775 DC Motor DC 12V - 24V Max 12000 RPM ... Motor 2-Pack (with Bracket)"
    Last purchased 2024-01-07. Listed at $26.88 on 2026-08-28.

pack_quantity = 2: one purchased unit is a 2-pack, which is why two motors came
from one order line. Follows the majority convention here (11 supplier parts
carry pack != 1), not the per-item exception documented on #276.

PRICE IS THE CURRENT LISTING, NOT WHAT WAS PAID. $26.88 is what the page showed
today; the 2024-01-07 figure is unknown and is not guessed at.
"""
import argparse, datetime, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from company.models import Company, SupplierPart                 # noqa: E402
from part.models import Part                                     # noqa: E402

PART, ASIN = 1139, "B08NTK8JXZ"
TODAY = datetime.date.today()

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

amazon = Company.objects.get(name="Amazon", is_supplier=True)
p = Part.objects.get(pk=PART)
print(f"part #{p.pk} {p.name}")
print(f"  supplier parts now: {SupplierPart.objects.filter(part=p).count()}")
if SupplierPart.objects.filter(SKU=ASIN).exists():
    sys.exit("!! that ASIN already exists")
if not a.commit:
    raise SystemExit("\nDRY RUN — add --commit")

sp = SupplierPart.objects.create(part=p, supplier=amazon, SKU=ASIN,
                                 pack_quantity="2",
                                 link=f"https://www.amazon.com/dp/{ASIN}")
got = SupplierPart.objects.get(pk=sp.pk)
assert got.SKU == ASIN and str(got.pack_quantity) == "2", "supplier part did not stick"
print(f"OK  SupplierPart {got.SKU} under Amazon, pack=2")

add = (
 "\n\n--- VENDOR RESOLVED 2026-08-28, and the earlier note was wrong ---\n"
 "AMAZON, ASIN B08NTK8JXZ, brand Puly, sold by Pulyyds. Listing title: \"775 DC "
 "Motor DC 12V - 24V Max 12000 RPM Ball Bearing Large Torque High Power Low "
 "Noise Gear Motor Electronic Component Motor 2-Pack (with Bracket)\". Last "
 "purchased 2024-01-07. Listed at $26.88 on 2026-08-28 — that is the CURRENT "
 "price, not what was paid; the 2024 figure is unknown and is not guessed.\n\n"
 "So the Banggood/AliExpress recollection was wrong and the Amazon-format FNSKU "
 "on the carton was right after all. Scott found it by searching his own order "
 "history, which this side cannot reach.\n\n"
 "THE LISTING CONTRADICTS ITSELF, so measure before designing. The title says "
 "'Max 12000 RPM'; the spec table on the same page says Speed 20000 rpm. The "
 "'Horsepower' field reads '12 watts', which is not a horsepower. A page that "
 "cannot keep two numbers straight is not a datasheet — this is the 775-is-a-can-"
 "size problem again, now with a source that disagrees with itself. Voltage "
 "range 12-24 V is the one figure both halves agree on.\n\n"
 "AND THIS IS THE REAL FINDING: Amazon is the most heavily swept vendor in this "
 "system, with 396 supplier parts. A 2024-01-07 order for a $27 item still "
 "produced no purchase order and no supplier part until it was entered by hand "
 "today. The gap is not an unknown vendor — it is a hole in the Amazon sweep "
 "itself, which is worse, because that is the channel everyone assumes is "
 "covered.")
Part.objects.filter(pk=PART).update(notes=(p.notes or "") + add)
assert "VENDOR RESOLVED" in Part.objects.get(pk=PART).notes, "notes did not stick"
print("OK  part notes corrected")
