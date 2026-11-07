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
