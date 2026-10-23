"""Explode the LRD copies of the two ALLECIN kits into value stock, from their lids.

Scott photographed both kits at LRD on 2026-10-23 and said to assume they are
unused. That makes every quantity here CARD-STATED (tier 2, see
[[kit-count-evidence-tiers]]): 10 pcs per value printed on the lid, not
counted. Rows go in as `[ESTIMATE]` with **no stocktake date**, so the
never-counted report keeps surfacing them until someone counts a bin.

Why explode now and not leave the kit parts alone: #1 and #6 carry no stock
rows, so 490 parts at LRD read as zero to any search by value. That zero is
what nearly bought 330R/470R for the G1000 build (#1's notes). Seeding off the
lid removes the zero without anyone counting anything.

Each kit becomes a LOCATION inside LRD/Bench Wall/Cab2/Cab2-D3, where Scott
said all three kits are "for now" (2026-10-23). The EMGTMS ceramic kit (loc 471)
was filed at the LRD root only because no drawer was known; it moves into the
same drawer here, by .save() and not queryset .update(), which moves the FK and
leaves the MPTT tree and pathstring at the old place (TRAPS.md). Its 24 rows
gain the same "assume unused" line; their quantities stay card-stated.

Value resolution is by (value, voltage, BODY) for the electrolytics. The 4x7
and 5x11 versions of a value are different parts here and are not merged.
The lid writes 6x11 where the catalogue writes 6.3x11mm; that is the same
standard can, so those two resolve together. The resistors are 1/2W, and every
existing 1/2W-free part is 1/4W, so only 150R reuses a part (#949). The other 24
are new, because a 1/4W row would misstate the rating that G1000 build wants.

Idempotent: an existing kit location is reused, an existing part is matched by
exact name, and a part that already has a row at the kit is skipped.

    itq run scripts/seed_allecin_lrd.py            # dry run
    itq run scripts/seed_allecin_lrd.py --commit
"""
import argparse, os, re, sys, time, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.db import OperationalError, transaction
from part.models import Part, PartCategory
from stock.models import StockItem, StockLocation
from plugins.notes_compat import note_text, note_set, note_append

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

DRAWER = StockLocation.objects.get(pk=629)
assert DRAWER.pathstring == "LRD/Bench Wall/Cab2/Cab2-D3", DRAWER.pathstring
EMG = StockLocation.objects.get(pk=471)
CAPS = PartCategory.objects.get(pk=51)
RES = PartCategory.objects.get(pk=69)
PER = 10
TODAY = "2026-10-23"

# Transcribed from the lid photo, 2026-10-23: (uF, V, body on the lid)
ELEC = [("0.1", 50, "4x7"), ("0.22", 50, "5x11"), ("0.47", 50, "5x11"),
        ("1", 50, "5x11"), ("2.2", 50, "4x7"), ("3.3", 50, "4x7"),
        ("4.7", 50, "4x7"), ("10", 25, "4x7"), ("10", 50, "5x11"),
        ("22", 16, "4x7"), ("22", 25, "4x7"), ("33", 16, "4x7"),
        ("47", 10, "4x7"), ("47", 25, "5x11"), ("47", 50, "6x11"),
        ("100", 16, "5x11"), ("100", 25, "5x11"), ("220", 10, "5x11"),
        ("220", 25, "6x11"), ("330", 25, "8x12"), ("470", 10, "6x11"),
        ("470", 16, "8x12"), ("680", 16, "8x12"), ("1000", 16, "10x16")]

# Transcribed from the lid photo; same 25 as #1's notes (Amazon listing).
RVAL = ["1R", "2.2R", "3.3R", "10R", "22R", "47R", "68R", "100R", "120R",
        "150R", "220R", "330R", "470R", "560R", "680R", "1k", "2k", "2.2k",
        "4.7k", "5.6k", "10k", "22k", "47k", "100k", "1M"]

KITS = {
    "elec": dict(
        name="Kit - ALLECIN 24-Value Electrolytic",
        desc="ALLECIN 240pcs electrolytic kit, 24 values x 10 pcs, 10-50V, "
             "0.1-1000uF. Seen at LRD 2026-10-23 (lid photo); in Cab2-D3 "
             "for now (Scott). Kit part #6 (retired).",
        kit_part=6),
    "res": dict(
        name="Kit - ALLECIN 25-Value 1/2W Resistor",
        desc="ALLECIN 250pcs 1/2W 1% metal film kit, 25 values x 10 pcs, 1R-1M. "
             "Seen at LRD 2026-10-23 (lid photo); in Cab2-D3 for now (Scott). "
             "Kit part #1.",
        kit_part=1),
}


def body_key(b):
    """'6.3x11mm' and the lid's '6x11' are the same can."""
    b = b.lower().replace("mm", "").strip()
    return "6x11" if b == "6.3x11" else b


def ohms_text(v):
    m = re.fullmatch(r"([0-9.]+)([RkM])", v)
    n, u = m.groups()
    return f"{n} {'ohm' if u == 'R' else {'k': 'kohm', 'M': 'Mohm'}[u]}"


# Catalogue index for electrolytics: (uF, V, body) -> [parts], active only.
elec_ix = {}
for p in Part.objects.filter(name__istartswith="Capacitor Electrolytic"):
    m = re.fullmatch(r"Capacitor Electrolytic ([0-9.]+)uF (\d+)V \(([0-9.x]+(?:mm)?)\)", p.name)
    if m:
        elec_ix.setdefault((m.group(1), int(m.group(2)), body_key(m.group(3))), []).append(p)

plan = []   # (kit key, label, part or None, new-part kwargs, note)


def card_note(kit, detail):
    return (f"[ESTIMATE] Kit card claim: {kit}, **10 pcs per value** (printed on "
            f"the lid, not divided out). {detail}\n\n"
            f"NOT counted. Scott photographed the kit at LRD on {TODAY} and said "
            f"to assume it is unused, so this is the lid's number, not a tally. "
            f"Correct it on a physical count.")


for uf, v, body in ELEC:
    key = (uf, v, body_key(body))
    cands = elec_ix.get(key, [])
    act = [c for c in cands if c.active]
    label = f"{uf}uF {v}V ({body})"
    note = card_note("ALLECIN 240pcs 24-value electrolytic", f"{uf}uF {v}V, {body} body on the lid.")
    if len(act) > 1:
        plan.append(("elec", label, "AMBIGUOUS " + ", ".join(f"#{c.pk}" for c in act), None, note))
    elif act:
        plan.append(("elec", label, act[0], None, note))
    else:
        if cands:
            print(f"  ! {label}: only INACTIVE match(es) {[c.pk for c in cands]} — creating new anyway, check")
        plan.append(("elec", label, None, dict(
            name=f"Capacitor Electrolytic {uf}uF {v}V ({body})", category=CAPS,
            description=f"Aluminium electrolytic capacitor, {uf}uF {v}V, {body} body "
                        f"(as printed on the ALLECIN lid)."), note))

for rv in RVAL:
    name = f"Resistor {rv} 1% 1/2W"
    hits = list(Part.objects.filter(name=name))
    act = [h for h in hits if h.active]
    note = card_note("ALLECIN 250pcs 25-value 1/2W 1% metal film", f"{rv}, 1/2W, 9mm x 3mm body.")
    if len(act) > 1:
        plan.append(("res", rv, "AMBIGUOUS " + ", ".join(f"#{c.pk}" for c in act), None, note))
    elif act:
        plan.append(("res", rv, act[0], None, note))
    else:
        if hits:
            print(f"  ! {rv}: only INACTIVE {[h.pk for h in hits]} — creating new anyway, check")
        plan.append(("res", rv, None, dict(
            name=name, category=RES,
            description=f"Metal film resistor, {ohms_text(rv)}, 1% tolerance, 1/2W"), note))

locs = {k: StockLocation.objects.filter(parent=DRAWER, name=d["name"]).first() for k, d in KITS.items()}
bad = [p for p in plan if isinstance(p[2], str)]
for k, label, part, new, _ in plan:
    loc = locs[k]
    if isinstance(part, str):
        print(f"  STOP  {k:<4} {label:<18} {part}")
    elif part is None:
        print(f"  NEW   {k:<4} {label:<18} -> create {new['name']!r}")
    elif loc and StockItem.objects.filter(part=part, location=loc).exists():
        print(f"  have  {k:<4} {label:<18} -> #{part.pk} already at kit")
    else:
        print(f"  SEED  {k:<4} {label:<18} -> #{part.pk} {part.name}")
print(f"\n{sum(1 for p in plan if p[2] is None)} new parts, "
      f"{sum(1 for p in plan if isinstance(p[2], Part))} existing, {len(bad)} ambiguous; "
      f"locations: " + ", ".join(f"{k}={'[%d]' % l.pk if l else 'NEW'}" for k, l in locs.items()))

if bad:
    print("AMBIGUOUS VALUES — resolve before committing"); sys.exit(1)
if not a.commit:
    print("DRY RUN"); sys.exit(0)

# ---- write ----
for k, d in KITS.items():
    if locs[k] is None:
        locs[k] = StockLocation.objects.create(parent=DRAWER, name=d["name"], description=d["desc"])

def retry(fn, tries=7):
    """SQLite takes a database-wide write lock and the django-q worker polls it.
    Safe to retry only because every unit below is idempotent and atomic."""
    for i in range(tries):
        try:
            return fn()
        except OperationalError as e:
            if "locked" not in str(e).lower() or i == tries - 1:
                raise
            time.sleep(0.5 * (2 ** i))


def seed_one(k, part, new, note):
    loc = locs[k]
    with transaction.atomic():
        if part is None:
            part = Part.objects.filter(name=new["name"], active=True).first() or \
                Part.objects.create(component=True, purchaseable=True, default_location=loc, **new)
        s = StockItem.objects.filter(part=part, location=loc).first()
        fresh = s is None
        if fresh:
            s = StockItem.objects.create(part=part, location=loc, quantity=PER)
        if not note_text(s).startswith("[ESTIMATE]"):
            note_set(s, note)
        return fresh


made = 0
for k, label, part, new, note in plan:
    made += bool(retry(lambda: seed_one(k, part, new, note)))

EMG_DESC = ("EMGTMS Y&Z 24 Values 480pcs MLCC kit, 20 pcs per value, 50V, foot "
            "pitch 5.08mm. ASIN B0D2GVNDHY.\n\nIn LRD/Bench Wall/Cab2/Cab2-D3 since "
            f"{TODAY} (Scott: 'for now'). Was at the LRD root until then only "
            "because no drawer existed. Card photographed at LRD the same day; all "
            "24 values match the seeded rows. Scott said assume unused.")
def move_emg():
    if EMG.parent_id != DRAWER.pk:
        EMG.parent = DRAWER
        EMG.description = EMG_DESC
        EMG.save()
retry(move_emg)
EMG_LINE = (f"{TODAY}: Scott photographed this kit at LRD (in Cab2-D3) and said to "
            f"assume it is unused. Quantity stays the card's number, not a tally.")
for s in StockItem.objects.filter(location=EMG):
    if "assume it is unused" not in note_text(s):
        retry(lambda: note_append(s, EMG_LINE))

for k, d in KITS.items():
    kp = Part.objects.get(pk=d["kit_part"])
    marker = f"LRD COPY EXPLODED {TODAY}"
    if marker not in note_text(kp):
        retry(lambda: note_append(kp, f"=== {marker} ===\nThe LRD copy's values now live as stock "
                        f"in {locs[k].pathstring} (loc {locs[k].pk}), 10 pcs per value, "
                        f"[ESTIMATE] from the lid; Scott said assume unused. The SLN "
                        f"copy is NOT exploded and still reads as zero."))

# ---- verify by re-reading; .save() here has reported success and written nothing ----
fails = []
for k in KITS:
    for s in StockItem.objects.filter(location=locs[k]):
        why = []
        if int(s.quantity) != PER: why.append(f"qty={s.quantity}")
        if s.stocktake_date is not None: why.append("stocktake_date set")
        if not note_text(s).startswith("[ESTIMATE]"): why.append("note lacks [ESTIMATE] prefix")
        if why:
            fails.append((s.part.name, s.pk, "; ".join(why)))
for k, d in KITS.items():
    n = StockItem.objects.filter(location=locs[k]).count()
    want = len(ELEC) if k == "elec" else len(RVAL)
    print(f"[{locs[k].pk}] {locs[k].pathstring}: {n}/{want} rows")
    if n != want: fails.append((d["name"], None, f"{n} rows, want {want}"))
    if f"LRD COPY EXPLODED {TODAY}" not in note_text(Part.objects.get(pk=d["kit_part"])):
        fails.append((f"kit part #{d['kit_part']}", None, "note not written"))

e = StockLocation.objects.get(pk=471)
print(f"[471] {e.pathstring} level={e.level} parent={e.parent_id}")
if e.parent_id != DRAWER.pk or e.level != DRAWER.level + 1 \
        or not e.pathstring.startswith(DRAWER.pathstring + "/"):
    fails.append(("EMGTMS move", 471, f"parent={e.parent_id} level={e.level} path={e.pathstring}"))
emg_rows = list(StockItem.objects.filter(location=e))
missing = [s.pk for s in emg_rows if "assume it is unused" not in note_text(s)]
print(f"  EMGTMS rows {len(emg_rows)}, note line on {len(emg_rows) - len(missing)}")
if len(emg_rows) != 24 or missing:
    fails.append(("EMGTMS notes", None, f"rows={len(emg_rows)} missing={missing}"))

print(f"WROTE {made} new stock items this run")
if fails:
    print("VERIFY FAILED:")
    for f in fails: print("  ", f)
    sys.exit(1)
print("verified: every row qty 10 at its kit, [ESTIMATE], no stocktake date")
