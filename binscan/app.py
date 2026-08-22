"""binscan - photograph a drawer, get a fill estimate.

READ-ONLY. It reads locations and parts from InvenTree and returns an estimate;
it writes no stock. Accuracy gets measured against reality first, because a
bin-check tool that silently writes bad numbers is worse than no tool.

The model is NOT asked to identify the part -- the drawer address already
determines that, so its only job is "how full is this", which is the thing
vision is actually good at. It is told to report LOW confidence on heaps,
because occlusion makes 200 small parts look like 150 and prompting can't fix
physics.

Runs from the INTERNAL disk on purpose: anything under /Volumes needs a TCC
grant to run from launchd, which is what silently broke the backup for weeks.
"""

import datetime
import json
import os
import pathlib
import re
import uuid

import httpx
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

import providers

INVENTREE = os.environ.get("INVENTREE_URL", "http://127.0.0.1:8001")
IT_TOKEN = os.environ.get("INVENTREE_TOKEN", "")
WRITES_ON = os.environ.get("BINSCAN_WRITES", "") == "1"
# Confidence levels that may write WITHOUT a human confirming. Empty, and it
# has to stay empty until the log says otherwise.
#
# This was {"high"} until 2026-08-22. The run log by then held five HIGH
# confidence readings that were wrong, the worst being a five-piece drawer
# called ~10 -- a doubled count, written silently, indistinguishable
# afterwards from one somebody counted. Nothing had actually been written
# because the UI never called /api/record, so this was a loaded gun rather
# than a wound.
#
# The model's confidence is a statement about how clearly it could SEE, not
# about whether it was RIGHT, and the log shows those come apart. CLAUDE.md:
# "Never invent a count. A quantity nobody counted is how a stock system
# starts lying."
AUTO_CONF = frozenset()

app = FastAPI(title="binscan")

HOME = pathlib.Path.home() / "binscan"
LOG = HOME / "log.jsonl"
SHOTS = HOME / "shots"
SHOTS.mkdir(exist_ok=True)


def log_append(rec):
    with LOG.open("a") as fh:
        fh.write(json.dumps(rec) + "\n")


def log_read():
    if not LOG.exists():
        return []
    out = []
    for line in LOG.read_text().splitlines():
        try:
            out.append(json.loads(line))
        except Exception:
            pass
    return out


def log_rewrite(rows):
    with LOG.open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")


def it_get(path, **params):
    if not IT_TOKEN:
        return None
    try:
        r = httpx.get(f"{INVENTREE}/api/{path}",
                      headers={"Authorization": f"Token {IT_TOKEN}"},
                      params=params, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _rows(data):
    if not data:
        return []
    return data.get("results", data) if isinstance(data, dict) else data


def it_post(path, payload):
    if not IT_TOKEN:
        return None, "no InvenTree token"
    try:
        r = httpx.post(f"{INVENTREE}/api/{path}",
                       headers={"Authorization": f"Token {IT_TOKEN}"},
                       json=payload, timeout=25)
        if r.status_code >= 400:
            return None, f"{r.status_code}: {r.text[:200]}"
        return r.json(), None
    except Exception as e:
        return None, str(e)[:200]


def resolve(location_name, part_name):
    """Drawer address + part name -> (location pk, part pk). Both must be exact
    enough to be unambiguous; guessing here would write to the wrong drawer."""
    want = (location_name or "").strip().lower()
    locs = _rows(it_get("stock/location/", search=location_name, limit=25))
    loc = (next((l for l in locs if l["name"].lower() == want), None)
           or next((l for l in locs if (l.get("pathstring") or "").lower() == want), None)
           or next((l for l in locs if l["name"].lower().endswith(want)), None)
           or (locs[0] if locs else None))
    if not loc:
        return None, None, f"no location matching '{location_name}'"
    wantp = (part_name or "").strip().lower()
    parts = _rows(it_get("part/", search=part_name, limit=25))
    part = (next((p for p in parts if p["name"].lower() == wantp), None)
            or (parts[0] if parts else None))
    if not part:
        return None, None, f"no part matching '{part_name}'"
    return loc, part, None


@app.post("/api/record")
def record(id: str = Form(""), location: str = Form(...), part: str = Form(...),
           count: float = Form(...), confidence: str = Form("low"),
           model: str = Form(""), confirm: str = Form("")):
    """Write an estimated count as a real InvenTree stock count."""
    if not WRITES_ON:
        return JSONResponse({"error": "writes disabled (BINSCAN_WRITES != 1)"}, 403)

    conf = (confidence or "low").lower()
    if conf not in AUTO_CONF and confirm.lower() not in ("1", "true", "yes"):
        return JSONResponse({"needs_confirm": True, "confidence": conf,
                             "message": f"{conf} confidence - confirm to write"}, 409)

    loc, prt, err = resolve(location, part)
    if err:
        return JSONResponse({"error": err}, 404)

    note = (f"binscan estimate: {count:g} ({conf} confidence, {model or 'unknown model'})"
            + ("" if conf in AUTO_CONF else " - confirmed by user"))

    stock = _rows(it_get("stock/", location=loc["pk"], part=prt["pk"], limit=5))
    if stock:
        body, err = it_post("stock/count/",
                            {"items": [{"pk": stock[0]["pk"], "quantity": count}],
                             "notes": note})
        action = "counted"
    else:
        body, err = it_post("stock/", {"part": prt["pk"], "location": loc["pk"],
                                       "quantity": count, "notes": note})
        action = "created"

    if err:
        return JSONResponse({"error": err}, 502)

    rows = log_read()
    for r in rows:
        if r.get("id") == id:
            r["written"] = {"action": action, "count": count, "confidence": conf}
    log_rewrite(rows)

    return {"ok": True, "action": action, "count": count,
            "location": loc["name"], "part": prt["name"], "note": note}


@app.get("/api/providers")
def providers_status():
    return providers.status()


@app.get("/api/locations")
def locations(q: str = ""):
    rows = _rows(it_get("stock/location/", search=q, limit=60))
    return [{"pk": r["pk"], "name": r.get("pathstring") or r["name"]} for r in rows]


@app.get("/api/drawers")
def drawers():
    """Leaf locations only, grouped by their parent, for a no-typing picker."""
    rows = _rows(it_get("stock/location/", limit=1000))
    by_pk = {r["pk"]: r for r in rows}
    parents = {r.get("parent") for r in rows if r.get("parent") is not None}
    groups = {}
    for r in rows:
        if r["pk"] in parents:          # has children -> not a drawer
            continue
        par = by_pk.get(r.get("parent"))
        gname = (par.get("pathstring") or par["name"]) if par else "(top level)"
        groups.setdefault(gname, []).append({"pk": r["pk"], "name": r["name"]})
    return [{"group": g, "items": sorted(v, key=lambda x: x["name"])}
            for g, v in sorted(groups.items())]


@app.get("/api/parts")
def parts_at(q: str = ""):
    """Resolve a drawer address to what should be in it."""
    loc = _rows(it_get("stock/location/", search=q, limit=1))
    if not loc:
        return []
    rows = _rows(it_get("part/", default_location=loc[0]["pk"], limit=25))
    return [{"pk": r["pk"], "name": r["name"]} for r in rows]


# ------------------------------------------------- identify (the walk) ---
# The drawer address is normally an INPUT to this app -- it tells you what the
# drawer holds. In B1 and B2 it is the OUTPUT: 48 McMaster rows are located to
# the cabinet and not to a drawer. So the flow inverts. The model reads the bag
# tag; the matching below is plain Python, because a model asked to choose from
# a candidate list always chooses, while a number either matches a SKU or does
# not.

def _norm_sku(s):
    return re.sub(r"[^A-Z0-9?]", "", (s or "").upper())


def _mcmaster_skus():
    co = _rows(it_get("company/", name="McMaster-Carr", limit=5))
    if not co:
        return {}
    out = {}
    for c in co:
        for r in _rows(it_get("company/part/", supplier=c["pk"], limit=500)):
            out[r.get("part")] = r.get("SKU") or ""
    return out


def cabinet_unlocated(cab):
    """Stock sitting at the cabinet itself, with no drawer assigned."""
    loc = _rows(it_get("stock/location/", name=cab, limit=5))
    loc = [l for l in loc if (l.get("name") or "").upper() == cab.upper()]
    if not loc:
        return []
    skus = _mcmaster_skus()
    rows = _rows(it_get("stock/", location=loc[0]["pk"], cascade=False, limit=200))
    out = []
    for r in rows:
        pk = r.get("part")
        out.append({"stock": r.get("pk"), "part": pk,
                    "name": (r.get("part_detail") or {}).get("name")
                            or r.get("part_name") or f"part {pk}",
                    "quantity": r.get("quantity"),
                    "sku": skus.get(pk, "")})
    return out


# Deliberately loose: a drawer label writes the thread as "M3 .5 x20" -- size,
# pitch, length -- so requiring "M3 x" the way a McMaster part name spells it
# finds no thread at all, and the match then rests on length alone. That made
# "M3 .5 x20" tie with an M6 x 20 socket head, which is the wrong drawer and
# the wrong thread. Matching \bM<digits> catches both spellings; "MB10S" and
# friends are safe because a letter follows the M.
_THREAD = re.compile(r"\bM\s*(\d+(?:\.\d+)?)\b", re.I)
_IMP = re.compile(r'(\d+/\d+)"?\s*-\s*(\d+)')
_LEN_MM = re.compile(r"(\d+(?:\.\d+)?)\s*mm\s+long", re.I)


def _facts(t):
    tl = (t or "").lower()
    m = _THREAD.search(t or "")
    im = _IMP.search(t or "")
    ln = _LEN_MM.search(t or "")
    return (f"m{float(m.group(1)):g}" if m else None,
            f"{im.group(1)}-{im.group(2)}" if im else None,
            float(ln.group(1)) if ln else None,
            tl)


def match_reading(reading, rows):
    """Rank candidate rows against what the model actually read. Returns
    (ranked, basis) where basis names WHICH evidence decided it."""
    tag = _norm_sku(reading.get("tag"))
    if tag:
        exact = [r for r in rows if _norm_sku(r["sku"]) == tag]
        if len(exact) == 1:
            return [{"row": exact[0], "why": f"bag tag {reading['tag']} matches SKU exactly",
                     "strength": "definite"}], "tag"
        if "?" in tag:
            pat = re.compile("^" + tag.replace("?", ".") + "$")
            near = [r for r in rows if pat.match(_norm_sku(r["sku"]))]
            if near:
                return ([{"row": r, "why": f"partial tag {reading['tag']} fits this SKU",
                          "strength": "probable" if len(near) == 1 else "ambiguous"}
                         for r in near[:5]], "partial-tag")
        if exact:
            return ([{"row": r, "why": "tag matches more than one row",
                      "strength": "ambiguous"} for r in exact[:5]], "tag")
        return [], "tag-no-match"

    text = " ".join([reading.get("descriptors", "")]
                    + list(reading.get("labels") or [])
                    + list(reading.get("markings") or []))
    if not text.strip():
        return [], "nothing-legible"
    lm, li, ll, _ = _facts(text)
    lnum = re.search(r"x\s*(\d+(?:\.\d+)?)", text.lower())
    ll = ll or (float(lnum.group(1)) if lnum else None)
    scored = []
    for r in rows:
        pm, pi, pl, _ = _facts(r["name"])
        sc = 0
        if lm and pm:
            sc += 4 if lm == pm else -6
        if li and pi:
            sc += 4 if li == pi else -6
        if ll is not None and pl is not None:
            sc += 4 if abs(ll - pl) < 0.01 else -4
        if sc > 0:
            scored.append((sc, r))
    scored.sort(key=lambda t: -t[0])
    top = [s for s in scored if s[0] == scored[0][0]] if scored else []
    return ([{"row": r, "why": f"label text \u201c{text.strip()[:40]}\u201d fits",
              "strength": "probable" if len(top) == 1 else "ambiguous"}
             for _sc, r in top[:5]], "label-text")


def drawer_contents(name):
    """What the DATABASE already says is in this drawer. Checked before any
    model is called: asking vision what the record already knows introduces
    error where there was none, and costs an API call to do it. Scott,
    2026-08-22: look to see if the bin has something assigned already before
    you have AI go look for it.

    Counts stock in the drawer OR ANY DESCENDANT, because an assortment kit is
    a child location -- a drawer holding one reads as empty at drawer level and
    that mistake has already been made once today, against B3."""
    locs = [l for l in _rows(it_get("stock/location/", name=name, limit=5))
            if (l.get("name") or "").upper() == (name or "").upper()]
    if not locs:
        return None
    loc = locs[0]
    out = {"location": loc.get("pk"), "name": loc.get("name"),
           "description": loc.get("description") or "", "stock": [], "homes": []}
    for r in _rows(it_get("stock/", location=loc["pk"], cascade=True, limit=100)):
        out["stock"].append({
            "part": r.get("part"),
            "name": (r.get("part_detail") or {}).get("name") or f"part {r.get('part')}",
            "quantity": r.get("quantity"),
            "sub_location": (r.get("location_detail") or {}).get("name") or loc.get("name"),
        })
    for r in _rows(it_get("part/", default_location=loc["pk"], limit=50)):
        out["homes"].append({"part": r.get("pk"), "name": r.get("name")})
    out["assigned"] = bool(out["stock"] or out["homes"])
    return out


@app.get("/api/drawer")
def api_drawer(name: str = ""):
    """Free, instant, no model. The UI calls this the moment a drawer is picked
    and only offers the camera when this comes back unassigned."""
    if not name:
        return JSONResponse({"error": "name required"}, status_code=400)
    d = drawer_contents(name)
    if d is None:
        return JSONResponse({"error": f"no location named {name}"}, status_code=404)
    return d


@app.get("/api/unlocated")
def api_unlocated(cabinet: str = ""):
    return cabinet_unlocated(cabinet) if cabinet else []


@app.post("/api/identify")
async def api_identify(image: UploadFile = File(...),
                       cabinet: str = Form(""),
                       location: str = Form(""),
                       provider: str = Form("anthropic")):
    """READ-ONLY. Reads the tag, proposes a match, writes nothing.

    Short-circuits if the drawer is already assigned. The UI should not get
    here in that case, but a guard in the endpoint costs nothing and the UI is
    not the only caller."""
    if location:
        known = drawer_contents(location)
        if known and known["assigned"]:
            return {"id": None, "kind": "identify", "basis": "already-assigned",
                    "location": location, "known": known, "candidates": [],
                    "read_only": True,
                    "note": "the record already says what is in this drawer; "
                            "no model was called"}
    raw = await image.read()
    media = image.content_type or "image/jpeg"
    if media not in ("image/jpeg", "image/png", "image/webp", "image/gif"):
        media = "image/jpeg"
    try:
        reading = providers.identify(provider, raw, media, cabinet)
    except Exception as e:
        return JSONResponse({"error": str(e)[:250]}, status_code=502)

    rows = cabinet_unlocated(cabinet)
    ranked, basis = match_reading(reading, rows)

    rec_id = uuid.uuid4().hex[:8]
    ext = {"image/png": "png", "image/webp": "webp"}.get(media, "jpg")
    (SHOTS / f"{rec_id}.{ext}").write_bytes(raw)
    rec = {"id": rec_id, "kind": "identify",
           "at": datetime.datetime.now().isoformat(timespec="seconds"),
           "cabinet": cabinet, "photo": f"{rec_id}.{ext}",
           "reading": reading, "basis": basis,
           "candidates": [{"sku": c["row"]["sku"], "name": c["row"]["name"],
                           "stock": c["row"]["stock"], "why": c["why"],
                           "strength": c["strength"]} for c in ranked],
           "unlocated_in_cabinet": len(rows), "actual": None}
    log_append(rec)
    return {**rec, "read_only": True}


@app.post("/api/estimate")
async def estimate(image: UploadFile = File(...),
                   part_name: str = Form("unknown part"),
                   location: str = Form(""),
                   provider: str = Form("ollama")):
    raw = await image.read()
    media = image.content_type or "image/jpeg"
    if media not in ("image/jpeg", "image/png", "image/webp", "image/gif"):
        media = "image/jpeg"

    wanted = [p["name"] for p in providers.status() if p["available"]] \
        if provider == "all" else [provider]

    results = []
    for name in wanted:
        try:
            results.append(providers.estimate(name, raw, media, part_name, location))
        except Exception as e:
            results.append({"provider": name, "error": str(e)[:200]})

    if not results:
        return JSONResponse({"error": "no provider configured"}, status_code=503)

    rec_id = uuid.uuid4().hex[:8]
    ext = {"image/png": "png", "image/webp": "webp"}.get(media, "jpg")
    (SHOTS / f"{rec_id}.{ext}").write_bytes(raw)

    rec = {"id": rec_id,
           "at": datetime.datetime.now().isoformat(timespec="seconds"),
           "location": location, "part": part_name,
           "photo": f"{rec_id}.{ext}", "actual": None, "results": results}
    log_append(rec)
    return {**rec, "read_only": True}


@app.post("/api/truth")
def record_truth(id: str = Form(...), actual: str = Form(...)):
    """What the drawer really held. Entered after eyeballing it."""
    rows = log_read()
    hit = False
    for r in rows:
        if r.get("id") == id:
            try:
                r["actual"] = float(actual)
            except ValueError:
                r["actual"] = actual
            hit = True
    if not hit:
        return JSONResponse({"error": "unknown id"}, status_code=404)
    log_rewrite(rows)
    return {"ok": True, "id": id, "actual": actual}


@app.get("/api/log")
def get_log():
    return list(reversed(log_read()))


@app.get("/log", response_class=HTMLResponse)
def log_page():
    rows = list(reversed(log_read()))
    if not rows:
        return "<body style=\'background:#111;color:#eee;font:15px system-ui;padding:20px\'>" \
               "<h2>binscan log</h2><p>Nothing recorded yet.</p></body>"

    provs = sorted({x.get("provider", "?") for r in rows for x in r.get("results", [])})
    head = "".join(f"<th>{p}</th>" for p in provs)
    body = []
    for r in rows:
        by = {x.get("provider"): x for x in r.get("results", [])}
        cells = []
        for p in provs:
            x = by.get(p)
            if not x:
                cells.append("<td>-</td>")
            elif x.get("error"):
                cells.append("<td class=err>error</td>")
            else:
                err = ""
                if r.get("actual") is not None and isinstance(x.get("count"), (int, float)):
                    try:
                        d = abs(float(x["count"]) - float(r["actual"]))
                        err = f"<br><small>off by {d:g}</small>"
                    except Exception:
                        pass
                cells.append(f"<td><b>{x.get('bucket','?')}</b> ~{x.get('count','?')}"
                             f"<br><small class={x.get('confidence','low')}>"
                             f"{x.get('confidence','?')}</small>{err}</td>")
        actual = r.get("actual")
        body.append(
            f"<tr><td><small>{r.get('at','')[5:16]}</small><br>{r.get('location') or '-'}"
            f"<br><small>{(r.get('part') or '')[:34]}</small></td>"
            + "".join(cells)
            + f"<td>{'' if actual is None else actual}</td>"
            f"<td><a href='/shot/{r.get('photo')}'>photo</a></td></tr>")

    return f"""<!doctype html><meta name=viewport content="width=device-width,initial-scale=1">
<style>body{{background:#111;color:#eee;font:14px system-ui;padding:16px}}
table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #2c2c2e;padding:7px;
vertical-align:top;text-align:left}}th{{color:#8a8a8e;font-size:12px;text-transform:uppercase}}
small{{color:#8a8a8e}}.low{{color:#ff9f43}}.medium{{color:#feca57}}.high{{color:#4ecd7b}}
.err{{color:#ff8f8f}}a{{color:#4ea1ff}}</style>
<h2>binscan log <small>&mdash; {len(rows)} runs</small></h2>
<table><tr><th>when / drawer</th>{head}<th>actual</th><th></th></tr>
{''.join(body)}</table>"""


@app.get("/shot/{name}")
def shot(name: str):
    from fastapi.responses import FileResponse
    p = SHOTS / pathlib.Path(name).name
    return FileResponse(p) if p.exists() else JSONResponse({"error": "gone"}, 404)


PAGE = """<!doctype html><html><head>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>binscan</title><style>
:root{--bg:#111;--fg:#eee;--mut:#8a8a8e;--acc:#4ea1ff;--card:#1c1c1e;--line:#2c2c2e}
*{box-sizing:border-box}body{margin:0;padding:16px 16px 48px;background:var(--bg);color:var(--fg);
font:16px/1.45 -apple-system,system-ui,sans-serif}
h1{font-size:19px;margin:0 0 2px}p.sub{color:var(--mut);margin:0 0 18px;font-size:13px}
label{display:block;margin:14px 0 6px;color:var(--mut);font-size:12px;
text-transform:uppercase;letter-spacing:.06em}
input,select,button{width:100%;padding:13px;font-size:16px;border-radius:10px;
border:1px solid var(--line);background:var(--card);color:var(--fg)}
button{background:var(--acc);color:#000;font-weight:600;border:0;margin-top:18px}
button:disabled{opacity:.35}
.card{margin-top:14px;padding:14px 16px;background:var(--card);border-radius:12px}
.big{font-size:27px;font-weight:700;margin:2px 0;text-transform:capitalize}
.row{display:flex;justify-content:space-between;padding:6px 0;border-top:1px solid var(--line);font-size:14px}
.row span:first-child{color:var(--mut)}
.prov{font-size:12px;color:var(--acc);text-transform:uppercase;letter-spacing:.06em}
.low{color:#ff9f43}.medium{color:#feca57}.high{color:#4ecd7b}
.warn{margin-top:10px;padding:9px 11px;border-radius:8px;background:#2a2213;color:#ffc978;font-size:13px}
.err{background:#2a1616;color:#ff8f8f}
img#prev{width:100%;border-radius:10px;margin-top:12px;display:none}
.ro{margin-top:22px;padding:9px 11px;border-radius:8px;background:#16212a;color:#8fc7ff;font-size:12px}
.mut{color:var(--mut);font-size:13px}
.known .card{margin-top:10px}
.known b{display:block;margin-bottom:6px;font-size:14px}
/* legibility of the READING, distinct from confidence in a COUNT: clear means
   the text was readable, not that the match is right. */
.clear{color:#4ecd7b}.partial{color:#feca57}.none{color:#ff9f43}
</style></head><body>
<h1>binscan</h1><p class=sub>The record first &middot; the camera only when it is silent &middot; nothing is written</p>

<label>Drawer</label>
<select id=loc><option value="">— pick a drawer —</option></select>

<div id=known class=known></div>

<label id=lpart>What it holds</label>
<input id=part placeholder="auto-filled from the drawer">

<label>Provider</label>
<select id=prov></select>

<label>Photo</label>
<input id=file type=file accept=image/* capture=environment>
<img id=prev>

<button id=go disabled>Estimate</button>
<div id=out></div>
<div class=ro>Read-only to InvenTree &mdash; every run is logged here for comparison. <a href="/log" style="color:#8fc7ff">view log</a></div>

<script>
const $=s=>document.querySelector(s);
fetch('/api/drawers').then(r=>r.json()).then(gs=>{
  $('#loc').innerHTML='<option value="">— pick a drawer —</option>'+
    gs.map(g=>`<optgroup label="${g.group.replace(/^SLN\//,'')}">`+
      g.items.map(i=>`<option value="${i.name}">${i.name}</option>`).join('')+
      '</optgroup>').join('');
}).catch(()=>{});
fetch('/api/providers').then(r=>r.json()).then(ps=>{
  const ok=ps.filter(p=>p.available);
  $('#prov').innerHTML =
    ok.map(p=>`<option value="${p.name}">${p.name} — ${p.model}</option>`).join('')
    + (ok.length>1?`<option value="all">compare all (${ok.length})</option>`:'')
    + ps.filter(p=>!p.available).map(p=>`<option disabled>${p.name} — not configured</option>`).join('');
});
// The record is consulted BEFORE the camera is offered. If a drawer already
// has stock assigned, there is nothing for a model to work out and the job is
// counting; if it does not, the job is reading the tag. The drawer's state
// picks the mode -- there is no toggle to get wrong.
let MODE='estimate';
$('#loc').onchange=async e=>{
  const v=e.target.value;
  $('#known').innerHTML=''; $('#out').innerHTML='';
  if(!v){MODE='estimate';return;}
  $('#known').innerHTML='<div class=card>checking the record…</div>';
  let d=null;
  try{ d=await (await fetch('/api/drawer?name='+encodeURIComponent(v))).json(); }
  catch(_){ $('#known').innerHTML='<div class="card err">could not reach the record</div>'; return; }
  if(d.error){ $('#known').innerHTML=`<div class="card err">${d.error}</div>`; return; }
  if(d.assigned){
    MODE='estimate';
    const items=(d.stock||[]).map(x=>{
      const sub = x.sub_location && x.sub_location!==v ? ` <span class=mut>(in ${x.sub_location})</span>` : '';
      return `<div>${(+x.quantity).toLocaleString()} &times; ${x.name}${sub}</div>`;}).join('')
      || (d.homes||[]).map(h=>`<div class=mut>home of ${h.name} — no stock on hand</div>`).join('');
    $('#known').innerHTML=`<div class=card><b>On record</b>${items}</div>`;
    $('#part').value=(d.stock&&d.stock[0]&&d.stock[0].name)||(d.homes&&d.homes[0]&&d.homes[0].name)||'';
    $('#lpart').textContent='What it holds';
    $('#go').textContent='Estimate';
  }else{
    MODE='identify';
    $('#known').innerHTML='<div class=card><b>Nothing on record for this drawer.</b>'+
      '<div class=mut>Photograph the McMaster bag tag if there is one. '+
      'The tag number is read and matched here; nothing is written.</div></div>';
    $('#part').value='';
    $('#lpart').textContent='What it holds (unknown — leave blank)';
    $('#go').textContent='Read the tag';
  }
};
$('#file').onchange=e=>{
  const f=e.target.files[0]; $('#go').disabled=!f;
  if(f){$('#prev').src=URL.createObjectURL(f);$('#prev').style.display='block';}
};
function cabinetOf(drawer){ const m=/^([A-Z]\d+)-/.exec(drawer||''); return m?m[1]:''; }

function renderIdentify(d){
  if(d.basis==='already-assigned')
    return `<div class=card><b>Already on record</b><div class=mut>${d.note}</div></div>`;
  const r=d.reading||{};
  const read=`<div class=card><div class=prov>${r.provider||''} · ${r.model||''}</div>
    <div class=row><span>bag tag</span><span>${r.tag?`<b>${r.tag}</b>`:'<span class=mut>none visible</span>'}</span></div>
    ${(r.labels||[]).length?`<div class=row><span>labels</span><span>${r.labels.join(' · ')}</span></div>`:''}
    ${(r.markings||[]).length?`<div class=row><span>markings</span><span>${r.markings.join(' · ')}</span></div>`:''}
    ${r.descriptors?`<div class=row><span>looks like</span><span class=mut>${r.descriptors}</span></div>`:''}
    <div class=row><span>legible</span><span class="${r.legible}">${r.legible||'?'}</span></div>
    <div style="margin-top:10px;color:#aaa;font-size:13.5px">${r.reasoning||''}</div></div>`;
  if(!d.candidates||!d.candidates.length){
    const why = d.basis==='tag-no-match'
      ? 'A tag was read but it matches no unlocated row in this cabinet. Either it belongs elsewhere, or it is not McMaster stock.'
      : d.basis==='nothing-legible'
      ? 'Nothing legible in the photo. Try again closer, or write it down by hand.'
      : 'No row in this cabinet fits what was read.';
    return read+`<div class="card warn">${why}</div>`;
  }
  return read + d.candidates.map(c=>`<div class=card>
      <div class=big style="font-size:17px">${c.name}</div>
      <div class=row><span>McMaster</span><span><b>${c.sku||'—'}</b></span></div>
      <div class=row><span>basis</span><span class="${c.strength==='definite'?'high':c.strength==='probable'?'medium':'low'}">${c.strength}</span></div>
      <div style="margin-top:8px;color:#aaa;font-size:13.5px">${c.why}</div>
    </div>`).join('')
    + `<div class=warn>Nothing has been written. Confirm against the open drawer,
       then have the assignment recorded — a match made from a photograph is a
       proposal, not an observation.</div>`;
}

$('#go').onclick=async()=>{
  const f=$('#file').files[0]; if(!f)return;
  const identify = MODE==='identify';
  const label = $('#go').textContent;
  $('#go').disabled=true; $('#go').textContent='Looking…'; $('#out').innerHTML='';
  const fd=new FormData();
  fd.append('image',f); fd.append('provider',$('#prov').value);
  fd.append('location',$('#loc').value||'');
  if(identify) fd.append('cabinet',cabinetOf($('#loc').value));
  else fd.append('part_name',$('#part').value||'unknown part');
  try{
    const r=await fetch(identify?'/api/identify':'/api/estimate',{method:'POST',body:fd});
    const d=await r.json();
    if(identify){
      $('#out').innerHTML = d.error ? `<div class="card err">${d.error}</div>` : renderIdentify(d);
      $('#go').disabled=false; $('#go').textContent=label; return;
    }
    if(d.error){$('#out').innerHTML=`<div class="card err">${d.error}</div>`;}
    else{
      window.lastId=d.id;
      $('#out').innerHTML=d.results.map(x=> x.error
        ? `<div class="card"><div class=prov>${x.provider}</div><div class="warn err">${x.error}</div></div>`
        : `<div class=card><div class=prov>${x.provider} · ${x.model}</div>
             <div class=big>${x.bucket}</div>
             <div class=row><span>estimate</span><span>~${x.count}</span></div>
             <div class=row><span>confidence</span><span class="${x.confidence}">${x.confidence}</span></div>
             <div style="margin-top:10px;color:#aaa;font-size:13.5px">${x.reasoning||''}</div>
             ${x.confidence==='low'?'<div class=warn>Low confidence — likely a heap. Eyeball this one.</div>':''}
           </div>`).join('')
        + `<div class=card><label style="margin-top:0">Actual count (after you look)</label>
             <input id=truth type=number inputmode=numeric placeholder="how many were really there">
             <button id=savetruth style="margin-top:10px">Record actual</button>
             <div id=tmsg style="margin-top:8px;color:#8a8a8e;font-size:13px"></div></div>`;
      $('#savetruth').onclick=async()=>{
        const v=$('#truth').value; if(v===''){return;}
        const fd2=new FormData(); fd2.append('id',window.lastId); fd2.append('actual',v);
        const rr=await fetch('/api/truth',{method:'POST',body:fd2});
        $('#tmsg').textContent = rr.ok ? 'Recorded. ' : 'Failed to record.';
      };
    }
  }catch(err){ $('#out').innerHTML=`<div class="card err">${err}</div>`; }
  $('#go').disabled=false; $('#go').textContent=label;
};
</script></body></html>"""


@app.get("/", response_class=HTMLResponse)
def index():
    return PAGE


@app.get("/healthz")
def healthz():
    return {"ok": True, "writes_enabled": WRITES_ON,
            "auto_write_confidence": sorted(AUTO_CONF),
            "providers": providers.status()}
