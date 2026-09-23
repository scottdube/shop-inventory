"""2026-09-23  Merge the two live EC11 rotary encoder parts: 50 -> 200.

Same physical item on two rows. Part 50's own notes say "ASIN B07F24TRYG
recovered 2026-09-17" and its description carries "pack: 5"; part 200 carries
that same ASIN as its IPN and supplier part. Nothing was in doubt - they were
simply never merged after the ASIN was recovered onto 50.

SURVIVOR IS 200, not the better-named 50. 200 holds the stock (5 pieces received
today), the supplier part, the PO history and the home. 50 holds a name, a
category and a BOM reference - all of which move. Deactivating 200 instead would
orphan an open supplier part and a closed PO line, which is the expensive
direction.

50 is used in ONE BOM as a sub_part: BomItem 110 on Sim G1000 (1137), qty 3,
ref ENC-S. That line is repointed FIRST. Deactivating 50 without it would leave
the G1000 BOM pointing at an inactive part, and an inactive part with 0 stock
reads as a merge receipt, so the BOM would look satisfied by something retired.

The BOM note is preserved verbatim except for its "#50" reference, which is
rewritten to "#200" - a PK that no longer resolves to the live row is exactly
the unlookupable citation the shop rules warn about. The note's engineering
content (FSD specifies EC11E15244G1, 15mm knurled shaft, verify before
substituting) is NOT touched: it is still true of the surviving part.

Category moves to Electromechanical (pk 20), where the other rotary encoder
(446, E6B2-CWZ6C) already lives. Rejected leaving it in
Electronics/Passives/Potentiometers: an encoder is not a potentiometer, and the
Amazon listing title calling it a "Digital Potentiometer" is marketing, not the
part. Rejected Electronics/Electromechanical (pk 66, 3 parts) for the flat root
(pk 20, 20 parts), per the usual shadow-root rule here.

Name taken from 50 verbatim. Rejected composing a third, better name: this row
gets renamed once, today, and a name nobody has seen before is a new identity
rather than a merge.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()

from part.models import Part, PartCategory, BomItem
from stock.models import StockItem

COMMIT = "--commit" in sys.argv
LOSER, SURVIVOR, NEWCAT = 50, 200, 20

loser = Part.objects.get(pk=LOSER)
surv = Part.objects.get(pk=SURVIVOR)
cat = PartCategory.objects.get(pk=NEWCAT)
NEWNAME = loser.name

# --- safety: never merge away a row that still holds stock
loser_stock = StockItem.objects.filter(part=loser)
print("loser  [%s] %s" % (loser.pk, loser.name))
print("   active=%s stock_rows=%d total_stock=%s" % (loser.active, loser_stock.count(), loser.total_stock))
print("survivor [%s] %s" % (surv.pk, surv.name[:64]))
print("   active=%s total_stock=%s cat=%s" % (surv.active, surv.total_stock, surv.category.pathstring))
assert loser_stock.count() == 0 and loser.total_stock == 0, "loser holds stock - refusing"

boms = list(BomItem.objects.filter(sub_part=loser))
print("\nBOM lines to repoint: %d" % len(boms))
for bi in boms:
    print("   BomItem %s on [%s] %s  qty=%s ref=%r" % (bi.pk, bi.part.pk, bi.part.name[:40], bi.quantity, bi.reference))
    print("      note contains '#50': %s" % ("#%d" % LOSER in (bi.note or "")))

kw = sorted(set(
    [k.strip() for k in (surv.keywords or "").split(",") if k.strip()] +
    [k.strip() for k in (loser.keywords or "").split(",") if k.strip()]),
    key=str.lower)
NEWKW = ", ".join(kw)

MERGE_NOTE = (
    "\n\n---\n"
    "## Merged 2026-09-23\n\n"
    "Part #%d (\"%s\") was the same item on a second row and is now inactive as a\n"
    "merge receipt. Same ASIN B07F24TRYG on both. This row survived because it\n"
    "holds the stock, the supplier part and the PO history; #%d contributed the\n"
    "name, the category and the Sim G1000 BOM reference.\n\n"
    "### Notes carried over from #%d\n\n%s\n"
) % (LOSER, loser.name, LOSER, LOSER, (loser.notes or "(none)").strip())

print("\nPLAN")
print("  1. repoint %d BOM line(s) sub_part %d -> %d, rewriting '#%d' to '#%d' in the note"
      % (len(boms), LOSER, SURVIVOR, LOSER, SURVIVOR))
print("  2. part %d: name  -> %r" % (SURVIVOR, NEWNAME))
print("     part %d: cat   -> %s (pk %s)" % (SURVIVOR, cat.pathstring, cat.pk))
print("     part %d: kw    -> %s" % (SURVIVOR, NEWKW))
print("     part %d: notes += merge record (%d chars)" % (SURVIVOR, len(MERGE_NOTE)))
print("  3. part %d: name  -> %r, active -> False" % (LOSER, loser.name + " [merged]"))

if not COMMIT:
    print("\nDRY RUN — nothing written.")
    sys.exit(0)

# 1. BOM first
for bi in boms:
    bi.sub_part = surv
    if bi.note:
        bi.note = bi.note.replace("#%d" % LOSER, "#%d" % SURVIVOR)
    bi.save()
    bi.refresh_from_db()
    print("\n  BomItem %s -> sub_part %s (%s)" % (bi.pk, bi.sub_part_id, "OK" if bi.sub_part_id == SURVIVOR else "FAILED"))
    print("     note now references #%d: %s" % (SURVIVOR, "#%d" % SURVIVOR in (bi.note or "")))
    print("     note still references #%d: %s" % (LOSER, "#%d" % LOSER in (bi.note or "")))

# 2. survivor
surv.name = NEWNAME
surv.category = cat
surv.keywords = NEWKW
surv.notes = (surv.notes or "") + MERGE_NOTE
surv.save()
surv.refresh_from_db()
bad = []
if surv.name != NEWNAME: bad.append("name")
if surv.category_id != cat.pk: bad.append("category")
if surv.keywords != NEWKW: bad.append("keywords")
if "Merged 2026-09-23" not in (surv.notes or ""): bad.append("notes")
print("\n  survivor %d verified: %s" % (SURVIVOR, "OK" if not bad else "FAILED %s" % bad))

# 3. loser
loser.name = loser.name + " [merged]"
loser.active = False
loser.save()
loser.refresh_from_db()
bad = []
if not loser.name.endswith("[merged]"): bad.append("name")
if loser.active: bad.append("active")
print("  loser   %d verified: %s  (name=%r active=%s stock=%s)"
      % (LOSER, "OK" if not bad else "FAILED %s" % bad, loser.name[:60], loser.active, loser.total_stock))

print("\nREADBACK")
surv.refresh_from_db()
print("  [%s] %s" % (surv.pk, surv.name))
print("       cat=%s  stock=%s  home=%s" % (surv.category.pathstring, surv.total_stock,
      surv.default_location.pathstring if surv.default_location else "-"))
print("       http://192.168.50.10:8001/web/part/%s" % surv.pk)
print("  BOM lines now pointing at %d: %d" % (SURVIVOR, BomItem.objects.filter(sub_part=surv).count()))
print("  BOM lines still pointing at %d: %d" % (LOSER, BomItem.objects.filter(sub_part=loser).count()))
