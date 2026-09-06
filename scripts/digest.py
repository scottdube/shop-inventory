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
from stock.models import StockItem, StockLocation  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--count-loc", help="force this week's counting location")
ap.add_argument("--today", help="override the date, for testing")
ap.add_argument("--backup-status", metavar="PATH",
                help="override the backup verdict file (for testing the alarm)")
ap.add_argument("--html-out", metavar="PATH",
                help="write the HTML body to a file so it can be looked at before sending")
ap.add_argument("--email", metavar="ADDR",
                help="send the digest to this address instead of only printing it")
a = ap.parse_args()

TODAY = (datetime.date.fromisoformat(a.today) if a.today else datetime.date.today())
SITE = None
rows_hand, rows_count, rows_check = [], [], []
loc = None
backup_alarm = None


def q(x):
    """Quantities, without six decimal places of nothing.

    InvenTree stores quantities as Decimal, and Decimal PRESERVES SCALE - so
    format(Decimal('1.000000'), 'g') is '1.000000', not '1'. Casting to float
    first is what makes :g trim. Reads as 100, 0.5, 84 rather than 100.00000.
    """
    return f"{float(x):g}"


def link(kind, pk, text):
    """A bare pk is unlookupable; give the reader something to click."""
    return (kind, pk, text)


# ---------------- gather ---------------------------------------------------
from django.conf import settings  # noqa: E402
SITE = (getattr(settings, "SITE_URL", "") or "http://192.168.50.10:8001").rstrip("/")

low = sorted(((p_.total_stock, p_.minimum_stock, p_) for p_ in
              Part.objects.exclude(minimum_stock=0)
              if p_.total_stock < p_.minimum_stock), key=lambda r: r[0])
rows_hand.append(("parts below minimum", len(low), bool(low),
                  [(f"{q(h)}/{q(w)}" + ("  OUT" if h == 0 else ""),
                    link("part", pp.pk, pp.name)) for h, w, pp in low]))

od = [po for po in PurchaseOrder.objects.filter(status=20)
      if po.target_date and po.target_date < TODAY]
rows_hand.append(("purchase orders overdue", len(od), bool(od),
                  [(f"{(TODAY - po.target_date).days}d late",
                    link("po", po.pk, f"{po.reference} — {po.description[:44]}"))
                   for po in od]))

unclosed = [po for po in PurchaseOrder.objects.exclude(status__in=(30, 40, 50, 60))
            if po.lines.exists()
            and all(float(l.received) >= float(l.quantity) for l in po.lines.all())]
rows_hand.append(("received but not closed", len(unclosed), bool(unclosed),
                  [("", link("po", po.pk, f"{po.reference} — {po.description[:44]}"))
                   for po in unclosed]))

# backup heartbeat — age matters as much as the word, because a stopped job
# leaves its last OK in place forever
BSTAT = a.backup_status or os.path.expanduser("~/.inventree/last_backup_status")
try:
    verdict = open(BSTAT).read().strip()
    age_h = (datetime.datetime.now()
             - datetime.datetime.fromtimestamp(os.path.getmtime(BSTAT))).total_seconds() / 3600
    stale = age_h > 30
    bad = not verdict.startswith("OK")
    backup_alarm = "BACKUP STALE" if stale else "BACKUP FAILED" if bad else None
    rows_hand.append(("backup verdict", f"{age_h:.0f}h old", bool(backup_alarm),
                      [("", (None, None, verdict))]))
except FileNotFoundError:
    backup_alarm = "NO BACKUP STATUS"
    rows_hand.append(("backup verdict", "MISSING", True, []))

# ---------------- this week's count ----------------------------------------
uncounted = StockItem.objects.filter(stocktake_date__isnull=True, quantity__gt=0)
total_unc = uncounted.count()


def countable(si):
    """Would anyone actually stand in front of this and finish it?

    Capital equipment is qty 1 forever and counting it is theatre. A kit's
    contents graduate through use rather than getting tallied. A room is not a
    job; a drawer is.
    """
    if not si.location:
        return False
    if si.part.category and si.part.category.pathstring.startswith("Equipment"):
        return False
    l = si.location
    if l.parent is None or l.parent.parent is None:
        return False
    if "Kit -" in l.pathstring or "Kit-" in l.pathstring:
        return False
    return True


countables = [si for si in uncounted if countable(si)]
by_loc = Counter(si.location.pk for si in countables)
if a.count_loc:
    loc = StockLocation.objects.get(name=a.count_loc)
elif by_loc:
    loc = StockLocation.objects.get(pk=by_loc.most_common(1)[0][0])
if loc:
    rows_count = sorted([si for si in countables if si.location_id == loc.pk],
                        key=lambda s_: s_.part.name)

# ---------------- standing checks ------------------------------------------
orph = StockItem.objects.filter(location__isnull=True, belongs_to__isnull=True).count()
est = StockItem.objects.filter(notes__startswith="[ESTIMATE]").count()
contra = StockItem.objects.filter(notes__startswith="[ESTIMATE]",
                                  stocktake_date__isnull=False).count()
rows_check = [
    ("rows with no location at all", orph, orph > 0, "orphan_stock.py"),
    ("rows never counted", total_unc, False, ""),
    ("  ^ of those, worth counting", len(countables), False, "rest is capital equipment"),
    ("rows marked [ESTIMATE]", est, False, ""),
    ("  ^ self-contradicting", contra, contra > 0, "should be 0"),
    ("open build orders", Build.objects.filter(status=10).count(), False, ""),
    ("parts with a minimum set", Part.objects.exclude(minimum_stock=0).count(), False,
     f"of {Part.objects.count()} — only these can raise a warning"),
]

# ---------------- render: plain text ---------------------------------------
t = [f"SHOP DIGEST — {TODAY}", "=" * 34, "", "NEEDS A HAND", "-" * 12]
for label, val, alarm, items in rows_hand:
    t.append(f"  {label:<34} {str(val):>8}{'  <<' if alarm else ''}")
    for pre, (_k, _pk, text) in items:
        t.append(f"      {pre:<12} {text}")
t += ["", "THIS WEEK'S COUNT — one location, one walk", "-" * 42]
if loc:
    t.append(f"  {loc.pathstring}")
    t.append(f"  {len(rows_count)} row(s) here have never been counted:")
    for si in rows_count[:15]:
        t.append(f"      {q(si.quantity):>8}  {si.part.name[:50]}")
    if len(rows_count) > 15:
        t.append(f"      ... and {len(rows_count) - 15} more in the same place")
    t.append("")
    t.append(f"  Counting it moves the countable figure from {len(countables)} "
             f"to {len(countables) - len(rows_count)}.")
else:
    t.append("  nothing countable is uncounted — nice.")
t += ["", "STANDING CHECKS", "-" * 15]
for label, val, alarm, note in rows_check:
    t.append(f"  {label:<34} {val:>6}{'  <<' if alarm else ''}  {note}")
t += ["", "-- shop-inventory/scripts/digest.py"]
text = "\n".join(t)
print(text)


# ---------------- render: html ---------------------------------------------
URLS = {"part": "/web/part/%s", "po": "/web/purchasing/purchase-order/%s",
        "loc": "/web/stock/location/%s", "item": "/web/stock/item/%s"}
E = {"&": "&amp;", "<": "&lt;", ">": "&gt;"}


def esc(x):
    return "".join(E.get(c, c) for c in str(x))


def a_(kind, pk, text):
    if not kind:
        return esc(text)
    return (f'<a href="{SITE}{URLS[kind] % pk}" '
            f'style="color:#1a5fb4;text-decoration:none">{esc(text)}</a>')


F = "font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif"
h = [f'<div style="{F};font-size:14px;color:#1b1b1b;max-width:760px">']
h.append(f'<h2 style="margin:0 0 2px;font-size:19px">Shop digest</h2>'
         f'<div style="color:#666;font-size:13px;margin-bottom:18px">{TODAY}</div>')

h.append('<h3 style="font-size:15px;margin:22px 0 8px;padding-bottom:5px;'
         'border-bottom:2px solid #1b1b1b">Needs a hand</h3>')
h.append('<table cellpadding="0" cellspacing="0" style="width:100%;font-size:14px">')
for label, val, alarm, items in rows_hand:
    bg = "#fdeaea" if alarm else "#f4f8f4"
    mark = "&#9679;" if alarm else "&#10003;"
    col = "#b3261e" if alarm else "#2e7d32"
    h.append(f'<tr><td style="padding:7px 10px;background:{bg};border-radius:4px">'
             f'<span style="color:{col};font-weight:700">{mark}</span> {esc(label)}'
             f'<span style="float:right;font-weight:700;color:{col}">{esc(val)}</span></td></tr>')
    for pre, (k, pk, txt) in items:
        h.append(f'<tr><td style="padding:3px 10px 3px 30px;color:#444">'
                 f'<span style="color:#b3261e;font-weight:700">{esc(pre)}</span> '
                 f'{a_(k, pk, txt)}</td></tr>')
h.append('</table>')

h.append('<h3 style="font-size:15px;margin:26px 0 8px;padding-bottom:5px;'
         'border-bottom:2px solid #1b1b1b">This week&rsquo;s count</h3>')
if loc:
    h.append(f'<div style="margin-bottom:6px">One location, one walk: '
             f'{a_("loc", loc.pk, loc.pathstring)}</div>')
    h.append('<table cellpadding="0" cellspacing="0" style="width:100%;font-size:14px;'
             'border-collapse:collapse">')
    for i, si in enumerate(rows_count[:15]):
        z = "#fafafa" if i % 2 else "#fff"
        h.append(f'<tr style="background:{z}">'
                 f'<td style="padding:5px 10px;text-align:right;width:70px;'
                 f'font-variant-numeric:tabular-nums;color:#666">{q(si.quantity)}</td>'
                 f'<td style="padding:5px 10px">{a_("part", si.part.pk, si.part.name)}</td></tr>')
    h.append('</table>')
    if len(rows_count) > 15:
        h.append(f'<div style="color:#666;padding:6px 10px">&hellip; and '
                 f'{len(rows_count) - 15} more in the same place</div>')
    h.append(f'<div style="color:#666;margin-top:8px">Counting it moves the countable '
             f'figure from <b>{len(countables)}</b> to '
             f'<b>{len(countables) - len(rows_count)}</b>.</div>')
else:
    h.append('<div>nothing countable is uncounted &mdash; nice.</div>')

h.append('<h3 style="font-size:15px;margin:26px 0 8px;padding-bottom:5px;'
         'border-bottom:2px solid #1b1b1b">Standing checks</h3>')
h.append('<table cellpadding="0" cellspacing="0" style="width:100%;font-size:14px;'
         'border-collapse:collapse">')
for i, (label, val, alarm, note) in enumerate(rows_check):
    z = "#fafafa" if i % 2 else "#fff"
    c = "#b3261e" if alarm else "#1b1b1b"
    h.append(f'<tr style="background:{z}">'
             f'<td style="padding:5px 10px">{esc(label)}</td>'
             f'<td style="padding:5px 10px;text-align:right;font-weight:700;color:{c};'
             f'font-variant-numeric:tabular-nums;width:70px">{val}</td>'
             f'<td style="padding:5px 10px;color:#666;font-size:13px">{esc(note)}</td></tr>')
h.append('</table>')
h.append(f'<div style="color:#888;font-size:12px;margin-top:22px;border-top:1px solid #ddd;'
         f'padding-top:8px">shop-inventory/scripts/digest.py &middot; '
         f'<a href="{SITE}" style="color:#1a5fb4">{esc(SITE)}</a></div></div>')
html = "\n".join(h)

if a.html_out:
    with open(a.html_out, "w") as fh:
        fh.write("<!doctype html><meta charset=utf-8>"
                 "<body style='background:#fff;margin:24px'>" + html + "</body>")
    print(f"\n[html written to {a.html_out}]")

if a.email:
    from django.core.mail import EmailMultiAlternatives

    heads = []
    if backup_alarm:
        heads.append(backup_alarm)
    if low:
        outs = sum(1 for hv, _, _ in low if hv == 0)
        heads.append(f"{len(low)} below min" + (f" ({outs} OUT)" if outs else ""))
    if od:
        heads.append(f"{len(od)} PO overdue")
    if unclosed:
        heads.append(f"{len(unclosed)} PO unclosed")
    subject = f"Shop digest {TODAY} — " + ("; ".join(heads) if heads else "all clear")

    msg = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, [a.email])
    msg.attach_alternative(html, "text/html")
    n = msg.send()
    print(f"\n[emailed to {a.email}: send returned {n}]")
