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

## Import DONE 2026-10-03: purchase history only

`scripts/bambu_import.py` brought in all 12 confirmations: **PO-0189 to PO-0200,
44 parts, 0 stock rows**. Verified by re-reading. Each PO's lines equal its
emailed subtotal, all are COMPLETE, and AA187 carries pack 20 in both fields.

- **Categories created:** `Shop/Consumables/Filament` (#142, 28 filaments and
  3 bundles), `Shop/Accessories/3D Printer` (#140, hotends, plates, glue,
  Flipper, screws), `Equipment/3D Printers` (#141, X1C and H2D, no stock rows).
- **PO `destination` = ship-to site.** 10 orders went to SLN and 2 (2026-02
  and 2026-03) to LRD. That is provenance only. Scott moved some SLN filament
  to LRD and does not know which, so the LRD count settles it, not these POs.
- **Bodies were transcribed, not parsed.** The Gmail MCP returns the body into
  context and cannot write it to disk, so `bambu_parse.py` had nothing to run
  on. The line data was read off the emails into
  `~/code/scripts/bambu_orders_1003.json` (PRIVATE repo, because it holds order
  numbers). The importer refuses any order whose lines do not sum to its
  emailed subtotal, which is the same checksum the parser relied on.
- **Discounts were allocated back to their lines.** The 2023-11 and 2024-03
  emails carry an order-level membership discount ($8 a spool). The 2025-08
  PLA-CF 4-roll bundle listed no per-roll price and was split evenly at
  $27.99 each.
- **2023 lines had no numeric code.** PETG-CF Black and PLA Basic Orange took
  31100 and 10300 from later orders. The part notes say "INFERRED".
- **TPU 85A (51107) and 90A (51103): the orders name no form.** 51103 was
  settled as with spool from the boxes at WS3 on 2026-10-03, and its grade (90A)
  is on the receipt.
- **Bundles are one unit each** (CMYK Lithophane, Gratitude 2x Black,
  Starter Classic). Their colors are unknown, and opened rolls count under
  their own color parts.

### Still open

- **Count at SLN.** Stock is created from the count, not from orders.
- **Count at LRD on arrival.** That is the only way to settle the
  undocumented SLN-to-LRD moves.
- ~~Shelf boxes no order explained~~ **Explained 2026-10-03.** Yellow, Magenta
  and Cyan with spool are the 2023 PLA CMYK Lithophane Bundle (PO-0190). Scott:
  *"all bambu filament was bought from bambu"*. The Hatchbox ABS is the only
  non-Bambu box, and where it was bought is not recorded.
- ~~Printer locations~~ **Done 2026-10-03.** H2D stock 879 at SLN (Scott, same day);
  X1C stock 880 at LRD (Scott, 2026-08-22). Both are located to the site only.
- Add `noreply@bambulab.com` to the overnight agent's vendor sweep.

### Why no stock rows

**The import must NOT create stock rows.** Scott, 2026-10-03: *"if we run the
import wont we end up with a lot of filament that has been used up?"* He is
right. `mcmaster_import.py` books every purchased unit as an `[ESTIMATE]` stock
row, which works for screws that sit in a drawer. Filament gets burned, and
some of these orders go back to 2023. Copying that pattern would put three
years of printed-away spools on the shelf. Plan (not yet built): import parts,
supplier parts and POs as **history only**. Lines are marked received, the
order is complete, and no StockItem is created. Stock comes only from Scott's
physical count at each site. A side benefit: bought minus on-hand gives the
consumption rate per SKU.

## Seeding the SLN filament — started 2026-10-03

Scott sent two photos of the unopened filament at SLN (a carton and a wire
shelf) and asked to start tracking it. Inventory state when measured: **no
filament part existed, no 3D-printing category, and Bambu Lab (company #29)
still had 0 supplier parts and 0 POs**, so the import above has not run.
Nothing has been created yet. Counts and the shelf location are still owed by
Scott, because a photo shows what each box is, not how many there are.

**Reading the form off a sealed box. Confirmed 2026-10-03 against two orders.**
- OLD rectangular labels: the Model/SKU suffix. `-SPLFREE` = refill, `-SPL` =
  with spool. Some old labels also print "With Spool" by the color dot.
- NEW oval side labels: a **ring printed around the color dot that reads "With
  Spool"**. No ring = refill. Checked against Pink 10203 (no ring, ordered as a
  refill) and Pumpkin Orange 10301 (ring, ordered with spool).
- Text on the oval labels is too small to read from a whole-shelf photo. Crop
  and zoom first. I read TPU "95A" off one and nearly put it in the record
  against the receipt, which says 90A (PO-0198). A blurry label is not a
  witness. When the receipt names the item, the receipt wins.

**SEEDED 2026-10-03: 19 sealed boxes at `SLN/Garage/WS3`** (location #623,
main garage beside the H2D), stock 881-895, `stocktake_date` set. Scott
confirmed the two photos show every box: a carton of 8 and 11 on the shelf.
The carton is the 2025-11 order (PO-0198). The H2D moved from bare SLN to
SLN/Garage on the same evidence. TPU 51103 renamed "with spool" (both boxes
carry the ring). Its SKU stays `51103` because that is the importer's
idempotency key. New parts: Yellow/Magenta/Cyan with spool (Cyan's old label
prints no code, so its IPN is blank) and Hatchbox ABS True Black.

**Tracking usage: no InvenTree plugin found** (searched 2026-10-03). The
standard tool is Spoolman (Donkie/Spoolman), with Bambu feeders such as
OpenSpoolMan and Bambuddy that read AMS trays and 3MF usage. A split was
proposed and is **not decided**: InvenTree counts sealed boxes per SKU, and a
spool moves to Spoolman when it is opened. Before relying on the feeders,
check whether the H2D/X1C firmware still lets third parties read the printer
without LAN/developer mode.
