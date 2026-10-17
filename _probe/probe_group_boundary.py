# -*- coding: utf-8 -*-
r"""Is the file-group boundary ever ambiguous?

Grouping rule under test: a .sld belongs to entity `P` if its name is
`P_<token>_x1`.  That rule is only safe if stripping a token never lands on a
name that is itself an entity.

  Q1  files f where strip1(f) is ALSO some file's own name (nesting collision)
  Q2  what those look like
  Q3  do the graphics records of one group share an internal `name` stem?
      (confirms the grouping from recorded data rather than from strings)
"""
import collections, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
os.chdir(ROOT)

import aoe2mod.api as A

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")
_on_disk = sorted(fn for fn in os.listdir(GP) if fn.endswith(".sld"))


def no_res(fn):
    return fn[:-4][:-3] if fn[:-4].endswith("_x1") else fn[:-4]


def strip1(nr):
    return nr.rpartition("_")[0] if "_" in nr else ""


_names = set(no_res(f) for f in _on_disk)

# Q1/Q2 ---------------------------------------------------------------------
_coll = collections.defaultdict(list)
for fn in _on_disk:
    nr = no_res(fn)
    s = strip1(nr)
    if s and s in _names:
        _coll[s].append(nr)
print("=" * 72)
print("Q1  nesting collisions (strip1 of a file IS another file's name)")
print("=" * 72)
print("  number of colliding base names: %d" % len(_coll))
_tot = sum(len(v) for v in _coll.values())
print("  files involved: %d" % _tot)
for s, v in sorted(_coll.items(), key=lambda kv: -len(kv[1]))[:12]:
    print("     base %-34s + %d   e.g. %s" % (s, len(v), sorted(v)[:4]))

# Q3 ------------------------------------------------------------------------
print()
print("=" * 72)
print("Q3  do group members share an internal graphics `name` stem?")
print("=" * 72)
tk = A.open_toolkit(game_root=GAME)
tk._ensure()
_gfx = tk._stats["graphics"]


def rec_name(x):
    n = x.get("name")
    return n.strip() if isinstance(n, str) and n.strip() not in ("", "None") else None


def rec_file(x):
    f = x.get("file")
    if not isinstance(f, str):
        return None
    f = f.strip()
    return f if f and f != "None" else None


for x in _gfx[:1]:
    pass
for probe_group in ("u_arc_archer", "u_monk_west", "u_shp_fishing", "b_dark_barracks"):
    print("  group %r:" % probe_group)
    for x in _gfx:
        f = rec_file(x)
        if f and strip1(no_res(f)) == probe_group:
            print("     %-34s name=%-16s gfx=%s" % (f, rec_name(x), x.get("id")))
