"""#977 went into the sim rudder pedals. Zero it, and correct BO-0015's status.

Scott 2026-08-26: "I believe nine seventy seven actually got used on the rudder
pedals in the simulator."

That answers why it never surfaced in the wire-shelf walk: it is not on a shelf,
it is in the machine.

IT ALSO CORRECTS BO-0015, CREATED AN HOUR AGO SAYING "parts gathered, not
built". Wrong -- the pedals are PARTIALLY BUILT. Springs are fitted. The damper
sits on a shop-printed mount that was made for it. That is assembly, not
gathering, and "paused mid-build" is a different thing to plan around than
"paused before starting".

AND THE DESIGN NOW READS. The damper's note already said "a spring alone would
oscillate; the adjustable damping knob is the reason that part was chosen over a
fixed strut" -- written before anyone knew where the springs were. #977 is that
spring: extension springs return the pedals to centre, the damper stops them
ringing about it. Centring force and damping force are two different jobs and
the parts for both were bought.

Zeroed rather than deleted, and delete_on_deplete cleared FIRST -- taking a row
to zero with that flag set destroys the row and the explanation with it, which
happened to stock 522 earlier today.
"""
import argparse, os, sys, django, datetime

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model
from part.models import Part
from stock.models import StockItem
from build.models import Build

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

user = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
si = StockItem.objects.filter(part_id=977).first()
bo = Build.objects.get(reference="BO-0015")
print(f"[977] qty={si.quantity:g} loc={si.location or 'UNLOCATED'} depl={si.delete_on_deplete}")
print(f"target build: {bo.reference} {bo.title}")

if not a.commit:
    print("\nDRY RUN -- add --commit")
    sys.exit()

StockItem.objects.filter(pk=si.pk).update(delete_on_deplete=False)
si.refresh_from_db()
if si.quantity > 0:
    si.take_stock(si.quantity, user,
                  notes="Used on the sim rudder pedals (BO-0015). Scott, 2026-08-26.")
if not StockItem.objects.filter(pk=si.pk).exists():
    sys.exit("row was deleted despite the flag -- stop and investigate")

StockItem.objects.filter(pk=si.pk).update(
    stocktake_date=datetime.date(2026, 8, 26),
    notes=("COUNTED 0 — correct, and not an error. Scott, 2026-08-26: used on "
           "the rudder pedals in the flight simulator (BO-0015).\n\n"
           "This row had read 'unlocated' since the McMaster import and had been "
           "hunted for all afternoon. It was never on a shelf: it is in the "
           "machine.\n\n"
           "DO NOT let #1132 satisfy a future call for this part. The P-9602 "
           "retail card is 15/32 in against this 1/2 in, same length, same loop "
           "ends — and zinc-plated rather than music wire, so it takes a set "
           "under sustained load. On rudder pedals that means the centring "
           "force fades. If these need replacing, replace them with music "
           "wire.\n\n"
           "The row stays at zero with this note rather than being deleted: a "
           "zero with an explanation is a fact."))

Part.objects.filter(pk=977).update(notes=(Part.objects.get(pk=977).notes or "").rstrip() +
    "\n\nCONSUMED ON BO-0015, SIM RUDDER PEDALS, per Scott 2026-08-26. Stock is "
    "zero and the reason is on the row. The 'STILL UNSEEN' note above is "
    "superseded — it was never lost, it was fitted.")

Build.objects.filter(pk=bo.pk).update(notes=(bo.notes or "").rstrip() +
    "\n\n**PARTIALLY BUILT, corrected 2026-08-26.** This record was created the "
    "same day saying 'parts are being gathered'. Wrong: assembly has happened. "
    "#977, a pair of McMaster music-wire extension springs, is FITTED to the "
    "pedals, and the damper #1129 sits on a shop-printed mount made for it.\n\n"
    "'Paused mid-build' is a different thing to plan around than 'paused before "
    "starting' — the next session is picking up a partial assembly, not opening "
    "a box.\n\n"
    "THE DESIGN, now that both halves are known: the extension springs return "
    "the pedals to centre and the damper stops them ringing about it. Centring "
    "force and damping force are two separate jobs, and parts for both were "
    "bought. The damper's own note argued a spring alone would oscillate — "
    "written before anyone knew where the spring was.")

si.refresh_from_db()
print(f"\n[977] qty={si.quantity:g} exists={StockItem.objects.filter(pk=si.pk).exists()} "
      f"stocktake={si.stocktake_date}")
print(f"unlocated rows with stock: "
      f"{StockItem.objects.filter(location__isnull=True, quantity__gt=0).count()}")
