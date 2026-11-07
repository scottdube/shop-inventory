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
