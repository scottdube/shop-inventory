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
    if __package__:
        try:
            return __import__(f"{__package__}.{name}", fromlist=[name])
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
