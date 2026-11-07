"""Pure parts of the BinScan receive client. Runs locally."""
import importlib.util, os, pathlib
os.environ.setdefault("INVENTREE_TOKEN", "x")
HERE = pathlib.Path(__file__).resolve().parent.parent


def load(name, path):
    s = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


rc = load("receiving", HERE / "binscan/receiving.py")
pv = load("providers", HERE / "binscan/providers.py")

print("=== evidence_text merges typed + model ===")
lab = {"orders": ["113-846985?-5845865"], "tracking": ["TBA305553921000"], "skus": [], "words": ["MTCELL", "7 pin female header"], "ship_to": "The Villages FL"}
t = rc.evidence_text("header sockets", lab)
assert t.splitlines()[0] == "header sockets" and "TBA305553921000" in t and "7 pin female header" in t, t
assert rc.evidence_text("", None) == ""
assert rc.site_from_label(lab) == "LRD" and rc.site_from_label({"ship_to": "Dover NH"}) == "SLN" and rc.site_from_label(None) is None

print("=== _parse_label: fences stripped, lists coerced, ? kept ===")
raw = '```json\n{"orders": "113-846985?-5845865", "tracking": [], "skus": ["B0GM7T6XWP"], "words": "MTCELL", "ship_to": "The Villages FL 32163"}\n```'
d = pv._parse_label(raw)
assert d["orders"] == ["113-846985?-5845865"] and d["skus"] == ["B0GM7T6XWP"] and d["words"] == ["MTCELL"], d
assert pv._parse_label("not json at all") == {"orders": [], "tracking": [], "skus": [], "words": [], "ship_to": ""}
assert "never complete" in pv.LABEL_SYSTEM.lower() or "never guess" in pv.LABEL_SYSTEM.lower()
print("\nALL OK")
