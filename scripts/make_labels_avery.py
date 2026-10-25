"""Drawer address labels laid out for Avery 5167 / 8167.

Akro-Mils drawers have no label window, so these are peel-and-stick. 5167 is
1/2" x 1-3/4", 80 to a sheet, which clears every drawer front with margin:

    10164 (A cabinets)   front 2-1/4  x 1-5/8
    10144 (B cabinets)   small 2-7/32 x 1-9/16   large 4-9/16 x 2-3/16

Die-cut, so nothing gets trimmed by hand or lasered. The label carries the
ADDRESS only - a place, not contents - plus a QR of the same plain text so any
phone reads it and binscan can use it directly.

Avery 5167 geometry (inches):
    label      1.75 x 0.5
    grid       4 across x 20 down
    margins    left 0.3125, top 0.5
    pitch      2.0625 horizontal, 0.5 vertical (rows are contiguous)
"""

import argparse
import pathlib

import segno

IN = 96.0  # px per inch at 96dpi

L_W, L_H = 1.75 * IN, 0.5 * IN
M_L, M_T = 0.3125 * IN, 0.5 * IN
P_X, P_Y = 2.0625 * IN, 0.5 * IN
COLS, ROWS = 4, 20
PAGE_W, PAGE_H = 8.5 * IN, 11 * IN
PER_PAGE = COLS * ROWS

LAYOUT_64 = [(r, 8) for r in range(1, 9)]
LAYOUT_44 = [(r, 8) for r in range(1, 5)] + [(r, 4) for r in range(5, 8)]
# Akro-Mils 10124, the A0/B0 pair hung 2026-08-25: 24 drawers, 6 rows of 4, all
# large. Column ZERO — they hang to the LEFT of A1/B1, so nothing renumbers.
LAYOUT_24 = [(r, 4) for r in range(1, 7)]


def qr_rects(data, size, x, y):
    # make_qr, NOT make: segno.make() picks Micro QR (M3, 15x15) for a string
    # this short, and iPhone's camera silently refuses to decode Micro QR.
    # Forcing a standard symbol gives version 1, 21x21, which every phone reads.
    qr = segno.make_qr(data, error="m")
    m = [list(r) for r in qr.matrix]
    n = len(m)
    cell = size / n
    out = []
    for r, row in enumerate(m):
        run = None
        for c, v in enumerate(row + [0]):
            if v and run is None:
                run = c
            elif not v and run is not None:
                out.append(f'<rect x="{x + run * cell:.2f}" y="{y + r * cell:.2f}" '
                           f'width="{(c - run) * cell:.2f}" height="{cell:.2f}"/>')
                run = None
    return "".join(out)


def one(addr, x, y, qr=True, guides=False):
    parts = []
    if guides:
        parts.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{L_W:.2f}" '
                     f'height="{L_H:.2f}" fill="none" stroke="#e0e0e0" stroke-width="0.4"/>')
    pad = L_H * 0.10
    tx = x + pad
    if qr:
        # tighter margin on the QR than on the text: a 21x21 symbol on a 1/2"
        # label only clears 0.53 mm per module, and module size is the whole
        # game for scan reliability. The white label stock is its quiet zone.
        qpad = L_H * 0.06
        q = L_H - 2 * qpad
        parts.append(f'<g fill="#000">{qr_rects(addr, q, x + qpad, y + qpad)}</g>')
        tx = x + qpad + q + pad * 1.2
    fs = L_H * 0.44
    parts.append(
        f'<text x="{tx:.2f}" y="{y + L_H / 2 + fs * 0.35:.2f}" '
        f'font-family="Helvetica,Arial,sans-serif" font-size="{fs:.2f}" '
        f'font-weight="700" fill="#000">{addr}</text>')
    return "".join(parts)


def addresses(cabs, layout):
    return [f"{c}-R{r}C{col}" for c in cabs for r, cols in layout
            for col in range(1, cols + 1)]


def row(group):
    """Pad a group to whole sheet rows, so each cabinet starts on a fresh row."""
    return group + [None] * (-len(group) % COLS)


def lrd():
    """LRD: the Cab1-Cab8 bench wall, then Akro cabinets F0 (10124) and F1/F2 (10164).

    Cabinet-level labels first (one per cabinet frame), then each cabinet's
    levels on rows of their own. 224 slots = 3 sheets, blanks included.
    Names must exist in InvenTree with barcode_data set, or the QR scans to
    nothing: make_lrd_akro_1025.py does both.
    """
    out = row([f"Cab{n}" for n in range(1, 9)] + ["F0", "F1", "F2"])
    out += row([f"Cab1-S{s}" for s in range(1, 4)])
    for n in (2, 3, 4):
        out += row([f"Cab{n}-D{d}" for d in range(1, 6)])
    for n in (5, 6, 7, 8):
        out += row([f"Cab{n}-S{s}" for s in range(1, 6)])
    out += addresses(["F0"], LAYOUT_24)
    out += addresses(["F1", "F2"], LAYOUT_64)
    return out


def pages(addrs, qr, guides):
    out = []
    for i in range(0, len(addrs), PER_PAGE):
        chunk = addrs[i:i + PER_PAGE]
        body = [one(a, M_L + (j % COLS) * P_X, M_T + (j // COLS) * P_Y, qr, guides)
                for j, a in enumerate(chunk) if a]
        out.append(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{PAGE_W:.0f}" '
            f'height="{PAGE_H:.0f}" viewBox="0 0 {PAGE_W:.0f} {PAGE_H:.0f}">'
            f'<rect width="100%" height="100%" fill="#fff"/>{"".join(body)}</svg>')
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default="top",
                    choices=["top", "bottom", "col0", "all", "lrd"],
                    help="top=A1-A3, bottom=B1-B3, col0=A0/B0 (all = these three); "
                         "lrd = LRD Cab1-Cab8 + Akro F0-F2")
    ap.add_argument("--no-qr", action="store_true")
    ap.add_argument("--guides", action="store_true", help="faint label outlines")
    a = ap.parse_args()

    addrs = []
    if a.set in ("top", "all"):
        addrs += addresses(["A1", "A2", "A3"], LAYOUT_64)
    if a.set in ("bottom", "all"):
        addrs += addresses(["B1", "B2", "B3"], LAYOUT_44)
    if a.set in ("col0", "all"):
        addrs += addresses(["A0", "B0"], LAYOUT_24)
    if a.set == "lrd":
        addrs += lrd()
    # 8167 is the inkjet twin of 5167, same die-cut; LRD's pack is 8167.
    stock = "8167" if a.set == "lrd" else "5167"

    ps = pages(addrs, not a.no_qr, a.guides)
    for i, svg in enumerate(ps, 1):
        pathlib.Path(f"avery{stock}_{a.set}_p{i}.svg").write_text(svg)
        # An HTML wrapper as well, because the sheet gets PRINTED FROM CHROME and
        # a bare SVG is treated as an image: Chrome fits it to the printable area
        # and every label lands a few millimetres off its die-cut. @page pins the
        # media to Letter with zero margin, and the fixed px box holds the sheet
        # at exactly 1:1. Open the .html, not the .svg.
        pathlib.Path(f"avery{stock}_{a.set}_p{i}.html").write_text(
            "<!doctype html><meta charset=utf-8>"
            f"<title>Avery {stock} — {a.set} sheet {i}</title>"
            "<style>@page{size:8.5in 11in;margin:0}"
            "html,body{margin:0;padding:0}"
            f"svg{{display:block;width:{PAGE_W:.0f}px;height:{PAGE_H:.0f}px}}"
            "@media screen{body{background:#e9e9e9}"
            "svg{box-shadow:0 2px 12px rgba(0,0,0,.25);margin:12px auto}}"
            "</style>" + svg)

    used = sum(1 for x in addrs if x)
    print(f"{used} labels -> {len(ps)} sheet(s) of Avery {stock} (80/sheet)")
    print(f"  label 1.75 x 0.5 in, QR={'no' if a.no_qr else 'yes'}")
    for i in range(1, len(ps) + 1):
        print(f"  avery{stock}_{a.set}_p{i}.html   <- open THIS in Chrome to print")
        print(f"  avery{stock}_{a.set}_p{i}.svg")
    print("  Chrome: Cmd-P, Margins NONE, Scale 100% (not 'Fit to page'),")
    print("          headers/footers OFF. Print one on plain paper and hold it")
    print("          against a blank Avery sheet before committing a sheet.")
    if len(addrs) % PER_PAGE:
        print(f"  last sheet uses {len(addrs) % PER_PAGE} of {PER_PAGE} slots")


if __name__ == "__main__":
    main()
