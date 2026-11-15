#!/usr/bin/env python3
"""Prune the gdrive leg of the nightly backup to KEEP_LOCAL. Runs ON THE MINI.

Found 2026-11-15 while the SLN NAS (Big_Brother, one 3 TB disk) was filling.
The nightly job uploads one full archive to gdrive:InvenTreeBackups/ and never
deletes one: rclone_prune() was written for the NAS leg (2026-11-09) and only
the NAS leg calls it. Measured 2026-11-15: 94 archives in Drive, 2026-08-16 to
2026-11-15, 65.6 GB, growing ~0.99 GB a night. Active Backup for Google
Workspace on the NAS then stores every one of them a second time, so the Drive
leg was quietly costing NAS space too (network-docs/docs/backup-plan.md step 3,
network-docs/docs/incidents/sln-nas-volume-full-20261115.md).

The change: after a successful gdrive upload, call the same
rclone_prune(remote, "inventree_*.tar.gz", KEEP_LOCAL) the NAS leg calls, in
the same try/except, so the Drive leg matches the NAS leg at 14.

Rejected:
  * An age-based rclone delete (--min-age 14d). Count-based is what
    rclone_prune already does, for the reason in its docstring: a run of failed
    nights must never empty the remote.
  * Pruning before the upload. The prune sits inside `if rc == 0`, so a failed
    upload deletes nothing and the 14 that exist stay.
  * Keeping monthly copies on Drive. Monthlies already live on the Mini (12);
    the plan sets Drive at 14 like the NAS.

Deletes go to Drive's Trash (rclone's drive backend defaults to use_trash), so
they are recoverable from Drive Trash for 30 days, and the NAS's Active Backup
keeps its copies 30 days as well.

    itq run scripts/backup_drive_prune.py                 dry run: diff + what would go
    itq run scripts/backup_drive_prune.py --commit        patch the script
    itq run scripts/backup_drive_prune.py --commit --prune-now   patch, then prune Drive now
"""
import os
import py_compile
import shutil
import subprocess
import sys
import time

SRC = os.path.expanduser("~/.inventree/backup_inventree.py")
RCLONE = "/opt/homebrew/bin/rclone"
REMOTE = "gdrive:InvenTreeBackups"
PATTERN = "inventree_*.tar.gz"
KEEP = 14   # KEEP_LOCAL in the backup script
COMMIT = "--commit" in sys.argv
PRUNE_NOW = "--prune-now" in sys.argv

OLD = ('                        offsite_ok.append("gdrive")\n'
       '                        log(f"  gdrive: uploaded in {secs:.0f}s")\n')
NEW = ('                        # Same count-based prune as the NAS leg (added 2026-11-15:\n'
       '                        # Drive had never been pruned, 94 archives / 65.6 GB).\n'
       '                        try:\n'
       '                            rclone_prune("gdrive:InvenTreeBackups", "inventree_*.tar.gz", KEEP_LOCAL)\n'
       '                        except Exception as e:\n'
       '                            log(f"  gdrive: prune skipped - {e}")\n'
       '                        offsite_ok.append("gdrive")\n'
       '                        log(f"  gdrive: uploaded in {secs:.0f}s")\n')


def drive_listing():
    r = subprocess.run([RCLONE, "lsf", REMOTE, "--include", PATTERN, "--format", "sp"],
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        print(f"✗ rclone lsf failed: {r.stderr.strip()[-300:]}")
        sys.exit(1)
    rows = [l.split(";", 1) for l in r.stdout.splitlines() if l]
    return sorted((name, int(size)) for size, name in rows)


def show_plan(rows):
    gone, kept = rows[:-KEEP], rows[-KEEP:]
    gb = lambda rs: sum(s for _, s in rs) / 1e9
    print(f"Drive {REMOTE}: {len(rows)} archives, {gb(rows):.1f} GB")
    print(f"  keep {len(kept)}: {kept[0][0] if kept else '-'} .. {kept[-1][0] if kept else '-'}")
    print(f"  delete {len(gone)} ({gb(gone):.1f} GB): "
          f"{gone[0][0] if gone else '-'} .. {gone[-1][0] if gone else '-'}")
    return gone


src = open(SRC).read()
rows = drive_listing()
if len(rows) < KEEP + 1:
    print(f"only {len(rows)} archives in Drive; nothing to prune")
gone = show_plan(rows)

if NEW in src:
    print("script already patched")
elif OLD not in src:
    print("✗ anchor not found; the gdrive block has changed since 2026-11-15. Refusing to guess.")
    sys.exit(1)
else:
    print("\n--- patch ---")
    print("".join("- " + l + "\n" for l in OLD.splitlines()))
    print("".join("+ " + l + "\n" for l in NEW.splitlines()))
    if not COMMIT:
        print("DRY RUN: nothing changed. Re-run with --commit.")
        sys.exit(0)
    bak = f"{SRC}.bak.{time.strftime('%Y%m%d-%H%M%S')}"
    shutil.copy2(SRC, bak)
    open(SRC, "w").write(src.replace(OLD, NEW, 1))
    try:
        assert NEW in open(SRC).read()
        py_compile.compile(SRC, doraise=True)
    except Exception as e:
        shutil.copy2(bak, SRC)
        print(f"✗ REVERTED to {bak}: {e}")
        sys.exit(1)
    print(f"✓ patched {SRC} (backup {bak}), compiles")

if PRUNE_NOW and COMMIT:
    if not rows or rows[-1][0] < f"inventree_{time.strftime('%Y-%m-%d')}":
        print("✗ newest Drive archive is not from today; refusing to prune without a fresh copy")
        sys.exit(1)
    fails = 0
    for name, _ in gone:
        r = subprocess.run([RCLONE, "deletefile", f"{REMOTE}/{name}"],
                           capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            fails += 1
            print(f"  ✗ {name}: {r.stderr.strip()[-200:]}")
    print(f"deleted {len(gone) - fails} of {len(gone)}")
    print("after:")
    show_plan(drive_listing())
