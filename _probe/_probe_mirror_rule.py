# -*- coding: utf-8 -*-
"""Which selector rule does each Displayed* field actually track?

Candidate rules, applied to the raw attacks[]/armors[] list:
  P34  first PRESENT (any amount) among classes [3,4]
  P43  first PRESENT among [4,3]
  N34  first NONZERO among [3,4]
  N43  first NONZERO among [4,3]

The mirror must use the rule that best reproduces shipped data, because it has
to move exactly the entry the displayed value currently tracks.
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
tk.version
seen, units = set(), []
for c in tk._civs:
    for u in c["units"]:
        k = (u["id"], u.get("name"))
        if k not in seen:
            seen.add(k)
            units.append(u)

def pick(entries, cands, nonzero):
    for cls in cands:
        for e in entries:
            if e["class"] == cls and (e["amount"] != 0 or not nonzero):
                return cls, e["amount"]
    return None, None

RULES = [("P34", [3, 4], False), ("P43", [4, 3], False),
         ("N34", [3, 4], True), ("N43", [4, 3], True)]

def rate(label, get_disp, get_list):
    print()
    print("=== %s ===" % label)
    best = None
    for name, cands, nz in RULES:
        eq = ne = incomparable = 0
        for u in units:
            d = get_disp(u)
            if d is None:
                incomparable += 1
                continue
            cls, val = pick(get_list(u) or [], cands, nz)
            if val is None:
                incomparable += 1
                continue
            if d == val:
                eq += 1
            else:
                ne += 1
        if eq + ne:
            pct = 100.0 * eq / (eq + ne)
            print("   %-4s candidates=%-8s nonzero=%-5s agree %-5d diverge %-4d  %.2f%%"
                  % (name, cands, nz, eq, ne, pct))
            if best is None or pct > best[1]:
                best = (name, pct, eq, ne)
    print("   -> best: %s (%.2f%%)" % (best[0], best[1]))
    return best

rate("displayed_attack",
     lambda u: (u.get("type50") or {}).get("displayed_attack"),
     lambda u: (u.get("type50") or {}).get("attacks"))
rate("displayed_melee_armour",
     lambda u: (u.get("type50") or {}).get("displayed_melee_armour"),
     lambda u: (u.get("type50") or {}).get("armors"))
rate("displayed_pierce_armour",
     lambda u: u.get("displayed_pierce_armour"),
     lambda u: (u.get("type50") or {}).get("armors"))

print()
print("=== how the CURRENT attack_entry selector behaves ===")
print("   _class_selectors uses the binding's class_candidates, and _targets_for_unit")
print("   yields the first PRESENT class in that order (amount is not consulted).")
print("   attack_classes.attack candidates = [3, 4]  -> rule P34")
print("   attack_classes.armour candidates = [4, 3]  -> rule P43")
