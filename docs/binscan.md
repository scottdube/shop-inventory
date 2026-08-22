# binscan — photograph a drawer, get a fill estimate

**It is not in this repo, and that is why it went missing.** Recovered
2026-08-22 after Scott referred to it and nothing in `~/code` matched; the only
trace on this laptop was a screenshot in `~/Downloads` of Safari failing to
resolve the hostname.

## Where it lives

| | |
|---|---|
| host | the LRD Mac Mini — `binscan.internal` resolves to `192.168.50.10` |
| code | `binscan/` in this repo as of 2026-08-22; deployed to `/Users/scottdube/binscan` |
| process | `uvicorn app:app --host 0.0.0.0 --port 8002`, LaunchAgent `com.binscan.plist` |
| public port | 80, via Caddy (`com.caddy.proxy.plist`) |
| state | `log.jsonl` (run history), `shots/` (submitted photos), `env` (API keys, mode 600) |
| versioning | `app.py.prelog`, `app.py.prepicker`, `app.py.prewrite` — copies, by hand |

**Phone access works.** A screenshot dated 2026-08-18 shows Safari failing to
resolve the hostname, and that was taken as the current state — wrongly. Scott,
2026-08-22: *"that photo must have been before we resolved the problem because
I'm on binscan right now."* A dated screenshot records the moment it was taken,
not the state of the world; treat one as evidence about the past only.

## What it does, and what it deliberately does not

Pick a drawer, photograph it, pick a vision provider, get a fullness estimate.
**Read-only to InvenTree** — it reads locations and parts and writes no stock,
on the stated grounds that a bin-check tool which silently writes bad numbers is
worse than no tool. Every run is logged for comparison at `/log`.

From its docstring: *the model is NOT asked to identify the part — the drawer
address already determines that, so its only job is "how full is this", which is
the thing vision is actually good at.* It is told to report LOW confidence on
heaps, *because occlusion makes 200 small parts look like 150 and prompting
can't fix physics.*

Providers configured: `anthropic` (claude-sonnet-5) **available**; `ollama`
(qwen2.5vl:7b) and `openai` (gpt-4o) present but not configured.

## Measured accuracy — 13 runs 2026-08-16, six with ground truth

| actual | anthropic | haiku-4.5 | sonnet-5 |
|---|---|---|---|
| 4 | off by 0 | off by 1 | off by 0 |
| 4 | off by 1 | **off by 41** | off by 0 |
| 5 | off by 0 | off by 5 | off by 0 |
| 20 | off by 15 | off by 5 | off by 5 |
| 65 | off by 15 | off by 5 | off by 25 |

**Usable below about five. Unreliable above about twenty**, where the error runs
25-40% and does not degrade predictably — the 41-off case was a four-piece
drawer read as forty-five. This is the measurement behind "photographs show
identity, not quantity": the rule is not superstition, it has a shape, and the
shape is that occlusion beats the model as soon as parts overlap.

## The identify mode — added 2026-08-22

**The record is consulted before the camera.** Picking a drawer calls
`/api/drawer`, which is free and instant and reports what InvenTree already
holds for it — counting stock in the drawer *or any descendant*, so a drawer
holding an assortment kit does not read as empty. Scott: *"look to see if the
bin has something assigned already before you have AI go look for it."*

The drawer's state then picks the mode, so there is no toggle to set wrongly:

| drawer state | job | what runs |
|---|---|---|
| already assigned | how many are there | the original estimate flow |
| nothing on record | which part is this | `/api/identify` |

`/api/identify` asks the model to **read text, not to identify the part** — the
McMaster bag tag, any Brady or handwritten label, any stamping. Matching against
the 48 unlocated rows happens in Python in `match_reading()`, because a model
asked to choose from a candidate list always chooses, while a number either
matches a SKU or does not. Results are graded `definite` (tag matches one SKU
exactly), `probable`, or `ambiguous`, and the basis is reported — `tag`,
`partial-tag`, `label-text`, `tag-no-match`, `nothing-legible`.

The model is told to transcribe rather than correct, and to write `?` for a
character it cannot read. A plausible completion of a part number is worse than
a short answer, because a wrong McMaster number matches a real and different
part.

**Still read-only.** It proposes; nothing is written. Seven matcher cases pass,
including the one that caught a real bug: a drawer label reading `M3 .5 x20`
matched an *M6* x 20 socket head, because the thread regex expected McMaster's
`M6 x` spelling and found no thread at all in the label's, leaving length as the
only evidence.

## Why the original design did not solve the B1/B2 walk

The walk needs the drawer address to be an OUTPUT. binscan assumes it is an
INPUT — *"the drawer address already determines that"* — which is true for every
cabinet except the two where the assignment is missing. Asking it what a B1
drawer holds asks the one question it was built not to answer.

**The extension that would work** is reading the McMaster bag tag Scott kept
inside most drawers. That is text on a printed label, which is the case
photographs ARE reliable for, and the number matches exactly one of the 48
unlocated rows. It would need a second prompt and endpoint, stay read-only, and
propose matches for confirmation rather than writing them — same discipline as
`docs/b1-b2-worksheet.md`. Not built.

## Risks worth acting on

- **No version control and no backup.** One `rm` loses it, and it took a
  screenshot and a DNS lookup to find it at all.
- **`env` holds API keys** on a machine whose backups have silently broken
  before. Not in this repo, correctly — but not anywhere else either.
- Runs from the internal disk deliberately: anything under `/Volumes` needs a
  TCC grant to run from launchd, which is what silently broke the InvenTree
  backup for weeks.
