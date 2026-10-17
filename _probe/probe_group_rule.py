# -*- coding: utf-8 -*-
r"""Which grouping rule is the right one -- measured over EVERY unit.

Two candidate definitions for "the files that draw this entity":

  P (prefix)  every .sld whose name starts with `<standing file minus its last
              token>_`.  Cheap, computed from filenames only.  Risk: names
              nest (`b_misc_waypoint_flag` vs `b_misc_waypoint_flag_armenians`).
  N (name)    every graphics record whose internal `name` stem (`Archer` out of
              `Archer (Attack)`) equals the standing record's stem.  This is
              what the ENGINE calls the group.

If they agree everywhere, either is safe.  Where they disagree, the engine's own
field wins, and the disagreement is a fact the product must report.
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


tk = A.open_toolkit(game_root=GAME)
tk._ensure()
_gfx = tk._stats["graphics"]
_by_id = {x.get("id"): x for x in _gfx}


def rec_file(x):
    if not isinstance(x, dict):
        return None
    f = x.get("file")
    if not isinstance(f, str):
        return None
    f = f.strip()
    return f if f and f != "None" else None


def rec_name(x):
    if not isinstance(x, dict):
        return None
    n = x.get("name")
    return n.strip() if isinstance(n, str) and n.strip() not in ("", "None") else None


def stem_of_name(n):
    """'Archer (Attack)' -> 'Archer';  'FSHSP_FN' -> 'FSHSP_FN'."""
    if n is None:
        return None
    i = n.find(" (")
    return (n[:i] if i > 0 else n).strip() or None


# prefix family ---------------------------------------------------------------
_pref_files = collections.defaultdict(set)
for fn in _on_disk:
    nr = no_res(fn)
    _pref_files[strip1(nr)].add(fn)

# name stem -> files (via graphics records) -----------------------------------
_stem_files = collections.defaultdict(set)
for x in _gfx:
    f = rec_file(x)
    if not f:
        continue
    s = stem_of_name(rec_name(x))
    if s:
        _stem_files[s].add(f + ".sld")

# ---- per unit ---------------------------------------------------------------
print("=" * 72)
print("P (filename prefix) vs N (graphics-record name stem), over every unit id")
print("=" * 72)
_on_disk_set = set(_on_disk)

_seen = set()
_agree = _disagree = _nores = 0
_ex = []
for c in tk._civs:
    for u in c["units"]:
        uid = u["id"]
        if uid in _seen:
            continue
        _seen.add(uid)
        sg = u.get("standing_graphic")
        f = rec_file(_by_id.get(sg[0])) if sg else None
        if not f or (f + ".sld") not in _on_disk_set:
            _nores += 1
            continue
        P = set(x for x in _pref_files.get(strip1(no_res(f)), ()) if x in _on_disk_set)
        N = set(_stem_files.get(stem_of_name(rec_name(_by_id.get(sg[0]))), ()))
        if P == N:
            _agree += 1
        else:
            _disagree += 1
            if len(_ex) < 10:
                _ex.append((uid, f, sorted(P - N)[:4], sorted(N - P)[:4]))
print("  units considered          : %d" % len(_seen))
print("  no resolvable standing art: %d" % _nores)
print("  P == N                    : %d" % _agree)
print("  P != N                    : %d" % _disagree)
for uid, f, onlyp, onlyn in _ex:
    print("     unit %-5d standing %s" % (uid, f))
    print("         only in prefix-family : %s" % onlyp)
    print("         only in name-stem     : %s" % onlyn)

# ---- the nesting cases, resolved -------------------------------------------
print()
print("=" * 72)
print("the nesting case: a prefix that is ALSO a file's own name")
print("=" * 72)
_names = set(no_res(f) for f in _on_disk)
for base in ("b_misc_waypoint_flag", "n_plant", "b_afri_town_center_age2"):
    fam = sorted(x for x in _pref_files.get(base, ()) if x in _on_disk)
    print("  %-30s family %d files" % (base, len(fam)))
    for x in fam[:6]:
        print("        %s" % x)
    print("        ...")
    _stems = set()
    for x in fam:
        for g in _gfx:
            if rec_file(g) == x[:-4]:
                _stems.add(stem_of_name(rec_name(g)))
                break
    print("        name stems in that family: %s" % sorted(_stems)[:6])
