# Fabricated PCBs — what was ordered, and how to tell them apart

Forty bare boards across five JLCPCB orders since 2019. Two designs are now in
the catalogue. This exists so a stack of green boards found in a bin can be
identified rather than guessed at.

**The 2019 order is solved (2026-08-21).** It had been the one entry here with
no identification at all, because JLCPCB named the gerber with a content hash
and the shipping email carried nothing else. The answer was silkscreened on the
board the whole time: `Arduino Nano NRF24L01 adaptor`, with the author, the
licence and the repo URL, plus a panel code `2583209A-Y1-190313` whose trailing
digits are the fab date matching the order. **Read the board before mining the
paperwork** — a bare PCB usually carries its own provenance, and this one
survived seven years of it.

**Surplus boards now have a home (2026-08-21): `A3-R2C1`, long-term storage.**
Nine NRF24L01 adaptors and four minisplit CN105 adapters are filed there and
counted. The Rat GDO boards stay in `RB-12` because they belong to an active
project kit, which is a different thing.

The distinction that governs this, in Scott's words: **red bins are LIVE
storage** — things used regularly — and the bare boards kept there (`RB-06`)
are unetched copper-clad blanks awaiting the mill or the laser. Finished
fabricated boards are the far end of the same pipeline and do not belong in
the same place. Both get called "blank boards" in speech; the pipeline stage
is what separates them.

## The orders

| Order | Date | Gerber name | Qty | Merch | Total |
|---|---|---|---:|---:|---:|
| `W20190313241946` | 2019-03-12 | `0158016a7a36450d93c96a5692df10…` **= NRF24L01 adaptor** | 10 | $2.00 | $7.24 |
| `W202401071001106` | 2024-01-06 | `Gerber_PCB_FFB_Arduino_Yoke_1…` | 5 | $2.00 | $20.05 |
| `W202406142358683` | 2024-06-14 | `Gerber_G1000_nxi_v2_shield_rev…` | 10 | $29.50 | $67.62 |
| `W2026060711329921` | 2026-06-06 | `sln-shop-minisplit-cn105-adapt…` | 5 | $2.00 | $5.12 |
| `W2026062810308875` | 2026-06-28 | `Rat-RatGDO_Y7` | 10 | $5.00 | $14.59 |

Note how little the boards themselves cost — **shipping is most of every
order**. That is why ordering ten instead of five is close to free, and why
surplus accumulates without anyone deciding to accumulate it.

## Identifying them

| Design | Where the files are | In the catalogue? |
|---|---|---|
| **Rat GDO** — silkscreen `RatGDO OpenSource D1Mini-ESP32 v2.5.0 2023`, marks `SHT4x_I2C`, `Piezo 12v`, `BATT`, `GDO` | `my-rat-ratgdo/kicad_files/D1 Mini - ESP32/` | yes, part `[877]`, 7 on hand in RB-12 |
| **Shop minisplit CN105 adapter** | `sln-ha-config/electronics/kicad/sln-shop-minisplit-adapter/` and gerber zip `…_2026-06-07` | yes, part `[909]`, 4 in A3-R2C1 |
| **FFB Arduino Yoke** | not in any repo — third-party gerber zip | **no** |
| **G1000 NXi shield** | not in any repo — third-party gerber zip | **no** |
| **Arduino Nano NRF24L01 adaptor** — silkscreen `Arduino Nano NRF24L01 adaptor`, `github.com/markjb/NRF24L01_Adaptors`, panel code `2583209A-Y1-190313` | upstream repo (third-party, CC BY-SA 4.0); nothing local | yes, part `[938]` |

## Two gaps worth knowing before the bin walk

**The Cessna sim has 15 boards fabbed and none on its BOM.** BO-0006 lists a
MEGA2560, two SG90 servos and a proto shield. The force-feedback yoke (5) and
the G1000 NXi shield (10) are both flight-sim hardware bought in 2024, and
`MC-T3` is described as *"Connectors and ribbon cable staged for the CESSNA
FLIGHT SIMULATOR (BO-0006)"* while holding **zero recorded lines**. That tray
and those boards are the same undocumented layer of one project.

**The two sim boards have different futures — decided 2026-08-20.**

| Board | Status |
|---|---|
| **G1000 NXi shield** (10 pcs, 2024-06) | **A real project, to be documented incrementally.** The design was bought and the gerbers sent straight to JLCPCB, but the board is large — roughly 7×10 or 8×10 cm — and Scott populated it himself with a lot of components. Buying the *design* does not make the *build* a purchase. No build order yet purely for bandwidth; pick away at it. |
| **FFB Arduino Yoke** (5 pcs, 2024-01) | **Dead end. Not needed.** Do not create a project, do not chase the boards, do not treat their absence as a gap. |

**MySensors is dead — decided 2026-08-21.** The nine NRF24L01 adaptor boards,
the loose nRF24L01 radios and a Sensebender Gateway are all one 2018-19
MySensors cluster. Scott: *"disperse it to loose stock... that project's dead
in the water. Gone."* So: **no project, no build order, no kit bin.** The parts
are good stock for anything else and stay as loose stock; each carries a note
saying where it came from and that the project is dead. Recorded for the same
reason as the FFB yoke below — so the next person to find nine identical
adaptor boards does not read them as an undocumented project awaiting
reconstruction, and does not go looking for the rest of it.

**The minisplit CN105 adapter has boards but no project.** Five were fabbed
2026-06-06 from a design that lives in `sln-ha-config`, with an ADR
(`015-shop-minisplit-jrre-cut-remote-temp.md`) and running ESPHome configs —
but no part, no build order, and no stock record.

## Method note

Order contents came from the JLCPCB **shipping notification emails**, which list
gerber name and quantity. The web order-history page shows totals but returns
"No Data" for the item list on older orders, so the mail archive is the better
source here.
