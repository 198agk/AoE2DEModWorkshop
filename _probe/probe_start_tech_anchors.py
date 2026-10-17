# -*- coding: utf-8 -*-
r"""Which tech can hand a British player a Barracks unit in the DARK AGE?

v5 and v6 both gate the Champi Scout button behind a Castle (user m26421).  Both
attached the enable command to `tech 263 'Longbow (make avail)'`, which is
civ-owned and has no research location -- my heuristic said that meant "active at
game start", and the user's two runs say that heuristic is WRONG.

So stop guessing from field shapes and copy a recipe the game already ships:
find every civ-owned tech whose effect ENABLES a unit (type 2, slot B == 1), and
report the earliest Age ID that unit carries in any civilization's tree.
A tech that enables a Dark-Age unit is a tech that must fire at game start.
"""
import contextlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

from aoe2mod.dat import parser as P                          # noqa: E402
from aoe2mod.game import civtechtrees as CT                  # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
SHIPPED = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")

data, how = P.load_dat(SHIPPED)
p = P.Parser(data)
with contextlib.redirect_stdout(io.StringIO()):
    p.parse()
civs = p.stats["civs"]
techs = p.stats["techs"]
effects = p.stats["effects"]

trees = CT.load_trees(GAME)

# earliest Age ID each unit id carries in any tree row, and which civs have a row
age_of, row_civs = {}, {}
for ck, tree in trees.items():
    for r in CT.rows_of(tree):
        try:
            nid = int(r.get("Node ID"))
        except (TypeError, ValueError):
            continue
        if r.get("Use Type") != "Unit":
            continue
        row_civs.setdefault(nid, set()).add(ck)
        a = r.get("Age ID")
        if isinstance(a, int):
            age_of[nid] = min(age_of.get(nid, 99), a)

names = {}
for i, t in enumerate(techs):
    if t.get("name"):
        names[i] = t["name"]


def cmds(effect_id):
    """★ The tech record has NO `commands` key -- commands live on the EFFECT it
    points at via `effect_id`.  Reading `t["commands"]` silently yields nothing,
    which is exactly how an earlier pass printed `types=[]` for every tech."""
    try:
        e = effects[effect_id]
    except (IndexError, TypeError):
        return []
    out = []
    for c in e.get("commands") or []:
        if isinstance(c, dict):
            out.append((c.get("type"), c.get("a"), c.get("b"), c.get("c"), c.get("d")))
        else:
            out.append(tuple(c))
    return out


def tech_cmds(t):
    return cmds(t.get("effect_id"))


def can_enable(t):
    """(unit_id) entries this tech turns ON: type 2, slot B == 1."""
    return [a for (ty, a, b, _c, _d) in tech_cmds(t) if ty == 2 and b == 1]


def tech_types(t):
    return sorted({c[0] for c in tech_cmds(t)})


def loc_building(t):
    locs = t.get("research_locations") or []
    if not locs:
        return None
    first = locs[0]
    if isinstance(first, dict):
        for k in ("building_id", "research_location", "building"):
            if k in first:
                v = first[k]
                return v if isinstance(v, int) else None
        return None
    try:
        return int(first[0])
    except (TypeError, ValueError, IndexError):
        return None


print("=" * 78)
print("A  every civ-owned tech whose effect enables a unit (type 2, b == 1)")
print("=" * 78)
rows = []
for ti, t in enumerate(techs):
    civ = t.get("civ")
    if civ is None or civ == -1:
        continue
    for a in can_enable(t):
        bldg = loc_building(t)
        rows.append({"tech": ti, "name": names.get(ti, "?"),
                     "civ_index": civ,
                     "civ": civs[civ].get("name") if isinstance(civ, int) and 0 <= civ < len(civs) else civ,
                     "loc_building": bldg, "unit": a,
                     "unit_age": age_of.get(a), "unit_rows_in": len(row_civs.get(a, ())) })
print("  matches: %d" % len(rows))
for r in rows:
    print("   tech %-5d %-34r owner=%-12s loc_building=%-5s -> unit %-5s age=%-4s rows_in=%s"
          % (r["tech"], r["name"], r["civ"], r["loc_building"], r["unit"],
             r["unit_age"], r["unit_rows_in"]))

print()
print("=" * 78)
print("B  the same, but restricted to techs with NO research location")
print("=" * 78)
no_loc = [r for r in rows if r["loc_building"] in (None, -1)]
print("  count: %d" % len(no_loc))
for r in no_loc:
    print("   tech %-5d %-34r owner=%-12s -> unit %-5s age=%s"
          % (r["tech"], r["name"], r["civ"], r["unit"], r["unit_age"]))

print()
print("=" * 78)
print("C  what does the DARK-AGE (age 1) Champi line look like for its 4 owners?")
print("=" * 78)
for uid in (2550, 2552, 2554, 2588):
    enablers = []
    for ti, t in enumerate(techs):
        if uid in can_enable(t):
            enablers.append((ti, names.get(ti, "?"), t.get("civ"),
                             loc_building(t), t.get("effect_id")))
    print("  unit %-5d age=%s rows_in=%s" % (uid, age_of.get(uid), len(row_civs.get(uid, ()))))
    for e in enablers:
        print("      enabled by tech %-5d %-30r civ=%-4s loc_building=%-5s eff=%s" % e)

print()
print("=" * 78)
print("D  British (civ 1) techs with no research location -- the candidate anchors")
print("=" * 78)
for ti, t in enumerate(techs):
    if t.get("civ") != 1:
        continue
    lb = loc_building(t)
    if lb not in (None, -1):
        continue
    kinds = tech_types(t)
    print("   tech %-5d %-34r eff=%-5s types=%s locs=%s"
          % (ti, names.get(ti, "?"), t.get("effect_id"), kinds,
             t.get("research_locations")))

print()
print("=" * 78)
print("E  how many techs are civ-owned vs global, and age techs")
print("=" * 78)
owned = sum(1 for t in techs if isinstance(t.get("civ"), int) and t["civ"] != -1)
print("  civ-owned techs: %d   global: %d" % (owned, len(techs) - owned))
for want in ("Feudal Age", "Castle Age", "Imperial Age", "Dark Age"):
    hits = [i for i, t in enumerate(techs)
            if (t.get("name") or "").strip().lower() == want.lower()]
    print("  tech named %-14r -> %s" % (want, hits))
print()
print("done")
