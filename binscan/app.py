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

import collections
import datetime
import json
import math
import os
import pathlib
import re
import uuid

import httpx
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, Response

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


def _one(resp):
    """POST /api/stock/ returns a LIST, POST /api/part/ returns a dict. Calling
    .get() on the list threw AttributeError AFTER the part had been created, so
    the request 500'd having already written half of what it meant to -- the
    caller saw a failure and the catalogue kept the part."""
    if isinstance(resp, list):
        resp = resp[0] if resp else {}
    return resp if isinstance(resp, dict) else {}


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
        # A SITE ROOT is not a place you can stand. SLN and LRD qualified as
        # areas because a couple of leaves hang directly off them -- Receiving,
        # Triage, and at LRD an assortment kit filed at the top of the tree --
        # but nobody walks "LRD" from the Dover shop, and offering it as a
        # destination alongside B2 implies a parity that does not exist.
        if par.get("parent") is None:
            continue
        full = par.get("pathstring") or par["name"]
        out.append({"name": par["name"], "pk": pk, "drawers": len(leaves),
                    "grid": bool(DRAWER_RE.match(leaves[0]["name"] or "")),
                    # The site is carried explicitly so the header can say which
                    # one you are in. Everything is SLN today; the error worth
                    # pre-empting is filing an SLN part into an LRD drawer once
                    # Florida has drawers, and that is much easier to prevent
                    # before the ambiguity exists than after.
                    "site": full.split("/")[0],
                    "path": full.replace("SLN/", "")})
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

    filled, counted = set(), {}
    for r in _rows(it_get("stock/", location=loc["pk"], cascade=True, limit=1000)):
        kn = owner.get(r.get("location"))
        if kn:
            filled.add(kn)
            # A drawer counts as counted only if EVERY row in it has been.
            counted[kn] = counted.get(kn, True) and bool(_counted_from(r))

    cells = []
    for k in kids:
        m = DRAWER_RE.match(k["name"] or "")
        desc = k.get("description") or ""
        # DECLARED: the record here is finished and the absence of a count is
        # deliberate -- a pre-sort bucket, a consumable, a bin of prototypes.
        # Without it these fall through to "unknown", which the UI calls
        # "nobody has looked", and they stay amber forever: opening one shows
        # exactly what the description already said and changes nothing. Five
        # places were in that state on 2026-08-23, and a walk that keeps
        # offering settled places teaches people to ignore amber.
        #
        # The marker lives in the DESCRIPTION rather than in metadata because
        # the location serializer does not expose metadata and the dedicated
        # metadata endpoint answers 403 CSRF to a token client. Bracketed, so
        # it is stripped from the cell label by the same rule that hides the
        # size annotation -- machine-readable, invisible to the walker.
        declared = bool(_DECLARED_RE.search(desc))
        state = ("filled" if (k["name"] in filled and counted.get(k["name"]))
                 else "uncounted" if k["name"] in filled
                 else "empty" if desc.upper().startswith("VERIFIED EMPTY")
                 else "declared" if declared
                 else "mixed" if desc.upper().startswith("PRE-SORT")
                 else "unknown")
        cells.append({"name": k["name"], "pk": k["pk"], "state": state,
                      "r": int(m.group(2)) if m else None,
                      "c": int(m.group(3)) if m else None,
                      "large": "large" in desc.lower(),
                      "label": re.sub(r"\s*\[[^\]]*\]\s*", "", desc).strip()[:40]})
    # Grid areas sort by row and column. Everything else sorts by CREATION
    # ORDER, not alphabetically: LRD's bench wall came out LCab1..4 then
    # UCab1..4, with the uppers listed below the lowers they physically sit
    # above. Creation order is the order someone laid the place out, which is
    # closer to how it is walked than the alphabet is.
    cells.sort(key=lambda x: (x["r"] or 0, x["c"] or 0, x["pk"])
               if x["r"] else (0, 0, x["pk"]))
    tally = {s: sum(1 for c in cells if c["state"] == s)
             for s in ("filled", "uncounted", "mixed", "declared", "empty",
                       "unknown")}
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

# The one durable marker of "a human counted this", written into notes because
# every other field that could carry it is unwritable through the API.
COUNTED_RE = re.compile(r"binscan \d{4}-\d\d-\d\d: filed into \S+ and COUNTED at "
                        r"([\d.]+) by hand", re.I)


def _counted_from(row):
    """A stocktake date if InvenTree recorded one, else binscan's own marker."""
    st = row.get("stocktake_date")
    if st:
        return st
    m = COUNTED_RE.search(row.get("notes") or "")
    if not m:
        return None
    d = re.search(r"binscan (\d{4}-\d\d-\d\d)", row.get("notes") or "")
    return d.group(1) if d else "counted"


# A drawer's description carries at most ONE state stamp plus the original
# label. Without this, marking a mixed drawer empty produced
# "VERIFIED EMPTY ... previously labelled: PRE-SORT ... previously labelled:
# ..." -- each state wrapping the last, with the real label buried and the size
# annotation drifting to the end. Strip any prior stamp before writing a new
# one; "previously labelled" should mean the human label, not the app's own
# last opinion.
_DECLARED_RE = re.compile(r"\[DECLARED\]", re.I)

_STAMP = re.compile(r"^\s*(?:VERIFIED EMPTY|PRE-SORT)\s+\d{4}-\d\d-\d\d\s*"
                    r"(?:—|--)?\s*(?:mixed, not itemised)?\s*:?\s*"
                    r"(?:previously labelled:)?\s*", re.I)


def _strip_stamp(desc):
    d = (desc or "").strip()
    for _ in range(4):
        n = _STAMP.sub("", d).strip()
        if n == d:
            break
        d = n
    return d


# A description that NAMES CONTENTS is evidence the drawer is not empty. One
# that CLAIMS EMPTINESS is evidence of the opposite -- and the first version of
# this guard could not tell them apart, because it asked only whether there was
# any text at all.
#
# That blocked 31 of A3's 64 drawers on the 2026-08-23 walk. They carry bulk
# reports written 2026-08-21 -- "Reported AVAILABLE ... a cabinet-level
# statement, not a per-drawer check" and "Reported EMPTY ... a bulk statement
# covering A3-R4C1..R5C8" -- which are precisely the unverified claims a walk
# exists to turn into per-drawer facts. The guard refused the upgrade because
# somebody had written the claim down.
_EMPTY_CLAIM = re.compile(
    r"^(REPORTED\s+)?(AVAILABLE|EMPTY|VERIFIED\s+EMPTY|PRE-SORT)\b", re.I)


def _names_contents(body):
    """True when a description names what is IN the drawer.

    False for no description, and false for one that only claims the drawer is
    empty or available -- a person looking in and finding nothing contradicts
    nothing.
    """
    return bool(body) and not _EMPTY_CLAIM.match(body)


def _empty_description(desc, today):
    """The VERIFIED EMPTY stamp, keeping the bracketed size annotation.

    Two things the naive `stamp + " previously labelled: " + desc` got wrong.

    A superseded claim is not a previous label. "Reported AVAILABLE ... glance
    in before filling" is an instruction that a verified check has just
    answered; carrying it forward puts two statements of different strength
    side by side and tells the next reader to go and look again.

    And it overran. Those descriptions plus their bracketed size run past the
    250-character column, and the truncation falls on the END of the string --
    which is exactly where the size annotation lives. Preserving the claim
    would have silently eaten the dimensions off 31 drawers.
    """
    raw = desc or ""
    size = " ".join(re.findall(r"\[[^\]]*\]", raw))
    body = re.sub(r"\[[^\]]*\]", "", raw).strip(" ,;-—")
    out = f"VERIFIED EMPTY {today}"
    if _names_contents(body):
        out += f" — previously labelled: {body}"
    if size:
        out += f" {size}"
    return out[:250]


def clear_empty_stamp(loc):
    """Filing into a drawer RETIRES any 'verified empty' claim on it.

    B2-R4C8 was marked empty, then filed with hex nuts, and its Details tab went
    on saying VERIFIED EMPTY while its Stock Items tab listed the nuts. Scott
    caught it in the InvenTree app: two screens of the same record disagreeing,
    and the wrong one is the one a person reads first.

    Same rule as the notes: an action that resolves a state must retire the
    sentence describing it. The original label is kept -- that is a human's
    text, not the app's last opinion.
    """
    desc = (loc.get("description") or "").strip()
    if not desc.upper().startswith(("VERIFIED EMPTY", "PRE-SORT")):
        return None
    restored = _strip_stamp(desc)
    it_patch(f"stock/location/{loc['pk']}/", {"description": restored})
    again = it_get(f"stock/location/{loc['pk']}/") or {}
    return {"was": desc, "now": again.get("description")}


class Ambiguous(Exception):
    """More than one location answers to this name."""


def resolve_loc(name, site=""):
    """Exactly one location, or nothing, or a refusal.

    Location names are NOT unique in InvenTree -- `Receiving` already exists at
    both SLN and LRD -- and every lookup here took the first match. That is a
    silent write to the wrong site waiting for a duplicate name, and duplicates
    become likely the moment Florida is laid out: Scott's proposed upper
    cabinets are Cabinet 1..4, and SLN already has C1..C3 reserved for the row
    below B.

    A name that matches twice is not a location. Refuse, loudly, rather than
    pick one and be right half the time.
    """
    hits = [l for l in _rows(it_get("stock/location/", name=name, limit=20))
            if (l.get("name") or "").upper() == (name or "").upper()]
    if site:
        scoped = [l for l in hits
                  if (l.get("pathstring") or "").split("/")[0].upper() == site.upper()]
        if scoped:
            hits = scoped
    if not hits:
        return None
    if len(hits) > 1:
        where = ", ".join(l.get("pathstring") or l["name"] for l in hits[:4])
        raise Ambiguous(f"{len(hits)} locations are called {name!r} ({where}). "
                        f"Refusing to guess which one you meant.")
    return hits[0]


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

    # Rows with NO location at all are MORE unfiled than cabinet-level ones and
    # were invisible to this list entirely, so they could not be picked by hand.
    # Found 2026-08-22 when Scott had 1/4in washers in B2-R3C3 and six McMaster
    # washer rows sat locationless where nothing could reach them. A row nobody
    # can select is a row that gets entered twice.
    # `location__isnull=true` is SILENTLY IGNORED by this API -- it returns all
    # 560 stock rows, so the "homeless" list contained every row in the shop and
    # the picker showed 91251A585 twice, once from the cabinet and once from
    # here. Third silent filter failure on this install after `name=` on parts
    # and `stocktake_date` on stock. Filter in Python; the API's word that it
    # understood a parameter is worth nothing.
    all_stock = _rows(it_get("stock/", limit=2000))
    seen = {r.get("pk") for r in rows}
    nowhere = [r for r in all_stock
               if r.get("location") is None
               and r.get("pk") not in seen
               and skus.get(r.get("part"))]
    # Parts ALREADY filed in a drawer of this cabinet, offered so a second lot
    # of the same part can go in a second drawer. 91251A585 was purchased 50;
    # 4 were found in B2-R4C3 and counted, which set the row to 4 -- and the
    # other 46, sitting in another drawer, became invisible. A fastener bought
    # in one lot does not stay in one drawer.
    # Built from ALL stock, filtered here. `cascade=True` is the third or
    # fourth parameter this API has quietly ignored -- after location__isnull,
    # name= on parts, and stocktake_date -- and each time the symptom was an
    # empty or over-full result rather than an error. Fetch once, filter in
    # Python, stop asking whether this particular argument is honoured.
    drawer_pks = {}
    for l in _rows(it_get("stock/location/", limit=1000)):
        cur, hops = l, 0
        while cur is not None and cur.get("parent") is not None and hops < 12:
            if cur["parent"] == loc[0]["pk"]:
                drawer_pks[l["pk"]] = cur["name"]
                break
            cur = next((z for z in [None]), None) or None
            break
    # direct children only is enough: a second lot goes in a drawer, not a kit
    for l in _rows(it_get("stock/location/", parent=loc[0]["pk"], limit=200)):
        drawer_pks[l["pk"]] = l["name"]

    elsewhere = []
    for r in all_stock:
        lp = r.get("location")
        if lp in drawer_pks and skus.get(r.get("part")):
            r = dict(r)
            r["_at"] = drawer_pks[lp]
            elsewhere.append(r)

    out = []
    for r in rows + nowhere:
        pk = r.get("part")
        nm = ((r.get("part_detail") or {}).get("name")
              or r.get("part_name") or f"part {pk}")
        homeless = r.get("location") is None
        out.append({"stock": r.get("pk"), "part": pk,
                    "name": ("(NOT LOCATED ANYWHERE) " + nm) if homeless else nm,
                    "quantity": r.get("quantity"),
                    "homeless": homeless,
                    "sku": skus.get(pk, "")})
    for r in elsewhere:
        pk = r.get("part")
        out.append({"stock": r.get("pk"), "part": pk,
                    "name": ((r.get("part_detail") or {}).get("name")
                             or f"part {pk}"),
                    "quantity": r.get("quantity"),
                    "at": r.get("_at") or "",
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
# The inch mark sits between diameter and dash, and it is written three ways:
# McMaster prints 1/4"-20, an Everbilt retail box prints 3/8 in-16, and a
# handwritten label prints 3/8-16. The word form broke twice over -- the thread
# did not parse AND "3/8 in" was then read as a LENGTH of 0.375in, so a box of
# 3/8-16 hex nuts arrived at the matcher as a three-eighths-inch-long something.
_IMP_DASH = re.compile(r'(?<![\d/])#?\s*(\d+(?:/\d+)?)\s*'
                       r'(?:"|\u2033|\bin\b|\binch\b)?\s*-\s*(\d+)(?![\d/])',
                       re.I)
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
          ("dowel", "dowel"), ("standoff", "standoff"), ("header", "header"),
          # Present so a MISMATCH registers. A bearing scored no kind at all,
          # so "hex nuts" and "sleeve bearing" could not disagree -- the penalty
          # for a wrong type never fired because one side was blank.
          ("bearing", "bearing"), ("bushing", "bearing"), ("sleeve", "bearing"),
          ("spacer", "spacer"), ("o-ring", "oring"), ("clip", "clip"),
          ("rivet", "rivet"), ("anchor", "anchor"), ("pin", "pin"),
          ("terminal", "terminal"), ("connector", "connector"),
          ("threaded rod", "rod"), ("all-thread", "rod"), ("stud", "rod"),
          ("rod", "rod"), ("shim", "shim"), ("key", "key"), ("retaining", "clip"),
          ("grommet", "grommet"), ("insert", "insert"), ("bearing", "bearing"))


_KIND_RE = [(re.compile(r"\b" + re.escape(w) + r"s?\b"), tag) for w, tag in _KINDS]


def _kinds(t):
    """WORD boundaries, not substrings, and this is not fussiness.

    A Home Depot hex-nut label carries "THIS PRODUCT IS APPROVED FOR USE WITH
    A.C.Q. WOOD PRODUCTS", and "rod" is inside "product". So the label was
    tagged BOTH nut and rod, the kind sets intersected on rod, and a box of hex
    nuts scored +3 for AGREEING with a threaded rod. The wrong-type penalty had
    been fixed twice by then and was firing correctly -- it was simply
    outvoted by a match manufactured out of boilerplate.

    The trailing `s?` keeps plurals working: the label says HEX NUTS and the
    catalogue says Hex Nut.
    """
    tl = (t or "").lower()
    return {tag for rx, tag in _KIND_RE if rx.search(tl)}


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

    # DESCRIPTORS ARE NOT MATCHED ON. The prompt calls them "the one place you
    # may say what you see rather than read... treated as a weak hint, never as
    # proof", and then this function weighted them exactly like read text.
    #
    # A photograph of a box of Everbilt hex nuts produced descriptors reading
    # "cardboard box with orange and black retail label containing stainless hex
    # nuts in plastic packaging" -- accurate prose, no part number -- and the
    # matcher scored it against a nylon sleeve bearing and offered that. Prose
    # about packaging cannot identify a fastener, and letting it try turns a
    # correct reading into a confident wrong answer.
    text = " ".join(list(reading.get("labels") or [])
                    + list(reading.get("markings") or []))
    if not text.strip():
        return [], "nothing-legible"
    lm, li, lmm, lin = _facts(text)
    lk = _kinds(text)
    # No thread, no match. Length and finish and even the fastener TYPE are
    # shared by dozens of rows; the thread is the only attribute that narrows to
    # something worth proposing. Without one there is nothing to be confident
    # about, and "no candidate" is an answer the UI handles well -- it offers
    # the filter and the create path.
    if not (lm or li):
        return [], "no-thread-read"
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
        elif lk and not pk:
            # THE LABEL NAMED A TYPE AND THE ROW'S TYPE IS UNKNOWN. Penalise,
            # do not ignore.
            #
            # This is the general form of a bug hit twice: a nylon sleeve
            # bearing and then a threaded rod were both proposed for a box of
            # hex nuts, because neither word was in the vocabulary, so one side
            # of the comparison came back empty and "cannot tell" scored the
            # same as "agrees". Adding the missing word each time fixes one case
            # and leaves the next one waiting.
            #
            # An unrecognised type cannot CORROBORATE a named one. Thread and
            # finish alone are not enough -- a 3/8-16 stainless nut and a 3/8-16
            # stainless rod agree on both and are not remotely the same thing.
            sc -= 4
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


_STOP = {"the", "and", "for", "with", "from", "this", "that", "your", "not",
         "all", "new", "pcs", "pack", "set", "kit", "x1", "inc", "ltd", "co",
         "made", "china", "ce", "rohs", "compliant", "manufacturer", "works",
         "smart", "module", "type", "model", "max", "min", "dc", "ac", "v",
         "mm", "cm", "in", "of", "to", "by", "or", "a", "an"}


def _tokens(text):
    """Distinctive lowercase tokens: what two descriptions of one object share.

    Alphanumeric runs only. A first version allowed `.` and `/` inside a token
    so that "u.fl" survived -- and it turned "U.FL/IPEX" into the single token
    `u.fl/ipex`, which matches nothing a human would type. Splitting hard and
    letting "fl" and "ipex" stand alone is worth more than keeping "u.fl"
    whole.
    """
    return {t for t in re.findall(r"[a-z0-9]+", (text or "").lower())
            if len(t) >= 2 and t not in _STOP}


def _catalogue_index():
    """Every part, tokenised, with an IDF weight per token.

    The whole catalogue is under a thousand rows, so scoring locally beats
    guessing search queries -- which is how the first version failed. It built
    queries from whole label lines and from the LONGEST tokens on the bag, and
    on an antenna pigtail those were `cn1083961339vudae` and `9375669B5015`:
    the order id and the batch code, the two least useful strings present. It
    never searched for "pigtail" or "sma" at all.

    IDF is what makes the ranking mean anything. "cable" appears on dozens of
    parts and says almost nothing; "pigtail" appears on one and says
    everything. Weighting by rarity separates them without a hand-tuned list.
    """
    rows = _rows(it_get("part/", limit=2000))
    docs = []
    df = collections.Counter()
    for r in rows:
        toks = _tokens(f"{r.get('name') or ''} {r.get('description') or ''}")
        if toks:
            docs.append((r, toks))
            df.update(toks)
    n = len(docs) or 1
    idf = {t: math.log(n / (1 + c)) + 0.25 for t, c in df.items()}
    return docs, idf


def catalogue_matches(reading, limit=6):
    """Parts whose NAME matches the label text, searched across the CATALOGUE.

    `match_reading()` is a fastener matcher: it scores a reading against the
    cabinet's unlocated McMaster rows using SKU, thread and length. A retail
    box has no thread, so it bails with `no-thread-read` and proposes nothing.

    Scott photographed a Shelly Plus 2PM on 2026-08-23. The read was perfect --
    brand, model, ratings, terminal legend, EAN, manufacturer address -- and the
    answer was `candidates: []`. The part existed as #79 the whole time. It did
    not fail to find it; it never looked.

    `/api/fasteners` already carried the right instinct in its own docstring:
    *the whole catalogue, not just the cabinet's unlocated rows, because a part
    you are holding may well exist already and creating a second one is the
    outcome worth preventing.* This gives identify the same reach.

    Scores by shared distinctive tokens rather than by asking a model to
    choose. A model asked to pick from a list always picks; token overlap can
    come back empty, and empty is a real answer.
    """
    r = reading or {}
    text = " ".join(filter(None, [
        r.get("tag") or "",
        " ".join(r.get("labels") or []),
        " ".join(r.get("markings") or []),
        r.get("descriptors") or "",
    ]))
    return catalogue_search(text, limit=limit)


def catalogue_search(text, limit=6, floor=0.9):
    """Rank the catalogue against free text -- a label read, or something typed.

    Shared by identify and by the by-hand picker, because they are the same
    question asked twice: *which part is this?* The picker used to filter only
    the cabinet's unlocated rows, so typing "sma" while holding an SMA pigtail
    returned nothing while the part sat in the catalogue at #732.

    `floor` keeps a single common word from proposing half the shop. Below it
    the honest answer is nothing.
    """
    want = _tokens(text)
    if not want:
        return []
    docs, idf = _catalogue_index()

    scored = []
    for row, have in docs:
        shared = want & have
        if not shared:
            continue
        # Sum the RARITY of what matched, then damp by how many words the part
        # had to offer: a long name that shares three tokens had more chances
        # than a short one that shares three.
        score = sum(idf.get(t, 0.25) for t in shared) / (len(have) ** 0.5 or 1)
        if score < floor:
            continue
        best = sorted(shared, key=lambda t: -idf.get(t, 0))[:6]
        scored.append((score, best, row))

    scored.sort(key=lambda s: -s[0])
    out = []
    for score, shared, row in scored[:limit]:
        pk = row["pk"]
        rows = _rows(it_get("stock/", part=pk, limit=20))
        out.append({
            "part": pk,
            "name": row.get("name") or "",
            "description": (row.get("description") or "")[:160],
            "score": round(score, 3),
            "shared": shared,
            "stock_rows": len(rows),
            "where": [{"stock": s.get("pk"), "quantity": s.get("quantity"),
                       "location": (s.get("location_detail") or {}).get("name")}
                      for s in rows],
            "why": ("matches on " + ", ".join(shared)) if shared else "",
        })
    return out


def part_docs(part_pk):
    """Attachments belonging to a PART, for showing on a STOCK screen.

    Scott, 2026-08-23: *"you're gonna go in through stock ninety nine percent
    of the time because you wanna know if you have it. So having to go in
    through parts doesn't really help you."*

    Right, and it is worse than an inconvenience: InvenTree keys attachments by
    model, so a stock screen shows an EMPTY attachment list. Not "see the
    part" -- nothing. A datasheet that exists is indistinguishable from one
    that does not, at the bench, holding the component.

    The document still belongs to the part. What was missing was any sign of it
    where people actually look.
    """
    out = []
    for a in _rows(it_get("attachment/", model_type="part", model_id=part_pk,
                          limit=20)):
        name = (a.get("attachment") or a.get("link") or "").rstrip("/").split("/")[-1]
        out.append({"pk": a.get("pk"), "name": name or "document",
                    "comment": (a.get("comment") or "")[:90]})
    return out


@app.get("/api/doc/{pk}")
def api_doc(pk: int):
    """Stream an InvenTree attachment through binscan.

    InvenTree serves /media/ behind authentication -- a direct link answers 401
    on a phone that has no InvenTree session, which is most phones at a drawer.
    binscan already holds a token, so it fetches the file server-side and hands
    it over. The walker taps once and the PDF opens.

    Read-only, and by attachment pk rather than by path: a path parameter that
    reaches the filesystem is how a file server becomes an exfiltration tool.
    """
    meta = _one(it_get(f"attachment/{pk}/"))
    if not meta:
        return JSONResponse({"error": f"no attachment {pk}"}, 404)
    url = meta.get("attachment") or meta.get("link") or ""
    if not url:
        return JSONResponse({"error": "attachment has no file"}, 404)
    if url.startswith("/"):
        url = INVENTREE + url
    try:
        r = httpx.get(url, headers={"Authorization": f"Token {IT_TOKEN}"},
                      timeout=30, follow_redirects=True)
        r.raise_for_status()
    except Exception as e:
        return JSONResponse({"error": f"could not fetch: {e}"}, 502)
    fname = url.rstrip("/").split("/")[-1] or "document"
    return Response(content=r.content,
                    media_type=r.headers.get("content-type",
                                             "application/octet-stream"),
                    headers={"Content-Disposition":
                             f'inline; filename="{fname}"'})


def drawer_contents(name, site=""):
    """What the DATABASE already says is in this drawer. Checked before any
    model is called: asking vision what the record already knows introduces
    error where there was none, and costs an API call to do it. Scott,
    2026-08-22: look to see if the bin has something assigned already before
    you have AI go look for it.

    Counts stock in the drawer OR ANY DESCENDANT, because an assortment kit is
    a child location -- a drawer holding one reads as empty at drawer level and
    that mistake has already been made once today, against B3."""
    try:
        loc = resolve_loc(name, site)
    except Ambiguous as e:
        return {"error": str(e)}
    if loc is None:
        return None
    out = {"location": loc.get("pk"), "name": loc.get("name"),
           "description": loc.get("description") or "", "stock": [], "homes": []}
    for r in _rows(it_get("stock/", location=loc["pk"], cascade=True, limit=100)):
        # Counted or merely carried? A filed row shows a bare number either way,
        # and the two have opposite reliability. Scott, mid-walk 2026-08-22:
        # "it doesn't tell you anywhere that that's an estimate... it looks the
        # same as one point one, which has in fact been counted."
        st = _counted_from(r)
        out["stock"].append({
            # The STOCK ROW's own pk. Its absence is why the recount button
            # posted stock=None and got a 422: the panel had everything needed
            # to display a row and nothing needed to act on one.
            "stock": r.get("pk"),
            "part": r.get("part"),
            "name": (r.get("part_detail") or {}).get("name") or f"part {r.get('part')}",
            "quantity": r.get("quantity"),
            "counted": bool(st),
            "docs": part_docs(r.get("part")),
            "stocktake_date": st,
            "estimate": (r.get("notes") or "").startswith("[ESTIMATE]"),
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
        m = DRAWER_RE.match(name or "")
        cab = m.group(1) if m else ""
        rows = cabinet_unlocated(cab) if cab else []
        # ALWAYS returned for an unassigned drawer, labelled or not. It was
        # returned only alongside a label match, so an unlabelled drawer got an
        # empty list and the pick-by-hand card suppressed itself -- which meant
        # a person standing at an open drawer, who could see exactly what was in
        # it, had to photograph it first to unlock a filter box.
        out["unlocated"] = [{"stock": r["stock"], "sku": r["sku"],
                             "name": r["name"], "quantity": r["quantity"]}
                            for r in rows]
        body = re.sub(r"\[[^\]]*\]", "", out["description"]).strip(" ,;-\u2014")
        if body and not body.upper().startswith(("VERIFIED EMPTY", "PRE-SORT")):
            ranked, basis = match_reading({"tag": "", "labels": [body],
                                           "markings": [], "descriptors": ""}, rows)
            out["label"] = body
            out["label_basis"] = basis
            out["label_candidates"] = [
                {"sku": c["row"]["sku"], "name": c["row"]["name"],
                 "stock": c["row"]["stock"], "quantity": c["row"].get("quantity"),
                 "why": c["why"], "strength": c["strength"]} for c in ranked]
    return out


@app.get("/api/drawer")
def api_drawer(name: str = "", site: str = ""):
    """Free, instant, no model. The UI calls this the moment a drawer is picked
    and only offers the camera when this comes back unassigned."""
    if not name:
        return JSONResponse({"error": "name required"}, status_code=400)
    d = drawer_contents(name, site)
    if isinstance(d, dict) and d.get("error"):
        return JSONResponse(d, status_code=409)
    if d is None:
        return JSONResponse({"error": f"no location named {name}"}, status_code=404)
    return d


@app.post("/api/mixed")
def api_mixed(location: str = Form(...), note: str = Form(""),
              site: str = Form(""), confirm: str = Form("")):
    """Record a drawer as a mixed jumble: LOOKED AT, deliberately not itemised.

    Some drawers hold oddments -- a handful of hex bolts in three lengths, a few
    socket heads, leftovers from jobs. Itemising those means creating a part per
    fastener for things nobody stocks, and skipping records nothing, so the
    drawer stays amber and gets opened again on the next pass.

    'Mixed' is a finding. It says a person looked, and the contents are not
    worth a row each yet.

    Uses the PRE-SORT prefix the catalogue already reserves -- the four buckets
    at A2-R8C5..C8 -- so mark_empty.py's existing guard leaves it alone and it
    reads the same as every other queue in the shop.
    """
    if not WRITES_ON:
        return JSONResponse({"error": "writes disabled (BINSCAN_WRITES != 1)"}, 403)
    if confirm.lower() not in ("1", "true", "yes"):
        return JSONResponse({"error": "confirm required"}, 400)

    try:
        loc = resolve_loc(location, site)
    except Ambiguous as e:
        return JSONResponse({"error": str(e)}, 409)
    if loc is None:
        return JSONResponse({"error": f"no location named {location}"}, 404)

    known = drawer_contents(location, site) or {}
    if known.get("stock"):
        return JSONResponse({"error": "this drawer has stock filed in it; a mixed "
                                      "bucket holds only unitemised oddments"}, 409)

    desc = _strip_stamp(loc.get("description"))
    size = re.search(r"\[[^\]]*\]", desc)
    tag = f"PRE-SORT {datetime.date.today().isoformat()} — mixed, not itemised"
    if note.strip():
        tag += f": {note.strip()[:120]}"
    new = (tag + (" " + size.group(0) if size else ""))[:250]
    _b, err = it_patch(f"stock/location/{loc['pk']}/", {"description": new})
    if err:
        return JSONResponse({"error": f"could not write: {err}"}, 502)
    again = it_get(f"stock/location/{loc['pk']}/") or {}
    if not (again.get("description") or "").upper().startswith("PRE-SORT"):
        return JSONResponse({"error": "write did not verify on re-read"}, 500)

    log_append({"id": uuid.uuid4().hex[:8], "kind": "mixed",
                "at": datetime.datetime.now().isoformat(timespec="seconds"),
                "location": loc["name"], "before": {"description": desc},
                "after": {"description": again.get("description")}})
    return {"ok": True, "location": loc["name"], "description": again.get("description")}


_FINISH = [
    ("black-oxide", ("black-oxide", "black oxide", "blackox")),
    ("18-8 stainless", ("18-8", "18/8", "passivated 18-8")),
    ("316 stainless", ("316 stainless",)),
    ("stainless", ("stainless",)),
    ("galvanized", ("galvanized", "galvanised")),
    ("zinc-plated", ("zinc-plated", "zinc plated", "zinc")),
    ("brass", ("brass",)),
    ("nylon", ("nylon plastic", "nylon washer")),
    ("plain steel", ("plain steel", "low-strength steel", "carbon steel")),
]
_HEAD = [
    ("socket head", ("socket head",)), ("low-profile socket", ("low-profile",)),
    ("button head", ("button head",)), ("flat head", ("flat head",)),
    ("pan head", ("pan head",)), ("fillister", ("fillister",)),
    ("hex head", ("hex head", "hex bolt", "hex cap")),
    ("set screw", ("set screw", "cup-point")),
    ("nyloc nut", ("nylon-insert", "nyloc", "locknut", "lock nut")),
    ("cap nut", ("cap nut",)), ("hex nut", ("hex nut",)), ("nut", ("nut,", " nut")),
    ("flat washer", ("flat washer", "general purpose steel washer")),
    ("fender washer", ("fender washer",)),
    ("lock washer", ("lock washer", "spring lock")),
    ("washer", ("washer",)),
    ("threaded rod", ("threaded rod",)), ("dowel pin", ("dowel",)),
    ("spring pin", ("slotted spring", "spring pin")),
    ("machine key", ("machine key",)), ("standoff", ("standoff",)),
]


def _first(text, table):
    t = (text or "").lower()
    for label, needles in table:
        if any(n in t for n in needles):
            return label
    return ""


@app.get("/api/fasteners")
def api_fasteners():
    """Every catalogued fastener, broken into attributes, for faceted search.

    Scott asked for a McMaster-style funnel: narrow by attribute and watch the
    count fall. That is a FINDER first and a creator second -- when the facets
    bottom out at zero, absence is proven by construction rather than by having
    scrolled far enough, which is the failure he described standing at B2-R4C1.

    The whole catalogue, not just the cabinet's unlocated rows: a part you are
    holding may well exist already and be filed in another drawer, and creating
    a second one is the outcome worth preventing.
    """
    skus = _mcmaster_skus()
    out = []
    for r in _rows(it_get("part/", limit=2000)):
        name = r.get("name") or ""
        head = _first(name, _HEAD)
        if not head:
            continue
        metric, imp, mm, inch = _facts(name)
        thread = metric.upper() if metric else (imp or "")
        length = (f"{mm:g}mm" if mm is not None
                  else f"{inch:g}in" if inch is not None else "")
        out.append({"pk": r.get("pk"), "name": name,
                    "sku": skus.get(r.get("pk"), ""),
                    "head": head, "thread": thread,
                    "system": "metric" if metric else ("imperial" if imp else ""),
                    "length": length,
                    "finish": _first(name, _FINISH)})
    return out


@app.post("/api/newpart")
def api_newpart(name: str = Form(...), location: str = Form(...),
                quantity: str = Form(""), notes: str = Form(""),
                site: str = Form(""), confirm: str = Form("")):
    """Create a part that is not in the catalogue, from the drawer, on the walk.

    Two drawers in B2 alone held things that had never been entered -- 1/4in
    stainless washers and 5/16-18 lock nuts -- and the walk had nowhere to put
    them. Skipping records nothing, so the drawer stays unknown and the parts
    stay invisible; filing the wrong row would be worse.

    Guarded, because a create path on a phone is how a catalogue fills with
    near-duplicates. Two importers have already entered the same item twice
    under different names.
    """
    if not WRITES_ON:
        return JSONResponse({"error": "writes disabled (BINSCAN_WRITES != 1)"}, 403)
    if confirm.lower() not in ("1", "true", "yes"):
        return JSONResponse({"error": "confirm required"}, 400)

    name = " ".join((name or "").split())
    if len(name) < 8:
        return JSONResponse({"error": "give it a real name - at least 8 characters, "
                                      "in the house style, e.g. "
                                      "'Nyloc Nut 5/16-18, zinc-plated steel'"}, 400)

    # `name=` is NOT an exact-match filter on this API -- it is ignored, so the
    # first version of this check returned nothing and passed every time. It
    # created a second "Flat Washer 1/4in ID x 5/8in OD, 18-8 stainless" during
    # its own guard test. `search=` works. A guard that cannot fail is not a
    # guard, and this repo already has two importers that entered the same item
    # twice under different names.
    def _norm(t):
        return re.sub(r"[^a-z0-9]", "", (t or "").lower())
    want = _norm(name)
    for r in _rows(it_get("part/", search=name[:60], limit=50)):
        if _norm(r.get("name")) == want:
            return JSONResponse({"error": f"part #{r.get('pk')} is already called "
                                          f"'{r.get('name')}'"}, 409)

    try:
        loc = resolve_loc(location, site)
    except Ambiguous as e:
        return JSONResponse({"error": str(e)}, 409)
    if loc is None:
        return JSONResponse({"error": f"no location named {location}"}, 404)

    counted = None
    if str(quantity).strip():
        try:
            counted = float(quantity)
        except ValueError:
            return JSONResponse({"error": f"quantity {quantity!r} is not a number"}, 400)
        if counted < 0:
            return JSONResponse({"error": "quantity cannot be negative"}, 400)

    # Category from a sibling rather than hard-coded: the tree is the shop's,
    # not this app's, and guessing an id would break the day it is reorganised.
    cat = None
    for probe in (name.split()[0], "Washer", "Nut", "Screw"):
        sib = _rows(it_get("part/", search=probe, limit=5))
        cat = next((r.get("category") for r in sib if r.get("category")), None)
        if cat:
            break

    stamp = datetime.date.today().isoformat()
    body = (f"Created on the walk with binscan, {stamp}, at {loc['name']}. "
            f"**Not from any recorded purchase** - it matched nothing in the "
            f"catalogue, so it will never reconcile against a purchase order and "
            f"the purchased-vs-counted report has nothing to say about it.\n\n"
            + (notes.strip() + "\n\n" if notes.strip() else "")
            + ("Quantity COUNTED by hand at the drawer."
               if counted is not None else
               "[ESTIMATE] No quantity recorded - nobody counted it."))

    payload = {"name": name, "description": name[:250], "active": True,
               "purchaseable": True, "component": True,
               "default_location": loc["pk"], "notes": body}
    if cat:
        payload["category"] = cat
    part, err = it_post("part/", payload)
    part = _one(part)
    if err or not part.get("pk"):
        return JSONResponse({"error": f"could not create the part: {err}"}, 502)

    stock = None
    if counted is not None:
        stock, err = it_post("stock/", {"part": part["pk"], "location": loc["pk"],
                                        "quantity": counted,
                                        "notes": f"binscan {stamp}: filed into "
                                                 f"{loc['name']} and COUNTED at "
                                                 f"{counted:g} by hand."})
        stock = _one(stock)
        if err or not stock.get("pk"):
            return JSONResponse({"error": f"part created (#{part['pk']}) but the "
                                          f"stock row failed: {err}",
                                 "part": part["pk"]}, 502)

    again = it_get(f"part/{part['pk']}/") or {}
    if again.get("default_location") != loc["pk"]:
        return JSONResponse({"error": "part created but its home did not verify",
                             "part": part["pk"]}, 500)

    clear_empty_stamp(loc)
    log_append({"id": uuid.uuid4().hex[:8], "kind": "newpart",
                "at": datetime.datetime.now().isoformat(timespec="seconds"),
                "part": part["pk"], "name": name, "location": loc["name"],
                "stock": (stock or {}).get("pk"), "quantity": counted,
                "counted": counted is not None})
    return {"ok": True, "part": part["pk"], "name": name,
            "location": loc["name"], "quantity": counted,
            "counted": counted is not None, "category": cat}


@app.post("/api/empty")
def api_empty(location: str = Form(...), site: str = Form(""),
              confirm: str = Form("")):
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

    try:
        loc = resolve_loc(location, site)
    except Ambiguous as e:
        return JSONResponse({"error": str(e)}, 409)
    if loc is None:
        return JSONResponse({"error": f"no location named {location}"}, 404)

    known = drawer_contents(location, site) or {}
    if known.get("stock"):
        what = known["stock"][0]["name"][:44]
        return JSONResponse({"error": f"not empty - it holds {what}"}, 409)
    if known.get("homes"):
        who = known["homes"][0]["name"][:44]
        return JSONResponse({"error": f"this is a PARKING SPOT, the home of "
                                      f"'{who}'. It has no stock by design; that "
                                      f"is not the same as empty."}, 409)

    desc = _strip_stamp(loc.get("description"))
    body = re.sub(r"\[[^\]]*\]", "", desc).strip(" ,;-\u2014")
    if (loc.get("description") or "").upper().startswith("VERIFIED EMPTY"):
        return {"ok": True, "already": True, "description": desc,
                "note": "already recorded empty; nothing changed"}
    if _names_contents(body):
        return JSONResponse({"error": f"the drawer's own description names "
                                      f"something: \u201c{body[:80]}\u201d. Check by "
                                      f"eye - a description is often the only "
                                      f"place the contents were written down."}, 409)

    new = _empty_description(desc, datetime.date.today().isoformat())
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
               quantity: str = Form(""), split: str = Form(""),
               site: str = Form(""), confirm: str = Form("")):
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

    try:
        loc = resolve_loc(location, site)
    except Ambiguous as e:
        return JSONResponse({"error": str(e)}, 409)
    if loc is None:
        return JSONResponse({"error": f"no location named {location}"}, 404)

    before = it_get(f"stock/{stock}/")
    if not before:
        return JSONResponse({"error": f"no stock item {stock}"}, 404)

    # SPLIT: the part is already filed in another drawer and some of it is here
    # too. Create a SECOND row rather than moving the first, because moving it
    # would empty a drawer that is not empty.
    if split.lower() in ("1", "true", "yes"):
        if not str(quantity).strip():
            return JSONResponse({"error": "a second lot needs a count - without "
                                          "one there is no way to say how much "
                                          "is in THIS drawer"}, 400)
        try:
            n = float(quantity)
        except ValueError:
            return JSONResponse({"error": f"quantity {quantity!r} is not a number"}, 400)
        if n <= 0:
            return JSONResponse({"error": "a second lot must be more than zero"}, 400)
        stamp2 = datetime.date.today().isoformat()
        body, err = it_post("stock/", {
            "part": before.get("part"), "location": loc["pk"], "quantity": n,
            "notes": (f"binscan {stamp2}: filed into {loc['name']} and COUNTED at "
                      f"{n:g} by hand. SECOND LOT — the same part is also filed "
                      f"in another drawer; this row is what is HERE, not the "
                      f"total. Sum the rows for the shop total.")})
        body = _one(body)
        if err or not body.get("pk"):
            return JSONResponse({"error": f"could not create the second lot: {err}"}, 502)
        chk = it_get(f"stock/{body['pk']}/") or {}
        if chk.get("location") != loc["pk"] or abs(float(chk.get("quantity", -1)) - n) > 1e-6:
            return JSONResponse({"error": "second lot did not verify on re-read"}, 500)
        clear_empty_stamp(loc)
        log_append({"id": uuid.uuid4().hex[:8], "kind": "split",
                    "at": datetime.datetime.now().isoformat(timespec="seconds"),
                    "from_stock": stock, "new_stock": body["pk"],
                    "part": before.get("part"), "location": loc["name"],
                    "quantity": n, "counted": True})
        return {"ok": True, "verified": True, "split": True,
                "location": loc["name"], "quantity": n, "counted": True,
                "note": "second lot created; the other drawer is untouched"}

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
    # Counted-ness is recorded in METADATA, not in stocktake_date, and this is
    # forced rather than chosen.
    #
    # stocktake_date is READ-ONLY on the stock API: a PATCH setting it returns
    # HTTP 200 and changes nothing -- a write reporting success while doing
    # nothing, which is the failure mode this install is already known for.
    # The only route that sets it is stock/count/, and that is a NO-OP when the
    # counted figure equals the stored one. So B2-R3C8, where Scott counted 50
    # against a purchased 50, ended up with notes saying COUNTED and no
    # stocktake date, and the grid called it uncounted.
    #
    # A count that CONFIRMS the existing number is still a count, and arguably
    # the most valuable one -- it is the only thing that turns a purchased
    # figure into a verified one. Recording it must not depend on the number
    # having changed.
    #
    # scripts/sync_stocktake.py copies these into the real stocktake_date via
    # the ORM, which is not bound by the serializer, so InvenTree's own
    # never-counted reports stay correct.
    # NOTES ARE THE ONLY WRITABLE CHANNEL, and that is measured, not assumed:
    #   stocktake_date   read_only on the serializer. PATCH returns 200 and
    #                    changes nothing.
    #   metadata         same -- 200, ignored. The dedicated
    #                    /stock/<pk>/metadata/ endpoint returns 403 CSRF.
    #   stock/count/     sets stocktake_date, but is a NO-OP when the counted
    #                    figure equals the stored one.
    # So B2-R3C8, counted at 50 against a purchased 50, could not record that it
    # had been counted at all. Two writes returned success and did nothing,
    # which is this install's signature failure.
    #
    # The marker below is therefore the authoritative record of a count, and
    # COUNTED_RE is what reads it back. scripts/sync_stocktake.py mirrors it
    # into the real stocktake_date through the ORM, which the serializer does
    # not gate, so InvenTree's own never-counted reports stay right.
    patch = {"notes": body_notes}
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
    got_st = _counted_from(after)
    ok_st = bool(got_st) == (counted is not None)
    if not (ok_loc and ok_qty and ok_st):
        return JSONResponse({"error": "write did not verify on re-read",
                             "wanted_location": loc["pk"], "got_location": got_loc,
                             "wanted_quantity": counted, "got_quantity": got_qty,
                             "wanted_stocktake": bool(counted is not None),
                             "got_stocktake": got_st}, 500)

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
    cleared = clear_empty_stamp(loc)
    flagged = (after.get("notes") or "").startswith("[ESTIMATE]")
    if (counted is None) != flagged:
        return JSONResponse({"error": "the [ESTIMATE] flag did not land as intended",
                             "counted": counted is not None, "flagged": flagged}, 500)
    return {"ok": True, "verified": True, "location": loc["name"],
            "quantity": got_qty, "counted": counted is not None,
            "estimate_flag": flagged, "cleared_empty": cleared, "note": note}


@app.get("/api/partsearch")
def api_partsearch(q: str = "", limit: int = 8):
    """Search the CATALOGUE by text, for the by-hand picker.

    The picker filtered `UNLOCATED` -- the cabinet's rows waiting to be filed --
    and nothing else. Its own message admitted the hole: *"the part may still
    exist and already be filed in another drawer"*, with no way to reach it.

    Scott, 2026-08-23, holding an SMA pigtail and typing "Sma": *"still cant
    make it work."* Nothing unlocated in A3 matched, which was true and
    useless; `SMA Female to U.FL/IPEX Pigtail Cable, 1.13, 15cm` was part #732
    the whole time, with no stock.
    """
    q = (q or "").strip()
    if len(q) < 2:
        return []
    return catalogue_search(q, limit=limit)


@app.post("/api/filepart")
def api_filepart(part: int = Form(...), location: str = Form(...),
                 quantity: str = Form(""), site: str = Form(""),
                 confirm: str = Form("")):
    """Create a part's FIRST stock row, from the drawer, on the walk.

    `/api/assign` MOVES an existing row. That covers the import backlog, where
    every part already had a row sitting at cabinet level -- and covers nothing
    else. Measured 2026-08-23: **465 of 992 active parts have no stock row
    anywhere**, 47% of the catalogue. Every one of them is a thing you can find
    in a drawer and be unable to record from where you are standing.

    It cost three separate dead ends in one morning: a bagged capacitor kit, a
    Shelly Plus 2PM identified perfectly from its box, and an MHCOZY relay. In
    each case the part existed, the drawer was open, and the only route was to
    walk back to a desk.

    `/api/newpart` cannot be that route -- it duplicate-checks and refuses,
    correctly, because the part is already there. The missing verb was never
    "create a part"; it was "put this part HERE".

    **A quantity is required, unlike assign.** Assign can leave it blank because
    the row already carries a purchased figure and blank means "moved, not
    counted". There is no such figure here: creating a row means stating how
    much is in the drawer, and the only honest source for that is someone
    looking. So the count is the price of admission rather than an option.
    """
    if not WRITES_ON:
        return JSONResponse({"error": "writes disabled (BINSCAN_WRITES != 1)"}, 403)
    if confirm.lower() not in ("1", "true", "yes"):
        return JSONResponse({"error": "confirm required"}, 400)

    try:
        loc = resolve_loc(location, site)
    except Ambiguous as e:
        return JSONResponse({"error": str(e)}, 409)
    if loc is None:
        return JSONResponse({"error": f"no location named {location}"}, 404)

    p = it_get(f"part/{part}/")
    if not p:
        return JSONResponse({"error": f"no part {part}"}, 404)

    if not str(quantity).strip():
        return JSONResponse({"error": "a count is required to create stock - "
                                      "there is no purchased figure to carry "
                                      "over, so a blank would be an invented "
                                      "number"}, 400)
    try:
        n = float(quantity)
    except ValueError:
        return JSONResponse({"error": f"quantity {quantity!r} is not a number"}, 400)
    if n < 0:
        return JSONResponse({"error": "quantity cannot be negative"}, 400)

    existing = _rows(it_get("stock/", part=part, limit=50))
    here = [s for s in existing if s.get("location") == loc["pk"]]
    if here:
        return JSONResponse({"error": f"part {part} already has stock in "
                                      f"{loc['name']} (row {here[0].get('pk')}) - "
                                      f"use Recount rather than adding a row"}, 409)

    stamp = datetime.date.today().isoformat()
    note = (f"binscan {stamp}: filed into {loc['name']} and COUNTED at {n:g} by "
            f"hand. First stock row for this part.")
    if existing:
        # Same rule as a split: this row is what is HERE, not the shop total.
        note = (f"binscan {stamp}: filed into {loc['name']} and COUNTED at {n:g} "
                f"by hand. The same part is also filed in "
                f"{len(existing)} other row(s); this row is what is HERE, not "
                f"the total. Sum the rows for the shop figure.")

    body, err = it_post("stock/", {"part": part, "location": loc["pk"],
                                   "quantity": n, "notes": note})
    body = _one(body)
    if err or not body.get("pk"):
        return JSONResponse({"error": f"could not create the stock row: {err}"}, 502)

    # Verify by re-read. The API's word is worth nothing on this install --
    # four parameters are silently ignored and still return success.
    chk = it_get(f"stock/{body['pk']}/") or {}
    if (chk.get("location") != loc["pk"]
            or abs(float(chk.get("quantity", -1)) - n) > 1e-6):
        return JSONResponse({"error": "the new row did not verify on re-read",
                             "got": {"location": chk.get("location"),
                                     "quantity": chk.get("quantity")}}, 500)

    cleared = clear_empty_stamp(loc)
    log_append({"id": uuid.uuid4().hex[:8], "kind": "filepart",
                "at": datetime.datetime.now().isoformat(timespec="seconds"),
                "part": part, "part_name": p.get("name"),
                "new_stock": body["pk"], "location": loc["name"],
                "location_pk": loc["pk"], "quantity": n, "counted": True,
                "first_row": not existing, "cleared_empty": bool(cleared)})
    return {"ok": True, "verified": True, "created": True,
            "stock": body["pk"], "part": part, "name": p.get("name"),
            "location": loc["name"], "quantity": n, "counted": True,
            "first_row": not existing, "cleared_empty": cleared,
            "note": ("first stock row for this part" if not existing
                     else "another row for a part filed elsewhere too")}


@app.get("/api/unlocated")
def api_unlocated(cabinet: str = ""):
    return cabinet_unlocated(cabinet) if cabinet else []


@app.post("/api/identify")
async def api_identify(image: UploadFile = File(...),
                       cabinet: str = Form(""),
                       location: str = Form(""),
                       more: str = Form(""),
                       # The client has always posted `site`; this endpoint just
                       # never declared it, so the drawer_contents(location, site)
                       # call below raised NameError and returned a plain-text
                       # 500 -- which Safari reports as "SyntaxError: The string
                       # did not match the expected pattern", naming neither the
                       # endpoint nor the variable. Identify was dead on its main
                       # path from f25e3f0 until 2026-08-23.
                       site: str = Form(""),
                       provider: str = Form("anthropic")):
    """READ-ONLY. Reads the tag, proposes a match, writes nothing.

    Short-circuits if the drawer is already assigned. The UI should not get
    here in that case, but a guard in the endpoint costs nothing and the UI is
    not the only caller."""
    # `more` means the caller is deliberately adding a SECOND part to a drawer
    # that already holds one. The short-circuit below exists so a model is never
    # asked what the record already knows -- correct for the normal flow, and
    # exactly wrong here, where the drawer being assigned is the premise rather
    # than the objection. Scott hit this filing a second part into B1-R1C1: he
    # photographed it and got "already on record" with no way forward.
    if location and more.lower() not in ("1", "true", "yes"):
        known = drawer_contents(location, site)
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

    # When nothing matches, hand back a STARTING POSITION for creating it rather
    # than a blank form. The read already contains everything the funnel asks
    # for -- "EVERBILT HEX NUTS 3/8 in-16 I.D. STAINLESS 25PK" is a thread, a
    # type and a material -- and making someone re-enter what was just read off
    # the label is the tool wasting the work it did.
    #
    # It is a SUGGESTION and the fields stay editable: the label is evidence
    # about the box, and the box is evidence about its contents only as long as
    # nobody refilled it.
    suggest = None
    if not ranked:
        read_text = " ".join(list(reading.get("labels") or [])
                             + list(reading.get("markings") or []))
        metric, imp, mm, inch = _facts(read_text)
        head = _first(read_text, _HEAD)
        fin = _first(read_text, _FINISH)
        thread = (metric.upper() if metric else imp) or ""
        if thread:
            nice = {"socket head": "Socket Head Cap Screw", "hex nut": "Hex Nut",
                    "nyloc nut": "Nyloc Nut", "hex head": "Hex Bolt",
                    "flat washer": "Flat Washer", "button head": "Button Head Cap Screw",
                    "flat head": "Flat Head Cap Screw", "pan head": "Pan Head Machine Screw",
                    "lock washer": "Split Lock Washer", "set screw": "Set Screw",
                    }.get(head, head.title() if head else "")
            length = (f"{mm:g}mm" if mm is not None
                      else f"{inch:g}in" if inch is not None else "")
            nolen = "nut" in head or "washer" in head
            name = " ".join(x for x in [nice, thread] if x)
            if length and not nolen:
                name += f" x {length}"
            if fin:
                name += f", {fin}"
            suggest = {"name": name.strip(), "system": "metric" if metric else "imperial",
                       "thread": thread, "head": head, "finish": fin,
                       "length": length if not nolen else ""}

    # The fastener matcher has had its say. If it found nothing, ask the
    # catalogue by NAME -- most of what is in these drawers is not a fastener,
    # and a module's box carries a brand and a model rather than a thread.
    catalogue = [] if ranked else catalogue_matches(reading)

    rec_id = uuid.uuid4().hex[:8]
    ext = {"image/png": "png", "image/webp": "webp"}.get(media, "jpg")
    (SHOTS / f"{rec_id}.{ext}").write_bytes(raw)
    rec = {"id": rec_id, "kind": "identify", "catalogue": catalogue,
           "at": datetime.datetime.now().isoformat(timespec="seconds"),
           "cabinet": cabinet, "photo": f"{rec_id}.{ext}",
           "reading": reading, "basis": basis,
           "candidates": [{"sku": c["row"]["sku"], "name": c["row"]["name"],
                           "stock": c["row"]["stock"], "why": c["why"],
                           "quantity": c["row"].get("quantity"),
                           "strength": c["strength"]} for c in ranked],
           "unlocated_in_cabinet": len(rows), "actual": None, "suggest": suggest,
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
/* ── binscan visual system ────────────────────────────────────────────────
   iPhone first, dark only, its own identity — not InvenTree's.
   Read at arm's length in a garage, one-handed, with the other hand holding
   a part. Every state carries a GLYPH as well as a colour (Scott is mildly
   colourblind), and the explanatory notes STAY: this gets used in bursts
   weeks apart, so it has to be legible to someone who last saw it a month
   ago. They are demoted, not deleted.
   Capped at 560px so a small iPad reads as a column, not a stretched phone.
   ──────────────────────────────────────────────────────────────────────── */
:root{
  --bg:#0b0b0e; --surface:#15151a; --surface-2:#1c1c22; --line:#2a2a32;
  --fg:#f2f2f5; --mut:#8e8e9a; --dim:#65656f;
  /* A brighter rule for things that are OBJECTS -- cabinets, drawers -- as
     opposed to the hairlines that merely separate text. Under shop lighting the
     dim rule made the tiles read as a flat field rather than as things you can
     press, and for a mildly colourblind reader edge contrast does more work
     than fill colour. */
  --edge:#4d4d5c;
  --acc:#4ea1ff; --acc-ink:#04121f;
  --ok:#4ade80; --info:#38bdf8; --warn:#fde047; --bad:#ff8f8f; --mix:#d8a0ff;
  --s1:6px; --s2:10px; --s3:16px; --s4:24px;
  --r1:8px; --r2:12px; --r3:16px;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0 auto;max-width:560px;padding:0 var(--s3) 4px;background:var(--bg);
  color:var(--fg);font:15px/1.5 -apple-system,system-ui,"SF Pro Text",sans-serif;
  -webkit-font-smoothing:antialiased}

/* ── header: compact, sticky, always says where you are ─────────────────── */
.appbar{position:sticky;top:0;z-index:30;margin:0 calc(var(--s3) * -1);
  padding:10px var(--s3) 9px;background:rgba(11,11,14,.92);
  backdrop-filter:saturate(140%) blur(12px);border-bottom:1px solid var(--line);
  display:flex;align-items:baseline;gap:9px}
/* The mark is the drawer grid, with the one you are looking at lit -- the
   whole tool in nine rectangles. */
.logo{width:19px;height:19px;flex:0 0 auto;align-self:center}
.logo rect{fill:var(--dim)}
.logo rect.lit{fill:var(--acc)}
.appbar h1{font-size:17px;font-weight:800;margin:0;letter-spacing:-.02em}
.appbar h1 span{color:var(--acc)}
/* The badge and the drawer address travel together, right-aligned as a group.
   Putting margin-left:auto on the badge alone meant that hiding the badge --
   which is the normal case, at home -- left the drawer address stranded beside
   the ? button instead of at the right edge. */
.hdrright{margin-left:auto;display:flex;align-items:center;gap:7px}
.appbar .where{font-size:11.5px;color:var(--mut);font-weight:600;
  font-variant-numeric:tabular-nums;white-space:nowrap}
.appbar .where b{color:var(--fg);font-weight:700}

p.sub{color:var(--dim);margin:8px 0 2px;font-size:12.5px;line-height:1.45}

/* ── site switcher: in the header, tap to toggle ────────────────────────── */
/* The SITE is the prominent one and the drawer address is context. Scott: the
   drawer is already shown twice -- the cabinet tile is highlighted and the
   drawer cell is outlined -- while the house has no visual anywhere else on
   screen. Emphasis follows what is NOT otherwise visible, not what is most
   specific. */
.sitebtn{width:auto;min-height:0;margin:0;padding:4px 12px;font-size:13px;
  font-weight:800;letter-spacing:.04em;background:var(--surface-2);
  color:var(--fg);border:1px solid var(--edge);border-radius:999px}
.sitebtn.away{background:#3a2f07;color:var(--warn);border-color:#7a6410}

/* ── section labels ─────────────────────────────────────────────────────── */
label{display:block;margin:14px 0 5px;color:var(--mut);font-size:11px;
  font-weight:700;text-transform:uppercase;letter-spacing:.07em}

/* ── controls ───────────────────────────────────────────────────────────── */
input,select,button{width:100%;padding:12px 13px;font-size:16px;border-radius:var(--r2);
  border:1px solid var(--line);background:var(--surface);color:var(--fg);
  font-family:inherit}
input::placeholder{color:var(--dim)}
select{appearance:none;background-image:linear-gradient(45deg,transparent 50%,var(--mut) 50%),
  linear-gradient(135deg,var(--mut) 50%,transparent 50%);
  background-position:calc(100% - 18px) 21px,calc(100% - 13px) 21px;
  background-size:5px 5px,5px 5px;background-repeat:no-repeat;padding-right:34px}
button{background:var(--acc);color:var(--acc-ink);font-weight:700;border:0;
  margin-top:var(--s2);min-height:46px;letter-spacing:-.01em}
button:disabled{opacity:.3}
button.quiet{background:var(--surface-2);color:var(--fg);border:1px solid var(--line);
  font-weight:600}

/* ── cards ──────────────────────────────────────────────────────────────── */
.card{margin-top:var(--s2);padding:13px 14px;background:var(--surface);
  border:1px solid var(--line);border-radius:var(--r3)}
.card>b:first-child{display:block;margin-bottom:var(--s1);font-size:14.5px}
.big{font-size:17px;font-weight:700;margin:1px 0 2px;letter-spacing:-.01em;line-height:1.3}
.row{display:flex;justify-content:space-between;gap:10px;padding:7px 0;
  border-top:1px solid var(--line);font-size:13.5px}
.row span:first-child{color:var(--mut)}
.prov{font-size:10.5px;color:var(--acc);text-transform:uppercase;letter-spacing:.08em;
  font-weight:700;margin-bottom:var(--s1)}

/* ── notes and hints: kept, demoted ─────────────────────────────────────── */
.mut{color:var(--mut);font-size:12.5px;line-height:1.45}
.warn{margin-top:var(--s2);padding:9px 11px;border-radius:var(--r1);
  background:#241d0d;color:#f4d38a;font-size:12.5px;line-height:1.45;
  border-left:3px solid #8a6d1a}
.err{background:#2a1517;color:var(--bad);border-left-color:#7a2b31}
.ro{margin:var(--s3) 0 var(--s2);padding:9px 11px;border-radius:var(--r1);
  background:#101c26;color:#8fc7ff;font-size:11.5px;line-height:1.5;
  border-left:3px solid #23516f}

/* ── state colours: glyph first, colour second ──────────────────────────── */
.low{color:#ff9f43}.medium{color:var(--warn)}.high{color:var(--ok)}
.clear{color:var(--ok)}.partial{color:var(--warn)}.none{color:#ff9f43}

/* ── area chips ─────────────────────────────────────────────────────────── */
/* A cabinet is a rectangle on a wall, so its button is a rectangle -- roughly
   the 4:3 of the real thing. Pills read as tags; these read as objects you
   could point at. */
.chips{display:flex;flex-wrap:wrap;gap:5px}
/* THREE PER ROW, so the picker is laid out like the wall: A1 A2 A3 over
   B1 B2 B3. Same idea as the drawer grid -- a picker that mirrors the thing it
   picks from needs no legend, because you already know where to look. */
.chips{flex-direction:column;gap:5px}
.wallrow{display:flex;gap:5px}
/* Centred under the wall rather than left-aligned: it belongs to all of them,
   not to the first column. */
.wallrow.centred{justify-content:center}
/* One min-height for every tile so "elsewhere", whose label is smaller, still
   lines up with the cabinets rather than sitting 4px short. */
.chip{width:auto;min-height:51px;margin:0;padding:8px 0 7px;font-weight:800;
  justify-content:center;
  flex:1 1 0;font-size:16px;letter-spacing:-.01em;
  background:var(--surface);color:var(--fg);border:1px solid var(--edge);
  border-radius:var(--r1);display:flex;flex-direction:column;align-items:center;
  gap:1px;line-height:1.1}
.chip .mut{font-size:10.5px;margin:0;font-weight:700;font-variant-numeric:tabular-nums}
.chip.on{background:var(--acc);color:var(--acc-ink);border-color:var(--acc)}
.chip.on .mut{color:rgba(4,18,31,.65)}
/* Two tiles wide, not one: it stands for twenty-odd places, and a single tile
   would size it like one cabinet. Not full width either -- that would read as
   the whole wall. Dashed, because it is a door to somewhere else rather than a
   thing on this wall. */
.chip#more{flex:0 0 calc(((100% - (var(--cols,3) - 1) * 5px) / var(--cols,3)) * 2 + 5px);
  font-size:16px;font-weight:800;color:var(--fg);border-style:dashed;
  letter-spacing:-.01em}
.chip#more.on{color:var(--acc-ink);border-style:solid}
/* The places behind "Elsewhere" get the same treatment as the cabinets: bordered
   rectangles, name over count, one visual language for "a place you can go".
   Two per row rather than three, because these names are words -- Metrology
   Bench, Florida Staging -- not two characters, and a name that wraps to three
   lines is worse than a shorter row. */
/* Three wide, matching the cabinet rows above -- possible only because the long
   names are abbreviated on the tile. */
#rest{display:grid;grid-template-columns:repeat(3,1fr);gap:5px;margin-top:5px}
#rest .chip{flex:none;width:auto;font-size:12.5px;font-weight:800;padding:9px 4px 8px;
  line-height:1.2}
#rest .chip .mut{font-size:10.5px}

/* ── the drawer grid ────────────────────────────────────────────────────── */
.gridbox{margin-top:var(--s2);overflow-x:auto;-webkit-overflow-scrolling:touch}
.grow{display:flex;gap:4px;margin-bottom:4px}
.cell{flex:1 1 0;min-width:32px;height:44px;padding:0;margin:0;font-size:9.5px;
  line-height:1.05;border-radius:var(--r1);border:1px solid var(--edge);
  background:var(--surface);color:var(--dim);display:flex;flex-direction:column;
  align-items:center;justify-content:center;gap:2px;font-weight:600;min-height:0}
.cell .g{font-size:16px;font-weight:800;line-height:1}
.cell.large{height:52px}
.cell.filled{background:#0f2a19;color:var(--ok);border-color:#2c6b43}
.cell.uncounted{background:#0b2333;color:var(--info);border-color:#245a7e}
.cell.unknown{background:#332a06;color:var(--warn);border-color:#7a6410}
.cell.empty{background:var(--surface);color:#6a6a76;border-color:#3a3a46}
.cell.mixed{background:#271433;color:var(--mix);border-color:#5a3570}
.cell.declared{background:#0d2a2a;color:#6fd0c4;border-color:#2c6660}
.cell.on{outline:2px solid var(--acc);outline-offset:1px;color:var(--fg)}
.legend{display:flex;flex-wrap:wrap;gap:3px 12px;margin-top:8px;
  font-size:11px;font-weight:600;line-height:1.5}

/* ── the record panel ───────────────────────────────────────────────────── */
.known .card{margin-top:var(--s2)}
/* Only the panel HEADING is a block. Scoping this to every <b> inside .known
   turned the number inside "Recording 50 again is still a count" into its own
   line, which read as three broken fragments. */
.known > .card > b:first-child{display:block;margin-bottom:var(--s1);font-size:14.5px}
.onrow{padding:8px 0;border-top:1px solid var(--line)}
.onrow:first-of-type{border-top:0}
.onrow .countbox{margin-top:9px}
.docs{margin-top:5px;display:flex;flex-wrap:wrap;gap:6px}
.doclink{display:inline-flex;align-items:center;gap:5px;font-size:12px;
  font-weight:600;color:var(--acc);text-decoration:none;padding:3px 8px;
  border:1px solid var(--line);border-radius:999px;background:var(--surface)}
.doclink:active{background:#0b2333}
.uncount{display:inline-block;margin-left:5px;padding:1px 7px;border-radius:999px;
  background:#0b2333;color:var(--info);border:1px solid #245a7e;font-size:10.5px;
  text-transform:uppercase;letter-spacing:.05em;font-weight:800}

/* ── pick list ──────────────────────────────────────────────────────────── */
.picklist{max-height:300px;overflow-y:auto;margin-top:var(--s2);
  border:1px solid var(--line);border-radius:var(--r2);background:var(--bg)}
.pick{display:block;width:100%;margin:0;padding:10px 12px;border:0;min-height:0;
  border-bottom:1px solid var(--line);border-radius:0;background:transparent;
  color:var(--fg);text-align:left;font-size:13.5px;line-height:1.35;font-weight:400}
.pick:last-child{border-bottom:0}
.pick.on{background:#0b2333;box-shadow:inset 3px 0 0 var(--acc)}
.pick .top{display:flex;justify-content:space-between;align-items:baseline;gap:8px}
.pick .sku{color:var(--acc);font-family:ui-monospace,SFMono-Regular,monospace;
  font-size:11.5px;font-weight:600}
.pick .nm{display:block;margin-top:2px;white-space:normal;color:var(--fg)}
.pick .qt{color:var(--mut);font-size:11.5px;white-space:nowrap;
  font-variant-numeric:tabular-nums}
.pick.split{background:#1b1526}
.pick .elsewhere{display:block;margin-top:4px;font-size:11.5px;color:#c3a6ff;
  line-height:1.4}

/* ── the count box: the point of the exercise ───────────────────────────── */
.countbox{margin-top:var(--s3);padding:12px;border-radius:var(--r2);
  background:#0b2333;border:1px solid #2c6f9e}
.countbox label{margin:0 0 var(--s1);color:#8fd3ff;font-size:11px;font-weight:800}
.countbox input{background:#061520;border-color:#2c6f9e;font-size:22px;
  font-weight:800;text-align:center;padding:12px;font-variant-numeric:tabular-nums}
.countbox .why{margin-top:var(--s1);color:#86aec6;font-size:11.5px;line-height:1.45}

/* ── the funnel ─────────────────────────────────────────────────────────── */
.fchip{padding:7px 11px;font-size:13px;font-weight:600}
.fchip .ct{margin-left:6px;font-size:10.5px;color:var(--mut);font-weight:700;
  font-variant-numeric:tabular-nums}
.fchip.on .ct{color:rgba(4,18,31,.65)}
.fchip.zero{opacity:.5;border-style:dashed}
.fchip.zero .ct{color:var(--warn)}
.fresult{margin-top:var(--s3);padding:11px 12px;border-radius:var(--r2);
  background:var(--bg);border:1px solid var(--line);font-size:13px;line-height:1.45}

/* ── options drawer ─────────────────────────────────────────────────────── */
details#opts{margin-top:var(--s3);border:1px solid var(--line);border-radius:var(--r2);
  padding:9px 12px;background:var(--surface)}
details#opts summary{color:var(--mut);font-size:11px;text-transform:uppercase;
  letter-spacing:.07em;cursor:pointer;font-weight:700;list-style:none}
details#opts summary::-webkit-details-marker{display:none}
details#opts summary::before{content:"\203A  ";display:inline-block;
  transition:transform .15s}
details#opts[open] summary::before{transform:rotate(90deg)}
details#opts label{margin-top:var(--s2)}
details.card summary{list-style:none;font-weight:700}
details.card summary::-webkit-details-marker{display:none}

/* ── hints: kept, but off by default ────────────────────────────────────────
   Scott: "it is really too busy with text in its current form" -- and earlier,
   that he will not be in this daily once the inventory settles, so the
   explanations cannot simply be deleted. Both are true, so the prose is behind
   one switch. Off, the screen shows state and controls. On, it explains itself
   to someone who last used it a month ago. The setting persists.            */
.hint{display:none}
body.hints-on .hint{display:revert}
.hintbtn{width:auto;min-height:0;margin:0;padding:3px 9px;font-size:12px;
  font-weight:800;border-radius:999px;background:var(--surface-2);
  color:var(--mut);border:1px solid var(--line)}
.hintbtn.on{background:var(--acc);color:var(--acc-ink);border-color:var(--acc)}
/* Help that tells you what to DO. The first version of this was design
   rationale scattered through the screen -- why the count box is blank, why a
   photograph is not proof -- which is worth keeping but is not what someone
   returning after a month needs first. That person needs the five steps and
   the key to the marks. */
.helppanel{margin-top:var(--s2);padding:14px;border-radius:var(--r3);
  background:var(--surface);border:1px solid var(--line);font-size:13px;
  line-height:1.5}
.helppanel .hh{font-size:10.5px;font-weight:800;text-transform:uppercase;
  letter-spacing:.08em;color:var(--acc);margin:var(--s3) 0 var(--s1)}
.helppanel .hh:first-child{margin-top:0}
.helppanel ol,.helppanel ul{margin:0;padding-left:19px;color:var(--fg)}
.helppanel li{margin:5px 0}
.helppanel b{font-weight:700}
.key{width:100%;border-collapse:collapse;font-size:12.5px}
.key td{padding:3px 0;vertical-align:top;color:var(--mut)}
.key td:nth-child(2){color:var(--fg);font-weight:700;width:78px;padding-left:9px}
.key td.k{width:20px;font-weight:800;font-size:15px;text-align:center}
.hp-foot{margin-top:var(--s3);padding-top:var(--s2);border-top:1px solid var(--line);
  color:var(--dim);font-size:11.5px}

/* ── flash: survives the advance ────────────────────────────────────────── */
.flash{margin-top:var(--s2);padding:11px 13px;border-radius:var(--r2);
  background:#0f2a19;color:#a7e8c0;border:1px solid #2c6b43;font-size:13px;
  line-height:1.45}
.flash b{color:#d6f8e3}

/* ── the action bar: everything needed to act, never scrolls away ───────── */
/* Hidden while a count is being typed. The keypad shrinks the viewport and the
   sticky bar then sits on top of the very button you are reaching for -- and
   the bar is useless mid-count anyway: you are not taking a photo. */
body.counting .actionbar{display:none}
.actionbar{position:sticky;bottom:0;z-index:20;margin:var(--s3) calc(var(--s3) * -1) 0;
  padding:10px var(--s3) calc(12px + env(safe-area-inset-bottom));
  background:var(--bg);border-top:1px solid var(--line);
  box-shadow:0 -14px 26px -10px rgba(0,0,0,.9)}
.actionbar button{margin-top:8px}
.shot{display:flex;gap:10px;align-items:center}
.shot .hint{color:var(--mut);font-size:12px;line-height:1.4}
#file{position:absolute;width:1px;height:1px;opacity:0;pointer-events:none}
.camera{display:inline-flex;align-items:center;gap:6px;margin:0;padding:11px 14px;
  border-radius:var(--r2);background:var(--surface-2);color:var(--fg);
  border:1px solid var(--line);font-size:14px;font-weight:700;text-transform:none;
  letter-spacing:0;white-space:nowrap;cursor:pointer}
.camera:active{background:#2a2a32}
img#prev{height:58px;width:auto;max-width:34%;object-fit:cover;
  border-radius:var(--r1);display:none;border:1px solid var(--line)}
</style></head><body>
<div class=appbar>
  <svg class=logo viewBox="0 0 24 24" aria-hidden="true">
    <rect x="1"  y="1"  width="6.6" height="6.6" rx="1.6"/>
    <rect x="8.7" y="1"  width="6.6" height="6.6" rx="1.6"/>
    <rect x="16.4" y="1"  width="6.6" height="6.6" rx="1.6"/>
    <rect x="1"  y="8.7" width="6.6" height="6.6" rx="1.6"/>
    <rect class=lit x="8.7" y="8.7" width="6.6" height="6.6" rx="1.6"/>
    <rect x="16.4" y="8.7" width="6.6" height="6.6" rx="1.6"/>
    <rect x="1"  y="16.4" width="6.6" height="6.6" rx="1.6"/>
    <rect x="8.7" y="16.4" width="6.6" height="6.6" rx="1.6"/>
    <rect x="16.4" y="16.4" width="6.6" height="6.6" rx="1.6"/>
  </svg>
  <h1>Bin<span>Scan</span></h1>
  <button class=hintbtn id=hintbtn title="how this works">?</button>
  <span class=hdrright>
    <button class=sitebtn id=sitebtn title="tap to switch site"></button>
    <span class=where id=whereat></span>
  </span></div>
<div class="helppanel hint">
  <div class=hh>How this works</div>
  <ol>
    <li>Tap a <b>cabinet</b>, then a <b>drawer</b>.</li>
    <li>If the record already knows that drawer, it shows you what is in it.</li>
    <li>If it does not: <b>photograph the label</b>, <b>pick the part by hand</b>,
        or say the drawer is <b>empty</b>.</li>
    <li>Put in a <b>count</b> only if you actually counted. Left blank, the
        quantity stays the figure from the purchase order and is flagged as
        not counted.</li>
    <li><b>File it.</b> The grid updates and moves you to the next drawer.</li>
  </ol>
  <div class=hh>What the marks mean</div>
  <table class=key>
    <tr><td class=k style="color:#4ade80">&#10003;</td><td>counted</td><td>somebody tallied it</td></tr>
    <tr><td class=k style="color:#38bdf8">~</td><td>uncounted</td><td>filed, but the number came from the purchase order</td></tr>
    <tr><td class=k style="color:#fde047">?</td><td>unseen</td><td>nobody has opened it yet</td></tr>
    <tr><td class=k style="color:#d8a0ff">&equiv;</td><td>mixed</td><td>oddments, looked at and deliberately not itemised</td></tr>
    <tr><td class=k style="color:#5a5a5e">&middot;</td><td>empty</td><td>opened and confirmed empty</td></tr>
  </table>
  <div class=hh>Two things worth trusting</div>
  <ul>
    <li><b>Nothing is written until you press a File button.</b> Photographing
        and identifying change nothing.</li>
    <li><b>A match from a photo is a proposal.</b> The drawer in your hand
        outranks it.</li>
  </ul>
  <div class=hp-foot>Tap <b>?</b> again to hide this.</div>
</div>

<label>Where</label>
<div id=areas class=chips></div>
<div id=gridwrap></div>

<div id=flash></div>
<div id=known class=known></div>

<div id=partwrap style="display:none">
  <label id=lpart>What it holds</label>
  <input id=part placeholder="auto-filled from the drawer">
</div>

<details id=opts>
  <summary>Options &mdash; site, model, advance direction</summary>
  <div id=siterow style="display:none">
    <label>Site &mdash; which places to show</label>
    <select id=sitesel></select>
    <button id=sethome class=quiet style="display:none">Set as where I am</button>
    <div class="mut hint" id=homenote></div>
  </div>
  <label>Provider</label>
  <select id=prov></select>
  <label>After submit</label>
  <select id=adv>
    <option value="across" selected>advance across the row (C1&rarr;C2&hellip;)</option>
    <option value="down">advance down the column (R1&rarr;R2&hellip;)</option>
    <option value="stay">stay on this drawer</option>
  </select>
</details>



<div id=out></div>
<div class=actionbar>
  <div class=shot>
    <input id=file type=file accept=image/* capture=environment>
    <label class=camera for=file>&#128247; Take photo</label>
    <img id=prev>
    <div class=hint id=shothint>Pick a drawer first</div>
  </div>
  <button id=go disabled>Estimate</button>
</div>
<div class="ro hint">Every photo and every write is logged.
<a href="/log" style="color:#8fc7ff">view the log</a></div>

<script>
const $=s=>document.querySelector(s);
(function(){
  const on = localStorage.getItem('binscan.hints') === '1';
  document.body.classList.toggle('hints-on', on);
  const b=$('#hintbtn'); b.classList.toggle('on', on);
  b.onclick=()=>{
    const now=!document.body.classList.contains('hints-on');
    document.body.classList.toggle('hints-on', now);
    b.classList.toggle('on', now);
    localStorage.setItem('binscan.hints', now?'1':'0');
  };
})();
// A 478-entry select is the wrong control on a phone: reaching B3 meant
// scrolling past everything, and B3 is not even last. Two stages instead --
// pick a place, then tap the drawer where it physically sits. The grid mirrors
// the cabinet, so the picker doubles as a progress view.
// Glyph first, colour second.
const STATE={
  filled:    {g:'\u2713', word:'counted'},
  uncounted: {g:'~',       word:'filed, not counted'},
  unknown:   {g:'?',       word:'nobody has looked'},
  empty:     {g:'\u00b7', word:'verified empty'},
  mixed:     {g:'\u2261', word:'mixed jumble, not itemised'},
  declared:  {g:'\u25c6', word:'declared \u2014 nothing left to count here'},
};
let AREA=null, CELLS=[], CUR=null, LABEL='', MORE=false, SUGGEST=null;
let SITE='', SITES=[], as_cache=[];
fetch('/api/areas').then(r=>r.json()).then(as=>{
  as_cache = as;
  // Two sites, and Scott is about to lay Florida out properly. A switcher was
  // deferred on the grounds that LRD had nothing walkable -- he overruled it as
  // a timing question rather than a design one, which is right: he knows the
  // trajectory and the measurement only knew the snapshot.
  SITES=[...new Set(as.map(a=>a.site))].sort();
  SITE = SITES.includes('SLN') ? 'SLN' : SITES[0] || '';
  function switchTo(s, ask){
    // Confirm only when leaving HOME. Scott: "it's not like you're going to be
    // switching back and forth -- it's one switch six months later, switch it
    // back." A rare action deserves a question; the return trip does not, and
    // nagging on the safe direction is how people learn to dismiss dialogs
    // without reading them.
    if(ask && s !== HOME && !confirm(
        `Switch to ${s}?\n\nYou are working in ${HOME}. This only changes which `
      + `places BinScan shows you — nothing is written, and nothing already `
      + `filed is affected.`)){
      if($('#sitesel')) $('#sitesel').value = SITE;
      return;
    }
    SITE=s;
    AREA=null; CUR=null; CELLS=[]; UNLOCATED=[]; LABEL=''; SUGGEST=null; MORE=false;
    $('#gridwrap').innerHTML=''; $('#known').innerHTML=''; $('#out').innerHTML='';
    $('#flash').innerHTML=''; $('#go').disabled=true;
    if($('#sitesel')) $('#sitesel').value=SITE;
    syncHomeUI();
    setWhere(''); renderAreas();
  }

  function syncHomeUI(){
    const b=$('#sethome'), n=$('#homenote');
    if(!b) return;
    const away = SITE && SITE !== HOME;
    b.style.display = away ? '' : 'none';
    b.textContent = `I am at ${SITE} now`;
    if(n) n.textContent = away
      ? `You are recorded as being at ${HOME}, so ${SITE} shows a badge in the header.`
      : `You are at ${HOME}. No badge is shown while you are viewing it.`;
  }
  if(SITES.length > 1){
    $('#siterow').style.display='';
    $('#sitesel').innerHTML = SITES.map(x=>{
      const n = as.filter(a=>a.site===x).length;
      return `<option value="${x}"${x===SITE?' selected':''}>${x} — ${n} place${n===1?'':'s'}</option>`;
    }).join('');
    $('#sitesel').onchange=e=>switchTo(e.target.value, true);
    $('#sethome').onclick=()=>{
      HOME = SITE;
      localStorage.setItem('binscan.home', HOME);
      syncHomeUI(); setWhere($('#whereat').innerHTML);
    };
    syncHomeUI();
  }
  // The header badge only exists when you are away, and its only job is to
  // bring you home.
  // Tapping the badge toggles. Leaving home asks; coming home does not.
  $('#sitebtn').onclick=()=>{
    if(SITES.length < 2) return;
    const other = SITES.find(x=>x!==SITE);
    if(SITE === HOME) switchTo(other, true);
    else switchTo(HOME, false);
  };
  setWhere('');
  // The bin wall is where the work is; twenty-odd other places are real but
  // rarely the answer, and showing all of them cost nine rows of chips.
  // Shorter labels for the tiles only. The location's REAL name is unchanged
  // and stays in data-a and the tooltip -- this is display, not a rename, and
  // renaming would break every barcode, label and query that uses it.
  // Two jobs: shorten the long ones, and EXPLAIN the arcane ones. BL and BR are
  // meaningful only if you already know they are the pedestals under the
  // electronics bench -- which is exactly the knowledge someone returning after
  // a month has lost. Every label below comes from the location's own
  // description, so the tile says what the record says.
  const SHORT={
    'Metrology Bench':'Metrology', 'Florida Staging':'FL Staging',
    'Assembly & Test':'Assy & Test', 'Machine Shop':'Mach Shop',
    'Electronics Bench':'Elec Bench',
    'BL':'Bench Left',    'BR':'Bench Right',      // pedestals under the e-bench
    'L1':'Laser Cab L',   'L2':'Laser Cab R',      // cabinets under the laser bench
    'LW1':'Laser Wall 1', 'LW2':'Laser Wall 2', 'LW3':'Laser Wall 3',
    'WS1':'Wire Rack 1',  'WS2':'Wire Rack 2', 'WS2-S5':'Rack 2 Sh 5',
    'Kits':'Kit Boxes',   'SLN':'SLN site',    'LRD':'LRD Florida',
  };
  const label=n=>SHORT[n]||n;
  const chip=a=>`<button class=chip data-a="${a.name}" title="${a.name} — ${a.drawers} drawers">`
    + `${label(a.name)}<span class=mut>${a.drawers}</span></button>`;
  window.renderAreas = function(){
  const here = as_cache.filter(a=>a.site===SITE);
  const wall=here.filter(a=>a.grid), rest=here.filter(a=>!a.grid);
  // Group by the LETTER, one flex row per wall row, so the picker keeps
  // mirroring the wall as the wall changes. A0 and B0 arrive next week, making
  // those rows four wide, and row C is planned below B once the plywood table
  // goes. A hard-coded three-per-row would have quietly stopped matching the
  // shop the day the new cabinets went up.
  const byRow={};
  wall.forEach(a=>{
    const m=/^([A-Z]+)(\d+)$/.exec(a.name);
    const k=m?m[1]:'~';
    (byRow[k]=byRow[k]||[]).push({...a, n:m?+m[2]:0});
  });
  const rows=Object.keys(byRow).sort().map(k=>
    `<div class=wallrow>` + byRow[k].sort((x,y)=>x.n-y.n).map(chip).join('') + `</div>`
  ).join('');
  // "elsewhere" is a tile like any other, so it is sized against the widest
  // wall row rather than stretched across. The column count is whatever the
  // wall currently has -- three today, four once A0/B0 are up -- so it is
  // measured, not assumed.
  const cols = Math.max(...Object.values(byRow).map(v=>v.length), 1);
  $('#areas').style.setProperty('--cols', cols);
  $('#areas').innerHTML = rows
    + (rest.length
       ? `<div class="wallrow centred"><button class=chip id=more>Elsewhere<span class=mut>${rest.length}</span></button></div>`
         + `<div id=rest style="display:none;width:100%;margin-top:7px" class=chips>${rest.map(chip).join('')}</div>`
       : '');
  $('#areas').querySelectorAll('.chip[data-a]').forEach(b=>b.onclick=()=>loadArea(b.dataset.a));
  if($('#more')) $('#more').onclick=()=>{ const r=$('#rest');
    // 'grid', not 'flex': #rest lays out as a two-column grid of tiles, and an
    // inline style beats the stylesheet, so setting flex here silently undid it.
    const open=r.style.display!=='none'; r.style.display=open?'none':'grid';
    $('#more').classList.toggle('on',!open); };
  };
  renderAreas();
}).catch(()=>{ $('#areas').innerHTML='<div class="card err">could not load areas</div>'; });

async function loadArea(name){
  AREA=name; CUR=null;
  SITE=(as_cache.find(a=>a.name===name)||{}).site||SITE;
  setWhere(name);
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
           title="${c.name} — ${STATE[c.state].word}${c.label?' — '+c.label:''}">
           <span class=g>${STATE[c.state].g}</span><span>${c.r}.${c.c}</span></button>`).join('')+'</div>';
    });
  }else{
    html+='<div class=grow style="flex-wrap:wrap">'+CELLS.map(c=>
      `<button class="cell ${c.state}" style="flex:0 0 auto;min-width:96px;padding:0 10px"
         data-n="${c.name}" title="${STATE[c.state].word}">
         <span class=g>${STATE[c.state].g}</span><span>${c.name}</span></button>`).join('')+'</div>';
  }
  html+=`</div><div class=legend>
    <span style="color:#4ade80"><b>&#10003;</b> ${t.filled} counted</span>
    <span style="color:#38bdf8"><b>~</b> ${t.uncounted||0} uncounted</span>
    <span style="color:#fde047"><b>?</b> ${t.unknown} unseen</span>
    <span style="color:#d8a0ff"><b>&equiv;</b> ${t.mixed||0} mixed</span>
    <span style="color:#5a5a5e"><b>&middot;</b> ${t.empty} empty</span></div>`;
  $('#gridwrap').innerHTML=html;
  $('#gridwrap').querySelectorAll('.cell').forEach(b=>b.onclick=()=>pick(b.dataset.n));
}

// After a write, re-read the grid from the server rather than patching the
// cell in place. The local patch changed the colour class and left the GLYPH
// span alone, so a filed drawer went green and kept saying "?" -- invisible if
// you read colour, and the whole point of the glyph is that Scott reads the
// glyph. Two representations of one fact will disagree; keep one.
async function repaint(){
  if(!AREA) return;
  try{
    const g=await (await fetch('/api/grid?area='+encodeURIComponent(AREA))).json();
    if(g.error) return;
    CELLS=g.cells;
    g.cells.forEach(c=>{
      const b=$('#gridwrap').querySelector(`.cell[data-n="${c.name}"]`);
      if(!b) return;
      b.className='cell '+c.state+(c.large?' large':'')+(c.name===CUR?' on':'');
      b.innerHTML=`<span class=g>${STATE[c.state].g}</span><span>${c.r}.${c.c}</span>`;
      b.title=`${c.name} — ${STATE[c.state].word}`;
    });
    const t=g.tally, L=$('#gridwrap').querySelector('.legend');
    if(L) L.innerHTML=`<span style="color:#4ade80"><b>&#10003;</b> ${t.filled} counted</span>
      <span style="color:#38bdf8"><b>~</b> ${t.uncounted||0} uncounted</span>
      <span style="color:#fde047"><b>?</b> ${t.unknown} unseen</span>
      <span style="color:#5a5a5e"><b>&middot;</b> ${t.empty} empty</span>`;
  }catch(_){}
}

// The site lives in the header, as the thing you tap to change it -- Scott's
// idea, and better than the segmented control it replaced: a segmented control
// is for three or more, and this gives back a row above the grid. An accidental
// tap is contained, because switching only changes what is DISPLAYED; a drawer
// still has to be picked before anything can be written, and the header reads
// the new site the whole time.
// The site is shown ONLY when you are away from home. Scott: "it's too big and
// distracting, and really probably unnecessary most of the time" -- true, you
// are at SLN essentially always, and a label that never changes is a label
// nobody reads. So SLN shows nothing and LRD shows a loud badge: the indicator
// earns its space precisely when it is telling you something.
// The control itself lives in Options, with the set-once settings.
// WHERE YOU PHYSICALLY ARE, persisted. Scott: "by home you mean the one you're
// at geographically?" -- yes, and hard-coding SLN was wrong the moment he is
// actually in Florida. Two different intents needed separating:
//
//   "I have moved to Florida"        durable  -> changes HOME
//   "let me peek at Florida from NH" temporary -> changes only what is shown
//
// So the Options select changes the VIEW, and a separate one-tap action makes
// the viewed site your location. The badge means "you are looking somewhere
// other than where you are standing", which is the only time it is worth
// screen space.
let HOME = localStorage.getItem('binscan.home') || 'SLN';
// The site is ALWAYS shown, and it comes first. Scott: "the house is even more
// important -- make sure you're in the right place when you're working this."
// Right, and it overturns the earlier hide-at-home design: getting the drawer
// wrong costs a correction, getting the HOUSE wrong files Dover stock into
// Florida. An indicator that disappears when correct cannot reassure you that
// it is correct.
//
// Quiet when you are viewing where you stand, amber when you are not -- the
// distinction still earns its keep, it just no longer decides whether the
// label exists.
// FastAPI returns validation failures under `detail`, not `error`, so a 422
// surfaced as a bare "failed" with the actual reason thrown away -- which cost
// a round trip to diagnose something the response had already explained.
function errText(j){
  if(j && j.error) return j.error;
  if(j && Array.isArray(j.detail))
    return j.detail.map(d=>`${(d.loc||[]).slice(-1)[0]}: ${d.msg}`).join('; ');
  if(j && j.detail) return String(j.detail);
  return 'failed — no reason given';
}

function countingMode(on){ document.body.classList.toggle('counting', !!on); }

// Any count field, anywhere, puts the app in counting mode while it has focus.
document.addEventListener('focusin', e=>{
  if(e.target.matches('.countbox input')) countingMode(true);
});
document.addEventListener('focusout', e=>{
  if(e.target.matches('.countbox input')) setTimeout(()=>{
    if(!document.querySelector('.countbox input:focus')) countingMode(false);
  }, 120);
});

function wireRecount(drawer){
  $('#known').querySelectorAll('button.recount').forEach(b=>{
    // Stash the original label ONCE, before it can be overwritten by "Cancel".
    if(!b.dataset.was) b.dataset.was = b.textContent.trim();
    b.onclick=()=>{
      const box=$('#known').querySelector(`.recountbox[data-i="${b.dataset.i}"]`);
      const open = box.style.display !== 'none';
      box.style.display = open ? 'none' : '';
      b.textContent = open ? b.dataset.was : 'Cancel';
      countingMode(!open);
      if(!open){ box.querySelector('.rq').focus();
                 box.scrollIntoView({behavior:'smooth',block:'center'}); }
    };
  });
  $('#known').querySelectorAll('button.rgo').forEach(b=>b.onclick=async()=>{
    const i=b.dataset.i;
    const msg=$('#known').querySelector(`.rmsg[data-i="${i}"]`);
    const q=$('#known').querySelector(`.rq[data-i="${i}"]`).value.trim();
    if(!q){ msg.style.color='#ff8f8f'; msg.textContent='enter a number, or cancel'; return; }
    b.disabled=true; msg.style.color='#8a8a8e'; msg.textContent='recording…';
    const fd=new FormData();
    fd.append('stock',b.dataset.stock); fd.append('location',drawer);
    fd.append('site',SITE); fd.append('quantity',q); fd.append('confirm','yes');
    try{
      const j=await (await fetch('/api/assign',{method:'POST',body:fd})).json();
      if(j.ok){
        countingMode(false);
        setFlash(`&#10003; <b>${drawer}</b> counted at <b>${j.quantity}</b>, verified.`);
        await repaint();
        await refreshDrawer(drawer,true);
      }else{ msg.style.color='#ff8f8f'; msg.textContent=errText(j); b.disabled=false; }
    }catch(e){ msg.style.color='#ff8f8f'; msg.textContent=String(e); b.disabled=false; }
  });
}

function setWhere(t){
  const b=$('#sitebtn');
  if(b){
    const away = SITE && SITE !== HOME;
    b.style.display = SITE ? '' : 'none';
    b.textContent = SITE;
    b.classList.toggle('away', !!away);
    b.title = away
      ? `Viewing ${SITE}; you are at ${HOME}. Tap to go back.`
      : `You are at ${SITE}.` + (SITES.length > 1 ? ` Tap to view ${SITES.find(x=>x!==SITE)}.` : '');
  }
  const e=$('#whereat'); if(e) e.innerHTML = t || '';
}

function pick(name){
  CUR=name; LABEL=''; MORE=false; SUGGEST=null;
  setWhere(`<b>${name}</b>`);
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
  try{ d=await (await fetch('/api/drawer?name='+encodeURIComponent(v)+'&site='+encodeURIComponent(SITE))).json(); }
  catch(_){ $('#known').innerHTML='<div class="card err">could not reach the record</div>'; return; }
  if(d.error){ $('#known').innerHTML=`<div class="card err">${d.error}</div>`; return; }
  if(d.assigned){
    MODE='estimate';
    // Every filed row gets a way to correct its count. Without this a drawer
    // that had already been filed was read-only -- Scott went to A2-R1C1
    // knowing the real number and had nowhere to put it. Counting an existing
    // row is the commonest correction there is, and it was the one path the
    // app did not have.
    const items=(d.stock||[]).map((x,i)=>{
      const sub = x.sub_location && x.sub_location!==v ? ` <span class=mut>(in ${x.sub_location})</span>` : '';
      const mark = x.counted
        ? `<span class=high style="font-size:12px"> &#10003; counted ${x.stocktake_date}</span>`
        : `<span class=uncount>~ NOT COUNTED &mdash; purchased figure</span>`;
      // A datasheet lives on the PART, and this is a STOCK screen, so
      // InvenTree shows nothing here at all -- not even a hint one exists.
      // Scott: "you're gonna go in through stock ninety nine percent of the
      // time because you wanna know if you have it." So the sign of the
      // document goes where the walker already is, and the link is served by
      // binscan rather than by InvenTree, whose /media/ answers 401 to a phone
      // with no session.
      const docs = (x.docs||[]).map(dd =>
        `<a class=doclink href="/api/doc/${dd.pk}" target="_blank" rel="noopener"
            title="${(dd.comment||'').replace(/"/g,'&quot;')}">&#128196; ${dd.name}</a>`
      ).join('');
      return `<div class=onrow style="margin:6px 0">
        <div>${(+x.quantity).toLocaleString()} &times; ${x.name}${sub}${mark}</div>
        ${docs ? `<div class=docs>${docs}</div>` : ''}
        <button class="quiet recount" data-i="${i}" data-stock="${x.stock}"
                style="margin-top:6px;padding:7px 11px;font-size:12.5px;width:auto">
          ${x.counted ? 'Recount' : 'Count it'}</button>
        <div class=recountbox data-i="${i}" style="display:none">
          <div class=countbox>
            <label># HOW MANY ARE IN THE DRAWER?</label>
            <input class=rq data-i="${i}" type=number inputmode=decimal
                   placeholder="tap to count" value="">
            <div class=why>Recording <b>${(+x.quantity).toLocaleString()}</b> again
              is still a count &mdash; it turns the purchased figure into a
              verified one.</div>
          </div>
          <button class="rgo" data-i="${i}" data-stock="${x.stock}">Record count</button>
          <div class=rmsg data-i="${i}" style="margin-top:8px;font-size:13px"></div>
        </div></div>`;}).join('')
      || (d.homes||[]).map(h=>`<div class=mut>home of ${h.name} — no stock on hand</div>`).join('');
    // "Add another" used to exist only in the moments after a filing, so
    // leaving the drawer and coming back lost it. A drawer that holds one thing
    // can hold two whenever you next open it, not only in the sixty seconds
    // after the first was filed.
    $('#known').innerHTML=`<div class=card><b>On record</b>${items}
      <button id=addmorebtn style="margin-top:12px;background:var(--card);color:var(--fg);border:1px solid var(--line)">
        + Add another part to ${v}</button></div>`;
    $('#addmorebtn').onclick=()=>fileAnother(v);
    wireRecount(v);
    $('#part').value=(d.stock&&d.stock[0]&&d.stock[0].name)||(d.homes&&d.homes[0]&&d.homes[0].name)||'';
    $('#lpart').textContent='What it holds';
    $('#partwrap').style.display='';
    $('#go').textContent='Estimate';
    if(!$('#file').files[0]) $('#shothint').textContent='On record — photograph it to estimate the count';
  }else{
    MODE='identify';
    UNLOCATED = d.unlocated || []; LABEL = d.label || '';
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
        + manualCard() + createCard(LABEL) + skipCard();
      setTimeout(()=>wireFiling(v), 0);
    }
    $('#known').innerHTML='<div class=card><b>Nothing on record for this drawer.</b>'+
      '<div class="mut hint">Photograph the McMaster bag tag if there is one, '+
      'or say it is empty.</div>'+
      `<button id=emptybtn style="margin-top:12px;background:var(--card);color:var(--fg);border:1px solid var(--line)">&middot; This drawer is empty</button>`+
      `<button id=mixedbtn style="margin-top:8px;background:var(--card);color:var(--fg);border:1px solid var(--line)">&equiv; Oddments &mdash; ones and twos, not worth a row each</button>`+
      `<div class="mut hint" style="margin-top:7px">Four or more of the same thing? Catalogue it above instead.</div>`+
      '<div id=emptymsg class=mut style="margin-top:8px"></div></div>';
    $('#emptybtn').onclick=()=>markEmpty(v);
    $('#mixedbtn').onclick=()=>markMixed(v);
    $('#part').value='';
    $('#partwrap').style.display='none';
    $('#go').textContent='Identify from this photo';
    if(!$('#file').files[0]) $('#shothint').textContent='No record — photograph it, pick by hand, or say it is empty';
    // Offer the hand paths straight away, without requiring a photograph. A
    // drawer with no label still often has a person standing at it who can
    // read what is in it -- making them photograph it first to unlock a filter
    // box is the camera getting in the way of the record.
    if(!d.label){
      $('#out').innerHTML = manualCard() + createCard('') + skipCard();
      setTimeout(()=>wireFiling(v), 0);
    }
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
  const fd=new FormData(); fd.append('location',drawer); fd.append('site',SITE); fd.append('confirm','yes');
  try{
    const j=await (await fetch('/api/empty',{method:'POST',body:fd})).json();
    if(j.ok){
      setFlash(`&#10003; <b>${j.location}</b> recorded ${j.already?'(already)':''} as verified empty.`);
      await repaint();
      if($('#adv').value!=='stay') setTimeout(()=>advance(), 1100);
      else { msg.style.color='#7fd39b'; msg.textContent='recorded'; }
    }else{
      msg.style.color='#ff8f8f'; msg.textContent=errText(j); btn.disabled=false;
    }
  }catch(e){ msg.style.color='#ff8f8f'; msg.textContent=String(e); btn.disabled=false; }
}

async function markMixed(drawer){
  const note = prompt("Roughly what is in it? And did you take anything OUT to "
                    + "catalogue separately? (e.g. 'ones and twos of hex bolts; "
                    + "the 4 black SHCS were catalogued')") || "";
  const btn=$('#mixedbtn'), msg=$('#emptymsg');
  btn.disabled=true; msg.textContent='recording…';
  const fd=new FormData();
  fd.append('location',drawer); fd.append('note',note); fd.append('confirm','yes');
  try{
    const j=await (await fetch('/api/mixed',{method:'POST',body:fd})).json();
    if(j.ok){
      setFlash(`&#8801; <b>${j.location}</b> recorded as a mixed jumble &mdash; looked at, not itemised.`);
      await repaint();
      if($('#adv').value!=='stay') setTimeout(()=>advance(), 1200);
    }else{ msg.style.color='#ff8f8f'; msg.textContent=errText(j); btn.disabled=false; }
  }catch(e){ msg.style.color='#ff8f8f'; msg.textContent=String(e); btn.disabled=false; }
}

function setFlash(html){ $('#flash').innerHTML = html ? `<div class=flash>${html}</div>` : ''; }

function skipCard(){
  const nx=nextDrawer(CUR,$('#adv').value);
  return `<div class=card><div class=mut>Nothing to file here?</div>
    <button id=skipbtn style="background:var(--card);color:var(--fg);border:1px solid var(--line)">
      ${nx?`Skip to ${nx}`:'No next drawer in this direction'}</button></div>`;
}

// Two B2 drawers held things that were never entered. Skipping records
// nothing and filing the wrong row is worse, so there has to be a third way
// out. Collapsed by default: creating a part is the rare case, and an open
// text box invites a near-duplicate of something already in the catalogue.
// A faceted funnel, in Scott's order: system, then thread, then head. Each step
// is a question you can answer with the part in your hand -- a thread gauge, a
// look, a caliper -- which is why it is easier than typing a name, not harder.
//
// One inversion from McMaster: they hide options with no results. Here a ZERO
// is the useful answer. Narrowing to nothing is how you learn the part is not
// in the catalogue, and it is proof rather than "I scrolled and did not see
// it", which is what sent Scott looking through the same list several times.
//
// Faceted over the WHOLE catalogue, not the cabinet's unlocated rows: a part
// you are holding may already exist, filed in another drawer, and creating a
// second one is the outcome worth preventing.
let FAST=[], FSEL={system:'',thread:'',head:'',length:'',finish:''};
const F_IMP=['#2-56','#4-40','#6-32','#8-32','#10-24','#10-32','#12-24',
  '1/4-20','1/4-28','5/16-18','5/16-24','3/8-16','3/8-24','7/16-14','7/16-20',
  '1/2-13','1/2-20','9/16-12','5/8-11','3/4-10'];
const F_MET=['M2','M2.5','M3','M4','M5','M6','M8','M10','M12','M14','M16'];
const F_HEAD=['socket head','button head','flat head','pan head','hex head',
  'fillister','low-profile socket','set screw','hex nut','nyloc nut','cap nut',
  'flat washer','fender washer','lock washer','threaded rod','dowel pin',
  'spring pin','standoff'];
const F_FIN=['zinc-plated','black-oxide','18-8 stainless','316 stainless',
  'galvanized','plain steel','brass','nylon'];

function fmatch(upto){
  const order=['system','thread','head','length','finish'];
  const keys=order.slice(0, order.indexOf(upto)+1);
  return FAST.filter(x=>keys.every(k=>!FSEL[k] || x[k]===FSEL[k]));
}
function fcount(key,val){
  const order=['system','thread','head','length','finish'];
  const before=order.slice(0,order.indexOf(key));
  return FAST.filter(x=>before.every(k=>!FSEL[k]||x[k]===FSEL[k]) && x[key]===val).length;
}
function chips(key,vals){
  return `<div class=chips style="margin-top:7px">` + vals.map(v=>{
    const n=fcount(key,v), on=FSEL[key]===v;
    return `<button class="chip fchip${on?' on':''}${n?'':' zero'}"
              data-k="${key}" data-v="${v}">${v}<span class=ct>${n}</span></button>`;
  }).join('') + `</div>`;
}
// The facet VALUE is a search word; the part NAME is a proper noun. "socket
// head" narrows well and reads badly, so they are not the same string.
const F_NAME={'socket head':'Socket Head Cap Screw','button head':'Button Head Cap Screw',
  'flat head':'Flat Head Cap Screw','pan head':'Pan Head Machine Screw',
  'hex head':'Hex Bolt','fillister':'Fillister Head Screw',
  'low-profile socket':'Low-Profile Socket Head Screw','set screw':'Set Screw',
  'hex nut':'Hex Nut','nyloc nut':'Nyloc Nut','cap nut':'Cap Nut',
  'flat washer':'Flat Washer','fender washer':'Fender Washer',
  'lock washer':'Split Lock Washer','threaded rod':'Threaded Rod',
  'dowel pin':'Dowel Pin','spring pin':'Spring Pin','standoff':'Standoff'};

function funnelName(){
  const t=FSEL.head, sz=FSEL.thread, ln=($('#fLen')?$('#fLen').value.trim():''),
        fin=FSEL.finish;
  if(!t||!sz) return '';
  const nolen=/nut|washer/.test(t);
  const metric=FSEL.system==='metric';
  const Title=F_NAME[t] || t.replace(/\b\w/g,c=>c.toUpperCase());
  let core=`${Title} ${sz}`;
  if(!nolen && ln) core+=` x ${ln}${/[a-z"']/i.test(ln)?'':(metric?'mm':'in')}`;
  return core + (fin?`, ${fin}`:'');
}
function renderFunnel(){
  const box=$('#funnel'); if(!box) return;
  const sizes = FSEL.system==='metric' ? F_MET
              : FSEL.system==='imperial' ? F_IMP : [];
  const hit=fmatch('finish');
  const nolen=/nut|washer/.test(FSEL.head||'');
  box.innerHTML =
    `<label>1 &middot; thread system</label>${chips('system',['imperial','metric'])}`
  + (FSEL.system?`<label style="margin-top:11px">2 &middot; thread size</label>${chips('thread',sizes)}`:'')
  + (FSEL.thread?`<label style="margin-top:11px">3 &middot; head or type</label>${chips('head',F_HEAD)}`:'')
  + (FSEL.head?`<label style="margin-top:11px">4 &middot; finish</label>${chips('finish',F_FIN)}`:'')
  + (FSEL.head&&!nolen?`<label style="margin-top:11px">5 &middot; length</label>
       <input id=fLen placeholder="e.g. 3/4 or 20" autocomplete=off value="${$('#fLen')?$('#fLen').value:''}">`:'')
  + `<div class=fresult>` + (
      !FSEL.thread ? `<span class=mut>${hit.length} fasteners in the catalogue &mdash; keep narrowing</span>`
      : hit.length ? `<b>${hit.length}</b> in the catalogue match so far:` +
          `<div class=picklist style="max-height:150px;margin-top:7px">` +
          hit.slice(0,20).map(x=>`<div class=pick style="cursor:default">
             <span class=top><span class=sku>${x.sku||'—'}</span></span>
             <span class=nm>${x.name}</span></div>`).join('')
          + `</div>`
      : `<b style="color:#4ade80">&#10003; Nothing in the catalogue matches.</b>
         <div class=mut style="margin-top:5px">Not "you missed it" &mdash; the whole
         catalogue was filtered by these attributes and came back empty. Safe to
         create it.</div>`)
    + `</div>`;
  box.querySelectorAll('.fchip').forEach(b=>b.onclick=()=>{
    const k=b.dataset.k;
    FSEL[k] = FSEL[k]===b.dataset.v ? '' : b.dataset.v;
    if(k==='system'){FSEL.thread='';FSEL.head='';FSEL.finish='';}
    if(k==='thread'){FSEL.head='';FSEL.finish='';}
    if(k==='head'){FSEL.finish='';}
    renderFunnel(); syncName();
  });
  const fl=$('#fLen'); if(fl) fl.oninput=syncName;
}
function syncName(){ const n=funnelName(); if(n) $('#npname').value=n; }

function createCard(seed){
  const s = (seed||'').trim();
  return `<details class=card id=newpartbox>
    <summary style="color:var(--acc);font-size:13px;cursor:pointer">
      Not in the list? Narrow it down and create it</summary>
    <div id=funnel></div>
    <label style="margin-top:12px">Name that will be saved &mdash; edit freely</label>
    <input id=npname value="${s.replace(/"/g,'&quot;')}" placeholder="or just type it">
    <label style="margin-top:10px">Anything worth recording (optional)</label>
    <input id=npnotes placeholder="markings, material, how you identified it">
    <div class=countbox>
      <label># HOW MANY ARE IN THE DRAWER?</label>
      <input id=npqty type=number inputmode=decimal placeholder="tap to count">
      <div class=why>Blank = not counted.</div>
    </div>
    <button id=npgo style="margin-top:10px">Create and file in ${CUR}</button>
    <div id=npmsg style="margin-top:8px;font-size:13px"></div>
    <div class="mut hint" style="margin-top:8px">No supplier and no purchase
      record, so this part will never show up in the bought-vs-counted report.</div>
  </details>`;
}

async function loadFasteners(){
  if(FAST.length) return;
  try{ FAST = await (await fetch('/api/fasteners')).json(); }catch(_){ FAST=[]; }
}

function wireCreate(drawer){
  const go=$('#npgo'); if(!go) return;
  // Pre-set the funnel from the read so the count of matching catalogue rows
  // is visible immediately -- which is the evidence that creating is the right
  // move, not a leap of faith.
  FSEL = SUGGEST
    ? {system:SUGGEST.system||'', thread:SUGGEST.thread||'',
       head:SUGGEST.head||'', length:'', finish:SUGGEST.finish||''}
    : {system:'',thread:'',head:'',length:'',finish:''};
  loadFasteners().then(()=>{
    renderFunnel();
    if(SUGGEST){
      const box=$('#newpartbox'); if(box) box.open=true;
      const fl=$('#fLen'); if(fl && SUGGEST.length) fl.value=SUGGEST.length.replace(/(mm|in)$/,'');
      if(SUGGEST.name) $('#npname').value=SUGGEST.name;
    }
  });
  const box=$('#newpartbox');
  if(box) box.addEventListener('toggle',()=>{ if(box.open) loadFasteners().then(renderFunnel); });
  go.onclick=async()=>{
    const msg=$('#npmsg');
    const fd=new FormData();
    fd.append('name',$('#npname').value); fd.append('location',drawer); fd.append('site',SITE);
    fd.append('quantity',$('#npqty').value.trim());
    fd.append('notes',$('#npnotes').value); fd.append('confirm','yes');
    go.disabled=true; msg.style.color='#8a8a8e'; msg.textContent='creating…';
    try{
      const j=await (await fetch('/api/newpart',{method:'POST',body:fd})).json();
      if(j.ok){
        setFlash(`&#10003; Created <b>${j.name}</b> and filed it in <b>${j.location}</b>`
          + (j.counted?`, <b>${j.quantity}</b> counted.`:', quantity <b>not counted</b>.'));
        await repaint();
        go.textContent='Created';
        $('#npmsg').innerHTML =
          `<button id=morebtn2 style="margin-top:10px;background:var(--card);color:var(--fg);border:1px solid var(--line)">Anything else in ${drawer}?</button>`;
        $('#morebtn2').onclick=()=>fileAnother(drawer);
      }else{
        msg.style.color='#ff8f8f'; msg.textContent=errText(j); go.disabled=false;
      }
    }catch(e){ msg.style.color='#ff8f8f'; msg.textContent=String(e); go.disabled=false; }
  };
}

function manualCard(){
  // Renders even with nothing unlocated. It used to return '' in that case,
  // which removed the only search box in the UI -- so in a cabinet whose
  // backlog was already filed there was no way to look a part up by hand at
  // all. The input now searches the CATALOGUE as well, which is the question
  // being asked whether or not this cabinet has a backlog.
  const none = !UNLOCATED.length;
  return `<div class=card>
    <div class=prov>${none ? 'search the catalogue' : 'or pick it by hand'}</div>
    <input id=manualq placeholder="${none ? 'what is it? &mdash; name or number'
                                          : 'filter &mdash; name or McMaster number'}" autocomplete=off>
    <div id=manualcount class=mut style="margin-top:7px"></div>
    <div id=manuallist class=picklist></div>
    <div id=catfound></div>
    <!-- The count box and the file button stay HIDDEN until a row is chosen.
         Shown up-front they invite a number with nothing to attach it to, above
         a disabled button, and the whole card reads as broken -- which is
         exactly how it read to Scott: "there's no way to commit that." -->
    <div id=manualact style="display:none">
      <div id=manualpicked class=mut style="margin-top:10px"></div>
      <div class=countbox>
        <label># HOW MANY ARE IN THE DRAWER?</label>
        <input class=qty data-i="m" type=number inputmode=decimal placeholder="tap to count">
        <div class=why>Blank = not counted.</div>
      </div>
      <button class=file data-i="m" data-stock="" id=manualfile>File it</button>
      <div class=msg data-i="m" style="margin-top:8px;font-size:13px"></div>
    </div>
  </div>`;
}

// A scrolling list cannot tell you whether a thing is absent or whether you
// missed it. Scott: "you think you're just not seeing it... I've stood there
// and looked through that list several times." So the filter REPORTS: how many
// of how many matched, and when nothing does it says so outright and points at
// the create path. Absence has to be an answer, not a failure to find.
// Shop words and catalogue words are not the same words. McMaster writes
// "Nylon-Insert Locknut"; Scott says "nyloc". A filter that misses on
// vocabulary reports ABSENCE, which is precisely the wrong answer to give
// someone deciding whether to create a new part.
const SYN=[['nyloc','nylock','nylon-insert','nylon insert','locknut','lock nut'],
           ['shcs','socket head','cap screw'],['bhcs','button head'],
           ['fhcs','flat head','countersink','countersunk'],
           ['machine screw','pan head','phillips'],
           ['setscrew','set screw','grub'],
           ['washer','flat washer'],['stainless','18-8','18/8','304','316'],
           ['zinc','zinc-plated','galvanized','galvanised'],
           ['blackox','black-oxide','black oxide']];
function expand(w){
  const out=new Set([w]);
  SYN.forEach(g=>{ if(g.some(x=>x.includes(w)||w.includes(x))) g.forEach(x=>out.add(x)); });
  return [...out];
}

// Catalogue results underneath the unlocated filter. Debounced and
// sequence-guarded: typing "pigtail" fires seven requests and they do not
// come back in order, so a slow early one must not overwrite a fast late one.
let CATSEQ = 0, CATTIMER = null;
async function catalogueFallback(t){
  const box = $('#catfound');
  if(!box) return;
  clearTimeout(CATTIMER);
  if(!t || t.length < 2){ box.innerHTML=''; return; }
  const seq = ++CATSEQ;
  CATTIMER = setTimeout(async ()=>{
    try{
      const r = await fetch('/api/partsearch?q='+encodeURIComponent(t));
      const list = await r.json();
      if(seq !== CATSEQ) return;              // a newer keystroke already won
      if(!list.length){ box.innerHTML=''; return; }
      box.innerHTML =
        `<div class=mut style="margin:14px 0 8px">Not waiting to be filed, but
           <b>in the catalogue</b> &mdash; ${list.length} match${list.length>1?'es':''}
           for &ldquo;${t}&rdquo;. Filing one of these creates stock where there
           was none.</div>` + catalogueCards(list, 'cat');
      wireFileParts(CUR);
    }catch(e){ box.innerHTML=`<div class=mut>catalogue search failed: ${e}</div>`; }
  }, 220);
}

function renderPicks(q){
  const list=$('#manuallist'), cnt=$('#manualcount'); if(!list) return;
  // Changing the filter unpicks whatever was picked; leaving the action block
  // open would let a count be filed against a row no longer on screen.
  const act=$('#manualact');
  if(act){ act.style.display='none'; const mf=$('#manualfile'); if(mf) mf.dataset.stock=''; }
  const t=(q||'').trim().toLowerCase();
  const terms=t.split(/\s+/).filter(Boolean);
  const hit=UNLOCATED.filter(u=>{
    const hay=((u.sku||'')+' '+u.name).toLowerCase();
    return terms.every(w=>expand(w).some(v=>hay.includes(v)));
  });
  cnt.innerHTML = !UNLOCATED.length
    ? (t ? '' : `Nothing is waiting to be filed in ${AREA} &mdash; type to search the whole catalogue`)
    : !t
    ? `${UNLOCATED.length} rows unlocated in ${AREA} &mdash; type to filter`
    : hit.length
      ? `<b>${hit.length}</b> of ${UNLOCATED.length} match &ldquo;${t}&rdquo;`
      : `<b style="color:#fde047">Nothing UNLOCATED in ${AREA} matches &ldquo;${t}&rdquo;.</b>
         A definite answer, not a scrolling problem. Note it means no row
         <i>waiting to be filed</i> &mdash; the part may still exist and already be
         filed in another drawer. If it is genuinely new, create it below.`;
  // The unlocated list answers "what is waiting to be filed in this cabinet".
  // It cannot answer "does this part exist", which is the question somebody
  // holding an unfamiliar part is actually asking. Ask the catalogue too.
  catalogueFallback(t);
  list.innerHTML = hit.slice(0,60).map(u=>
    `<button class=pick${u.at?' split':''} data-stock="${u.stock}" data-split="${u.at?1:0}">
       <span class=top><span class=sku>${u.sku||'—'}</span>
         <span class=qt>${(+u.quantity).toLocaleString()} ${u.at?`in ${u.at}`:'on record'}</span></span>
       <span class=nm>${u.name}</span>
       ${u.at?`<span class=elsewhere>already filed in ${u.at} &mdash; picking this adds a SECOND lot here, leaving that drawer alone</span>`:''}
     </button>`).join('')
    + (hit.length>60?`<div class=mut style="padding:6px 2px">…and ${hit.length-60} more, keep typing</div>`:'');
  list.querySelectorAll('.pick').forEach(b=>b.onclick=()=>{
    list.querySelectorAll('.pick').forEach(x=>x.classList.remove('on'));
    b.classList.add('on');
    const mf=$('#manualfile');
    mf.dataset.stock=b.dataset.stock;
    mf.dataset.split=b.dataset.split||'0';
    mf.disabled=false;
    mf.textContent = b.dataset.split==='1'
      ? `Add a second lot in ${CUR}` : `File in ${CUR}`;
    $('#manualact').style.display='';
    $('#manualpicked').innerHTML =
      `Chosen: <b style="color:var(--fg)">${b.querySelector('.nm').textContent}</b>`;
    $('#manualact').scrollIntoView({behavior:'smooth',block:'nearest'});
  });
}

function wireFiling(drawer){
  wireCreate(drawer);
  wireFileParts(drawer);
  const q=$('#manualq');
  if(q){ renderPicks(''); q.oninput=()=>renderPicks(q.value); }
  const sk=$('#skipbtn');
  if(sk) sk.onclick=()=>advance();
  $('#out').querySelectorAll('button.file').forEach(btn=>{
    btn.onclick=async()=>{
      const i=btn.dataset.i;
      const msg=$('#out').querySelector(`.msg[data-i="${i}"]`);
      const qty=$('#out').querySelector(`.qty[data-i="${i}"]`).value.trim();
      if(!btn.dataset.stock){ msg.style.color='#ff8f8f'; msg.textContent='choose a part first'; return; }
      if(btn.dataset.split==='1' && !qty){
        msg.style.color='#ff8f8f';
        msg.textContent='a second lot needs a count — otherwise there is no way to say how many are in THIS drawer';
        return; }
      btn.disabled=true; msg.textContent='filing…'; msg.style.color='#8a8a8e';
      const fd=new FormData();
      fd.append('stock',btn.dataset.stock); fd.append('location',drawer); fd.append('site',SITE);
      fd.append('quantity',qty); fd.append('confirm','yes');
      if(btn.dataset.split==='1') fd.append('split','1');
      try{
        const r=await fetch('/api/assign',{method:'POST',body:fd});
        const j=await r.json();
        if(j.ok){
          msg.style.color='#7fd39b';
          msg.textContent=`Filed in ${j.location}, verified. `
            + (j.counted?`Counted ${j.quantity}.`:`Quantity ${j.quantity} carried over — NOT counted.`);
          btn.textContent='Filed';
          await repaint();
          // The decision is made. Every other route to filing this drawer is
          // now a way to file it twice, so they go.
          $('#out').querySelectorAll('.card').forEach(c=>{
            if(!c.contains(btn)) c.style.display='none'; });
          $('#out').querySelectorAll('.warn').forEach(w=>w.style.display='none');
          const what = j.counted
            ? `<b>${j.quantity}</b> counted`
            : `<b>${j.quantity}</b> carried over, <b>not counted</b>`;
          setFlash(`&#10003; Filed into <b>${j.location}</b> &mdash; ${what}. Verified on re-read.`);
          // A drawer can hold more than one part, so filing one does NOT mean
          // the drawer is done -- and auto-advancing away would strand the
          // rest of its contents. Empty-marking still advances by itself: a
          // drawer is empty or it is not, and there is nothing more to add.
          // Here the answer is unknown, so it is asked rather than assumed.
          const nx=nextDrawer(drawer,$('#adv').value);
          const bar=document.createElement('div');
          bar.className='card';
          bar.innerHTML =
            `<div class=mut style="margin-bottom:10px">Filed into <b>${drawer}</b>.
               Is there anything else in that drawer?</div>
             <button id=morebtn style="background:var(--card);color:var(--fg);border:1px solid var(--line)">
               Yes &mdash; file another part in ${drawer}</button>`
            + (nx ? `<button id=nextbtn style="margin-top:9px">No &mdash; next drawer &rarr; ${nx}</button>`
                  : `<div class=mut style="margin-top:9px">That was the last drawer in this direction — pick another area above.</div>`);
          $('#out').appendChild(bar);
          if(nx) $('#nextbtn').onclick=()=>advance();
          $('#morebtn').onclick=()=>fileAnother(drawer);
        }else{
          msg.style.color='#ff8f8f'; msg.textContent=errText(j); btn.disabled=false;
        }
      }catch(e){ msg.style.color='#ff8f8f'; msg.textContent=String(e); btn.disabled=false; }
    };
  });
}

// Re-open the same drawer for a second part. Not a reload of the drawer view:
// that would now report the drawer as ASSIGNED -- correctly, it holds what was
// just filed -- and offer an estimate rather than another filing.
async function fileAnother(drawer){
  setFlash(''); MORE=true;
  try{
    const cab=cabinetOf(drawer);
    UNLOCATED = await (await fetch('/api/unlocated?cabinet='+encodeURIComponent(cab))).json();
  }catch(_){ UNLOCATED = []; }
  CUR = drawer;
  MODE='identify';
  $('#go').textContent='Identify from this photo';
  $('#go').disabled = !$('#file').files[0];
  $('#partwrap').style.display='none';
  $('#shothint').textContent='Adding another part — photograph it, or pick by hand';
  $('#known').innerHTML =
    `<div class=card><b>Adding another part to ${drawer}</b>
       <div class="mut hint">What is already filed here stays. Pick or create the
       next thing in the drawer.</div></div>`;
  $('#out').innerHTML = manualCard() + createCard('') +
    `<div class=card><div class=mut>Done with this drawer?</div>
       <button id=skipbtn style="background:var(--card);color:var(--fg);border:1px solid var(--line)">
         Move on</button></div>`;
  wireFiling(drawer);
  $('#known').scrollIntoView({behavior:'smooth',block:'nearest'});
}

async function advance(){
  const dir=$('#adv').value;
  if(dir==='stay') return;
  const nx=nextDrawer(CUR,dir);
  $('#file').value=''; $('#prev').style.display='none'; $('#prev').removeAttribute('src');
  $('#go').disabled=true; $('#out').innerHTML=''; UNLOCATED=[]; MORE=false;
  if(!nx){
    $('#known').innerHTML='<div class=card><b>End of cabinet.</b>'+
      '<div class=mut>Pick the next one by hand.</div></div>';
    return;
  }
  CUR=nx; setWhere(`<b>${nx}</b>`);
  $('#gridwrap').querySelectorAll('.cell').forEach(b=>b.classList.toggle('on',b.dataset.n===nx));
  await refreshDrawer(nx,false);
  $('#known').scrollIntoView({behavior:'smooth',block:'nearest'});
}
$('#file').onchange=e=>{
  const f=e.target.files[0]; $('#go').disabled=!f;
  if(f){
    $('#prev').src=URL.createObjectURL(f); $('#prev').style.display='block';
    $('#shothint').textContent = MODE==='identify'
      ? 'Photo ready. Press the blue button below.'
      : 'Photo ready — press Estimate below.';
  } else { $('#prev').style.display='none'; $('#shothint').textContent=''; }
};
function cabinetOf(drawer){ const m=/^([A-Z]\d+)-/.exec(drawer||''); return m?m[1]:''; }

// Filing a PART rather than a stock row. Separate from the button.file loop
// because that one refuses without a data-stock, which is exactly the case
// here: these parts may have no stock row at all, and creating the first one
// is the whole point.
function wireFileParts(drawer){
  $('#out').querySelectorAll('button.filepart').forEach(btn=>{
    if(btn.dataset.bound==='1') return;
    btn.dataset.bound='1';
    btn.onclick=async()=>{
      const i=btn.dataset.p;
      const msg=$('#out').querySelector(`.msg[data-p="${i}"]`);
      const qty=$('#out').querySelector(`.pqty[data-p="${i}"]`).value.trim();
      if(!qty){
        msg.style.color='#ff8f8f';
        msg.textContent='a count is required — creating stock means saying how many are in the drawer';
        return; }
      btn.disabled=true; msg.textContent='filing…'; msg.style.color='#8a8a8e';
      const fd=new FormData();
      fd.append('part',btn.dataset.part); fd.append('location',drawer);
      fd.append('site',SITE); fd.append('quantity',qty); fd.append('confirm','yes');
      try{
        const r=await fetch('/api/filepart',{method:'POST',body:fd});
        const j=await r.json();
        if(j.ok){
          msg.style.color='#7fd39b';
          msg.textContent=`Filed in ${j.location}, verified. Counted ${j.quantity}.`;
          btn.textContent='Filed';
          await repaint();
          $('#out').querySelectorAll('.card').forEach(c=>{
            if(!c.contains(btn)) c.style.display='none'; });
          $('#out').querySelectorAll('.warn').forEach(w=>w.style.display='none');
          setFlash(`&#10003; <b>${j.name}</b> filed into <b>${j.location}</b>
                    &mdash; <b>${j.quantity}</b> counted`
                   + (j.first_row?' (first stock row for this part)':'')
                   + `. Verified on re-read.`);
          const nx=nextDrawer(drawer,$('#adv').value);
          const bar=document.createElement('div');
          bar.className='card';
          bar.innerHTML =
            `<div class=mut style="margin-bottom:10px">Filed into <b>${drawer}</b>.
               Is there anything else in that drawer?</div>
             <button id=morebtn style="background:var(--card);color:var(--fg);border:1px solid var(--line)">
               Yes &mdash; file another part in ${drawer}</button>`
            + (nx ? `<button id=nextbtn style="margin-top:9px">No &mdash; next drawer &rarr; ${nx}</button>`
                  : `<div class=mut style="margin-top:9px">That was the last drawer in this direction.</div>`);
          $('#out').appendChild(bar);
          if(nx) $('#nextbtn').onclick=()=>advance();
          $('#morebtn').onclick=()=>fileAnother(drawer);
        }else{
          msg.style.color='#ff8f8f'; msg.textContent=errText(j); btn.disabled=false;
        }
      }catch(e){ msg.style.color='#ff8f8f'; msg.textContent=String(e); btn.disabled=false; }
    };
  });
}

// Parts the CATALOGUE matched by name, when the fastener matcher had nothing.
// These carry a part number rather than a stock number: the whole point is
// that they may have no stock row yet, which is why filing them needs
// /api/filepart instead of /api/assign.
function catalogueCards(list, pfx){
  if(!list || !list.length) return '';
  pfx = pfx || 'c';
  return list.map((c,i)=>{
    const key = pfx + i;
    const none = !c.stock_rows;
    const where = none
      ? `<span class=low>no stock anywhere yet</span>`
      : (c.where||[]).map(w=>`${w.location||'unlocated'} &times;${(+w.quantity).toLocaleString()}`).join(' · ');
    return `<div class=card>
      <div class=big style="font-size:17px">${c.name}</div>
      ${c.description?`<div class=mut style="margin-top:4px">${c.description}</div>`:''}
      <div class=row><span>part</span><span><b>#${c.part}</b></span></div>
      <div class=row><span>on record</span><span>${where}</span></div>
      <div style="margin-top:8px;color:#aaa;font-size:13.5px">${c.why}</div>
      <div class=countbox>
        <label># HOW MANY ARE IN THE DRAWER?</label>
        <input class=pqty data-p="${key}" type=number inputmode=decimal
               placeholder="count them">
        <div class=why>${none
          ? 'Required &mdash; this part has never had stock, so there is no purchased figure to carry over. A blank would be an invented number.'
          : 'Required &mdash; this would be a second lot, and only a count says how many are in THIS drawer.'}</div>
      </div>
      <button class=filepart data-p="${key}" data-part="${c.part}"
              style="margin-top:10px">File in ${CUR}</button>
      <div class=msg data-p="${key}" style="margin-top:8px;font-size:13px"></div>
    </div>`;
  }).join('');
}

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
    // Seed the create card from what was just READ, not from the drawer label.
    SUGGEST = d.suggest || null;
    const cat = catalogueCards(d.catalogue||[], 'id');
    // With catalogue matches the fastener advisory is misleading -- it says
    // nothing matched, when something did, just not in the fastener list.
    const lead = cat
      ? `<div class="card">The fastener matcher found nothing, but these are
           already in the <b>catalogue</b> by name. Check against the drawer.</div>`
      : `<div class="card warn">${why}</div>`;
    return read + lead + cat + manualCard()
         + createCard((d.suggest && d.suggest.name) || LABEL) + skipCard();
  }
  const here=CUR;
  return read + d.candidates.map((c,i)=>`<div class=card>
      <div class=big style="font-size:17px">${c.name}</div>
      <div class=row><span>McMaster</span><span><b>${c.sku||'—'}</b></span></div>
      <div class=row><span>basis</span><span class="${c.strength==='definite'?'high':c.strength==='probable'?'medium':'low'}">${c.strength}</span></div>
      <div style="margin-top:8px;color:#aaa;font-size:13.5px">${c.why}</div>
      <div class=countbox>
        <label># HOW MANY ARE IN THE DRAWER?</label>
        <input class=qty data-i="${i}" type=number inputmode=decimal
               placeholder="tap to count">
        <div class=why>Blank = not counted.<span class=hint> The
          <b>${(+c.quantity).toLocaleString()}</b> on record came from the purchase
          order, not from anyone looking.</span></div>
      </div>
      <button class=file data-i="${i}" data-stock="${c.stock}"
              style="margin-top:10px">File in ${here}</button>
      <div class=msg data-i="${i}" style="margin-top:8px;font-size:13px"></div>
    </div>`).join('')
    + `<div class=warn>Check it against the open drawer before filing.</div>`
    + manualCard() + createCard(LABEL) + skipCard();
}

$('#go').onclick=async()=>{
  const f=$('#file').files[0]; if(!f)return;
  const identify = MODE==='identify';
  const label = $('#go').textContent;
  $('#go').disabled=true; $('#go').textContent='Looking…'; $('#out').innerHTML='';
  const fd=new FormData();
  fd.append('image',f); fd.append('provider',$('#prov').value);
  fd.append('location',CUR||''); fd.append('site',SITE);
  if(identify){ fd.append('cabinet',cabinetOf(CUR)); if(MORE) fd.append('more','1'); }
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
    """The whole client is inside this page, so a cached page is stale CODE.

    Nothing set a cache header, and iOS Safari holds a page across reloads. On
    2026-08-23 a fix was deployed, verified on the server, and Scott went on
    hitting the old behaviour on his phone -- with both of us reading the
    server as proof it was fixed. A deploy that the walker cannot see is not
    deployed.

    no-store rather than a version query string: the page is 85 KB on a LAN,
    it changes on every deploy, and correctness here is worth more than a
    round trip.
    """
    return HTMLResponse(PAGE, headers={
        "Cache-Control": "no-store, no-cache, must-revalidate",
        "Pragma": "no-cache"})


@app.get("/healthz")
def healthz():
    return {"ok": True, "writes_enabled": WRITES_ON,
            "auto_write_confidence": sorted(AUTO_CONF),
            "providers": providers.status()}
