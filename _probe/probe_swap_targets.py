# -*- coding: utf-8 -*-
r"""What exactly does a reskin have to overwrite?  (second attempt)

The first version of this file had the prefix function wrong: it stripped only
the trailing `_x1`, so every animation became its own "prefix" and every unit
looked like a single file.  The grouping prefix is the name with `_<token>_x1`
removed -- `u_arc_archer_attackA_x1` and `u_arc_archer_idleA_x1` share
`u_arc_archer`.

  Z1  standing_graphic[1] -- the pair's SECOND int16
  Z2  the prefix -> file set a swap must overwrite, per unit
  Z3  is the x1/x2 pairing complete for every prefix a unit uses?
  Z4  how many units share one prefix (a swap reskins all of them)
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


def no_res(fn):                      # 'u_arc_archer_attackA_x1.sld' -> 'u_arc_archer_attackA'
    return fn[:-4][:-3] if fn[:-4].endswith("_x1") else fn[:-4]


def group_of(nr):                    # 'u_arc_archer_attackA' -> 'u_arc_archer'
    return nr.rpartition("_")[0]


def token_of(nr):
    return nr.rpartition("_")[2]


_groups = collections.defaultdict(set)
for fn in _on_disk:
    nr = no_res(fn)
    _groups[group_of(nr)].add(nr)

tk = A.open_toolkit(game_root=GAME)
tk._ensure()
_gfx = tk._stats["graphics"]
_by_id = {x.get("id"): x for x in _gfx}


def file_of(gid):
    if gid is None or gid < 0:
        return None
    r = _by_id.get(gid)
    if not isinstance(r, dict):
        return None
    f = r.get("file")
    if not isinstance(f, str):
        return None
    f = f.strip()
    return f if f and f != "None" else None


def standing(uid, civ="British"):
    for c in tk._civs:
        if c["name"] != civ:
            continue
        for u in c["units"]:
            if u["id"] == uid:
                return u.get("standing_graphic")
    return None


# Z1 -------------------------------------------------------------------------
print("=" * 72)
print("Z1  standing_graphic[1] -- the pair's SECOND int16")
print("=" * 72)
_live = _set = _ok = 0
_pat = collections.Counter()
_ex = []
for c in tk._civs:
    for u in c["units"]:
        sg = u.get("standing_graphic")
        if not sg:
            continue
        _live += 1
        if sg[1] == -1:
            continue
        _set += 1
        a, b = file_of(sg[0]), file_of(sg[1])
        if a and b:
            _ok += 1
            if group_of(no_res(a)) == group_of(no_res(b)):
                _pat["same group, other animation"] += 1
            else:
                _pat["different group entirely"] += 1
            if len(_ex) < 6:
                _ex.append((u["id"], a, b))
print("  unit records with a standing_graphic : %d" % _live)
print("  whose SECOND int16 is set (not -1)  : %d" % _set)
print("  ...and resolves to a real file      : %d" % _ok)
print("  pattern: %s" % dict(_pat))
for uid, a, b in _ex:
    print("     unit %-5d\n        first  %s\n        second %s" % (uid, a, b))

# Z2/Z3 ----------------------------------------------------------------------
print()
print("=" * 72)
print("Z2  prefix -> file set      Z3  x1/x2 pairing completeness")
print("=" * 72)
_missing_x2 = []
for uid in (4, 8, 83, 74, 2550, 12, 692, 125, 41, 13, 448, 594, 359, 66, 349):
    sg = standing(uid)
    f = file_of(sg[0]) if sg else None
    if not f:
        print("  unit %-5d  no standing graphic resolves" % uid)
        continue
    g = group_of(no_res(f))
    names = sorted(_groups.get(g, ()))
    x1 = [n for n in names if (n + "_x1.sld") in _on_disk]
    x2 = [n for n in names if (n + "_x2.sld") in _on_disk]
    if len(x1) != len(x2):
        _missing_x2.append((uid, g, len(x1), len(x2)))
    print("  unit %-5d  standing %-30s" % (uid, f))
    print("        group %-26s files %-3d x1 %-3d x2 %-3d" % (g, len(names), len(x1), len(x2)))
    for n in names:
        print("            %s" % n)
print()
print("  groups with an x1/x2 count mismatch: %d %s" % (len(_missing_x2), _missing_x2))

# Z4 -------------------------------------------------------------------------
print()
print("=" * 72)
print("Z4  units sharing one group (a group swap reskins all of them)")
print("=" * 72)
_share = collections.defaultdict(set)
for c in tk._civs:
    for u in c["units"]:
        sg = u.get("standing_graphic")
        if not sg:
            continue
        f = file_of(sg[0])
        if f and (f + ".sld") in _on_disk:
            _share[group_of(no_res(f))].add(u["id"])
_h = collections.Counter(len(v) for v in _share.values())
print("  distinct usable groups: %d" % len(_share))
print("  units per group histogram: %s" % dict(sorted(_h.items())))
for g, ids in sorted(_share.items(), key=lambda kv: -len(kv[1]))[:6]:
    print("     %-40s %3d units %s" % (g, len(ids), sorted(ids)[:8]))
