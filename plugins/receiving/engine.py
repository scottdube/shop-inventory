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
