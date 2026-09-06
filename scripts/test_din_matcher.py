"""Exercise the REAL matcher on the reading that caused the mis-file."""
import importlib.util, sys, os
os.environ.setdefault("BINSCAN_WRITES", "0")
spec = importlib.util.spec_from_file_location("bs", "/Users/scottdube/binscan/app.py")
bs = importlib.util.module_from_spec(spec)
try: spec.loader.exec_module(bs)
except SystemExit: pass

print("=== DIN numbers -> form ===")
for text, want in [("PART DESCRIPTION: M8 934-8", "nut"),
                   ("PART DESCRIPTION: M4X6 7380-1 A2 FT", "button"),
                   ("DIN 912 M6x20", "socket"),
                   ("QTY: 100 EA LOT #: U01140104418", None),
                   ("Line 3 on your packing list", None)]:
    got = bs._din_kinds(text)
    ok = (want in got) if want else (not got)
    print("  %-4s %-38s -> %s" % ("OK" if ok else "FAIL", text[:38], sorted(got) or "-"))
    assert ok

print("\n=== words still work, via _kinds ===")
print("  hex nut M8 ->", sorted(bs._kinds("hex nut M8")))
assert "nut" in bs._kinds("hex nut M8")

print("\n=== END TO END: the exact reading that mis-filed 92 nuts ===")
reading = {"tag": "", "labels": ["PART DESCRIPTION: M8 934-8",
                                 "PART #: HN4800800-100M1",
                                 "LOT #: U01140104418",
                                 "Line 3 on your packing list"], "markings": []}
rows = [
 {"sku": "91290A214", "name": "Black-Oxide Alloy Steel Socket Head Screw, M8 x 1.25 mm Thread, 60 mm Long, Fully Threaded"},
 {"sku": "91280A530", "name": "Medium-Strength Class 8.8 Steel Hex Head Screw, Zinc-Plated, M8 x 1.25 mm Thread"},
 {"sku": "97131A140", "name": "Medium-Strength Nylon-Insert Locknut, Class 8, Zinc Plated Steel, M8 x 1.25 mm"},
 {"sku": "90592A022", "name": "Steel Hex Nut, Medium-Strength, Class 8, M8 x 1.25 mm Thread"},
]
ranked, basis = bs.match_reading(reading, rows)
print("  basis:", basis)
for i, c in enumerate(ranked, 1):
    print("   %d. %-11s %s" % (i, c["row"]["sku"], c["row"]["name"][:52]))
assert ranked, "no candidates at all"
top = ranked[0]["row"]["sku"]
print("\n  top candidate:", top, "(was 91290A214, a SCREW, before this fix)")
assert top == "90592A022", "the hex nut is STILL not first"
print("  PASS - the hex nut now ranks first")
