"""Print part labels on the QL-810W through the CUPS plugin.

There was no scripted path to this: `make_location_labels.py` covers Avery
sheets for locations, and everything else went through the InvenTree UI. Filing
a drawer means printing a label per bag, so it needs one command.

    itq run scripts/print_part_label.py 697 696          # render only, no print
    itq run scripts/print_part_label.py 697 696 --print

Default is render-only on purpose. LABELLING.md's standing rule is *look at the
rendered output before printing* — every label failure in this shop passed an
automated check and was caught by eye. `--render-only` writes PDFs to /tmp on
the server; pull them with `itq pull` and actually look.

Templates (see LABELLING.md for why they are 62mm and not the stock 50mm):
  11  Shop Part 62mm (QR + Text)        default here
  12  Shop Stock Item 62mm (QR + Text)  --stockitem, takes StockItem pks
"""
import argparse, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from report.models import LabelTemplate
from part.models import Part
from stock.models import StockItem, StockLocation
from plugin.registry import registry

ap = argparse.ArgumentParser()
ap.add_argument("pks", nargs="+", type=int)
ap.add_argument("--print", dest="do_print", action="store_true",
                help="actually send to the printer; default renders only")
ap.add_argument("--location", action="store_true",
                help="pks are StockLocation ids; uses template 9 (62x25mm). Bins and "
                     "boxes take the taller label; drawers use 10, the 16mm compact, "
                     "which is sized to the Avery scale already on the bin wall.")
ap.add_argument("--stockitem", action="store_true",
                help="pks are StockItem ids, use the stock item template")
ap.add_argument("--template", type=int, default=None)
ap.add_argument("--compact", action="store_true",
                help="with --location, use the 16mm compact template instead of 25mm")
a = ap.parse_args()

tpl_pk = a.template or (10 if getattr(a, 'location', False) and a.compact
                        else 9 if getattr(a, 'location', False)
                        else 12 if a.stockitem else 11)
model = StockLocation if a.location else StockItem if a.stockitem else Part
t = LabelTemplate.objects.get(pk=tpl_pk)
print(f"template: {t.name}  {t.width}x{t.height}mm")

plug = None
if a.do_print:
    plug = registry.get_plugin("cupslabel")
    if plug is None or not plug.is_active():
        print("cupslabel plugin is not active — refusing to print")
        sys.exit(1)
    print(f"queue: {plug.get_setting('QUEUE')}")

fail = 0
for pk in a.pks:
    obj = model.objects.filter(pk=pk).first()
    if obj is None:
        print(f"  #{pk}: no such {model.__name__}")
        fail += 1
        continue

    label = getattr(obj, "name", None) or str(obj)
    pdf = t.render(obj)

    if not a.do_print:
        kind = 'loc' if a.location else 'si' if a.stockitem else 'part'
        out = f"/tmp/label_{kind}_{pk}.pdf"
        with open(out, "wb") as fh:
            fh.write(pdf)
        print(f"  #{pk} {label[:34]:34} -> {out} ({len(pdf)} bytes)")
        continue

    try:
        res = plug.print_label(pdf_data=pdf, width=t.width, height=t.height,
                               filename=f"{label}.pdf")
        print(f"  #{pk} {label[:34]:34} -> {res}")
    except Exception as exc:
        # A print that fails must not look like one that worked. This printer
        # has a history of accepting jobs and silently doing nothing, so a
        # visible failure is the only honest signal available.
        print(f"  #{pk} {label[:34]:34} -> FAILED: {exc}")
        fail += 1

if not a.do_print:
    print("\nRENDER ONLY — pull the PDFs and look at them, then re-run with --print")
if fail:
    sys.exit(1)
