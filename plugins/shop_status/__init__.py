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
from plugin.mixins import SettingsMixin, UserInterfaceMixin

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



class ShopStatusPlugin(SettingsMixin, UserInterfaceMixin, InvenTreePlugin):
    NAME = 'ShopStatus'
    SLUG = 'shopstatus'
    TITLE = _('Shop Status')
    DESCRIPTION = _('Open loops: put-away queue, unfiled items, lost stock, orders, projects')
    VERSION = '1.3.0'
    AUTHOR = 'Scott Dube'

    # Targets live in settings because the gauge bugs write to them: you set a
    # goal by dragging it on the instrument you read it from, not by finding a
    # form. See docs/DASHBOARD.md.
    SETTINGS = {
        'TARGET_IMAGES': {
            'name': _('Target — image coverage'),
            'description': _('Where the bug sits on the IMAGES gauge (percent)'),
            'default': 95,
            'validator': [int],
        },
        'TARGET_COUNTED': {
            'name': _('Target — stock counted'),
            'description': _('Where the bug sits on the COUNTED gauge (percent)'),
            'default': 90,
            'validator': [int],
        },
        'TARGET_BINWALL': {
            'name': _('Target — bin wall walked'),
            'description': _('Where the bug sits on the BIN WALL gauge (percent)'),
            'default': 100,
            'validator': [int],
        },
        # Which lamps have been silenced, and at what count. Silencing is not
        # clearing: the lamp stays lit while the condition holds, it just stops
        # flashing. Storing the COUNT as well as the time is what makes the
        # lamp flash again when the condition changes rather than every morning.
        'ACK_STATE': {
            'name': _('Acknowledged lamps'),
            'description': _('JSON: lamp key -> {n, at}. Written by the panel.'),
            'default': '{}',
        },
        'PREFLIGHT_PATH': {
            'name': _('Vendor session state file'),
            'description': _('Written by the overnight sweep; source of the SOURCES tiles'),
            'default': '/Volumes/4TB_Removable/inventree/preflight_state.json',
        },
    }

    # A vendor reading older than this has aged out. A stale reading rendered as
    # a live one is the failure the OFF flag exists to prevent.
    PANEL_STALE_H = 24

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
        ds_have, ds_eligible = self._datasheet_coverage()
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
                # Counts only locations a HUMAN confirmed empty by eye. Not
                # "locations with no stock rows" — B3-R3C2 had zero rows and a
                # drawer full of ICs, so records are not evidence of emptiness.
                # The label says "confirmed empty" for that reason: this is a
                # coverage number, not a capacity number, and reading it as
                # capacity is how you get sent to fill an occupied drawer.
                'free_drawers': StockLocation.objects.filter(
                    description__istartswith='VERIFIED EMPTY').count(),
                'unchecked_drawers': self._unchecked_drawers(),
                'ds_have': ds_have,
                'ds_eligible': ds_eligible,
            },
        }

    # Eligibility must match scripts/datasheets.py:candidates(). Two
    # definitions of "could have a datasheet" would drift, and the number on a
    # dashboard is the one people trust.
    _DS_SKIP_CATS = {'Capacitors', 'Resistors', 'LEDs'}
    _DS_BAD = re.compile(r'["\u2033\']|\bmm\b|\bawg\b|\bpcs?\b|\bpack\b|\bkit\b|\bassort', re.I)
    _DS_MPN = re.compile(
        r'\b(?=[A-Z0-9][A-Z0-9\-]{3,})(?=[A-Z0-9\-]*[0-9])(?=[A-Z0-9\-]*[A-Z])'
        r'[A-Z][A-Z0-9]*[0-9][A-Z0-9\-]*\b')

    _DRAWER = re.compile(r'^[A-Z][0-9]+-R\d+C\d+$')

    def _binwall(self):
        """(walked, total) bin-wall drawers.

        WALKED means somebody has established what is in it: it holds stock
        rows, or a human wrote VERIFIED EMPTY on it. Records alone are not
        evidence of emptiness — B3-R3C2 had zero rows and a drawer full of ICs,
        which is why "no stock rows" counts as unknown, not as empty.
        """
        from stock.models import StockItem, StockLocation
        occupied = set(StockItem.objects.filter(location__isnull=False)
                       .values_list('location_id', flat=True))
        walked = total = 0
        for l in StockLocation.objects.all().only('pk', 'name', 'description'):
            if not self._DRAWER.match(l.name or ''):
                continue
            total += 1
            if l.pk in occupied or (l.description or '').upper().startswith('VERIFIED EMPTY'):
                walked += 1
        return walked, total

    def _unchecked_drawers(self):
        """Bin-wall drawers nobody has actually looked in."""
        walked, total = self._binwall()
        return total - walked

    def _datasheet_coverage(self):
        """(have, eligible) — NOT (missing, total).

        A bare "no datasheet" count would read 900+ and be meaningless: most of
        this catalogue is passives from assortment kits, hardware, and tooling,
        none of which has a datasheet to find. Reporting coverage against the
        set that COULD have one turns trivia into a to-do list, which is what
        this panel is for.
        """
        # Deliberately NOT wrapped in a bare `except: return 0, 0`. An earlier
        # version was, and it silently reported 0/0 when `Part` was simply not
        # imported in this scope — a broken tile that looked like an honest
        # "nothing eligible". Only the one expected, survivable condition is
        # caught: a shop with no Electronics category at all.
        from common.models import Attachment
        from part.models import Part, PartCategory
        try:
            root = PartCategory.objects.get(name='Electronics')
        except PartCategory.DoesNotExist:
            return 0, 0
        pool = Part.objects.filter(
            active=True,
            category__in=root.get_descendants(include_self=True))
        have_ids = set(Attachment.objects.filter(model_type='part')
                       .values_list('model_id', flat=True))
        have = eligible = 0
        for prt in pool.select_related('category').only('pk', 'name', 'category'):
            if prt.category and prt.category.name in self._DS_SKIP_CATS:
                continue
            head = prt.name.split(',')[0]
            if self._DS_BAD.search(head):
                continue
            m = self._DS_MPN.search(head.upper())
            if not (m and len(m.group()) >= 4):
                continue
            eligible += 1
            if prt.pk in have_ids:
                have += 1
        return have, eligible


    # ------------------------------------------------------------------
    # The instrument panel. docs/DASHBOARD.md carries the argument; the one
    # rule that shapes this code rather than the CSS is: a reading that cannot
    # be proved renders OFF — never zero, never green, never blank.
    # ------------------------------------------------------------------

    def _ack_map(self):
        import json
        try:
            return json.loads(self.get_setting('ACK_STATE') or '{}')
        except (ValueError, TypeError):
            # A corrupt ack map must not read as "everything is silenced".
            return {}

    @staticmethod
    def _when(dt):
        """A timestamp as a person reads it: time if today, else a date."""
        import datetime
        if not dt:
            return '--:--'
        now = datetime.datetime.now()
        if dt.date() == now.date():
            return dt.strftime('%H:%M today')
        if (now.date() - dt.date()).days == 1:
            return dt.strftime('%H:%M yesterday')
        return dt.strftime('%b %-d %H:%M')

    def _gauges(self):
        from part.models import Part
        from stock.models import StockItem

        def pct(a, b):
            return round(100.0 * a / b) if b else 0

        def target(key, fallback):
            try:
                return int(self.get_setting(key))
            except (TypeError, ValueError):
                return fallback

        rows = StockItem.objects.count()
        counted_qs = StockItem.objects.filter(stocktake_date__isnull=False)
        counted = counted_qs.count()
        oldest = (counted_qs.order_by('stocktake_date')
                  .values_list('stocktake_date', flat=True).first())
        if oldest:
            import datetime
            age = (datetime.date.today() - oldest).days
            fresh = f'oldest count {age}d old'
        else:
            fresh = 'no count on record'

        walked, drawers = self._binwall()

        act = Part.objects.filter(active=True)
        img_all = act.count()
        img_have = act.exclude(image='').exclude(image__isnull=True).count()

        return [
            {
                # OFF on purpose. Coverage is meant to run against the
                # REACHABLE denominator, and the reachable/ruled-out split is
                # the sweep's accumulated evidence, not a query this panel can
                # run. Rendering the raw 53% instead would be exactly the
                # misleading number the redesign threw out — and rendering the
                # remembered 96% would be worse, because nothing here can tell
                # whether that exclusion set still holds.
                'key': 'images', 'name': 'IMAGES',
                'off': 'reachable denominator not supplied',
                'value': None,
                'sub': f'{img_have} / {img_all} raw — not the real denominator',
                'note': 'ruled-out split still owed by the sweep',
                'fresh': '',
                'target': target('TARGET_IMAGES', 95),
                'setting': 'TARGET_IMAGES',
                'url': '/web/part/',
            },
            {
                'key': 'counted', 'name': 'COUNTED',
                'off': None,
                'value': pct(counted, rows),
                'sub': f'{counted} / {rows} stock rows',
                'note': f'{rows - counted} never counted',
                'fresh': fresh,
                'target': target('TARGET_COUNTED', 90),
                'setting': 'TARGET_COUNTED',
                'url': '/web/stock/',
            },
            {
                'key': 'binwall', 'name': 'BIN WALL',
                'off': None,
                'value': pct(walked, drawers),
                'sub': f'{walked} / {drawers} drawers',
                'note': f'{drawers - walked} never opened',
                'fresh': 'walked = holds stock, or verified empty by eye',
                'target': target('TARGET_BINWALL', 100),
                'setting': 'TARGET_BINWALL',
                'url': '/web/stock/',
            },
        ]

    def _lamps(self):
        """Nine lamps. Red where a failure makes another check lie, yellow
        where it is work waiting. That split, not severity, is the rule — see
        DASHBOARD.md: a null issue date did not produce a wrong aging number,
        it removed the row from aging entirely."""
        import datetime

        from part.models import Part
        from stock.models import StockItem, StockLocation
        from order.models import PurchaseOrder
        try:
            from order.status_codes import PurchaseOrderStatus as POS
        except ImportError:
            from InvenTree.status_codes import PurchaseOrderStatus as POS

        placed = PurchaseOrder.objects.filter(status=POS.PLACED.value)

        # [ESTIMATE] is a PREFIX on StockItem.notes, not a substring anywhere in
        # it, and not on Part.description. Both of those wrong tests have been
        # run here and both returned a confident wrong number.
        est = StockItem.objects.filter(notes__istartswith='[ESTIMATE]')

        recv = StockLocation.objects.filter(name='Receiving')
        unfiled = StockLocation.objects.filter(name__istartswith='Unfiled')

        # The tombstone markers do NOT share a severity, and the first version of
        # this lamp got that wrong: it lit red on 14 rows, 13 of which were
        # "POSSIBLE RETURN - verify", a deliberate to-do queue. A red lamp over a
        # to-do list is the cry-wolf failure this panel exists to avoid.
        #
        # The split follows the rule in DASHBOARD.md - does this failure make
        # another check LIE?
        #   MERGED into / NOT INVENTORY on an ACTIVE part: yes. A merged part
        #     still active can be counted twice, and a non-inventory row sits in
        #     every coverage denominator on this panel. Red.
        #   REFUNDED / POSSIBLE RETURN: no. Nothing is wrong yet; somebody has to
        #     go and look. Yellow.
        def _tombs(tags):
            qs = Part.objects.none()
            for tag in tags:
                qs = qs | Part.objects.filter(active=True, description__icontains=tag)
            return qs.distinct()

        ghost = _tombs(('MERGED into', 'NOT INVENTORY'))
        verify = _tombs(('REFUNDED', 'POSSIBLE RETURN')).exclude(
            pk__in=ghost.values_list('pk', flat=True))

        state, newest = self._preflight()
        stale_h = None
        if newest:
            stale_h = int((datetime.datetime.now() - newest).total_seconds() // 3600)

        lamps = [
            {'key': 'contradiction', 'tone': 'warning',
             'n': est.filter(stocktake_date__isnull=False).count(),
             'label': 'Row contradicts itself', 'url': '/web/stock/',
             'why': 'marked [ESTIMATE] and stocktake-stamped — clear the date, not the marker'},
            {'key': 'po_no_date', 'tone': 'warning',
             'n': placed.filter(issue_date__isnull=True).count(),
             'label': 'PO has no issue date', 'url': '/web/purchasing/index/purchaseorders/',
             'why': 'a null issue date drops the row out of aging entirely'},
            {'key': 'negative', 'tone': 'warning',
             'n': StockItem.objects.filter(quantity__lt=0).count(),
             'label': 'Negative stock', 'url': '/web/stock/',
             'why': 'a stock system that can go below zero is not counting'},
            {'key': 'tombstone', 'tone': 'warning',
             'n': ghost.count(),
             'label': 'Merged part still active', 'url': '/web/part/',
             'why': 'merged or not-inventory rows that can still be counted twice'},
            {'key': 'lost', 'tone': 'caution',
             'n': StockItem.objects.filter(location__isnull=True).count(),
             'label': 'Stock with no location', 'url': '/web/stock/',
             'why': 'somewhere in the shop, nowhere in the record'},
            {'key': 'putaway', 'tone': 'caution',
             'n': StockItem.objects.filter(location__in=recv).count(),
             'label': 'Waiting in Receiving', 'url': '/web/stock/',
             'why': 'arrived, not yet given a home'},
            {'key': 'unfiled', 'tone': 'caution',
             'n': StockItem.objects.filter(location__in=unfiled).count(),
             'label': 'Unfiled — find these', 'url': '/web/stock/',
             'why': 'the import says it exists; nobody has found it'},
            {'key': 'to_verify', 'tone': 'caution',
             'n': verify.count(),
             'label': 'Refund — verify these', 'url': '/web/part/',
             'why': 'an order containing this was refunded; nobody has looked yet'},
            {'key': 'po_open', 'tone': 'caution',
             'n': placed.count(),
             'label': 'PO placed, unreceived', 'url': '/web/purchasing/index/purchaseorders/',
             'why': 'money out, nothing on the shelf yet'},
        ]

        # The sweep's own liveness. OFF rather than 0 when the state file
        # cannot be read: "the job is fine" and "I cannot tell" must not render
        # the same, which is the whole argument of the fourth state.
        if stale_h is None:
            lamps.append({'key': 'sweep', 'tone': 'caution', 'n': None, 'off': True,
                          'label': 'Sweep check-in', 'url': '/web/part/',
                          'why': 'no readable session-state file — cannot tell if it ran'})
        else:
            lamps.append({'key': 'sweep', 'tone': 'caution',
                          'n': stale_h if stale_h >= self.PANEL_STALE_H else 0,
                          'unit': 'h',
                          'label': 'Sweep has not checked in', 'url': '/web/part/',
                          'why': f'last check-in {stale_h}h ago'})

        acks = self._ack_map()
        import datetime as _dt
        for lamp in lamps:
            rec = acks.get(lamp['key']) or {}
            lamp['ack'] = bool(rec) and rec.get('n') == lamp.get('n')
            lamp['ack_age'] = ''
            if lamp['ack'] and rec.get('at'):
                try:
                    at = _dt.datetime.fromisoformat(rec['at'])
                    days = (_dt.datetime.now() - at).days
                    # A lamp silenced for weeks is itself a signal, so the age
                    # is shown rather than just a tick.
                    lamp['ack_age'] = 'today' if days < 1 else f'{days}d'
                except ValueError:
                    pass
        return lamps

    def _preflight(self):
        """(state dict, newest check-in) from the sweep's session file."""
        import datetime
        import json
        path = self.get_setting('PREFLIGHT_PATH')
        try:
            with open(path) as fh:
                state = json.load(fh)
        except (OSError, ValueError):
            return {}, None
        if not isinstance(state, dict):
            return {}, None
        newest = None
        for rec in state.values():
            if not isinstance(rec, dict):
                continue
            try:
                seen = datetime.datetime.fromisoformat(rec.get('checked') or '')
            except (TypeError, ValueError):
                continue
            newest = seen if (newest is None or seen > newest) else newest
        return state, newest

    def _sources(self):
        """Last read that PROVED something — not the last time a job ran.

        Those two diverge exactly when something is wrong, which is why the
        proof line is shown and the run time is not.
        """
        import datetime

        state, _ = self._preflight()
        if not state:
            return [{'key': 'sweep', 'name': 'Vendor sessions', 'time': '--:--',
                     'proof': 'session-state file unreadable', 'off': True}]

        out = []
        for vendor in sorted(state):
            rec = state[vendor] if isinstance(state[vendor], dict) else {}
            st = (rec.get('state') or 'UNKNOWN').upper()
            try:
                checked = datetime.datetime.fromisoformat(rec.get('checked') or '')
            except (TypeError, ValueError):
                checked = None
            try:
                last_ok = datetime.datetime.fromisoformat(rec.get('last_ok') or '')
            except (TypeError, ValueError):
                last_ok = None

            stale = (checked is None
                     or (datetime.datetime.now() - checked).total_seconds()
                     > self.PANEL_STALE_H * 3600)

            if st == 'UNKNOWN' or stale:
                # No usable reading. A reading that has aged out is not a
                # reading; a needle parked on the last known value is a lie
                # with a timestamp.
                row = {'time': '--:--', 'off': True,
                       'proof': ('never proved' if checked is None
                                 else f'last checked {self._when(checked)} — aged out')}
            elif st == 'OUT':
                # A real reading that says "signed out". Not OFF: the probe
                # worked, the answer is bad news.
                row = {'time': self._when(checked), 'off': False, 'out': True,
                       'proof': f'signed out · last healthy {self._when(last_ok)}'}
            else:
                row = {'time': self._when(last_ok or checked), 'off': False,
                       'proof': 'session proved live'}
            row['key'] = vendor
            row['name'] = vendor.title()
            out.append(row)
        return out

    def _panel(self):
        import datetime
        return {
            'gauges': self._gauges(),
            'lamps': self._lamps(),
            'sources': self._sources(),
            'measured': datetime.datetime.now().strftime('%H:%M'),
            'stale_h': self.PANEL_STALE_H,
        }

    def get_ui_dashboard_items(self, request, context, **kwargs):
        """Five widgets: the instrument panel, then the work queue,
        orders/projects, what to buy, the numbers.

        The panel is computed in its own try. It is the new one and the four
        below have been right for weeks — a panel that throws must not take
        the working widgets down with it.
        """
        import logging

        try:
            data = self._gather()
        except Exception:
            logging.getLogger('inventree').exception('ShopStatus: _gather failed')
            return []

        items = []
        try:
            items.append({
                'key': 'shop-status-panel',
                'title': _('Instrument Panel'),
                'description': _('Coverage gauges, annunciator lamps, source tiles'),
                'icon': 'ti:gauge:outline',
                'source': self.plugin_static_file('shop_status.js:renderPanel'),
                'context': {'panel': self._panel()},
                'options': {'width': 12, 'height': 10},
            })
        except Exception:
            logging.getLogger('inventree').exception('ShopStatus: _panel failed')

        return items + [
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
