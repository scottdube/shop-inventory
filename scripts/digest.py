#!/usr/bin/env python3
"""Weekly shop digest — what needs a hand, and one walk's worth of counting.

Built 2026-09-06 after Scott asked whether email could carry anything useful.
It can: the measurement that prompted this found BOTH label rolls at zero stock
on the day 25 labels were printed. LABELLING.md already warned that discovering
that mid-run, at night, is how an evening disappears.

DESIGN NOTES, because the obvious version of this is worse than useless:

**It does not list 310 never-counted rows.** A number that large does not move
because you looked at it, and a list nobody can finish is a list nobody opens.
It names ONE LOCATION and the rows in it, which is a job with an end.

**It picks a location, not N items.** A trip out costs about the same whatever
you do when you get there, so five items scattered across five rooms is five
trips. One drawer is one walk. See the trip-cost rule in memory.

**Standing checks report as TRENDS, not lists.** Orphan rows and pack
mismatches are real and slow-moving; printing 27 lines every week trains you to
skip the whole message.

**Normal has a uniform shape so abnormal breaks it** — the instrument-panel
principle. Every section prints even when it is clean, and clean says "0" in the
same column position, so the eye finds the odd one without reading.

    itq run scripts/digest.py
    itq run scripts/digest.py --count-loc B3-R2C1   # force a location
"""
import argparse
import datetime
import os
import sys
from collections import Counter

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from build.models import Build  # noqa: E402
from order.models import PurchaseOrder  # noqa: E402
from part.models import Part  # noqa: E402
from stock.models import StockItem  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--count-loc", help="force this week's counting location")
ap.add_argument("--today", help="override the date, for testing")
ap.add_argument("--email", metavar="ADDR",
                help="send the digest to this address instead of only printing it")
a = ap.parse_args()

TODAY = (datetime.date.fromisoformat(a.today) if a.today else datetime.date.today())
W = 46
out = []


def head(t):
    out.append("")
    out.append(t)
    out.append("-" * len(t))


def row(label, value, flag=""):
    out.append(f"  {label:<{W}} {value:>5}{flag}")


out.append(f"SHOP DIGEST — {TODAY}")
out.append("=" * 34)

# ---------------- 1. things that cost money or time if ignored ------------
head("NEEDS A HAND")

low = sorted(((p.total_stock, p.minimum_stock, p) for p in
              Part.objects.exclude(minimum_stock=0)
              if p.total_stock < p.minimum_stock), key=lambda r: r[0])
row("parts below minimum", len(low), "  <<" if low else "")
for have, want, p in low:
    urgent = " OUT" if have == 0 else ""
    out.append(f"      {have:g}/{want:g}{urgent:<5} {p.name[:52]}")

od = [po for po in PurchaseOrder.objects.filter(status=20)
      if po.target_date and po.target_date < TODAY]
row("purchase orders overdue", len(od), "  <<" if od else "")
for po in od:
    days = (TODAY - po.target_date).days
    out.append(f"      {days}d late  {po.reference}  {po.description[:40]}")

# a PO fully received but never closed reads as outstanding forever
unclosed = [po for po in PurchaseOrder.objects.exclude(status__in=(30, 40, 50, 60))
            if po.lines.exists()
            and all(float(l.received) >= float(l.quantity) for l in po.lines.all())]
row("received but not closed", len(unclosed), "  <<" if unclosed else "")
for po in unclosed:
    out.append(f"      {po.reference}  {po.description[:44]}")

# ---------------- 2. one walk's worth of counting -------------------------
head("THIS WEEK'S COUNT — one location, one walk")

uncounted = StockItem.objects.filter(stocktake_date__isnull=True, quantity__gt=0)
total_unc = uncounted.count()


def countable(si):
    """Is this row something anyone would ever cycle count?

    The first run of this script picked SLN/Machine Shop with 46 rows and called
    it "one walk". Those rows are a Tormach 1100MX, a 15L lathe, operator
    consoles and printed manuals. Capital equipment is qty 1 and stays qty 1;
    counting it is theatre, and putting it at the top of a weekly email is how
    the email stops being read.

    Two filters, both about the SHAPE of the thing rather than its name:

      - not in the Equipment category tree
      - in a real CONTAINER, not an area. A location one level under a site
        (SLN/Machine Shop) is a room. Three levels down (SLN/Bin Wall/B3/B3-R2C1)
        is a drawer you can stand in front of and finish.
    """
    if not si.location:
        return False
    cat = si.part.category
    if cat and cat.pathstring.startswith("Equipment"):
        return False
    l = si.location
    if l.parent is None or l.parent.parent is None:
        return False
    # An assortment kit's contents are the LEAST worthwhile thing to count.
    # The second run of this script proposed a 30-value resistor kit - about 840
    # resistors - which is precisely the work rejected for the four screw kits on
    # 2026-08-31. A kit is one unit; its sizes GRADUATE into parts as they get
    # used and counted for a job. Proposing it as a weekly chore would contradict
    # a convention written the same week, and nobody would do it twice.
    if "Kit -" in l.pathstring or "Kit-" in l.pathstring:
        return False
    return True


countables = [si for si in uncounted if countable(si)]
by_loc = Counter(si.location.pk for si in countables)
if a.count_loc:
    from stock.models import StockLocation
    loc = StockLocation.objects.get(name=a.count_loc)
elif by_loc:
    from stock.models import StockLocation
    loc = StockLocation.objects.get(pk=by_loc.most_common(1)[0][0])
else:
    loc = None

if loc:
    rows = [si for si in countables if si.location_id == loc.pk]
    out.append(f"  {loc.pathstring}")
    out.append(f"  {len(rows)} row(s) here have never been counted:")
    SHOW = 15
    for si in sorted(rows, key=lambda s_: s_.part.name)[:SHOW]:
        out.append(f"      {si.quantity:>8g}  {si.part.name[:50]}")
    if len(rows) > SHOW:
        out.append(f"      ... and {len(rows) - SHOW} more in the same place")
    out.append("")
    out.append(f"  Counting this drawer moves the countable never-counted figure")
    out.append(f"  from {len(countables)} to {len(countables) - len(rows)}.")
else:
    out.append("  nothing countable is uncounted — nice.")

# ---------------- 3. slow-moving standing checks, as numbers --------------
head("STANDING CHECKS (trend — run the script for the list)")

orph = StockItem.objects.filter(location__isnull=True, belongs_to__isnull=True).count()
row("rows with no location at all", orph, "   orphan_stock.py")
row("rows never counted", total_unc, "")
row("  ^ of those, worth counting", len(countables),
    "   rest is capital equipment")
est = StockItem.objects.filter(notes__startswith="[ESTIMATE]").count()
bad = StockItem.objects.filter(notes__startswith="[ESTIMATE]",
                               stocktake_date__isnull=False).count()
row("rows marked [ESTIMATE]", est, "")
row("  ^ self-contradicting", bad, "  <<" if bad else "   should be 0")
row("open build orders", Build.objects.filter(status=10).count(), "")
row("parts with a minimum set", Part.objects.exclude(minimum_stock=0).count(),
    f" of {Part.objects.count()}")

out.append("")
out.append("  Only the enrolled parts can ever trigger a low-stock warning.")
out.append("  Enrolling a consumable is what makes the first line of this")
out.append("  digest able to see it at all.")

out.append("")
out.append("-- shop-inventory/scripts/digest.py")

text = "\n".join(out)
print(text)

if a.email:
    from django.conf import settings
    from django.core.mail import send_mail

    # Subject carries the headline so the inbox list is readable without opening
    # it. A digest whose subject is always the same word gets filed unread.
    heads = []
    if low:
        outs = sum(1 for have, _, _ in low if have == 0)
        heads.append(f"{len(low)} below min" + (f" ({outs} OUT)" if outs else ""))
    if od:
        heads.append(f"{len(od)} PO overdue")
    if unclosed:
        heads.append(f"{len(unclosed)} PO unclosed")
    subject = f"Shop digest {TODAY} — " + ("; ".join(heads) if heads else "all clear")

    n = send_mail(subject=subject, message=text,
                  from_email=settings.DEFAULT_FROM_EMAIL,
                  recipient_list=[a.email], fail_silently=False)
    print(f"\n[emailed to {a.email}: send_mail returned {n}]")
