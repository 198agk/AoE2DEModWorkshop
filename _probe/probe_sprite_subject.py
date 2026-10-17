# -*- coding: utf-8 -*-
r"""Pick the subject for the ONE in-game test that settles loose-.sld override.

The loose-PNG override is proven; loose .sld is not -- no installed mod ships
one (0 of 9).  So the test must be small, unmistakable, and early:

  W1  resource / scenery objects the player sees in the first 20 seconds
      (gold, stone, tree, berry bush, sheep, boar, deer), with their stem,
      byte cost and anim count
  W2  the same for the villager and the Barracks (fallback subjects)
  W3  the frame grid of donor and target for each candidate pair
  W4  a genuinely different-looking donor: can we find one within ~1 MB?
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
_sem = None


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


_files = collections.defaultdict(set)
for fn in _on_disk:
    if fn.endswith("_x1.sld"):
        _files[stem_of(fn[:-4])].add(fn[:-4])
_byname = {}
for rec in _gfx:
    f = fname(rec)
    if f:
        _byname.setdefault(stem_of(f), []).append(rec)


def size(st, anims=None):
    tot = 0
    for n in _files.get(st, ()):
        if anims and anim_of(n) not in anims:
            continue
        for rel in (n + ".sld", n[:-3] + "_x2.sld"):
            p = os.path.join(GP, rel)
            if os.path.exists(p):
                tot += os.path.getsize(p)
    return tot


def grid(st, a):
    r = _byname.get(st, [])
    for rec in r:
        f = fname(rec)
        if f and anim_of(f) == a:
            return (rec.get("frame_count"), rec.get("angle_count"))
    return None


# resolve by unit id, using any civ
_id_stem = {}
_id_name = {}
for c in tk._civs:
    for u in c["units"]:
        sg = u.get("standing_graphic")
        if not sg:
            continue
        f = fname(_by_id.get(sg[0]))
        if f and (f + ".sld") in _on_disk:
            _id_stem.setdefault(u["id"], stem_of(f))
            _id_name.setdefault(u["id"], u.get("name"))

print("=" * 72)
print("W1  resource / scenery subjects (the player sees these at 0:00)")
print("=" * 72)
CAND = {
    66: "Gold Mine", 102: "Stone Mine", 349: "Oak Tree", 59: "Berry Bush",
    594: "Sheep", 48: "Boar", 65: "Deer", 1051: "Forage Bush?",
    284: "Fish?", 69: "Hawk?",
}
print("  %-6s %-26s %-30s %5s %10s %s"
      % ("unit", "internal name", "stem", "anims", "bytes", "idleA grid"))
for uid, label in sorted(CAND.items()):
    st = _id_stem.get(uid)
    if not st:
        print("  %-6d %-26s <no stem>" % (uid, label))
        continue
    print("  %-6d %-26s %-30s %5d %10d %s"
          % (uid, str(_id_name.get(uid))[:26], st,
             len(_files.get(st, ())), size(st), grid(st, "idleA")))

print()
print("  actually, let's not guess ids.  Stems whose name looks like these:")
for pat in ("gold", "stone", "tree_oak", "bush", "sheep", "boar", "deer", "berry"):
    hits = sorted(st for st in _files if pat in st)
    small = sorted(hits, key=lambda s: size(s))[:4]
    print("  %-10s %3d stems; smallest: %s"
          % (pat, len(hits), [(s, size(s)) for s in small]))

print()
print("=" * 72)
print("W2  fallback subjects: villager and Barracks")
print("=" * 72)
for uid in (83, 293, 12, 498):
    st = _id_stem.get(uid)
    if st:
        print("  unit %-5d %-30s anims %d bytes %d idleA %s"
              % (uid, st, len(_files.get(st, ())), size(st), grid(st, "idleA")))

print()
print("=" * 72)
print("W3/W4  one-animation swaps, cost and grid, for scenery")
print("=" * 72)


def one(st, a):
    for n in _files.get(st, ()):
        if anim_of(n) == a:
            tot = 0
            for rel in (n + ".sld", n[:-3] + "_x2.sld"):
                p = os.path.join(GP, rel)
                if os.path.exists(p):
                    tot += os.path.getsize(p)
            return tot
    return 0


_pairs = [("n_gold", "n_stone"), ("n_gold", "n_tree_oak"),
          ("u_vil_male_villager", "u_monk_west"),
          ("b_dark_barracks", "b_dark_house")]
for a, b in _pairs:
    if a not in _files or b not in _files:
        print("  %-24s / %-24s  <one is absent>" % (a, b))
        continue
    print("  target %-22s idleA %9d B grid %s" % (a, one(a, "idleA"), grid(a, "idleA")))
    print("  donor  %-22s idleA %9d B grid %s" % (b, one(b, "idleA"), grid(b, "idleA")))
    print("     -> swap ships %d B;  frames %s vs %s"
          % (one(b, "idleA"), (grid(b, "idleA") or (0, 0))[0] * (grid(b, "idleA") or (0, 1))[0],
             (grid(a, "idleA") or (0, 0))[0] * (grid(a, "idleA") or (0, 1))[0]))
    print()

print("=" * 72)
print("W5  cheapest possible subjects overall (smallest stems with idleA)")
print("=" * 72)
_rows = [(size(st), st, len(_files.get(st, ()))) for st in _files if grid(st, "idleA")]
_rows.sort()
for s, st, n in _rows[:15]:
    print("  %9d B  %-34s %d anims  grid %s" % (s, st, n, grid(st, "idleA")))
