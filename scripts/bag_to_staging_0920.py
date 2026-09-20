"""Move the G1000 build #3 kit from MC-T3 to SLN/Florida Staging, and check
the one florida earmark whose reason was deleted today.

Scott, 2026-09-20: the Florida bag is a physical bag on the bench, being
filled from MC-T3 as the drawer is emptied. The eight rows still reading
MC-T3 are in that bag, not in the drawer - so the record is describing a
drawer that is nearly empty as though it were full.

Florida Staging (loc 503) already exists for exactly this and says so:
"Boxes packed at SLN and bound for LRD. Stock here is still owned and still
counted - it has just left the shelf." Using it empties MC-T3 to zero rows,
which is the stated goal of this whole pass.

Also inspects row 125 (#634 Resistor 10k), whose florida earmark was created
for the mux pull-up at shield footprint R2 - a line REMOVED from the BOM
earlier today after Peter confirmed the pull-up is on the mux module. The
earmark is only cleared if the recorded reason actually names that, because
an earmark with some other justification is not mine to drop.
"""
import os, sys, django
from datetime import date
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from stock.models import StockItem, StockLocation
from django.contrib.auth import get_user_model

COMMIT = "--commit" in sys.argv
MCT3 = StockLocation.objects.get(pk=432)
BAG = StockLocation.objects.get(pk=503)
user = get_user_model().objects.filter(is_superuser=True).first()

rows = list(StockItem.objects.filter(location=MCT3).order_by('pk'))
print("=== moving %d rows: MC-T3 -> %s ===" % (len(rows), BAG.pathstring))
for si in rows:
    print("  %s [%s] %-50s qty=%s florida=%s"
          % (si.pk, si.part.pk, si.part.name[:50], si.quantity,
             'florida' in list(si.tags.names())))
notag = [si for si in rows if 'florida' not in list(si.tags.names())]
print("  rows WITHOUT the florida tag: %s" % ([si.pk for si in notag] or "none"))

r125 = StockItem.objects.get(pk=125)
why = (r125.metadata or {}).get('florida', {}).get('why', '')
print()
print("=== row 125 [#634] Resistor 10k - earmark reason ===")
print("  %r" % why)
stale = any(w in why.lower() for w in ('mux', 'pull-up', 'pullup', 'r2'))
print("  names the removed mux pull-up? %s -> %s"
      % (stale, "CLEAR IT" if stale else "LEAVE IT ALONE"))

if not COMMIT:
    print("\nDRY RUN - add --commit")
    sys.exit()

for si in rows:
    si.location = BAG
    si.save()

if stale:
    md = dict(r125.metadata or {})
    md.pop('florida', None)
    md['florida_dropped'] = {
        'was': why, 'on': str(date.today()),
        'why': ('BOM line removed 2026-09-20 - the only 10k on G1000 build #3 '
                'was the mux pull-up at shield footprint R2, and Peter '
                'confirmed the pull-up is already on the mux module. Kept '
                'here rather than deleted so the earmark can be restored if '
                'the R2 question reopens.')}
    r125.metadata = md
    r125.save()
    r125.tags.remove('florida')

left = StockItem.objects.filter(location=MCT3)
print("\nMC-T3 now holds %d rows" % left.count())
for si in left:
    print("   STILL THERE: %s [%s] %s" % (si.pk, si.part.pk, si.part.name))
print("Florida Staging now holds %d rows:" % StockItem.objects.filter(location=BAG).count())
for si in StockItem.objects.filter(location=BAG).order_by('pk'):
    print("   %s [%s] %-48s qty=%s" % (si.pk, si.part.pk, si.part.name[:48], si.quantity))
r125 = StockItem.objects.get(pk=125)
print("\nrow 125 tags=%s  metadata keys=%s"
      % (list(r125.tags.names()), sorted((r125.metadata or {}).keys())))
ok = (left.count() == 0 and (not stale or 'florida' not in list(r125.tags.names())))
print("VERIFIED" if ok else "MISMATCH - stop and look")
