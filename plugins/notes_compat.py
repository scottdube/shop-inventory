"""notes_compat -- one way to read and write an object's notes on InvenTree 1.5.x AND 1.6.x.

1.5.x: Part, StockItem, PurchaseOrder, Company, Build ... carry a ``notes`` text
       column holding markdown.
1.6.x: that column is GONE (InvenTree #11971).  Notes are rows of ``common.Note``
       hung off the object through the GenericRelation ``notes_list``; ``content`` is
       nh3-sanitized HTML and exactly one note per object is ``primary``.  The data
       migration common.0051 turned every non-empty legacy note into the primary Note
       with ``content = markdown -> HTML`` (so ``[ESTIMATE] x`` became
       ``<p>[ESTIMATE] x</p>`` and the purchase-history table became ``<table>``).
       ``obj.notes`` still exists but is a QuerySet, so old code fails loudly.

This shop keeps its count-evidence conventions IN THE TEXT of the primary note
(decision and rejected options: docs/inventree-16-notes-port.md):

    [ESTIMATE] ...                 prefix on a stock row          (shop_status, BinScan, unaccounted)
    binscan DATE: ... COUNTED at N by hand                         (BinScan, sync_stocktake)
    TOOL 12,13 -- ...              prefix on a tooling stock row   (tool_tag)
    RECEIVED n on DATE from PO ... line                            (deploy_po, receive_po)
    CONSUMED BY: ...               line on a Part                  (unaccounted)
    ## Purchase history (who) + | pipe | table | on a Part        (shop_status)

Every function here takes the model instance and speaks PLAIN TEXT.  On 1.6 the
text is what a reader of the note would see: block tags become line breaks,
``<h2>`` becomes ``## ``, table rows become ``| a | b |`` pipe rows, so every
regex and parser written against the 1.5 markdown keeps working unchanged.
Writes on 1.6 never rewrite the existing HTML from text (that would flatten the
links and bold the McMaster import wrote): prepend/append add a block next to
the existing HTML, and the new text goes through the same markdown->HTML
conversion the migration used.  Every write is verified by re-reading the row.

Lives at <backend>/plugins/notes_compat.py on the Mini (the untracked plugins
dir survives a checkout) and is imported by the itq scripts as
``from plugins.notes_compat import ...``.  BinScan is a separate process on the
REST API and carries its own copy of the HTML<->text code in binscan/app.py.
"""

import html as _html
import re
from html.parser import HTMLParser

__all__ = [
    "is_v16", "note_text", "note_html", "note_set", "note_prepend", "note_append",
    "filter_notes", "html_to_text", "text_to_html", "primary_note",
]

_V16 = None


def is_v16():
    """True when the running InvenTree has no ``notes`` column on StockItem (1.6+)."""
    global _V16
    if _V16 is None:
        from stock.models import StockItem
        _V16 = not any(f.name == "notes" for f in StockItem._meta.concrete_fields)
    return _V16


# ----------------------------------------------------------------------------- HTML <-> text

_BLOCK_END = {"p": "\n\n", "div": "\n", "li": "\n", "tr": None, "h1": "\n\n", "h2": "\n\n",
              "h3": "\n\n", "h4": "\n\n", "h5": "\n\n", "h6": "\n\n", "blockquote": "\n\n",
              "pre": "\n\n", "table": "\n", "ul": "\n", "ol": "\n"}
_HEAD = {"h1": "# ", "h2": "## ", "h3": "### ", "h4": "#### ", "h5": "##### ", "h6": "###### "}


class _ToText(HTMLParser):
    """HTML -> the plain text a reader sees, keeping the shapes our parsers key on."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.row = None          # list of cells while inside <tr>
        self.cell = None         # list of text pieces while inside <td>/<th>
        self.in_pre = 0
        self.thead_rows = 0
        self.in_thead = False
        self.li_depth = 0

    def _emit(self, s):
        if self.cell is not None:
            self.cell.append(s)
        else:
            self.out.append(s)

    def _at_line_start(self):
        joined = "".join(self.out)
        return not joined or joined.endswith("\n")

    def handle_starttag(self, tag, attrs):
        if tag == "br":
            self._emit("\n")
        elif tag in _HEAD:
            if not self._at_line_start():
                self._emit("\n")
            self._emit(_HEAD[tag])
        elif tag == "li":
            if not self._at_line_start():
                self._emit("\n")
            self._emit("- ")
        elif tag == "tr":
            self.row = []
        elif tag in ("td", "th"):
            self.cell = []
        elif tag == "thead":
            self.in_thead = True
        elif tag == "pre":
            self.in_pre += 1
        elif tag == "img":
            alt = dict(attrs).get("alt") or ""
            if alt:
                self._emit(alt)
        elif tag in ("p", "div", "blockquote", "table", "ul", "ol"):
            if not self._at_line_start():
                self._emit("\n")

    def handle_endtag(self, tag):
        if tag in ("td", "th"):
            text = "".join(self.cell or []).strip()
            if self.row is not None:
                self.row.append(text)
            self.cell = None
        elif tag == "tr":
            cells = self.row or []
            self.row = None
            self.out.append("| " + " | ".join(cells) + " |\n")
            if self.in_thead:
                self.thead_rows += 1
        elif tag == "thead":
            self.in_thead = False
            if self.thead_rows:
                n = self.out[-1].count("|") - 1 if self.out else 0
                self.out.append("|" + "|".join(["---"] * max(n, 1)) + "|\n")
        elif tag == "pre":
            self.in_pre = max(0, self.in_pre - 1)
            self._emit("\n\n")
        elif tag in _BLOCK_END and _BLOCK_END[tag]:
            self._emit(_BLOCK_END[tag])

    def handle_data(self, data):
        if self.in_pre:
            self._emit(data)
            return
        if not data.strip():
            # whitespace between blocks is layout, inside a line it is a space
            if self.cell is None and self._at_line_start():
                return
            if self.cell is None and self.out and self.out[-1].endswith(" "):
                return
            self._emit(" ")
            return
        if self.cell is not None:
            data = re.sub(r"\s+", " ", data)
        else:
            # a soft line break inside a paragraph (markdown kept it as "\n") is a
            # line boundary to our parsers: four legacy notes have a table row
            # written straight under a sentence, and joining them hid the row
            data = re.sub(r"[ \t\r\f\v]*\n\s*", "\n", data)
            data = re.sub(r"[ \t\r\f\v]+", " ", data)
        if self.cell is None and self._at_line_start():
            data = data.lstrip()
        self._emit(data)


def html_to_text(h):
    """The plain text of a 1.6 note.  Markdown emphasis is dropped; structure kept."""
    if not h:
        return ""
    if "<" not in h:
        return _html.unescape(h).strip()
    p = _ToText()
    p.feed(h)
    p.close()
    text = "".join(p.out)
    text = "\n".join(line.rstrip() for line in text.splitlines())
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def text_to_html(text):
    """Plain/markdown text -> HTML, exactly the way the 1.6 migration converted legacy notes."""
    import markdown
    from django.conf import settings
    try:
        cfg = settings.MARKDOWNIFY["default"]
    except (AttributeError, KeyError):
        cfg = {}
    return markdown.markdown(
        text or "",
        extensions=cfg.get("MARKDOWN_EXTENSIONS", []),
        extension_configs=cfg.get("MARKDOWN_EXTENSION_CONFIGS", {}),
        output_format="html",
    )


# ----------------------------------------------------------------------------- read

def primary_note(obj):
    """The 1.6 primary Note row for obj (or the oldest note when none is flagged), else None."""
    from django.contrib.contenttypes.models import ContentType
    from common.models import Note
    ct = ContentType.objects.get_for_model(type(obj))
    qs = Note.objects.filter(model_type=ct, model_id=obj.pk, template=False)
    return qs.filter(primary=True).first() or qs.order_by("pk").first()


def note_html(obj):
    """Raw stored form: markdown on 1.5, HTML on 1.6."""
    if not is_v16():
        return obj.notes or ""
    n = primary_note(obj)
    return (n.content or "") if n else ""


def note_text(obj):
    """What a reader of the object's notes sees, as plain text.  '' when there is none."""
    if not is_v16():
        return obj.notes or ""
    return html_to_text(note_html(obj))


# ----------------------------------------------------------------------------- write

def _write_15(obj, text):
    model = type(obj)
    model.objects.filter(pk=obj.pk).update(notes=text)
    chk = model.objects.get(pk=obj.pk)
    if (chk.notes or "") != text:
        raise RuntimeError(f"{model.__name__} #{obj.pk}: notes write did not land")
    obj.notes = text
    return chk.notes


def _write_16_html(obj, new_html, user=None):
    from django.contrib.contenttypes.models import ContentType
    from common.models import Note
    n = primary_note(obj)
    if n is None:
        n = Note(model_type=ContentType.objects.get_for_model(type(obj)), model_id=obj.pk,
                 title="Note", primary=True)
    n.content = new_html
    if user is not None and hasattr(n, "updated_by"):
        n.updated_by = user
    n.clean()                       # nh3 sanitize, same as the API path
    n.save()
    chk = Note.objects.get(pk=n.pk)
    return chk.content or ""


def note_set(obj, text, user=None):
    """Replace the whole note with ``text``.  Returns the stored text (plain)."""
    if not is_v16():
        return _write_15(obj, text)
    stored = _write_16_html(obj, text_to_html(text), user)
    got = html_to_text(stored)
    want = html_to_text(text_to_html(text))
    if got != want:
        raise RuntimeError(f"{type(obj).__name__} #{obj.pk}: note write did not land\n want {want!r}\n got {got!r}")
    return got


def note_prepend(obj, text, user=None, sep="\n\n"):
    """Put ``text`` in front of the existing note (a new first paragraph on 1.6)."""
    if not is_v16():
        cur = obj.notes or ""
        return _write_15(obj, (text + (sep + cur if cur.strip() else "")).strip())
    cur = note_html(obj)
    new = text_to_html(text) + ("\n" + cur if cur.strip() else "")
    stored = _write_16_html(obj, new, user)
    got = html_to_text(stored)
    if not got.startswith(html_to_text(text_to_html(text))[:40]):
        raise RuntimeError(f"{type(obj).__name__} #{obj.pk}: prepend did not land: {got[:120]!r}")
    return got


def note_append(obj, text, user=None, sep="\n\n"):
    """Put ``text`` after the existing note (a new last paragraph on 1.6)."""
    if not is_v16():
        cur = (obj.notes or "").rstrip()
        return _write_15(obj, ((cur + sep) if cur else "") + text)
    cur = note_html(obj)
    new = (cur + "\n" if cur.strip() else "") + text_to_html(text)
    stored = _write_16_html(obj, new, user)
    got = html_to_text(stored)
    probe = html_to_text(text_to_html(text))[:40]
    if probe not in got:
        raise RuntimeError(f"{type(obj).__name__} #{obj.pk}: append did not land: {got[-160:]!r}")
    return got


# ----------------------------------------------------------------------------- query

def filter_notes(qs, prefix=None, contains=None, nonempty=False):
    """Narrow a queryset of note-carrying objects by their (primary) note text.

    prefix   : the note TEXT starts with this (case-insensitive) -- e.g. '[ESTIMATE]'.
               On 1.6 that is the first paragraph's text, so '<p>[ESTIMATE]' and NOT
               '[ESTIMATE]' anywhere in the note: the substring test has been run on
               this database before and returned a confident wrong number.
    contains : the note contains this text anywhere.
    nonempty : the object has a non-empty note at all.
    """
    if not is_v16():
        if prefix is not None:
            qs = qs.filter(notes__istartswith=prefix)
        if contains is not None:
            qs = qs.filter(notes__icontains=contains)
        if nonempty:
            qs = qs.exclude(notes="").exclude(notes__isnull=True)
        return qs
    if prefix is not None:
        pat = r"^\s*(<p[^>]*>\s*)?" + re.escape(_html.escape(prefix, quote=False))
        qs = qs.filter(notes_list__primary=True, notes_list__content__iregex=pat)
    if contains is not None:
        qs = qs.filter(notes_list__primary=True,
                       notes_list__content__icontains=_html.escape(contains, quote=False))
    if nonempty:
        qs = qs.filter(notes_list__primary=True).exclude(notes_list__content="")
    return qs.distinct()
