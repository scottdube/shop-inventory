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
