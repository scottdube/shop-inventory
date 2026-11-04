"""Section 3 of docs/consumable-flag-draft.md: 16 owned tools and 4 components that sat in
Consumables with component=True. Scott 2026-11-04: "Yes, move them".

1. Merge the two duplicates. The SURVIVOR is the Amazon-imported record (#445, #309), not
   the hand-made Equipment record (#91, #85): the import carries the supplier part, the IPN
   and the purchase-history note, and the merge rule refuses to retire a part that has a
   supplier part. So the survivor takes the Equipment record's cleaner name and category,
   keywords are unioned, the loser's note (#85's ASIN-recovery story) is appended to the
   survivor, and the Equipment record is retired with the MERGED prefix.
2. Move the remaining tools into Equipment/Soldering or Equipment/Hand Tools and the 4
   components to Switches / Prototyping.
3. component=False on every tool (they are never built into anything).

No stock rows are created: 13 of these tools have none, and only Scott can say which he
owns and where. Writes are queryset .update() plus a re-read of every row.
Dry run by default.  itq run scripts/move_section3_tools_1104.py [--commit]"""
import os, sys
sys.path.insert(0, os.getcwd()); os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
import django; django.setup()
from part.models import Part, PartCategory
from plugins.notes_compat import note_text, note_append

COMMIT = "--commit" in sys.argv
CATS = {"SOLDER": (39, "Equipment/Soldering"), "TEST": (38, "Equipment/Test Equipment"),
        "HAND": (40, "Equipment/Hand Tools"), "SW": (33, "Switches"), "PROTO": (27, "Prototyping")}
for key, (pk, path) in CATS.items():
    got = PartCategory.objects.get(pk=pk).pathstring
    assert got == path, f"category {pk} is {got!r}, expected {path!r}"

# (survivor, loser, category key)
MERGES = [(445, 91, "SOLDER"), (309, 85, "TEST")]
MOVES = {"SOLDER": [314, 311, 474, 407, 201, 438, 316, 353, 315, 364, 209],
         "HAND": [853, 1490, 492], "SW": [141, 421], "PROTO": [396, 334]}
TOOLS = set(MOVES["SOLDER"] + MOVES["HAND"] + [s for s, _, _ in MERGES])
assert len(TOOLS) == 16

# ---- merges: refusal checks first
plan = []
for live_pk, dead_pk, cat in MERGES:
    live, dead = Part.objects.get(pk=live_pk), Part.objects.get(pk=dead_pk)
    assert dead.active, f"#{dead_pk} already retired"
    assert dead.stock_items.count() == 0, f"#{dead_pk} has stock rows"
    assert dead.supplier_parts.count() == 0, f"#{dead_pk} has supplier parts"
    assert dead.get_descendants().count() == 0, f"#{dead_pk} has variants"
    assert dead.used_in.count() == 0, f"#{dead_pk} is used in a BOM"
    seen, kws = set(), []
    for k in (live.keywords or "").split(",") + (dead.keywords or "").split(","):
        k = k.strip()
        if k and k.lower() not in seen:
            seen.add(k.lower()); kws.append(k)
    kw = ", ".join(kws)
    dnote = note_text(dead)
    plan.append((live, dead, cat, kw, dnote))
    print(f"MERGE #{dead_pk} -> #{live_pk}  [{CATS[cat][1]}]")
    print(f"   name  {live.name[:70]!r}\n      -> {dead.name!r}")
    print(f"   kw    {len((live.keywords or '').split(','))} + {len((dead.keywords or '').split(','))} -> {len(kws)}")
    print(f"   note  carry {len(dnote)} chars from #{dead_pk}" if dnote else "   note  none to carry")

for cat, pks in MOVES.items():
    print(f"\nMOVE -> {CATS[cat][1]}")
    for p in Part.objects.filter(pk__in=pks).select_related("category").order_by("pk"):
        print(f"   #{p.pk:5} [{p.category.pathstring}] comp={p.component} {p.name[:60]}")

if not COMMIT:
    print("\nDRY RUN - nothing written"); sys.exit(0)

# ---- write
for live, dead, cat, kw, dnote in plan:
    n = Part.objects.filter(pk=live.pk).update(name=dead.name, keywords=kw, category_id=CATS[cat][0])
    assert n == 1
    if dnote and dnote[:40] not in note_text(Part.objects.get(pk=live.pk)):
        note_append(Part.objects.get(pk=live.pk),
                    f"Merged 2026-11-04 from part #{dead.pk} (hand-made Equipment record). Its note:\n\n{dnote}")
    marker = f"MERGED into part #{live.pk} ({dead.name}). "
    if not (dead.description or "").startswith("MERGED into"):
        Part.objects.filter(pk=dead.pk).update(active=False, description=(marker + (dead.description or ""))[:250])
for cat, pks in MOVES.items():
    Part.objects.filter(pk__in=pks).update(category_id=CATS[cat][0])
Part.objects.filter(pk__in=TOOLS).update(component=False)

# ---- re-read every row
bad = []
for live, dead, cat, kw, dnote in plan:
    l, d = Part.objects.get(pk=live.pk), Part.objects.get(pk=dead.pk)
    if l.name != dead.name or l.category_id != CATS[cat][0] or l.keywords != kw or l.component:
        bad.append(f"survivor #{l.pk}")
    if dnote and dnote[:40] not in note_text(l):
        bad.append(f"note on #{l.pk}")
    if d.active or not d.description.startswith("MERGED into"):
        bad.append(f"loser #{d.pk}")
for cat, pks in MOVES.items():
    for pk, cid, comp in Part.objects.filter(pk__in=pks).values_list("pk", "category_id", "component"):
        if cid != CATS[cat][0] or (pk in TOOLS and comp):
            bad.append(f"#{pk}")
print("re-read problems:", bad or "none")
print("VERDICT:", "SUCCESS" if not bad else "FAILED")
