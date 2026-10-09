"""Tool records for the 1100MX: the TOOL is the cutter, numbered as Fusion and PathPilot
number it; the holder is an optional attribute of the tool.

Scott, 2026-10-08: "the tool number is the cutter, that's how fusion does it and how
pathpilot does it, the holder could and should be an optional attribute but is not the
identity of the tool."  And a cutter may carry two numbers (roughing and finishing
entries for the same physical cutter), so numbers are a LIST and a number on two
cutters is a WARNING, never an error ("dont make that impossible").

Record shape on this install (InvenTree 1.5.5):

  * A tool is one qty-1 StockItem of a cutter part, split off the part's counted row
    when the cutter goes into service.  Its tool numbers are TAGS (`T7`, `T17`):
    stock items have no parameters in 1.5.5 (no InvenTreeParameterMixin on StockItem,
    probed 2026-10-08), and tags are visible, filterable, multi-valued and non-unique,
    which is exactly the contract above.  The QR on the tag label is the item's own
    barcode (`INV-SI<pk>`), so the InvenTree app, a phone camera and the later
    tool-check app all resolve it.
  * The holder is a qty-1 split of the holder part's rack row, INSTALLED into the tool
    item (`belongs_to`), the same mechanism as the pull studs already fitted in the
    shrink-fit holders.  Holders are interchangeable within a part, so they carry no
    serial: `unfit` merges the holder back into the rack row.  A stud installed in the
    source holder row comes along (split 1, re-parented) and goes back the same way.
  * A bare cutter in a drawer with no T number is plain stock, not a tool.
  * Replacing a worn cutter (`replace`) keeps the old item as history: status DESTROYED,
    quantity 0, delete_on_deplete False -- because depleting a row DELETES it on this
    install (TRAPS "Counting a row to zero DELETES it").  The tags and the holder move
    to a fresh split of the same part; the label must be reprinted because the QR is a
    new pk.
  * Reorder = SupplierPart.link (audited, not rewritten).  Speeds & feeds = an
    Attachment with a link on the cutter PART, comment starting "Speeds & feeds".

The Fusion tool library "Tormach 1100MX Unified" is the master list of T numbers (Scott,
2026-10-08: "Unified is going to be the master"); this mirrors it, never the reverse.  Labels are rendered on request only (memory: labels-print-on-request).

Usage (all mutate only with --commit; run via ~/code/scripts/itq):

  itq run scripts/tool_tag.py audit
  itq run scripts/tool_tag.py show T7
  itq run scripts/tool_tag.py new <cutter_part_pk> T7[,T17] [--holder <holder_part_pk>] [--note "..."] --commit
  itq run scripts/tool_tag.py set <stock_pk|T7> T7,T17 --commit        # replace the list
  itq run scripts/tool_tag.py fit <stock_pk|T7> <holder_part_pk> --commit
  itq run scripts/tool_tag.py unfit <stock_pk|T7> --commit
  itq run scripts/tool_tag.py replace <stock_pk|T7> [--reason "..."] --commit
  itq run scripts/tool_tag.py scrap <stock_pk|T7> --reason "..." --commit  # no replacement
  itq run scripts/tool_tag.py sf <part_pk> <url> [--comment "..."] --commit  # speeds & feeds link
  itq run scripts/tool_tag.py sf <part_pk> none --commit                 # "none published"
  itq run scripts/tool_tag.py sf-batch /tmp/sf_links.tsv --commit        # part<TAB>url|none<TAB>comment per line
                                                                         # (itq push the file first; one SSH session, not 55)
"""
import argparse
import datetime as dt
import os
import re
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.contrib.auth import get_user_model          # noqa: E402
from django.contrib.contenttypes.models import ContentType  # noqa: E402

from common.models import Attachment                     # noqa: E402
from company.models import SupplierPart                  # noqa: E402
from part.models import Part, PartCategory               # noqa: E402
from stock.models import StockItem, StockLocation        # noqa: E402
from stock.status_codes import StockStatus               # noqa: E402

RACK_PK = 423          # SLN/Machine Shop/Toolholder Rack
HOLDER_CATS = (44, 84)  # Tooling/Holders, Tooling/Toolholders/BT30
CUTTER_ROOTS = (42, 45, 73)  # Tooling/Endmills, Tooling/Drills & Taps, Tooling/Cutting Tools (+children)
# speeds & feeds are expected only for rotating cutters a T number can land on; not taps, inserts, turning tools
SF_CATS = (42, 74, 75, 76, 77, 78, 79, 81, 90, 100)
TNUM = re.compile(r"^T\d{1,3}$")
SF_PREFIX = "Speeds & feeds"
SF_NONE = "Speeds & feeds: none"   # comment prefix of a "no chart published" record (link = vendor page checked)
TODAY = dt.date.today().isoformat()
USER = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()


# ----------------------------------------------------------------- helpers
def die(msg):
    print(f"!! {msg}")
    raise SystemExit(1)


def cutter_cats():
    pks = set()
    for root in CUTTER_ROOTS:
        c = PartCategory.objects.get(pk=root)
        pks.add(c.pk)
        pks.update(PartCategory.objects.filter(pathstring__startswith=c.pathstring + "/").values_list("pk", flat=True))
    return pks


def tool_items():
    """Stock items carrying at least one T-number tag."""
    seen = {}
    for s in StockItem.objects.exclude(tags=None).select_related("part", "location"):
        nums = tool_numbers(s)
        if nums:
            seen[s.pk] = s
    return list(seen.values())


def tool_numbers(s):
    return sorted((t.name for t in s.tags.all() if TNUM.match(t.name)), key=lambda x: int(x[1:]))


def parse_numbers(text):
    nums = [n.strip().upper() for n in text.split(",") if n.strip()]
    for n in nums:
        if not TNUM.match(n):
            die(f"{n!r} is not a tool number (T1..T999)")
    return sorted(set(nums), key=lambda x: int(x[1:]))


def resolve(ref):
    """<stock pk> or T<n> -> the tool StockItem."""
    if TNUM.match(ref.upper()):
        hits = [s for s in tool_items() if ref.upper() in tool_numbers(s)]
        if not hits:
            die(f"no tool carries {ref.upper()}")
        if len(hits) > 1:
            print(f"?? {ref.upper()} is on {len(hits)} items: {[h.pk for h in hits]} -- give the stock pk instead")
            raise SystemExit(1)
        return hits[0]
    return StockItem.objects.get(pk=int(ref))


def url(s):
    return f"http://192.168.50.10:8001/web/stock/item/{s.pk}"


def holder_of(s):
    hs = [c for c in s.installed_parts.all() if c.part.category_id in HOLDER_CATS and "stud" not in c.part.name.lower()]
    return hs[0] if hs else None


def describe(s):
    nums = ",".join(tool_numbers(s)) or "-"
    h = holder_of(s)
    htxt = f"holder #{h.pk} {h.part.name}" if h else "no holder"
    loc = s.location.pathstring if s.location else "-"
    return (f"#{s.pk} [{nums}] {s.part.name[:60]} qty={s.quantity:g} status={StockStatus(s.status).label} "
            f"@ {loc} | {htxt} | {url(s)}")


def warn_shared(nums, exclude_pk=None):
    for s in tool_items():
        if s.pk == exclude_pk:
            continue
        shared = set(nums) & set(tool_numbers(s))
        if shared:
            print(f"?? WARNING {','.join(sorted(shared))} already on #{s.pk} {s.part.name[:50]} -- allowed, check it is intended")


def counted_row(part, location):
    """The part's single un-serialized, un-installed row at a location (one row per part per location)."""
    rows = list(StockItem.objects.filter(part=part, location=location, belongs_to=None, quantity__gt=0,
                                         serial__isnull=True).order_by("pk"))
    rows += list(StockItem.objects.filter(part=part, location=location, belongs_to=None, quantity__gt=0,
                                          serial="").order_by("pk"))
    rows = list({r.pk: r for r in rows}.values())
    return rows


def set_tags(s, nums):
    s.tags.set(nums)
    chk = StockItem.objects.get(pk=s.pk)
    got = tool_numbers(chk)
    assert got == list(nums), f"tags did not stick: wanted {nums} got {got}"
    return chk


def split_one(row, note):
    new = row.splitStock(1, row.location, USER, notes=note)
    assert new is not None and new.pk != row.pk, "splitStock returned nothing"
    chk = StockItem.objects.get(pk=new.pk)
    assert float(chk.quantity) == 1.0, f"split qty {chk.quantity}"
    return chk


def install(child, parent, note):
    parent.installStockItem(child, 1, USER, note)
    chk = StockItem.objects.get(pk=child.pk)
    assert chk.belongs_to_id == parent.pk, f"belongs_to did not stick on #{child.pk}"
    return chk


def fit_holder(tool, holder_part, note):
    """Split one holder off its rack row (plus one installed stud if the row has them) and install it in the tool."""
    rows = counted_row(holder_part, StockLocation.objects.get(pk=RACK_PK))
    if not rows:
        die(f"no counted row of {holder_part.name} on the Toolholder Rack")
    if len(rows) > 1:
        print(f"-- {len(rows)} rows of {holder_part.name} on the rack ({[r.pk for r in rows]}); taking the oldest, #{rows[0].pk}")
    row = rows[0]
    if float(row.quantity) == 1.0:
        holder = row
        print(f"   holder row #{row.pk} is the last one; installing the row itself (no split)")
    else:
        holder = split_one(row, f"split 1 for tool #{tool.pk} ({note})")
        print(f"OK split holder #{holder.pk} off row #{row.pk} (row now {StockItem.objects.get(pk=row.pk).quantity:g})")
        # bring one pull stud along if the source row has studs installed
        for stud in list(row.installed_parts.all()):
            if float(stud.quantity) >= 1:
                s1 = stud if float(stud.quantity) == 1.0 else split_one(stud, f"stud follows holder #{holder.pk}")
                StockItem.objects.filter(pk=s1.pk).update(belongs_to=holder)
                assert StockItem.objects.get(pk=s1.pk).belongs_to_id == holder.pk
                print(f"OK stud #{s1.pk} re-parented to holder #{holder.pk}")
                break
    holder = install(holder, tool, note)
    print(f"OK holder #{holder.pk} {holder_part.name[:50]} installed in tool #{tool.pk}")
    return holder


def unfit_holder(tool, note):
    h = holder_of(tool)
    if not h:
        print("-- no holder fitted")
        return
    rack = StockLocation.objects.get(pk=RACK_PK)
    h.uninstall_into_location(rack, USER, note)
    h = StockItem.objects.get(pk=h.pk)
    assert h.belongs_to_id is None and h.location_id == RACK_PK, "uninstall did not stick"
    print(f"OK holder #{h.pk} uninstalled to {rack.pathstring}")
    # merge back into the rack row (holders of one part are interchangeable)
    rows = [r for r in counted_row(h.part, rack) if r.pk != h.pk]
    if rows:
        tgt = rows[0]
        # studs: merge the holder's stud into the row's stud, or re-parent it
        for stud in list(h.installed_parts.all()):
            row_studs = [x for x in tgt.installed_parts.all() if x.part_id == stud.part_id]
            if row_studs:
                row_studs[0].merge_stock_items([stud], user=USER, notes=note, raise_error=True)
                print(f"OK stud #{stud.pk} merged into #{row_studs[0].pk}")
            else:
                StockItem.objects.filter(pk=stud.pk).update(belongs_to=tgt)
                print(f"OK stud #{stud.pk} re-parented to row #{tgt.pk}")
        before = float(tgt.quantity)
        tgt.merge_stock_items([h], user=USER, notes=note, raise_error=True)
        chk = StockItem.objects.get(pk=tgt.pk)
        assert float(chk.quantity) == before + 1, f"merge qty {chk.quantity}"
        assert not StockItem.objects.filter(pk=h.pk).exists(), "merged holder row still exists"
        print(f"OK holder merged back into row #{tgt.pk} (now {chk.quantity:g})")
    else:
        print(f"-- no other row of {h.part.name[:40]} on the rack; #{h.pk} stays as the row")


def retire(tool, reason, status):
    """Keep the row as history: status, qty 0, delete_on_deplete False, tags removed."""
    StockItem.objects.filter(pk=tool.pk).update(delete_on_deplete=False, status=status)
    tool = StockItem.objects.get(pk=tool.pk)
    assert tool.delete_on_deplete is False and tool.status == status
    nums = tool_numbers(tool)
    tool.tags.clear()
    note = f"{TODAY} RETIRED ({StockStatus(status).label}) was {','.join(nums) or 'untagged'}: {reason}"
    tool.notes = ((tool.notes or "") + "\n" + note).strip()
    tool.save()
    tool.updateQuantity(0)
    chk = StockItem.objects.get(pk=tool.pk)  # must still exist
    assert float(chk.quantity) == 0 and chk.status == status and note in (chk.notes or ""), "retire did not stick"
    print(f"OK tool #{chk.pk} retired: {StockStatus(status).label}, qty 0, row kept, numbers {','.join(nums) or '-'} released")
    return nums


# ----------------------------------------------------------------- commands
def cmd_audit(a):
    tools = tool_items()
    print(f"== tools ({len(tools)}) ==")
    by_num = {}
    for s in sorted(tools, key=lambda s: int(tool_numbers(s)[0][1:])):
        print("  " + describe(s))
        for n in tool_numbers(s):
            by_num.setdefault(n, []).append(s.pk)
    shared = {n: p for n, p in by_num.items() if len(p) > 1}
    print(f"\n== shared numbers ({len(shared)}) ==")
    for n, p in shared.items():
        print(f"  ?? {n} on {p}")
    cc = cutter_cats()
    cutters = Part.objects.filter(category_id__in=cc, active=True).order_by("name")
    holders = Part.objects.filter(category_id__in=HOLDER_CATS, active=True, name__icontains="BT30").exclude(name__icontains="pull stud").order_by("name")
    print(f"\n== reorder links: cutters {cutters.count()}, holders {holders.count()} ==")
    for p in list(cutters) + list(holders):
        sps = list(SupplierPart.objects.filter(part=p))
        if not sps:
            print(f"  !! no supplier part: #{p.pk} {p.name[:60]} (stock {p.total_stock:g})")
        for sp in sps:
            if not sp.link:
                print(f"  !! supplier part without link: #{p.pk} {p.name[:50]} {sp.supplier.name} {sp.SKU}")
    print(f"\n== speeds & feeds attachments (cutter parts in stock) ==")
    ct = ContentType.objects.get_for_model(Part)
    missing, nopub = [], []
    for p in cutters:
        if p.total_stock <= 0 or p.category_id not in SF_CATS:
            continue
        atts = [x for x in Attachment.objects.filter(model_type=ct, model_id=p.pk) if (x.comment or "").startswith(SF_PREFIX)]
        if not atts:
            missing.append(p)
        elif atts[0].comment.startswith(SF_NONE):
            nopub.append((p, atts[0]))
        else:
            print(f"  ok #{p.pk} {p.name[:50]} -> {atts[0].link or atts[0].attachment.name} ({atts[0].comment})")
    for p, x in nopub:
        print(f"  -- no chart: #{p.pk} {p.name[:50]} ({x.comment[len(SF_PREFIX)+2:]})")
    for p in missing:
        print(f"  !! unchecked: #{p.pk} {p.name[:70]}")
    print(f"\n== holders on the rack ==")
    for p in holders:
        for r in StockItem.objects.filter(part=p, quantity__gt=0).order_by("pk"):
            where = f"in tool #{r.belongs_to_id}" if r.belongs_to_id else (r.location.pathstring if r.location else "-")
            print(f"  #{r.pk} {p.name[:55]} qty={r.quantity:g} {where}")
    print(f"\nAUDIT {'CLEAN' if not shared and not missing else 'FINDINGS'}: {len(tools)} tools, {len(shared)} shared numbers, {len(missing)} cutter parts with no speeds & feeds record ({len(nopub)} recorded as none published)")


def cmd_show(a):
    s = resolve(a.ref)
    print(describe(s))
    for c in s.installed_parts.all():
        print(f"   contains #{c.pk} {c.part.name[:60]} qty={c.quantity:g}")
        for g in c.installed_parts.all():
            print(f"      contains #{g.pk} {g.part.name[:60]} qty={g.quantity:g}")
    print(f"   barcode {s.format_barcode()}")
    print(f"   notes: {(s.notes or '')[:300]!r}")


def cmd_new(a):
    part = Part.objects.get(pk=a.part)
    if part.category_id not in cutter_cats():
        print(f"?? #{part.pk} is in {part.category.pathstring}, not a cutter category -- continuing")
    nums = parse_numbers(a.numbers)
    warn_shared(nums)
    rows = [r for r in StockItem.objects.filter(part=part, belongs_to=None, quantity__gt=0).order_by("pk") if not r.serialized]
    if not rows:
        die(f"no stock of {part.name} to put into service")
    row = rows[0]
    hp = Part.objects.get(pk=a.holder) if a.holder else None
    print(f"tool    {','.join(nums)} <- #{part.pk} {part.name}\nfrom    row #{row.pk} qty={row.quantity:g} @ {row.location.pathstring if row.location else '-'}")
    print(f"holder  {hp.name if hp else '(none)'}")
    if not a.commit:
        print("\nDRY RUN -- add --commit"); return
    note = a.note or f"into service {TODAY} as {','.join(nums)}"
    rack = StockLocation.objects.get(pk=RACK_PK)
    tool = row if float(row.quantity) == 1.0 else split_one(row, note)
    if tool.location_id != RACK_PK:
        tool.location = rack
        tool.save()
        assert StockItem.objects.get(pk=tool.pk).location_id == RACK_PK
    tool = set_tags(tool, nums)
    tool.notes = f"TOOL {','.join(nums)} -- {note}. Tool numbers are the tags; the Fusion tool library is the master list."
    tool.save()
    assert "TOOL" in StockItem.objects.get(pk=tool.pk).notes
    print(f"OK tool #{tool.pk} tagged {','.join(nums)} @ {rack.pathstring}")
    if hp:
        fit_holder(tool, hp, note)
    print("\n" + describe(StockItem.objects.get(pk=tool.pk)))
    print("SUCCESS")


def cmd_set(a):
    s = resolve(a.ref)
    nums = parse_numbers(a.numbers)
    warn_shared(nums, exclude_pk=s.pk)
    print(f"{describe(s)}\n  -> {','.join(nums)}")
    if not a.commit:
        print("\nDRY RUN -- add --commit"); return
    s = set_tags(s, nums)
    s.add_tracking_entry(99, USER, notes=f"tool numbers set to {','.join(nums)}")
    print("OK " + describe(s) + "\nSUCCESS")


def cmd_fit(a):
    s = resolve(a.ref)
    hp = Part.objects.get(pk=a.holder)
    if holder_of(s):
        die(f"tool #{s.pk} already has a holder; unfit first")
    print(f"{describe(s)}\n  fit holder {hp.name}")
    if not a.commit:
        print("\nDRY RUN -- add --commit"); return
    fit_holder(s, hp, f"fitted {TODAY} to tool #{s.pk} {','.join(tool_numbers(s))}")
    print(describe(StockItem.objects.get(pk=s.pk)) + "\nSUCCESS")


def cmd_unfit(a):
    s = resolve(a.ref)
    print(describe(s))
    if not a.commit:
        print("\nDRY RUN -- add --commit"); return
    unfit_holder(s, f"unfitted {TODAY} from tool #{s.pk}")
    print(describe(StockItem.objects.get(pk=s.pk)) + "\nSUCCESS")


def cmd_replace(a):
    old = resolve(a.ref)
    nums = tool_numbers(old)
    h = holder_of(old)
    rows = [r for r in StockItem.objects.filter(part=old.part, belongs_to=None, quantity__gt=0).exclude(pk=old.pk).order_by("pk") if not r.serialized]
    print(describe(old))
    print(f"  replace with a fresh {old.part.name[:50]} from {'row #%d qty=%g' % (rows[0].pk, rows[0].quantity) if rows else 'NOTHING -- no stock left'}")
    if not rows:
        die("no replacement stock; use scrap, then reorder")
    if not a.commit:
        print("\nDRY RUN -- add --commit"); return
    reason = a.reason or "worn/damaged, replaced"
    # move the holder across first so retire() never touches it
    new = rows[0] if float(rows[0].quantity) == 1.0 else split_one(rows[0], f"replacement for tool #{old.pk} {','.join(nums)}")
    if new.location_id != RACK_PK:
        new.location = StockLocation.objects.get(pk=RACK_PK); new.save()
    if h:
        h.uninstall_into_location(StockLocation.objects.get(pk=RACK_PK), USER, f"moved to replacement tool #{new.pk}")
        h = StockItem.objects.get(pk=h.pk)
        install(h, new, f"moved from retired tool #{old.pk}")
        print(f"OK holder #{h.pk} moved to #{new.pk}")
    retire(old, reason, StockStatus.DESTROYED.value)
    new = set_tags(new, nums)
    new.notes = f"TOOL {','.join(nums)} -- replaced #{old.pk} on {TODAY} ({reason}). Reprint the label: new QR."
    new.save()
    print(describe(StockItem.objects.get(pk=new.pk)) + "\nREPRINT the label for this tool (new QR)\nSUCCESS")


def cmd_scrap(a):
    s = resolve(a.ref)
    print(describe(s))
    if not a.reason:
        die("--reason is required")
    if not a.commit:
        print("\nDRY RUN -- add --commit"); return
    unfit_holder(s, f"tool #{s.pk} scrapped: {a.reason}")
    retire(s, a.reason, StockStatus.DESTROYED.value)
    print("SUCCESS")


def set_sf(part_pk, url_text, comment, commit):
    """One speeds & feeds link Attachment per cutter part (comment starts SF_PREFIX); updates in place."""
    p = Part.objects.get(pk=part_pk)
    ct = ContentType.objects.get_for_model(Part)
    existing = [x for x in Attachment.objects.filter(model_type=ct, model_id=p.pk) if (x.comment or "").startswith(SF_PREFIX)]
    none = url_text.lower() == "none"
    if none:
        # An Attachment must carry a file or a link (ValidationError "Missing external link", hit
        # 2026-10-08), so "none published" points at the vendor page where the absence was checked.
        pages = [sp.link for sp in SupplierPart.objects.filter(part=p) if sp.link]
        if not pages:
            die(f"#{p.pk}: 'none' needs a supplier part with a link to point at; give a URL instead")
        link = pages[0]
        comment = comment or f"{SF_PREFIX}: none published by the manufacturer ({TODAY})"
        if not comment.startswith(SF_NONE):
            die(f"#{p.pk}: a 'none' comment must start {SF_NONE!r} so the audit can tell it from a chart")
    else:
        link = url_text
        comment = comment or f"{SF_PREFIX} (mfg)"
        if not comment.startswith(SF_PREFIX):
            comment = f"{SF_PREFIX}: {comment}"   # the audit finds these by prefix; a free comment would hide the link from it
        if comment.startswith(SF_NONE):
            die(f"#{p.pk}: a chart link must not carry a 'none' comment")
    print(f"#{p.pk} {p.name[:60]}\n  existing: {[(x.link, x.comment) for x in existing]}\n  set: {link} | {comment}")
    if not commit:
        return
    if existing:
        x = existing[0]
        Attachment.objects.filter(pk=x.pk).update(link=link or "", comment=comment)
    else:
        x = Attachment(model_type=ct, model_id=p.pk, link=link or "", comment=comment, upload_user=USER)
        x.save()
    chk = Attachment.objects.get(pk=x.pk)
    assert (chk.link or None) == link and chk.comment == comment, "attachment did not stick"
    print(f"  OK attachment #{chk.pk}: {chk.link or '(no link)'}")


def cmd_sf(a):
    set_sf(a.part, a.url, a.comment, a.commit)
    print("SUCCESS" if a.commit else "\nDRY RUN -- add --commit")


def cmd_sf_batch(a):
    rows = []
    for n, line in enumerate(open(a.file, encoding="utf-8"), 1):
        line = line.rstrip("\n")
        if not line.strip() or line.startswith("#"):
            continue
        f = line.split("\t")
        if len(f) < 2:
            die(f"{a.file}:{n}: need part<TAB>url[<TAB>comment]")
        rows.append((int(f[0]), f[1].strip(), f[2].strip() if len(f) > 2 and f[2].strip() else None))
    for pk, u, c in rows:
        set_sf(pk, u, c, a.commit)
    print(f"{len(rows)} parts")
    print("SUCCESS" if a.commit else "\nDRY RUN -- add --commit")


ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
sub = ap.add_subparsers(dest="cmd", required=True)
sub.add_parser("audit")
x = sub.add_parser("show"); x.add_argument("ref")
x = sub.add_parser("new"); x.add_argument("part", type=int); x.add_argument("numbers"); x.add_argument("--holder", type=int); x.add_argument("--note"); x.add_argument("--commit", action="store_true")
x = sub.add_parser("set"); x.add_argument("ref"); x.add_argument("numbers"); x.add_argument("--commit", action="store_true")
x = sub.add_parser("fit"); x.add_argument("ref"); x.add_argument("holder", type=int); x.add_argument("--commit", action="store_true")
x = sub.add_parser("unfit"); x.add_argument("ref"); x.add_argument("--commit", action="store_true")
x = sub.add_parser("replace"); x.add_argument("ref"); x.add_argument("--reason"); x.add_argument("--commit", action="store_true")
x = sub.add_parser("scrap"); x.add_argument("ref"); x.add_argument("--reason"); x.add_argument("--commit", action="store_true")
x = sub.add_parser("sf"); x.add_argument("part", type=int); x.add_argument("url"); x.add_argument("--comment"); x.add_argument("--commit", action="store_true")
x = sub.add_parser("sf-batch"); x.add_argument("file"); x.add_argument("--commit", action="store_true")
args = ap.parse_args()
globals()[f"cmd_{args.cmd.replace('-', '_')}"](args)
