"""Read-only: evidence on each side of the two duplicate tool pairs found 2026-11-04
(ATTEN ST-862D #445/#91, WG-026 leads #309/#85), so the merge keeps the record carrying
the evidence (merge_nozzle_86.py rule). Run: itq run scripts/tool_dupes_probe_1104.py"""
import os, sys
sys.path.insert(0, os.getcwd()); os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
import django; django.setup()
from django.contrib.contenttypes.models import ContentType
from part.models import Part, PartCategory
from common.models import Note, Attachment
from plugins.notes_compat import note_text
ct = ContentType.objects.get_for_model(Part)
for a, b in ((445, 91), (309, 85)):
    for pk in (a, b):
        p = Part.objects.select_related("category").get(pk=pk)
        sps = list(p.supplier_parts.all())
        lines = sum(sp.purchase_order_line_items.count() for sp in sps)
        print(f"#{pk} [{p.category.pathstring}] active={p.active} {p.name[:70]}")
        print(f"   IPN={p.IPN!r} image={'yes' if p.image else 'no'} kw={(p.keywords or '')[:60]!r} component={p.component}")
        print(f"   suppliers={[(sp.supplier.name, sp.SKU) for sp in sps]} po_lines={lines} stock={p.stock_items.count()}")
        print(f"   notes={Note.objects.filter(model_type=ct, model_id=pk).count()} "
              f"attach={Attachment.objects.filter(model_type='part', model_id=pk).count()} "
              f"bom_uses={p.used_in.count()} params={p.parameters_list.count() if hasattr(p, 'parameters_list') else '?'} "
              f"variants={p.get_descendants().count()}")
        print(f"   note: {note_text(p)[:160]!r}")
    print()
for name in ("Soldering", "Hand Tools", "Test Equipment"):
    print("cat", name, [(c.pk, c.pathstring) for c in PartCategory.objects.filter(name=name)])
print("cat Switches", [(c.pk, c.pathstring) for c in PartCategory.objects.filter(name="Switches")])
print("cat Prototyping", [(c.pk, c.pathstring) for c in PartCategory.objects.filter(name="Prototyping")])
