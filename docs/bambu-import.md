# Bambu Lab import

Supplier created 2026-08-22 (company #29). **12 order confirmations exist,
2023-06-21 → 2026-03-26**, all from `noreply@bambulab.com` with subject
`Order <ref> confirmed` or `Your order <ref> is confirmed`. Nothing 3D-printer
related was in the catalogue before this — no filament, plates, hotends or AMS
parts at all.

Parser: `scripts/bambu_parse.py`, verified against all three template eras.

## The traps, all paid for during the survey

**Prices are EXTENDED — divide by quantity.** Same as Tormach, Shars, Haas and
Pololu. An AMS Flipper line reading `x 2 ... $6.40` is $3.20 each.

**Three email templates, and the discount column MOVES between them.** A
discounted line shows two prices, and which one was paid is not consistent:

| Order | Line | Paid |
|---|---|---|
| 2025-11 | `$19.99 $12.99` | the **second** |
| 2026-03 | `$65.99 $91.96` | the **first** |

Do not guess, and do not hardcode a rule per era. **Sum both interpretations
and keep whichever matches the stated Subtotal.** The email carries its own
checksum, and using it is the only approach that survives the next template
change. Verified: 2026 pipe-table → first, 2025 pipe-table → second, 2023
plain-text → first, all three reconciling to the cent.

**2023 mails use a multiplication sign (`×`), later ones the letter `x`.** Match
both. Also anchor the item name to a single line — with `re.DOTALL` a lazy
`.+?` swallows the `Order summary\n-----` header into the first item.

## Locations: the rule differs by what was bought

**Consumables: the ship-to address IS the location.** Scott: *"the filament and
parts orders shipped to FL are definitely FL, unless I move them north."*
Filament, plates and hotends get used where they land, so an FL order is LRD
stock — file it there and earmark it.

**But even for consumables it is a DEFAULT, not a fact.** Scott: *"I also
seeded the LRD filament inventory with some SLN filament."* Spools have moved
north-to-south, so imported filament is **per-order provenance, not a per-site
count**, and the two sites cannot be reconciled from purchase records alone.
Only a physical count at each site settles it — so do not present imported
filament as a counted location total. This is the same distinction as
`[ESTIMATE]` versus a stocktake: the number is fine, the implied confidence is
what would be wrong.

**Equipment: the ship-to address is only where it ARRIVED.** The X1C shipped to
Dover in 2023 and now lives in Florida. A printer gets moved; its purchase
record says nothing about where it is today.

## Printers are equipment, not stock

These orders contain an **X1-Carbon Combo ($1,449)** and an **H2D AMS Combo
($2,099)**. Those belong in the Equipment tree as one-of instruments, per the
existing rule that instruments owned one-of and never consumed are not stock
lines. The consumables around them — plates, hotends, AMS parts — are stock.

## Naming: one part per SKU, keyed on Bambu's part number

Decided 2026-08-22. **Not** one part per material with colour in the
description — Scott: *"by part number, respecting the differences."*

Bambu puts a numeric code on every filament: `PLA Basic / Hot Pink (10204)`,
`ABS Black (40101)`, `PETG HF / Black (33102)`, `TPU 85A / Black (51107)`.
Hardware and accessories use letter codes instead — `AA187` for the M3 FHCS
pack, `ZH076` for the AMS Flipper. **That code is the IPN.**

**But the code alone is not unique — refill and spool share it.** The same
colour appears as `/ Refill / 1kg` and as `/ Filament with spool / 1 kg`, and
the difference is operational rather than cosmetic: a refill has no spool, so
it cannot be run without a reusable spool already in hand. Owning three refills
and no spare spool is not the same as owning three usable rolls, and a
catalogue that cannot express that is lying by omission.

So part identity is **(code, form)**:

    PLA Basic Hot Pink 10204, refill 1kg
    PLA Basic Hot Pink 10204, with spool 1kg

Same IPN `10204`, two parts, distinguished in the name. This is the same
principle as footprint being part identity for a component, and grade being
part identity for a fastener — the shared number is not the whole identity.

## Printers go to Equipment, not stock

Confirmed 2026-08-22. The **X1-Carbon Combo** ($1,449, order 2023-06-21) and
the **H2D AMS Combo** ($2,099, order 2025-11-22) are one-of instruments and
belong in the Equipment tree, never as consumable stock lines.

**The X1C is located at LRD**, not where its order shipped. Its purchase record
says Dover; it lives in Florida. Set the location from that fact, not from the
order.

## Still to do

The 12 confirmations have been located and the parser proven, but **the orders
are not yet imported**. Remaining: fetch the 8 unread bodies, run them through
the parser, and create POs the same way `mcmaster_import.py` does — idempotent
on the vendor order number, PLACED first and status moved by queryset
`.update()`, never `save()` on a completed order.

Also add `noreply@bambulab.com` to the overnight agent's vendor list so new
orders are swept automatically rather than needing another historical import.
