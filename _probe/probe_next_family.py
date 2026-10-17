# -*- coding: utf-8 -*-
"""Which refused effect family is worth wiring next -- and can a user change
the population limit at all?

Command COUNT alone would pick Upgrade Unit (424).  What a player would
RECOGNISE picks something else.  This probe prints the recognisability
evidence: owner tech name -> target name, for the four families whose meaning
a casual modder would ask for by name.

  A  type 101 Tech Cost Modifier / 103 Tech Time Modifier -> cheaper/faster
  B  population limit      -- every command touching resource 4, plus the civ
                              array (this is a top-2 casual request and I have
                              never verified whether it is reachable)
  C  type 2 Enable/Disable Unit (192 commands, shape unknown)
  D  type 7 Spawn Unit      -- "start with N more units", 35 commands

Nothing here edits anything; it is a measurement.
"""
import os
import sys
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.api as A                                     # noqa: E402
from aoe2mod.dat import locate as L                         # noqa: E402
from aoe2mod.intent import compiler as C                    # noqa: E402
from aoe2mod.semantic.index import index as semantic_index  # noqa: E402

tk = A.open_toolkit()
tk._ensure()
raw = tk._raw
tail, gv = tk._parsed[4], tk._parsed[3]

techs = L.locate_techs(raw, tail, gv)
effects, effects_start = L.locate_effects(raw)
ix = semantic_index()
labels = C.load_resource_labels()

TABLES = C.load_effect_tables()
TYPES = TABLES.get("types") if isinstance(TABLES, dict) else None


def type_params(t):
    e = (TYPES or {}).get(str(t)) or {}
    return e.get("params") or []


def type_name(t):
    e = (TYPES or {}).get(str(t)) or {}
    return e.get("name") or ("type %s" % t)


def tech_name(tid):
    try:
        tid = int(tid)
    except (TypeError, ValueError):
        return "?%r" % (tid,)
    e = ix.get("tech", tid)
    disp = e.display if e is not None else None
    internal = techs[tid].get("name") if 0 <= tid < len(techs) else None
    return "%s [%s]" % (disp or "?", (internal or "")[:34])


def unit_name(uid):
    try:
        uid = int(uid)
    except (TypeError, ValueError):
        return "?%r" % (uid,)
    e = ix.get("unit", uid)
    internal = None
    for c in tk._civs:
        for u in (c.get("units") or ()):
            if u.get("id") == uid:
                internal = u.get("name")
                break
        if internal:
            break
    return "%s [%s]" % ((e.display if e is not None else "?"), (internal or "")[:20])


def fnum(x):
    return int(x) if isinstance(x, float) and float(x).is_integer() else x


# ---------------------------------------------------------------- collect
per_type = collections.defaultdict(list)          # type -> [(owner_ti, ci, cmd)]
for ti, t in enumerate(techs):
    eid = t.get("effect_id")
    if eid is None or not (0 <= eid < len(effects)):
        continue
    for ci, c in enumerate(effects[eid].get("commands") or ()):
        per_type[c.get("type")].append((ti, ci, c))

RES_MOD = (1, 6, 11, 16, 21, 26, 31, 36, 41, 46)

# ================================================== A. cheaper / faster techs
for ty in (101, 103):
    items = per_type.get(ty) or []
    print("")
    print("=" * 72)
    print("A. type %d %s -- %d commands over %d techs"
          % (ty, type_name(ty), len(items), len({x[0] for x in items})))
    print("   params %s" % (type_params(ty),))
    print("   owners (tech -> how many of its commands):")
    own = collections.Counter(x[0] for x in items)
    for oti, n in own.most_common(8):
        print("      tech[%d] %s  x%d" % (oti, tech_name(oti), n))
    print("   sample rows (owner -> target b c d):")
    for oti, ci, c in items[:18]:
        print("      tech[%d] %-46s cmd %2d  a=%-22s b=%-4s c=%-4s d=%s"
              % (oti, tech_name(oti)[:46], ci,
                 tech_name(c.get("a"))[:22], c.get("b"), c.get("c"), fnum(c.get("d"))))
    ds = sorted({fnum(c.get("d")) for _, _, c in items}, key=lambda v: (v is None, v))
    print("   distinct d: %s" % ds[:24])

# ================================================== B. population limit
print("")
print("=" * 72)
print("B. population limit")
res4 = [(ti, ci, c) for ty in RES_MOD for (ti, ci, c) in (per_type.get(ty) or ())
        if c.get("a") == 4]
print("   effect commands whose target resource is 4 (Population Headroom): %d" % len(res4))
for ti, ci, c in res4[:10]:
    print("      tech[%d] %s cmd %d type %s d=%s"
          % (ti, tech_name(ti)[:40], ci, c.get("type"), fnum(c.get("d"))))
any4 = collections.Counter()
idx4 = collections.Counter()
for i, cv in enumerate(tk._civs):
    rs = cv.get("resources") or []
    if len(rs) > 4:
        idx4[rs[4]] += 1
    for j, v in enumerate(rs):
        if v:
            any4[j] += 1
print("   civ resources[4] distinct values across 63 civs: %s" % dict(idx4))
print("   civ resources[4] value for Gaia/British: %s / %s"
      % ((tk._civs[0].get("resources") or [None] * 5)[4],
         (tk._civs[1].get("resources") or [None] * 5)[4]))
print("   unit.cost population (resource 4) is a UNIT pop COST, not the cap:")
n_pop = sum(1 for c in tk._civs for u in (c.get("units") or ())
            for cost in (u.get("costs") or ()) if cost.get("type") == 4)
print("      %d unit cost slots charge population" % n_pop)

# ================================================== C. enable / disable unit
for ty in (2, 7):
    items = per_type.get(ty) or []
    print("")
    print("=" * 72)
    print("%s. type %d %s -- %d commands over %d techs"
          % ("C" if ty == 2 else "D", ty, type_name(ty),
             len(items), len({x[0] for x in items})))
    print("   params %s" % (type_params(ty),))
    for oti, ci, c in items[:12]:
        print("      tech[%d] %-40s cmd %2d a=%-26s b=%-5s c=%-4s d=%s"
              % (oti, tech_name(oti)[:40], ci,
                 unit_name(c.get("a"))[:26] if ty == 7 else c.get("a"),
                 c.get("b"), c.get("c"), fnum(c.get("d"))))
    for slot in ("a", "b", "c", "d"):
        vals = collections.Counter(c.get(slot) for _, _, c in items)
        print("   %s: distinct %-5d top %s" % (slot, len(vals), vals.most_common(8)))
