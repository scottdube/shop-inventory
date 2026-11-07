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
