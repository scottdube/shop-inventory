"""Seed the EMGTMS 24-value ceramic kit at LRD from its printed card.

The kit is in Florida; Scott is in New Hampshire. Nobody can count it, so the
card is the only authority available and every line goes in as `[ESTIMATE]`
with **no stocktake date** — the never-counted report keeps surfacing it until
someone stands in front of the box.

Why the card and not division: unlike the EAONE resistor kit (850/30 = 28, a
derived number), the EMGTMS card states 20 pcs per value outright for all 24.
That is still a claim about a box nobody has opened, not a count, so it earns
the same `[ESTIMATE]` treatment — but it is not arithmetic invented here.

Why stock lands on parts whose `default_location` is elsewhere: 11 of the 24
values are shared with the BOJACK kit and the loose bags at A3-R8C3, so their
home is those drawers. A part is stocked where it physically sits;
`default_location` says where a *spare* goes home. Both are true at once.

Idempotent: a value that already has a stock item at the kit location is left
alone, so a partial run can simply be re-run.

    itq run scripts/seed_emgtms.py            # dry run
    itq run scripts/seed_emgtms.py --commit
"""
import argparse, os, re, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part
from stock.models import StockItem, StockLocation

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

KIT_PK = 471
PER_VALUE = 20

# Transcribed from the EMGTMS card; same list as ceramic_apply.py, which
# created the 13 values that were not already in the catalog.
EMGTMS = [(10, "10"), (22, "22"), (30, "30"), (47, "47"), (100, "101"),
          (220, "221"), (330, "331"), (470, "471"), (1_000, "102"),
          (2_200, "222"), (3_300, "332"), (4_700, "472"), (6_800, "682"),
          (10_000, "103"), (22_000, "223"), (47_000, "473"), (68_000, "683"),
          (100_000, "104"), (220_000, "224"), (470_000, "474"),
          (1_000_000, "105"), (2_200_000, "225"), (4_700_000, "475"),
          (10_000_000, "106")]

UNIT = {"pf": 1, "nf": 1000, "uf": 1_000_000}


def canon(pf):
    if pf < 1000:
        v, u = pf, "pF"
    elif pf < 1_000_000:
        v, u = pf / 1000, "nF"
    else:
        v, u = pf / 1_000_000, "uF"
    return f"{v:.10g}{u}"


def parse(name):
    m = re.search(r"Capacitor Ceramic\s+([0-9.]+)\s*(pF|nF|uF)", name, re.I)
    return int(round(float(m.group(1)) * UNIT[m.group(2).lower()])) if m else None


def note(code):
    return (f"[ESTIMATE] Kit card claim: EMGTMS Y&Z, 24 values, 480 pcs, "
            f"**20 pcs per value** (stated on the card, not divided out), 50 V, "
            f"marking {code}. ASIN B0D2GVNDHY.\n\n"
            f"NOT counted — the kit is at LRD and has never been opened in "
            f"front of anyone recording it. Whether it is new or has been drawn "
            f"from is unknown. Correct this on a physical count.")


kit = StockLocation.objects.get(pk=KIT_PK)
print(f"kit: [{kit.pk}] {kit.pathstring}\n")

# Index the catalog by capacitance so the shared values resolve to the same
# part the rest of the system already uses.
by_val = {}
for p in Part.objects.filter(name__istartswith="Capacitor Ceramic", active=True):
    pf = parse(p.name)
    if pf is not None:
        by_val.setdefault(pf, []).append(p)

missing, existing, planned = [], [], []
for pf, code in EMGTMS:
    cands = by_val.get(pf, [])
    if not cands:
        missing.append((pf, code))
        continue
    if len(cands) > 1:
        print(f"  ! {canon(pf)} matches {len(cands)} active parts "
              f"({', '.join('#%d' % c.pk for c in cands)}) — skipped, resolve first")
        missing.append((pf, code))
        continue
    p = cands[0]
    if StockItem.objects.filter(part=p, location=kit).exists():
        existing.append((pf, code, p))
    else:
        planned.append((pf, code, p))

for pf, code, p in planned:
    print(f"  SEED  {canon(pf):<8} code {code:<4} -> #{p.pk} {p.name}")
for pf, code, p in existing:
    print(f"  have  {canon(pf):<8} code {code:<4} -> #{p.pk} (stock item already at kit)")
for pf, code in missing:
    print(f"  MISS  {canon(pf):<8} code {code:<4} — no single active part")

print(f"\n{len(planned)} to seed, {len(existing)} already present, "
      f"{len(missing)} unresolved, of {len(EMGTMS)} card values")

if not a.commit:
    print("DRY RUN")
    sys.exit(0)

# ---- write, then verify every row by re-reading it ----
# .save() on this install has reported success and written nothing, so a write
# is not done until the database agrees it happened.
made, bad = [], []
for pf, code, p in planned:
    s = StockItem.objects.create(part=p, location=kit, quantity=PER_VALUE,
                                 notes=note(code))
    made.append((pf, code, p, s.pk))

for pf, code, p, pk in made:
    s = StockItem.objects.filter(pk=pk).first()
    why = []
    if s is None:
        why.append("row absent")
    else:
        if s.location_id != KIT_PK:
            why.append(f"location={s.location_id}")
        if int(s.quantity) != PER_VALUE:
            why.append(f"qty={s.quantity}")
        if s.stocktake_date is not None:
            why.append(f"stocktake_date={s.stocktake_date} (must be unset)")
        if "[ESTIMATE]" not in (s.notes or ""):
            why.append("notes missing [ESTIMATE]")
    if why:
        bad.append((canon(pf), pk, "; ".join(why)))

print(f"\nWROTE {len(made)} stock items at {kit.pathstring}")
if bad:
    print("VERIFY FAILED:")
    for name, pk, why in bad:
        print(f"  {name} item {pk}: {why}")
    sys.exit(1)
print(f"verified {len(made)}/{len(made)}: qty {PER_VALUE}, at the kit, "
      f"[ESTIMATE], no stocktake date")
