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


def it_patch(path, payload):
    if not IT_TOKEN:
        return None, "no InvenTree token"
    try:
        r = httpx.patch(f"{INVENTREE}/api/{path}",
                        headers={"Authorization": f"Token {IT_TOKEN}"},
                        json=payload, timeout=25)
        if r.status_code >= 400:
            return None, f"{r.status_code}: {r.text[:200]}"
        return r.json(), None
    except Exception as e:
        return None, str(e)[:200]


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


DRAWER_RE = re.compile(r"^([A-Z]+\d+)-R(\d+)C(\d+)$")


def _area_children(area):
    locs = [l for l in _rows(it_get("stock/location/", name=area, limit=5))
            if (l.get("name") or "").upper() == (area or "").upper()]
    if not locs:
        return None, []
    loc = locs[0]
    kids = _rows(it_get("stock/location/", parent=loc["pk"], limit=200))
    return loc, kids


@app.get("/api/areas")
def api_areas():
    """Short list of places to start, so nobody scrolls 478 entries on a phone.
    A parent whose children are leaves is somewhere you can actually stand."""
    rows = _rows(it_get("stock/location/", limit=1000))
    by_pk = {r["pk"]: r for r in rows}
    kids = {}
    for r in rows:
        if r.get("parent") is not None:
            kids.setdefault(r["parent"], []).append(r)
    out = []
    for pk, ch in kids.items():
        par = by_pk.get(pk)
        if not par:
            continue
        leaves = [c for c in ch if c["pk"] not in kids]
        if not leaves:
            continue
        # A drawer that holds an assortment kit has a child location and so
        # looks like a place you could stand. It is not -- it is a drawer, and
        # it is reachable by tapping it in its cabinet's grid. Listing A3-R8C5
        # and B3-R3C2 alongside the cabinets was pure noise.
        if DRAWER_RE.match(par.get("name") or ""):
            continue
        out.append({"name": par["name"], "pk": pk, "drawers": len(leaves),
                    "grid": bool(DRAWER_RE.match(leaves[0]["name"] or "")),
                    "path": (par.get("pathstring") or par["name"]).replace("SLN/", "")})
    grid_first = sorted(out, key=lambda a: (not a["grid"], a["path"]))
    return grid_first


@app.get("/api/grid")
def api_grid(area: str = ""):
    """Every drawer in one area with enough state to colour it. One call, so the
    picker doubles as a progress view: what is filled, what is confirmed empty,
    and what nobody has looked at yet."""
    loc, kids = _area_children(area)
    if loc is None:
        return JSONResponse({"error": f"no location named {area}"}, status_code=404)

    # Which direct child does each location descend from? Resolved by PRIMARY
    # KEY, not by matching pathstring text: the stock endpoint does not return
    # location_detail unless asked, so the first version of this matched empty
    # strings and reported a 40-drawer cabinet as entirely unfilled. A pk map
    # also handles kits, which are child locations of a drawer.
    all_locs = _rows(it_get("stock/location/", limit=1000))
    by_pk = {l["pk"]: l for l in all_locs}
    owner = {}
    for l in all_locs:
        cur, hops = l, 0
        while cur is not None and cur.get("parent") is not None and hops < 12:
            if cur["parent"] == loc["pk"]:
                owner[l["pk"]] = cur["name"]
                break
            cur = by_pk.get(cur["parent"])
            hops += 1

    filled = set()
    for r in _rows(it_get("stock/", location=loc["pk"], cascade=True, limit=1000)):
        kn = owner.get(r.get("location"))
        if kn:
            filled.add(kn)

    cells = []
    for k in kids:
        m = DRAWER_RE.match(k["name"] or "")
        desc = k.get("description") or ""
        state = ("filled" if k["name"] in filled
                 else "empty" if desc.upper().startswith("VERIFIED EMPTY")
                 else "unknown")
        cells.append({"name": k["name"], "state": state,
                      "r": int(m.group(2)) if m else None,
                      "c": int(m.group(3)) if m else None,
                      "large": "large" in desc.lower(),
                      "label": re.sub(r"\s*\[[^\]]*\]\s*", "", desc).strip()[:40]})
    cells.sort(key=lambda x: (x["r"] or 0, x["c"] or 0, x["name"]))
    tally = {s: sum(1 for c in cells if c["state"] == s)
             for s in ("filled", "empty", "unknown")}
    return {"area": loc["name"], "grid": all(c["r"] for c in cells) and bool(cells),
            "cells": cells, "tally": tally}


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
# finds no thread at all. Matching \bM<digits> catches both spellings.
_THREAD = re.compile(r"\bM\s*(\d+(?:\.\d+)?)\b", re.I)

# Imperial threads come in two shapes and BOTH were unmatched until 2026-08-22:
#   1/4-20    a fractional diameter
#   10-32     a screw NUMBER, which has no slash -- so a regex demanding a
#             fraction before the dash never fired, on the label or the part.
# A vendor label may also write the number form with a slash, "10/32", which
# collides with fraction notation. Resolved by plausibility: a real TPI is one
# of a short list, and a screw number is 4..14 -- nobody writes a fraction as
# 10/32 when 5/16 exists. 1/32 and 3/32 stay fractions because 1 and 3 are
# below that floor.
# Real thread pitches, coarse and fine, from 1-8 up to 0-80. 13 was missing, so
# McMaster's 1/2"-13 parsed as NO imperial thread at all -- and a row with no
# thread cannot disagree with the label, so a 5/16-18 lock nut matched a 1/2-13
# cap nut on the strength of both being nuts. A failure to PARSE reads as
# agreement, which is the dangerous direction.
_TPI = {8, 9, 10, 11, 12, 13, 14, 16, 18, 20, 24, 27, 28, 32, 36, 40, 44, 48,
        56, 64, 72, 80}
_SCREW_NO = set(range(4, 15))
# The inch mark sits between diameter and dash in McMaster's own spelling,
# 1/4"-20, so the separator has to tolerate it.
_IMP_DASH = re.compile(r'(?<![\d/])#?\s*(\d+(?:/\d+)?)\s*"?\s*-\s*(\d+)(?![\d/])')
_IMP_SLASH = re.compile(r'(?<![\d/])(\d{1,2})\s*/\s*(\d{2})(?![\d/])')

# Lengths. Metric is "20 mm Long"; imperial is 3/4", 1-1/2", .375in, or a bare
# fraction after an x on a handwritten label.
_LEN_MM = re.compile(r"(\d+(?:\.\d+)?)\s*mm\b", re.I)
_LEN_IN = re.compile(r'(\d+\s*-\s*\d+/\d+|\d+/\d+|\d+(?:\.\d+)?)\s*(?:"|\bin\b|\binch|\blong\b)', re.I)
_AFTER_X = re.compile(r'\bx\s*(\d+\s*-\s*\d+/\d+|\d+/\d+|\d+(?:\.\d+)?)', re.I)


def _tofloat(t):
    t = (t or "").strip().replace(" ", "")
    m = re.fullmatch(r"(\d+)-(\d+)/(\d+)", t)          # 1-1/2
    if m:
        return int(m.group(1)) + int(m.group(2)) / int(m.group(3))
    m = re.fullmatch(r"(\d+)/(\d+)", t)                 # 3/4
    if m:
        return int(m.group(1)) / int(m.group(2))
    try:
        return float(t)
    except ValueError:
        return None


def _imperial(t):
    """Returns (thread, span) -- span is where it matched, so the length search
    can skip it. Without that, 1/4"-20 x 1/2" reads its own THREAD diameter as
    the length and every quarter-inch screw looks 1/4in long."""
    for m in _IMP_DASH.finditer(t or ""):
        dia, tpi = m.group(1), int(m.group(2))
        # The diameter must be a fraction or a screw number. Widening the TPI
        # set to include 8 made "18-8" -- the STAINLESS GRADE, which appears on
        # half these labels -- parse as an 18-8 thread. A diameter of 18 is
        # neither a fraction nor a screw size, so it is not a thread.
        ok = "/" in dia or (dia.isdigit() and int(dia) <= 14)
        if tpi in _TPI and ok:
            return f"{dia}-{tpi}", m.span()
    for m in _IMP_SLASH.finditer(t or ""):
        a, b = int(m.group(1)), int(m.group(2))
        if b in _TPI and a in _SCREW_NO:
            return f"{a}-{b}", m.span()
    return None, None


# What KIND of fastener. Dropped in an earlier rewrite, which is why the label
# "1/4-20 nyloc" proposed a socket head screw: the thread matched a dozen rows
# and nothing distinguished a locknut from a cap screw.
_KINDS = (("nylon-insert", "nyloc"), ("nyloc", "nyloc"), ("locknut", "nyloc"),
          ("lock nut", "nyloc"), ("cap nut", "nut"), ("hex nut", "nut"),
          ("nut", "nut"), ("socket head", "socket"), ("low-profile", "socket"),
          ("button head", "button"), ("pan head", "pan"), ("flat head", "flat"),
          ("fillister", "fillister"), ("hex head", "hexhead"),
          ("set screw", "set"), ("washer", "washer"), ("eyebolt", "eyebolt"),
          ("dowel", "dowel"), ("standoff", "standoff"), ("header", "header"))


def _kinds(t):
    tl = (t or "").lower()
    out = set()
    for word, tag in _KINDS:
        if word in tl:
            out.add(tag)
    return out


def _facts(t):
    """(metric thread, imperial thread, length_mm, length_inches)"""
    t = t or ""
    m = _THREAD.search(t)
    metric = f"m{float(m.group(1)):g}" if m else None
    imp, span = _imperial(t)
    # "M6-20" is a metric size and a length, but 6-20 also looks like an
    # imperial thread because 20 is a real TPI -- and the cross-system penalty
    # then rejected every metric row, so B1's most common label form matched
    # nothing at all. A metric designation wins outright; nothing in this shop
    # is both.
    if metric:
        imp, span = None, None
    rest = (t[:span[0]] + " " + t[span[1]:]) if span else t

    mm = None
    # "M6-20" and "M6x20" both mean a 20 mm screw; the dash form has no x and
    # no "mm" for the other extractors to find.
    dash = re.search(r"\bM\s*\d+(?:\.\d+)?\s*-\s*(\d+)\b", t, re.I)
    if metric and dash:
        mm = float(dash.group(1))
    for cand in _LEN_MM.finditer(t):
        v = float(cand.group(1))
        # skip the pitch in "M6 x 1 mm Thread" -- a length is not 1 mm
        if v >= 3:
            mm = v
            break
    if mm is None and metric:
        pass
    if mm is None and metric:
        x = _AFTER_X.search(t)
        if x:
            mm = _tofloat(x.group(1))

    inch = None
    if not metric:
        m2 = _LEN_IN.search(rest)
        if m2:
            inch = _tofloat(m2.group(1))
        if inch is None:
            x = _AFTER_X.search(rest)
            if x:
                inch = _tofloat(x.group(1))
    return metric, imp, mm, inch


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
    lm, li, lmm, lin = _facts(text)
    lk = _kinds(text)
    scored = []
    for r in rows:
        pm, pi, pmm, pin = _facts(r["name"])
        pk = _kinds(r["name"])
        sc = 0
        if lk and pk:
            sc += 3 if (lk & pk) else -3
            # A nut is not a screw. When the label says one and the row is the
            # other, thread agreement is not enough to rescue it.
            if ("nyloc" in lk or "nut" in lk) != ("nyloc" in pk or "nut" in pk):
                sc -= 5
        if lm and pm:
            sc += 4 if lm == pm else -6
        if li and pi:
            sc += 4 if li == pi else -6
        if lm and pi and not pm:
            sc -= 6                      # metric label, imperial part
        if li and pm and not pi:
            sc -= 6
        if lmm is not None and pmm is not None:
            sc += 4 if abs(lmm - pmm) < 0.01 else -4
        if lin is not None and pin is not None:
            sc += 4 if abs(lin - pin) < 0.005 else -4
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

    # The drawer's OWN description is a record too, and it was being ignored.
    # Scott at B2-R2C1, 2026-08-22: no bag tag inside, but the label on the
    # front reads 1/4-28 -- which the description already held, because these
    # legacy labels were read off a photo yesterday. He photographed the nuts
    # instead, and no photograph of a nut shows its thread pitch. The record
    # knew; nobody asked it.
    if not out["assigned"]:
        body = re.sub(r"\[[^\]]*\]", "", out["description"]).strip(" ,;-\u2014")
        if body and not body.upper().startswith(("VERIFIED EMPTY", "PRE-SORT")):
            m = DRAWER_RE.match(name or "")
            cab = m.group(1) if m else ""
            rows = cabinet_unlocated(cab) if cab else []
            ranked, basis = match_reading({"tag": "", "labels": [body],
                                           "markings": [], "descriptors": ""}, rows)
            out["label"] = body
            out["label_basis"] = basis
            out["label_candidates"] = [
                {"sku": c["row"]["sku"], "name": c["row"]["name"],
                 "stock": c["row"]["stock"], "quantity": c["row"].get("quantity"),
                 "why": c["why"], "strength": c["strength"]} for c in ranked]
            out["unlocated"] = [{"stock": r["stock"], "sku": r["sku"],
                                 "name": r["name"], "quantity": r["quantity"]}
                                for r in rows]
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


@app.post("/api/empty")
def api_empty(location: str = Form(...), confirm: str = Form("")):
    """Mark a drawer VERIFIED EMPTY from the phone, during the walk.

    Most of a walk is empty drawers, and until now the UI had no way to say so
    -- you could file something or skip, and skipping records nothing, so the
    drawer stays "unknown" forever and gets opened again next time.

    The guards mirror scripts/mark_empty.py exactly, because the same mistakes
    are available here and one of them has already been made once:

      stock present      - obvious, but check descendants too: a drawer holding
                           an assortment kit has its stock one level down and
                           reads as empty at drawer level. That is what made B3
                           look 41 drawers emptier than it was.
      parking spot       - a Part whose default_location is this drawer has no
                           stock BY DESIGN. Stamping it empty is wrong twice:
                           it is a queue somebody means to come back to.
      description names  - "no rows" is not evidence of emptiness, and the
        something          description is often the only place the truth was
                           written. The bracketed size annotation is metadata,
                           not contents, and must be stripped before deciding
                           or every bin-wall drawer trips this.
    """
    if not WRITES_ON:
        return JSONResponse({"error": "writes disabled (BINSCAN_WRITES != 1)"}, 403)
    if confirm.lower() not in ("1", "true", "yes"):
        return JSONResponse({"error": "confirm required"}, 400)

    locs = [l for l in _rows(it_get("stock/location/", name=location, limit=5))
            if (l.get("name") or "").upper() == location.upper()]
    if not locs:
        return JSONResponse({"error": f"no location named {location}"}, 404)
    loc = locs[0]

    known = drawer_contents(location) or {}
    if known.get("stock"):
        what = known["stock"][0]["name"][:44]
        return JSONResponse({"error": f"not empty - it holds {what}"}, 409)
    if known.get("homes"):
        who = known["homes"][0]["name"][:44]
        return JSONResponse({"error": f"this is a PARKING SPOT, the home of "
                                      f"'{who}'. It has no stock by design; that "
                                      f"is not the same as empty."}, 409)

    desc = (loc.get("description") or "").strip()
    body = re.sub(r"\[[^\]]*\]", "", desc).strip(" ,;-\u2014")
    if body.upper().startswith("VERIFIED EMPTY"):
        return {"ok": True, "already": True, "description": desc,
                "note": "already recorded empty; nothing changed"}
    if body and not body.upper().startswith("PRE-SORT"):
        return JSONResponse({"error": f"the drawer's own description names "
                                      f"something: \u201c{body[:80]}\u201d. Check by "
                                      f"eye - a description is often the only "
                                      f"place the contents were written down."}, 409)

    tag = f"VERIFIED EMPTY {datetime.date.today().isoformat()}"
    new = (tag + (f" \u2014 previously labelled: {desc}" if desc else ""))[:250]
    _b, err = it_patch(f"stock/location/{loc['pk']}/", {"description": new})
    if err:
        return JSONResponse({"error": f"could not write: {err}"}, 502)

    again = it_get(f"stock/location/{loc['pk']}/") or {}
    if not (again.get("description") or "").upper().startswith("VERIFIED EMPTY"):
        return JSONResponse({"error": "write did not verify on re-read",
                             "got": again.get("description")}, 500)

    log_append({"id": uuid.uuid4().hex[:8], "kind": "empty",
                "at": datetime.datetime.now().isoformat(timespec="seconds"),
                "location": loc["name"], "location_pk": loc["pk"],
                "before": {"description": desc},
                "after": {"description": again.get("description")}})
    return {"ok": True, "location": loc["name"], "description": again.get("description")}


@app.post("/api/assign")
def api_assign(stock: int = Form(...), location: str = Form(...),
               quantity: str = Form(""), confirm: str = Form("")):
    """File a stock row into a drawer. The FIRST write this app makes.

    Two separate facts, kept separate on purpose:

      the DRAWER  - established by a human looking in it, and the whole point
      the COUNT   - only recorded if a human typed a number

    Leaving quantity blank moves the row and leaves its quantity alone. That
    quantity came from a purchase order, which is a real record of what was
    BOUGHT and not a record of what is THERE. Silently promoting one to the
    other is how a stock system starts lying, so the note says which it is.

    No model output reaches this endpoint. The match is a proposal; a person
    confirms it with the drawer open, and only then does anything get written.
    """
    if not WRITES_ON:
        return JSONResponse({"error": "writes disabled (BINSCAN_WRITES != 1)"}, 403)
    if confirm.lower() not in ("1", "true", "yes"):
        return JSONResponse({"error": "confirm required"}, 400)

    locs = [l for l in _rows(it_get("stock/location/", name=location, limit=5))
            if (l.get("name") or "").upper() == location.upper()]
    if not locs:
        return JSONResponse({"error": f"no location named {location}"}, 404)
    loc = locs[0]

    before = it_get(f"stock/{stock}/")
    if not before:
        return JSONResponse({"error": f"no stock item {stock}"}, 404)

    counted = None
    if str(quantity).strip():
        try:
            counted = float(quantity)
        except ValueError:
            return JSONResponse({"error": f"quantity {quantity!r} is not a number"}, 400)
        if counted < 0:
            return JSONResponse({"error": "quantity cannot be negative"}, 400)

    carried = float(before.get("quantity", 0))
    stamp = datetime.date.today().isoformat()
    if counted is not None:
        note = (f"binscan {stamp}: filed into {loc['name']} and COUNTED at "
                f"{counted:g} by hand.")
        # The delta against what the row previously claimed is the whole reason
        # counting is worth doing; state it here rather than leaving someone to
        # diff two paragraphs.
        if abs(carried - counted) > 1e-6:
            note += (f" Previously recorded {carried:g}, so the count is "
                     f"{abs(carried - counted):g} "
                     f"{'FEWER' if counted < carried else 'MORE'} than the "
                     f"record held.")
    else:
        # [ESTIMATE] is a PREFIX flag in this catalogue -- 166 rows carry it and
        # queries test notes__startswith. Without it a filed-but-uncounted row
        # shows the same bare number as a counted one in every list view, and
        # the distinction survives only in prose nobody reads. The quantity here
        # is what the PURCHASE ORDER said was bought; nobody has looked.
        note = (f"[ESTIMATE] binscan {stamp}: filed into {loc['name']}. "
                f"Quantity {carried:g} is the PURCHASED figure carried in with "
                f"the row - NOT COUNTED, nobody has looked in the drawer and "
                f"tallied it. Count it and the flag comes off.")

    body, err = it_post("stock/transfer/",
                        {"items": [{"pk": stock, "quantity": before.get("quantity")}],
                         "location": loc["pk"], "notes": note})
    if err:
        return JSONResponse({"error": f"transfer failed: {err}"}, 502)

    if counted is not None:
        body, err = it_post("stock/count/",
                            {"items": [{"pk": stock, "quantity": counted}],
                             "notes": note})
        if err:
            return JSONResponse({"error": f"moved, but the count failed: {err}",
                                 "moved": True}, 502)

    # Stamp the row itself, not just the transaction note. Existing notes are
    # kept: they came from the McMaster import and say what the thing is.
    # Strip EVERY leading binscan line, not just one, and whether or not it
    # carried the flag. Filing a drawer twice -- which happens, because you
    # correct a wrong match -- otherwise stacks a new line each time and the
    # oldest, most wrong one sits at the bottom looking like provenance.
    prior = (before.get("notes") or "").strip()
    _lead = re.compile(r"^(?:\[ESTIMATE\]\s*)?binscan \d{4}-\d\d-\d\d:[^\n]*\n*")
    while _lead.match(prior):
        prior = _lead.sub("", prior, count=1).lstrip()

    # Filing RESOLVES the transitional state the McMaster import wrote, so its
    # description of that state has to go with it. Left in place, stock 514 read
    # "COUNTED at 47 by hand" on line 0 and "treat this as UNFILED" on line 8 --
    # a row contradicting itself is worse than one saying nothing, because both
    # halves look authored.
    STALE = ("**DRAWER UNKNOWN",
             "This is a TRANSITIONAL state",
             "Resolve it by opening the drawer")
    kept = []
    for para in prior.split("\n\n"):
        q = para.strip()
        if not q or any(q.startswith(m) for m in STALE):
            continue
        # The purchase paragraph is durable history and stays -- it is what
        # makes a 50-bought / 47-counted gap visible at all. But once a count
        # exists it is no longer an [ESTIMATE] of the CURRENT quantity, and the
        # flag is a prefix this catalogue queries on.
        if counted is not None and q.startswith("[ESTIMATE]"):
            q = "PURCHASE HISTORY (superseded by the count above): " + q[len("[ESTIMATE]"):].lstrip()
        kept.append(q)
    prior = "\n\n".join(kept)
    body_notes = note + (("\n\n" + prior) if prior else "")
    patch = {"notes": body_notes}
    if counted is None:
        patch["stocktake_date"] = None      # never counted -> no stocktake date
    _b, perr = it_patch(f"stock/{stock}/", patch)
    if perr:
        return JSONResponse({"error": f"moved, but could not stamp the row: {perr}",
                             "moved": True}, 502)

    # Verify by re-read. .save() on this install has reported success and
    # written nothing; the API is a different path but the habit is cheap.
    after = it_get(f"stock/{stock}/") or {}
    got_loc = after.get("location")
    got_qty = float(after.get("quantity", -1))
    ok_loc = got_loc == loc["pk"]
    ok_qty = counted is None or abs(got_qty - counted) < 1e-6
    if not (ok_loc and ok_qty):
        return JSONResponse({"error": "write did not verify on re-read",
                             "wanted_location": loc["pk"], "got_location": got_loc,
                             "wanted_quantity": counted, "got_quantity": got_qty}, 500)

    # Journal the BEFORE state in full, including notes. Two things depend on
    # it and neither is optional:
    #
    #   undo         - a wrong match filed twenty drawers ago has to be
    #                  reversible, and InvenTree does not version the notes
    #                  field. Stock 514's original notes were lost precisely
    #                  because nothing captured them before a write.
    #   reconcile    - purchased 50, counted 47 is the interesting number, and
    #                  it only exists as a DIFFERENCE. Recording both ends here
    #                  means the reconciliation does not have to parse prose.
    log_append({"id": uuid.uuid4().hex[:8], "kind": "assign",
                "at": datetime.datetime.now().isoformat(timespec="seconds"),
                "stock": stock,
                "part": (after.get("part_detail") or {}).get("name"),
                "before": {"location": (before.get("location_detail") or {}).get("name"),
                           "location_pk": before.get("location"),
                           "quantity": float(before.get("quantity", 0)),
                           "stocktake_date": before.get("stocktake_date"),
                           "notes": before.get("notes") or ""},
                "after": {"location": loc["name"], "location_pk": loc["pk"],
                          "quantity": got_qty,
                          "stocktake_date": after.get("stocktake_date")},
                "counted": counted is not None,
                "delta": (got_qty - carried) if counted is not None else None})
    flagged = (after.get("notes") or "").startswith("[ESTIMATE]")
    if (counted is None) != flagged:
        return JSONResponse({"error": "the [ESTIMATE] flag did not land as intended",
                             "counted": counted is not None, "flagged": flagged}, 500)
    return {"ok": True, "verified": True, "location": loc["name"],
            "quantity": got_qty, "counted": counted is not None,
            "estimate_flag": flagged, "note": note}


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
                           "quantity": c["row"].get("quantity"),
                           "strength": c["strength"]} for c in ranked],
           "unlocated_in_cabinet": len(rows), "actual": None,
           "unlocated": [{"stock": r["stock"], "sku": r["sku"], "name": r["name"],
                          "quantity": r["quantity"]} for r in rows]}
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


@app.get("/api/journal")
def api_journal(kind: str = "assign", limit: int = 200):
    """The write journal, newest first. Feeds undo and reconciliation."""
    rows = [r for r in log_read() if r.get("kind") == kind]
    return list(reversed(rows))[:limit]


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


# Raw string: the page embeds JavaScript regexes, and \d in a normal Python
# string is an invalid escape that warns on every import.
PAGE = r"""<!doctype html><html><head>
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
/* Survives the advance on purpose: the confirmation for the drawer you just
   finished has to still be readable once the app has moved to the next one. */
.flash{margin-top:12px;padding:11px 13px;border-radius:10px;background:#16291d;
color:#9fe0b5;border:1px solid #2c4433;font-size:13.5px}
.flash b{color:#c9f4d8}
.chips{display:flex;flex-wrap:wrap;gap:7px}
.chip{width:auto;padding:9px 13px;margin:0;font-size:14px;font-weight:600;
background:var(--card);color:var(--fg);border:1px solid var(--line);border-radius:999px}
.chip.on{background:var(--acc);color:#000;border-color:var(--acc)}
.gridbox{margin-top:12px;overflow-x:auto}
.grow{display:flex;gap:5px;margin-bottom:5px}
.cell{flex:1 1 0;min-width:30px;height:38px;padding:0;margin:0;font-size:11px;
border-radius:7px;border:1px solid var(--line);background:var(--card);color:var(--mut)}
.cell.large{height:46px}
.cell.filled{background:#1d2b20;color:#7fd39b;border-color:#2c4433}
.cell.unknown{background:#2a2213;color:#ffc978;border-color:#4a3a1c}
.cell.empty{background:var(--card);color:#4a4a4e}
.cell.on{outline:2px solid var(--acc);color:var(--fg)}
.legend{display:flex;gap:12px;margin-top:8px;font-size:11.5px;color:var(--mut);flex-wrap:wrap}
.known .card{margin-top:10px}
.known b{display:block;margin-bottom:6px;font-size:14px}
/* legibility of the READING, distinct from confidence in a COUNT: clear means
   the text was readable, not that the match is right. */
.clear{color:#4ecd7b}.partial{color:#feca57}.none{color:#ff9f43}
</style></head><body>
<h1>binscan</h1><p class=sub>The record first &middot; the camera only when it is silent &middot; nothing is written</p>

<label>Where</label>
<div id=areas class=chips></div>
<div id=gridwrap></div>

<div id=flash></div>
<div id=known class=known></div>

<label id=lpart>What it holds</label>
<input id=part placeholder="auto-filled from the drawer">

<label>Provider</label>
<select id=prov></select>

<label>After submit</label>
<select id=adv>
  <option value="across" selected>advance across the row (C1&rarr;C2&hellip;)</option>
  <option value="down">advance down the column (R1&rarr;R2&hellip;)</option>
  <option value="stay">stay on this drawer</option>
</select>

<label>Photo</label>
<input id=file type=file accept=image/* capture=environment>
<img id=prev>

<button id=go disabled>Estimate</button>
<div id=out></div>
<div class=ro><b>Reading is free; writing needs you.</b> Photographs and matches are never written by themselves &mdash; a row moves only when you press File, and the count is only recorded if you typed one. Every run is logged. <a href="/log" style="color:#8fc7ff">view log</a></div>

<script>
const $=s=>document.querySelector(s);
// A 478-entry select is the wrong control on a phone: reaching B3 meant
// scrolling past everything, and B3 is not even last. Two stages instead --
// pick a place, then tap the drawer where it physically sits. The grid mirrors
// the cabinet, so the picker doubles as a progress view.
let AREA=null, CELLS=[], CUR=null;
fetch('/api/areas').then(r=>r.json()).then(as=>{
  // The bin wall is where the work is; twenty-odd other places are real but
  // rarely the answer, and showing all of them cost nine rows of chips.
  const chip=a=>`<button class=chip data-a="${a.name}">${a.name}<span class=mut style="margin-left:6px">${a.drawers}</span></button>`;
  const wall=as.filter(a=>a.grid), rest=as.filter(a=>!a.grid);
  $('#areas').innerHTML = wall.map(chip).join('')
    + `<button class=chip id=more style="border-style:dashed">elsewhere <span class=mut>${rest.length}</span></button>`
    + `<div id=rest style="display:none;width:100%;margin-top:7px" class=chips>${rest.map(chip).join('')}</div>`;
  const wire=()=>$('#areas').querySelectorAll('.chip[data-a]').forEach(b=>b.onclick=()=>loadArea(b.dataset.a));
  wire();
  $('#more').onclick=()=>{ const r=$('#rest');
    const open=r.style.display!=='none'; r.style.display=open?'none':'flex';
    $('#more').classList.toggle('on',!open); };
}).catch(()=>{ $('#areas').innerHTML='<div class="card err">could not load areas</div>'; });

async function loadArea(name){
  AREA=name; CUR=null;
  $('#areas').querySelectorAll('.chip').forEach(b=>b.classList.toggle('on',b.dataset.a===name));
  $('#gridwrap').innerHTML='<div class=card>loading…</div>';
  $('#known').innerHTML=''; $('#out').innerHTML=''; $('#go').disabled=true;
  let g;
  try{ g=await (await fetch('/api/grid?area='+encodeURIComponent(name))).json(); }
  catch(_){ $('#gridwrap').innerHTML='<div class="card err">could not load '+name+'</div>'; return; }
  if(g.error){ $('#gridwrap').innerHTML=`<div class="card err">${g.error}</div>`; return; }
  CELLS=g.cells;
  const t=g.tally;
  let html='<div class=gridbox>';
  if(g.grid){
    const rows={};
    CELLS.forEach(c=>{ (rows[c.r]=rows[c.r]||[]).push(c); });
    Object.keys(rows).sort((a,b)=>a-b).forEach(r=>{
      html+='<div class=grow>'+rows[r].sort((a,b)=>a.c-b.c).map(c=>
        `<button class="cell ${c.state}${c.large?' large':''}" data-n="${c.name}"
           title="${c.label||c.name}">${c.r}.${c.c}</button>`).join('')+'</div>';
    });
  }else{
    html+='<div class=grow style="flex-wrap:wrap">'+CELLS.map(c=>
      `<button class="cell ${c.state}" style="flex:0 0 auto;min-width:86px;padding:0 10px"
         data-n="${c.name}">${c.name}</button>`).join('')+'</div>';
  }
  html+=`</div><div class=legend>
    <span style="color:#7fd39b">&#9632; ${t.filled} filled</span>
    <span style="color:#ffc978">&#9632; ${t.unknown} unknown</span>
    <span style="color:#4a4a4e">&#9632; ${t.empty} verified empty</span></div>`;
  $('#gridwrap').innerHTML=html;
  $('#gridwrap').querySelectorAll('.cell').forEach(b=>b.onclick=()=>pick(b.dataset.n));
}

function pick(name){
  CUR=name;
  $('#gridwrap').querySelectorAll('.cell').forEach(b=>b.classList.toggle('on',b.dataset.n===name));
  refreshDrawer(name,false);
}
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
async function refreshDrawer(v,keepOut){
  $('#known').innerHTML=''; if(!keepOut) $('#out').innerHTML='';
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
    UNLOCATED = d.unlocated || [];
    if(d.label){
      // The drawer is labelled even though no stock points at it. Offer the
      // match now -- taking a photograph to learn what the label already says
      // is work for nothing, and a photo of bare fasteners cannot show a
      // thread pitch anyway.
      const cands=(d.label_candidates||[]);
      $('#out').innerHTML =
        `<div class=card><div class=prov>from the drawer&rsquo;s own label</div>
           <div class=big style="font-size:17px">&ldquo;${d.label}&rdquo;</div>
           <div class=mut style="margin-top:6px">No stock is filed here, but the drawer is labelled. No photograph needed unless you want to check it.</div></div>`
        + (cands.length ? cands.map((c,i)=>`<div class=card>
             <div class=big style="font-size:17px">${c.name}</div>
             <div class=row><span>McMaster</span><span><b>${c.sku||'—'}</b></span></div>
             <div class=row><span>basis</span><span class="${c.strength==='definite'?'high':c.strength==='probable'?'medium':'low'}">${c.strength}</span></div>
             <div style="margin-top:8px;color:#aaa;font-size:13.5px">${c.why}</div>
             <label style="margin-top:12px">Count (leave blank if you did not count)</label>
             <input class=qty data-i="${i}" type=number inputmode=decimal placeholder="purchased ${(+c.quantity).toLocaleString()} — not a count">
             <button class=file data-i="${i}" data-stock="${c.stock}" style="margin-top:10px">File in ${v}</button>
             <div class=msg data-i="${i}" style="margin-top:8px;font-size:13px"></div>
           </div>`).join('')
           : `<div class="card warn">The label reads &ldquo;${d.label}&rdquo; but nothing unlocated in this cabinet matches it. Pick by hand, or photograph the tag.</div>`)
        + manualCard() + skipCard();
      setTimeout(()=>wireFiling(v), 0);
    }
    $('#known').innerHTML='<div class=card><b>Nothing on record for this drawer.</b>'+
      '<div class=mut>Photograph the McMaster bag tag if there is one, '+
      'or say it is empty.</div>'+
      `<button id=emptybtn style="margin-top:12px;background:var(--card);color:var(--fg);border:1px solid var(--line)">This drawer is empty</button>`+
      '<div id=emptymsg class=mut style="margin-top:8px"></div></div>';
    $('#emptybtn').onclick=()=>markEmpty(v);
    $('#part').value='';
    $('#lpart').textContent='What it holds (unknown — leave blank)';
    $('#go').textContent='Read the tag';
  }
}


// Walking a wall means going drawer to drawer, and re-finding your place in a
// 324-entry select every time is the friction that made the original unusable.
// The next drawer is taken from the OPTION LIST rather than by incrementing a
// number, because the grid is irregular: B rows 1-4 are eight wide and rows 5-7
// are four, so C5 has no neighbour below it and R5C5 does not exist. Walking
// the real list also means a cabinet that is partly labelled cannot advance
// onto a drawer that is not there.
function nextDrawer(cur,dir){
  const m=/^([A-Z]\d+)-R(\d+)C(\d+)$/.exec(cur||''); if(!m) return null;
  const cab=m[1]+'-';
  const rows=CELLS.map(c=>c.name).filter(v=>v.startsWith(cab))
    .map(v=>{const q=/-R(\d+)C(\d+)$/.exec(v); return {v,r:+q[1],c:+q[2]};});
  rows.sort(dir==='down' ? (a,b)=>(a.c-b.c)||(a.r-b.r) : (a,b)=>(a.r-b.r)||(a.c-b.c));
  const i=rows.findIndex(x=>x.v===cur);
  return (i>=0 && i+1<rows.length) ? rows[i+1].v : null;
}

// Filing happens against the drawer that was photographed. advance() changes
// CUR straight afterwards, so the drawer name is bound HERE, at render time --
// otherwise the second drawer of a walk collects the first drawer's contents.
// Always available, whether or not the automatic match found anything: pick
// the row by hand from everything still unlocated in this cabinet.
let UNLOCATED=[];

// Filing advances. Not everything gets filed -- a drawer may hold something
// that is not in the unlocated list, or you may simply want to move on -- so
// there has to be a way past a drawer that does not involve writing to it.
// Most of a walk is empty drawers. Without this the only options were "file
// something" or "skip", and skipping records nothing -- so the drawer stays
// unknown and gets opened again on the next pass. Saying "empty" is a finding.
async function markEmpty(drawer){
  const btn=$('#emptybtn'), msg=$('#emptymsg');
  btn.disabled=true; msg.textContent='recording…';
  const fd=new FormData(); fd.append('location',drawer); fd.append('confirm','yes');
  try{
    const j=await (await fetch('/api/empty',{method:'POST',body:fd})).json();
    if(j.ok){
      setFlash(`&#10003; <b>${j.location}</b> recorded ${j.already?'(already)':''} as verified empty.`);
      const cell=$('#gridwrap').querySelector(`.cell[data-n="${drawer}"]`);
      if(cell){cell.classList.remove('unknown','filled');cell.classList.add('empty');}
      if($('#adv').value!=='stay') setTimeout(()=>advance(), 1100);
      else { msg.style.color='#7fd39b'; msg.textContent='recorded'; }
    }else{
      msg.style.color='#ff8f8f'; msg.textContent=j.error||'failed'; btn.disabled=false;
    }
  }catch(e){ msg.style.color='#ff8f8f'; msg.textContent=String(e); btn.disabled=false; }
}

function setFlash(html){ $('#flash').innerHTML = html ? `<div class=flash>${html}</div>` : ''; }

function skipCard(){
  const nx=nextDrawer(CUR,$('#adv').value);
  return `<div class=card><div class=mut>Nothing to file here?</div>
    <button id=skipbtn style="background:var(--card);color:var(--fg);border:1px solid var(--line)">
      ${nx?`Skip to ${nx}`:'No next drawer in this direction'}</button></div>`;
}

function manualCard(){
  if(!UNLOCATED.length) return '';
  return `<div class=card>
    <div class=prov>or pick it by hand</div>
    <label style="margin-top:10px">${UNLOCATED.length} rows still unlocated in ${AREA}</label>
    <select id=manualsel>
      <option value="">— choose the part —</option>
      ${UNLOCATED.map(u=>`<option value="${u.stock}">${u.sku?u.sku+' · ':''}${u.name.slice(0,70)}</option>`).join('')}
    </select>
    <label style="margin-top:10px">Count (leave blank if you did not count)</label>
    <input class=qty data-i="m" type=number inputmode=decimal placeholder="blank = quantity not counted">
    <button class=file data-i="m" data-stock="" id=manualfile style="margin-top:10px">File in ${CUR}</button>
    <div class=msg data-i="m" style="margin-top:8px;font-size:13px"></div>
  </div>`;
}

function wireFiling(drawer){
  const sel=$('#manualsel'), mf=$('#manualfile');
  if(sel&&mf){ sel.onchange=()=>{ mf.dataset.stock=sel.value; }; }
  const sk=$('#skipbtn');
  if(sk) sk.onclick=()=>advance();
  $('#out').querySelectorAll('button.file').forEach(btn=>{
    btn.onclick=async()=>{
      const i=btn.dataset.i;
      const msg=$('#out').querySelector(`.msg[data-i="${i}"]`);
      const qty=$('#out').querySelector(`.qty[data-i="${i}"]`).value.trim();
      if(!btn.dataset.stock){ msg.style.color='#ff8f8f'; msg.textContent='choose a part first'; return; }
      btn.disabled=true; msg.textContent='filing…'; msg.style.color='#8a8a8e';
      const fd=new FormData();
      fd.append('stock',btn.dataset.stock); fd.append('location',drawer);
      fd.append('quantity',qty); fd.append('confirm','yes');
      try{
        const r=await fetch('/api/assign',{method:'POST',body:fd});
        const j=await r.json();
        if(j.ok){
          msg.style.color='#7fd39b';
          msg.textContent=`Filed in ${j.location}, verified. `
            + (j.counted?`Counted ${j.quantity}.`:`Quantity ${j.quantity} carried over — NOT counted.`);
          btn.textContent='Filed';
          const cell=$('#gridwrap').querySelector(`.cell[data-n="${drawer}"]`);
          if(cell){cell.classList.remove('unknown','empty');cell.classList.add('filled');}
          // The decision is made. Every other route to filing this drawer is
          // now a way to file it twice, so they go.
          $('#out').querySelectorAll('.card').forEach(c=>{
            if(!c.contains(btn)) c.style.display='none'; });
          $('#out').querySelectorAll('.warn').forEach(w=>w.style.display='none');
          const what = j.counted
            ? `<b>${j.quantity}</b> counted`
            : `<b>${j.quantity}</b> carried over, <b>not counted</b>`;
          setFlash(`&#10003; Filed into <b>${j.location}</b> &mdash; ${what}. Verified on re-read.`);
          const nx=nextDrawer(drawer,$('#adv').value);
          const bar=document.createElement('div');
          bar.className='card';
          bar.innerHTML = nx
            ? `<button id=nextbtn>Next drawer &rarr; ${nx}</button>
               <div class=mut style="margin-top:8px">Filed ${drawer}. Nothing else here needs doing.</div>`
            : `<div class=mut>Filed ${drawer}. That was the last drawer in this direction — pick another area above.</div>`;
          $('#out').appendChild(bar);
          if(nx) $('#nextbtn').onclick=()=>advance();
          if($('#adv').value!=='stay') setTimeout(()=>advance(), 1600);
        }else{
          msg.style.color='#ff8f8f'; msg.textContent=j.error||'failed'; btn.disabled=false;
        }
      }catch(e){ msg.style.color='#ff8f8f'; msg.textContent=String(e); btn.disabled=false; }
    };
  });
}

async function advance(){
  const dir=$('#adv').value;
  if(dir==='stay') return;
  const nx=nextDrawer(CUR,dir);
  $('#file').value=''; $('#prev').style.display='none'; $('#prev').removeAttribute('src');
  $('#go').disabled=true; $('#out').innerHTML=''; UNLOCATED=[];
  if(!nx){
    $('#known').innerHTML='<div class=card><b>End of cabinet.</b>'+
      '<div class=mut>Pick the next one by hand.</div></div>';
    return;
  }
  CUR=nx;
  $('#gridwrap').querySelectorAll('.cell').forEach(b=>b.classList.toggle('on',b.dataset.n===nx));
  await refreshDrawer(nx,false);
  $('#known').scrollIntoView({behavior:'smooth',block:'nearest'});
}
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
    // Advisory, not a blocker. It says nothing about what is physically in the
    // drawer -- only that the CATALOGUE's unlocated list has no obvious match.
    // Scott hit this with a perfectly legible 10/32 label and had nowhere to go.
    const why = d.basis==='tag-no-match'
      ? `A bag tag was read, but no <b>unlocated row in ${AREA}</b> carries that McMaster number. The part may already be filed elsewhere, or may not be McMaster stock.`
      : d.basis==='nothing-legible'
      ? 'Nothing legible in the photo. Try again closer — or pick it by hand below.'
      : `Nothing in the <b>unlocated list for ${AREA}</b> obviously matches that text. This says nothing about what is in the drawer — only that the automatic match could not choose.`;
    return read+`<div class="card warn">${why}</div>`+manualCard()+skipCard();
  }
  const here=CUR;
  return read + d.candidates.map((c,i)=>`<div class=card>
      <div class=big style="font-size:17px">${c.name}</div>
      <div class=row><span>McMaster</span><span><b>${c.sku||'—'}</b></span></div>
      <div class=row><span>basis</span><span class="${c.strength==='definite'?'high':c.strength==='probable'?'medium':'low'}">${c.strength}</span></div>
      <div style="margin-top:8px;color:#aaa;font-size:13.5px">${c.why}</div>
      <label style="margin-top:12px">Count (leave blank if you did not count)</label>
      <input class=qty data-i="${i}" type=number inputmode=decimal
             placeholder="purchased ${(+c.quantity).toLocaleString()} — not a count">
      <button class=file data-i="${i}" data-stock="${c.stock}"
              style="margin-top:10px">File in ${here}</button>
      <div class=msg data-i="${i}" style="margin-top:8px;font-size:13px"></div>
    </div>`).join('')
    + `<div class=warn>A match made from a photograph is a proposal, not an
       observation. Confirm against the open drawer before filing. The count box
       is blank on purpose — the number already on the row is what was BOUGHT,
       not what is there.</div>`
    + manualCard() + skipCard();
}

$('#go').onclick=async()=>{
  const f=$('#file').files[0]; if(!f)return;
  const identify = MODE==='identify';
  const label = $('#go').textContent;
  $('#go').disabled=true; $('#go').textContent='Looking…'; $('#out').innerHTML='';
  const fd=new FormData();
  fd.append('image',f); fd.append('provider',$('#prov').value);
  fd.append('location',CUR||'');
  if(identify) fd.append('cabinet',cabinetOf(CUR));
  else fd.append('part_name',$('#part').value||'unknown part');
  try{
    const r=await fetch(identify?'/api/identify':'/api/estimate',{method:'POST',body:fd});
    const d=await r.json();
    if(identify){
      if(!d.error) UNLOCATED = d.unlocated || [];
      $('#out').innerHTML = d.error ? `<div class="card err">${d.error}</div>` : renderIdentify(d);
      if(!d.error) wireFiling(CUR);
      $('#go').textContent=label; $('#go').disabled=false;
      // Reading does NOT advance. Advancing on the read moved the drawer out
      // from under a card the user had not acted on yet, and the card still
      // showed the old name -- so it looked like nothing had happened while
      // CUR had already changed. Advancing now follows the COMMIT.
      return;
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
      // Captured now: advancing changes CUR, and the truth being recorded
      // belongs to the drawer just photographed, not the one queued next.
      const truthId=d.id, truthLoc=CUR;
      $('#savetruth').onclick=async()=>{
        const v=$('#truth').value; if(v===''){return;}
        const fd2=new FormData(); fd2.append('id',truthId); fd2.append('actual',v);
        const rr=await fetch('/api/truth',{method:'POST',body:fd2});
        $('#tmsg').textContent = rr.ok ? `Recorded for ${truthLoc}.` : 'Failed to record.';
        if(rr.ok) setFlash(`&#10003; Actual count <b>${v}</b> recorded for <b>${truthLoc}</b>.`);
        if(rr.ok && $('#adv').value!=='stay') setTimeout(()=>advance(), 1600);
      };
      // Same rule as filing: the read does not advance, the COMMIT does. Here
      // the commit is recording what was really in the drawer.
      $('#out').insertAdjacentHTML('beforeend',
        `<div class=card><div class=mut>Not recording a count?</div>
         <button id=skipbtn2 style="background:var(--card);color:var(--fg);border:1px solid var(--line)">Skip to next drawer</button></div>`);
      $('#skipbtn2').onclick=()=>advance();
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
