# Amazon import reconcile — 2026-08-19

Run overnight after two import gaps turned up by accident during the Rat GDO
work (a JST XH connector kit from 2023 and a Glarks header kit from 2024, both
real purchases with no trace in the catalogue). The question: how many more?

**Answer: fewer than feared.** Four confirmed shop-relevant gaps, three
marginal ones, out of ~330 recorded orders. The import is broadly sound.

## Confirmed gaps — real shop items, no catalogue record

| Ordered | Item | Price |
|---|---|---|
| 2023-08-07 | **SHNITPWR 12V 30A 360W** AC-DC supply | $22.99 |
| 2023-08-07 | **Bergen Industries PS615143** appliance/power-tool cord, 6 ft 14 AWG 15A 1875W | $7.37 |
| 2024-01-07 | **SHNITPWR 24V 10A 240W** AC-DC supply | — |
| 2024-01-10 | **SHNITPWR 24V 10A 240W** AC-DC supply *(second unit, three days later)* | — |

Both SHNITPWR 12 V and 24 V bricks are the kind of thing that ends up powering
a bench project and then cannot be found. Worth adding. Note there are **two**
24 V units, not one.

## Marginal — real purchases, probably deliberately not inventoried

| Ordered | Item | Why it may not belong |
|---|---|---|
| 2024-04-14 | Milwaukee 48-32-4440 ECX insert bits, 2-pack | hand-tool consumable |
| 2025-07-25 | 1/4 HP lathe bandsaw | equipment, not stock |
| 2026-04-01 | PERFEIDY 19V 6.3A NUC charger | IT kit, not shop |

## Already fixed tonight

| Ordered | Item | Action |
|---|---|---|
| 2023-07-31 | SWANAMB 460-pc JST-XH2.54 connector kit | created [887], split into 11 parts |
| 2024-06-19 | Glarks 80-pc double-row female header sockets | created [907] |

## Checked and present — no action

Raspberry Pi Zero WH, Smraza 5.1V, Taiss rotary encoders, Hosyond servos, DROK
delay relay, QimKero HDMI, ADRESUNO WS2812B, Seloky LM2596, AITRIP Supermini
ESP32-S3, Comidox B0505S, AITRIP FT232RL, EC Buying XY6020L, and ~30 others
across the 2016–2026 range.

## Method, and a better one for next time

This pass worked from **Gmail order-confirmation subjects**, matched against
part names by distinctive token. Two problems with that:

1. **Amazon changed the subject format around 2026-07-16.** Older mails say
   `Ordered: "<product title>..."`; newer ones say `Ordered: 1 Electronics
   item` with no title at all. Anything after that date is invisible to a
   subject-based sweep.
2. **Fuzzy matching produced false "found" results**, which is the dangerous
   direction — a false match hides a real gap. `SHNITPWR 12V Power Supply`
   scored against *DROK Time Delay Relay*; `Raspberry Pi Zero WH` against an
   *HDMI adapter*; `1/4 HP Lathe BandSaw` against a *threadmill*. Every
   apparent match needs its brand token checked directly before being believed.

**The better tool, found late:** Amazon exposes a searchable order history at

```
https://www.amazon.com/your-orders/search?search=<terms>
```

It returns **full product titles** for every matching order, works back to at
least 2016, and is immune to the subject-format change. A future reconcile
should drive from there — iterate the catalogue's supplier records against it —
rather than from the mail archive.

## Scope not covered

- Orders after 2026-07-16 whose subjects carry no title (roughly six weeks).
- Non-Amazon vendors. AliExpress in particular has 42 supplier parts with
  composite SKUs and no derivable links, and was not examined here.

## Addendum 2026-08-21 — the sweep had a category blind spot

A bag of TOGGLER SnapToggle anchors came off the plywood table with no
catalogue record. Scott: *"those were ordered from Amazon, so that order's out
there. It just probably got skipped in the import."* Correct — the order was
sitting in Gmail in the **old, title-bearing subject format**, the exact format
this sweep could read.

It was not missed by the matcher. **It was never in scope.** This pass hunted
electronics — power supplies, connector kits, dev boards — and a drywall anchor
is not one. Nothing was wrong with the method; the *question* was narrower than
the catalogue turned out to be.

That matters now in a way it did not in August, because the shop has since
started inventorying **hardware**: two fastener cabinets, a McMaster import, a
Hardware category. Amazon hardware orders are a whole gap class nobody has
looked for, and they will keep surfacing one bag at a time on benches.

**The lesson is about scoping a sweep, not about this anchor.** A reconcile
that finds "fewer gaps than feared" has only established that for the
categories it asked about. Record what a sweep did NOT cover, or its clean bill
of health gets read as covering everything. This one read that way for two
days.

### Amazon has two confirmation formats, and the old one carries no line items

Both were seen in the same search:

| Format | Body contains |
|---|---|
| Newer (seen 2025-07) | full untruncated product title, quantity, per-line price, ship-to city |
| Older (seen 2025-04) | **no line items at all** — ship-to city and an order total only |

The old format leaves the truncated *subject* as the only description of what
was bought, and the subject is where Amazon truncates. So an old-format mail
can prove an order happened and still not say what was in it or how many.

Also: **an order total of $0.00 is a replacement or a credit, not a free
item.** It is a real shipment of real goods, and skipping it as noise loses
stock that physically arrived.

