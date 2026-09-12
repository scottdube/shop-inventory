#!/usr/bin/env python3
"""Make the gdrive leg say what it is doing. Runs ON THE MINI.

2026-09-12: the leg failed twice in four nights and the log said only

    gdrive: FAILED - ... timed out after 1800 seconds

which cannot distinguish "uploading too slowly" from "retrying a failing
upload over and over". Both look like a timeout from outside. The manual retry
that day was equally mute: `--stats 60s --stats-one-line` printed NOTHING,
because rclone emits stats at INFO level and its default is NOTICE.

So the stats flags already in use were decorative. Adding -v turns them on.

This is diagnosis capacity, not behaviour: no destination, retry count or
timeout changes. The next failure should be readable without anyone
reconstructing it from interface counters -- which is what was tried on
2026-09-12, and it gave a wrong answer.

    itq run scripts/backup_verbose_logging.py
    itq run scripts/backup_verbose_logging.py --commit
"""
import os
import shutil
import sys
import time
import py_compile

SRC = os.path.expanduser("~/.inventree/backup_inventree.py")
COMMIT = "--commit" in sys.argv

OLD = ('                    r = subprocess.run([RCLONE, "copy", staged, "gdrive:InvenTreeBackups/",\n'
       '                                        "--retries", "5", "--low-level-retries", "20"],\n'
       '                                       capture_output=True, text=True, timeout=5400)\n')
NEW = ('                    r = subprocess.run([RCLONE, "copy", staged, "gdrive:InvenTreeBackups/",\n'
       '                                        "--retries", "5", "--low-level-retries", "20",\n'
       '                                        "-v", "--stats", "120s", "--stats-one-line"],\n'
       '                                       capture_output=True, text=True, timeout=5400)\n')

src = open(SRC).read()
if NEW in src:
    print("already verbose — nothing to do")
    sys.exit(0)
if OLD not in src:
    print("✗ anchor not found. Refusing to guess.")
    sys.exit(1)

if not COMMIT:
    print("would add: -v --stats 120s --stats-one-line")
    print("DRY RUN — nothing written. Re-run with --commit.")
    sys.exit(0)

bak = f"{SRC}.bak.{time.strftime('%Y%m%d-%H%M%S')}"
shutil.copy2(SRC, bak)
open(SRC, "w").write(src.replace(OLD, NEW, 1))

check = open(SRC).read()
ok = NEW in check
try:
    py_compile.compile(SRC, doraise=True)
    compiles = True
except Exception as e:
    compiles = False
    print(f"✗ does not compile: {e}")

print(f"backup: {bak}\npatched={ok}  compiles={compiles}")
if not (ok and compiles):
    shutil.copy2(bak, SRC)
    print("✗ REVERTED")
    sys.exit(1)

# rclone writes stats to stderr; confirm the script logs stderr on failure
import re
tail = re.search(r'gdrive: FAILED - \{r\.stderr[^\n]*', check)
print(f"stderr is logged on failure: {bool(tail)}")
print("✓ verbose")
