# binscan

Photograph a drawer, get an estimate. Runs on the LRD Mac Mini, reachable at
`http://binscan.internal` (= 192.168.50.10) behind Caddy on port 80.

**This directory is the source of truth as of 2026-08-22.** Before that the code
existed only on the Mini, with no repo and no backup, and a session lost track
of it entirely — see `../docs/binscan.md` and the TRAPS entry.

## Deploy

    itq push binscan/app.py       /Users/scottdube/binscan/app.py
    itq push binscan/providers.py /Users/scottdube/binscan/providers.py
    launchctl kickstart -k gui/$(id -u)/com.binscan

The LaunchAgent is `com.binscan.plist`; it runs
`uvicorn app:app --host 0.0.0.0 --port 8002` from `~/binscan/venv`.

## Configuration

Keys come from the environment, loaded from `~/binscan/env` (mode 600, **not in
this repo**): `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `INVENTREE_TOKEN`,
optionally `INVENTREE_URL`, `OLLAMA_URL`, `BINSCAN_WRITES`.

`BINSCAN_WRITES=1` is the only thing that lets it write to InvenTree, and **it
is ON** — an earlier version of this file said otherwise, from the docstring's
intent rather than from `/healthz`. Read the running service, not the comment.

What makes that safe is `AUTO_CONF`, the set of confidence levels allowed to
write with no human confirming. **It is empty and must stay empty.** It held
`{"high"}` until 2026-08-22, when the run log turned out to contain five HIGH
confidence readings that were wrong — worst case a five-piece drawer called
~10. Nothing had been written only because the UI never called `/api/record`.
A model's confidence describes how clearly it could see, not whether it was
right, and the log shows those two come apart.

## What it is for, and what it is not good at

See `../docs/binscan.md` for the measured accuracy. Short version: fill
estimates are reliable below about five pieces and 25-40% wrong above twenty,
because occlusion beats the model as soon as parts overlap. Identity read off a
printed tag is a different and far more reliable problem.
