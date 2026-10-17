# -*- coding: utf-8 -*-
r"""How does one unit own five animations?

The unit record names exactly ONE graphic (standing_graphic -> file).  The game
still walks, attacks and dies with different art.  Two candidate mechanisms:

  (a) the animation records sit at a fixed OFFSET from the standing one, or
  (b) the engine finds each animation by NAME, replacing the trailing token
      of the standing file.

This decides what a swap must write, so measure it directly.

  Y1  the exact file each unit's standing_graphic resolves to
  Y2  the graphics ids of one unit's animation records, and their arrangement
  Y3  is the trailing token of a resolved file always an ANIMATION, or can it
      be a variant word (gold / stone / 33 / 66)?
  Y4  how many files a unit really owns, by each candidate rule
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
_gfx = tk._stats["graphics"]
_by_id = {x.get("id"): x for x in _gfx}
_order = {x.get("id"): i for i, x in enumerate(_gfx)}


def fname(rec):
    if not isinstance(rec, dict):
        return None
    f = rec.get("file")
    if not isinstance(f, str):
        return None
    f = f.strip()
    return f if f and f != "None" else None


def anim_of(n):
    return n[:-3].rsplit("_", 1)[-1] if n.endswith("_x1") else None


def prefix_of(n):
    return n[:-3].rsplit("_", 1)[0] if n.endswith("_x1") else None


# the animation vocabulary, measured from the whole corpus
ANIMS = set()
for fn in _on_disk:
    if fn.endswith("_x1.sld"):
        ANIMS.add(anim_of(fn[:-4]))
print("distinct trailing tokens on disk: %d" % len(ANIMS))
print("  %s" % sorted(ANIMS)[:60])

# Y1 -------------------------------------------------------------------------
print()
print("=" * 72)
print("Y1  exact resolved file, per unit")
print("=" * 72)
_first = {}
for c in tk._civs:
    for u in c["units"]:
        sg = u.get("standing_graphic")
        if not sg:
            continue
        _first.setdefault(u["id"], (sg[0], fname(_by_id.get(sg[0]))))
for uid in (4, 8, 66, 102, 83, 74, 349, 594, 2550, 12):
    gid, f = _first.get(uid, (None, None))
    print("  unit %-5d gfx %-7s file %-34s trailing %r  prefix %r"
          % (uid, gid, f, anim_of(f) if f else None, prefix_of(f) if f else None))

# Y2 -------------------------------------------------------------------------
print()
print("=" * 72)
print("Y2  one unit's animation records: ids and arrangement")
print("=" * 72)
for uid in (4, 83, 66, 102):
    gid, f = _first.get(uid, (None, None))
    if not f:
        continue
    pf = prefix_of(f)
    sibs = [(x.get("id"), _order[x.get("id")], fname(x)) for x in _gfx
            if fname(x) and prefix_of(fname(x)) == pf]
    sibs.sort(key=lambda t: t[1])
    print("  unit %-5d standing gfx %-6d prefix %r" % (uid, gid, pf))
    print("        %d sibling records:" % len(sibs))
    for sid, pos, sf in sibs:
        print("           gfx %-6d arrpos %-6d %-34s  delta_id %+d  delta_pos %+d"
              % (sid, pos, sf, sid - gid, pos - _order[gid]))
    print()

# Y3 -------------------------------------------------------------------------
print("=" * 72)
print("Y3  is the trailing token an animation, or a variant word?")
print("=" * 72)
KNOWN = {"idleA", "idleB", "idleC", "walkA", "walkB", "attackA", "attackB",
         "deathA", "decayA", "runA", "taskA", "carryidleA", "carrywalkA",
         "flyA", "hoverA", "idle", "walk", "death", "decay", "attack", "run",
         "destruction", "rubble", "ruins", "cracked", "dead", "wreck", "fixed"}
_u = _v = 0
_ex = []
for c in tk._civs:
    for u in c["units"]:
        sg = u.get("standing_graphic")
        if not sg:
            continue
        f = fname(_by_id.get(sg[0]))
        if not f or (f + ".sld") not in _on_disk:
            continue
        t = anim_of(f)
        if t in KNOWN:
            _u += 1
        else:
            _v += 1
            if len(_ex) < 12:
                _ex.append((u["id"], f, t))
print("  records of RESOLVED units, trailing token:")
print("     a known animation word : %d" % _u)
print("     something else         : %d  %s" % (_v, _ex[:8]))
print()
print("  distinct non-animation tokens among unit-resolved files:")
_toks = collections.Counter()
for c in tk._civs:
    for u in c["units"]:
        sg = u.get("standing_graphic")
        if not sg:
            continue
        f = fname(_by_id.get(sg[0]))
        if f and (f + ".sld") in _on_disk and anim_of(f) not in KNOWN:
            _toks[anim_of(f)] += 1
print("     %s" % dict(_toks.most_common(20)))

# Y4 -------------------------------------------------------------------------
print()
print("=" * 72)
print("Y4  how many files a unit owns under the PREFIX rule")
print("=" * 72)
_files = collections.defaultdict(set)
for fn in _on_disk:
    if fn.endswith("_x1.sld"):
        _files[prefix_of(fn[:-4])].add(fn[:-4])
print("  distinct prefixes: %d" % len(_files))
for uid in (4, 8, 66, 102, 83, 349, 594, 2550):
    gid, f = _first.get(uid, (None, None))
    if not f:
        continue
    pf = prefix_of(f)
    names = sorted(_files.get(pf, ()))
    ids = sorted(set(i for c in tk._civs for u in c["units"]
                     if u.get("standing_graphic")
                     and fname(_by_id.get(u["standing_graphic"][0]))
                     and prefix_of(fname(_by_id.get(u["standing_graphic"][0]))) == pf
                     for i in [u["id"]]))
    print("  unit %-5d prefix %-24s files %d  ids sharing it %s"
          % (uid, pf, len(names), ids[:8]))
    for n in names:
        print("        %s  (%s)" % (n, anim_of(n)))
