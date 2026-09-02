"""Printer return follow-up: part #1057 notes + whether the replacement has printed.

Read-only. Written 2026-09-02 for the Staples-dropoff follow-up. Two questions in
one trip because both answers live on the Mini:

  1. What does the PART record say about the dead unit and the return? (The stock
     item that carried the "DEAD 2026-08-24" note was deleted by depleting it to
     zero -- see TRAPS.md -- so the part notes are the only surviving record.)
  2. Has the replacement actually printed since it landed 2026-08-26?

Q2 is the point of the exercise: the original failure went unnoticed for four
days because nothing watched the completed-job list. "The queue is accepting" is
a claim about CUPS; "a label came out" is a claim about the printer.

Usage:  itq run scripts/printer_return_check.py
"""

import os
import subprocess
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part  # noqa: E402

p = Part.objects.filter(pk=1057).first()
print(f"=== part #1057: {p.full_name if p else 'MISSING'}")
if p and p.notes:
    print(p.notes.strip())
print()

for label, cmd in [
    ("completed jobs", ["lpstat", "-W", "completed", "-o", "QL810W"]),
    ("queue state", ["lpstat", "-p", "QL810W"]),
]:
    print(f"=== {label}: {' '.join(cmd)}")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        out = (r.stdout + r.stderr).strip()
        print(out if out else "(no output)")
    except Exception as e:  # noqa: BLE001
        print(f"(failed: {e})")
    print()
