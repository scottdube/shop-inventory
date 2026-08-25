"""Print the last-po-sweep marker and open-decision count from pending_decisions.md.

Read-only. Exists so the daytime sweep can learn its sweep window through the
one stable `itq run` command shape instead of a hand-built ssh/cat line.
"""

import pathlib
import re

QUEUE = pathlib.Path("/Volumes/4TB_Removable/inventree/pending_decisions.md")


def main() -> None:
    if not QUEUE.exists():
        print(f"MISSING: {QUEUE}")
        return
    text = QUEUE.read_text()
    m = re.search(r"<!--\s*last-po-sweep:\s*(\d{4}-\d{2}-\d{2})\s*-->", text)
    print(f"last-po-sweep: {m.group(1) if m else 'NONE'}")
    open_items = re.findall(r"^- \[ \] .*$", text, re.M)
    print(f"open decisions: {len(open_items)}")
    for line in open_items[-10:]:
        print(f"  {line}")


if __name__ == "__main__":
    main()
