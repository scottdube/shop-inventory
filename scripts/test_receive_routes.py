"""Routes exist, writes are gated, journal rows have the right shape. Local."""
import importlib.util, os, sys, pathlib, tempfile
os.environ["BINSCAN_WRITES"] = "0"
os.environ["BINSCAN_HOME"] = tempfile.mkdtemp()
os.environ.setdefault("INVENTREE_TOKEN", "x")
HERE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "binscan"))
spec = importlib.util.spec_from_file_location("bs", HERE / "binscan/app.py")
bs = importlib.util.module_from_spec(spec)
try: spec.loader.exec_module(bs)
except SystemExit: pass
from fastapi.testclient import TestClient
c = TestClient(bs.app)

print("=== /receive is served no-store ===")
r = c.get("/receive")
assert r.status_code == 200 and "no-store" in r.headers["cache-control"] and "All here" in r.text
print("=== commit/undo gated when writes are off ===")
assert c.post("/api/receive/commit", json={"plan": {}}).status_code == 403
assert c.post("/api/receive/undo", json={"receipt": {}}).status_code == 403
print("=== unsettled journals a row ===")
r = c.post("/api/receive/unsettled", json={"text": "1x7 header", "results": [{"reference": "PO-0291"}]})
assert r.status_code == 200
rows = bs.log_read()
assert rows[-1]["kind"] == "receive-unsettled" and rows[-1]["text"] == "1x7 header", rows[-1]
print("=== pending merges the journal row (plugin unreachable here is tolerated) ===")
r = c.get("/api/receive/pending?site=LRD")
assert r.status_code == 200 and any(i["kind"] == "unsettled" for i in r.json()["items"]), r.json()
print("\nALL OK")
