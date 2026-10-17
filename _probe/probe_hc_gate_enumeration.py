"""Enumerate EVERY per-civ feature of the .dat that could separate the civs
which can build Hand Cannoneer from those that cannot.

Already refuted (each with a probe):
  * membership in the civ's own unit array  -- all 63 civs contain unit 5
  * the unit RECORD                          -- identical for all 63 except `civ`
  * the effect layer's type 2 / 102          -- unit 5's enable is global (tech 85,
                                                civ=-1); no civ owns a disable
  * the dat TechTree                        -- ONE global object (DatFile.h:109)
  * transitive availability of Chemistry     -- Chemistry is ResearchedCompleted
                                                for all 62 playable civs, yet 38
                                                cannot build Hand Cannoneer

So this probe stops arguing by exclusion and enumerates every remaining
per-civ-scoped datum that MENTIONS unit 5 (or its prerequisite chain), printing
the civ-ownership of each.  If nothing separates 24 from 38, that is a strong
statement: the .dat cannot express it.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aoe2mod.api as A                     # noqa: E402
import aoe2mod.game.civtechtrees as CT      # noqa: E402

tk = A.open_toolkit()
tk._ensure()

civs = tk._civs
trees = tk._trees()
techs = tk._tech_records()
effects = tk._effect_records()

UNIT = 5          # Hand Cannoneer
CHEM = 47         # Chemistry


def tree_status(civ_name, node_id, use=CT.UNIT_USE_TYPES):
    t = trees.get(CT.civ_file_stem(civ_name))
    return CT.node_status(t, node_id, use) if t else None


can = [c["name"] for c in civs if tree_status(c["name"], UNIT) not in (None, "NotAvailable")]
cannot = [c["name"] for c in civs if tree_status(c["name"], UNIT) == "NotAvailable"]
print("civs that CAN build unit %d   : %d" % (UNIT, len(can)))
print("civs told NotAvailable         : %d" % len(cannot))
print()

# ---------------------------------------------------------------- effect scan
print("=" * 74)
print("EVERY effect command that mentions unit %d or tech %d" % (UNIT, CHEM))
print("=" * 74)

hits = []
for ti, t in enumerate(techs):
    eid = t.get("effect_id")
    if eid is None or eid < 0 or eid >= len(effects):
        continue
    for ci, cmd in enumerate(effects[eid].get("commands", []) or []):
        a, b = cmd.get("a"), cmd.get("b")
        if UNIT in (a, b) or CHEM in (a, b):
            hits.append((ti, t.get("name"), t.get("civ"), ci, cmd.get("type"), a, b,
                         cmd.get("c"), cmd.get("d")))

print("commands mentioning %d or %d : %d" % (UNIT, CHEM, len(hits)))
by_civ = {}
for h in hits:
    by_civ.setdefault(h[2], []).append(h)
print("their civ owners (None/-1 == global): %s"
      % sorted(by_civ, key=lambda x: (x is None, x)))
print()

for civ_owner, hs in sorted(by_civ.items(), key=lambda kv: (kv[0] is None, kv[0])):
    tag = "GLOBAL" if civ_owner in (None, -1) else "civ=%s" % civ_owner
    print("  %-10s %d commands" % (tag, len(hs)))
    for (ti, nm, cv, ci, ty, a, b, c, d) in hs[:6]:
        print("      tech[%d] %-38s cmd%d type=%-4s A=%-5s B=%-5s C=%-5s D=%s"
              % (ti, str(nm)[:38], ci, ty, a, b, c, d))
    if len(hs) > 6:
        print("      ... %d more" % (len(hs) - 6))

# ---------------------------------------------------------------- unit record
print()
print("=" * 74)
print("UNIT-ARRAY POSITION and neighbour structure for unit %d" % UNIT)
print("=" * 74)
pos = {}
for c in civs:
    ids = [u["id"] for u in c["units"]]
    pos.setdefault(ids.index(UNIT) if UNIT in ids else None, []).append(c["name"])
print("array index of unit %d, by civ: %d distinct positions" % (UNIT, len(pos)))
for p, names in sorted(pos.items(), key=lambda kv: (kv[0] is None, kv[0]))[:6]:
    print("  index %-6s : %3d civs  %s" % (p, len(names), names[:6]))
if len(pos) > 6:
    print("  ... %d more positions" % (len(pos) - 6))

# does any library/tech-array structure differ?
print()
print("=" * 74)
print("PER-CIV COUNTS (any of these differing could carry the gate)")
print("=" * 74)
feats = {}
for c in civs:
    feats.setdefault((
        len(c["units"]),
        c.get("unit_pointers_total"),
        c.get("tech_tree_id"),
        c.get("team_bonus_id"),
        len(c.get("resources") or []),
    ), []).append(c["name"])
print("distinct (units, ptrs, tree_id, bonus, res_len) tuples: %d" % len(feats))
for k, names in sorted(feats.items(), key=lambda kv: -len(kv[1]))[:4]:
    print("  %s : %d civs" % (k, len(names)))
