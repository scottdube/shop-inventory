#!/bin/bash
# Wrapper so the service picks up ~/binscan/env without secrets in the plist.
set -a
[ -f "$HOME/binscan/env" ] && . "$HOME/binscan/env"
set +a
cd "$HOME/binscan"
exec ./venv/bin/uvicorn app:app --host 0.0.0.0 --port 8002
