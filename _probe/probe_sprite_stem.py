# -*- coding: utf-8 -*-
r"""A unit is more than its standing animation.

StandingGraphic.first gives ONE file: u_arc_archer_idleA_x1.sld.  A unit in
game also walks, attacks, dies and decays.  Those files exist on disk under the
same STEM.  If the stem is derivable from the resolved name, then "swap this
unit's appearance" means "swap every file with this stem" -- a mechanical rule
that needs no second .dat field.

Measure:
  S6  the stem rule: strip the trailing <animation>_x1 and keep the rest
  S7  files per stem on disk (the whole appearance)
  S8  is the stem stable for one unit id across civilizations?
  S9  bytes for a whole-unit swap
  S10 stem collisions: do two different unit ids share a stem?
  S11 the x1/x2 pairing holds for every stem file too
"""
import collections, os, re, sys

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


def stem_of(name):
    r"""u_arc_archer_idleA_x1 -> u_arc_archer ; the last two '_' segments go."""
    if not name.endswith("_x1") and not name.endswith("_x2"):
        return None
    body = name[:-3]                       # drop "_x1"
    if "_" not in body:
        return None
    return body.rsplit("_", 1)[0]          # drop the animation segment


# ---------------------------------------------------------------- build index
print("=" * 72)
print("S6/S7  the stem rule, and how many files a unit really is")
print("=" * 72)
_stem_files = collections.defaultdict(set)
for fn in _on_disk:
    if not fn.endswith("_x1.sld"):
        continue
    st = stem_of(fn[:-4])
    if st:
        _stem_files[st].add(fn[:-4])
print("  distinct stems on disk (x1 side): %d" % len(_stem_files))
_h = collections.Counter(len(v) for v in _stem_files.values())
print("  files per stem: %s" % dict(sorted(_h.items())))
print("  total stems with an _x2 twin for every _x1: ", end="")
_ok = 0; _bad = []
for st, names in _stem_files.items():
    good = all((n[:-3] + "_x2.sld") in _on_disk for n in names)
    if good:
        _ok += 1
    else:
        _bad.append(st)
print("%d of %d" % (_ok, len(_stem_files)))
if _bad:
    print("  stems missing an x2 twin: %d %s" % (len(_bad), _bad[:5]))

# ---------------------------------------------------- unit id -> stem, census
print()
print("  unit id -> stem, taken from each civ's own record:")
_id_stem = {}
_id_stem_all = collections.defaultdict(set)
for c in tk._civs:
    for u in c["units"]:
        sg = u.get("standing_graphic")
        if not sg:
            continue
        f = fname(_by_id.get(sg[0]))
        if not f or (f + ".sld") not in _on_disk:
            continue
        st = stem_of(f)
        if not st:
            continue
        _id_stem_all[u["id"]].add(st)
        _id_stem.setdefault(u["id"], st)
print("    unit ids with a resolvable stem            : %d" % len(_id_stem_all))

# ------------------------------------------------------------- S8 stability
print()
print("=" * 72)
print("S8  is the stem the same for one unit id across civilizations?")
print("=" * 72)
_var = {i: s for i, s in _id_stem_all.items() if len(s) > 1}
print("  unit ids whose stem VARIES by civilization : %d of %d"
      % (len(_var), len(_id_stem_all)))
for i in sorted(_var)[:8]:
    print("     id %-5d %s" % (i, sorted(_var[i])))
print("  -> a swap must be per-civ whenever this is non-zero for its target." if _var
      else "  -> the stem is a property of the unit id alone.")

# ------------------------------------------------------------- S10 collision
print()
print("=" * 72)
print("S10  do two different unit ids share a stem?")
print("=" * 72)
_stem_ids = collections.defaultdict(set)
for i, st in _id_stem.items():
    _stem_ids[st].add(i)
_shared = {st: ids for st, ids in _stem_ids.items() if len(ids) > 1}
print("  stems drawn by more than one unit id: %d of %d"
      % (len(_shared), len(_stem_ids)))
for st, ids in sorted(_shared.items(), key=lambda kv: -len(kv[1]))[:6]:
    print("     %-40s %d ids %s" % (st, len(ids), sorted(ids)[:8]))

# ------------------------------------------------------------- S9 bytes
print()
print("=" * 72)
print("S9  what a WHOLE-unit swap would ship")
print("=" * 72)
_rows = []
for uid in (4, 8, 74, 83, 93, 2550, 12):
    st = _id_stem.get(uid)
    if not st:
        continue
    names = _stem_files.get(st, set())
    tot = 0
    for n in names:
        for suf in ("_x1.sld", "_x2.sld"):
            p = os.path.join(GP, n + suf)
            if os.path.exists(p):
                tot += os.path.getsize(p)
    _rows.append((uid, st, len(names), tot))
for uid, st, n, tot in _rows:
    print("     unit %-5d %-32s %2d animations  %10d B (%.1f MB)"
          % (uid, st, n, tot, tot / 1048576.0))

print()
print("  vs ONE animation (the standing one) for the same unit:")
for uid, st, n, tot in _rows[:4]:
    f = None
    for c in tk._civs:
        for u in c["units"]:
            if u["id"] == uid:
                sg = u.get("standing_graphic")
                f = fname(_by_id.get(sg[0])) if sg else None
                break
        if f:
            break
    one = 0
    for suf in ("_x1.sld", "_x2.sld"):
        p = os.path.join(GP, (f[:-3] if f.endswith("_x1") else f) + suf)
        if os.path.exists(p):
            one += os.path.getsize(p)
    print("     unit %-5d whole %10d B   standing only %9d B   ratio %.1fx"
          % (uid, tot, one, tot / max(one, 1)))

print()
print("=" * 72)
print("S11  does the stem rule ever produce a stem with NO files?")
print("=" * 72)
_missing = [(i, st) for i, st in _id_stem.items() if st not in _stem_files]
print("  unit ids whose derived stem has no file on disk: %d %s"
      % (len(_missing), _missing[:5]))
print("  (the stem is derived FROM a file that exists, so this must be 0)")
