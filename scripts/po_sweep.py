import os, sys, re, json, urllib.request, datetime
sys.path.insert(0, '/path/to/inventree/src/src/backend/InvenTree')
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()

from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from part.models import Part
from company.models import Company, SupplierPart
from order.models import PurchaseOrder, PurchaseOrderLineItem
from order.status_codes import PurchaseOrderStatus

PROGRESS = '/path/to/inventree/enrich_progress.md'

def journal(line):
    with open(PROGRESS, 'a') as f:
        f.write(line.rstrip() + "\n")

def D(s):
    return datetime.date.fromisoformat(s)

POLOLU = Company.objects.get(name='Pololu')
AMAZON = Company.objects.get(name='Amazon')
SEEED = Company.objects.get(name='Seeed Studio')

PLACED = PurchaseOrderStatus.PLACED.value


def existing_po(order_no):
    """Idempotency: match on reference OR supplier_reference."""
    qs = PurchaseOrder.objects.filter(reference=order_no)
    if qs.exists():
        return qs.first()
    qs = PurchaseOrder.objects.filter(supplier_reference=order_no)
    if qs.exists():
        return qs.first()
    return None


def make_po(supplier, order_no, issue_date, description, notes):
    """Create a PLACED PO. Try vendor order number as reference; fall back to
    auto-reference + supplier_reference if InvenTree's reference pattern rejects it."""
    found = existing_po(order_no)
    if found:
        print(f"SKIP (exists): {order_no} -> PO#{found.pk} {found.reference}")
        return None, False

    po = PurchaseOrder(
        supplier=supplier,
        reference=order_no,
        supplier_reference=order_no,
        description=description[:250],
        notes=notes,
        issue_date=issue_date,
        status=PLACED,
    )
    used_fallback = False
    try:
        po.full_clean(exclude=['reference_int'])
        po.save()
    except ValidationError as e:
        # reference pattern rejected the vendor number -> auto reference
        used_fallback = True
        po = PurchaseOrder(
            supplier=supplier,
            reference=PurchaseOrder.generate_reference(),
            supplier_reference=order_no,
            description=description[:250],
            notes=notes + f"\n\nVendor order number: {order_no}",
            issue_date=issue_date,
            status=PLACED,
        )
        po.save()
    po.status = PLACED
    po.save()
    print(f"CREATED PO#{po.pk} ref={po.reference} supplier_ref={po.supplier_reference} "
          f"supplier={supplier.name} status={po.status} fallback={used_fallback}")
    return po, True


created = []

# ---------------------------------------------------------------- 1. POLOLU
print("=" * 60)
print("POLOLU PO-REDACTED — itemised, real line items")
print("=" * 60)

POLOLU_LINES = [
    # SKU,  qty, extended, unit
    ('3692', 2, '27.90', '13.95'),
    ('3415', 1, '22.95', '22.95'),
    ('4562', 2, '5.38', '2.69'),
    ('4561', 2, '5.38', '2.69'),
    ('4565', 1, '2.85', '2.85'),
    ('4564', 1, '2.85', '2.85'),
]

po, isnew = make_po(
    POLOLU, 'PO-REDACTED', D('2026-07-22'),
    'Pololu sales order PO-REDACTED — ToF distance sensors + premium jumper wires',
    ('Auto-created from Pololu order confirmation email (VENDOR-EMAIL-REDACTED, 2026-07-22).\n'
     'Pololu quotes EXTENDED price per line; unit price = extended / qty.\n'
     'Order total $79.26 incl. $11.95 S&H (shipping not carried on any line).\n'
     'PLACED, not received — receive by hand when the box is physically checked in.'),
)
if isnew:
    created.append(('Pololu', 'PO-REDACTED', po.pk))
    for sku, qty, ext, unit in POLOLU_LINES:
        try:
            sp = SupplierPart.objects.get(supplier=POLOLU, SKU=sku)
        except SupplierPart.DoesNotExist:
            print(f"  !! no SupplierPart for Pololu SKU {sku} — line skipped")
            continue
        li = PurchaseOrderLineItem(
            order=po, part=sp, quantity=qty,
            purchase_price=unit, purchase_price_currency='USD',
            notes=f"Pololu #{sku}; email extended price {ext} for qty {qty}",
        )
        li.save()
        print(f"  line: {sku} qty={qty} unit=${unit} (ext ${ext}) -> part #{sp.part.pk} {sp.part.name}")

journal(f"- {datetime.datetime.now():%Y-%m-%d %H:%M} — chunk done: Pololu PO PO-REDACTED created (6 lines, unit prices from extended).")

# ---------------------------------------------------------------- 2. AMAZON STUBS
print()
print("=" * 60)
print("AMAZON stub POs — new-format emails carry no line items")
print("=" * 60)

AMAZON_ORDERS = [
    ('ORDER-REDACTED', '2026-07-23', '15.32', '1 Hardware item'),
    ('ORDER-REDACTED', '2026-07-24', '9.99',  '1 Hardware item'),
    ('ORDER-REDACTED', '2026-07-26', '44.58', '2 Hardware items'),
    ('ORDER-REDACTED', '2026-07-27', '88.99', '1 Hardware item'),
    ('ORDER-REDACTED', '2026-08-03', '25.79', '1 Hardware item'),
    ('ORDER-REDACTED', '2026-08-03', '29.00', '1 Electronics item'),
    ('ORDER-REDACTED', '2026-08-08', '14.99', '1 Electronics item'),
    ('ORDER-REDACTED', '2026-08-09', '29.88', '2 Electronics items'),
    ('ORDER-REDACTED', '2026-08-12', '4.10',  '1 Electrical & Heating item'),
    ('ORDER-REDACTED', '2026-08-14', '29.99', '1 Tools item'),
    ('ORDER-REDACTED', '2026-08-15', '10.76', 'part of a 4-item Hardware / Electrical & Heating order'),
    ('ORDER-REDACTED', '2026-08-15', '7.97',  '1 Electronics item'),
    ('ORDER-REDACTED', '2026-08-15', '6.59',  '1 Hardware item'),
    ('ORDER-REDACTED', '2026-08-15', '16.90', '1 Hardware item'),
    ('ORDER-REDACTED', '2026-08-15', '6.99',  '1 Tools item'),
    ('ORDER-REDACTED', '2026-08-16', '9.99',  '1 Electronics item'),
    ('ORDER-REDACTED', '2026-08-16', '9.99',  '1 Electronics item'),
]

for order_no, date, total, cat in AMAZON_ORDERS:
    po, isnew = make_po(
        AMAZON, order_no, D(date),
        f'Amazon order {order_no} — {cat} (STUB, needs line reconciliation)',
        (f'STUB PURCHASE ORDER — needs manual reconciliation.\n'
         f'Amazon order confirmation email of {date} carries NO line items; it gives only the\n'
         f'order number, the category hint "{cat}", and a grand total of ${total} USD.\n'
         f'Line items are unrecoverable from email — reconcile from the Amazon order page:\n'
         f'https://www.amazon.com/your-orders/order-details?orderID={order_no}\n'
         f'Classified shop-relevant by category hint. PLACED, not received.'),
    )
    if isnew:
        created.append(('Amazon', order_no, po.pk))

journal(f"- {datetime.datetime.now():%Y-%m-%d %H:%M} — chunk done: Amazon stub POs created ({len([c for c in created if c[0]=='Amazon'])}).")

# ---------------------------------------------------------------- 3. SEEED STUB
print()
print("=" * 60)
print("SEEED stub PO")
print("=" * 60)

po, isnew = make_po(
    SEEED, '4000567982', D('2026-08-13'),
    'Seeed Studio order 4000567982 (STUB, needs line reconciliation)',
    ('STUB PURCHASE ORDER — needs manual reconciliation.\n'
     'Seeed order-received email carries the order number only: no line items and no total.\n'
     'Shipped 2026-08-14 via USPS, tracking 420038209261290198196828229707.\n'
     'Itemised invoice is available in the Seeed account under "My Orders".\n'
     'PLACED, not received.'),
)
if isnew:
    created.append(('Seeed Studio', '4000567982', po.pk))

journal(f"- {datetime.datetime.now():%Y-%m-%d %H:%M} — chunk done: Seeed stub PO 4000567982 created.")

# ---------------------------------------------------------------- 4. IMAGES
print()
print("=" * 60)
print("QUEUE A — product images for the parts on the new Pololu PO")
print("=" * 60)

UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
                    '(KHTML, like Gecko) Chrome/125.0 Safari/537.36'}

def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

img_done, img_fail = [], []

for pk, sku in [(712, '3692'), (713, '3415'), (714, '4562'),
                (715, '4561'), (716, '4565'), (717, '4564')]:
    p = Part.objects.get(pk=pk)
    if p.image:
        print(f"#{pk} already has an image — left alone")
        continue
    url = f'https://www.pololu.com/product/{sku}'
    try:
        html = fetch(url).decode('utf-8', 'replace')
    except Exception as e:
        print(f"#{pk} {sku}: page fetch FAILED: {e}")
        img_fail.append((pk, sku, f'page: {e}'))
        continue

    cands = re.findall(r'https://a\.pololu-files\.com/picture/[A-Za-z0-9_.\-]+\.(?:jpg|png)', html)
    # prefer the largest rendition of the first distinct picture id
    if not cands:
        print(f"#{pk} {sku}: no image URL found on page")
        img_fail.append((pk, sku, 'no image url in html'))
        continue

    def score(u):
        m = re.search(r'\.(\d+)\.(?:jpg|png)$', u)
        return int(m.group(1)) if m else 0

    first_id = re.search(r'picture/([A-Za-z0-9]+)\.', cands[0]).group(1)
    same = [u for u in cands if f'picture/{first_id}.' in u]
    best = max(same, key=score)

    try:
        data = fetch(best)
    except Exception as e:
        print(f"#{pk} {sku}: image fetch FAILED: {e}")
        img_fail.append((pk, sku, f'image: {e}'))
        continue

    if len(data) < 2000:
        print(f"#{pk} {sku}: image suspiciously small ({len(data)} bytes) — refused")
        img_fail.append((pk, sku, f'{len(data)} bytes'))
        continue

    ext = 'png' if best.endswith('.png') else 'jpg'
    p.image.save(f'pololu_{sku}.{ext}', ContentFile(data), save=True)
    print(f"#{pk} {sku}: image attached ({len(data)} bytes) from {best}")
    img_done.append((pk, sku, len(data)))

    # while we are here, record the product link on the SupplierPart (it was empty)
    for sp in SupplierPart.objects.filter(part=p, supplier=POLOLU):
        if not sp.link:
            sp.link = url
            sp.save()
            print(f"      + SupplierPart link set to {url}")

journal(f"- {datetime.datetime.now():%Y-%m-%d %H:%M} — chunk done: images attached to {len(img_done)} Pololu parts, {len(img_fail)} failed.")

# ---------------------------------------------------------------- SUMMARY
print()
print("=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"POs created: {len(created)}")
for s, o, pk in created:
    print(f"   {s:15s} {o:24s} PO#{pk}")
print(f"Images attached: {len(img_done)}  failed: {len(img_fail)}")
for f in img_fail:
    print(f"   FAIL {f}")

tot = Part.objects.count()
print(f"\nTotals now: parts={tot} POs={PurchaseOrder.objects.count()} "
      f"images={Part.objects.exclude(image='').count()}/{tot} "
      f"stock={__import__('stock').models.StockItem.objects.count()}")
print("DONE")
