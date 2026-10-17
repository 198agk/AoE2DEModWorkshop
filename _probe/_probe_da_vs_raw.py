# -*- coding: utf-8 -*-
"""Is DisplayedAttack ALWAYS equal to the unit's raw base attack entry?

If yes, `unit.stat displayed_attack` is only half an edit: the panel number and
the damage maths disagree after it.  If no, some units legitimately differ and a
blind mirror would be wrong.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import sys
from collections import Counter
root = _HERE_PATH()
sys.path.insert(0, root)
from aoe2mod import api as A

tk = A.open_toolkit()
tk.version                   # forces _ensure(); search() alone does NOT load
civs = tk._civs
print("civs:", len(civs))

seen = {}
agree = Counter()
disagree = []
no_base = []

for u in (u for c in civs for u in c["units"]):
    t50 = u.get("type50")
    if not t50:
        continue
    da = t50.get("displayed_attack")
    base = None
    for want in (3, 4):
        for a in t50["attacks"]:
            if a["class"] == want and a["amount"] != 0:
                base = (want, a["amount"])
                break
        if base:
            break
    key = (u["id"], u.get("name"))
    if key in seen:
        continue
    seen[key] = 1
    if base is None:
        no_base.append((u["id"], u.get("name"), da))
        continue
    if da == base[1]:
        agree[base[0]] += 1
    else:
        disagree.append((u["id"], u.get("name"), da, base))

print("distinct units examined :", len(seen))
print("displayed == raw base   :", sum(agree.values()), " by class:", dict(agree))
print("displayed != raw base   :", len(disagree))
print("displayed set but NO raw class-3/4 entry:", len(no_base))
for d in disagree[:25]:
    print("   id %-6s %-34s displayed=%-8s raw class %s = %s" % (d[0], d[1], d[2], d[3][0], d[3][1]))
for d in no_base[:10]:
    print("   NOBASE id %-6s %-34s displayed=%s" % d)
