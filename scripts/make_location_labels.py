#!/usr/bin/env python3
"""Avery 5167/8167 labels for STOCK LOCATIONS.

InvenTree's built-in stocklocation template is 50 x 20 mm, which is not any
Avery sheet Scott owns - that mismatch is why the generated PDFs looked wrong.
This uses the same 1.75 x 0.5 in geometry as the part labels, which printed
correctly.

    make_location_labels.py --parent "Mobile Cart" --skip-rows 7 -o mc.html --commit

QR payload is LOC-<pk>, assigned to the location barcode with --commit so a scan
resolves in InvenTree. The location NAME is set large and first: at half an inch
tall the thing that has to survive a glance from three feet away is "MC-T4", not
the breadcrumb.
"""
import argparse
import os
import sys

import django
import segno

sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()

from stock.models import StockLocation  # noqa: E402

IN = 96.0
L_W, L_H = 1.75 * IN, 0.5 * IN
M_L, M_T = 0.3125 * IN, 0.5 * IN
P_X, P_Y = 2.0625 * IN, 0.5 * IN
COLS, ROWS = 4, 20
PAGE_W, PAGE_H = 8.5 * IN, 11 * IN
PER_PAGE = COLS * ROWS


def qr_rects(data, size, x, y):
    """make_qr, not make - make() drops to Micro QR for short payloads and
    phone cameras refuse to decode those."""
    qr = segno.make_qr(data, error='m')
    m = [list(r) for r in qr.matrix]
    n = len(m)
    pad = size * 0.06
    mod = (size - 2 * pad) / n
    out = []
    for r in range(n):
        c = 0
        while c < n:
            if m[r][c]:
                run = 1
                while c + run < n and m[r][c + run]:
                    run += 1
                out.append(
                    f'<rect x="{x + pad + c * mod:.2f}" y="{y + pad + r * mod:.2f}" '
                    f'width="{mod * run:.2f}" height="{mod:.2f}" fill="#000"/>')
                c += run
            else:
                c += 1
    return ''.join(out)


def esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def label_svg(loc, x, y):
    payload = f'LOC-{loc.pk}'
    qr_size = L_H - 4
    rects = qr_rects(payload, qr_size, x + 2, y + 2)
    tx = x + qr_size + 6

    parent = loc.parent.name if loc.parent else ''
    desc = (loc.description or '').split('.')[0][:30]

    t = [f'<text x="{tx:.1f}" y="{y + 20:.1f}" font-family="Helvetica,Arial" '
         f'font-size="15" font-weight="bold">{esc(loc.name)}</text>']
    if parent:
        t.append(f'<text x="{tx:.1f}" y="{y + 31:.1f}" font-family="Helvetica,Arial" '
                 f'font-size="6.8" fill="#333">{esc(parent)}</text>')
    if desc:
        t.append(f'<text x="{tx:.1f}" y="{y + L_H - 5:.1f}" '
                 f'font-family="Helvetica,Arial" font-size="5.6" fill="#666">'
                 f'{esc(desc)}</text>')
    return rects + ''.join(t)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--parent', help='label every child of this location')
    ap.add_argument('--names', help='comma-separated location names')
    ap.add_argument('--skip-rows', type=int, default=0)
    ap.add_argument('-o', '--out', default='location_labels.html')
    ap.add_argument('--commit', action='store_true')
    args = ap.parse_args()

    locs = []
    if args.parent:
        p = StockLocation.objects.get(name=args.parent)
        locs += list(p.children.all().order_by('name'))
    if args.names:
        for n in args.names.split(','):
            locs.append(StockLocation.objects.get(name=n.strip()))
    if not locs:
        print('nothing to label'); sys.exit(1)

    if args.commit:
        for loc in locs:
            payload = f'LOC-{loc.pk}'
            if loc.barcode_data != payload:
                loc.assign_barcode(barcode_data=payload)
        print(f'assigned {len(locs)} location barcode(s)')

    cells = [None] * (args.skip_rows * COLS) + locs
    pages, i = [], 0
    while i < len(cells):
        chunk = cells[i:i + PER_PAGE]
        body = []
        for j, loc in enumerate(chunk):
            if loc is None:
                continue
            c, r = j % COLS, j // COLS
            body.append(label_svg(loc, M_L + c * P_X, M_T + r * P_Y))
        pages.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{PAGE_W}" '
                     f'height="{PAGE_H}" viewBox="0 0 {PAGE_W} {PAGE_H}">'
                     f'<rect width="100%" height="100%" fill="#fff"/>'
                     + ''.join(body) + '</svg>')
        i += PER_PAGE

    html = ('<html><head><meta charset="utf-8"><title>Location labels</title>'
            '<style>@page{size:letter;margin:0}body{margin:0}'
            'svg{display:block;page-break-after:always}</style></head><body>'
            + ''.join(pages) + '</body></html>')
    open(args.out, 'w').write(html)
    print(f'{len(locs)} label(s), {len(pages)} page(s), '
          f'{args.skip_rows} row(s) skipped -> {args.out}')
    for loc in locs:
        print(f'   LOC-{loc.pk:<5} {loc.name}')


if __name__ == '__main__':
    main()
