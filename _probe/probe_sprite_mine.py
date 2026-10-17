# -*- coding: utf-8 -*-
r"""Pin the decisive subject: scenery with a tiny, unmistakable swap.

  X1  every stem matching n_mine* -- files, bytes, grid
  X2  which unit ids resolve to each, and their .dat `name`
  X3  the exact mod a swap would ship (file list + total bytes)
  X4  a second subject with a different look at the same cost
"""
import collections, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
os.chdir(ROOT)

import aoe2mod.api as A

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")
_on_disk = set(fn for fn in os.listdir(GP) if fn.endswith(".sld"))

tk = A.open_toolkit(game_root=GAME)
tk._ensure()
_by_id = {x.get("id"): x for x in tk._stats["graphics"]}


def fname(rec):
    if not isinstance(rec, dict):
        return None
    f = rec.get("file")
    if not isinstance(f, str):
        return None
    f = f.strip()
    return f if f and f != "None" else None


def stem_of(n):
    return n[:-3].rsplit("_", 1)[0] if n.endswith("_x1") else None


_files = collections.defaultdict(set)
for fn in _on_disk:
    if fn.endswith("_x1.sld"):
        _files[stem_of(fn[:-4])].add(fn[:-4])

_units_by_stem = collections.defaultdict(set)
_unit_name = {}
for c in tk._civs:
    for u in c["units"]:
        sg = u.get("standing_graphic")
        if not sg:
            continue
        f = fname(_by_id.get(sg[0]))
        if f and (f + ".sld") in _on_disk:
            _units_by_stem[stem_of(f)].add(u["id"])
            _unit_name.setdefault(u["id"], u.get("name"))

print("=" * 72)
print("X1  every n_mine* stem")
print("=" * 72)
for st in sorted(s for s in _files if s.startswith("n_mine")):
    tot = 0
    rows = []
    for n in sorted(_files[st]):
        b1 = os.path.getsize(os.path.join(GP, n + ".sld")) if (n + ".sld") in _on_disk else 0
        n2 = n[:-3] + "_x2"
        b2 = os.path.getsize(os.path.join(GP, n2 + ".sld")) if (n2 + ".sld") in _on_disk else 0
        tot += b1 + b2
        rows.append((n, b1, b2))
    print("  %-24s %d anims  %8d B  units %s"
          % (st, len(rows), tot, sorted(_units_by_stem.get(st, ()))))
    for n, b1, b2 in rows:
        print("       %-32s x1 %8d  x2 %8d" % (n, b1, b2))

print()
print("=" * 72)
print("X2  which unit ids, and what the .dat calls them")
print("=" * 72)
for uid in (66, 102, 594, 65, 48, 59, 349, 1051, 284, 4, 83):
    print("  unit %-5d name %-16s stem %s"
          % (uid, _unit_name.get(uid), sorted(_units_by_stem.get(
              next((s for s in _files if uid in _units_by_stem.get(s, ())), "<none>"), ()))[:6]))

print()
print("=" * 72)
print("X3  what a gold<->stone swap would ship")
print("=" * 72)


def manifest_for(stem):
    out = []
    for n in sorted(_files.get(stem, ())):
        for rel in (n + ".sld", n[:-3] + "_x2.sld"):
            p = os.path.join(GP, rel)
            if os.path.exists(p):
                out.append((rel, os.path.getsize(p)))
    return out


for st in ("n_mine", "n_mine_gold"):
    m = manifest_for(st)
    print("  stem %-14s %d files, %d B" % (st, len(m), sum(b for _, b in m)))
    for rel, b in m:
        print("       %-38s %8d" % (rel, b))

print()
print("  a swap that replaces the WHOLE stem writes those files under")
print("  resources/_common/drs/graphics/ in the mod.")
print()
print("  X4  second subject: bush (n_plant_bush 95368 B) and forage (n_forage_bush)")
for st in ("n_plant_bush", "n_forage_bush", "n_tree_bush", "n_mine"):
    m = manifest_for(st)
    print("     %-20s %2d files  %8d B  units %s"
          % (st, len(m), sum(b for _, b in m), sorted(_units_by_stem.get(st, ()))))
