"""Write the 16:40 2026-09-18 shape-based candidate set to /tmp on the Mini.

vendor_triage.py takes a FILE path, and it runs on the Mini, so the candidates
have to land there first. Written as a script rather than pushed as a blob so
the exact input this run classified is recoverable later.

Source query (section 4), window = last-po-sweep 2026-09-18 minus 1 day:

    category:purchases after:2026/09/17 -from:<each known itemised vendor>

Four hits, all four carried through unedited — the classifier decides the
bucket, not me.
"""
import json

ROWS = [
    {
        "sender": "no-reply@toasttab.com",
        "subject": "Your Toast eGift Card Order Receipt",
        "date": "2026-09-18",
        "snippet": ("Nick's Steakhouse @nicksyork 369 US-Route 1 York, ME, "
                    "03909 207-606-8900 E-Gift Cards Check #1 Ordered: "
                    "9/18/26 9:53 AM How was your visit?"),
    },
    {
        "sender": "Auto_Reply@mailer.wexhealth.com",
        "subject": "Your WEX debit card purchase",
        "date": "2026-09-18",
        "snippet": ("A debit card transaction has been processed for 10.00 "
                    "on 9/18/2026. Merchant name: OPTUM HOME DELIVERY. This "
                    "email is to confirm a recent transaction made using "
                    "your WEX card."),
    },
    {
        "sender": "USPSInformeddelivery@email.informeddelivery.usps.com",
        "subject": "Your Mail Was Delivered Thu, Sep 17",
        "date": "2026-09-17",
        "snippet": ("MAIL DELIVERY NOTIFICATION Your mail has been delivered "
                    "today, September 17!"),
    },
    {
        "sender": "USPSInformeddelivery@email.informeddelivery.usps.com",
        "subject": "Your Daily Digest for Thu, 9/17 is ready to view",
        "date": "2026-09-17",
        "snippet": ("COMING TO YOU SOON Hi, Scott! You have 3 mailpiece(s) "
                    "and 0 inbound package(s) arriving soon."),
    },
]

with open("/tmp/cands.json", "w") as fh:
    json.dump(ROWS, fh, indent=1)
print(f"wrote /tmp/cands.json with {len(ROWS)} candidate(s)")
for r in ROWS:
    print(f"  {r['date']}  {r['sender']}  {r['subject']}")
