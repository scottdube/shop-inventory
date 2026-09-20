"""Write the 12:40 2026-09-20 shape-based candidate set to /tmp on the Mini.

vendor_triage.py takes a FILE path and runs on the Mini, so the candidates have
to land there first. Written as a script rather than pushed as a blob so the
exact input this run classified is recoverable later.

Source query, window = last-po-sweep 2026-09-20 minus 1 day:

    category:purchases newer_than:2d -from:<each known itemised vendor>

SECTION 4 AS WRITTEN, and only that. The subject-shaped union proposed by the
12:40 and 16:40 runs on 2026-09-19 is still an OPEN decision
(`section-4-category-purchases-has-a-hole`, rider
`section-4-subject-search-measured-both-ways`) and has not been approved, so its
output is NOT fed to the classifier here. Same reasoning the 22:40 run gave:
running an unapproved procedure every sweep quietly turns a proposal into
practice.

I did run the subject-shaped query this window as a READ-ONLY safety net, and
it is recorded here rather than classified, because a third measurement of the
same trade buys nothing and re-queueing it would be the fourth copy of one
question. It returned six threads and NO unknown parts vendor: rusticedgeco.com
"Order #6663 confirmed" (apparel, suppressed — the same mail the documented hole
drops, reproduced a third time), customercare@paypal.com and three
alerts@services.barclaysus.com transaction alerts (payment rail),
support@trustworthy.com invoice reminder (personal admin), and the known false
positive rjgatorsfloridaseagrillbar@mg.owner.com restaurant marketing. Nothing
in that set is a vendor of goods this system would stock.

Two hits from section 4 as written, both carried through unedited — the
classifier decides the bucket, not me. Both are the carrier notices that arrive
every day.
"""
import json

ROWS = [
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
]

with open("/tmp/cands.json", "w") as fh:
    json.dump(ROWS, fh, indent=1)
print(f"wrote /tmp/cands.json with {len(ROWS)} candidate(s)")
for r in ROWS:
    print(f"  {r['date']}  {r['sender']}  {r['subject']}")
