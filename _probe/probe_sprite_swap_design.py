# -*- coding: utf-8 -*-
r"""What a sprite swap must write, and what the engine reads.

The unit record names ONE graphic (standing_graphic).  The game still animates
walk/attack/death, so siblings must be reachable some other way.  Measure:

  U1  the graphics record's own `name` field vs the file stem
  U2  every graphics record whose stem matches a target unit's stem
  U3  the one installed mod that ships .sld files (proof the path loads)
  U4  exact byte cost of replacing an ENTIRE stem, for the units a player
      would actually pick, and the blast radius on other units
  U5  donor/target animation-set mismatch, per real pair
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


def fname(rec):
    if not isinstance(rec, dict):
        return None
    f = rec.get("file")
    if not isinstance(f, str):
        return None
    f = f.strip()
    return f if f and f != "None" else None


def stem_of(name):
    if not name.endswith("_x1"):
        return None
    return name[:-3].rsplit("_", 1)[0]


def anim_of(name):
    return name[:-3].rsplit("_", 1)[-1]


def pair(n):                                   # n ends in _x1
    return [n + ".sld", n[:-3] + "_x2.sld"]


# U1 -------------------------------------------------------------------------
print("=" * 72)
print("U1  graphics record `name` vs the file stem")
print("=" * 72)
_same = _diff = _other = 0
_ex = []
for rec in _gfx:
    f = fname(rec)
    if not f or not f.endswith("_x1"):
        continue
    st = stem_of(f)
    nm = rec.get("name")
    if not isinstance(nm, str):
        _other += 1
        continue
    nm = nm.strip()
    if nm == st:
        _same += 1
    elif nm.startswith(st):
        _diff += 1
        if len(_ex) < 6:
            _ex.append((rec.get("id"), nm, f, st))
    else:
        _other += 1
print("  records: name == stem        : %d" % _same)
print("  records: name STARTS WITH stem: %d  e.g. %s" % (_diff, _ex[:3]))
print("  records: neither              : %d" % _other)

print()
print("  unit 4's standing graphic record in full:")
_arc = _by_id.get(633)
if _arc:
    for k in sorted(_arc):
        print("     %-24s %r" % (k, _arc[k]))

# U2 -------------------------------------------------------------------------
print()
print("=" * 72)
print("U2  do all animations of one unit have their OWN graphics record?")
print("=" * 72)
_stem_recs = collections.defaultdict(list)
for rec in _gfx:
    f = fname(rec)
    if f and f.endswith("_x1"):
        _stem_recs[stem_of(f)].append(rec)
_stem_files = collections.defaultdict(set)
for fn in _on_disk:
    if fn.endswith("_x1.sld"):
        _stem_files[stem_of(fn[:-4])].add(fn[:-4])

print("  stem                     records  files  match?")
for st in ("u_arc_archer", "u_inf_militia", "u_vil_male_villager",
           "u_inf_champi_scout", "b_dark_barracks"):
    r = sorted(a for a in (anim_of(fname(x)) for x in _stem_recs.get(st, [])) if a)
    f = sorted(anim_of(n) for n in _stem_files.get(st, ()))
    print("  %-24s %7d %6d  %s" % (st, len(r), len(f), "yes" if r == f else "NO r=%s f=%s" % (r, f)))

# U3 -------------------------------------------------------------------------
print()
print("=" * 72)
print("U3  the installed mod that ships .sld files")
print("=" * 72)
if not hasattr(__import__("aoe2mod.game.locations", fromlist=["x"]), "mod_dirs"):
    pass
import aoe2mod.game.locations as G
_prof = r"C:\Users\26913\Games\Age of Empires 2 DE"
try:
    _acc = G.pick_account(_prof)
    _mods = os.path.join(_acc, "mods")
except Exception as e:
    _acc = None
    _mods = None
    print("  (could not locate profile: %s)" % e)
if _mods and os.path.isdir(_mods):
    _found = []
    for base, dirs, files in os.walk(_mods):
        for fn in files:
            if fn.endswith(".sld"):
                _found.append(os.path.join(base, fn))
    print("  .sld files shipped by installed mods: %d" % len(_found))
    for p in _found[:12]:
        print("     %8d B  %s" % (os.path.getsize(p), os.path.relpath(p, _mods)))
    if _found:
        print()
        print("  are they byte-identical to the shipped file of the same name?")
        for p in _found[:12]:
            rel = os.path.relpath(p, _mods)
            parts = rel.split(os.sep)
            # .../<mod>/<storage path>/<name>
            for i in range(1, len(parts)):
                cand = os.path.join(GP, parts[-1])
                if os.path.exists(cand):
                    a = open(p, "rb").read()
                    b = open(cand, "rb").read()
                    print("     %-52s same=%s  mod %d B vs game %d B"
                          % (parts[-1], a == b, len(a), len(b)))
                    break
            else:
                print("     %-52s <no counterpart in game dir>" % parts[-1])

# U4 -------------------------------------------------------------------------
print()
print("=" * 72)
print("U4  whole-stem replacement: bytes and blast radius")
print("=" * 72)
_id_stem = {}
for c in tk._civs:
    for u in c["units"]:
        sg = u.get("standing_graphic")
        if not sg:
            continue
        f = fname(_by_id.get(sg[0]))
        if f and (f + ".sld") in _on_disk:
            _id_stem.setdefault(u["id"], stem_of(f))
_stem_ids = collections.defaultdict(set)
for i, st in _id_stem.items():
    if st:
        _stem_ids[st].add(i)


def whole_bytes(st):
    tot = 0
    for n in _stem_files.get(st, ()):
        for rel in pair(n):
            p = os.path.join(GP, rel)
            if os.path.exists(p):
                tot += os.path.getsize(p)
    return tot


print("  %-6s %-24s %6s %12s  %s" % ("unit", "stem", "anims", "bytes", "other units drawn"))
for uid in (4, 8, 74, 83, 93, 125, 2550, 692, 41, 13, 12, 82):
    st = _id_stem.get(uid)
    if not st:
        continue
    others = sorted(_stem_ids.get(st, set()) - {uid})
    print("  %-6d %-24s %6d %12d  %d %s"
          % (uid, st, len(_stem_files.get(st, ())), whole_bytes(st),
             len(others), others[:6]))

# U5 -------------------------------------------------------------------------
print()
print("=" * 72)
print("U5  donor/target animation sets for real pairs")
print("=" * 72)
for a, b in ((4, 8), (4, 74), (83, 74), (74, 4), (4, 2550), (93, 74), (8, 4)):
    sa, sb = _id_stem.get(a), _id_stem.get(b)
    if not sa or not sb:
        print("  unit %d or %d unresolved" % (a, b)); continue
    na = set(anim_of(n) for n in _stem_files.get(sa, ()))
    nb = set(anim_of(n) for n in _stem_files.get(sb, ()))
    print("  %-5d %-22s -> %-5d %-22s  tgt-only %-14s donor-only %s"
          % (a, sa, b, sb, sorted(na - nb), sorted(nb - na)))
print()
print("  a donor-only animation is dead weight; a target-only animation keeps")
print("  the game's art (the swap silently leaves it original).")
