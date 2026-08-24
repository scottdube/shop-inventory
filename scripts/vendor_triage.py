"""Triage purchase mail from vendors the nightly sweep does not know about.

THE PROBLEM. The sweep asks `from:<known sender>` for a fixed vendor list, so a
purchase from anyone else is not "unhandled" — it is INVISIBLE. No query the job
makes could ever return it. Measured 2026-08-24 over 45 days: 201 candidates,
including an order from MFC Machining & Design Services and an Akro-Mils
24-drawer cabinet from Walmart. Both are shop inventory. Neither was reachable.

THE INVERSION. Search by SHAPE instead of sender — Gmail's own
`category:purchases` classifier — then subtract what we already handle. That
turns an unknown-unknown into an enumerable list.

WHAT THIS DOES NOT DO. It never creates a PO. An unknown vendor has no Company
record, and rule 2 says uncertain goes OUT-but-listed. Output is a triage queue
for Scott; approval is what promotes a domain into the known list, so the
question is asked once per vendor rather than once per order.

Input: JSON array of {sender, subject, date, snippet, threadId}.
Output: three buckets, and decision-queue lines for the unknown one.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

ap = argparse.ArgumentParser()
ap.add_argument("--candidates", required=True, help="JSON array from the Gmail sweep")
ap.add_argument("--registry", default=os.path.join(HERE, "vendor_registry.json"))
ap.add_argument("--emit-decisions", action="store_true",
                help="print decide.py --add arguments for the unknown bucket")
a = ap.parse_args()

reg = json.load(open(a.registry))
rows = json.load(open(a.candidates))


def domain(sender):
    m = re.search(r"@([\w.\-]+)", sender or "")
    return m.group(1).lower() if m else (sender or "").lower()


def suffix_hit(dom, domains):
    return any(dom == d or dom.endswith("." + d) for d in domains)


def bucket_of(dom):
    if suffix_hit(dom, reg["known"]["domains"]):
        return "known", "already swept"
    for reason, spec in reg["suppress"].items():
        if reason == "_comment":
            continue
        if suffix_hit(dom, spec["domains"]):
            return "suppress", reason
    if suffix_hit(dom, reg["platform"]["domains"]):
        return "platform", "merchant name is in the BODY, not the sender"
    if suffix_hit(dom, reg["mixed_use"]["domains"]):
        return "mixed", "sells both shop and household — classify per order"
    return "unknown", "not on any list"


NOT_ORDER = reg["lifecycle"]["not_an_order"]


def is_order_event(subject):
    s = (subject or "").lower()
    return not any(p in s for p in NOT_ORDER)


def order_no(text):
    m = re.search(r"(?:order|#)\s*#?\s*([A-Z0-9][A-Z0-9\-]{4,})", text or "", re.I)
    return m.group(1) if m else None


buckets = {"known": [], "suppress": [], "platform": [], "mixed": [], "unknown": []}
for r in rows:
    dom = domain(r.get("sender"))
    b, why = bucket_of(dom)
    r["_domain"], r["_why"] = dom, why
    r["_order_event"] = is_order_event(r.get("subject"))
    r["_order_no"] = order_no((r.get("subject") or "") + " " + (r.get("snippet") or ""))
    buckets[b].append(r)

print(f"{len(rows)} candidates\n")
for b in ("known", "suppress"):
    byreason = {}
    for r in buckets[b]:
        byreason.setdefault(r["_why"], []).append(r)
    print(f"-- {b}: {len(buckets[b])}")
    for why, rs in sorted(byreason.items()):
        doms = sorted({r["_domain"] for r in rs})
        print(f"     {why:14s} {len(rs):3d}  {', '.join(doms[:5])}")
print()

# Medical is suppressed AND redacted: log that it happened, never what it was.
med = [r for r in buckets["suppress"] if r["_why"] == "medical"]
if med:
    print(f"!! {len(med)} medical/benefits message(s) suppressed and NOT transcribed "
          f"(rule 3). Domains only: {sorted({r['_domain'] for r in med})}\n")

actionable = []
# The lifecycle filter is right for a vendor we already sweep — there the order
# confirmation is guaranteed to have been seen, so a ship notice is a duplicate.
# It is WRONG for a vendor we have never heard of. Measured 2026-08-24: MFC
# Machining & Design Services emitted only "on the way" / "out for delivery" /
# "delivered" inside the window, so filtering to order events dropped the single
# most shop-relevant vendor in the sweep to ZERO. For discovery, a ship notice is
# proof a purchase happened and it carries the order number. Keep it, dedupe by
# order number, and say how the vendor was found.
DISCOVERY = {"platform", "unknown"}

for b in ("platform", "mixed", "unknown"):
    live = buckets[b] if b in DISCOVERY else [r for r in buckets[b] if r["_order_event"]]
    noise = len(buckets[b]) - len(live)
    print(f"-- {b}: {len(buckets[b])}  ({len(live)} order events, {noise} lifecycle/non-order)")
    # One line per ORDER, not per email — a purchase emits four of these.
    seen = {}
    for r in sorted(live, key=lambda x: x.get("date", "")):
        key = r["_order_no"] or (r["_domain"], r.get("subject"))
        if key in seen:
            continue
        seen[key] = r
        actionable.append((b, r))
        via = "" if r["_order_event"] else "  [via ship notice]"
        print(f"     {r.get('date','')[:10]}  {r['_domain']:28s} "
              f"{(r.get('subject') or '')[:52]}{via}")
    if noise:
        print(f"     ...{noise} suppressed as ship/delivery/marketing stages")
    print()

print(f"=> {len(actionable)} distinct purchases need a decision\n")

if a.emit_decisions:
    print("--- decide.py lines ---")
    for b, r in actionable:
        vend = r["_domain"]
        on = r["_order_no"] or "no order number in subject/snippet"
        print(f'--add "new vendor {vend} {on} | unknown vendor, needs a call | '
              f'{(r.get("subject") or "")[:90]} | first seen {r.get("date","")[:10]} '
              f'| {r["_why"]}"')
