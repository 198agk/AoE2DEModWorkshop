# -*- coding: utf-8 -*-
r"""Can the product offer "swap this unit's animation"?

The unit -> .sld index now exists.  The next question is what a SWAP needs:
a swap means writing <target basename>_x1.sld / _x2.sld into the mod, filled
with a donor's bytes.  So measure:

  S1  every resolved unit gives a basename pair, and BOTH files exist on disk
  S2  the x2 name is the x1 name with the suffix swapped (not a separate field)
  S3  frame counts: is a donor's frame count equal to the target's?
      (the survey warned that a mismatch PLAYS THE WRONG FRAME rather than
       erroring, so the writer must be able to warn)
  S4  the graphics record's own frame_count vs the .sld header's num_frames
  S5  how much would a mod have to ship (bytes) for one unit
"""
import collections, os, struct, sys

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
_by_id = {x.get("id"): x for x in tk._stats["graphics"]}


def fname(rec):
    if not isinstance(rec, dict):
        return None
    f = rec.get("file")
    if not isinstance(f, str):
        return None
    f = f.strip()
    return f if f and f != "None" else None


print("=" * 72)
print("S1/S2  the basename pair")
print("=" * 72)
_n = 0
_x2_from_suffix = 0
_x2_other = []
_no_pair = []
_by_file = {}
for c in tk._civs:
    for u in c["units"]:
        sg = u.get("standing_graphic")
        if not sg:
            continue
        f = fname(_by_id.get(sg[0]))
        if not f or (f + ".sld") not in _on_disk:
            continue
        _n += 1
        _by_file.setdefault(f, set()).add(u["id"])
        if f.endswith("_x1"):
            x2 = f[:-3] + "_x2"
            if (x2 + ".sld") in _on_disk:
                _x2_from_suffix += 1
            else:
                _no_pair.append((u["id"], f, "x2 missing on disk"))
        else:
            _x2_other.append((u["id"], f))
print("  unit records resolving to a real .sld        : %d" % _n)
print("  whose name ends _x1 and whose _x2 also exists: %d (%.1f%%)"
      % (_x2_from_suffix, 100.0 * _x2_from_suffix / max(_n, 1)))
print("  names that do NOT end in _x1                 : %d %s"
      % (len(_x2_other), _x2_other[:5]))
print("  x1 present but x2 missing                    : %d %s"
      % (len(_no_pair), _no_pair[:5]))

print()
print("=" * 72)
print("S3  frame counts: would a swap know it went wrong?")
print("=" * 72)
_fc = {}
for f in sorted(_by_file):
    p = os.path.join(GP, f + ".sld")
    try:
        s = sldlib.read_sld(p)
        _fc[f] = len(s)
    except Exception as e:
        _fc[f] = None
print("  resolved sprites whose .sld parses: %d of %d"
      % (sum(1 for v in _fc.values() if v is not None), len(_fc)))

_gc = {}
for f, ids in _by_file.items():
    for rec in tk._stats["graphics"]:
        if fname(rec) == f:
            _gc[f] = (rec.get("frame_count"), rec.get("angle_count"))
            break
_agree = sum(1 for f, v in _fc.items()
             if v is not None and _gc.get(f) and _gc[f][0] == v)
print("  .sld header num_frames == graphics.frame_count: %d of %d"
      % (_agree, len(_fc)))
_dis = [(f, _fc[f], _gc.get(f)) for f in _fc
        if _fc[f] is not None and _gc.get(f) and _gc[f][0] != _fc[f]]
print("  disagreements: %d %s" % (len(_dis), _dis[:4]))

# Pairwise: pick concrete donor/target pairs and compare frame counts.
print()
print("  what a SWAP would face (donor frames vs target frames):")
_ex = []
for tgt in (4, 8, 74, 83, 93, 2550):
    recs = [u for c in tk._civs for u in c["units"] if u["id"] == tgt]
    if not recs:
        continue
    f = fname(_by_id.get((recs[0].get("standing_graphic") or [None])[0]))
    if not f or f not in _fc:
        continue
    _ex.append((tgt, f, _fc[f]))
for tgt, f, n in _ex:
    _same = [g for g, v in _fc.items() if v == n and g != f]
    print("     unit %-5d %-34s frames %-4d  -- %d other sprites have exactly that count"
          % (tgt, f, n, len(_same)))

print()
print("=" * 72)
print("S4  bytes a one-unit swap would ship")
print("=" * 72)
for tgt, f, n in _ex[:4]:
    tot = 0
    for suf in ("_x1", "_x2"):
        nm = f[:-3] + suf if f.endswith("_x1") else f + suf
        p = os.path.join(GP, nm + ".sld")
        if os.path.exists(p):
            tot += os.path.getsize(p)
    print("     unit %-5d ships %8d B  (%s_x1/_x2)" % (tgt, tot, f[:-3]))

print()
print("=" * 72)
print("S5  how many units share each sprite (a swap target's blast radius)")
print("=" * 72)
_hist = collections.Counter(len(v) for v in _by_file.values())
print("     %s" % dict(sorted(_hist.items())))
_big = sorted(_by_file.items(), key=lambda kv: -len(kv[1]))[:5]
for f, ids in _big:
    print("     %-38s draws %d units %s" % (f, len(ids), sorted(ids)[:8]))
print()
print("  A swap writes ONE basename, so every unit drawn by it changes.")
print("  -> the intent must say how many units share the donor/target.")
