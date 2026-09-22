"""Write the 12:40 2026-09-22 shape-based candidate set to /tmp on the Mini.

vendor_triage.py takes a FILE path and runs on the Mini, so the candidates have
to land there first. Written as a script rather than pushed as a blob so the
exact input this run classified is recoverable later.

Source query, window = last-po-sweep 2026-09-22 minus 1 day:

    category:purchases newer_than:2d -from:<each known itemised vendor>

newer_than:2d reaches back to 2026-09-20, one day wider than the prescribed
window. Deliberate, same reasoning as the 0921 run: a wider net here costs only
classifier work.

SECTION 4 AS WRITTEN, and only that. The subject-shaped union is still an OPEN
decision (`section-4-category-purchases-has-a-hole` plus its riders) and has not
been approved, so its output is NOT fed to the classifier here, and the trade is
NOT re-measured — that would be the fifth copy of one question.

I also ran an unconstrained sender-list safety net over the itemised vendors as a
READ-ONLY check (15 threads, all marketing / shipping / delivery / return /
pharmacy notices, no unimported order; result set complete, nothing truncated).
Recorded here rather than classified because it found nothing section 3 had not
already imported.

All seven section-4 hits are carried through unedited -- the classifier decides
the bucket, not me. Two are the daily USPS carrier notices. Two are the PayPal
legs of athom.tech order 56290, which is NO LONGER an open question: PO-0181
exists for it as of this morning's run, so the classifier's own idempotency
check should now drop them as ALREADY IMPORTED rather than bucketing them --
this run is the first chance to see that check fire on a vendor it previously
surfaced as unknown. Two are WEX benefits-card legs of pharmacy transactions,
carried for bucketing only with no item transcribed. One is an iFIT membership
cancellation, which is a membership line and out by standing rule.
"""
import json

ROWS = [
    {
        "sender": "Auto_Reply@mailer.wexhealth.com",
        "subject": "Your WEX debit card purchase",
        "date": "2026-09-22",
        "snippet": ("A debit card transaction has been processed on 9/21/2026. "
                    "This email is to confirm a recent transaction made using "
                    "your WEX benefits card."),
    },
    {
        "sender": "billing@account.ifit.com",
        "subject": "We miss you already, Scott!",
        "date": "2026-09-21",
        "snippet": "Your iFIT membership was canceled.",
    },
    {
        "sender": "USPSInformeddelivery@email.informeddelivery.usps.com",
        "subject": "Your Mail Was Delivered Mon, Sep 21",
        "date": "2026-09-21",
        "snippet": ("MAIL DELIVERY NOTIFICATION View Dashboard Your mail has "
                    "been delivered today, September 21!"),
    },
    {
        "sender": "USPSInformeddelivery@email.informeddelivery.usps.com",
        "subject": "Your Daily Digest for Mon, 9/21 is ready to view",
        "date": "2026-09-21",
        "snippet": ("COMING TO YOU SOON Hi, Scott! You have 1 mailpiece(s) "
                    "and 0 inbound package(s) arriving soon."),
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
        "sender": "service@paypal.com",
        "subject": "深圳市极乌智能科技有限公司: $99.50 USD",
        "date": "2026-09-20",
        "snippet": ("Track your purchase from this email. Hello, Scott Dube "
                    "You paid $99.50 USD to "
                    "深圳市极乌智能科技有限公司 "
                    "Transaction date September 20, 2026 1:09:23 PM PDT "
                    "order 56290"),
    },
    {
        "sender": "service@paypal.com",
        "subject": "Receipt for your PayPal payment",
        "date": "2026-09-20",
        "snippet": ("Scott Dube, thanks for paying with PayPal. Here's your "
                    "receipt. To see the payment details, log in to your "
                    "PayPal account."),
    },
]

with open("/tmp/cands.json", "w") as fh:
    json.dump(ROWS, fh, indent=1)
print(f"wrote /tmp/cands.json with {len(ROWS)} candidate(s)")
for r in ROWS:
    print(f"  {r['date']}  {r['sender']}  {r['subject']}")
