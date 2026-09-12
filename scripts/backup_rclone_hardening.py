#!/usr/bin/env python3
"""Harden the gdrive leg of the nightly backup. Runs ON THE MINI.

2026-09-12 FAIL: "NO OFF-SITE COPY - every copy is on the same disk as the
database." Two independent legs failed the same night --  gdrive timed out and
the NAS mount was rejected -- and the verdict correctly refused to call that
survivable. The backup itself was fine: 720.8 MB archive, snapshot ok, 1174
parts.

THE GDRIVE HALF IS A SIZING PROBLEM, NOT A FAULT. subprocess timeout was a
hardcoded 1800 s against an archive that is 720.8 MB and grows ~1 MB/day, so
the leg needs 0.41 MB/s sustained and rises every night. It passed 09-10 and
09-11, failed 09-09 and 09-12. That is a margin that has already run out.

Two changes, both conservative:
  * timeout 1800 -> 5400 s. At 5400 the same archive needs 0.13 MB/s. Still
    bounded, so a genuinely wedged upload cannot hang the job forever.
  * --retries 5 --low-level-retries 20, so a dropped connection is retried
    inside rclone instead of failing the whole leg.

NOT changed, deliberately: the archive is a full 720 MB tar.gz every night and
that is the real long-term problem. Incremental or dedup backup is the actual
fix and is a design job, not a one-line patch. Raising the timeout buys room;
it does not solve growth.

    itq run scripts/backup_rclone_hardening.py
    itq run scripts/backup_rclone_hardening.py --commit
"""
import os
import shutil
import sys
import time

SRC = os.path.expanduser("~/.inventree/backup_inventree.py")
COMMIT = "--commit" in sys.argv

OLD = ('                    r = subprocess.run([RCLONE, "copy", staged, "gdrive:InvenTreeBackups/"],\n'
       '                                       capture_output=True, text=True, timeout=1800)\n')
NEW = ('                    r = subprocess.run([RCLONE, "copy", staged, "gdrive:InvenTreeBackups/",\n'
       '                                        "--retries", "5", "--low-level-retries", "20"],\n'
       '                                       capture_output=True, text=True, timeout=5400)\n')

src = open(SRC).read()

if NEW in src:
    print("already hardened — nothing to do")
    sys.exit(0)
if OLD not in src:
    print("✗ anchor not found; the rclone call has changed. Refusing to guess.")
    print("  Looked for:")
    print(OLD)
    sys.exit(1)

print("will replace:\n" + OLD)
print("with:\n" + NEW)

if not COMMIT:
    print("DRY RUN — nothing written. Re-run with --commit.")
    sys.exit(0)

bak = f"{SRC}.bak.{time.strftime('%Y%m%d-%H%M%S')}"
shutil.copy2(SRC, bak)
open(SRC, "w").write(src.replace(OLD, NEW, 1))

check = open(SRC).read()
ok = NEW in check and OLD not in check
import py_compile
try:
    py_compile.compile(SRC, doraise=True)
    compiles = True
except Exception as e:
    compiles = False
    print(f"✗ does not compile: {e}")

print(f"backup: {bak}")
print(f"patched={ok}  compiles={compiles}")
if not (ok and compiles):
    shutil.copy2(bak, SRC)
    print("✗ REVERTED")
    sys.exit(1)
print("✓ hardened")
