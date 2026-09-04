"""DEAD — superseded 2026-09-03 by `part_find.py --category <pathstring>`.

Kept as a marker because this script is the one that caused the damage, and the
next person to need "list a category" will look for exactly this filename.

What it did wrong: it printed `pk`, `name` and `created` for each part in a
category, and NOT `active` or stock. Ten of the 22 parts in the top-level `ICs`
tree are inactive merge tombstones. Without the active column they read as live
records, so NE555, ADUM1201 and PC817 each looked like a live cross-tree
duplicate. All three had been merged weeks before — #16 is literally named
"[merged 16]" and I read straight past it. That produced a three-option
taxonomy decision on Scott's queue, several rounds of chat, and no work.

Use the stable tool, which always prints active and stock and hides tombstones:

    itq run scripts/part_find.py --category ICs
    itq run scripts/part_find.py --category ICs --all     # show tombstones too
"""
raise SystemExit(__doc__)
