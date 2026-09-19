"""Write the 16:40 2026-09-19 shape-based candidate set to /tmp on the Mini.

vendor_triage.py takes a FILE path, and it runs on the Mini, so the candidates
have to land there first. Written as a script rather than pushed as a blob so
the exact input this run classified is recoverable later.

Source queries, window = last-po-sweep 2026-09-19 minus 1 day:

  (a) section 4 as written:
      category:purchases newer_than:2d -from:<each known itemised vendor>
  (b) the subject-shaped search proposed this morning as a FIX for section 4's
      category hole (open decision `section-4-category-purchases-has-a-hole`,
      filed 2026-09-19 12:40):
      newer_than:2d (subject:"order confirmed" OR "order confirmation" OR
      "your order" OR "thanks for your order" OR "order #" OR receipt)
      -from:<each known itemised vendor>

Both were run and the hits UNIONED. That is not an edit to the task file — the
file is unchanged and the decision is still open — it is running one extra
search alongside the prescribed one, which costs nothing and closes the hole
for this window. And it earned its keep immediately: (b) surfaced two senders
(rusticedgeco.com, paypal.com) that (a) did not return, which is exactly the
failure mode the decision item describes.

Seven hits, all seven carried through unedited — the classifier decides the
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
        "subject": "Your Mail Was Delivered Sat, Sep 19",
        "date": "2026-09-19",
        "snippet": ("MAIL DELIVERY NOTIFICATION Your mail has been delivered "
                    "today, September 19!"),
    },
    {
        "sender": "USPSInformeddelivery@email.informeddelivery.usps.com",
        "subject": "Your Daily Digest for Sat, 9/19 is ready to view",
        "date": "2026-09-19",
        "snippet": ("COMING TO YOU SOON Hi, Scott! You have 1 mailpiece(s) "
                    "and 0 inbound package(s) arriving soon."),
    },
    {
        "sender": "support@rusticedgeco.com",
        "subject": "Order #6663 confirmed",
        "date": "2026-09-19",
        "snippet": ("Order #6663 Thanks for your order! We've got your order. "
                    "Every Rustic Edge shirt is made to order, so yours is "
                    "headed for the press, not a warehouse shelf. Once it's "
                    "printed, shipping takes 2-5 days."),
    },
    {
        "sender": "customercare@paypal.com",
        "subject": "Receipt for your payment to PayPal Credit",
        "date": "2026-09-19",
        "snippet": ("You paid 61.50 USD on September 19, 2026. Hello, Scott "
                    "Dube You paid 61.50 USD to PayPal Credit. Thanks for "
                    "making your payment. Transaction ID 6U9767334K5650412."),
    },
    {
        "sender": "rjgatorsfloridaseagrillbar@mg.owner.com",
        "subject": "Order your menu favorites from RJ Gator's Florida Sea Grill & Bar",
        "date": "2026-09-18",
        "snippet": "Pick your go-to's or try something new.",
    },
]

with open("/tmp/cands.json", "w") as fh:
    json.dump(ROWS, fh, indent=1)
print(f"wrote /tmp/cands.json with {len(ROWS)} candidate(s)")
for r in ROWS:
    print(f"  {r['date']}  {r['sender']}  {r['subject']}")
