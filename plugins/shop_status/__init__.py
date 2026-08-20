"""Shop Status — dashboard widgets and a part panel for this shop's OPEN LOOPS.

Not inventory statistics ("you have 800 parts" is trivia) but the to-do list:
what arrived and needs a drawer, what the imports claim exists but nobody has
found, what is lost, what is on order, and how each project's parts are
tracking. All computed server-side and passed as context, so the JS is pure
rendering with no extra API round-trip.

Also a "Where to Buy" panel on the part page, answering the question actually
asked standing at the bench with an empty drawer: where did this come from
last, and who else sells it.
"""

import re
from urllib.parse import quote

from django.utils.translation import gettext_lazy as _

from plugin import InvenTreePlugin
from plugin.mixins import UserInterfaceMixin

# Rows shown per section before the "N more" link. The widget scrolls, but
# what fits without scrolling is what actually gets acted on.
PREVIEW = 4

# Half this catalogue is machine tooling, where component distributors are dead
# weight — nobody looks up a boring bar on Octopart. Routing is by the part's
# ROOT category, because the tree splits cleanly at the top level and a single
# ancestor lookup is easy to retune later.
TOOLING_ROOTS = {'Tooling', 'Equipment', 'Shop', 'Tools', 'Materials', 'Pneumatic'}

# Aggregator first where there is one: it is the link that actually compares
# vendors. Amazon is in both sets because it is where this shop mostly buys.
VENDORS = {
    'electronics': [
        ('Octopart', 'https://octopart.com/search?q={q}'),
        ('LCSC', 'https://www.lcsc.com/search?q={q}'),
        ('DigiKey', 'https://www.digikey.com/en/products/result?keywords={q}'),
        ('Mouser', 'https://www.mouser.com/c/?q={q}'),
        ('Amazon', 'https://www.amazon.com/s?k={q}'),
    ],
    'tooling': [
        ('Shars', 'https://www.shars.com/catalogsearch/result/?q={q}'),
        ('Lakeshore', 'https://lakeshorecarbide.com/catalogsearch/result/?q={q}'),
        ('Haas', 'https://www.haastooling.com/search?q={q}'),
        ('MSC', 'https://www.mscdirect.com/browse/tn?searchterm={q}'),
        ('Tormach', 'https://tormach.com/catalogsearch/result/?q={q}'),
        ('Amazon', 'https://www.amazon.com/s?k={q}'),
    ],
}

# A part number worth searching: mixed letters and digits, no spaces.
# "MB10S", "2N7002", "AO3400A", "LM2596" pass; "Capacitor", "Resistor" do not.
PN = re.compile(r'^[A-Za-z0-9][A-Za-z0-9\-./]{2,24}$')



class ShopStatusPlugin(UserInterfaceMixin, InvenTreePlugin):
    NAME = 'ShopStatus'
    SLUG = 'shopstatus'
    TITLE = _('Shop Status')
    DESCRIPTION = _('Open loops: put-away queue, unfiled items, lost stock, orders, projects')
    VERSION = '1.2.0'
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

    def _vendor_set(self, part):
        """Which vendors to offer, from the part's ROOT category.

        Falls back to electronics for an unrecognised or missing root — that is
        the larger half of the catalogue, so an unclassified part is more likely
        a component than a boring bar.
        """
        cat = part.category
        if not cat:
            return 'electronics'
        root = cat.get_root() if hasattr(cat, 'get_root') else cat
        return 'tooling' if (root.name in TOOLING_ROOTS) else 'electronics'

    def _search_term(self, part):
        """What to search other vendors for, and how much to trust it.

        A real MPN is the only thing that finds the SAME component elsewhere, so
        it wins outright — but only 4 parts have one. Failing that, guess from
        the name: shop convention puts the part number first ("MB10S Bridge
        Rectifier ..."). If the first token is not part-number shaped, fall back
        to the opening words, which at least lands on a category.

        The caller shows which rule fired, so a 'guess' reads as a starting
        point rather than an answer.
        """
        from company.models import ManufacturerPart

        mp = ManufacturerPart.objects.filter(part=part).exclude(MPN='').first()
        if mp and mp.MPN:
            return mp.MPN, 'MPN'

        words = (part.name or '').split()
        first = words[0] if words else ''
        if PN.match(first) and any(c.isdigit() for c in first) \
                and any(c.isalpha() for c in first):
            return first, 'name'

        # Trailing punctuation is dead weight in a search box — shop names are
        # comma-separated spec lists, so a four-word slice usually ends on one.
        return ' '.join(words[:4]).strip(' ,.;:-'), 'guess'

    def _last_bought(self, part):
        """Most recent purchase — real orders first, notes table second.

        Most of this catalogue predates the purchase-order pipeline; its buying
        history is a markdown table the Amazon import wrote into Part.notes.
        Reading only PurchaseOrderLineItem would report "never bought" for
        hundreds of parts that plainly were.

        'src' says which source answered, so a note-derived price is never
        mistaken for a receipted one.
        """
        from order.models import PurchaseOrderLineItem

        # PLACED and COMPLETE only. A PENDING order is a shopping list — the
        # TO-ORDER list would otherwise report itself as the most recent
        # purchase, which is the opposite of the truth.
        best = None
        for li in (PurchaseOrderLineItem.objects
                   .filter(part__part=part, order__status__in=[20, 30])
                   .select_related('order', 'order__supplier')):
            o = li.order
            # issue_date is when it was ORDERED; creation_date is when the row
            # was typed in, which for back-filled history is months later and
            # would report the bookkeeping date as the purchase date.
            when = o.issue_date or o.complete_date
            approx = when is None
            if approx:
                when = o.creation_date
            if not when or (best and when <= best['sort']):
                continue
            best = {
                'sort': when,
                'when': str(when) + (' (recorded)' if approx else ''),
                'who': o.supplier.name if o.supplier else '—',
                'price': str(li.purchase_price) if li.purchase_price is not None else '',
                'ref': o.reference[:20],
                'url': f'/web/purchasing/purchase-order/{o.pk}/',
                'src': 'order',
            }
        if best:
            best.pop('sort')
            return best

        return self._parse_notes_history(part)

    @staticmethod
    def _parse_notes_history(part):
        """Read the markdown purchase table out of Part.notes.

        There is more than one table shape in this database and they disagree
        about column ORDER, so positions cannot be assumed:

            | Date | Qty | Unit | Line total | Order |      (Amazon import)
            | Date | Order | Qty | Unit |                   (Lakeshore etc.)
            | Date | Quote | Order | Qty | Unit |           (Tormach)

        Reading by position turned a $69.49 threadmill into "$1" — it had
        picked up the quantity column — and skipped the Tormach tables
        entirely because their order number is not numeric. So find the header
        and read by NAME.

        Among rows, the most recent one wins, except that a zero price loses to
        a real one: several parts carry a $0 replacement line dated after the
        actual purchase, and reporting $0 as the price paid is worse than
        reporting nothing.
        """
        notes = part.notes or ''
        who = 'unknown'
        m = re.search(r'##\s*Purchase history\s*\(([^)]+)\)', notes)
        if m:
            who = m.group(1).strip()[:22]

        cols, best = None, None
        for line in notes.splitlines():
            line = line.strip()
            if not line.startswith('|'):
                continue
            cells = [c.strip() for c in line.strip('|').split('|')]
            low = [c.lower() for c in cells]

            if cols is None:
                if 'date' in low:
                    cols = {name: low.index(name) for name in ('date', 'qty', 'unit')
                            if name in low}
                continue
            if set(''.join(cells)) <= set('-: '):
                continue                       # the |---|---| separator

            def cell(name):
                i = cols.get(name)
                return cells[i] if i is not None and i < len(cells) else ''

            when = cell('date')
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', when):
                continue
            raw = cell('unit').replace('$', '').replace(',', '').strip()
            try:
                amount = float(raw) if raw else 0.0
            except ValueError:
                amount = 0.0

            cand = {'when': when, 'amount': amount, 'qty': cell('qty') or '1'}
            if best is None \
                    or (cand['amount'] > 0 and best['amount'] == 0) \
                    or (when > best['when']
                        and not (cand['amount'] == 0 and best['amount'] > 0)):
                best = cand

        if not best:
            return None
        return {
            'when': best['when'],
            'who': who,
            'price': f'${best["amount"]:,.2f}' if best['amount'] else '',
            'ref': f'{best["qty"]} unit(s)',
            'url': '',
            'src': 'notes',
        }

    def _where_to_buy(self, part):
        from company.models import SupplierPart

        sups = [{
            'who': sp.supplier.name[:22],
            'sku': (sp.SKU or '')[:26],
            'url': sp.link or '',
        } for sp in (SupplierPart.objects.filter(part=part)
                     .select_related('supplier').order_by('supplier__name'))]

        # An assembly is built, not bought. Offering to shop for a Rat GDO is
        # noise, so the alternates block is suppressed rather than faked.
        if part.purchaseable:
            term, how = self._search_term(part)
            kind = self._vendor_set(part)
            alts = [{'who': n, 'url': u.format(q=quote(term))}
                    for n, u in VENDORS[kind]]
        else:
            term, how, kind, alts = '', 'notbuyable', '', []

        return {
            'last': self._last_bought(part),
            'sups': sups,
            'alts': alts,
            'term': term,
            'how': how,
            'kind': kind,
            'name': part.name[:70],
        }

    def get_ui_panels(self, request, context, **kwargs):
        """A 'Where to Buy' panel, on part pages only."""
        context = context or {}
        if context.get('target_model') != 'part':
            return []

        from part.models import Part

        try:
            part = Part.objects.get(pk=context.get('target_id'))
        except (Part.DoesNotExist, ValueError, TypeError):
            return []

        try:
            data = self._where_to_buy(part)
        except Exception:
            import logging
            logging.getLogger('inventree').exception(
                'ShopStatus: _where_to_buy failed for part %s', part.pk)
            return []

        return [{
            'key': 'shop-status-buy',
            'title': _('Where to Buy'),
            'icon': 'ti:shopping-bag:outline',
            'source': self.plugin_static_file('shop_status.js:renderBuy'),
            'context': data,
        }]

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
