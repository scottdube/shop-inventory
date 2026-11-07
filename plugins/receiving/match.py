"""Pure matcher: the model transcribes, this matches. No Django here, so it
runs locally against a snapshot of real orders.

Scoring per spec §3. Decisive evidence (an order number, its last 7 digits,
an ASIN/SKU, a tracking number found in the PO note) wins outright. Words are
IDF-weighted overlap, the same formula BinScan's catalogue search uses:
score = sum(idf of shared tokens) / sqrt(number of tokens on the card).
"""
import math
import re

WORD_FLOOR = 0.5    # provisional: set from the photo fixture set (spec §8).
                    # 1.0 was too high: four specific words on a real 10-13 token
                    # card score 0.84-0.96 with only five cards in the pool.
                    # 0.5 keeps "hakko tip" (0.62), drops a lone "header" (0.24).
WORD_RATIO = 2.0

ORDER_RE = re.compile(r"\b(\d{3}-\d{7}-\d{7})\b")          # Amazon
PLAIN_ORDER_RE = re.compile(r"\b(\d{10,16})\b")              # Hakko 1000204070, AliExpress 8215070970595753
LAST7_RE = re.compile(r"(?<![\d-])(\d{7})\b")
ASIN_RE = re.compile(r"\b(B0[A-Z0-9]{8})\b")
SKU_RE = re.compile(r"\b([A-Z]{1,4}\d{2,4}-[A-Z0-9]{2,6})\b")  # FX971-010, T39-D24
TRACK_RE = re.compile(r"\b(TBA\d{12,15}|1Z[A-Z0-9]{16}|\d{20,22})\b")
_STOP = {"the", "and", "for", "with", "pcs", "pack", "of", "to", "x", "in", "mm", "order",
         "amazon", "aliexpress", "villages", "fl", "dover", "nh", "ships", "auto", "created"}


def extract_ids(text):
    t = (text or "").upper()
    orders = ORDER_RE.findall(t)
    orders += [o for o in PLAIN_ORDER_RE.findall(t) if o not in "".join(orders)]
    last7 = [o[-7:] for o in orders]
    if not orders:
        # a label often shows only the tail of the order number; a "?" anywhere
        # in the run breaks the \d{7}, which is the point - never complete it
        last7 = LAST7_RE.findall(t)
    skus = ASIN_RE.findall(t) + SKU_RE.findall(t)
    return {"orders": orders, "last7": last7, "skus": skus, "tracking": TRACK_RE.findall(t)}


def tokens(text):
    raw = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {w for w in raw if len(w) >= 2 and w not in _STOP}


def _card_text(c):
    bits = [c.get("description") or ""]
    for ln in c.get("lines", []):
        bits += [ln.get("name") or "", ln.get("sp_description") or ""]
    return " ".join(bits)


def score(text, cards):
    ids = extract_ids(text)
    want = tokens(text)
    docs = [(c, tokens(_card_text(c))) for c in cards]
    n = len(docs) or 1
    df = {}
    for _c, toks in docs:
        for t in toks:
            df[t] = df.get(t, 0) + 1
    idf = {t: math.log(n / (1 + c)) + 0.25 for t, c in df.items()}

    out = []
    for c, have in docs:
        decisive = []
        ref = (c.get("supplier_reference") or "").upper()
        if ref and ref in ids["orders"]:
            decisive.append(f"order {ref}")
        elif ref and ref[-7:] in ids["last7"]:
            decisive.append(f"last7 {ref[-7:]}")
        for ln in c.get("lines", []):
            sku = (ln.get("sku") or "").upper()
            if sku and any(sku == s or sku.startswith(s + "/") for s in ids["skus"]):
                decisive.append(f"sku {sku}")
        note = (c.get("note") or "").upper()
        for tr in ids["tracking"]:
            if tr in note:
                decisive.append(f"tracking {tr}")
        shared = want & have
        wscore = sum(idf.get(t, 0.25) for t in shared) / (math.sqrt(len(have)) or 1) if shared else 0.0
        if not decisive and wscore < WORD_FLOOR:
            continue
        out.append({"po": c["po"], "reference": c.get("reference"), "closed": bool(c.get("closed")),
                    "score": round(wscore, 3), "decisive": decisive,
                    "shared": sorted(shared, key=lambda t: -idf.get(t, 0))[:6]})
    out.sort(key=lambda r: (-len(r["decisive"]), -r["score"]))
    return out


def verdict(results):
    if not results:
        return "none"
    dec = [r for r in results if r["decisive"]]
    if dec:
        return "one" if len(dec) == 1 else "several"
    top = results[0]["score"]
    runner = results[1]["score"] if len(results) > 1 else 0.0
    if top >= WORD_FLOOR and (runner == 0.0 or top >= WORD_RATIO * runner):
        return "one"
    return "several"
