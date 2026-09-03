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

CHANGED 2026-08-27, closing decision item vendor-triage-no-idempotency-check:
the script now asks InvenTree whether an extracted order number already has a
PO, and drops those candidates from the decision output. Before this, triage
re-surfaced Walmart 2000151-82176030 as "needs a decision" while PO-0142 sat
in the system — its "Arrived" mail carries the order number in the body only,
the dedupe key fell back to (domain, subject), and NOTHING here ever called
po_check. The fallback key also gains the date, because two DISTINCT Walmart
orders thread under one identical subject and were merged into a single
decision on 2026-08-24, which Scott had to split by hand.
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
        # "already swept" was a lie for five of these domains and generated
        # the same journal contradiction four runs in a row: aliexpress/seeed/
        # jlcpcb/lcsc/precisebits are KNOWN (skip: don't re-ask about the
        # vendor) but NOT swept by section 3, so their orders are invisible,
        # not handled. The registry now says which is which; print the truth.
        for d, note in reg["known"].get("not_actually_swept", {}).items():
            if d == "_comment":
                continue
            if dom == d or dom.endswith("." + d):
                return "known", note
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
    # A real order number contains a DIGIT. Without that requirement the
    # regex returned "Confirmation" for "Order Confirmation #FTC-99887"
    # (caught by the 2026-08-27 regression test) — an English word that then
    # poisoned the dedupe key, the idempotency lookup, and the decision line.
    for m in re.finditer(r"(?:order|#)\s*#?\s*([A-Z0-9][A-Z0-9\-]{4,})", text or "", re.I):
        if any(c.isdigit() for c in m.group(1)):
            return m.group(1)
    return None


buckets = {"known": [], "suppress": [], "platform": [], "mixed": [], "unknown": []}
for r in rows:
    dom = domain(r.get("sender"))
    b, why = bucket_of(dom)
    r["_domain"], r["_why"] = dom, why
    r["_order_event"] = is_order_event(r.get("subject"))
    r["_order_no"] = order_no((r.get("subject") or "") + " " + (r.get("snippet") or ""))
    buckets[b].append(r)


def existing_po_refs():
    """supplier_reference -> PO reference for every PO, normalized.

    Runs under itq on the Mini where Django is importable; anywhere else the
    check degrades to 'unknown' with a visible warning rather than a silent
    pass, because a suppression nobody can see is how the Walmart bug lived.
    """
    try:
        import django
        sys.path.insert(0, os.getcwd())
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
        django.setup()
        from order.models import PurchaseOrder
        out = {}
        for ref, sref in PurchaseOrder.objects.values_list("reference", "supplier_reference"):
            key = re.sub(r"[^A-Za-z0-9]", "", (sref or "")).lower()
            if key:
                out[key] = ref
        return out
    except Exception as exc:  # noqa: BLE001
        print(f"!! InvenTree not reachable from here ({type(exc).__name__}) — "
              "idempotency check SKIPPED; already-imported orders may re-surface. "
              "Run via itq so the check works.\n")
        return None


PO_REFS = existing_po_refs()


def already_imported(order):
    if PO_REFS is None or not order:
        return None
    return PO_REFS.get(re.sub(r"[^A-Za-z0-9]", "", order).lower())


QUEUE_PATH = "/Volumes/4TB_Removable/inventree/pending_decisions.md"


def open_queue_orders():
    """Normalized order numbers carried by OPEN decision items.

    The PO check above can never fire for the UNKNOWN bucket, because an unknown
    vendor by rule never gets a PO — so before this existed the same order was
    re-emitted on every run inside its window, forever. Measured 2026-09-02:
    omnifixo 40098 reached the queue twice and a third line was suppressed only
    because a run hand-grepped first. Same degrade-loudly contract as PO_REFS.
    """
    try:
        text = open(QUEUE_PATH).read()
    except OSError as exc:  # noqa: BLE001
        print(f"!! decision queue unreadable from here ({type(exc).__name__}) — "
              "queue-dedupe check SKIPPED; already-queued orders may re-surface. "
              "Run via itq so the check works.\n")
        return None
    # Only OPEN items suppress. A closed "- [x]" item is a settled question, and
    # a fresh order from that vendor deserves to be asked again.
    # Every token must contain a digit — the same rule the order-number regex
    # uses. Without it the set fills with prose ("vendor", "unknown") and a
    # future order number that happens to be a word would be silently dropped.
    return {re.sub(r"[^A-Za-z0-9]", "", tok).lower()
            for line in text.splitlines() if line.lstrip().startswith("- [ ]")
            for tok in re.findall(r"[A-Za-z0-9][A-Za-z0-9-]{3,}", line)
            if any(c.isdigit() for c in tok)}


QUEUE_ORDERS = open_queue_orders()


def already_queued(order):
    if QUEUE_ORDERS is None or not order:
        return False
    return re.sub(r"[^A-Za-z0-9]", "", order).lower() in QUEUE_ORDERS

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
    # The no-order-number fallback key includes the DATE: two distinct Walmart
    # orders share one identical subject, and (domain, subject) alone merged
    # them into a single decision on 2026-08-24.
    seen = {}
    for r in sorted(live, key=lambda x: x.get("date", "")):
        key = r["_order_no"] or (r["_domain"], r.get("subject"), (r.get("date") or "")[:10])
        if key in seen:
            continue
        seen[key] = r
        po = already_imported(r["_order_no"])
        if po:
            print(f"     {r.get('date','')[:10]}  {r['_domain']:28s} "
                  f"order {r['_order_no']} ALREADY IMPORTED as {po} — no decision")
            continue
        if already_queued(r["_order_no"]):
            print(f"     {r.get('date','')[:10]}  {r['_domain']:28s} "
                  f"order {r['_order_no']} ALREADY QUEUED — no decision")
            continue
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
        # The no-number fallback must carry the date, or two such orders from
        # one vendor share a decide.py key and the second is silently deduped
        # away at queue time — a decision that never reaches Scott.
        on = r["_order_no"] or f"no-order-no-{(r.get('date') or 'undated')[:10]}"
        print(f'--add "new vendor {vend} {on} | unknown vendor, needs a call | '
              f'{(r.get("subject") or "")[:90]} | first seen {r.get("date","")[:10]} '
              f'| {r["_why"]}"')
