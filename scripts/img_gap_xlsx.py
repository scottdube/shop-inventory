"""Write the imageless-parts backlog to an .xlsx for Scott to look through.

Scott, 2026-08-27, after the AliExpress reversal: *"provide a list of skus and
descriptions preferably in a spreadsheet so I can look."* The question behind it
is whether the other queue-A rulings-out share the mistake that one made —
"the SKU is not a product ID, therefore nothing can be looked up" — which was a
true observation and a false conclusion, because those 16 digits were an order
id. A count cannot be checked by eye; a list can.

Runs ON THE MINI (`itq run`) because that is where both the data and openpyxl
already are; the laptop's system python is PEP-668 managed and cannot install
into itself. Pull the result back with `itq pull`.

Four tabs: Summary, the three groups Scott asked about, everything else that
carries a SKU, and the 400-odd parts with no supplier part at all — the last of
which is the drawer walk's territory, not a scraping problem.
"""
import argparse
import os
import sys

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from openpyxl import Workbook                                    # noqa: E402
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side  # noqa: E402
from openpyxl.utils import get_column_letter                     # noqa: E402
from part.models import Part                                     # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--out", default="/tmp/imageless_parts.xlsx")
a = ap.parse_args()

WEB = "http://192.168.50.10:8001/web/part/{}/"

# The standing verdict per supplier, and WHAT ELIMINATED IT. A ruling without
# its evidence is just an opinion, and this file exists to be second-guessed.
RULING = {
    "Lakeshore Carbide": ("RULED OUT 2026-08-23 + 08-26",
        "Site carries only generic per-FAMILY photos; the LC/TAS SKUs appear nowhere on the site "
        "or in its sitemap. Real search is GET /search.aspx?find= (the stored /catalogsearch/ links "
        "were dead 404s). Endmill renders are 150x25px slivers, thread mills multi-match, drills no result."),
    "CNC Kitchen": ("RULED OUT 2026-08-23",
        "SKUs are synthetic ('SETXXL-M3 x 5.7'), derived from the kit packaging rather than being "
        "catalogue numbers, so there is nothing to search for."),
    "Amazon": ("RULED OUT 2026-08-26",
        "11 of 11 tested backlog ASINs return Amazon's real 404 - dead listings, not bot-blocks, "
        "calibrated against a known-live ASIN in the same browser. Note 21 OTHER Amazon parts were "
        "filled from order-details thumbnails, which survive listing death."),
    "McMaster-Carr": ("RULED OUT 2026-08-24",
        "Not present in order history at all - probably older than the site's display retention. "
        "The ImageCache URL embeds a GUID + timestamp, so unlike Haas it is NOT derivable from the "
        "SKU, and product-detail scraping is out of scope (login-gated)."),
    "Precise Bits": ("RULED OUT 2026-08-24 + 08-26",
        "Image URLs only partly derivable: /images/app-images/app-<SKU>.png hit 1 of 7 and is an "
        "application DIAGRAM, not a product photo. The ?s= search links return the homepage."),
    "Tormach": ("RULED OUT 2026-08-24 + 08-26",
        "/products/<SKU> is a soft 404 - identical body for all six. Magento SKU search is fuzzy: "
        "4 of 6 SKUs returned unrelated products, so they were skipped rather than guessed."),
    "AliExpress": ("REVERSED 2026-08-27 - 30 of 34 filled",
        "The remaining 4: three share ONE placeholder image hash across unrelated products (a "
        "delisting placeholder, rejected deliberately), and one order renders 'Please switch account'."),
    "Mouser Electronics": ("RULED OUT 2026-08-24",
        "The page yields a correct og:image URL but the image host is defended - it returns 13KB of "
        "text/html with a 200 status. Caught by file(1) before HTML was written into two image slots."),
    "DigiKey": ("SKIPPED DELIBERATELY 2026-08-24",
        "og:image for our C&K ILSTB25050 is a different actuator variant in the same series. "
        "Wrong-family photo; an empty slot is better."),
    "MSC Industrial Supply": ("NO PHOTO EXISTS 2026-08-24",
        "MSC's own og:image is an empty path for this item (Tapmatic)."),
}
ASKED = {"Lakeshore Carbide", "CNC Kitchen", "Amazon"}

HDR = Font(name="Arial", size=10, bold=True, color="FFFFFF")
HDRFILL = PatternFill("solid", fgColor="333333")
BODY = Font(name="Arial", size=10)
BOLD = Font(name="Arial", size=10, bold=True)
NOTE = Font(name="Arial", size=10, italic=True, color="666666")
TITLE = Font(name="Arial", size=12, bold=True)
THIN = Border(bottom=Side(style="thin", color="CCCCCC"))

NOIMG = Q(image="") | Q(image__isnull=True)
rows = []
for p in Part.objects.filter(NOIMG).distinct().order_by("pk").prefetch_related(
        "supplier_parts__supplier"):
    base = dict(pk=p.pk,
                category=p.category.pathstring if p.category else "",
                name=(p.name or "").replace("\n", " "),
                description=(p.description or "").replace("\n", " "),
                ipn=p.IPN or "",
                stock=float(p.total_stock),
                active="yes" if p.active else "NO")
    sps = list(p.supplier_parts.all())
    if not sps:
        rows.append(dict(base, supplier="", sku=""))
        continue
    for sp in sps:
        rows.append(dict(base, supplier=sp.supplier.name if sp.supplier else "?",
                         sku=sp.SKU or ""))

COLS = [("pk", 7), ("supplier", 20), ("sku", 30), ("name", 52), ("description", 62),
        ("category", 26), ("ipn", 14), ("stock", 8), ("active", 8), ("InvenTree", 42)]


def write_sheet(ws, subset, with_ruling):
    cols = COLS[:3] + [("ruling", 30), ("what eliminated it", 72)] + COLS[3:] \
        if with_ruling else COLS[:]
    for i, (h, w) in enumerate(cols, 1):
        c = ws.cell(row=1, column=i, value=h)
        c.font, c.fill = HDR, HDRFILL
        c.alignment = Alignment(vertical="center")
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{len(subset) + 1}"

    wrap = (5, 6, 7) if with_ruling else (4, 5)
    for r, row in enumerate(subset, 2):
        vals = [row["pk"], row["supplier"], row["sku"]]
        if with_ruling:
            vals += list(RULING.get(row["supplier"], ("", "")))
        vals += [row["name"], row["description"], row["category"], row["ipn"],
                 row["stock"], row["active"], WEB.format(row["pk"])]
        for i, v in enumerate(vals, 1):
            c = ws.cell(row=r, column=i, value=v)
            c.font = BODY
            c.alignment = Alignment(vertical="top", wrap_text=i in wrap)
            c.border = THIN


wb = Workbook()
ws = wb.active
ws.title = "Summary"
ws["A1"] = "Parts with no image in InvenTree - 2026-08-27"
ws["A1"].font = TITLE
blurb = [
    f"{len({r['pk'] for r in rows})} of {Part.objects.count()} parts have no image. Most of them have no "
    "supplier part at all, so there is no SKU to look anything up with - those are the drawer walk's "
    "territory, not a scraping problem.",
    "The ones that DO carry a SKU are on the other tabs. 'Asked about' holds the three groups whose "
    "ruling-out used the same reasoning the AliExpress reversal just disproved: the SKU is not a product "
    "ID, therefore nothing can be looked up. That was true of AliExpress too - and those 16 digits turned "
    "out to be an order id.",
]
for i, text in enumerate(blurb, start=2):
    ws.cell(row=i, column=1, value=text).font = NOTE
    ws.merge_cells(start_row=i, start_column=1, end_row=i, end_column=6)
    ws.cell(row=i, column=1).alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[i].height = 32

for i, (h, w) in enumerate(zip(
        ["supplier", "imageless", "as built", "asked about?", "ruling", "what eliminated it"],
        [24, 12, 11, 14, 30, 86]), 1):
    c = ws.cell(row=5, column=i, value=h)
    c.font, c.fill = HDR, HDRFILL
    ws.column_dimensions[get_column_letter(i)].width = w

sups = sorted({r["supplier"] for r in rows if r["supplier"]},
              key=lambda s: (-sum(1 for r in rows if r["supplier"] == s), s))
r = 6
for s in sups:
    verdict, why = RULING.get(s, ("", ""))
    ws.cell(row=r, column=1, value=s).font = BODY
    # Counted from the data tabs by formula, not precomputed in Python, so the
    # summary stays true if rows are filtered or deleted.
    ws.cell(row=r, column=2, value=(
        f"=COUNTIF('Asked about'!$B:$B,$A{r})+COUNTIF('Other with a SKU'!$B:$B,$A{r})")).font = BODY
    # Column C is the same count as a plain number. Neither machine here has
    # LibreOffice, so the formulas in column B could not be recalculated before
    # delivery: they populate when Excel or Numbers opens the file, and read
    # blank in Quick Look. An unverifiable formula next to a verified constant
    # is honest; a blank cell that looks like a zero is not.
    ws.cell(row=r, column=3,
            value=sum(1 for x in rows if x["supplier"] == s)).font = BODY
    ws.cell(row=r, column=4, value="YES" if s in ASKED else "").font = BODY
    ws.cell(row=r, column=5, value=verdict).font = BODY
    c = ws.cell(row=r, column=6, value=why)
    c.font, c.alignment = BODY, Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[r].height = 44
    r += 1

ws.cell(row=r, column=1, value="no supplier part at all").font = NOTE
ws.cell(row=r, column=2, value="=COUNTA('No supplier part'!$A:$A)-1").font = BODY
ws.cell(row=r, column=3, value=sum(1 for x in rows if not x["supplier"])).font = BODY
ws.cell(row=r, column=6,
        value="No SKU exists, so there is nothing to look up. Photograph at the drawer instead.").font = NOTE
r += 1
ws.cell(row=r, column=1, value="TOTAL rows").font = BOLD
ws.cell(row=r, column=2, value=f"=SUM(B6:B{r - 1})").font = BOLD
ws.cell(row=r, column=3, value=len(rows)).font = BOLD

asked = sorted([x for x in rows if x["supplier"] in ASKED], key=lambda x: (x["supplier"], x["pk"]))
other = sorted([x for x in rows if x["supplier"] and x["supplier"] not in ASKED],
               key=lambda x: (x["supplier"], x["pk"]))
none_ = sorted([x for x in rows if not x["supplier"]], key=lambda x: (x["category"], x["pk"]))

write_sheet(wb.create_sheet("Asked about"), asked, True)
write_sheet(wb.create_sheet("Other with a SKU"), other, True)
write_sheet(wb.create_sheet("No supplier part"), none_, False)

wb.save(a.out)
print(f"wrote {a.out}: asked={len(asked)} other={len(other)} no_supplier={len(none_)}")
