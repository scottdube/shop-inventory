#!/usr/bin/env python3
"""Extract every image Scott has sent from the session transcript.

Claude Code stores attached images as base64 inside the session JSONL, which
means the photos taken during the bin walk are already on disk - they just are
not in a form anything else can use. This pulls them out and, critically,
carries the surrounding conversation text with each one, because a directory of
40 anonymous JPEGs is not usefully better than no photos at all. The text is
what says "this is B3-R6C4".

    photo_pull.py [transcript.jsonl] [outdir]
"""
import base64
import hashlib
import json
import os
import sys

def newest_transcript():
    """Most recently modified session JSONL for this project."""
    root = os.path.expanduser('~/.claude/projects')
    best = None
    for dirpath, _, files in os.walk(root):
        for f in files:
            if not f.endswith('.jsonl'):
                continue
            full = os.path.join(dirpath, f)
            if best is None or os.path.getmtime(full) > os.path.getmtime(best):
                best = full
    return best


TR = sys.argv[1] if len(sys.argv) > 1 else newest_transcript()
if not TR:
    print('no session transcript found under ~/.claude/projects')
    sys.exit(1)
OUT = sys.argv[2] if len(sys.argv) > 2 else 'photos'
os.makedirs(OUT, exist_ok=True)

EXT = {'image/jpeg': 'jpg', 'image/png': 'png', 'image/webp': 'webp'}


def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return ' '.join(b.get('text', '') for b in content
                        if isinstance(b, dict) and b.get('type') == 'text')
    return ''


rows, pending_user_text, seen = [], '', {}
lines = list(open(TR, errors='replace'))

for i, line in enumerate(lines):
    try:
        d = json.loads(line)
    except Exception:
        continue
    msg = d.get('message') or {}
    if msg.get('role') != 'user':
        # remember the assistant's last words - they usually name the drawer
        if msg.get('role') == 'assistant':
            t = text_of(msg.get('content'))
            if t.strip():
                pending_user_text = t.strip()[-400:]
        continue

    content = msg.get('content')
    if not isinstance(content, list):
        continue
    imgs = [b for b in content if isinstance(b, dict) and b.get('type') == 'image']
    if not imgs:
        continue
    caption = text_of(content).strip()

    for b in imgs:
        src = b.get('source', {})
        if src.get('type') != 'base64':
            continue
        raw = base64.b64decode(src.get('data', ''))
        h = hashlib.sha256(raw).hexdigest()[:12]
        if h in seen:
            continue                      # same photo re-sent, keep one copy
        ext = EXT.get(src.get('media_type'), 'bin')
        n = len(seen) + 1
        name = f'{n:02d}_{h}.{ext}'
        open(os.path.join(OUT, name), 'wb').write(raw)
        seen[h] = name
        rows.append(dict(n=n, file=name, bytes=len(raw), ts=d.get('timestamp', ''),
                         caption=caption[:300], asked=pending_user_text[:300]))

json.dump(rows, open(os.path.join(OUT, 'manifest.json'), 'w'), indent=1)
print(f'{len(rows)} unique image(s) -> {OUT}/\n')
for r in rows:
    print(f"{r['n']:>2}  {r['file']}  {r['bytes']//1024:>4}KB  {r['ts'][:19]}")
    if r['asked']:
        print(f"      I had just said: ...{r['asked'][-110:]}")
    if r['caption']:
        print(f"      Scott said: {r['caption'][:110]}")
