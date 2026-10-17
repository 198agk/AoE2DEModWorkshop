# -*- coding: utf-8 -*-
r"""The swap's real safety condition.

Earlier I compared the .sld's total frame count to the graphics record's
`frame_count` and reported 1,484 disagreements.  That was my comparison being
wrong: `frame_count` is frames PER ANGLE and `angle_count` is the number of
angles, so the .sld total should be frame_count * angle_count.

  V1  sld_frames == frame_count * angle_count ?
  V2  for real donor->target pairs, do the (frames, angles) grids match
      per animation?  A mismatch is the silent "plays the wrong frame" case
      the graphics survey warned about.
  V3  what a swap must therefore REFUSE or WARN about
"""
import collections, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
os.chdir(ROOT)

import aoe2mod.api as A
import sldlib

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")
_on_disk = set(fn for fn in os.listdir(GP) if fn.endswith(".sld"))

tk = A.open_toolkit(game_root=GAME)
tk._ensure()
_gfx = tk._stats["graphics"]
_by_id = {x.get("id"): x for x in _gfx}


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


def anim_of(n):
    return n[:-3].rsplit("_", 1)[-1]


# V1 -------------------------------------------------------------------------
print("=" * 72)
print("V1  is the .sld total really frame_count * angle_count?")
print("=" * 72)
_ok = _bad = _missing = 0
_ex = []
for rec in _gfx:
    f = fname(rec)
    if not f or (f + ".sld") not in _on_disk:
        continue
    fc, ac = rec.get("frame_count"), rec.get("angle_count")
    if not isinstance(fc, int) or not isinstance(ac, int):
        continue
    p = os.path.join(GP, f + ".sld")
    try:
        n = len(sldlib.read_sld(p))
    except Exception:
        _missing += 1
        continue
    if fc * ac == n:
        _ok += 1
    else:
        # maybe the sld total is per-angle-total already, or has an extra frame
        if fc * ac + 1 == n or fc == n:
            _bad += 1
            if len(_ex) < 6:
                _ex.append((rec.get("id"), f, fc, ac, n, "off-by-one"
                            if fc * ac + 1 == n else "frame_count==total"))
        else:
            _bad += 1
            if len(_ex) < 6:
                _ex.append((rec.get("id"), f, fc, ac, n, "neither"))
print("  records checked        : %d" % (_ok + _bad + _missing))
print("  fc * ac == sld total   : %d" % _ok)
print("  off                 : %d" % _bad)
print("  sld unparsable         : %d" % _missing)
for e in _ex:
    print("     gfx %-6d %-34s fc=%-4d ac=%-4d total=%-5d %s" % e)

# V2 -------------------------------------------------------------------------
print()
print("=" * 72)
print("V2  donor vs target grids, per animation")
print("=" * 72)
_grid = {}
for rec in _gfx:
    f = fname(rec)
    if f and f.endswith("_x1"):
        _grid[f] = (rec.get("frame_count"), rec.get("angle_count"))


def grid(st, anim):
    return _grid.get("%s_%s_x1" % (st, anim))


_id_stem = {}
for c in tk._civs:
    for u in c["units"]:
        sg = u.get("standing_graphic")
        if not sg:
            continue
        f = fname(_by_id.get(sg[0]))
        if f and (f + ".sld") in _on_disk:
            _id_stem.setdefault(u["id"], stem_of(f))

print("  %-5s %-22s -> %-5s %-22s  %s"
      % ("from", "stem", "to", "stem", "per-animation grid comparison"))
for a, b in ((4, 8), (74, 83), (4, 74), (83, 74), (4, 2550), (8, 4)):
    sa, sb = _id_stem.get(a), _id_stem.get(b)
    if not sa or not sb:
        continue
    ga = {anim_of(n): grid(sa, anim_of(n)) for n in
          [x[:-4] for x in _on_disk if x.endswith("_x1.sld") and stem_of(x[:-4]) == sa]}
    gb = {anim_of(n): grid(sb, anim_of(n)) for n in
          [x[:-4] for x in _on_disk if x.endswith("_x1.sld") and stem_of(x[:-4]) == sb]}
    same, diff = [], []
    for k in sorted(set(ga) & set(gb)):
        (same if ga[k] == gb[k] else diff).append((k, ga[k], gb[k]))
    print("  %-5d %-22s -> %-5d %-22s" % (a, sa, b, sb))
    print("        shared animations %d: identical grid %d, DIFFERENT grid %d"
          % (len(set(ga) & set(gb)), len(same), len(diff)))
    for k, x, y in diff[:6]:
        print("           %-10s donor %s vs target %s" % (k, x, y))
    print("        donor-only %s   target-only %s"
          % (sorted(set(gb) - set(ga)), sorted(set(ga) - set(gb))))

# V3 -------------------------------------------------------------------------
print()
print("=" * 72)
print("V3  across the whole corpus: how often would a grid mismatch happen?")
print("=" * 72)
# group stems by their idle grid -- a swap between different grids is the risk
_by_idle = collections.defaultdict(list)
for st in set(_id_stem.values()):
    g = grid(st, "idleA")
    if g:
        _by_idle[g].append(st)
print("  distinct idle grids: %d" % len(_by_idle))
for g, sts in sorted(_by_idle.items(), key=lambda kv: -len(kv[1])):
    print("     %-14s %4d stems  e.g. %s" % (str(g), len(sts), sorted(sts)[:4]))

print()
print("  animation-name coverage across stems with an idleA file:")
_cov = collections.Counter()
for st in set(_id_stem.values()):
    for a in ("idleA", "walkA", "attackA", "deathA", "decayA", "idleB", "idleC",
              "taskA", "runA", "carryidleA", "carrywalkA", "attackB"):
        if grid(st, a):
            _cov[a] += 1
for k, v in _cov.most_common():
    print("     %-12s %d" % (k, v))
