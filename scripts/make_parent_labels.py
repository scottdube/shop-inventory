#!/usr/bin/env python3
"""Avery 5167/8167 labels for PARENT locations - the furniture, not the drawers.

Scott's point: a drawer label ends up on the top lip and vanishes the moment the
drawer is closed. So the cabinet itself has to say what its prefix means,
otherwise "AT-D1" is a code with nothing to decode it.

The prefix is derived from the children rather than stored anywhere - AT-D1,
AT-D2, AT-D3 share "AT-D", which trims at the last dash to "AT". That works for
every coded group in the shop (MC, RB, TC, WS1, A3, L1 ...) without adding a
field to the model that would then need maintaining.

    make_parent_labels.py --all --skip-rows 10 -o parents.html --commit
    make_parent_labels.py --names "Assembly & Test" -o at.html
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


def child_prefix(loc):
    """The code the children share, e.g. AT-D1/AT-D2 -> 'AT'. None if unlike."""
    names = [c.name for c in loc.children.all()]
    if len(names) < 2:
        return None
    common = os.path.commonprefix(names)
    if '-' not in common:
        return None
    return common.rsplit('-', 1)[0]


def qr_rects(data, size, x, y):
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


def label_svg(loc, prefix, x, y):
    """Prefix set large, full name under it, child range as the third line."""
    rects = qr_rects(f'LOC-{loc.pk}', L_H - 4, x + 2, y + 2)
    tx = x + (L_H - 4) + 6

    kids = sorted(c.name for c in loc.children.all())
    rng = f'{kids[0]} - {kids[-1]}' if len(kids) > 1 else (kids[0] if kids else '')

    # Where the location is already named by its code (A3, WS1, BL...), repeating
    # the name under it says nothing. Use the description's first clause instead -
    # "Top row, right" is what actually helps someone find the cabinet.
    code = prefix or loc.name[:6]
    if loc.name.strip().upper() == code.strip().upper():
        second = (loc.description or '').split('—')[0].split(' - ')[0].strip()
        second = second.rstrip('.,;') or loc.name
    else:
        second = loc.name

    t = [f'<text x="{tx:.1f}" y="{y + 19:.1f}" font-family="Helvetica,Arial" '
         f'font-size="16" font-weight="700" letter-spacing="0.5">'
         f'{esc(code)}</text>']
    t.append(f'<text x="{tx:.1f}" y="{y + 30:.1f}" font-family="Helvetica,Arial" '
             f'font-size="7" font-weight="600">{esc(second[:30])}</text>')
    if rng:
        t.append(f'<text x="{tx:.1f}" y="{y + L_H - 5:.1f}" '
                 f'font-family="Helvetica,Arial" font-size="5.2" fill="#666">'
                 f'{esc(rng[:34])}</text>')
    return rects + ''.join(t)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--all', action='store_true',
                    help='every location whose children share a code prefix')
    ap.add_argument('--names', help='comma-separated location names')
    ap.add_argument('--skip-rows', type=int, default=0)
    ap.add_argument('-o', '--out', default='parent_labels.html')
    ap.add_argument('--commit', action='store_true')
    args = ap.parse_args()

    rows = []
    if args.all:
        for loc in StockLocation.objects.all().order_by('name'):
            p = child_prefix(loc)
            if p:
                rows.append((loc, p))
    if args.names:
        for n in args.names.split(','):
            loc = StockLocation.objects.get(name=n.strip())
            rows.append((loc, child_prefix(loc)))
    if not rows:
        print('nothing to label')
        sys.exit(1)

    if args.commit:
        for loc, _ in rows:
            payload = f'LOC-{loc.pk}'
            if loc.barcode_data != payload:
                loc.assign_barcode(barcode_data=payload)
        print(f'assigned {len(rows)} location barcode(s)')

    cells = [None] * (args.skip_rows * COLS) + rows
    pages, i = [], 0
    while i < len(cells):
        chunk = cells[i:i + PER_PAGE]
        body = []
        for j, cell in enumerate(chunk):
            if cell is None:
                continue
            loc, prefix = cell
            c, r = j % COLS, j // COLS
            body.append(label_svg(loc, prefix, M_L + c * P_X, M_T + r * P_Y))
        pages.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{PAGE_W}" '
                     f'height="{PAGE_H}" viewBox="0 0 {PAGE_W} {PAGE_H}">'
                     f'<rect width="100%" height="100%" fill="#fff"/>'
                     + ''.join(body) + '</svg>')
        i += PER_PAGE

    html = ('<html><head><meta charset="utf-8"><title>Parent labels</title>'
            '<style>@page{size:letter;margin:0}body{margin:0}'
            'svg{display:block;page-break-after:always}</style></head><body>'
            + ''.join(pages) + '</body></html>')
    open(args.out, 'w').write(html)
    print(f'{len(rows)} label(s), {len(pages)} page(s), '
          f'{args.skip_rows} row(s) skipped -> {args.out}\n')
    for loc, prefix in rows:
        kids = loc.children.count()
        print(f'   {prefix or "-":<6} {loc.name[:34]:36} {kids:>3} children')


if __name__ == '__main__':
    main()
