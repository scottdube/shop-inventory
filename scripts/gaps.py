#!/usr/bin/env python3
"""Per-call elapsed for the most recently modified session transcript.

Exists because three open decision items argue about where the sweep's hours
go and none of them measured the gap distribution. Prints every gap over 60s.
"""
import json, glob, os, datetime

d = os.path.expanduser("~/.claude/projects/-Users-scottdube-code")
files = sorted(glob.glob(os.path.join(d, "*.jsonl")), key=os.path.getmtime)
if not files:
    raise SystemExit("no transcripts")
path = files[-1]
print(f"transcript: {os.path.basename(path)}")

recs = []
with open(path) as fh:
    for line in fh:
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except ValueError:
            continue
        ts = r.get("timestamp")
        if ts:
            recs.append((ts, r))

print(f"records with timestamps: {len(recs)}")
if not recs:
    raise SystemExit(0)


def parse(ts):
    return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))


def describe(r):
    msg = r.get("message") or {}
    content = msg.get("content")
    bits = []
    if isinstance(content, list):
        for c in content:
            if not isinstance(c, dict):
                continue
            if c.get("type") == "tool_use":
                name = c.get("name", "?")
                inp = c.get("input") or {}
                detail = inp.get("command") or inp.get("file_path") or inp.get("query") or inp.get("url") or ""
                bits.append(f"{name}: {str(detail)[:110]}")
            elif c.get("type") == "tool_result":
                bits.append("tool_result")
    return "; ".join(bits) or r.get("type", "?")


t0, tn = parse(recs[0][0]), parse(recs[-1][0])
print(f"span: {t0.astimezone()} -> {tn.astimezone()}  = {(tn - t0).total_seconds()/60:.1f} min")

gaps = []
for (a_ts, a), (b_ts, b) in zip(recs, recs[1:]):
    delta = (parse(b_ts) - parse(a_ts)).total_seconds()
    gaps.append((delta, a_ts, describe(a)))

gaps.sort(reverse=True)
total = sum(g[0] for g in gaps)
big = [g for g in gaps if g[0] >= 60]
print(f"total gap: {total/60:.1f} min; gaps >=60s: {len(big)} accounting for {sum(g[0] for g in big)/60:.1f} min\n")
for delta, ts, what in big[:15]:
    local = parse(ts).astimezone().strftime("%H:%M:%S")
    print(f"{delta/60:8.1f} min  after {local}  {what}")
