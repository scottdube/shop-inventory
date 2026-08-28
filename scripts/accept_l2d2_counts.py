"""L2-D2: Scott accepts the purchase counts, none used. Drop the [ESTIMATE].

Scott 2026-08-28: "l2D2 go with counts from purchase none used."

TIER CHANGE, NOT A COUNT. The evidence tiers here are tallied > card-stated >
divided > accepted, and only the middle two carry [ESTIMATE]. These were seeded
card-stated, with the standing caveat that a kit may already have been drawn
from. "None used" removes exactly that caveat: the packs are intact, so the
purchase figure IS the current figure and the marker no longer applies.

STILL NO stocktake_date. Nobody counted anything — accepting a figure is not
tallying it, and stamping a date would claim a count that never happened. Same
call as scripts/receive_sleeve.py, where Scott accepted 15 m off the pack label
and the row deliberately got no stocktake date.

Applies to L2-D2 ONLY. The L1-D2 hardware kits stay [ESTIMATE]: the T-nut box
is visibly OPEN in the photo with loose nuts in it, so its 120 is still an
upper bound.

    itq run scripts/accept_l2d2_counts.py            # dry run
    itq run scripts/accept_l2d2_counts.py --commit
"""
import argparse, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part                                     # noqa: E402
from stock.models import StockItem, StockLocation                # noqa: E402

ACCEPTED = (
 "ACCEPTED COUNT — Scott, 2026-08-28: \"go with counts from purchase, none "
 "used.\" The quantity is the purchase/pack figure and the pack is intact, so "
 "it is the current figure and not an upper bound. NO [ESTIMATE] marker: that "
 "marks a figure somebody should check, and this one has been checked as far as "
 "it usefully can be.\n\n"
 "NO stocktake_date all the same. Accepting a figure is not tallying it, and a "
 "date would claim a count that never happened.")

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

loc = StockLocation.objects.get(name__iexact="L2-D2")
rows = list(StockItem.objects.filter(location=loc).select_related("part"))
print(f"{loc.pathstring}: {len(rows)} catalogued row(s)")
for s in rows:
    has = (s.notes or "").startswith("[ESTIMATE]")
    print(f"  [{s.pk}] {float(s.quantity):>4g}x {s.part.name[:46]:48} "
          f"{'[ESTIMATE]' if has else '(clean)'}  stocktake={s.stocktake_date}")
if not a.commit:
    raise SystemExit("\nDRY RUN — add --commit")

for s in rows:
    n = (s.notes or "")
    n = n.replace("[ESTIMATE] ", "").replace("[ESTIMATE]", "")
    n = ACCEPTED + "\n\n" + n.lstrip()
    # the holders line is now sharper, not softer: none used means they exist
    n = n.replace(
        "Either they were used, or they are elsewhere in the box.",
        "Scott says none used, which means they SHOULD still be in the box — so "
        "'used' is ruled out and 'elsewhere in the box' is the live answer. "
        "Worth one look.")
    StockItem.objects.filter(pk=s.pk).update(notes=n)
    p = Part.objects.get(pk=s.part_id)
    pn = (p.notes or "").replace("[ESTIMATE] ", "").replace("[ESTIMATE]", "")
    Part.objects.filter(pk=p.pk).update(notes=ACCEPTED + "\n\n" + pn.lstrip())
    f = StockItem.objects.get(pk=s.pk)
    # startswith, NEVER `in`. The acceptance text above contains the literal
    # string "[ESTIMATE]" while explaining that it does not apply, and a
    # substring test flags it. docs/TRAPS.md, twice now.
    assert not (f.notes or "").startswith("[ESTIMATE]"), f"[{s.pk}] marker survived"
    assert "ACCEPTED COUNT" in f.notes, f"[{s.pk}] acceptance did not stick"
    assert f.stocktake_date is None, f"[{s.pk}] something stamped a stocktake date"
    print(f"OK  [{s.pk}] {s.part.name[:44]} — accepted, no marker, no date")
