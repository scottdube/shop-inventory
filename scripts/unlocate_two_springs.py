"""Retract the location on two spring rows. They were never located or counted.

Scott 2026-08-26, on the 302 stainless compression and the small compression:
"neither of these were located or counted."

WHAT I DID WRONG. Scott said "they're all there that we talked about this
afternoon". Three springs had been on the bench and handled; two had only been
DISCUSSED. I noticed the ambiguity, reasoned about it explicitly, and resolved
it by filing all five while withholding stocktake_date from the two -- calling
them "located but not counted".

That compromise was still a false claim. **Withholding the count did not make
the location true.** I split one uncertain assertion into two fields and
recorded the half I had no evidence for, which is worse than recording nothing:
a null location says "unknown" out loud, while a location says a person put it
there.

The irony is on the record: in the same script I deliberately EXCLUDED the
music-wire loop-end springs because "all there" could not include a part fitted
to the pedals, and wrote that sweeping it in "is the exact failure mode of a
bulk operation reading a casual 'all'." Then did it to the other two.

**THE RULE THAT WOULD HAVE CAUGHT IT: "all" from a person covers what they
handled, not what was mentioned.** When a bulk instruction is ambiguous, apply
it to the narrow reading and ASK about the remainder. The narrow reading here
was three rows and one question.

Reverted to location=NULL. The rows return to being honestly unknown.
"""
import argparse, os, sys, time, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.db.utils import OperationalError
from stock.models import StockItem

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

def retry(fn, what, tries=6):
    for i in range(tries):
        try:
            return fn()
        except OperationalError as e:
            if "locked" not in str(e).lower() or i == tries - 1:
                raise
            print(f"  locked on {what}, retry {i+1}")
            time.sleep(0.5 * (2 ** i))

ROWS = {1001: "302 stainless compression, 1 in",
        1002: "small compression, 0.938 in x 0.188 in OD"}

for pk, what in ROWS.items():
    si = StockItem.objects.filter(part_id=pk).first()
    print(f"  {what}: {si.quantity:g} @ {si.location.name if si.location else 'UNLOCATED'}")

if not a.commit:
    print("\nDRY RUN -- add --commit")
    sys.exit()

for pk, what in ROWS.items():
    si = StockItem.objects.filter(part_id=pk).first()
    def clear(si=si):
        si.location = None
        si.save()
    retry(clear, f"unlocate {pk}")
    retry(lambda si=si, what=what: StockItem.objects.filter(pk=si.pk).update(
        notes=(si.notes or "").rstrip() +
        "\n\n**LOCATION RETRACTED 2026-08-26.** Scott: \"neither of these were "
        "located or counted.\"\n\n"
        "This row was filed to B2-R7C1 minutes earlier on a reading of \"they're "
        "all there that we talked about this afternoon\". Three springs had been "
        "on the bench and handled; this one had only been DISCUSSED. The "
        "ambiguity was noticed and resolved the wrong way — filed with the "
        "stocktake_date withheld, described as 'located but not counted'.\n\n"
        "Withholding the count did not make the location true. A null location "
        "says UNKNOWN out loud; a location says a person put it there. Recording "
        "the half there was no evidence for is worse than recording nothing.\n\n"
        f"Still owned, still {si.quantity:g} on the books from PO-0122's line "
        "quantity in 2023 — a purchase figure, not a count — and genuinely "
        "unlocated. B2-R7C1 remains its default_location: that is where it goes, "
        "not where it is."), f"note {pk}")

print("\nverify:")
for pk, what in ROWS.items():
    si = StockItem.objects.filter(part_id=pk).first()
    print(f"  {what}: {si.quantity:g} @ {si.location.name if si.location else 'UNLOCATED'} "
          f"stocktake={si.stocktake_date}")
from stock.models import StockLocation
cell = StockLocation.objects.get(pk=289)
print(f"\nsprings cell now holds {StockItem.objects.filter(location=cell).count()} rows")
print(f"unlocated rows with stock: "
      f"{StockItem.objects.filter(location__isnull=True, quantity__gt=0).count()}")
