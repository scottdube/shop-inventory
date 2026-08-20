#!/usr/bin/env python3
"""Extract a bill of materials from a KiCad 6+ .kicad_sch file.

    kicad_bom.py board.kicad_sch
    kicad_bom.py --compare dir/          # every variant side by side

THE TRAP: a .kicad_sch contains a `(lib_symbols ...)` block holding the library
DEFINITION of every symbol used, in the same `(symbol ...)` shape as the placed
instances. Parse naively and every part appears twice — once as a definition
with no real reference designator, once as the thing actually on the board. This
skips the lib_symbols span by paren-matching before looking at anything else.

Power symbols (#PWR), net ties and graphical items carry references starting
with '#' and are excluded: they are schematic bookkeeping, not parts to buy.
"""
import argparse
import os
import re
import sys
from collections import defaultdict


def span(text, start):
    """End index of the s-expression opening at `start`, respecting strings."""
    depth, i, in_str = 0, start, False
    while i < len(text):
        c = text[i]
        if in_str:
            if c == '\\':
                i += 2
                continue
            if c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return len(text)


PROP = re.compile(r'\(property\s+"([^"]+)"\s+"([^"]*)"')


def parse(path):
    text = open(path, encoding='utf-8', errors='replace').read()

    # excise the library definitions before doing anything else
    m = re.search(r'\(lib_symbols\b', text)
    if m:
        text = text[:m.start()] + text[span(text, m.start()):]

    parts = []
    for m in re.finditer(r'\(symbol\b', text):
        body = text[m.start():span(text, m.start())]
        props = dict(PROP.findall(body))
        ref = props.get('Reference', '')
        if not ref or ref.startswith('#'):
            continue                      # power flags, net ties, graphics
        parts.append(dict(ref=ref, value=props.get('Value', ''),
                          footprint=props.get('Footprint', ''),
                          desc=props.get('Description', '')))
    return parts


def rows(parts):
    """Collapse to one row per (value, footprint) with the refs listed."""
    g = defaultdict(list)
    for p in parts:
        g[(p['value'], p['footprint'])].append(p['ref'])
    out = []
    for (value, fp), refs in g.items():
        out.append(dict(qty=len(refs), value=value, footprint=fp,
                        refs=', '.join(sorted(refs))))
    return sorted(out, key=lambda r: (-r['qty'], r['value']))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('target')
    ap.add_argument('--compare', action='store_true',
                    help='treat target as a directory of variants')
    args = ap.parse_args()

    if not args.compare:
        parts = parse(args.target)
        print(f'{len(parts)} placed component(s) in '
              f'{os.path.basename(args.target)}\n')
        print(f'{"QTY":>3}  {"VALUE":24} {"FOOTPRINT":38} REFS')
        print('-' * 100)
        for r in rows(parts):
            print(f'{r["qty"]:>3}  {r["value"][:24]:24} '
                  f'{r["footprint"][:38]:38} {r["refs"][:28]}')
        return

    # KiCad writes autosaves into .history/ — same schematic, older revision.
    # Including them makes a five-variant project look like six.
    SKIP = {'.history', 'backup', 'backups', '_autosave'}
    found = []
    for dirpath, dirs, files in os.walk(args.target):
        dirs[:] = [d for d in dirs if d not in SKIP and not d.startswith('.')]
        for f in files:
            if f.endswith('.kicad_sch'):
                found.append(os.path.join(dirpath, f))
    if not found:
        print(f'no .kicad_sch under {args.target}')
        sys.exit(1)

    for path in sorted(found):
        parts = parse(path)
        variant = os.path.basename(os.path.dirname(path))
        print(f'\n=== {variant}  ({len(parts)} components) ===')
        for r in rows(parts):
            print(f'  {r["qty"]:>3} x {r["value"][:26]:28} '
                  f'{r["footprint"][:34]}')


if __name__ == '__main__':
    main()
