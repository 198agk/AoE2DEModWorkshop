"""Locate a real 'set' Resource Modifier row (type 1, B=0, C=-1).

The shapes probe needs one, and hardcoding guessed tech ids was how its 'set'
branch silently checked nothing while the summary still claimed all three
operations were covered.
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import aoe2mod.api as A

tk = A.open_toolkit()
tk._ensure()
ntech = len(tk._tech_records())
hits = []
for tid in range(ntech):
    for row in tk.effects(tid)["rows"]:
        if row["resource"] and row["operation"] == "set":
            hits.append((tid, row["index"], row["target_label"], row["value"],
                         row["editable"]))
print("type 1 with B=0 (set), total rows: %d" % len(hits))
for h in hits[:15]:
    print("  tech %-5d cmd %d  %-28s %-10r editable=%s" % h)
