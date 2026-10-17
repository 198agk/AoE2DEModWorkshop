"""v9: SEMANTIC cross-check using the project's own parser (SECONDARY evidence only).
Enumerates every unit record of every civ via aoe2mod and counts which unit IDs have a
different hit_points between game and mod. This must agree with the raw-byte answer
(27 IDs x 63 civs). Clearly labelled secondary: the PRIMARY evidence is v2/v3/v7/v8b raw bytes."""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import json
import os
import sys

sys.path.insert(0, _HERE_PATH("..", "..", ".."))
from aoe2mod.dat.parser import Parser, load_dat  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\local\aoe2mod Smoke5 TreeVsPanel"
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"

out = []

def p(s=""):
    out.append(s)
    print(s)

def hp_map(path):
    g, how = load_dat(path)
    d = Parser(g).parse()
    m = {}
    for ci, civ in enumerate(d["civs"]):
        for u in civ["units"]:
            m.setdefault(u["id"], {})[ci] = u.get("hit_points")
    return m, d["civ_count"], how

mg, ng, howg = hp_map(os.path.join(GAME, r"resources\_common\dat\empires2_x2_p1.dat"))
mm, nm, howm = hp_map(os.path.join(MOD, r"resources\_common\dat\empires2_x2_p1.dat"))
p("parser reported: game %s (%d civs), mod %s (%d civs)" % (howg, ng, howm, nm))

changed_ids = {}
for uid in sorted(set(mg) | set(mm)):
    a, b = mg.get(uid, {}), mm.get(uid, {})
    per = {c: (a.get(c), b.get(c)) for c in set(a) | set(b) if a.get(c) != b.get(c)}
    if per:
        changed_ids[uid] = per

p("unit IDs whose hit_points differ between game and mod: %d" % len(changed_ids))
for uid in sorted(changed_ids):
    per = changed_ids[uid]
    pairs = {v for v in per.values()}
    p("   id %-5d civs %d  pairs %s" % (uid, len(per), pairs))

allpairs = {v for per in changed_ids.values() for v in per.values()}
p("union of (game_hp, mod_hp) pairs over every changed unit/civ: %s" % allpairs)
p("every changed unit changed in exactly 63 civs: %s"
  % (len({len(v) for v in changed_ids.values()}) == 1 and {len(v) for v in changed_ids.values()} == {63}))
p("id 83 present among changed: %s" % (83 in changed_ids))
p("class of changed units (from game): ")
# classes
gd = Parser(load_dat(os.path.join(GAME, r"resources\_common\dat\empires2_x2_p1.dat"))[0]).parse()
civs = gd["civs"]
seen = {}
for civ in civs:
    for u in (civ.get("units") or []):
        if u["id"] in changed_ids and u["id"] not in seen:
            seen[u["id"]] = (u.get("class"), u.get("name"))
for uid in sorted(seen):
    p("   id %-5d class=%-3s name=%r" % (uid, seen[uid][0], seen[uid][1]))

with open(os.path.join(HERE, "v9_aoe2mod_crosscheck.json"), "w", encoding="utf-8") as f:
    json.dump({"changed_ids": {str(k): {str(c): list(v) for c, v in per.items()}
                               for k, per in changed_ids.items()}}, f, indent=1)
with open(os.path.join(HERE, "v9_out.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(out))
