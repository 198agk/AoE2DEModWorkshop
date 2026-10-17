# -*- coding: utf-8 -*-
"""Exactly what would a display<->raw mirror rule have to handle?

Fix over v1: displayed_pierce_armour lives in the CREATABLE block (not Type50),
and the melee/pierce class preference must be single-class, not "first nonzero",
because displayed_melee_armour tracks class 4 specifically.
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
civs = tk._civs

seen = set()
units = []
for c in civs:
    for u in c["units"]:
        key = (u["id"], u.get("name"))
        if key in seen:
            continue
        seen.add(key)
        units.append(u)

has50 = sum(1 for u in units if u.get("type50"))
print("distinct units: %d | with a type50 block: %d | without: %d"
      % (len(units), has50, len(units) - has50))

def entry(entries, cls):
    for e in entries:
        if e["class"] == cls:
            return e["amount"]
    return None

def stats(label, get_disp, get_list, cls):
    buckets = Counter()
    agree = diverge = 0
    examples = []
    for u in units:
        disp = get_disp(u)
        raw = get_list(u) or []
        v = entry(raw, cls)
        if disp is None:
            buckets["no displayed field"] += 1
            continue
        if v is None:
            buckets["displayed but NO raw class-%d entry" % cls] += 1
            if disp != 0 and len(examples) < 6:
                examples.append((u["id"], u.get("name"), disp, None,
                                 [(e["class"], e["amount"]) for e in raw]))
        else:
            buckets["both present"] += 1
            if disp == v:
                agree += 1
            else:
                diverge += 1
                if len(examples) < 12:
                    examples.append((u["id"], u.get("name"), disp, v,
                                     [(e["class"], e["amount"]) for e in raw]))
    print()
    print("=== %s  (tracks raw class %d) ===" % (label, cls))
    for k, v in buckets.most_common():
        print("   %-42s %d" % (k, v))
    if buckets["both present"]:
        print("   of those both-present: agrees %d / diverges %d (%.1f%% agree)"
              % (agree, diverge, 100.0 * agree / (agree + diverge)))
    for e in examples:
        print("      id %-6s %-34s displayed=%-6s raw=%-5s list=%s" % e)

stats("displayed_attack",
      lambda u: (u.get("type50") or {}).get("displayed_attack"),
      lambda u: (u.get("type50") or {}).get("attacks"), 3)
stats("displayed_attack",
      lambda u: (u.get("type50") or {}).get("displayed_attack"),
      lambda u: (u.get("type50") or {}).get("attacks"), 4)
stats("displayed_melee_armour",
      lambda u: (u.get("type50") or {}).get("displayed_melee_armour"),
      lambda u: (u.get("type50") or {}).get("armors"), 4)
stats("displayed_pierce_armour",
      lambda u: u.get("displayed_pierce_armour"),
      lambda u: (u.get("type50") or {}).get("armors"), 3)

print()
print("=== do the units that carry an attack actually have type>=50? ===")
bad = [u for u in units
       if (u.get("type50") or {}).get("displayed_attack") not in (None, 0)
       and u.get("type", 0) < 50]
print("   units with a NONZERO displayed_attack but type < 50:", len(bad))
for u in bad[:8]:
    print("      id %-6s type=%-4s %s" % (u["id"], u.get("type"), u.get("name")))
print()
print("=== orphan attack units that are NOT buildings/empty ===")
for u in units:
    t50 = u.get("type50") or {}
    da = t50.get("displayed_attack")
    raw = t50.get("attacks") or []
    if da is not None and da != 0 and not any(e["class"] in (3, 4) for e in raw):
        print("      id %-6s type=%-4s %-34s displayed=%-4s attacks=%s"
              % (u["id"], u.get("type"), u.get("name"), da,
                 [(e["class"], e["amount"]) for e in raw]))
