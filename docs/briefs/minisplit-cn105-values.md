# Brief for the Cowork project — Shop Mini-Split CN105 Adapter

**Ask:** four component values that the KiCad design does not specify.

---

## The board

CN105 service-port adapter for the shop Mitsubishi **MSZ-GS36NA2-U1** mini-split.
Seeed **XIAO ESP32-C6** plus a **BSS138 4-channel bidirectional level shifter**,
running the `echavet/MitsubishiCN105ESPHome` fork (platform `cn105`).

- Covered by **SLN ADR-015** — JRRE jumper cut per Mitsubishi AN 3048, plus
  Sonoff-driven remote temperature. Accepted 2026-06-17.
- KiCad source: `sln-ha-config/electronics/kicad/sln-shop-minisplit-adapter/`
- Gerbers: `sln-ha-config/electronics/gerber/sln-shop-minisplit-cn105-adapter_2026-06-07`
- **5 boards fabbed**, JLCPCB order `W2026060711329921`, 2026-06-06

## The problem

The schematic went to fab carrying **KiCad's placeholder values**. `C`,
`C_Polarized` and `R` are library symbol names, not specifications:

```
C1  Value="C_Polarized"   footprint CP_Radial_D8.0mm_P3.50mm
C2  Value="C"             footprint C_Radial_D5.0mm_H11.0mm
R1  Value="R"             footprint R_Axial_DIN0207
D1  Value="LED"           footprint LED_D3.0mm
```

Fabrication didn't care — a fab house only needs copper and drill files — but
nothing now records what to populate.

## What's needed

| # | Ref | What it is | Question |
|---|---|---|---|
| 1 | **C1** | polarized electrolytic, 8 mm can, 3.5 mm lead pitch | capacitance **and voltage rating**? |
| 2 | **C2** | non-polarized ceramic, 5 mm disc | capacitance? |
| 3 | **R1** | axial, DIN0207 (¼ W) | resistance? *Believed* to be D1's series resistor — that is inference from the schematic, not something it states. |
| 4 | **D1** | 3 mm LED | colour, and what does it indicate — power, link, activity? |

## Working hypothesis — explicitly unconfirmed

**C1 ≈ 470 µF, C2 ≈ 0.1 µF.** Plausible against the footprints, but this is a
recollection ("not positive"), not a record.

**Please confirm or correct these rather than treat them as given.**

## If the answer isn't there

**Say so plainly.** A gap gets recorded as a gap. A plausible number that nobody
re-checks is worse than a blank, because the blank still asks to be filled — and
that is exactly how this board ended up fabbed with no values in the first place.

## Bonus, if the docs cover it

**J1** is a 4-pin 2.54 mm male header carrying the CN105 cable. Presumably
5 V / GND / TX / RX — confirm the **pinout and pin order**?

---

*Answers go to InvenTree part `[908] Shop Minisplit CN105 Adapter`, build
`BO-0013`. Nothing is on the BOM for these four positions until confirmed.*
