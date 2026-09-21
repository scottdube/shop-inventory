"""Write the 08:40 2026-09-21 shape-based candidate set to /tmp on the Mini.

vendor_triage.py takes a FILE path and runs on the Mini, so the candidates have
to land there first. Written as a script rather than pushed as a blob so the
exact input this run classified is recoverable later.

Source query, window = last-po-sweep 2026-09-20 minus 1 day:

    category:purchases newer_than:3d -from:<each known itemised vendor>

newer_than:3d reaches back to 2026-09-18, one day wider than the prescribed
window. Deliberate: 3d is the coarsest Gmail duration that certainly covers
2026-09-19, and a wider net here costs only classifier work.

SECTION 4 AS WRITTEN, and only that. The subject-shaped union proposed on
2026-09-19 is still an OPEN decision (`section-4-category-purchases-has-a-hole`,
riders `section-4-subject-search-measured-both-ways` and
`section-4-hole-now-has-a-real-cost`) and has not been approved, so its output is
NOT fed to the classifier here. Fourth sighting of the same trade would buy
nothing and re-queueing it would be the fifth copy of one question.

I did run an unconstrained sender-list safety net over the itemised vendors as a
READ-ONLY check (24 threads, all shipping/delivery/marketing/offer/return/
pharmacy notices, no unimported order). It is recorded here rather than
classified because it found nothing section 3 had not already imported.

All seven section-4 hits are carried through unedited -- the classifier decides
the bucket, not me. Three are the daily USPS carrier notices. Two are the PayPal
legs of athom.tech order 56290, ALREADY OPEN as `athom-tech-new-vendor` with the
order read off the vendor's own order page on 2026-09-20; the merchant string
renders as the Shenzhen corporate name because the payment went through PayPal,
which is exactly how that vendor surfaced in the first place. One is the WEX
benefits-card leg of a pharmacy transaction, carried for bucketing only with no
item transcribed. One is the toasttab gift-card receipt already open as
`toasttab-gift-card-suppress` and deliberately not re-asked.
"""
import json

ROWS = [
    {
        "sender": "USPSInformeddelivery@email.informeddelivery.usps.com",
        "subject": "Your Daily Digest for Mon, 9/21 is ready to view",
        "date": "2026-09-21",
        "snippet": ("COMING TO YOU SOON Hi, Scott! You have 1 mailpiece(s) "
                    "and 0 inbound package(s) arriving soon."),
    },
    {
        "sender": "USPSInformeddelivery@email.informeddelivery.usps.com",
        "subject": "Your Mail Was Delivered Sat, Sep 19",
        "date": "2026-09-19",
        "snippet": ("MAIL DELIVERY NOTIFICATION View Dashboard Your mail has "
                    "been delivered today, September 19!"),
    },
    {
        "sender": "USPSInformeddelivery@email.informeddelivery.usps.com",
        "subject": "Your Daily Digest for Sat, 9/19 is ready to view",
        "date": "2026-09-19",
        "snippet": ("COMING TO YOU SOON Hi, Scott! You have 1 mailpiece(s) "
                    "and 0 inbound package(s) arriving soon."),
    },
    {
        "sender": "service@paypal.com",
        "subject": "深圳市极乌智能科技有限公司: $99.50 USD",
        "date": "2026-09-20",
        "snippet": ("Track your purchase from this email. Hello, Scott Dube "
                    "You paid $99.50 USD to "
                    "深圳市极乌智能科技有限公司 "
                    "Transaction date September 20, 2026 1:09:23 PM PDT"),
    },
    {
        "sender": "service@paypal.com",
        "subject": "Receipt for your PayPal payment",
        "date": "2026-09-20",
        "snippet": ("Scott Dube, thanks for paying with PayPal. Here's your "
                    "receipt. To see the payment details, log in to your "
                    "PayPal account."),
    },
    {
        "sender": "Auto_Reply@mailer.wexhealth.com",
        "subject": "Your WEX debit card purchase",
        "date": "2026-09-21",
        "snippet": ("A debit card transaction has been processed on 9/20/2026. "
                    "This email is to confirm a recent transaction made using "
                    "your WEX benefits card."),
    },
    {
        "sender": "no-reply@toasttab.com",
        "subject": "Your Toast eGift Card Order Receipt",
        "date": "2026-09-18",
        "snippet": ("Nick's Steakhouse E-Gift Cards Check #1 Ordered: "
                    "9/18/26 9:53 AM"),
    },
]

with open("/tmp/cands.json", "w") as fh:
    json.dump(ROWS, fh, indent=1)
print(f"wrote /tmp/cands.json with {len(ROWS)} candidate(s)")
for r in ROWS:
    print(f"  {r['date']}  {r['sender']}  {r['subject']}")
