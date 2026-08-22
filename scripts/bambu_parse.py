"""Parse a Bambu Lab order confirmation. Three template eras, one checksum."""
import re

def parse(body, order, when):
    site = ("LRD" if re.search(r"Shipping [Aa]ddress.{0,120}?(Villages|Florida)", body, re.S)
            else "SLN")
    sub = None
    m = re.search(r"Subtotal[^$]{0,20}\$([\d,]+\.\d\d)", body)
    if m:
        sub = float(m.group(1).replace(",", ""))

    rows = []
    # new/mid era: pipe rows  "| | NAME x N variant | $A [$B] |"
    for m in re.finditer(r"\|\s*\|\s*(.+?)\s*\|\s*\$([\d,]+\.\d\d)(?:\s*\$([\d,]+\.\d\d))?\s*\|", body):
        desc, p1, p2 = m.group(1), m.group(2), m.group(3)
        if re.match(r"(Subtotal|shipping|Taxes|Grand total|Net Payment|FL )", desc, re.I):
            continue
        q = re.search(r"[x×]\s*(\d+)\s", desc)
        rows.append({"desc": desc.strip(), "qty": int(q.group(1)) if q else 1,
                     "p1": float(p1.replace(",", "")),
                     "p2": float(p2.replace(",", "")) if p2 else None})
    if not rows:
        # 2023 era: plain text  "NAME × N\n\nvariant\n\n$PRICE"
        # [^\n]+ for the NAME: with re.S a plain .+? swallows the "Order
        # summary\n-----" header into the first item's name.
        for m in re.finditer(r"^([^\n]+?)\s*×\s*(\d+)\s*\n\n(.*?)\n\n\$([\d,]+\.\d\d)",
                             body, re.M | re.S):
            rows.append({"desc": f"{m.group(1).strip()} x {m.group(2)} {m.group(3).strip()}",
                         "qty": int(m.group(2)),
                         "p1": float(m.group(4).replace(",", "")), "p2": None})

    # Which column was actually PAID? The templates disagree, so let the
    # subtotal decide instead of guessing. Verified: 2025-11 pays the SECOND
    # price, 2026-03 pays the FIRST, same vendor.
    which = "p1"
    if sub and any(r["p2"] for r in rows):
        s1 = sum(r["p1"] for r in rows)
        s2 = sum((r["p2"] if r["p2"] else r["p1"]) for r in rows)
        if abs(s2 - sub) < 0.02 and abs(s1 - sub) >= 0.02:
            which = "p2"
    for r in rows:
        ext = r[which] if r[which] is not None else r["p1"]
        r["ext"] = ext
        r["unit"] = round(ext / r["qty"], 4) if r["qty"] else ext
    check = round(sum(r["ext"] for r in rows), 2)
    return {"order": order, "date": when, "site": site, "subtotal": sub,
            "sum": check, "ok": (sub is None or abs(check - sub) < 0.02),
            "price_col": which, "lines": rows}
