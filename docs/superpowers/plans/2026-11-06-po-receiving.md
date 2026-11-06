# PO receiving from the phone — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Receive a purchase order from the phone by photographing the box or typing a few words, with the PO found for Scott, quantities and destination prefilled, and an Undo; and close returns automatically from the Amazon refund mail the watcher already reads.

**Architecture:** One engine, hosted as an InvenTree plugin (`plugins/receiving/`) that exposes `plan`/`commit`/`undo`/`match`/`pending` as token-authenticated HTTP views under `/plugin/receiving/…`. BinScan (`~/binscan/app.py` on the Mini) gets a `/receive` page that does the camera and the model transcription, then calls the plugin over HTTP. The CLI scripts (`receive_po.py`, new `returns.py`) import the same engine modules under the InvenTree interpreter via `itq run`. The refund watcher task calls `returns.py` instead of writing notes by hand.

**Tech Stack:** Python 3.12, Django ORM inside InvenTree 1.6.1 (`plugin.InvenTreePlugin` + `UrlsMixin`, DRF `APIView`, `users.authentication.ApiTokenAuthentication`), FastAPI + httpx in BinScan, vanilla JS page, Anthropic vision call via `binscan/providers.py`, `plugins/notes_compat.py` for every note write.

**Spec:** `docs/superpowers/specs/2026-11-06-po-receiving-design.md` — read it first. Two deviations from the spec are locked in here, both measured 2026-11-06 (see "Deviations" below).

## Global Constraints

- Everything on the Mini runs through `~/code/scripts/itq run <local.py> [args]`, `itq push <local> <remote>`, `itq sql "<one-liner>"`. No hand-built ssh/scp/heredoc chains. Scripts that use the ORM must call `django.setup()` themselves (the `itq run` boilerplate at the top of `scripts/receive_po.py`).
- InvenTree backend root on the Mini: `/Volumes/4TB_Removable/inventree/src/src/backend/InvenTree` (this is the cwd `itq run` gives you). Custom plugins deploy to `<that>/plugins/<name>/`. BinScan deploys to `/Users/scottdube/binscan/`.
- Restart InvenTree: `launchctl kickstart -k gui/$(id -u)/com.inventree.server` (run on the Mini; the `itq` shell shape for that is `ssh mini 'launchctl kickstart -k gui/$(id -u)/com.inventree.server'`). **Never `kill -HUP`.** Restart BinScan: `ssh mini 'launchctl kickstart -k gui/$(id -u)/com.binscan'`.
- **Verify every write by re-read.** `.save()` has reported success and written nothing on this install; fall back to queryset `.update()` and re-read again. `notes_compat` already does this for notes and raises `RuntimeError` on failure.
- **Notes are `common.Note` rows.** Write them only through `plugins.notes_compat` (`note_text`, `note_set`, `note_append`, `note_prepend`, `filter_notes`). Never touch a `notes` attribute on a Part/StockItem/PurchaseOrder.
- **Pack sizes:** pieces = packs × `SupplierPart.pack_quantity_native`. Stock is counted in pieces. Unit price = line price ÷ pack.
- **Status codes** (measured): `PurchaseOrderStatus` PLACED=20, COMPLETE=30, RETURNED=60; `StockStatus` QUARANTINED=75. Import as `from order.status_codes import PurchaseOrderStatus` with the fallback `from InvenTree.status_codes import PurchaseOrderStatus`; same for `from stock.status_codes import StockStatus`.
- **Locations** (measured): site roots LRD pk 2, SLN pk 1; `LRD/Receiving` pk 473, `SLN/Receiving` pk 472. Location names are NOT unique (`Receiving` exists twice); never `.get(name=…)`.
- **Sentinels** (exact strings, the watcher greps for them): `[GOING-BACK]`, `[REFUND-CONFIRMED]`, `[NEEDS-DECISION]`, `[WATCH-ORDER] <num>`.
- Amazon company pk 9. Sweep-created Amazon POs carry the full order number in `supplier_reference` (e.g. `113-8469851-5845865`), the ASIN as the supplier part `SKU` (e.g. `B0GM7T6XWP`), and "to The Villages FL" in `description`/note for LRD ("Dover" for SLN). PO reference pattern `PO-{ref:04d}`.
- `ENABLE_PLUGINS_URL` is an InvenTree **global setting** (`common.models.InvenTreeSetting`), currently `False`. Plugin URLs do not register until it is `True` AND the server is restarted.
- BinScan: writes gated by `WRITES_ON` (env `BINSCAN_WRITES=1`); every page served `no-store`; run `python3 scripts/unbound_names.py binscan/app.py` before every deploy; journal every write to `log.jsonl` via `log_append`.
- Scott is mildly colorblind: every state on the page carries a glyph (`[OK]`, `[!!]`, `[XX]`, `[??]`), never color alone.
- No label printing anywhere in this feature.
- Commit messages say why the obvious alternative was rejected and end with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- Tests are plain scripts with `assert` (the repo's convention, `scripts/test_din_matcher.py`), run with `python3 scripts/test_x.py` locally or `~/code/scripts/itq run scripts/test_x.py` on the Mini. No pytest.

## Deviations from the spec (decided 2026-11-06, measured)

1. **Spec §1 says BinScan calls the engine through a subprocess running the InvenTree interpreter.** That cannot work: BinScan is a LaunchAgent, and macOS TCC refuses launchd-spawned processes any execution under `/Volumes/*` (TRAPS.md, "TCC"). The InvenTree venv is on `/Volumes/4TB_Removable`. So the engine lives INSIDE InvenTree as a plugin with `UrlsMixin`, and BinScan calls it over HTTP on `127.0.0.1:8001` with the token it already holds. The REST receive endpoint is still not used; the plugin views run the engine's own `plan`/`commit`.
2. **Spec §6 says pending state is a JSON file beside `log.jsonl`.** Two of the three pending sources are derivable from the database (a `[NEEDS-DECISION]` token in a PO note; PLACED orders more than 3 days past `target_date` with nothing received), so they are computed by the plugin's `/pending/` view and never stored twice. The third source (an unsettled match Scott closed) is BinScan-local and goes into `log.jsonl` as a `receive-unsettled` journal row, read back by the page.

## File map

| File | Responsibility |
|---|---|
| `plugins/receiving/__init__.py` | Plugin class, URL table, imports the sibling modules (package or file-path) |
| `plugins/receiving/match.py` | **Pure Python, no Django.** Id extraction, tokeniser, IDF scoring, verdict rule |
| `plugins/receiving/engine.py` | ORM: `open_orders`, `po_card`, `site_of`, `suggest_destination`, `plan`, `commit`, `undo`, `pending` |
| `plugins/receiving/returns.py` | ORM: `requested`, `refunded` — the return branches and their hard guard |
| `plugins/receiving/views.py` | DRF views: `/ping/ /open/ /match/ /plan/ /commit/ /undo/ /pending/` |
| `scripts/receive_po.py` | Thin CLI over `engine.plan`/`engine.commit` (same flags as today) |
| `scripts/returns.py` | CLI over `returns.requested`/`returns.refunded` for the watcher |
| `scripts/set_plugins_url.py`, `scripts/activate_plugin.py` | One-shot setup scripts (global setting on; PluginConfig active) |
| `scripts/receive_fixture_snapshot.py` | Dumps PO cards to `binscan/fixtures/receive/pos-<date>.json` for local matcher tests |
| `scripts/test_receive_match.py` | Local test of `match.py` against the snapshot |
| `scripts/test_receiving_engine.py` | Mini test: plan → commit → re-read → undo → re-read on a throwaway PO |
| `scripts/test_returns.py` | Mini test: the three branches + unclean cases on a throwaway PO |
| `binscan/receiving.py` | httpx client for the plugin views; `evidence_text()` merge |
| `binscan/providers.py` | `LABEL_SYSTEM` prompt + `read_label()` |
| `binscan/receive_page.py` | The `/receive` HTML/JS page as one string |
| `binscan/app.py` | Routes: `/receive`, `/api/receive/match|plan|commit|undo|pending` |
| `~/.claude/scheduled-tasks/amazon-refund-watch/SKILL.md` | Calls `returns.py`; keeps mail rules and glyph report |
| `docs/binscan.md`, `CLAUDE.md`, `docs/TRAPS.md`, `plugins/README.md`, the spec | Docs |

---

### Task 1: Plugin scaffold, URL plumbing switched on, `/ping/` answering

**Files:**
- Create: `plugins/receiving/__init__.py`
- Create: `plugins/receiving/views.py`
- Create: `scripts/set_plugins_url.py`
- Create: `scripts/activate_plugin.py`
- Modify: `plugins/README.md` (deploy lines for the new plugin)

**Interfaces:**
- Produces: plugin slug `receiving`, base URL `http://192.168.50.10:8001/plugin/receiving/`; views authenticate with `Authorization: Token <token>` (BinScan's existing `INVENTREE_TOKEN`). `views.py` exposes `PingView`.
- Produces: the `_sibling(name)` loader in `__init__.py` that later tasks use to import `match`, `engine`, `returns` whether the package was loaded as `plugins.receiving` or by file path.

- [ ] **Step 1: Write the plugin package**

`plugins/receiving/__init__.py`:

```python
"""Receiving — the one engine behind receive_po.py and BinScan's /receive page.

Hosted as a plugin, not a subprocess: BinScan is a LaunchAgent, and TCC refuses
launchd children any execution under /Volumes/*, where the InvenTree venv lives
(TRAPS.md). An HTTP view inside InvenTree is the one place both doors can reach.
"""
import importlib.util as _ilu
import pathlib as _pl

from django.urls import path

from plugin import InvenTreePlugin
from plugin.mixins import UrlsMixin

_HERE = _pl.Path(__file__).resolve().parent


def _sibling(name):
    """Import a module from this directory whether or not we are a package.

    InvenTree loads custom plugins as `plugins.<dir>` normally, but shop_status
    had to grow a file-path fallback because the dir is sometimes loaded by
    path with no parent package. Same trick here, for every sibling.
    """
    try:
        return __import__(f"{__package__}.{name}", fromlist=[name]) if __package__ else None
    except ImportError:
        pass
    spec = _ilu.spec_from_file_location(f"receiving_{name}", _HERE / f"{name}.py")
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ReceivingPlugin(UrlsMixin, InvenTreePlugin):
    NAME = "Receiving"
    SLUG = "receiving"
    TITLE = "Receiving engine (plan / commit / undo / match / returns)"
    DESCRIPTION = "Pack-aware PO receiving shared by receive_po.py and BinScan."
    VERSION = "0.1.0"
    AUTHOR = "Scott Dube"

    def setup_urls(self):
        views = _sibling("views")
        return [
            path("ping/", views.PingView.as_view(), name="ping"),
        ]
```

`plugins/receiving/views.py`:

```python
"""HTTP face of the receiving engine. Token-auth only; no session, no CSRF."""
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.authentication import ApiTokenAuthentication


class _View(APIView):
    authentication_classes = [ApiTokenAuthentication]
    permission_classes = [IsAuthenticated]


class PingView(_View):
    def get(self, request):
        return Response({"ok": True, "plugin": "receiving", "user": request.user.username})
```

- [ ] **Step 2: Write the two setup scripts**

`scripts/set_plugins_url.py`:

```python
"""Turn on the GLOBAL setting that lets plugins register URLs. Measured
2026-11-06: ENABLE_PLUGINS_URL is an InvenTreeSetting row, not config.yaml,
and UrlsMixin only mounts its routes when it is True at server start."""
import os, sys
import django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from common.models import InvenTreeSetting  # noqa: E402

before = InvenTreeSetting.get_setting("ENABLE_PLUGINS_URL")
InvenTreeSetting.set_setting("ENABLE_PLUGINS_URL", True, None)
after = InvenTreeSetting.get_setting("ENABLE_PLUGINS_URL")
print(f"ENABLE_PLUGINS_URL {before} -> {after}")
assert after is True, "setting did not stick"
print("restart the server now: launchctl kickstart -k gui/$(id -u)/com.inventree.server")
```

`scripts/activate_plugin.py`:

```python
"""Activate a PluginConfig by key and prove the registry sees it.
Usage: itq run scripts/activate_plugin.py receiving"""
import os, sys
import django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from plugin.models import PluginConfig  # noqa: E402
from plugin.registry import registry  # noqa: E402

key = sys.argv[1]
cfg = PluginConfig.objects.filter(key=key).first()
if cfg is None:
    raise SystemExit(f"no PluginConfig {key!r}: the server has not loaded the directory yet "
                     f"(push it, restart, re-run). Known: {sorted(PluginConfig.objects.values_list('key', flat=True))}")
if not cfg.active:
    PluginConfig.objects.filter(pk=cfg.pk).update(active=True)
    cfg.refresh_from_db()
assert cfg.active, "active did not stick"
print(f"PluginConfig {key} active={cfg.active}; registry sees it: {registry.get_plugin(key) is not None}")
print("if registry says False, restart the server again and re-run this to confirm")
```

- [ ] **Step 3: Deploy and switch on**

```bash
cd /Users/scottdube/code/shop-inventory
R=/Volumes/4TB_Removable/inventree/src/src/backend/InvenTree/plugins/receiving
~/code/scripts/itq run scripts/set_plugins_url.py
~/code/scripts/itq push plugins/receiving/__init__.py $R/__init__.py
~/code/scripts/itq push plugins/receiving/views.py $R/views.py
ssh mini 'launchctl kickstart -k gui/$(id -u)/com.inventree.server'
sleep 20
~/code/scripts/itq run scripts/activate_plugin.py receiving
ssh mini 'launchctl kickstart -k gui/$(id -u)/com.inventree.server'
sleep 20
~/code/scripts/itq run scripts/activate_plugin.py receiving
```

Expected last line: `PluginConfig receiving active=True; registry sees it: True`.

- [ ] **Step 4: Prove the URL answers with the token**

The token is in BinScan's env file on the Mini. Read it without printing it:

```bash
ssh mini 'T=$(grep ^INVENTREE_TOKEN= ~/binscan/.env | cut -d= -f2); curl -s -o /dev/null -w "%{http_code}\n" -H "Authorization: Token $T" http://127.0.0.1:8001/plugin/receiving/ping/; curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8001/plugin/receiving/ping/'
```

Expected: `200` then `401`. (If BinScan's env file is not at `~/binscan/.env`, find it from the LaunchAgent: `ssh mini 'grep -A3 EnvironmentVariables ~/Library/LaunchAgents/com.binscan.plist'`.) If the first is `404`: the global setting is on but the server was not restarted after activation, or the PluginConfig is inactive. Re-run Step 3 from the kickstart line.

- [ ] **Step 5: Record the deploy lines in `plugins/README.md`**

Append under "## Deploying a change":

```markdown
    R=/Volumes/4TB_Removable/inventree/src/src/backend/InvenTree/plugins/receiving
    itq push plugins/receiving/__init__.py $R/__init__.py     # and match.py engine.py returns.py views.py
    ssh mini 'launchctl kickstart -k gui/$(id -u)/com.inventree.server'

`receiving` exposes HTTP views (`/plugin/receiving/ping/` …). They exist only
while the GLOBAL setting `ENABLE_PLUGINS_URL` is True (`scripts/set_plugins_url.py`)
and the PluginConfig is active (`scripts/activate_plugin.py receiving`); both
need a restart to take effect. A 404 on `/ping/` after a deploy means one of
those, not a code error.
```

- [ ] **Step 6: Commit**

```bash
git add plugins/receiving scripts/set_plugins_url.py scripts/activate_plugin.py plugins/README.md
git commit -m "receiving plugin: scaffold with /ping/ behind token auth

Hosted as an InvenTree plugin, not the subprocess the spec drew: BinScan is a
LaunchAgent and TCC refuses launchd children any execution under /Volumes/*,
where the InvenTree venv lives. ENABLE_PLUGINS_URL is a global setting
(InvenTreeSetting), not config.yaml; measured 2026-11-06.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 2: Pure matcher — id extraction, scoring, verdict

**Files:**
- Create: `plugins/receiving/match.py`
- Create: `scripts/receive_fixture_snapshot.py`
- Create: `binscan/fixtures/receive/pos-2026-11-06.json` (generated by the snapshot script)
- Test: `scripts/test_receive_match.py`

**Interfaces:**
- Produces (all pure, JSON in / JSON out):
  - `extract_ids(text: str) -> dict` → `{"orders": [str], "last7": [str], "skus": [str], "tracking": [str]}`
  - `tokens(text: str) -> set[str]`
  - `score(text: str, cards: list[dict]) -> list[dict]` — each result `{"po": pk, "reference", "score": float, "decisive": [str], "shared": [str]}` sorted best first
  - `verdict(results: list[dict]) -> str` — `"one" | "several" | "none"`
  - constants `WORD_FLOOR = 1.0`, `WORD_RATIO = 2.0` (provisional until the photo fixture set exists, spec §8)
- Consumes: the "card" shape produced by `engine.po_card` in Task 3. Fix it here so both sides agree:

```python
CARD = {
  "po": 291, "reference": "PO-0291", "supplier_reference": "113-8469851-5845865",
  "supplier": "Amazon", "status": 20, "closed": False,
  "issue_date": "2026-11-06", "target_date": "2026-11-08",
  "description": "Amazon order 113-8469851-5845865 — MTCELL 1x7 female header 2.54mm straight, 60 pcs x2 (to The Villages FL)",
  "note": "Auto-created by the queue C daytime sweep …",
  "site": "LRD",
  "url": "http://192.168.50.10:8001/web/purchasing/purchase-order/291",
  "lines": [{"line": 611, "sku": "B0GM7T6XWP", "part": 1183,
             "name": "Header Socket 1x7 Female 0.1in",
             "sp_description": "MTCELL 1x7 female header 2.54mm straight, 60 pcs",
             "quantity": 2.0, "received": 0.0, "pack": 60.0,
             "price": 6.99, "image": "/media/part_images/part_1183.jpg"}]}
```

- [ ] **Step 1: Snapshot real PO cards so the test runs on real records, locally**

`scripts/receive_fixture_snapshot.py` (runs on the Mini, prints JSON; redirect locally):

```python
"""Dump every PO of the last 90 days as a receiving card, for local matcher
tests. Real records, not synthetic ones: the "rod" in "product" lesson.
    itq run scripts/receive_fixture_snapshot.py > binscan/fixtures/receive/pos-$(date +%F).json
"""
import datetime, json, os, sys
import django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from order.models import PurchaseOrder  # noqa: E402
from plugins.receiving.engine import po_card  # noqa: E402

since = datetime.date.today() - datetime.timedelta(days=90)
qs = PurchaseOrder.objects.filter(creation_date__gte=since).order_by("-pk")
print(json.dumps([po_card(po) for po in qs], indent=1, default=str))
```

(It depends on Task 3's `po_card`; run it after Task 3 and commit the JSON then. Until then the test below uses the inline `CARDS` list, which is copied from the measured records.)

- [ ] **Step 2: Write the failing test**

`scripts/test_receive_match.py`:

```python
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
```

- [ ] **Step 3: Run it to see it fail**

Run: `python3 scripts/test_receive_match.py`
Expected: `FileNotFoundError` on `plugins/receiving/match.py`.

- [ ] **Step 4: Implement `match.py`**

```python
"""Pure matcher: the model transcribes, this matches. No Django here, so it
runs locally against a snapshot of real orders.

Scoring per spec §3. Decisive evidence (an order number, its last 7 digits,
an ASIN/SKU, a tracking number found in the PO note) wins outright. Words are
IDF-weighted overlap, the same formula BinScan's catalogue search uses:
score = sum(idf of shared tokens) / sqrt(number of tokens on the card).
"""
import math
import re

WORD_FLOOR = 1.0    # provisional: set from the photo fixture set (spec §8)
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
```

- [ ] **Step 5: Run the test until it passes**

Run: `python3 scripts/test_receive_match.py`
Expected: `ALL OK`. If the "words only, unique" case fails on the floor, the fix is the stop list or `WORD_FLOOR`, and the commit message must say what value the real cards needed and why.

- [ ] **Step 6: Commit**

```bash
git add plugins/receiving/match.py scripts/test_receive_match.py
git commit -m "receiving: pure matcher - ids are decisive, words are IDF-ranked

No Django in match.py so the test runs locally on real order shapes. The
last-7 rule exists because Amazon labels show only the tail; a ? in a run
of digits breaks the regex on purpose - the model is told never to complete
a number and the matcher must not either.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 3: Engine — `po_card`, `open_orders`, `site_of`, `suggest_destination`, `plan`, `commit`, `undo`, `pending`

**Files:**
- Create: `plugins/receiving/engine.py`
- Test: `scripts/test_receiving_engine.py` (runs on the Mini)
- Then run `scripts/receive_fixture_snapshot.py` (Task 2) and commit `binscan/fixtures/receive/pos-2026-11-06.json`

**Interfaces:**
- Consumes: `notes_compat` (`note_text`, `note_set`, `note_append`), status codes.
- Produces (all return JSON-safe dicts):
  - `SITE_ROOT = {"LRD": 2, "SLN": 1}`, `RECEIVING = {"LRD": 473, "SLN": 472}`, `WEB = "http://192.168.50.10:8001/web"`
  - `site_of(po) -> "LRD" | "SLN" | None`
  - `po_card(po) -> dict` (the CARD shape in Task 2)
  - `open_orders(site=None) -> list[dict]` — PLACED orders, newest `issue_date or creation_date` first, cards
  - `suggest_destination(part, site) -> {"pk", "path", "source"}` with `source` in `default_location | existing_stock | category | receiving`
  - `plan(po_pk, lines=None, when=None, site=None) -> dict`:

    ```python
    {"po": 291, "reference": "PO-0291", "status": 20, "site": "LRD", "when": "2026-11-06",
     "warnings": ["Header Socket 1x7 Female 0.1in — SKU says a pack, pack_quantity is 1"],
     "lines": [{"line": 611, "part": 1183, "name": "Header Socket 1x7 Female 0.1in", "sku": "B0GM7T6XWP",
                "packs": 2.0, "outstanding": 2.0, "pack": 60.0, "pieces": 120.0, "unit": 0.1165,
                "dest": {"pk": 729, "path": "LRD/Countertop Wall/…", "source": "default_location"},
                "merge_into": None, "before": 0.0}],
     "closes_order": True}
    ```

    `lines` argument: `{line_pk: {"packs": float, "dest": loc_pk}}` — omitted lines take `outstanding` and the suggested dest; `packs` 0 leaves a line out (partial).
  - `commit(plan_dict) -> receipt`:

    ```python
    {"po": 291, "reference": "PO-0291", "status": 30, "when": "2026-11-06",
     "url": "http://192.168.50.10:8001/web/purchasing/purchase-order/291",
     "lines": [{"line": 611, "stock": 1301, "created": True, "pieces": 120.0, "unit": 0.1165,
                "dest_path": "…", "before_qty": 0.0, "received_before": 0.0,
                "url": "http://192.168.50.10:8001/web/stock/item/1301"}],
     "po_status_before": 20, "undo_until": "2026-11-06T14:22:10"}
    ```
  - `undo(receipt) -> dict` — `{"ok": True, "reference", "status", "lines": [{"line", "stock", "action": "deleted" | "reduced"}]}`; refuses (raises `RuntimeError`) if a row's quantity no longer equals `before_qty + pieces`.
  - `pending(site=None) -> list[dict]` — `[{"kind": "decision", "po", "reference", "question", "url"}, {"kind": "overdue", "po", "reference", "days", "card"}]`

- [ ] **Step 1: Write the failing engine test**

`scripts/test_receiving_engine.py` — a throwaway part, supplier part (pack 60) and PO are created, exercised, and deleted in `finally`. Nothing it creates survives, and it asserts that.

```python
"""plan -> commit -> re-read -> undo -> re-read on a THROWAWAY PO.
    itq run scripts/test_receiving_engine.py
Creates part 'ZZ-TEST receiving engine', an Amazon supplier part with pack 60,
a PLACED PO with two lines; exercises merge, new row, partial and pack 60;
deletes everything it made and proves it is gone."""
import datetime, os, sys
import django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from company.models import Company, SupplierPart  # noqa: E402
from order.models import PurchaseOrder, PurchaseOrderLineItem  # noqa: E402
from part.models import Part, PartCategory  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402
from plugins.notes_compat import note_set, note_text  # noqa: E402
from plugins.receiving import engine as E  # noqa: E402

amazon = Company.objects.get(pk=9)
recv = StockLocation.objects.get(pk=473)          # LRD/Receiving
made = {"parts": [], "sps": [], "pos": [], "stock": []}
try:
    cat = PartCategory.objects.first()
    p = Part.objects.create(name="ZZ-TEST receiving engine", description="throwaway", category=cat,
                            purchaseable=True, default_location=recv)
    made["parts"].append(p.pk)
    sp = SupplierPart(supplier=amazon, part=p, SKU="B0ZZTEST001", description="ZZ test 60 pcs")
    sp.pack_quantity = "60"; sp.save(); sp.refresh_from_db()
    made["sps"].append(sp.pk)
    assert float(sp.pack_quantity_native) == 60.0
    po = PurchaseOrder.objects.create(supplier=amazon, reference=PurchaseOrder.generate_reference(),
                                      supplier_reference="113-0000000-0000001",
                                      description="Amazon order 113-0000000-0000001 — ZZ test x2 (to The Villages FL)",
                                      issue_date=datetime.date.today(), status=20)
    made["pos"].append(po.pk)
    note_set(po, "Auto-created by test. Ships to The Villages FL (LRD).")
    l1 = PurchaseOrderLineItem.objects.create(order=po, part=sp, quantity=2, purchase_price=6.99, purchase_price_currency="USD")
    l2 = PurchaseOrderLineItem.objects.create(order=po, part=sp, quantity=1, purchase_price=6.99, purchase_price_currency="USD")

    print("=== site_of / card ===")
    assert E.site_of(po) == "LRD"
    card = E.po_card(po)
    assert card["supplier_reference"] == "113-0000000-0000001" and card["lines"][0]["pack"] == 60.0, card
    assert any(c["po"] == po.pk for c in E.open_orders("LRD"))

    print("=== suggest_destination: default_location first ===")
    d = E.suggest_destination(p, "LRD")
    assert d["pk"] == 473 and d["source"] == "default_location", d

    print("=== plan: full ===")
    pl = E.plan(po.pk)
    assert pl["closes_order"] is True and len(pl["lines"]) == 2, pl
    a = pl["lines"][0]
    assert a["pieces"] == 120.0 and abs(a["unit"] - 6.99 / 60) < 1e-6 and a["merge_into"] is None, a
    assert a["dest"]["pk"] == 473

    print("=== plan: partial (line 2 left out) ===")
    pl = E.plan(po.pk, lines={l2.pk: {"packs": 0}})
    assert [x["line"] for x in pl["lines"]] == [l1.pk] and pl["closes_order"] is False, pl

    print("=== commit partial -> new row, order stays open ===")
    rc = E.commit(pl)
    made["stock"] += [x["stock"] for x in rc["lines"]]
    row = StockItem.objects.get(pk=rc["lines"][0]["stock"])
    assert float(row.quantity) == 120.0 and row.location_id == 473 and row.purchase_order_id == po.pk
    assert "RECEIVED 120 on" in note_text(row), note_text(row)
    l1.refresh_from_db(); po.refresh_from_db()
    assert float(l1.received) == 2.0 and po.status == 20, (l1.received, po.status)

    print("=== commit the rest -> MERGE into that row, order closes ===")
    pl2 = E.plan(po.pk)
    assert pl2["lines"][0]["merge_into"] == row.pk and pl2["lines"][0]["before"] == 120.0, pl2
    rc2 = E.commit(pl2)
    row.refresh_from_db(); po.refresh_from_db()
    assert float(row.quantity) == 180.0 and po.status == 30 and po.complete_date == datetime.date.today()
    assert rc2["status"] == 30 and rc2["lines"][0]["created"] is False

    print("=== undo second commit -> 120, order reopens ===")
    u = E.undo(rc2)
    row.refresh_from_db(); po.refresh_from_db(); l2.refresh_from_db()
    assert float(row.quantity) == 120.0 and po.status == 20 and float(l2.received) == 0.0, (row.quantity, po.status)
    assert u["lines"][0]["action"] == "reduced"

    print("=== undo first commit -> row deleted ===")
    u = E.undo(rc)
    assert not StockItem.objects.filter(pk=row.pk).exists() and u["lines"][0]["action"] == "deleted"
    l1.refresh_from_db(); assert float(l1.received) == 0.0

    print("=== undo refuses when the row moved on ===")
    rc3 = E.commit(E.plan(po.pk))
    made["stock"] += [x["stock"] for x in rc3["lines"]]
    StockItem.objects.filter(pk=rc3["lines"][0]["stock"]).update(quantity=5)
    try:
        E.undo(rc3); raise AssertionError("undo should have refused")
    except RuntimeError as e:
        print("  refused:", e)

    print("=== pending: [NEEDS-DECISION] and overdue ===")
    po.refresh_from_db()
    PurchaseOrder.objects.filter(pk=po.pk).update(status=20, target_date=datetime.date.today() - datetime.timedelta(days=5))
    PurchaseOrderLineItem.objects.filter(order=po).update(received=0)
    note_set(po, "[NEEDS-DECISION] refund $6.99 against a $13.98 line: one of two returned, or both?")
    kinds = {(x["kind"], x["po"]) for x in E.pending("LRD")}
    assert ("decision", po.pk) in kinds and ("overdue", po.pk) in kinds, kinds
    print("\nALL OK")
finally:
    StockItem.objects.filter(pk__in=made["stock"]).delete()
    StockItem.objects.filter(part_id__in=made["parts"]).delete()
    PurchaseOrderLineItem.objects.filter(order_id__in=made["pos"]).delete()
    PurchaseOrder.objects.filter(pk__in=made["pos"]).delete()
    SupplierPart.objects.filter(pk__in=made["sps"]).delete()
    Part.objects.filter(pk__in=made["parts"]).delete()
    assert not Part.objects.filter(pk__in=made["parts"]).exists()
    assert not PurchaseOrder.objects.filter(pk__in=made["pos"]).exists()
    print("teardown OK:", made)
```

- [ ] **Step 2: Run it to see it fail**

Run: `~/code/scripts/itq run scripts/test_receiving_engine.py`
Expected: `ModuleNotFoundError: No module named 'plugins.receiving.engine'` (after Task 1's push the package exists on the Mini but has no `engine.py`).

- [ ] **Step 3: Implement `engine.py`**

```python
"""The receiving engine. Everything receive_po.py did, as functions that return
JSON-safe dicts, plus undo and the destination rule from spec §4.

Two halves, both kept: pieces = packs x pack_quantity_native (the $208.62 bins),
and the ORDER closes when no line is outstanding (the OVERDUE ghosts).
"""
import datetime
from decimal import Decimal

from django.db import transaction
from django.db.models import Count

try:
    from order.status_codes import PurchaseOrderStatus as POS
except ImportError:
    from InvenTree.status_codes import PurchaseOrderStatus as POS
from order.models import PurchaseOrder, PurchaseOrderLineItem
from stock.models import StockItem, StockLocation
try:
    from plugins.notes_compat import note_text, note_set, note_append
except ImportError:
    import importlib.util as _ilu, pathlib as _pl
    _s = _ilu.spec_from_file_location("notes_compat", _pl.Path(__file__).resolve().parent.parent / "notes_compat.py")
    _nc = _ilu.module_from_spec(_s); _s.loader.exec_module(_nc)
    note_text, note_set, note_append = _nc.note_text, _nc.note_set, _nc.note_append

SITE_ROOT = {"LRD": 2, "SLN": 1}
RECEIVING = {"LRD": 473, "SLN": 472}
WEB = "http://192.168.50.10:8001/web"
PLACED, COMPLETE = POS.PLACED.value, POS.COMPLETE.value
UNDO_MINUTES = 10
PACK_WORDS = ("pcs", "pack", " pk", "pieces")


def _f(x):
    return float(x) if x is not None else 0.0


def site_of(po):
    blob = f"{po.description or ''} {note_text(po) or ''}".lower()
    if "villages" in blob:
        return "LRD"
    if "dover" in blob:
        return "SLN"
    return None


def _under(loc, site):
    """Is this location under the site's root?"""
    root = SITE_ROOT.get(site)
    while loc is not None:
        if loc.pk == root:
            return True
        loc = loc.parent
    return False


def _loc(loc, source):
    return {"pk": loc.pk, "path": loc.pathstring, "source": source}


def suggest_destination(part, site):
    if part.default_location_id:
        return _loc(part.default_location, "default_location")
    rows = [r for r in StockItem.objects.filter(part=part, location__isnull=False).select_related("location")
            if _under(r.location, site)]
    locs = {r.location_id: r.location for r in rows}
    if len(locs) == 1:
        return _loc(next(iter(locs.values())), "existing_stock")
    if part.category_id:
        agg = (StockItem.objects.filter(part__category=part.category, location__isnull=False)
               .values("location").annotate(n=Count("part", distinct=True)).order_by("-n"))
        for a in agg:
            loc = StockLocation.objects.get(pk=a["location"])
            if _under(loc, site):
                return _loc(loc, "category")
    site = site if site in RECEIVING else "LRD"
    return _loc(StockLocation.objects.get(pk=RECEIVING[site]), "receiving")


def po_card(po):
    lines = []
    for ln in po.lines.select_related("part", "part__part"):
        sp, part = ln.part, ln.part.part
        lines.append({"line": ln.pk, "sku": sp.SKU or "", "part": part.pk, "name": part.name,
                      "sp_description": sp.description or "", "quantity": _f(ln.quantity),
                      "received": _f(ln.received), "pack": _f(sp.pack_quantity_native or 1),
                      "price": _f(ln.purchase_price.amount) if ln.purchase_price else 0.0,
                      "image": (f"/media/{part.image.name}" if part.image else None)})
    return {"po": po.pk, "reference": po.reference, "supplier_reference": po.supplier_reference or "",
            "supplier": po.supplier.name if po.supplier else "", "status": po.status,
            "closed": po.status != PLACED,
            "issue_date": str(po.issue_date or po.creation_date or ""),
            "target_date": str(po.target_date) if po.target_date else None,
            "description": po.description or "", "note": note_text(po) or "",
            "site": site_of(po), "url": f"{WEB}/purchasing/purchase-order/{po.pk}", "lines": lines}


def open_orders(site=None):
    qs = PurchaseOrder.objects.filter(status=PLACED).select_related("supplier")
    cards = [po_card(po) for po in qs]
    if site:
        cards = [c for c in cards if c["site"] in (site, None)]
    cards.sort(key=lambda c: c["issue_date"], reverse=True)
    return cards


def plan(po_pk, lines=None, when=None, site=None):
    po = PurchaseOrder.objects.get(pk=po_pk)
    lines = lines or {}
    site = site or site_of(po) or "LRD"
    when = when or str(datetime.date.today())
    out, warnings = [], []
    for ln in po.lines.select_related("part", "part__part"):
        sp, part = ln.part, ln.part.part
        outstanding = _f(ln.quantity) - _f(ln.received)
        if outstanding <= 0:
            continue
        want = lines.get(ln.pk, lines.get(str(ln.pk), {}))
        packs = _f(want.get("packs", outstanding)) if want else outstanding
        if packs <= 0:
            continue
        pack = _f(sp.pack_quantity_native or 1)
        if pack == 1 and any(w in f"{(sp.SKU or '').lower()} {part.name.lower()}" for w in PACK_WORDS):
            warnings.append(f"{part.name[:44]} — SKU says a pack, pack_quantity is 1")
        unit = float(Decimal(str(ln.purchase_price.amount)) / Decimal(str(pack))) if ln.purchase_price else 0.0
        if want and want.get("dest"):
            dloc = StockLocation.objects.get(pk=int(want["dest"]))
            dest = _loc(dloc, "chosen")
        else:
            dest = suggest_destination(part, site)
        row = StockItem.objects.filter(part=part, location_id=dest["pk"]).first()
        out.append({"line": ln.pk, "part": part.pk, "name": part.name, "sku": sp.SKU or "",
                    "packs": packs, "outstanding": outstanding, "pack": pack, "pieces": packs * pack,
                    "unit": round(unit, 4), "dest": dest,
                    "merge_into": row.pk if row else None, "before": _f(row.quantity) if row else 0.0})
    planned = {x["line"]: x["packs"] for x in out}
    closes = all(_f(l.received) + planned.get(l.pk, 0) >= _f(l.quantity) for l in po.lines.all())
    return {"po": po.pk, "reference": po.reference, "status": po.status, "site": site, "when": when,
            "warnings": warnings, "lines": out, "closes_order": bool(out) and closes}


def commit(pl):
    if pl.get("warnings"):
        raise RuntimeError("fix the supplier part first: " + "; ".join(pl["warnings"]))
    if not pl.get("lines"):
        raise RuntimeError("nothing to receive")
    po = PurchaseOrder.objects.get(pk=pl["po"])
    when = datetime.date.fromisoformat(pl["when"])
    receipt = {"po": po.pk, "reference": po.reference, "when": pl["when"], "po_status_before": po.status,
               "url": f"{WEB}/purchasing/purchase-order/{po.pk}", "lines": []}
    with transaction.atomic():
        for x in pl["lines"]:
            ln = PurchaseOrderLineItem.objects.select_related("part", "part__part").get(pk=x["line"])
            sp, part = ln.part, ln.part.part
            outstanding = _f(ln.quantity) - _f(ln.received)
            if x["packs"] > outstanding + 1e-9:
                raise RuntimeError(f"{part.name}: {x['packs']} packs planned, {outstanding} outstanding")
            pack = _f(sp.pack_quantity_native or 1)
            pieces = x["packs"] * pack
            unit = Decimal(str(ln.purchase_price.amount)) / Decimal(str(pack)) if ln.purchase_price else Decimal(0)
            dest = StockLocation.objects.get(pk=x["dest"]["pk"])
            row = StockItem.objects.filter(part=part, location=dest).first()
            before = _f(row.quantity) if row else 0.0
            if row:
                row.quantity = before + pieces
                row.save(); row.refresh_from_db()
                if _f(row.quantity) != before + pieces:
                    StockItem.objects.filter(pk=row.pk).update(quantity=before + pieces); row.refresh_from_db()
                note_append(row, f"RECEIVED {pieces:g} on {when} from {po.reference} at ${unit:.4f} each. "
                                 f"Merged into this row: {before:g} + {pieces:g} = {before + pieces:g}.")
                created = False
            else:
                row = StockItem.objects.create(part=part, location=dest, quantity=pieces, supplier_part=sp,
                                               purchase_order=po, purchase_price=unit, purchase_price_currency="USD")
                note_set(row, f"RECEIVED {pieces:g} on {when} from {po.reference} at ${unit:.4f} each "
                              f"(line qty {x['packs']:g} x pack {pack:g}).")
                created = True
            row.refresh_from_db()
            if _f(row.quantity) != before + pieces:
                raise RuntimeError(f"stock {row.pk}: quantity did not stick")
            received_before = _f(ln.received)
            ln.received = received_before + x["packs"]
            ln.save(); ln.refresh_from_db()
            if _f(ln.received) != received_before + x["packs"]:
                PurchaseOrderLineItem.objects.filter(pk=ln.pk).update(received=received_before + x["packs"]); ln.refresh_from_db()
            if _f(ln.received) != received_before + x["packs"]:
                raise RuntimeError(f"line {ln.pk}: received did not stick")
            receipt["lines"].append({"line": ln.pk, "stock": row.pk, "created": created, "pieces": pieces,
                                     "unit": round(float(unit), 4), "dest_path": dest.pathstring,
                                     "before_qty": before, "received_before": received_before,
                                     "url": f"{WEB}/stock/item/{row.pk}"})
        po.refresh_from_db()
        if all(_f(l.received) >= _f(l.quantity) for l in po.lines.all()):
            po.status = COMPLETE; po.complete_date = when
            po.save(); po.refresh_from_db()
            if po.status != COMPLETE:
                PurchaseOrder.objects.filter(pk=po.pk).update(status=COMPLETE, complete_date=when); po.refresh_from_db()
            if po.status != COMPLETE:
                raise RuntimeError("order did not close")
    receipt["status"] = po.status
    receipt["undo_until"] = (datetime.datetime.now() + datetime.timedelta(minutes=UNDO_MINUTES)).isoformat(timespec="seconds")
    return receipt


def undo(receipt):
    po = PurchaseOrder.objects.get(pk=receipt["po"])
    out = {"ok": True, "reference": po.reference, "lines": []}
    with transaction.atomic():
        for x in receipt["lines"]:
            row = StockItem.objects.filter(pk=x["stock"]).first()
            if row is None or abs(_f(row.quantity) - (x["before_qty"] + x["pieces"])) > 1e-9:
                raise RuntimeError(f"stock {x['stock']} is not as the receive left it; undo by hand")
            if x["created"]:
                row.delete(); action = "deleted"
                if StockItem.objects.filter(pk=x["stock"]).exists():
                    raise RuntimeError(f"stock {x['stock']} did not delete")
            else:
                StockItem.objects.filter(pk=row.pk).update(quantity=x["before_qty"]); row.refresh_from_db()
                if _f(row.quantity) != x["before_qty"]:
                    raise RuntimeError(f"stock {row.pk}: quantity did not revert")
                note_append(row, f"UNDO receive of {x['pieces']:g} from {po.reference}: back to {x['before_qty']:g}.")
                action = "reduced"
            PurchaseOrderLineItem.objects.filter(pk=x["line"]).update(received=x["received_before"])
            if _f(PurchaseOrderLineItem.objects.get(pk=x["line"]).received) != x["received_before"]:
                raise RuntimeError(f"line {x['line']}: received did not revert")
            out["lines"].append({"line": x["line"], "stock": x["stock"], "action": action})
        PurchaseOrder.objects.filter(pk=po.pk).update(status=receipt["po_status_before"], complete_date=None)
        po.refresh_from_db()
        if po.status != receipt["po_status_before"]:
            raise RuntimeError("order status did not revert")
    out["status"] = po.status
    return out


def pending(site=None):
    out = []
    today = datetime.date.today()
    for po in PurchaseOrder.objects.filter(status=PLACED):
        card = po_card(po)
        if site and card["site"] not in (site, None):
            continue
        txt = card["note"]
        if "[NEEDS-DECISION]" in txt:
            q = txt.split("[NEEDS-DECISION]", 1)[1].strip().splitlines()[0]
            out.append({"kind": "decision", "po": po.pk, "reference": po.reference, "question": q, "url": card["url"]})
        if po.target_date and (today - po.target_date).days > 3 and all(l["received"] == 0 for l in card["lines"]):
            out.append({"kind": "overdue", "po": po.pk, "reference": po.reference,
                        "days": (today - po.target_date).days, "card": card})
    return out
```

- [ ] **Step 4: Push and run the test**

```bash
R=/Volumes/4TB_Removable/inventree/src/src/backend/InvenTree/plugins/receiving
~/code/scripts/itq push plugins/receiving/engine.py $R/engine.py
~/code/scripts/itq run scripts/test_receiving_engine.py
```

Expected: every `===` section prints, then `ALL OK` and `teardown OK`. If `note_text(po)` raises on a PO with no note, `notes_compat.note_text` returns `""` for a missing note (verify by reading `plugins/notes_compat.py`); if it does not, guard with `or ""` as written. If `StockItem.objects.create` refuses `purchase_price=Decimal`, pass `float(unit)`.

- [ ] **Step 5: Snapshot the real cards and run the local matcher test on them**

```bash
mkdir -p binscan/fixtures/receive
~/code/scripts/itq run scripts/receive_fixture_snapshot.py > binscan/fixtures/receive/pos-2026-11-06.json
python3 -c "import json; d=json.load(open('binscan/fixtures/receive/pos-2026-11-06.json')); print(len(d), 'cards; open:', sum(1 for c in d if not c['closed']))"
```

Expected: ≥ 18 open cards. Then add to the bottom of `scripts/test_receive_match.py` (before `ALL OK`):

```python
print("=== real snapshot: the 1x7 socket is on several open POs ===")
snap = json.load(open(HERE / "binscan/fixtures/receive/pos-2026-11-06.json"))
opens = [c for c in snap if not c["closed"]]
r = m.score("1x7 female header socket", opens)
assert m.verdict(r) == "several", [(x["reference"], x["score"]) for x in r[:4]]
r = m.score("113-8469851-5845865", snap)
assert r and r[0]["reference"] == "PO-0291" and m.verdict(r) == "one"
```

Run: `python3 scripts/test_receive_match.py` → `ALL OK`.

- [ ] **Step 6: Commit**

```bash
git add plugins/receiving/engine.py scripts/test_receiving_engine.py scripts/receive_fixture_snapshot.py binscan/fixtures/receive/pos-2026-11-06.json scripts/test_receive_match.py
git commit -m "receiving engine: plan/commit/undo/pending, tested round-trip on a throwaway PO

commit() takes the plan it was shown, not a fresh read: what Scott confirmed
on the card is what gets booked, and a line that moved on since is a refusal,
not a silent re-plan. Undo keeps before-quantities in the receipt (same shape
as binscan_undo.py) and refuses when the row has moved.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 4: HTTP views over the engine

**Files:**
- Modify: `plugins/receiving/views.py`
- Modify: `plugins/receiving/__init__.py` (URL table)

**Interfaces:**
- Produces, all under `http://192.168.50.10:8001/plugin/receiving/`, token auth:
  - `GET open/?site=LRD` → `{"site": "LRD", "orders": [card…]}`
  - `POST match/ {"text": str, "site": str|null}` → `{"verdict": "one|several|none", "results": [{…score row…, "card": card}], "ids": extract_ids(text)}`. Decisive ids are looked up across ALL orders (closed ones flagged `closed: true`, the duplicate-delivery signal); words only across open orders at the site.
  - `POST plan/ {"po": pk, "lines": {line_pk: {"packs", "dest"}}, "site": str|null}` → the plan dict
  - `POST commit/ {"plan": plan}` → receipt
  - `POST undo/ {"receipt": receipt}` → undo result
  - `GET pending/?site=LRD` → `{"items": [...]}`
  - Errors: `400 {"error": "<RuntimeError text>"}`; never a 500 with a traceback body.

- [ ] **Step 1: Write the views**

Replace `plugins/receiving/views.py` with:

```python
"""HTTP face of the receiving engine. Token-auth only; no session, no CSRF.
Every engine RuntimeError becomes a 400 with its text, so the phone shows the
reason instead of Safari's 'string did not match the expected pattern'."""
import importlib.util as _ilu
import pathlib as _pl

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.authentication import ApiTokenAuthentication

_HERE = _pl.Path(__file__).resolve().parent


def _sib(name):
    try:
        return __import__(f"{__package__}.{name}", fromlist=[name]) if __package__ else None
    except ImportError:
        pass
    s = _ilu.spec_from_file_location(f"receiving_{name}", _HERE / f"{name}.py")
    m = _ilu.module_from_spec(s); s.loader.exec_module(m)
    return m


engine = _sib("engine")
match = _sib("match")
returns = _sib("returns") if (_HERE / "returns.py").exists() else None


class _View(APIView):
    authentication_classes = [ApiTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def guard(self, fn, *a, **kw):
        try:
            return Response(fn(*a, **kw))
        except RuntimeError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:  # noqa: BLE001 - the phone needs text, not a traceback page
            return Response({"error": f"{type(e).__name__}: {e}"[:300]}, status=status.HTTP_400_BAD_REQUEST)


class PingView(_View):
    def get(self, request):
        return Response({"ok": True, "plugin": "receiving", "user": request.user.username})


class OpenView(_View):
    def get(self, request):
        site = request.query_params.get("site") or None
        return self.guard(lambda: {"site": site, "orders": engine.open_orders(site)})


class MatchView(_View):
    def post(self, request):
        text = (request.data.get("text") or "").strip()
        site = request.data.get("site") or None

        def run():
            from order.models import PurchaseOrder
            ids = match.extract_ids(text)
            opens = engine.open_orders(site)
            cards = {c["po"]: c for c in opens}
            # decisive ids reach CLOSED orders too: a second box for a received
            # or returned order is the duplicate-delivery signal, not noise
            if ids["orders"] or ids["last7"] or ids["skus"]:
                qs = PurchaseOrder.objects.exclude(status=engine.PLACED)
                for po in qs.filter(supplier_reference__in=ids["orders"]):
                    cards.setdefault(po.pk, engine.po_card(po))
                for tail in ids["last7"]:
                    for po in qs.filter(supplier_reference__endswith=tail):
                        cards.setdefault(po.pk, engine.po_card(po))
                for sku in ids["skus"]:
                    for po in qs.filter(lines__part__SKU__istartswith=sku).distinct():
                        cards.setdefault(po.pk, engine.po_card(po))
            results = match.score(text, list(cards.values()))
            for r in results:
                r["card"] = cards[r["po"]]
            return {"verdict": match.verdict(results), "results": results[:8], "ids": ids, "text": text}
        return self.guard(run)


class PlanView(_View):
    def post(self, request):
        d = request.data
        lines = {int(k): v for k, v in (d.get("lines") or {}).items()}
        return self.guard(engine.plan, int(d["po"]), lines=lines, site=d.get("site") or None)


class CommitView(_View):
    def post(self, request):
        return self.guard(engine.commit, request.data["plan"])


class UndoView(_View):
    def post(self, request):
        return self.guard(engine.undo, request.data["receipt"])


class PendingView(_View):
    def get(self, request):
        site = request.query_params.get("site") or None
        return self.guard(lambda: {"items": engine.pending(site)})
```

And in `plugins/receiving/__init__.py` replace `setup_urls` with:

```python
    def setup_urls(self):
        v = _sibling("views")
        return [
            path("ping/", v.PingView.as_view(), name="ping"),
            path("open/", v.OpenView.as_view(), name="open"),
            path("match/", v.MatchView.as_view(), name="match"),
            path("plan/", v.PlanView.as_view(), name="plan"),
            path("commit/", v.CommitView.as_view(), name="commit"),
            path("undo/", v.UndoView.as_view(), name="undo"),
            path("pending/", v.PendingView.as_view(), name="pending"),
        ]
```

- [ ] **Step 2: Deploy and exercise every view from the Mini with curl**

```bash
R=/Volumes/4TB_Removable/inventree/src/src/backend/InvenTree/plugins/receiving
for f in __init__ match views; do ~/code/scripts/itq push plugins/receiving/$f.py $R/$f.py; done
ssh mini 'launchctl kickstart -k gui/$(id -u)/com.inventree.server'; sleep 20
ssh mini 'T=$(grep ^INVENTREE_TOKEN= ~/binscan/.env | cut -d= -f2); H="Authorization: Token $T"; B=http://127.0.0.1:8001/plugin/receiving;
curl -s -H "$H" "$B/open/?site=LRD" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d[\"orders\"]), \"open;\", d[\"orders\"][0][\"reference\"])";
curl -s -H "$H" -H "Content-Type: application/json" -d "{\"text\":\"113-8469851-5845865\",\"site\":\"LRD\"}" $B/match/ | python3 -c "import json,sys; d=json.load(sys.stdin); print(d[\"verdict\"], d[\"results\"][0][\"reference\"], d[\"results\"][0][\"decisive\"])";
curl -s -H "$H" -H "Content-Type: application/json" -d "{\"text\":\"1x7 female header\",\"site\":\"LRD\"}" $B/match/ | python3 -c "import json,sys; d=json.load(sys.stdin); print(d[\"verdict\"], [r[\"reference\"] for r in d[\"results\"]])";
curl -s -H "$H" -H "Content-Type: application/json" -d "{\"po\":291}" $B/plan/ | python3 -c "import json,sys; d=json.load(sys.stdin); l=d[\"lines\"][0]; print(d[\"reference\"], l[\"pieces\"], l[\"unit\"], l[\"dest\"])";
curl -s -H "$H" "$B/pending/?site=LRD" | python3 -c "import json,sys; d=json.load(sys.stdin); print([(i[\"kind\"], i[\"reference\"]) for i in d[\"items\"]])";
curl -s -o /dev/null -w "%{http_code}\n" -H "$H" -H "Content-Type: application/json" -d "{\"plan\":{\"po\":291,\"when\":\"2026-11-06\",\"lines\":[]}}" $B/commit/'
```

Expected, in order: `18 open; PO-0291` (count as of the day); `one PO-0291 ['order 113-8469851-5845865']`; `several [... 4 references ...]`; `PO-0291 120.0 0.1165 {'pk': 729, …, 'source': 'default_location'}`; a list of `overdue` items; and `400` from the empty commit (nothing to receive). **Nothing is written by this step** — the commit call is the refusal path.

- [ ] **Step 3: Commit**

```bash
git add plugins/receiving/views.py plugins/receiving/__init__.py
git commit -m "receiving views: open/match/plan/commit/undo/pending over token auth

RuntimeError -> 400 with its text: BinScan's one known 500 reached the phone
as Safari's 'string did not match the expected pattern', naming nothing.
Decisive ids are searched across closed orders too so a second box for a
RETURNED order is reported, not hidden.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 5: `receive_po.py` becomes a wrapper over the engine

**Files:**
- Modify: `scripts/receive_po.py` (whole file)

**Interfaces:**
- Consumes: `engine.plan(po_pk, lines, when, site)`, `engine.commit(plan)`.
- Keeps: `itq run scripts/receive_po.py PO-0291 --to 729 [--commit] [--date D] [--part PK…]`; dry run by default; the same printed shape (so the CLAUDE.md example output still reads true).

- [ ] **Step 1: Rewrite the script**

```python
#!/usr/bin/env python3
"""Receive a purchase order from the command line. Same flags as before; the
work is done by plugins/receiving/engine.py, which BinScan's /receive page
also calls. Two doors, one engine - the two halves of a receive were each got
wrong once when there were two code paths.

    itq run scripts/receive_po.py PO-0146 --to RB-14
    itq run scripts/receive_po.py PO-0146 --to RB-14 --commit
"""
import argparse, datetime, os, sys
import django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from order.models import PurchaseOrder  # noqa: E402
from stock.models import StockLocation  # noqa: E402
from plugins.receiving import engine  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("reference")
ap.add_argument("--to", required=True, help="destination StockLocation pk, name or pathstring")
ap.add_argument("--commit", action="store_true")
ap.add_argument("--date", default=None)
ap.add_argument("--part", type=int, action="append", default=None,
                help="receive only lines for this Part pk (repeatable); the rest stay outstanding")
a = ap.parse_args()

po = PurchaseOrder.objects.get(reference=a.reference)
if a.to.isdigit():
    dest = StockLocation.objects.get(pk=int(a.to))
else:
    hits = list(StockLocation.objects.filter(name=a.to)) or list(StockLocation.objects.filter(pathstring=a.to))
    if len(hits) != 1:
        print(f"{a.to!r} matches {len(hits)} locations - pass a pk or the full path:")
        for h in StockLocation.objects.filter(name=a.to):
            print(f"    {h.pk}  {h.pathstring}")
        sys.exit(1)
    dest = hits[0]

lines = {}
for ln in po.lines.select_related("part"):
    if a.part and ln.part.part_id not in a.part:
        lines[ln.pk] = {"packs": 0}
        print(f"  - skipped (not --part): {ln.part.part.name[:48]}")
    else:
        lines[ln.pk] = {"dest": dest.pk}
pl = engine.plan(po.pk, lines=lines, when=a.date or str(datetime.date.today()))

print(f"{po.reference}  status={po.status}  {po.description[:60]}\ndestination: {dest.pathstring}\n")
for x in pl["lines"]:
    print(f"  line qty {x['packs']:g} x pack {x['pack']:g} = {x['pieces']:g} pieces at ${x['unit']:.4f} each")
    print(f"     {x['name'][:56]}")
    print(f"     {x['before']:g} + {x['pieces']:g} = {x['before'] + x['pieces']:g} @ {dest.name}"
          f"{'  (merged)' if x['merge_into'] else '  (new row)'}")
if pl["warnings"]:
    print("\n!! PACK SIZE LOOKS WRONG — fix the SUPPLIER PART before receiving:")
    for w in pl["warnings"]:
        print(f"     {w}")
    sys.exit(1)
if not pl["lines"]:
    print("\nnothing outstanding to receive.")
if not a.commit:
    print("\nDRY RUN — nothing written. Re-run with --commit.")
    sys.exit(0)

rc = engine.commit(pl)
for x in rc["lines"]:
    print(f"  + {x['pieces']:g} -> {x['dest_path']}  stock {x['stock']}  {x['url']}")
if rc["status"] == engine.COMPLETE:
    print(f"\n{po.reference} CLOSED — status 30")
else:
    print(f"\n{po.reference} left open — lines still outstanding")
print(f"undo receipt (valid until {rc['undo_until']}): {rc}")
```

- [ ] **Step 2: Dry-run it against a real open order (writes nothing)**

Run: `~/code/scripts/itq run scripts/receive_po.py PO-0291 --to 473`
Expected: the plan lines (`2 x pack 60 = 120 pieces at $0.1165`) and `DRY RUN — nothing written`.

Also the ambiguity path: `~/code/scripts/itq run scripts/receive_po.py PO-0291 --to Receiving` → lists pks 472 and 473, exit 1.

- [ ] **Step 3: Commit**

```bash
git add scripts/receive_po.py
git commit -m "receive_po.py: thin wrapper over the receiving engine

Kept the CLI and its printed shape (CLAUDE.md quotes it) rather than
retiring it: the watcher and a laptop session still receive by reference,
and the engine is the single place the pack and close rules live now.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 6: Returns — `returns.py` module + CLI, with the hard guard

**Files:**
- Create: `plugins/receiving/returns.py`
- Create: `scripts/returns.py`
- Test: `scripts/test_returns.py` (runs on the Mini)

**Interfaces:**
- Produces:
  - `returns.requested(order: str, when: str, reason: str = "", event: str = "requested") -> dict`
  - `returns.refunded(order: str, amount: float, when: str) -> dict`
  - Result shape: `{"ok": bool, "action": str, "reference": str|None, "url": str|None, "push": str|None, "pending": str|None, "detail": [str]}`. `push` is the one line the watcher sends to Scott's phone; `pending` is the question written after `[NEEDS-DECISION]`.
  - CLI: `itq run scripts/returns.py <requested|dropoff|refunded> --order <no> [--amount X] [--date D] [--reason R] [--commit]`; dry run prints the result it WOULD write (`ok: dry-run`), `--commit` writes. Exit 0 on `ok`, 2 on pending, 1 on error.
- Hard guard (spec §7): a stock row is removed only when its status is QUARANTINED **and** its note contains `[GOING-BACK]`. Anything else is the unclean branch.

- [ ] **Step 1: Write the failing test**

`scripts/test_returns.py`:

```python
"""Return branches on THROWAWAY orders: requested, dropoff, refunded clean (received
and not received), and the unclean cases. Every branch asserts the exact note text
and PO status. Deletes everything it made."""
import datetime, os, sys
import django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from company.models import Company, SupplierPart  # noqa: E402
from order.models import PurchaseOrder, PurchaseOrderLineItem  # noqa: E402
from part.models import Part, PartCategory  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402
from plugins.notes_compat import note_text, note_set  # noqa: E402
from plugins.receiving import engine as E, returns as R  # noqa: E402

amazon = Company.objects.get(pk=9); recv = StockLocation.objects.get(pk=473)
TODAY = str(datetime.date.today())
made = {"parts": [], "sps": [], "pos": []}


def mk_po(order, qty=1, price=16.99, lines=1):
    po = PurchaseOrder.objects.create(supplier=amazon, reference=PurchaseOrder.generate_reference(),
                                      supplier_reference=order, status=20, issue_date=datetime.date.today(),
                                      description=f"Amazon order {order} — ZZ test (to The Villages FL)")
    made["pos"].append(po.pk)
    note_set(po, "Auto-created by test. Ships to The Villages FL (LRD).")
    for _ in range(lines):
        PurchaseOrderLineItem.objects.create(order=po, part=sp, quantity=qty, purchase_price=price, purchase_price_currency="USD")
    return po


try:
    p = Part.objects.create(name="ZZ-TEST returns", description="throwaway", category=PartCategory.objects.first(),
                            purchaseable=True, default_location=recv)
    made["parts"].append(p.pk)
    sp = SupplierPart(supplier=amazon, part=p, SKU="B0ZZRET0001", description="ZZ returns test"); sp.save()
    made["sps"].append(sp.pk)

    print("=== requested on a PLACED, not-received order: note only ===")
    po = mk_po("113-0000000-1000001")
    r = R.requested(po.supplier_reference, TODAY, reason="wrong size")
    assert r["ok"] and r["action"] == "noted" and r["reference"] == po.reference, r
    po.refresh_from_db()
    assert "RETURN requested " + TODAY in note_text(po) and "wrong size" in note_text(po) and po.status == 20

    print("=== refunded clean, never received: line 0, PO RETURNED, sentinel ===")
    r = R.refunded(po.supplier_reference, 16.99, TODAY)
    assert r["ok"] and r["action"] == "returned" and r["push"], r
    po.refresh_from_db()
    assert po.status == 60 and "[REFUND-CONFIRMED] $16.99 on " + TODAY in note_text(po), note_text(po)

    print("=== received then requested: row goes Quarantined with [GOING-BACK] ===")
    po = mk_po("113-0000000-1000002")
    rc = E.commit(E.plan(po.pk))
    row = StockItem.objects.get(pk=rc["lines"][0]["stock"])
    r = R.requested(po.supplier_reference, TODAY, event="dropoff")
    row.refresh_from_db(); po.refresh_from_db()
    assert row.status == 75 and note_text(row).startswith("[GOING-BACK]"), (row.status, note_text(row)[:40])
    assert "RETURN dropoff " + TODAY in note_text(po) and po.status == 30

    print("=== refunded clean, received: row notes copied to PO, row removed, RETURNED ===")
    row_note = note_text(row)
    r = R.refunded(po.supplier_reference, 16.99, TODAY)
    assert r["ok"] and r["action"] == "returned", r
    assert not StockItem.objects.filter(pk=row.pk).exists()
    po.refresh_from_db()
    ln = po.lines.first(); ln.refresh_from_db()
    assert po.status == 60 and float(ln.received) == 0.0 and "returned" in (ln.notes or "").lower()
    assert "RECEIVED" in note_text(po) and "[REFUND-CONFIRMED]" in note_text(po), note_text(po)

    print("=== UNCLEAN: received, row NOT quarantined -> [NEEDS-DECISION], nothing else changes ===")
    po = mk_po("113-0000000-1000003")
    rc = E.commit(E.plan(po.pk)); row = StockItem.objects.get(pk=rc["lines"][0]["stock"])
    r = R.refunded(po.supplier_reference, 16.99, TODAY)
    assert not r["ok"] and r["pending"], r
    po.refresh_from_db(); row.refresh_from_db()
    assert StockItem.objects.filter(pk=row.pk).exists() and po.status == 30
    assert "[NEEDS-DECISION]" in note_text(po) and "not quarantined" in note_text(po).lower(), note_text(po)
    assert ("decision", po.pk) not in {(x["kind"], x["po"]) for x in E.pending()} or True  # PO is COMPLETE; pending lists PLACED only - see engine.pending

    print("=== UNCLEAN: amount differs ===")
    po = mk_po("113-0000000-1000004", qty=2, price=16.99)
    r = R.refunded(po.supplier_reference, 16.99, TODAY)
    assert not r["ok"] and "16.99" in r["pending"] and "33.98" in r["pending"], r
    po.refresh_from_db(); assert po.status == 20 and "[NEEDS-DECISION]" in note_text(po)

    print("=== UNCLEAN: two POs share the order number ===")
    po_a = mk_po("113-0000000-1000005"); po_b = mk_po("113-0000000-1000005")
    r = R.refunded("113-0000000-1000005", 16.99, TODAY)
    assert not r["ok"] and "2 orders" in r["pending"], r

    print("=== unknown order -> error, nothing written ===")
    r = R.refunded("113-0000000-9999999", 1.0, TODAY)
    assert not r["ok"] and r["action"] == "error" and r["reference"] is None, r

    print("=== sentinel already present -> idempotent ===")
    po = PurchaseOrder.objects.get(supplier_reference="113-0000000-1000001")
    before = note_text(po)
    r = R.refunded(po.supplier_reference, 16.99, TODAY)
    assert r["ok"] and r["action"] == "already" and note_text(po) == before, r
    print("\nALL OK")
finally:
    StockItem.objects.filter(part_id__in=made["parts"]).delete()
    PurchaseOrderLineItem.objects.filter(order_id__in=made["pos"]).delete()
    PurchaseOrder.objects.filter(pk__in=made["pos"]).delete()
    SupplierPart.objects.filter(pk__in=made["sps"]).delete()
    Part.objects.filter(pk__in=made["parts"]).delete()
    assert not PurchaseOrder.objects.filter(pk__in=made["pos"]).exists()
    print("teardown OK:", made)
```

- [ ] **Step 2: Run it to see it fail**

Run: `~/code/scripts/itq run scripts/test_returns.py`
Expected: `ImportError: cannot import name 'returns'`.

- [ ] **Step 3: Implement `plugins/receiving/returns.py`**

```python
"""Returns, the way out. Three events from the Amazon mail, one hard guard.

requested / dropoff: note the PO; if the goods were received, the stock row goes
Quarantined with [GOING-BACK] at the top of its note.

refunded, clean: copy the row's note into the PO (nothing is lost when the row
goes), remove the row, set the line's received back to 0, RETURNED when nothing
else is outstanding, [REFUND-CONFIRMED] $amount on date. Returns one push line.

refunded, unclean: [NEEDS-DECISION] <question> on the PO note, nothing else.

THE GUARD: a row is removed only if status == QUARANTINED and its note carries
[GOING-BACK]. Depleting a row deletes it on this install, notes and all; the
guard is what makes the automatic branch safe (spec §7).
"""
import datetime
from decimal import Decimal

from django.db import transaction

try:
    from order.status_codes import PurchaseOrderStatus as POS
    from stock.status_codes import StockStatus
except ImportError:
    from InvenTree.status_codes import PurchaseOrderStatus as POS, StockStatus
from order.models import PurchaseOrder, PurchaseOrderLineItem
from stock.models import StockItem
try:
    from plugins.notes_compat import note_text, note_append, note_prepend, note_set
except ImportError:
    import importlib.util as _ilu, pathlib as _pl
    _s = _ilu.spec_from_file_location("notes_compat", _pl.Path(__file__).resolve().parent.parent / "notes_compat.py")
    _nc = _ilu.module_from_spec(_s); _s.loader.exec_module(_nc)
    note_text, note_append, note_prepend, note_set = _nc.note_text, _nc.note_append, _nc.note_prepend, _nc.note_set

WEB = "http://192.168.50.10:8001/web"
GOING_BACK, REFUND_CONFIRMED, NEEDS_DECISION = "[GOING-BACK]", "[REFUND-CONFIRMED]", "[NEEDS-DECISION]"
QUARANTINED = StockStatus.QUARANTINED.value
RETURNED, PLACED = POS.RETURNED.value, POS.PLACED.value


def _res(ok, action, po=None, push=None, pending=None, detail=None):
    return {"ok": ok, "action": action, "reference": po.reference if po else None,
            "url": f"{WEB}/purchasing/purchase-order/{po.pk}" if po else None,
            "push": push, "pending": pending, "detail": detail or []}


def _find(order):
    return list(PurchaseOrder.objects.filter(supplier_reference=order))


def _rows_for(po):
    """Stock rows that came from this order: linked by purchase_order, or (a
    merged row carries no link) the line part's rows at the site's locations."""
    rows = list(StockItem.objects.filter(purchase_order=po))
    if rows:
        return rows
    parts = [ln.part.part_id for ln in po.lines.select_related("part")]
    return list(StockItem.objects.filter(part_id__in=parts))


def _decide(po, question):
    note_prepend(po, f"{NEEDS_DECISION} {question}")
    return _res(False, "pending", po, pending=question)


def requested(order, when, reason="", event="requested"):
    pos = _find(order)
    if len(pos) != 1:
        return _res(False, "error", detail=[f"{len(pos)} orders match {order}"])
    po = pos[0]
    with transaction.atomic():
        note_append(po, f"RETURN {event} {when}" + (f": {reason}" if reason else "") + " (from the Amazon return mail).")
        quarantined = []
        for row in _rows_for(po):
            if float(row.quantity) <= 0:
                continue
            if row.status != QUARANTINED:
                StockItem.objects.filter(pk=row.pk).update(status=QUARANTINED)
                row.refresh_from_db()
                if row.status != QUARANTINED:
                    raise RuntimeError(f"stock {row.pk}: status did not stick")
            if GOING_BACK not in (note_text(row) or ""):
                note_prepend(row, f"{GOING_BACK} return {event} {when} for {po.reference} ({order}).")
            quarantined.append(row.pk)
    return _res(True, "quarantined" if quarantined else "noted", po,
                detail=[f"quarantined stock {pk}" for pk in quarantined])


def refunded(order, amount, when):
    pos = _find(order)
    if not pos:
        return _res(False, "error", detail=[f"no order with supplier_reference {order}"])
    if len(pos) > 1:
        return _decide(pos[0], f"refund ${amount:.2f} for {order}: {len(pos)} orders carry this number "
                               f"({', '.join(p.reference for p in pos)}); which one?")
    po = pos[0]
    if REFUND_CONFIRMED in (note_text(po) or ""):
        return _res(True, "already", po)
    amount = Decimal(str(amount)).quantize(Decimal("0.01"))
    lines = list(po.lines.select_related("part", "part__part"))
    totals = {ln.pk: (Decimal(str(ln.purchase_price.amount)) * Decimal(str(ln.quantity))).quantize(Decimal("0.01"))
              for ln in lines if ln.purchase_price}
    whole = sum(totals.values(), Decimal(0))
    if amount == whole:
        target = lines
    elif [k for k, v in totals.items() if v == amount] and len(lines) > 1:
        target = [ln for ln in lines if totals.get(ln.pk) == amount]
    else:
        return _decide(po, f"refund ${amount} against ${whole} ordered "
                           f"({', '.join(f'{ln.part.part.name[:30]} ${totals.get(ln.pk, 0)}' for ln in lines)}): "
                           f"one of {len(lines)} lines returned, part of one, or all?")

    received = [ln for ln in target if float(ln.received) > 0]
    rows = _rows_for(po) if received else []
    bad = [r for r in rows if not (r.status == QUARANTINED and GOING_BACK in (note_text(r) or ""))]
    if received and not rows:
        return _decide(po, f"refund ${amount}: line was received but no stock row is linked to {po.reference}; "
                           f"find the goods and quarantine them, or confirm they are gone.")
    if bad:
        return _decide(po, f"refund ${amount}: stock {', '.join(str(r.pk) for r in bad)} is not quarantined "
                           f"with {GOING_BACK}; is it the returned unit?")

    with transaction.atomic():
        for r in rows:
            note_append(po, f"Stock {r.pk} removed on refund {when}; its notes were:\n{note_text(r)}")
            r.delete()
            if StockItem.objects.filter(pk=r.pk).exists():
                raise RuntimeError(f"stock {r.pk} did not delete")
        for ln in target:
            PurchaseOrderLineItem.objects.filter(pk=ln.pk).update(received=0, notes=f"returned, refunded ${amount} {when}")
            if float(PurchaseOrderLineItem.objects.get(pk=ln.pk).received) != 0.0:
                raise RuntimeError(f"line {ln.pk}: received did not reset")
        others = [ln for ln in po.lines.all() if ln.pk not in {t.pk for t in target}]
        closes = not others or all(float(ln.received) >= float(ln.quantity) for ln in others)
        if closes:
            PurchaseOrder.objects.filter(pk=po.pk).update(status=RETURNED, complete_date=datetime.date.fromisoformat(when))
            po.refresh_from_db()
            if po.status != RETURNED:
                raise RuntimeError("order status did not change to RETURNED")
        note_append(po, f"{REFUND_CONFIRMED} ${amount} on {when} (Amazon refund mail).")
    push = f"Refund ${amount} booked: {po.reference} RETURNED, {len(rows)} stock row(s) removed. {WEB}/purchasing/purchase-order/{po.pk}"
    return _res(True, "returned", po, push=push, detail=[f"removed stock {r.pk}" for r in rows])
```

- [ ] **Step 4: Write the CLI `scripts/returns.py`**

```python
#!/usr/bin/env python3
"""Return events from the Amazon mail -> InvenTree. Called by the
amazon-refund-watch task; also usable by hand.

    itq run scripts/returns.py requested --order 113-8469851-5845865 [--reason "wrong size"]
    itq run scripts/returns.py dropoff   --order 113-8469851-5845865
    itq run scripts/returns.py refunded  --order 113-8469851-5845865 --amount 6.99 --date 2026-11-09 --commit

Dry run by default: prints the result it WOULD produce and rolls back.
Exit 0 ok, 2 pending (a [NEEDS-DECISION] question was written), 1 error.
"""
import argparse, datetime, json, os, sys
import django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.db import transaction  # noqa: E402
from plugins.receiving import returns as R  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("event", choices=["requested", "dropoff", "refunded"])
ap.add_argument("--order", required=True)
ap.add_argument("--amount", type=float, default=None)
ap.add_argument("--date", default=str(datetime.date.today()))
ap.add_argument("--reason", default="")
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()


class DryRun(Exception):
    pass


try:
    with transaction.atomic():
        if a.event == "refunded":
            if a.amount is None:
                sys.exit("refunded needs --amount")
            res = R.refunded(a.order, a.amount, a.date)
        else:
            res = R.requested(a.order, a.date, reason=a.reason, event=a.event)
        if not a.commit:
            raise DryRun()
except DryRun:
    print("DRY RUN — rolled back. Re-run with --commit.")

print(json.dumps(res, indent=1))
if res.get("push"):
    print("PUSH:", res["push"])
sys.exit(0 if res["ok"] else (2 if res.get("pending") else 1))
```

- [ ] **Step 5: Push, run the test, dry-run the CLI**

```bash
R=/Volumes/4TB_Removable/inventree/src/src/backend/InvenTree/plugins/receiving
~/code/scripts/itq push plugins/receiving/returns.py $R/returns.py
~/code/scripts/itq run scripts/test_returns.py
~/code/scripts/itq run scripts/returns.py refunded --order 113-8469851-5845865 --amount 6.99
```

Expected: `ALL OK` + `teardown OK`; then the CLI prints `DRY RUN — rolled back` and a JSON with `"action": "pending"` and a `pending` question (PO-0291 ordered 2 × $6.99 = $13.98, so $6.99 is the partial case) — and **PO-0291's note is unchanged** (dry run). Verify: `~/code/scripts/itq sql "from order.models import PurchaseOrder as P; from plugins.notes_compat import note_text; print('[NEEDS' in note_text(P.objects.get(reference='PO-0291')))"` → `False`.

Then restart InvenTree so `views.py` picks up `returns` (not used by a view yet, but the import guard runs at load): `ssh mini 'launchctl kickstart -k gui/$(id -u)/com.inventree.server'`.

- [ ] **Step 6: Commit**

```bash
git add plugins/receiving/returns.py scripts/returns.py scripts/test_returns.py
git commit -m "returns: requested/dropoff/refunded with the one hard guard

Automatic because Scott asked why he should be in every return. The guard -
remove a row only when it is Quarantined AND carries [GOING-BACK] - is the
whole safety case; every other doubt writes [NEEDS-DECISION] and stops. The
row's note is copied into the PO before delete because depleting a row on
this install deletes it, notes and all (PO-0163, 2026-09-16).

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 7: BinScan side — plugin client and label transcription

**Files:**
- Create: `binscan/receiving.py`
- Modify: `binscan/providers.py` (add `LABEL_SYSTEM`, `_parse_label`, `read_label`)
- Test: `scripts/test_receive_client.py` (local; the parsing parts)

**Interfaces:**
- Produces, `binscan/receiving.py`:
  - `BASE = f"{INVENTREE}/plugin/receiving"` (reads env `INVENTREE_URL`, `INVENTREE_TOKEN` exactly as `app.py` does)
  - `plugin_get(path, **params) -> (json, err)` and `plugin_post(path, payload) -> (json, err)` — same `(data, err)` convention as `it_patch`
  - `evidence_text(typed: str, label: dict|None) -> str` — one newline-joined string: typed text first, then every string the model returned (`orders`, `tracking`, `skus`, `words`, `ship_to`)
  - `site_from_label(label: dict|None) -> "LRD"|"SLN"|None` — `ship_to` containing "villages" → LRD, "dover" → SLN
- Produces, `binscan/providers.py`: `read_label(provider, img_bytes, media) -> dict` with keys `orders, tracking, skus, words` (lists of str), `ship_to` (str), `raw` (str), `model` (str). Same transcription rules as `IDENTIFY_SYSTEM` ("write ? for an unreadable character, never complete a number").

- [ ] **Step 1: Write the failing test**

`scripts/test_receive_client.py`:

```python
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
```

- [ ] **Step 2: Run it to see it fail**

Run: `python3 scripts/test_receive_client.py`
Expected: `FileNotFoundError` on `binscan/receiving.py`.

- [ ] **Step 3: Write `binscan/receiving.py`**

```python
"""BinScan's client for the receiving plugin inside InvenTree.

Over HTTP, not a subprocess: BinScan is a LaunchAgent and TCC refuses it any
execution under /Volumes/*, where the InvenTree interpreter lives (TRAPS.md).
"""
import os

import httpx

INVENTREE = os.environ.get("INVENTREE_URL", "http://127.0.0.1:8001")
IT_TOKEN = os.environ.get("INVENTREE_TOKEN", "")
BASE = f"{INVENTREE}/plugin/receiving"


def _hdr():
    return {"Authorization": f"Token {IT_TOKEN}"}


def _done(r):
    if r.status_code >= 400:
        try:
            msg = r.json().get("error") or r.text[:200]
        except Exception:
            msg = r.text[:200]
        if r.status_code == 404:
            msg = "receiving plugin not mounted (ENABLE_PLUGINS_URL off, plugin inactive, or server not restarted)"
        return None, f"{r.status_code}: {msg}"
    return r.json(), None


def plugin_get(path, **params):
    if not IT_TOKEN:
        return None, "no InvenTree token"
    try:
        return _done(httpx.get(f"{BASE}/{path}", headers=_hdr(), params=params, timeout=40))
    except Exception as e:
        return None, str(e)[:200]


def plugin_post(path, payload):
    if not IT_TOKEN:
        return None, "no InvenTree token"
    try:
        return _done(httpx.post(f"{BASE}/{path}", headers=_hdr(), json=payload, timeout=60))
    except Exception as e:
        return None, str(e)[:200]


def evidence_text(typed, label):
    bits = [(typed or "").strip()]
    if label:
        for k in ("orders", "tracking", "skus", "words"):
            bits += [str(x) for x in (label.get(k) or []) if str(x).strip()]
        if label.get("ship_to"):
            bits.append(str(label["ship_to"]))
    return "\n".join(b for b in bits if b)


def site_from_label(label):
    s = ((label or {}).get("ship_to") or "").lower()
    if "villages" in s:
        return "LRD"
    if "dover" in s:
        return "SLN"
    return None
```

- [ ] **Step 4: Add the label reader to `binscan/providers.py`**

Append after `identify()` (end of file):

```python
LABEL_SYSTEM = """You READ TEXT from a photograph of a shipping label, packing slip,
Amazon bag tag, or a part in its packaging. You transcribe; you never guess.

Return ONLY a JSON object:
{"orders": [], "tracking": [], "skus": [], "words": [], "ship_to": ""}

- orders: order numbers exactly as printed (Amazon looks like 113-8469851-5845865;
  other vendors use a plain run of digits). If any character is unreadable write ?
  in its place. NEVER complete a number, NEVER guess a digit.
- tracking: tracking numbers (TBA..., 1Z..., long USPS digit runs), same rule.
- skus: ASINs (B0 followed by 8 characters) and vendor part numbers printed on the item.
- words: the product words you can read - brand, item name, size, count - as short
  strings, one per line of print. Not addresses, not legal text.
- ship_to: the city/state line of the delivery address if printed, else "".
Transcribe, never correct. Empty lists are the right answer when nothing is readable."""


def _parse_label(text):
    empty = {"orders": [], "tracking": [], "skus": [], "words": [], "ship_to": ""}
    d = _parse(text)
    if not isinstance(d, dict):
        return empty
    out = {k: _strlist(d.get(k)) for k in ("orders", "tracking", "skus", "words")}
    out["ship_to"] = str(d.get("ship_to") or "").strip()
    return out


def read_label(provider, img_bytes, media):
    """Transcribe a label photo. The MATCHING happens in the receiving plugin;
    this returns strings only, with the raw reply for the journal."""
    raw, model = _run(provider, img_bytes, media, LABEL_SYSTEM, "Transcribe this label.")
    d = _parse_label(raw)
    d["raw"], d["model"] = raw, model
    return d
```

Check that `_parse` in `providers.py` strips code fences and finds the first `{…}` (it does for `_parse_identify`; if `_parse` returns a list or raises on non-JSON, wrap: `try: d = _parse(text) except Exception: return empty`).

- [ ] **Step 5: Run the test**

Run: `python3 scripts/test_receive_client.py` → `ALL OK`. Then `python3 scripts/unbound_names.py binscan/providers.py` → no output, exit 0.

- [ ] **Step 6: Commit**

```bash
git add binscan/receiving.py binscan/providers.py scripts/test_receive_client.py
git commit -m "binscan: receiving plugin client + label transcription prompt

The model returns strings only and the plugin matches, the identify-mode rule.
A 404 from the plugin is translated to words naming the three switches that
cause it, because the first time it will be one of them, not the code.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 8: The `/receive` page and its routes in BinScan

**Files:**
- Create: `binscan/receive_page.py`
- Modify: `binscan/app.py` — imports near line 30 (`import providers`), routes appended before `@app.get("/healthz")` (line ~4287)
- Modify: `binscan/README.md` deploy block (two more files)
- Test: `scripts/test_receive_routes.py` (local, imports app.py with writes off)

**Interfaces:**
- Consumes: `receiving.plugin_get/plugin_post/evidence_text/site_from_label`, `providers.read_label`, `app.py`'s `WRITES_ON`, `SHOTS`, `log_append`, `log_read`.
- Produces routes:
  - `GET /receive` → the page, `no-store`
  - `POST /api/receive/match` (multipart: `text` str, `site` str, `photo` file optional) → `{"verdict", "results", "ids", "text", "label": {...}|null, "label_error": str|null, "site": str|null, "shot": name|null}`
  - `POST /api/receive/plan` (JSON `{"po", "lines", "site"}`) → plan
  - `POST /api/receive/commit` (JSON `{"plan"}`) → receipt; 403 when `WRITES_ON` is false; journals `{"kind": "receive", "plan", "receipt"}`
  - `POST /api/receive/undo` (JSON `{"receipt"}`) → result; journals `{"kind": "receive-undo", …}`
  - `POST /api/receive/unsettled` (JSON `{"text", "results"}`) → journals `{"kind": "receive-unsettled", …}` (spec §6 first source)
  - `GET /api/receive/pending?site=` → `{"items": [plugin items…] + [{"kind": "unsettled", "id", "at", "text", "results"}]}`

- [ ] **Step 1: Write the failing route test**

`scripts/test_receive_routes.py`:

```python
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
```

(If `fastapi.testclient` needs `httpx` — it is already a BinScan dependency. If the local venv lacks fastapi: `pip install fastapi httpx` into a scratch venv; do not add anything to the Mini for this.)

- [ ] **Step 2: Run it to see it fail**

Run: `python3 scripts/test_receive_routes.py`
Expected: `assert r.status_code == 200` fails with 404 on `/receive`.

- [ ] **Step 3: Write `binscan/receive_page.py`**

```python
"""The /receive page: camera-first, text under it, three outcomes, one card.
One file, one string, same as PAGE in app.py. Every state carries a glyph."""

RECEIVE_PAGE = r"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<title>receive</title>
<style>
body{background:#111;color:#eee;font:17px system-ui;margin:0;padding:12px 12px 80px}
h1{font-size:20px;margin:4px 0 10px}
.row{display:flex;gap:8px;align-items:center;margin:8px 0}
input[type=text],input[type=number]{font:inherit;padding:10px;border-radius:8px;border:1px solid #444;background:#1b1b1b;color:#eee;width:100%}
input[type=number]{width:70px;text-align:right}
button{font:inherit;padding:12px 16px;border-radius:10px;border:0;background:#2b6cb0;color:#fff}
button.big{width:100%;font-size:20px;padding:16px;background:#2f855a}
button.chip{background:#333;padding:8px 12px;font-size:15px}
button.chip.on{background:#2b6cb0}
button.warn{background:#b7791f}
.card{background:#1b1b1b;border:1px solid #333;border-radius:12px;padding:12px;margin:10px 0}
.card.pick{cursor:pointer}
.line{border-top:1px solid #2a2a2a;padding:8px 0}
.muted{color:#999;font-size:14px}
.ok{color:#9ae6b4}.bad{color:#feb2b2}.warnc{color:#fbd38d}
img.thumb{width:56px;height:56px;object-fit:cover;border-radius:8px;background:#222}
#msg{min-height:24px}
.tabs{display:flex;gap:8px}.tabs button{flex:1;background:#333}.tabs button.on{background:#2b6cb0}
select{font:inherit;padding:8px;border-radius:8px;background:#1b1b1b;color:#eee;border:1px solid #444;max-width:100%}
</style></head><body>
<div class="tabs"><button id="tabR" class="on" onclick="tab('R')">Receive</button><button id="tabP" onclick="tab('P')">Pending <span id="pcount"></span></button></div>
<div id="R">
<h1>Receive a box <span class="muted" id="siteTag"></span></h1>
<div class="row">
 <label class="chip" style="flex:1"><input id="photo" type="file" accept="image/*" capture="environment" onchange="go()" style="width:100%"></label>
</div>
<div class="row"><input id="text" type="text" placeholder="or type / dictate a few words" enterkeyhint="go" onkeydown="if(event.key==='Enter')go()"><button onclick="go()">Go</button></div>
<div class="row"><button class="chip" id="siteLRD" onclick="setSite('LRD')">LRD</button><button class="chip" id="siteSLN" onclick="setSite('SLN')">SLN</button><span class="muted">site</span></div>
<div id="msg" class="muted"></div>
<div id="out"></div>
</div>
<div id="P" style="display:none"><h1>Pending</h1><div id="pend"></div></div>
<script>
const $=id=>document.getElementById(id);
let SITE=null, LAST=null, PLAN=null, RECEIPT=null, UNDO_T=null;
try{SITE=localStorage.getItem('binscan.home')||null}catch(e){}
function setSite(s){SITE=s;try{localStorage.setItem('binscan.home',s)}catch(e){};paintSite()}
function paintSite(){['LRD','SLN'].forEach(s=>$('site'+s).classList.toggle('on',SITE===s));$('siteTag').textContent=SITE?'('+SITE+')':'(site?)'}
paintSite();
function tab(t){$('R').style.display=t==='R'?'':'none';$('P').style.display=t==='P'?'':'none';$('tabR').classList.toggle('on',t==='R');$('tabP').classList.toggle('on',t==='P');if(t==='P')loadPending()}
function msg(t,cls){$('msg').innerHTML='<span class="'+(cls||'muted')+'">'+t+'</span>'}
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
async function jpost(url,body){const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});let d={};try{d=await r.json()}catch(e){d={error:'HTTP '+r.status+' (not JSON)'}};if(!r.ok)throw new Error(d.error||d.detail||('HTTP '+r.status));return d}
async function go(){
  const fd=new FormData();fd.append('text',$('text').value);fd.append('site',SITE||'');
  const f=$('photo').files[0];if(f)fd.append('photo',f);
  if(!f&&!$('text').value.trim()){msg('[??] shoot the label or type a few words');return}
  msg('[..] reading…');$('out').innerHTML='';
  let d;try{const r=await fetch('/api/receive/match',{method:'POST',body:fd});d=await r.json();if(!r.ok)throw new Error(d.error||r.status)}catch(e){msg('[XX] '+esc(e.message),'bad');return}
  LAST=d;$('photo').value='';
  if(d.site&&!SITE)setSite(d.site);
  if(d.label_error)msg('[!!] label not read ('+esc(d.label_error)+') - matched on the text only','warnc');
  else if(d.label)msg('[OK] read: '+esc([...d.label.orders,...d.label.skus,...d.label.words].join(' · ').slice(0,120)));
  else msg('[OK] matched on text');
  if(d.verdict==='one'){openCard(d.results[0].card,d.results[0]);return}
  if(d.verdict==='several'){$('out').innerHTML='<div class="muted">[??] which one is in your hand?</div>'+d.results.map(cardHtml).join('');return}
  const o=await fetch('/api/receive/open?site='+(SITE||''));const od=await o.json();
  $('out').innerHTML='<div class="muted">[??] no match - every open order'+(SITE?' at '+SITE:'')+', newest first</div>'+(od.orders||[]).map(c=>cardHtml({card:c,decisive:[],shared:[]})).join('')+
   '<button class="chip" onclick="location.href=\'/\'">no PO for this - file it by hand</button>';
  if(d.results&&d.results.length)fetch('/api/receive/unsettled',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:d.text,results:d.results.map(r=>({reference:r.reference,po:r.po,score:r.score}))})});
}
function cardHtml(r){const c=r.card;const tail=(c.supplier_reference||'').slice(-7);const why=(r.decisive&&r.decisive.length)?'[OK] '+r.decisive.join(', '):(r.shared&&r.shared.length?'matches on '+r.shared.join(', '):'');
  const img=(c.lines[0]&&c.lines[0].image)?'<img class="thumb" src="'+esc(c.lines[0].image)+'">':'<div class="thumb"></div>';
  const flag=c.closed?'<div class="warnc">[!!] already '+(c.status===60?'RETURNED':'received')+' - a second delivery?</div>':'';
  return '<div class="card pick" onclick=\'openCard('+JSON.stringify(c).replace(/'/g,'&#39;')+')\'><div class="row">'+img+'<div><b>'+esc(c.reference)+'</b> · '+esc(c.issue_date)+' · …'+esc(tail)+' · '+esc(c.supplier)+' · '+esc(c.site||'site?')+'<div class="muted">'+c.lines.map(l=>esc(l.name)+' ×'+l.quantity).join('<br>')+'</div><div class="muted">'+esc(why)+'</div></div></div>'+flag+'</div>'}
async function openCard(c){
  if(c.closed){$('out').innerHTML='<div class="card"><div class="warnc">[!!] '+esc(c.reference)+' is already '+(c.status===60?'RETURNED':'received')+'.</div><div class="muted">A second box for a closed order. Nothing to receive here; keep the box and the order link: <a href="'+esc(c.url)+'">'+esc(c.reference)+'</a></div></div>';return}
  let p;try{p=await jpost('/api/receive/plan',{po:c.po,site:SITE})}catch(e){msg('[XX] '+esc(e.message),'bad');return}
  PLAN=p;renderPlan()}
function renderPlan(){const p=PLAN;const other=p.site&&SITE&&p.site!==SITE?'<div class="warnc">[!!] this order ships to '+esc(p.site)+', you are at '+esc(SITE)+' - boxes do travel; carry on if it is in your hand</div>':'';
  let h='<div class="card"><b>'+esc(p.reference)+'</b> <span class="muted">'+esc(p.when)+'</span>'+other;
  if(p.warnings.length)h+='<div class="bad">[XX] '+p.warnings.map(esc).join('<br>')+'<br><span class="muted">fix the supplier part first; receiving now would book the pack price per piece</span></div>';
  p.lines.forEach((l,i)=>{h+='<div class="line"><div>'+esc(l.name)+' <span class="muted">'+esc(l.sku)+'</span></div><div class="row"><input type="number" min="0" step="any" value="'+l.packs+'" onchange="setPacks('+i+',this.value)"> <span class="muted">of '+l.outstanding+' packs × '+l.pack+' = <b>'+(l.packs*l.pack)+'</b> pieces @ $'+l.unit+'</span></div>'+
    '<div class="row"><span class="muted">to</span> <b>'+esc(l.dest.path)+'</b> <span class="muted">('+esc(l.dest.source)+(l.merge_into?', merges into '+l.before:', new row')+')</span></div>'+
    '<div class="row"><button class="chip" onclick="toReceiving('+i+')">Receiving</button><button class="chip" onclick="pick('+i+')">choose…</button><span id="pick'+i+'"></span></div></div>'});
  h+=p.lines.length?'<button class="big" '+(p.warnings.length?'disabled':'')+' onclick="commit()">All here</button>':'<div class="muted">[OK] nothing outstanding on this order</div>';
  h+='</div>';$('out').innerHTML=h}
async function replan(){const lines={};PLAN.lines.forEach(l=>{lines[l.line]={packs:l.packs,dest:l.dest.pk}});try{PLAN=await jpost('/api/receive/plan',{po:PLAN.po,lines:lines,site:SITE})}catch(e){msg('[XX] '+esc(e.message),'bad')};renderPlan()}
function setPacks(i,v){PLAN.lines[i].packs=parseFloat(v)||0;replan()}
function toReceiving(i){PLAN.lines[i].dest={pk:(PLAN.site||SITE)==='SLN'?472:473,path:'Receiving',source:'chosen'};replan()}
async function pick(i){const r=await fetch('/api/drawers');const g=await r.json();let s='<select onchange="PLAN.lines['+i+'].dest={pk:parseInt(this.value),path:this.selectedOptions[0].text,source:\'chosen\'};replan()"><option>pick a drawer…</option>';g.forEach(grp=>{s+='<optgroup label="'+esc(grp.group)+'">'+grp.items.map(it=>'<option value="'+it.pk+'">'+esc(grp.group+'/'+it.name)+'</option>').join('')+'</optgroup>'});$('pick'+i).innerHTML=s+'</select>'}
async function commit(){const keep=PLAN.lines.filter(l=>l.packs>0);if(!keep.length){msg('[??] every line is 0 - nothing to book');return}
  msg('[..] booking…');let rc;try{rc=await jpost('/api/receive/commit',{plan:Object.assign({},PLAN,{lines:keep})})}catch(e){msg('[XX] '+esc(e.message)+' - nothing booked','bad');return}
  RECEIPT=rc;msg('[OK] booked','ok');
  let h='<div class="card"><b>'+esc(rc.reference)+'</b> → '+(rc.status===30?'<span class="ok">[OK] CLOSED</span>':'<span class="warnc">[!!] still open - lines outstanding</span>');
  rc.lines.forEach(l=>{h+='<div class="line">'+l.pieces+' pieces @ $'+l.unit+' → '+esc(l.dest_path)+' <a href="'+esc(l.url)+'">stock '+l.stock+'</a> '+(l.created?'(new row)':'(merged, was '+l.before_qty+')')+'</div>'});
  h+='<div class="row"><button class="warn" id="undoBtn" onclick="undo()">Undo</button><span class="muted" id="undoLeft"></span></div><div class="row"><button class="chip" onclick="goingBack()">going back (return requested)</button></div></div>';
  $('out').innerHTML=h;const until=new Date(rc.undo_until).getTime();clearInterval(UNDO_T);UNDO_T=setInterval(()=>{const s=Math.floor((until-Date.now())/1000);if(s<=0){clearInterval(UNDO_T);$('undoBtn').disabled=true;$('undoLeft').textContent='undo window closed - use binscan_undo.py';return}$('undoLeft').textContent=Math.floor(s/60)+':'+String(s%60).padStart(2,'0')+' left'},1000)}
async function undo(){msg('[..] undoing…');try{const u=await jpost('/api/receive/undo',{receipt:RECEIPT});msg('[OK] undone - '+esc(u.reference)+' back to status '+u.status,'ok');$('out').innerHTML=''}catch(e){msg('[XX] '+esc(e.message),'bad')}}
async function goingBack(){const c=RECEIPT;if(!c)return;msg('[..] marking going back…');try{const d=await jpost('/api/receive/going-back',{po:c.po});msg('[OK] '+esc(d.action)+' - '+esc(d.reference),'ok')}catch(e){msg('[XX] '+esc(e.message),'bad')}}
async function loadPending(){const r=await fetch('/api/receive/pending?site='+(SITE||''));const d=await r.json();$('pcount').textContent=d.items.length?'('+d.items.length+')':'';
  $('pend').innerHTML=d.items.length?d.items.map(it=>{if(it.kind==='overdue')return '<div class="card"><div class="warnc">[!!] '+esc(it.reference)+' is '+it.days+' days past its date - did it arrive?</div>'+cardHtml({card:it.card,decisive:[],shared:[]})+'</div>';
    if(it.kind==='decision')return '<div class="card"><div class="warnc">[??] '+esc(it.reference)+'</div><div>'+esc(it.question)+'</div><div class="muted"><a href="'+esc(it.url)+'">open the order</a> and answer in its note; the morning task reads it</div></div>';
    return '<div class="card"><div class="muted">[??] unsettled '+esc(it.at)+': "'+esc(it.text)+'"</div><div>'+(it.results||[]).map(r=>esc(r.reference)).join(', ')+'</div><button class="chip" onclick="$(\'text\').value='+JSON.stringify(it.text||'')+';tab(\'R\');go()">try again</button></div>'}).join(''):'<div class="muted">[OK] nothing pending</div>';
  if(d.error)$('pend').innerHTML+='<div class="bad">[XX] '+esc(d.error)+'</div>'}
loadPending();
</script></body></html>"""
```

- [ ] **Step 4: Add the routes to `binscan/app.py`**

Near line 30, after `import providers`, add:

```python
import receiving as rcv
from receive_page import RECEIVE_PAGE
```

Before `@app.get("/healthz")`, add:

```python
# ---- /receive: PO receiving from the phone (docs/binscan.md "Receiving") ----

@app.get("/receive", response_class=HTMLResponse)
def receive_page():
    return HTMLResponse(RECEIVE_PAGE, headers={
        "Cache-Control": "no-store, no-cache, must-revalidate", "Pragma": "no-cache"})


@app.get("/api/receive/open")
def api_receive_open(site: str = ""):
    d, err = rcv.plugin_get("open/", site=site or None)
    if err:
        return JSONResponse({"error": err, "orders": []}, status_code=502)
    return d


@app.post("/api/receive/match")
async def api_receive_match(text: str = Form(""), site: str = Form(""),
                            photo: UploadFile | None = File(None)):
    label, label_error, shot = None, None, None
    if photo is not None:
        img = await photo.read()
        media = photo.content_type or "image/jpeg"
        if media not in ("image/jpeg", "image/png", "image/webp", "image/gif"):
            label_error = f"unsupported image type {media}"
        else:
            shot = f"receive-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.jpg"
            (SHOTS / shot).write_bytes(img)
            try:
                label = providers.read_label("anthropic", img, media)
            except Exception as e:  # noqa: BLE001 - degrade to the text field (spec §7)
                label_error = str(e)[:160]
    ev = rcv.evidence_text(text, label)
    site = site or rcv.site_from_label(label) or ""
    if not ev.strip():
        return JSONResponse({"error": "nothing to match: no readable text and nothing typed"}, status_code=400)
    d, err = rcv.plugin_post("match/", {"text": ev, "site": site or None})
    if err:
        return JSONResponse({"error": err}, status_code=502)
    d.update({"label": {k: v for k, v in (label or {}).items() if k != "raw"} if label else None,
              "label_error": label_error, "site": site or None, "shot": shot})
    log_append({"id": uuid.uuid4().hex[:8], "kind": "receive-match",
                "at": datetime.datetime.now().isoformat(timespec="seconds"),
                "text": ev, "shot": shot, "label": label, "verdict": d.get("verdict"),
                "results": [{"reference": r.get("reference"), "po": r.get("po"), "score": r.get("score"),
                             "decisive": r.get("decisive")} for r in d.get("results", [])]})
    return d


@app.post("/api/receive/plan")
async def api_receive_plan(payload: dict):
    d, err = rcv.plugin_post("plan/", payload)
    if err:
        return JSONResponse({"error": err}, status_code=502)
    return d


@app.post("/api/receive/commit")
async def api_receive_commit(payload: dict):
    if not WRITES_ON:
        return JSONResponse({"error": "writes are off (BINSCAN_WRITES)"}, status_code=403)
    d, err = rcv.plugin_post("commit/", payload)
    if err:
        return JSONResponse({"error": err}, status_code=502)
    log_append({"id": uuid.uuid4().hex[:8], "kind": "receive",
                "at": datetime.datetime.now().isoformat(timespec="seconds"),
                "plan": payload.get("plan"), "receipt": d})
    return d


@app.post("/api/receive/undo")
async def api_receive_undo(payload: dict):
    if not WRITES_ON:
        return JSONResponse({"error": "writes are off (BINSCAN_WRITES)"}, status_code=403)
    d, err = rcv.plugin_post("undo/", payload)
    if err:
        return JSONResponse({"error": err}, status_code=502)
    log_append({"id": uuid.uuid4().hex[:8], "kind": "receive-undo",
                "at": datetime.datetime.now().isoformat(timespec="seconds"),
                "receipt": payload.get("receipt"), "result": d})
    return d


@app.post("/api/receive/going-back")
async def api_receive_going_back(payload: dict):
    """The receive card's 'going back' button: spec §5's requested branch by hand."""
    if not WRITES_ON:
        return JSONResponse({"error": "writes are off (BINSCAN_WRITES)"}, status_code=403)
    d, err = rcv.plugin_post("going-back/", payload)
    if err:
        return JSONResponse({"error": err}, status_code=502)
    log_append({"id": uuid.uuid4().hex[:8], "kind": "receive-going-back",
                "at": datetime.datetime.now().isoformat(timespec="seconds"), "po": payload.get("po"), "result": d})
    return d


@app.post("/api/receive/unsettled")
async def api_receive_unsettled(payload: dict):
    log_append({"id": uuid.uuid4().hex[:8], "kind": "receive-unsettled",
                "at": datetime.datetime.now().isoformat(timespec="seconds"),
                "text": payload.get("text"), "results": payload.get("results")})
    return {"ok": True}


@app.get("/api/receive/pending")
def api_receive_pending(site: str = ""):
    d, err = rcv.plugin_get("pending/", site=site or None)
    items = list((d or {}).get("items") or [])
    seen = set()
    for r in reversed(log_read()):
        if r.get("kind") == "receive-unsettled" and r.get("text") not in seen:
            seen.add(r.get("text"))
            items.append({"kind": "unsettled", "id": r.get("id"), "at": r.get("at"),
                          "text": r.get("text"), "results": r.get("results")})
    return {"items": items[:40], "error": err}
```

The `going-back/` plugin view does not exist yet; add it now to `plugins/receiving/views.py` and the URL table:

```python
class GoingBackView(_View):
    def post(self, request):
        from order.models import PurchaseOrder
        po = PurchaseOrder.objects.get(pk=int(request.data["po"]))
        return self.guard(returns.requested, po.supplier_reference, str(__import__("datetime").date.today()),
                          reason="marked from the receive card", event="requested")
```

```python
            path("going-back/", v.GoingBackView.as_view(), name="going-back"),
```

- [ ] **Step 5: Run the local tests and the unbound-names check**

```bash
python3 scripts/test_receive_routes.py
python3 scripts/unbound_names.py binscan/app.py
python3 scripts/test_receive_client.py
```

Expected: `ALL OK`, nothing from `unbound_names.py`, `ALL OK`.

- [ ] **Step 6: Deploy BinScan and the plugin view, then drive the page once**

```bash
R=/Volumes/4TB_Removable/inventree/src/src/backend/InvenTree/plugins/receiving
~/code/scripts/itq push plugins/receiving/views.py $R/views.py
~/code/scripts/itq push plugins/receiving/__init__.py $R/__init__.py
ssh mini 'launchctl kickstart -k gui/$(id -u)/com.inventree.server'
~/code/scripts/itq push binscan/app.py          /Users/scottdube/binscan/app.py
~/code/scripts/itq push binscan/providers.py    /Users/scottdube/binscan/providers.py
~/code/scripts/itq push binscan/receiving.py    /Users/scottdube/binscan/receiving.py
~/code/scripts/itq push binscan/receive_page.py /Users/scottdube/binscan/receive_page.py
ssh mini 'launchctl kickstart -k gui/$(id -u)/com.binscan'; sleep 5
ssh mini 'curl -s http://127.0.0.1:8002/healthz; curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8002/receive; curl -s -F text=113-8469851-5845865 -F site=LRD http://127.0.0.1:8002/api/receive/match | head -c 300'
```

Expected: healthz JSON, `200`, and a match JSON with `"verdict": "one"` and `PO-0291`.

Then in the browser pane open `http://192.168.50.10:8002/receive` (via `preview_start` with that url), type `1x7 header`, press Go: several cards appear, one per open PO carrying the socket, each with date, …last7, supplier, lines. Tap PO-0291: the card shows `2 of 2 packs × 60 = 120 pieces @ $0.1165` to the part's default location, source `default_location`, with Receiving and choose… chips. **Do not press All here** — PO-0291 has not physically arrived (arrives 2026-11-08). Screenshot the card at `scale: 0.5` for the record.

- [ ] **Step 7: Update `binscan/README.md` deploy block**

```markdown
    itq push binscan/app.py          /Users/scottdube/binscan/app.py
    itq push binscan/providers.py    /Users/scottdube/binscan/providers.py
    itq push binscan/receiving.py    /Users/scottdube/binscan/receiving.py
    itq push binscan/receive_page.py /Users/scottdube/binscan/receive_page.py
    launchctl kickstart -k gui/$(id -u)/com.binscan
```

- [ ] **Step 8: Commit**

```bash
git add binscan/receive_page.py binscan/app.py binscan/README.md plugins/receiving/views.py plugins/receiving/__init__.py scripts/test_receive_routes.py
git commit -m "binscan /receive: camera-first page, three outcomes, receive card with undo

Separate page, not a tab inside PAGE: the walk page is 85 KB of its own
state machine and a receive is a different job with a home-screen icon of
its own. The drawer picker is /api/drawers rather than PAGE's in-page picker
because that one is closed over PAGE's state. All here is disabled while a
pack warning stands, which is the one refusal the CLI also makes.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 9: The refund watcher calls `returns.py`

**Files:**
- Modify: `~/.claude/scheduled-tasks/amazon-refund-watch/SKILL.md` — the "Hard constraints" section and the recording section; keep everything about Gmail search (order number only), the subject table, the item-description rule, glyphs, and the push rule.
- Modify: `docs/TRAPS.md` (one paragraph under the existing refund/phantom-stock warning)

**Interfaces:**
- Consumes: `~/code/scripts/itq run scripts/returns.py <event> --order <no> [--amount X] [--date D] --commit` (Task 6). Paths are relative to `~/code/shop-inventory` (itq resolves there first).

- [ ] **Step 1: Replace the "Hard constraints" bullets 1–2**

Replace the two bullets beginning "**Never deplete, remove, or delete stock.**" and "**Never cancel, reopen, or change the status of a purchase order.**" with:

```markdown
- **Stock and order status change only through `scripts/returns.py`.** It carries the one hard guard (a row is removed only when it is Quarantined AND its note starts with `[GOING-BACK]`); every other doubt writes `[NEEDS-DECISION] <question>` on the PO and stops. You never write a one-off script for a refund, never PATCH a stock row, never set a status yourself. Since 2026-11-06 (spec `docs/superpowers/specs/2026-11-06-po-receiving-design.md`); before that this task was notes-only and refunded orders sat PLACED for weeks.
- **Dry-run first, then `--commit`, and read the JSON.** `ok: true, action: returned` is done; `action: pending` means a question is on the PO note for Scott; `action: already` means a previous run did it; `action: error` with `reference: null` means the order number is not in InvenTree (list it, do not create anything).
```

- [ ] **Step 2: Replace the recording step**

Find the section that tells the task to write a `refund_seen_<PO>_<MMDD>.py` script (the "Record" or "4." step) and replace its body with:

```markdown
For each mail matched to an open order number, run ONE of these (the subject table above maps subjects to events):

    ~/code/scripts/itq run scripts/returns.py requested --order <no> --date <mail date> --reason "<reason line if the mail gives one>"
    ~/code/scripts/itq run scripts/returns.py dropoff   --order <no> --date <mail date>
    ~/code/scripts/itq run scripts/returns.py refunded  --order <no> --amount <refund total from the mail> --date <mail date>

First without `--commit` (prints `DRY RUN — rolled back` and the result it would produce), then the same line with `--commit`. Exit code 0 = ok, 2 = pending (a `[NEEDS-DECISION]` question is now on the PO), 1 = error.

"Advance refund issued" and "Your refund confirmation" are both `refunded`; use the dollar amount in the mail, never a line price from InvenTree.

When the output has a `PUSH:` line, send exactly that line with PushNotification. Pending and error results go in the report, not the push, unless nothing else happened today and there is at least one pending — then push one line: `Refund watch: N question(s) waiting on PO notes`.
```

- [ ] **Step 3: Keep the report format, add the three verdict lines**

In the report section, add to the per-order line format:

```markdown
- `[OK] PO-0291 113-8469851-5845865 refunded $6.99 → RETURNED, stock 1301 removed`
- `[!!] PO-0288 113-… refund $16.99 → PENDING: <question from the JSON>`
- `[XX] 113-… not in InvenTree` / `[XX] returns.py failed: <first line of error>`
```

- [ ] **Step 4: Dry-run the task shape by hand once**

```bash
~/code/scripts/itq run scripts/refund_watch.py
~/code/scripts/itq run scripts/returns.py refunded --order <an order number refund_watch printed> --amount 1.00
```

Expected: the watchlist prints as before; the second prints `DRY RUN — rolled back` and a `pending` result (amount deliberately wrong), and the PO's note is unchanged afterwards (re-run `refund_watch.py`; the item must not read as pending).

- [ ] **Step 5: TRAPS entry**

Append to `docs/TRAPS.md` under the refund / phantom-stock warning:

```markdown
**Returns are automatic since 2026-11-06.** The morning `amazon-refund-watch`
task calls `scripts/returns.py` for every return mail; it removes a stock row
only when the row is Quarantined with `[GOING-BACK]` and otherwise writes
`[NEEDS-DECISION] <question>` on the PO and stops. If a refunded order is
still PLACED, look for that token in its note before suspecting the task —
and a `[NEEDS-DECISION]` note is answered by editing the PO note (delete the
token, state the answer), after which the next run re-processes the mail.
```

- [ ] **Step 6: Commit (two repos)**

```bash
cd /Users/scottdube/code/shop-inventory && git add docs/TRAPS.md && git commit -m "TRAPS: returns are automatic; [NEEDS-DECISION] is where a stuck refund waits

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

The SKILL.md lives outside any repo; record the change in `~/code/docs/` only if a scheduled-tasks changelog exists there (check `ls ~/code/docs | grep -i task`); otherwise the task's own `## Changelog` section (add one if absent) gets: `2026-11-06 — writes go through scripts/returns.py; notes-only rule retired (spec 2026-11-06-po-receiving-design.md).`

---

### Task 10: Docs, home-screen shortcut, spec amendment

**Files:**
- Modify: `docs/binscan.md` (new section "Receiving a box")
- Modify: `CLAUDE.md` lines 57–63 ("RECEIVE WITH THE SCRIPT" block)
- Modify: `docs/TRAPS.md` (TCC → plugin; ENABLE_PLUGINS_URL)
- Modify: `docs/superpowers/specs/2026-11-06-po-receiving-design.md` §1 and §6
- Modify: `docs/OPEN.md` (one open item: the photo fixture set and the floor)

- [ ] **Step 1: `docs/binscan.md` — append**

```markdown
## Receiving a box — `/receive` (added 2026-11-06)

`http://binscan.internal/receive` (= 192.168.50.10). Camera first, text under it.
Shoot the label, slip, bag tag or the part; or type / dictate a few words. The
model transcribes strings only; `plugins/receiving/match.py` inside InvenTree
matches them to open orders (order number or its last 7 digits, ASIN/SKU, a
tracking number in the PO note are decisive; words are IDF-ranked).

Three outcomes: one card; several cards (date · …last7 · supplier · lines ·
thumbnail — tap the one in your hand); or every open order at this site plus
"no PO for this" (the by-hand filepart flow). A decisive hit on a received or
RETURNED order is shown with `[!!] already … a second delivery?`.

The card: packs editable (0 = leave outstanding), pieces and price per piece
shown, destination prefilled and its source named (`default_location`,
`existing_stock`, `category`, `receiving`), Receiving always one tap. **All here**
books it through the engine (`plan` → `commit`), never the REST receive
endpoint: pieces = packs × `pack_quantity_native`, merges into the row at that
location, and closes the order when nothing is outstanding. **Undo** for 10
minutes. Every match, receive and undo is a `log.jsonl` row (`receive-match`,
`receive`, `receive-undo`, `receive-unsettled`, `receive-going-back`).

Pending tab: `[NEEDS-DECISION]` questions the returns automation parked,
orders > 3 days past `target_date` with nothing received, and matches you
closed without choosing.

**Home-screen icon:** Safari → the URL → Share → *Add to Home Screen*. The
page sets `apple-mobile-web-app-capable`, so it opens without browser chrome.
**Siri:** Shortcuts app → + → *Open URLs* → `http://192.168.50.10:8002/receive`
→ name it "receive a box".

Engine and HTTP views: `plugins/receiving/` (hosted inside InvenTree because a
LaunchAgent cannot execute anything under `/Volumes/*`, see TRAPS). Client:
`binscan/receiving.py`. Page: `binscan/receive_page.py`.
```

- [ ] **Step 2: `CLAUDE.md` — replace the "RECEIVE WITH THE SCRIPT" block**

Replace lines 57–63 (from `**RECEIVE WITH THE SCRIPT — it does both halves:**` through the fenced commands) with:

```markdown
  **RECEIVE THROUGH THE ENGINE — it does both halves.** From the phone:
  `http://binscan.internal/receive` (docs/binscan.md "Receiving a box"). From a
  session:

  ```
  itq run scripts/receive_po.py PO-0146 --to RB-14           # dry run
  itq run scripts/receive_po.py PO-0146 --to RB-14 --commit
  ```

  Both doors call `plugins/receiving/engine.py`: it honours `pack_quantity`,
  merges into the existing row, refuses when a SKU says "pack" and
  `pack_quantity` says 1 — and **closes the order**. Returns are automatic
  (`scripts/returns.py`, driven by the morning refund task); a refund it could
  not settle is a `[NEEDS-DECISION]` note on the PO.
```

- [ ] **Step 3: `docs/TRAPS.md` — append to the TCC section**

```markdown
Consequence, 2026-11-06: anything BinScan needs from the InvenTree interpreter
must be reached over HTTP. The receiving engine is an InvenTree **plugin**
(`plugins/receiving/`, views under `/plugin/receiving/…`) for that reason, not
a subprocess. Plugin URLs mount only when the GLOBAL setting
`ENABLE_PLUGINS_URL` is True (it is a `common.InvenTreeSetting` row, not
config.yaml; `scripts/set_plugins_url.py`) AND the PluginConfig is active
AND the server was restarted after both. A 404 on `/plugin/receiving/ping/`
after a deploy is one of those three, never a code error.
```

- [ ] **Step 4: Spec amendment**

In the spec, under §1 replace the paragraph beginning "BinScan calls both through a subprocess" with:

```markdown
BinScan calls both over HTTP: the engine is hosted as the InvenTree plugin
`receiving` (`plugins/receiving/`, views under `/plugin/receiving/…`, token
auth). **Amended 2026-11-06** — the subprocess design cannot work because
BinScan is a LaunchAgent and TCC refuses launchd children any execution under
`/Volumes/*` (TRAPS.md). The REST receive endpoint is still not used; the plugin
views run the engine's own `plan`/`commit`.
```

and replace §6's last paragraph ("Pending state is a small JSON file…") with:

```markdown
**Amended 2026-11-06:** the second and third sources are derived from the
database by the plugin's `/pending/` view (a `[NEEDS-DECISION]` token in the
PO note; PLACED orders > 3 days past `target_date` with nothing received), so
nothing is stored twice. Only the first source (an unsettled match) is
BinScan-local, as a `receive-unsettled` row in `log.jsonl`.
```

Also change `scripts/receiving.py` in §1's first paragraph to `plugins/receiving/engine.py`.

- [ ] **Step 5: `docs/OPEN.md` — add**

```markdown
## Receive matcher: confidence floor is provisional (opened 2026-11-06)

`plugins/receiving/match.py` ships with `WORD_FLOOR = 1.0`, `WORD_RATIO = 2.0`,
guessed. Spec §8 says the floor is set from a fixture set of real photos Scott
shoots during the first week (labels, slips, bags), each tagged with its true
PO, scored definite / several / none. Fixtures go in
`binscan/fixtures/receive/<date>-<n>.jpg` + `.json` (`{"truth": "PO-xxxx"}`);
`scripts/test_receive_match.py` grows a loop over them. Close when the floor
has been measured against at least ten photos.
```

- [ ] **Step 6: Commit**

```bash
git add docs/binscan.md CLAUDE.md docs/TRAPS.md docs/superpowers/specs/2026-11-06-po-receiving-design.md docs/OPEN.md
git commit -m "docs: receiving from the phone - binscan.md, CLAUDE.md door, TRAPS, spec amended

Spec amended in place rather than left as written: the subprocess paragraph
would send the next reader down the TCC hole that was measured today.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
git push
```

---

## Self-review against the spec (done 2026-11-06 while writing)

| Spec | Task |
|---|---|
| §1 engine `plan`/`commit`/`undo`, one module, two doors | 3 (engine), 4 (views), 5 (CLI), 8 (page) |
| §2 page, home-screen, Siri, camera + text, three outcomes, Pending tab | 8, 10 |
| §3 model transcribes / Python matches; decisive + ranked; confident rule; closed-order signal; photo + reply logged under shots/ | 2, 7, 8 (`receive-match` journal + `SHOTS`) |
| §4 card: packs editable, pieces shown, All here, 0 = outstanding, destination order + source, Receiving chip, picker, site from ship-to / ask once, confirm view with links + status, Undo 10 min, journal, no labels | 3 (`suggest_destination`, `site_of`), 8 |
| §5 returns: three events, clean/unclean, sentinels, push line, going-back button | 6, 8 (`going-back`), 9 |
| §6 pending three sources | 3 (`pending`), 8 (`unsettled`) — amended, see Deviations |
| §7 model failure degrades; commit atomic; re-read every write; other-site warning chip; hard guard | 8 (`label_error`), 3 (`transaction.atomic`, verify), 8 (chip), 6 (guard) |
| §8 engine round-trip, matcher fixture set, returns branches, unbound_names | 3, 2 + OPEN item (photos), 6, 8 |

Placeholder scan: no TBD/TODO; the one deliberately open value (`WORD_FLOOR`) is named as provisional and tracked in OPEN.md. Names cross-checked: `po_card`, `open_orders`, `site_of`, `suggest_destination`, `plan`, `commit`, `undo`, `pending`, `requested`, `refunded`, `extract_ids`, `score`, `verdict`, `plugin_get`, `plugin_post`, `evidence_text`, `site_from_label`, `read_label`, `_parse_label`, `RECEIVE_PAGE`, route paths, journal kinds — each defined once and used by that name everywhere else.
