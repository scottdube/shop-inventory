"""The matcher on real order shapes. Runs locally: match.py imports no Django."""
import importlib.util, json, os, pathlib

HERE = pathlib.Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("match", HERE / "plugins/receiving/match.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

# Measured 2026-11-06. PO-0291 is the 1x7 header socket; three other open POs
# also carry a 1x7 female header line (the "several" case in the spec).
CARDS = [
 {"po": 291, "reference": "PO-0291", "supplier_reference": "113-8469851-5845865", "supplier": "Amazon",
  "status": 20, "closed": False, "issue_date": "2026-11-06", "target_date": "2026-11-08", "site": "LRD",
  "description": "Amazon order 113-8469851-5845865 — MTCELL 1x7 female header 2.54mm straight, 60 pcs x2 (to The Villages FL)",
  "note": "Auto-created by the queue C daytime sweep. Ships to The Villages FL (LRD).",
  "lines": [{"line": 611, "sku": "B0GM7T6XWP", "part": 1183, "name": "Header Socket 1x7 Female 0.1in",
             "sp_description": "MTCELL 1x7 female header 2.54mm straight, 60 pcs", "quantity": 2, "received": 0, "pack": 60, "price": 6.99}]},
 {"po": 289, "reference": "PO-0289", "supplier_reference": "1000204070", "supplier": "Hakko",
  "status": 20, "closed": False, "issue_date": "2026-11-05", "target_date": None, "site": "LRD",
  "description": "Hakko order 1000204070 — FX-971 station, tips and sponge (to The Villages FL)", "note": "",
  "lines": [{"line": 601, "sku": "FX971-010", "part": 1170, "name": "Hakko FX-971 Soldering Station",
             "sp_description": "FX-971 soldering station", "quantity": 1, "received": 0, "pack": 1, "price": 299.0},
            {"line": 602, "sku": "T39-D24", "part": 1171, "name": "Hakko T39-D24 Chisel Tip 2.4mm",
             "sp_description": "T39 series chisel tip", "quantity": 2, "received": 0, "pack": 1, "price": 12.0}]},
 {"po": 283, "reference": "PO-0283", "supplier_reference": "8215070970595753", "supplier": "AliExpress",
  "status": 20, "closed": False, "issue_date": "2026-10-28", "target_date": "2026-11-20", "site": "LRD",
  "description": "AliExpress order 8215070970595753 — SiTai GC9A01 1.28in round display x2 (to The Villages FL)", "note": "",
  "lines": [{"line": 590, "sku": "8215070970595753/SiTai GC9A01 1.28in round", "part": 418, "name": "GC9A01 1.28in Round TFT Display 240x240",
             "sp_description": "SiTai GC9A01 1.28in round", "quantity": 2, "received": 0, "pack": 1, "price": 4.10}]},
 {"po": 270, "reference": "PO-0270", "supplier_reference": "113-1111111-2222222", "supplier": "Amazon",
  "status": 20, "closed": False, "issue_date": "2026-10-20", "target_date": "2026-10-23", "site": "LRD",
  "description": "Amazon order 113-1111111-2222222 — 1x7 female header strip 20 pcs (to The Villages FL)", "note": "",
  "lines": [{"line": 560, "sku": "B0XXXXXXXX", "part": 1183, "name": "Header Socket 1x7 Female 0.1in",
             "sp_description": "1x7 female header strip 20 pcs", "quantity": 1, "received": 0, "pack": 20, "price": 5.49}]},
 {"po": 163, "reference": "PO-0163", "supplier_reference": "113-9999999-8888888", "supplier": "Amazon",
  "status": 60, "closed": True, "issue_date": "2026-09-10", "target_date": "2026-09-13", "site": "LRD",
  "description": "Amazon order 113-9999999-8888888 — Monoprice MST hub (to The Villages FL)", "note": "[REFUND-CONFIRMED] 2026-09-15",
  "lines": [{"line": 300, "sku": "B0MSTHUB01", "part": 900, "name": "Monoprice MST DisplayPort Hub",
             "sp_description": "Monoprice MST hub", "quantity": 1, "received": 0, "pack": 1, "price": 39.99}]},
]

print("=== extract_ids ===")
ids = m.extract_ids("Order # 113-8469851-5845865  TBA305553921000  ASIN B0GM7T6XWP  1Z999AA10123456784")
assert ids["orders"] == ["113-8469851-5845865"], ids
assert ids["last7"] == ["5845865"], ids
assert ids["skus"] == ["B0GM7T6XWP"], ids
assert set(ids["tracking"]) == {"TBA305553921000", "1Z999AA10123456784"}, ids
assert m.extract_ids("Hakko order 1000204070")["orders"] == ["1000204070"]
assert m.extract_ids("1x7 header")["orders"] == []
print("  OK")

print("=== decisive: full order number ===")
r = m.score("113-8469851-5845865", CARDS)
assert r[0]["po"] == 291 and r[0]["decisive"] == ["order 113-8469851-5845865"], r[0]
assert m.verdict(r) == "one"
print("=== decisive: last 7 only (label shows the tail) ===")
r = m.score("Order ...5845865", CARDS)
assert r[0]["po"] == 291 and m.verdict(r) == "one", r[:2]
print("=== decisive: ASIN ===")
r = m.score("B0GM7T6XWP", CARDS)
assert r[0]["po"] == 291 and m.verdict(r) == "one"
print("=== decisive: Hakko SKU ===")
r = m.score("FX971-010", CARDS)
assert r[0]["po"] == 289 and m.verdict(r) == "one"
print("=== words only, two open POs with the same part -> several ===")
r = m.score("1x7 female header socket", CARDS)
tops = {x["po"] for x in r[:2]}
assert tops == {291, 270}, r[:3]
assert m.verdict(r) == "several", (m.verdict(r), [(x["po"], x["score"]) for x in r])
print("=== words only, unique -> one ===")
r = m.score("GC9A01 round display", CARDS)
assert r[0]["po"] == 283 and m.verdict(r) == "one", [(x["po"], x["score"]) for x in r]
print("=== nothing -> none ===")
r = m.score("lamp shade", CARDS)
assert m.verdict(r) == "none", r
print("=== decisive hit on a RETURNED order is REPORTED, flagged closed ===")
r = m.score("113-9999999-8888888", CARDS)
assert r[0]["po"] == 163 and r[0]["closed"] is True and m.verdict(r) == "one"
print("=== transcription with ? never completes a number ===")
r = m.score("113-846985?-5845865", CARDS)
assert not r or r[0]["decisive"] == ["last7 5845865"], r[:1]
print("\nALL OK")
