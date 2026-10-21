# InvenTree 1.6: notes moved to `common.Note` — how this shop reads and writes them

Written 2026-10-21 during the 1.5.8 → 1.6.1 port. Read this before touching
anything that stores a marker in a note (`[ESTIMATE]`, `binscan DATE: … COUNTED
at N by hand`, `TOOL n --`, `RECEIVED`, `CONSUMED BY:`, `## Purchase history`).

## What changed upstream (1.6.0, PR #11971)

- The `notes` column is gone from Part, StockItem, PurchaseOrder, Company,
  Build, ManufacturerPart, SupplierPart, ReturnOrder, SalesOrder,
  SalesOrderShipment (and the new TransferOrder never had one).
- Each object may own many `common.Note` rows (`model_type` ContentType FK +
  `model_id`); exactly one is `primary`. `content` is **HTML**, sanitized by
  nh3 in `clean()`. The web UI edits it with a Tiptap rich-text editor.
- Migration `common.0051` makes one primary note per non-empty legacy note:
  `content = sanitize(markdown_to_html(notes))` using the MARKDOWNIFY settings,
  so a markdown pipe table becomes a `<table>`, `**x**` becomes `<strong>`, and
  every blank-line paragraph becomes its own `<p>`.
- `obj.notes` is now a property returning a QuerySet (old code fails loudly on
  read); `obj.notes_list` is the GenericRelation.
- REST: `/api/note/` (filters `model_type` = "stockitem" / "part" / … or a
  ContentType id, `model_id`, `search`), `/api/note/<pk>/` PATCH `{content}`.
  Stock and Part serializers have **no `notes` field**: a POST that includes
  `notes` returns 201 and drops the key without a word (measured on the
  scratch copy: created row, zero notes).

## Decision: the markers stay as text at the start of the PRIMARY note

A marker is the first thing in the first `<p>` of the primary note, exactly
where the 1.5 text had it. Nothing moves to metadata or to a second Note row.

- **Read** through `html_to_text()` (plugins/notes_compat.py, twin copy in
  binscan/app.py): `<p>` → blank line, `<br>` → newline, `<h2>` → `## `,
  `<li>` → `- `, table rows → `| a | b |` with a `|---|` line after the
  header. Every existing parser (COUNTED_RE, the purchase-history table
  parser in shop_status, the CONSUMED BY line scanner) runs unchanged on that
  text. Emphasis is dropped, so `**x**` reads as `x`.
- **Write** by adding blocks, never by re-rendering what is there:
  `note_prepend` / `note_append` put a new `<p>` before or after the existing
  HTML; `note_set` replaces the whole note (only used on rows this code
  created). A McMaster import's table is therefore never flattened to text
  and rebuilt. BinScan's assign stamp (`_restamp_html`) works block by block:
  drops leading binscan stamps, drops the TRANSITIONAL paragraphs, rewrites
  `[ESTIMATE]` → `PURCHASE HISTORY (superseded by the count above):` inside
  the block, puts the new stamp first, and copies every other block byte for
  byte.
- **Query** a prefix with
  `notes_list__primary=True, notes_list__content__iregex=r"^\s*(<p[^>]*>\s*)?PREFIX"`
  and a substring with `content__icontains`; `filter_notes()` hides which
  one the server needs. On 1.5 the same calls become
  `notes__istartswith` / `notes__icontains`.
- **Version detection** is structural, not a version number: ORM side,
  "StockItem has no concrete `notes` field"; REST side, "a stock row has no
  `notes` key" (BinScan probes once from a real row and does not cache an
  unanswered probe).

One visible difference: on 1.5 `tool_tag.py set` prefixed the renumber line
into the same paragraph (`sep=" "`); on 1.6 it is its own paragraph. The
prefix query matches either.

## Rejected

- **One dedicated non-primary Note per marker** (a note titled "[ESTIMATE]",
  another titled "counted"). Clean to query, but it is a second record that
  must be kept consistent with the primary, BinScan's retire-on-count becomes
  a cross-endpoint delete, and the UI shows the primary note's body, which is
  where a human reads the flag today. Two records for one fact is how the
  pack-size-stored-twice trap started.
- **Metadata** (`StockItem.metadata["estimate"]`). Invisible to anyone reading
  the item page, and BinScan measured the `/stock/<pk>/metadata/` endpoint
  returning 403 in 2026-08; the notes channel was chosen then for being the
  only writable one, and 1.6 did not change that.
- **Re-rendering the whole note from text on every write** (text in, markdown
  out). Simplest code, but it turns a `<table>` into a pipe table that the
  1.6 editor shows as literal text, and loses any formatting a human added in
  the rich editor.

## Measured on the scratch copy (sqlite `.backup` of live, migrated 2026-10-21)

- migrate: 15 s. Note rows 2432 = live non-empty notes exactly (build 11,
  company 10, purchaseorder 182, part 1256, stockitem 973; the other five
  models 0).
- Fidelity after `html_to_text`: 0 missing; 0 mismatches on all seven marker
  checks (ESTIMATE prefix 282, COUNTED regex 89, TOOL prefix 1, RECEIVED 126,
  CONSUMED BY, binscan lead regex, purchase-table parse 492 of 525). 1232 of
  2432 notes byte-identical as text, 1685 identical as word sequences; the
  rest differ only in the `---:` table alignment markers and punctuation that
  dropped emphasis merged.
- shop_status purchase-parse fingerprint `0965ee953e3bceeffef13a1d85d00584`
  identical on live 1.5.8 and scratch 1.6.1.
- Round trips on scratch, all verified by re-read: BinScan assign (estimate
  → counted, TRANSITIONAL block dropped, purchase paragraph demoted), filepart,
  newpart (part note with `<strong>`, stock note), record; tool_tag renumber,
  deploy_po, sync_stocktake (13/13), plus prepend/append/set/create-on-empty
  through the ORM helper. One primary per object held throughout.
- Scripts whose dry runs print identically on both versions: sync_stocktake,
  unaccounted, tool_tag, receive_po, deploy_po.

## Traps found on the way

- Plugin keys are `shopstatus` and `cupslabel`, not the directory names.
- Port 8003 on the Mini is `com.shopstatus` (the standalone status page);
  8002 is BinScan. The scratch server runs on **8005**, scratch BinScan 8006.
- The REST user throttle is 60/second on both versions; a test script that
  reads a note per row in a tight loop gets 429. BinScan fetches the stock
  notes in bulk for list views and per row only for ≤3 rows.
- `ITQ_SCRATCH=16 itq run …` targets env16/src16/scratch16; without it,
  live.
