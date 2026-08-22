# binscan — photograph a drawer, get a fill estimate

**It is not in this repo, and that is why it went missing.** Recovered
2026-08-22 after Scott referred to it and nothing in `~/code` matched; the only
trace on this laptop was a screenshot in `~/Downloads` of Safari failing to
resolve the hostname.

## Where it lives

| | |
|---|---|
| host | the LRD Mac Mini — `binscan.internal` resolves to `192.168.50.10` |
| code | `/Users/scottdube/binscan` — **not a git repo**, no remote, not backed up |
| process | `uvicorn app:app --host 0.0.0.0 --port 8002`, LaunchAgent `com.binscan.plist` |
| public port | 80, via Caddy (`com.caddy.proxy.plist`) |
| state | `log.jsonl` (run history), `shots/` (submitted photos), `env` (API keys, mode 600) |
| versioning | `app.py.prelog`, `app.py.prepicker`, `app.py.prewrite` — copies, by hand |

**The hostname does not resolve from Scott's phone** (screenshot 2026-08-18,
Safari "server can't be found") though it resolves from this laptop. Whatever
serves `.internal` is not reaching the phone's resolver. Unfixed.

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

## Why it does not solve the B1/B2 walk

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
