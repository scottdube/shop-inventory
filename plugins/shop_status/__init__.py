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

# A pack size stated in the name or description: "10 pcs", "pack of 50",
# "(10-pack)", "Set of (10)". If the record says a part comes in packs and
# nothing records the pack SIZE, then any price on it is one division away from
# being ten or fifty times wrong — booked per piece when it was paid per pack.
# 19 storage bins read $208.62 against a $21.96 spend before this was noticed by
# a human rather than by the panel.
PACK_SIZE = re.compile(
    r'\b(\d{2,4})\s*(?:x\s*)?(?:pcs?|pieces|pack|-pack)\b'
    r'|\bset of \((\d+)\)|\bpack of (\d+)\b|\((\d+)-pack\)', re.I)

# What each readout MEANS, shown on hover and on keyboard focus. These are part
# of the instrument, not decoration: a lamp whose meaning has to be remembered
# is a lamp that gets pressed without being read, and that is the failure mode
# this panel was built to avoid. Each one says what is counted and why it earns
# the colour it has.
GAUGE_TIPS = {
    'images': (
        'Parts carrying an image, over the parts an image could actually be '
        'fetched for. Reachable means it already has one, or it has a supplier '
        'part — the SKU is what an image is fetched from. Ruled out is the '
        'imageless rows with no supplier part on file: not unreachable forever, '
        'just nothing on record saying where to look. Computed live. This is '
        "NOT the overnight sweep's reachable set, which is still owed as data."),
    'counted': (
        'Stock rows carrying a stocktake date, over the rows actually IN STOCK. '
        'Rows installed in a finished device, consumed by a build or run to zero '
        'are excluded — they are not on a shelf to be counted, and leaving them '
        'in would make this gauge fall every time something gets built. A row '
        'with no date has never been counted by anybody — its quantity came from an '
        'invoice, a kit label or an estimate. The oldest-count line underneath '
        'is the only figure on this panel that gets worse while nothing else '
        'changes.'),
    'binwall': (
        'Bin-wall drawers where somebody has established what is inside: it '
        'holds stock rows, or a human wrote VERIFIED EMPTY on it. Records alone '
        'are not evidence of emptiness — B3-R3C2 had zero rows and a drawer '
        'full of ICs — so a drawer nobody has opened counts as unknown space, '
        'never as free space.'),
}

LAMP_TIPS = {
    'contradiction': (
        'Stock rows whose notes begin [ESTIMATE] and which also carry a '
        'stocktake date. An estimate is by definition unstamped, so the two '
        'together mean a reasoned guess is wearing a counted label. The fix is '
        'to clear the DATE, not the marker — the notes say never counted.'),
    'po_no_date': (
        'Purchase orders marked Placed with no issue date. Aging is computed '
        'from that date, so these rows do not age wrongly — they drop out of '
        'aging altogether. The alarm does not misfire, it stops existing, which '
        'is what makes this one red rather than yellow.'),
    'negative': (
        'Stock rows holding a quantity below zero. A stock system that can go '
        'negative is not counting, and every coverage figure on this panel is '
        'computed over these same rows.'),
    'tombstone': (
        'Active parts whose description BEGINS with MERGED into or NOT '
        'INVENTORY — the tombstone marker is a prefix, and the surviving record '
        'of a merge mentions it in prose, so a substring test lights this lamp '
        'on the wrong side of the merge. A '
        'merged part left active can be counted twice under two names, and a '
        'not-inventory row sits inside every denominator above.'),
    'lost': (
        'Rows that are in stock and have no location: the item is in the record '
        'and somewhere in the shop, but the record cannot say where, so it is '
        'invisible to a drawer walk and to every location count. Items installed '
        'in a device or consumed by a build are NOT counted here — installing is '
        'what removes the location, so they can never be filed and would keep '
        'this lamp lit forever.'),
    'putaway': (
        'Stock sitting in Receiving: arrived, recorded, not yet given a home. '
        'The shortest queue here and the one that goes stale fastest, because '
        'the box is usually still on the floor.'),
    'unfiled': (
        'Stock in an Unfiled location. An import claims these exist; nobody has '
        'put eyes on them. Unlike Receiving there is no box to point at — each '
        'one is a search.'),
    'to_verify': (
        'Active parts belonging to an order that was refunded. Nothing is known '
        'to be wrong: somebody has to decide whether the item was kept, '
        'returned, or never arrived. Yellow because it is a queue, not a fault.'),
    'pack_price': (
        'Priced stock whose part name or description states a pack size — "10 '
        'pcs", "pack of 50" — while no supplier part records what that pack '
        'contains. It is a question about the RECORD, not an accusation about '
        'the price: every row this has flagged so far turned out to be priced '
        'correctly. What it prevents is the bin error, where a $10.98 ten-pack '
        'was booked at $10.98 per bin and 19 bins read $208.62, because nothing '
        'in the record said a pack was ten. Rows holding a single unit are '
        'skipped: one of a stated pack is a kit, priced per kit. Settle it from '
        'the vendor listing — the SKU and usually the link are on the supplier '
        'part — then set pack_quantity, which both clears this lamp and makes '
        'the next receipt of that SKU price itself.'),
    'recv_age': (
        'Rows that have sat on the staging dock longer than the stale threshold '
        '(a plugin setting, 14 days by default), measured from when the row was '
        'created. Receiving is the blind spot: something filed to a drawer gets '
        'seen again when that drawer is opened, but something used on the way '
        'past the dock is never opened again — the item leaves and the row stays '
        'behind, still answering yes to "do I have one?". Three items have gone '
        'that way so far; the two still on record were 7 days in when the second '
        'was caught by eye, which is why the default threshold is 7 and not the '
        '14 first proposed.'),
    'po_late': (
        'Purchase orders past the delivery date the supplier promised. An order '
        'that is merely OPEN is not a fault — money is out and the box is in '
        'transit, which is what ordering looks like — so this lamp stays dark '
        'until something is actually late. The open orders themselves are listed '
        'in the Orders & Projects widget with their ages. It reads OFF, not '
        'zero, while no purchase order carries an expected date: with nothing to '
        'compare against, "nothing is late" would be a claim this panel cannot '
        'support. InvenTree HAS the field (target_date, and the API filters on '
        'it); nothing here fills it in. Teaching the overnight sweep to capture '
        'the promised date off the order page it already reads turns this flag '
        'into a real reading.'),
    'sweep': (
        'Hours since the overnight sweep last recorded a vendor check, from its '
        'own session-state file. Lights after 24 h. Reads OFF, never zero, when '
        'that file cannot be read: "the job is fine" and "I cannot tell" must '
        'not look the same.'),
}

SOURCE_TIP = (
    'The last read that PROVED something for this vendor, not the last time a '
    'job ran — those two diverge exactly when something is wrong. OFF means '
    'there is no usable reading: never checked, or the last check has aged out. '
    'A probe reporting SIGNED OUT is not OFF; that is a working probe with bad '
    'news.')



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
        'RECEIVING_STALE_DAYS': {
            'name': _('Receiving — stale after (days)'),
            'description': _('A row on the staging dock older than this lights a lamp'),
            # 7, not the 14 first proposed. Measured: the DIN cable and the LiPo
            # were both received 2026-08-18 and were 7 days old when Scott found
            # the second one by eye — at 14 days neither had aged in yet, so the
            # lamp would have been silent through exactly the week it was needed.
            'default': 7,
            'validator': [int],
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
        """One location gets a deep link to its STOCK ITEMS tab; several fall
        back to the stock-items table.

        Not the location's details tab and not `/web/stock/`: the first shows a
        description where a list was wanted, and the second is not a route at
        all — it redirects to the location tree and drops any query string on
        the way."""
        if len(locations) == 1:
            return f'/web/stock/location/{locations[0].pk}/stock-items'
        return '/web/stock/location/index/stock-items'

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
        # Same rule as the panel's LOST lamp: installed and consumed rows have
        # no location and cannot be given one.
        lost_qs = StockItem.objects.filter(
            StockItem.IN_STOCK_FILTER, location__isnull=True)

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
                'url': '/web/stock/location/index/stock-items',
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
                # In-stock rows only, so this strip and the panel's COUNTED dial
                # cannot report two different denominators on the same screen.
                'stock': StockItem.objects.filter(StockItem.IN_STOCK_FILTER).count(),
                'uncounted': StockItem.objects.filter(
                    StockItem.IN_STOCK_FILTER, stocktake_date__isnull=True).count(),
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

    @staticmethod
    def _search_count(model, term):
        """How many ACTIVE rows a `search=` link would return — or -1 if that
        search would sweep in rows the lamp did not count.

        The API search covers name, IPN, keywords and description; these lamps
        are defined on description alone. If a part merely NAMED "refunded
        something" existed, the link would show more rows than the lamp counted;
        -1 makes the caller refuse the link rather than ship the discrepancy.
        """
        from django.db.models import Q
        desc = model.objects.filter(active=True, description__icontains=term)
        wide = model.objects.filter(
            Q(active=True) & (
                Q(description__icontains=term) | Q(name__icontains=term)
                | Q(IPN__icontains=term) | Q(keywords__icontains=term)))
        n = desc.count()
        return n if wide.count() == n else -1

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

        # Only rows that are actually IN STOCK. A row installed in a device or
        # consumed by a build cannot be counted on a shelf, so leaving it in the
        # denominator means the gauge falls a little further every time
        # something gets built — a coverage figure that decays for the healthiest
        # possible reason. InvenTree's own IN_STOCK_FILTER is the definition:
        # quantity > 0, not installed, not consumed, not sold, not in build.
        live = StockItem.objects.filter(StockItem.IN_STOCK_FILTER)
        rows = live.count()
        counted_qs = live.filter(stocktake_date__isnull=False)
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
        # Reachable = already has an image, or has a supplier part. The SKU is
        # the thing an image gets fetched from, so a row without one has nowhere
        # to fetch from and does not belong in the denominator.
        img_reach = img_have + (
            (act.filter(image='') | act.filter(image__isnull=True))
            .filter(supplier_parts__isnull=False).distinct().count())

        return [
            {
                # This gauge flew its OFF flag for a day, because the REACHABLE
                # denominator was defined as the sweep's accumulated evidence
                # (delisted / login-gated / synthetic SKU) and that has still not
                # been handed over. What changed is the realisation that waiting
                # for it was not the only honest option: "has somewhere to fetch
                # from" is a rule this panel can compute live, state in one line
                # on its own face, and be argued with. It is NOT the sweep's 96%
                # and does not pretend to be.
                'key': 'images', 'name': 'IMAGES',
                'off': None,
                'value': pct(img_have, img_reach),
                'sub': f'{img_have} / {img_reach} reachable',
                'note': f'{img_all - img_reach} ruled out — no SKU to fetch from',
                'fresh': 'reachable = has an image, or a supplier part',
                'target': target('TARGET_IMAGES', 95),
                'setting': 'TARGET_IMAGES',
                'url': '/web/part/category/index/parts',
                # No has_image filter exists on the part API — passing one
                # returns all 1,010 rows rather than an error. Measured.
                'exact': '',
            },
            {
                'key': 'counted', 'name': 'COUNTED',
                'off': None,
                'value': pct(counted, rows),
                'sub': f'{counted} / {rows} rows in stock',
                'note': f'{rows - counted} never counted',
                'fresh': fresh,
                'target': target('TARGET_COUNTED', 90),
                'setting': 'TARGET_COUNTED',
                'url': ('/web/stock/location/index/stock-items'
                        '?has_stocktake=false&in_stock=true'),
                'exact': f'{rows - counted} rows nobody has counted',
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
                'url': '/web/stock/location/index/sublocations',
                # "drawers nobody has opened" is not expressible as a location
                # filter: it is the absence of rows plus the absence of a note.
                'exact': '',
            },
        ]

    def _lamps(self):
        """Eleven lamps. Red where a failure makes another check lie, yellow
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
        # `overdue` is a real API filter keying on target_date, so the panel can
        # mirror it exactly — when there is anything to mirror.
        open_n = placed.count()
        dated = placed.filter(target_date__isnull=False).exists()
        late = placed.filter(target_date__isnull=False,
                             target_date__lt=datetime.date.today())

        # [ESTIMATE] is a PREFIX on StockItem.notes, not a substring anywhere in
        # it, and not on Part.description. Both of those wrong tests have been
        # run here and both returned a confident wrong number.
        est = StockItem.objects.filter(notes__istartswith='[ESTIMATE]')

        recv = StockLocation.objects.filter(name='Receiving')
        unfiled = StockLocation.objects.filter(name__istartswith='Unfiled')

        # A location-filtered link can only name ONE location id, so a lamp
        # counting several gets no exact link. Today each of these is a single
        # location that actually holds rows — LRD/Receiving also exists and is
        # empty, so it must not be the one linked to.
        def one_loc(qs):
            holding = [l for l in qs if StockItem.objects.filter(location=l).exists()]
            return holding[0].pk if len(holding) == 1 else None

        recv_pk, unfiled_pk = one_loc(recv), one_loc(unfiled)

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
        # istartswith, NOT icontains. The tombstone marker is a PREFIX: every
        # one of the 28 merged records begins "MERGED into part #N". Matched as
        # a substring it also catches the SURVIVOR, whose description explains
        # the merge in prose — part #71 reads "part #381 was merged into this
        # record", is supposed to be active, and lit the red lamp for a day.
        # This is the [ESTIMATE] error again, three files apart: a prefix marker
        # tested as a substring returns confident, plausible, wrong rows.
        def _tombs(tags):
            qs = Part.objects.none()
            for tag in tags:
                qs = qs | Part.objects.filter(active=True, description__istartswith=tag)
            return qs.distinct()

        ghost = _tombs(('MERGED into', 'NOT INVENTORY'))
        verify = _tombs(('POSSIBLE RETURN',)).exclude(
            pk__in=ghost.values_list('pk', flat=True))

        state, newest = self._preflight()
        stale_h = None
        if newest:
            stale_h = int((datetime.datetime.now() - newest).total_seconds() // 3600)

        # Age on the staging dock. The count lamp above says there is work; this
        # one says the work has stopped happening, which is a different claim and
        # the one nothing else on this panel can make.
        #
        # Three items have now been received and then USED on the way past —
        # a 6-20P plug, the DIN cable (#89), the LiPo (#92) — leaving a row that
        # read "awaiting a drawer" for something already fitted into a device.
        # Every one of them would have tripped this. See TRAPS.md.
        try:
            stale_days = int(self.get_setting('RECEIVING_STALE_DAYS'))
        except (TypeError, ValueError):
            stale_days = 14
        cutoff = datetime.date.today() - datetime.timedelta(days=stale_days)
        # creation_date, not `updated`: the question is how long ago it landed,
        # and `updated` is bumped by any edit — including editing the note that
        # says nobody has filed it.
        stale_qs = StockItem.objects.filter(
            StockItem.IN_STOCK_FILTER, location__in=recv, creation_date__lt=cutoff)
        stale_n = stale_qs.count()
        stale_link = None
        if recv_pk and stale_n:
            stale_link = (
                f'/web/stock/location/{recv_pk}/stock-items?created_before={cutoff}',
                StockItem.objects.filter(StockItem.IN_STOCK_FILTER,
                                         location__pk=recv_pk,
                                         creation_date__lt=cutoff).count())

        pack_n, pack_sample, pack_rows = self._pack_price_suspects()

        lamps = [
            {'key': 'contradiction', 'tone': 'warning',
             'n': est.filter(stocktake_date__isnull=False).count(),
             'ident': (est.filter(stocktake_date__isnull=False), 'stock'),
             'label': 'Row contradicts itself', 'url': '/web/stock/location/index/stock-items',
             'why': 'marked [ESTIMATE] and stocktake-stamped — clear the date, not the marker'},
            {'key': 'po_no_date', 'tone': 'warning',
             'n': placed.filter(issue_date__isnull=True).count(),
             'ident': (placed.filter(issue_date__isnull=True), 'po'),
             'label': 'PO has no issue date', 'url': '/web/purchasing/index/purchaseorders/',
             'why': 'a null issue date drops the row out of aging entirely'},
            {'key': 'negative', 'tone': 'warning',
             'n': StockItem.objects.filter(quantity__lt=0).count(),
             'ident': (StockItem.objects.filter(quantity__lt=0), 'stock'),
             'label': 'Negative stock', 'url': '/web/stock/location/index/stock-items',
             'link': ('/web/stock/location/index/stock-items?max_stock=-0.0001',
                      StockItem.objects.filter(quantity__lt=0).count()),
             'why': 'a stock system that can go below zero is not counting'},
            {'key': 'tombstone', 'tone': 'warning',
             'n': ghost.count(),
             'ident': (ghost, 'part'),
             'label': 'Merged part still active', 'url': '/web/part/category/index/parts',
             'link': ('/web/part/category/index/parts?active=true&search=MERGED+into',
                      self._search_count(Part, 'MERGED into')),
             'why': 'merged or not-inventory rows that can still be counted twice'},
            {'key': 'lost', 'tone': 'caution',
             # IN_STOCK_FILTER, not "location is null". A row that is installed
             # in a finished device, consumed by a build, sold, or run down to
             # zero HAS no location and never will — installing is precisely
             # what takes the location away. Counting those as lost gives a lamp
             # that can never reach zero, and a lamp that cannot clear teaches
             # you to stop reading it. The 7-Pin DIN cable (stock #89, wired
             # into the Standing Desk Controller) is the case that found this.
             'n': StockItem.objects.filter(
                 StockItem.IN_STOCK_FILTER, location__isnull=True).count(),
             'ident': (StockItem.objects.filter(
                 StockItem.IN_STOCK_FILTER, location__isnull=True), 'stock'),
             'label': 'Stock with no location', 'url': '/web/stock/location/index/stock-items',
             # cascade defaults TRUE, and with it on location=null returns every
             # row in the database. Measured: 650 back for a lamp reading 43.
             'link': ('/web/stock/location/index/stock-items'
                      '?location=null&cascade=false&in_stock=true',
                      StockItem.objects.filter(
                          StockItem.IN_STOCK_FILTER, location__isnull=True).count()),
             'why': 'in stock, somewhere in the shop, nowhere in the record'},
            {'key': 'putaway', 'tone': 'caution',
             'n': StockItem.objects.filter(location__in=recv).count(),
             'ident': (StockItem.objects.filter(location__in=recv), 'stock'),
             'label': 'Waiting in Receiving', 'url': '/web/stock/location/index/stock-items',
             'link': ((f'/web/stock/location/{recv_pk}/stock-items',
                       StockItem.objects.filter(location__pk=recv_pk).count())
                      if recv_pk else None),
             'why': 'arrived, not yet given a home'},
            {'key': 'unfiled', 'tone': 'caution',
             'n': StockItem.objects.filter(location__in=unfiled).count(),
             'ident': (StockItem.objects.filter(location__in=unfiled), 'stock'),
             'label': 'Unfiled — find these', 'url': '/web/stock/location/index/stock-items',
             'link': ((f'/web/stock/location/{unfiled_pk}/stock-items',
                       StockItem.objects.filter(location__pk=unfiled_pk).count())
                      if unfiled_pk else None),
             'why': 'the import says it exists; nobody has found it'},
            {'key': 'to_verify', 'tone': 'caution',
             'n': verify.count(),
             'ident': (verify, 'part'),
             'label': 'Refund — verify these', 'url': '/web/part/category/index/parts',
             'link': ('/web/part/category/index/parts?active=true&search=POSSIBLE+RETURN',
                      self._search_count(Part, 'POSSIBLE RETURN')),
             'why': 'an order containing this was refunded; nobody has looked yet'},
            {'key': 'pack_price', 'tone': 'caution',
             'n': pack_n,
             'ident': (pack_rows, 'stock'),
             'label': 'Pack size not recorded',
             'url': '/web/stock/location/index/stock-items',
             'link': self._rows_link(pack_rows),
             'why': 'the name states a pack size that no supplier part records — '
                    + ('; '.join(pack_sample) if pack_sample else 'none')},
            {'key': 'recv_age', 'tone': 'caution',
             'n': stale_n,
             'ident': (stale_qs, 'stock'),
             'label': f'In Receiving over {stale_days}d',
             'url': '/web/stock/location/index/stock-items',
             'link': stale_link,
             'why': 'the staging dock is supposed to trend toward empty'},
            # An open order is not a fault. Scott, 2026-08-26: "they're not
            # overdue, they're on time ... it's no real reason to raise a
            # warning. The warning should come when they are not on time." So
            # this lamp asks about LATENESS; the count of open orders lives in
            # the Orders & Projects widget, where it is a list rather than an
            # alarm.
            #
            # Lateness needs an expected date, and nothing on this instance has
            # one — 0 purchase orders of 67 carry target_date. "Nothing is late"
            # and "I cannot tell whether anything is late" must not render the
            # same, so with no dates on file this reads OFF rather than 0.
            # Four states, and Scott named three of them: "make it green if the
            # PO's are not overdue, dark if there are no POs."
            #
            #   no open orders          -> DARK    nothing to say
            #   open, dated, none late  -> GREEN   checked, and good
            #   open, dated, some late  -> YELLOW  a real warning
            #   open but no dates       -> OFF     cannot tell, must not read 0
            #
            # Green is the state this panel was missing. A dark lamp meant both
            # "nothing wrong" and "nothing here", so a healthy check looked
            # identical to an absent one — and on a 727 the crew reads the
            # engines by pattern, which needs the healthy case to SHOW.
            {'key': 'po_late',
             'tone': ('caution' if (dated and late.count()) else 'good'),
             'n': (None if (open_n and not dated)
                   else late.count() if late.count() else open_n),
             'off': bool(open_n) and not dated,
             'ident': (late, 'po'),
             'label': ('PO overdue' if (dated and late.count()) else
                       'PO on time' if open_n else 'No open POs'),
             'url': '/web/purchasing/index/purchaseorders/',
             'link': (('/web/purchasing/index/purchaseorders/?status=20&overdue=true',
                       late.count()) if (dated and late.count()) else
                      ('/web/purchasing/index/purchaseorders/?status=20', open_n)
                      if open_n else None),
             'why': ('no expected date on these orders — lateness cannot be '
                     'measured' if (open_n and not dated) else
                     'past the date the supplier promised' if late.count() else
                     'every open order is inside its promised date' if open_n else
                     'nothing on order')},
        ]

        # The sweep's own liveness. OFF rather than 0 when the state file
        # cannot be read: "the job is fine" and "I cannot tell" must not render
        # the same, which is the whole argument of the fourth state.
        if stale_h is None:
            lamps.append({'key': 'sweep', 'tone': 'caution', 'n': None, 'off': True,
                          'label': 'Sweep check-in', 'url': '/web/part/category/index/parts',
                          'why': 'no readable session-state file — cannot tell if it ran'})
        else:
            lamps.append({'key': 'sweep', 'tone': 'caution',
                          'n': stale_h if stale_h >= self.PANEL_STALE_H else 0,
                          'unit': 'h',
                          'label': 'Sweep has not checked in', 'url': '/web/part/category/index/parts',
                          'why': f'last check-in {stale_h}h ago'})

        acks = self._ack_map()
        import datetime as _dt
        for lamp in lamps:
            # A lamp's link must land on the rows the lamp counted. InvenTree's
            # tables pass unknown query parameters straight through to the API,
            # and the API IGNORES a filter it does not recognise — so a wrong
            # filter does not error, it silently returns the whole table. That
            # is what "open" did on the first build: 650 stock rows behind a
            # lamp reading 43. Each link therefore states the count it would
            # show, and is used only if that equals the lamp. Anything else
            # keeps the plain list and says so on the face of the lamp.
            link = lamp.pop('link', None)
            lamp['exact'] = bool(link) and link[1] == lamp.get('n')
            if lamp['exact']:
                lamp['url'] = link[0]

            # A lamp with no filtered view has to NAME its rows, or "open list"
            # hands over five purchase orders and no way to tell which two are
            # the ones it counted. Scott, 2026-08-26: "there are 5 I have no idea
            # which ones are the problem."
            ident = lamp.pop('ident', None)
            lamp['rows'] = ''
            if ident and not lamp['exact'] and lamp.get('n'):
                qs, kind = ident
                shown = []
                for o in list(qs[:8]):
                    if kind == 'stock':
                        shown.append(f'#{o.pk} {o.part.name[:36]}')
                    elif kind == 'part':
                        shown.append(f'#{o.pk} {o.name[:36]}')
                    else:
                        shown.append(f'{o.reference} — {(o.description or "")[:32]}')
                    # A single row needs no filter at all: link straight to it.
                    if lamp['n'] == 1:
                        lamp['url'] = (f'/web/stock/item/{o.pk}/' if kind == 'stock'
                                       else f'/web/part/{o.pk}/' if kind == 'part'
                                       else f'/web/purchasing/purchase-order/{o.pk}/')
                        lamp['exact'] = True
                more = lamp['n'] - len(shown)
                lamp['rows'] = ' · '.join(shown) + (f'  (+{more} more)' if more > 0 else '')
            rec = acks.get(lamp['key']) or {}
            lamp['tip'] = LAMP_TIPS.get(lamp['key'], '')
            lamp['ack'] = bool(rec) and rec.get('n') == lamp.get('n')
            lamp['ack_age'] = ''
            # Handed back so the browser can rewrite the whole ack map without
            # flattening every OTHER lamp's timestamp. A lamp silenced six weeks
            # ago is itself a signal; losing the date destroys it.
            lamp['ack_at'] = rec.get('at') if lamp['ack'] else None
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

    @staticmethod
    def _rows_link(rows):
        """A link that opens exactly THESE stock rows, or None.

        The API has no filter for a set of primary keys — `id`, `pk` and
        `id__in` are all silently ignored and return the whole table (measured;
        see TRAPS.md). What it does have is `search`, so: find a word every one
        of these rows' parts shares, mirror the API's own search fields in the
        ORM, and use the link ONLY if that search returns this exact number of
        rows. A word like "TERMINAL" that also catches other terminal blocks
        fails the count and is discarded; "KF301" passes.

        One row needs no filter at all — link straight to the item.
        """
        from django.db.models import Q
        from stock.models import StockItem

        if not rows:
            return None
        if len(rows) == 1:
            return (f'/web/stock/item/{rows[0].pk}/', 1)

        def mirror(term):
            # These are StockList.search_fields, verbatim. If they drift, the
            # count check fails and the link is simply not offered.
            q = (Q(serial__icontains=term) | Q(batch__icontains=term)
                 | Q(location__name__icontains=term)
                 | Q(part__name__icontains=term) | Q(part__IPN__icontains=term)
                 | Q(part__description__icontains=term)
                 | Q(supplier_part__SKU__icontains=term)
                 | Q(supplier_part__supplier__name__icontains=term)
                 | Q(supplier_part__manufacturer_part__MPN__icontains=term))
            return (StockItem.objects.filter(StockItem.IN_STOCK_FILTER)
                    .filter(q).distinct().count())

        words = None
        for r in rows:
            w = {t for t in re.split(r'[^A-Za-z0-9.]+', (r.part.name or '').upper())
                 if len(t) >= 3}
            words = w if words is None else (words & w)
        for term in sorted(words or (), key=len, reverse=True):
            if mirror(term) == len(rows):
                return (f'/web/stock/location/index/stock-items'
                        f'?search={quote(term)}&in_stock=true', len(rows))
        return None

    def _pack_price_suspects(self):
        """(count, sample) — priced stock whose part states a pack size that
        nothing in the record confirms.

        Deliberately NOT "this price is wrong". It cannot know that: a kit
        stocked as ONE unit is correctly priced per pack, and a Tormach pull
        stud really can cost $8.40 each. What it knows is that the record does
        not say which, while money is riding on the answer — and that is a
        question for the invoice, not for a guess.
        """
        from company.models import SupplierPart
        from stock.models import StockItem

        # quantity > 1 only. ONE unit of a stated pack is a kit stocked as a kit
        # and priced per kit — an ER20 collet set at $152.85, a 58-piece clamp
        # kit at $89.95, 2,000 Avery labels at $11.99 are all correct, and the
        # number in the name describes the CONTENTS, not a purchase multiple.
        # The shape that was wrong on the bins is quantity N of a stated pack of
        # N, so that is what this asks about.
        rows = (StockItem.objects.filter(StockItem.IN_STOCK_FILTER, quantity__gt=1)
                .exclude(purchase_price=None).select_related('part'))
        n, sample, hits = 0, [], []
        for r in rows:
            p = r.part
            m = PACK_SIZE.search(f'{p.name} {p.description or ""}')
            if not m:
                continue
            if any(sp.pack_quantity_native and float(sp.pack_quantity_native) > 1
                   for sp in SupplierPart.objects.filter(part=p)):
                continue          # the pack size IS recorded; nothing to ask
            n += 1
            hits.append(r)
            if len(sample) < 4:
                pack = next((g for g in m.groups() if g), '?')
                sample.append(f'{p.name[:34]} ({float(r.quantity):g} @ '
                              f'{r.purchase_price}, stated pack {pack})')
        return n, sample, hits

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
            row['tip'] = SOURCE_TIP + f'  Reported state: {st}.'
            out.append(row)
        return out

    def _panel(self):
        import datetime
        gauges = self._gauges()
        for g in gauges:
            g['tip'] = GAUGE_TIPS.get(g['key'], '')
        return {
            'gauges': gauges,
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
