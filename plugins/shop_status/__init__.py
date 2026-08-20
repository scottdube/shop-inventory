"""Shop Status — dashboard widgets showing this shop's OPEN LOOPS.

Not inventory statistics ("you have 800 parts" is trivia) but the to-do list:
what arrived and needs a drawer, what the imports claim exists but nobody has
found, what is lost, what is on order, and how each project's parts are
tracking. All computed server-side and passed as context, so the JS is pure
rendering with no extra API round-trip.
"""

from django.utils.translation import gettext_lazy as _

from plugin import InvenTreePlugin
from plugin.mixins import UserInterfaceMixin

# Rows shown per section before the "N more" link. The widget scrolls, but
# what fits without scrolling is what actually gets acted on.
PREVIEW = 4


class ShopStatusPlugin(UserInterfaceMixin, InvenTreePlugin):
    NAME = 'ShopStatus'
    SLUG = 'shopstatus'
    TITLE = _('Shop Status')
    DESCRIPTION = _('Open loops: put-away queue, unfiled items, lost stock, orders, projects')
    VERSION = '1.1.0'
    AUTHOR = 'Scott Dube'

    def _rows(self, qs):
        """Stock rows. Links go to the STOCK ITEM, not the part — the action
        these rows exist for is 'give this thing a location'."""
        out = []
        for s in qs.select_related('part', 'location')[:PREVIEW]:
            out.append({
                'qty': f'{float(s.quantity):g}',
                'name': s.part.name[:60],
                'where': s.location.name if s.location else '—',
                'url': f'/web/stock/item/{s.pk}/',
            })
        return out

    def _loc_url(self, locations):
        """One location gets a deep link; several fall back to the stock index."""
        if len(locations) == 1:
            return f'/web/stock/location/{locations[0].pk}/'
        return '/web/stock/'

    def _to_order(self):
        """What needs buying, from three signals that fail in different ways.

        BUILD DEMAND is the one InvenTree's own Low Stock report structurally
        cannot see. Low Stock compares on-hand against minimum_stock, so a part
        with no minimum is never "low" however empty it gets — and only 14 of
        812 component parts here have a minimum set. That is why the dashboard
        stayed quiet while 500-odd parts sat at zero.

        BELOW MINIMUM is the restock floor: deliberate thresholds on things kept
        as spares rather than bought per project.

        ALREADY LISTED closes the loop, so a part does not keep nagging after it
        has been written down. Rows in the first two sections are marked when
        they are already on a pending order.

        Caveat worth knowing: demand comes from every build that is not complete
        or cancelled. A build left Pending after the thing was physically built
        keeps asking for its parts forever, so a stale build inflates this list.
        """
        from django.db.models import Sum

        from build.models import Build
        from order.models import PurchaseOrderLineItem
        from part.models import BomItem, Part
        from stock.models import StockItem

        # one query for every on-hand total, rather than one per part
        have = {pk: float(t or 0) for pk, t in StockItem.objects.values_list('part')
                .annotate(t=Sum('quantity'))}

        # parts already written down on a pending (not yet placed) order
        listed = set(PurchaseOrderLineItem.objects
                     .filter(order__status=10)
                     .values_list('part__part_id', flat=True))

        demand, blame = {}, {}
        for b in Build.objects.exclude(status__in=[30, 40]).select_related('part'):
            for bi in BomItem.objects.filter(part=b.part, optional=False):
                need = float(bi.quantity) * float(b.quantity)
                demand[bi.sub_part_id] = demand.get(bi.sub_part_id, 0) + need
                blame.setdefault(bi.sub_part_id, b.reference)

        def row(pk, name, gap, where):
            return {'qty': f'{gap:g}', 'name': name[:60],
                    'where': where, 'url': f'/web/part/{pk}/'}

        short = []
        for pk, need in demand.items():
            gap = need - have.get(pk, 0)
            if gap > 0:
                p = Part.objects.filter(pk=pk).first()
                if p and p.active:
                    tag = 'on list' if pk in listed else blame.get(pk, '')
                    short.append((gap, row(pk, p.name, gap, tag)))
        short.sort(key=lambda x: -x[0])

        floor = []
        for p in Part.objects.filter(active=True, minimum_stock__gt=0):
            gap = float(p.minimum_stock) - have.get(p.pk, 0)
            if gap > 0:
                tag = 'on list' if p.pk in listed else f'min {float(p.minimum_stock):g}'
                floor.append((gap, row(p.pk, p.name, gap, tag)))
        floor.sort(key=lambda x: -x[0])

        onlist = []
        for li in (PurchaseOrderLineItem.objects.filter(order__status=10)
                   .select_related('part__part', 'order')):
            p = li.part.part
            onlist.append({'qty': f'{float(li.quantity):g}', 'name': p.name[:60],
                           'where': li.order.reference[:14],
                           'url': f'/web/purchasing/purchase-order/{li.order.pk}/'})

        return {
            'short': [r for _, r in short[:PREVIEW]], 'short_n': len(short),
            'floor': [r for _, r in floor[:PREVIEW]], 'floor_n': len(floor),
            'listed': onlist[:PREVIEW], 'listed_n': len(onlist),
        }

    def _gather(self):
        from django.utils import timezone

        from build.models import Build, BuildLine
        from order.models import PurchaseOrder
        from part.models import Part
        from stock.models import StockItem, StockLocation

        try:
            from order.status_codes import PurchaseOrderStatus as POS
        except ImportError:
            from InvenTree.status_codes import PurchaseOrderStatus as POS

        recv = list(StockLocation.objects.filter(name='Receiving'))
        unfiled = list(StockLocation.objects.filter(name__istartswith='Unfiled'))

        recv_qs = StockItem.objects.filter(location__in=recv)
        unfiled_qs = StockItem.objects.filter(location__in=unfiled)
        lost_qs = StockItem.objects.filter(location__isnull=True)

        sections = [
            {
                'label': 'Put away — Receiving',
                'tone': 'warn',
                'n': recv_qs.count(),
                'items': self._rows(recv_qs),
                'url': self._loc_url(recv),
                'empty': 'Tote is empty.',
            },
            {
                'label': 'Find these — Unfiled',
                'tone': 'warn',
                'n': unfiled_qs.count(),
                'items': self._rows(unfiled_qs),
                'url': self._loc_url(unfiled),
                'empty': 'Nothing unaccounted for.',
            },
            {
                'label': 'Lost — no location',
                'tone': 'bad',
                'n': lost_qs.count(),
                'items': self._rows(lost_qs),
                'url': '/web/stock/',
                'empty': 'Everything has a home.',
            },
        ]

        builds = []
        for b in Build.objects.all().order_by('reference'):
            lines = BuildLine.objects.filter(build=b)
            builds.append({
                'ref': b.reference,
                'name': b.part.name[:44],
                'done': sum(1 for line in lines if line.allocations.exists()),
                'total': lines.count(),
                'pk': b.pk,
            })

        today = timezone.now().date()
        pos = []
        for po in PurchaseOrder.objects.filter(status=POS.PLACED.value).order_by('reference'):
            placed = po.issue_date or (po.creation_date if hasattr(po, 'creation_date') else None)
            age = f'{(today - placed).days}d' if placed else ''
            pos.append({
                'ref': po.reference,
                'desc': (po.description or po.supplier_reference or '')[:52],
                'age': age,
                'pk': po.pk,
            })

        parts = Part.objects.filter(active=True)
        return {
            'sections': sections,
            'pos': pos,
            'builds': builds,
            'order': self._to_order(),
            'stats': {
                'parts': parts.count(),
                'stock': StockItem.objects.count(),
                'uncounted': StockItem.objects.filter(stocktake_date__isnull=True).count(),
                'no_image': parts.filter(image='').count(),
                'no_keywords': parts.filter(keywords='').count(),
                'free_drawers': StockLocation.objects.filter(
                    description__istartswith='VERIFIED EMPTY').count(),
            },
        }

    def get_ui_dashboard_items(self, request, context, **kwargs):
        """Four widgets: the work queue, orders/projects, what to buy, the numbers."""
        try:
            data = self._gather()
        except Exception:
            import logging
            logging.getLogger('inventree').exception('ShopStatus: _gather failed')
            return []

        return [
            {
                'key': 'shop-status-queue',
                'title': _('Needs Attention'),
                'description': _('Put away, find, and lost items'),
                'icon': 'ti:alert-triangle:outline',
                'source': self.plugin_static_file('shop_status.js:renderQueue'),
                'context': data,
                'options': {'width': 6, 'height': 5},
            },
            {
                'key': 'shop-status-orders',
                'title': _('Orders & Projects'),
                'description': _('Open purchase orders and build progress'),
                'icon': 'ti:clipboard-list:outline',
                'source': self.plugin_static_file('shop_status.js:renderOrders'),
                'context': data,
                'options': {'width': 6, 'height': 5},
            },
            {
                'key': 'shop-status-toorder',
                'title': _('To Order'),
                'description': _('Short for builds, below minimum, already listed'),
                'icon': 'ti:shopping-cart:outline',
                'source': self.plugin_static_file('shop_status.js:renderToOrder'),
                'context': data,
                'options': {'width': 6, 'height': 5},
            },
            {
                'key': 'shop-status-numbers',
                'title': _('Catalog Health'),
                'description': _('Coverage of counts, images, keywords'),
                'icon': 'ti:chart-bar:outline',
                'source': self.plugin_static_file('shop_status.js:renderStats'),
                'context': data,
                'options': {'width': 12, 'height': 2},
            },
        ]
