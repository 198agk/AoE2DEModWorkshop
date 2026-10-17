# -*- coding: utf-8 -*-
r"""Follow-ups the stem probe raised.

The stem probe shipped 0 B for whole-unit swaps -- my own bug (`fn[:-4]` keeps
the `_x1`, then I appended `_x1.sld` again).  Fix it, and answer the question
that decides the intent's shape:

  T1  corrected bytes for one animation vs the whole stem
  T2  how many graphics RECORDS share one stem, and which unit fields reach them
      -- if the engine resolves each animation through its own record, then
         "replace the unit's art" means "replace every record's file"
  T3  do donor and target stems have the same ANIMATION SET?  (a mismatched
      animation list is the silent failure the survey warned about)
  T4  which unit fields carry a graphic id at all
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
    if not (name.endswith("_x1") or name.endswith("_x2")):
        return None
    body = name[:-3]
    return body.rsplit("_", 1)[0] if "_" in body else None


def anim_of(name):
    if not (name.endswith("_x1") or name.endswith("_x2")):
        return None
    return name[:-3].rsplit("_", 1)[-1]


# T1 -------------------------------------------------------------------------
print("=" * 72)
print("T1  bytes: one animation vs the whole stem  (bug fixed)")
print("=" * 72)
_stem_files = collections.defaultdict(set)
for fn in _on_disk:
    if not fn.endswith("_x1.sld"):
        continue
    st = stem_of(fn[:-4])
    if st:
        _stem_files[st].add(fn[:-4])


def bytes_of(names):
    tot = 0
    for n in names:
        for suf in ("_x1.sld", "_x2.sld"):
            p = os.path.join(GP, n + suf)
            if os.path.exists(p):
                tot += os.path.getsize(p)
    return tot


_id_stem = {}
for c in tk._civs:
    for u in c["units"]:
        sg = u.get("standing_graphic")
        if not sg:
            continue
        f = fname(_by_id.get(sg[0]))
        if f and (f + ".sld") in _on_disk and stem_of(f):
            _id_stem.setdefault(u["id"], stem_of(f))

print("  %-6s %-26s %5s %14s %14s %8s" % ("unit", "stem", "anim", "whole B", "standing B", "ratio"))
for uid in (4, 8, 74, 83, 93, 2550, 12, 21):
    st = _id_stem.get(uid)
    if not st:
        continue
    names = _stem_files.get(st, set())
    whole = bytes_of(names)
    standing = None
    for c in tk._civs:
        for u in c["units"]:
            if u["id"] == uid:
                sg = u.get("standing_graphic")
                standing = fname(_by_id.get(sg[0])) if sg else None
                break
        if standing:
            break
    one = bytes_of([standing]) if standing else 0
    print("  %-6d %-26s %5d %14d %14d %7.1fx"
          % (uid, st, len(names), whole, one, whole / max(one, 1)))

# T2/T3 ---------------------------------------------------------------------
print()
print("=" * 72)
print("T2/T3  graphics records per stem, and the animation set")
print("=" * 72)
_recs_by_stem = collections.defaultdict(list)
for rec in _gfx:
    f = fname(rec)
    if f and stem_of(f):
        _recs_by_stem[stem_of(f)].append(rec)
print("  distinct stems that own graphics records : %d" % len(_recs_by_stem))
_h = collections.Counter(len(v) for v in _recs_by_stem.values())
print("  records per stem: %s" % dict(sorted(_h.items())))

print()
print("  animation sets -- same stem means the same set by construction;")
print("  the real risk is DONOR vs TARGET having different sets:")
for a, b in ((4, 8), (4, 74), (83, 74), (4, 2550)):
    sa, sb = _id_stem.get(a), _id_stem.get(b)
    if not sa or not sb:
        continue
    na = set(anim_of(n) for n in _stem_files.get(sa, ()))
    nb = set(anim_of(n) for n in _stem_files.get(sb, ()))
    print("     unit %-5d (%s) vs %-5d (%s)" % (a, sa, b, sb))
    print("        target %d anims, donor %d anims" % (len(na), len(nb)))
    print("        target-only %s" % sorted(na - nb))
    print("        donor-only  %s" % sorted(nb - na))

print()
print("  what animation names exist, across all resolved stems:")
_all_anims = collections.Counter()
for st in set(_id_stem.values()):
    for n in _stem_files.get(st, ()):
        _all_anims[anim_of(n)] += 1
for k, v in _all_anims.most_common():
    print("     %-20s %d stems" % (k, v))

# T4 -------------------------------------------------------------------------
print()
print("=" * 72)
print("T4  which unit fields carry a graphic id")
print("=" * 72)
print("  unit keys whose value is an int that indexes the graphics array:")
_ex = None
for c in tk._civs:
    for u in c["units"]:
        if u["id"] == 4:
            _ex = u
            break
    if _ex:
        break
for k in sorted(_ex):
    v = _ex[k]
    if isinstance(v, int) and not k.startswith("_") and 0 <= v < 21001:
        print("     %-24s %-8d" % (k, v))
print()
print("  graphics ids reachable from unit 4's own record:")
_ids = [v for k, v in _ex.items()
        if isinstance(v, int) and not k.startswith("_") and 0 <= v < 21001]
for gid in sorted(set(_ids)):
    rec = _by_id.get(gid)
    f = fname(rec) if rec else None
    print("     gfx %-7d %s" % (gid, f or "<no file>"))
