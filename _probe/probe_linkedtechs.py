# -*- coding: utf-8 -*-
"""What do the third-party dat-layer JSON overrides actually change?

The corpus cannot attribute an in-game effect to a JSON override, because every
mod that ships such JSON also ships a `.dat`.  But there is a second, cheaper
question that a `.dat` cannot confound:

    does the JSON carry information the `.dat` beside it CANNOT express?

If it does, then the mod is either (a) proof the engine reads the JSON, or
(b) broken.  If it does not, the JSON is redundant with the `.dat` and being a
cache becomes plausible.

`linkedTechs.json` is the useful case: three different mods ship it, and the
base game ships it too.  Its content should cross-reference the `.dat`'s own
tech-link layer (effect command type 102, "Disable Tech", and the
`MutuallyExclusive` / `StartingTech` / `Toggleable` / `Cycle` vocabulary that
sits next to it in the exe string pool).
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import hashlib
import json
import os
import sys

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
MODS = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods"
DAT_REL = os.path.join("resources", "_common", "dat")

FAILURES = []

def check(cond, label):
    print("[%s] %s" % ("PASS" if cond else "FAIL", label))
    if not cond:
        FAILURES.append(label)

def load(p):
    with open(p, "rb") as fh:
        raw = fh.read()
    return raw, json.loads(raw.decode("utf-8-sig"))

def shape(obj, depth=0):
    if isinstance(obj, dict):
        if not obj:
            return "{}"
        k = list(obj)[0]
        return "{ %s: %s, ... %d keys }" % (k, shape(obj[k], depth + 1), len(obj))
    if isinstance(obj, list):
        return "[ %s  x%d ]" % (shape(obj[0], depth + 1) if obj else "?", len(obj))
    return type(obj).__name__

base_p = os.path.join(GAME, DAT_REL, "linkedTechs.json")
base_raw, base = load(base_p)
print("=" * 76)
print("A -- the base game's own linkedTechs.json")
print("=" * 76)
print("    path   : %s" % base_p)
print("    bytes  : %d   sha %s" % (len(base_raw), hashlib.sha256(base_raw).hexdigest()[:16]))
print("    topkey : %s" % list(base))
print("    shape  : %s" % shape(base))

# find the list of records
records = None
for k, v in base.items():
    if isinstance(v, list) and v and isinstance(v[0], dict):
        records = v
        print("    records under %r : %d" % (k, len(v)))
        print("    record keys      : %s" % sorted(v[0]))
        print("    sample           : %s" % json.dumps(v[0], ensure_ascii=False))
        break
check(records is not None, "the base file has a list of records")

print()
print("=" * 76)
print("B -- every mod's linkedTechs.json against the base game's")
print("=" * 76)
for root, _dirs, files in os.walk(MODS):
    if "info.json" not in files:
        continue
    p = os.path.join(root, DAT_REL, "linkedTechs.json")
    if not os.path.exists(p):
        continue
    raw, obj = load(p)
    rel = os.path.relpath(p, MODS)
    same = hashlib.sha256(raw).hexdigest() == hashlib.sha256(base_raw).hexdigest()
    print("    %s" % rel)
    print("        bytes %d (base %d)  identical=%s" % (len(raw), len(base_raw), same))
    if not same:
        # where do they diverge?
        n = min(len(raw), len(base_raw))
        cp = 0
        while cp < n and raw[cp] == base_raw[cp]:
            cp += 1
        print("        first differing byte: %d" % cp)
        print("        base around it : %r" % base_raw[max(0, cp - 40):cp + 60])
        print("        mod  around it : %r" % raw[max(0, cp - 40):cp + 60])

print()
print("=" * 76)
print("C -- is linkedTechs a CACHE of the .dat, or independent data?")
print("=" * 76)
# Are the base file's records all present in the .dat's own tech data?
# The .dat cannot be read here without the product kernel, so cross-reference
# by NAME: every tech named in linkedTechs.json should be a real .dat tech.
sys.path.insert(0, _HERE_PATH(".."))
from aoe2mod.semantic.index import index as sem_index

sem = sem_index()
names = {}
for tid, e in sem.techs.items():
    for s in (e.internal, e.en):
        if s:
            names.setdefault(s.strip().lower(), tid)

if records:
    keys = sorted(records[0])
    # collect all string leaves
    def leaves(o, out):
        if isinstance(o, dict):
            for v in o.values():
                leaves(v, out)
        elif isinstance(o, list):
            for v in o:
                leaves(v, out)
        elif isinstance(o, str):
            out.append(o)
        return out

    allstr = leaves(records, [])
    named = [s for s in allstr if s.strip().lower() in names]
    print("    string leaves in base records      : %d" % len(allstr))
    print("    ...matching a .dat tech name       : %d (%.1f%%)" %
          (len(named), 100.0 * len(named) / max(len(allstr), 1)))
    print("    distinct unmatched strings         : %d" %
          len({s for s in allstr if s.strip().lower() not in names}))
    un = sorted({s for s in allstr if s.strip().lower() not in names})[:25]
    for s in un:
        print("        unmatched: %r" % s)

print()
if FAILURES:
    print("FAILURES: %d" % len(FAILURES))
    for f in FAILURES:
        print("  - %s" % f)
    sys.exit(1)
print("LINKED-TECHS PROBE: see the cross-reference above.")
