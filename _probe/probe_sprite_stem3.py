# -*- coding: utf-8 -*-
r"""T1 corrected, T4 completed.  (Previous run shipped 0 B again: `n` already
ends in `_x1`, and bytes_of appended `_x1.sld` a second time -- the same shape
of mistake twice.  Build the twin name from the SUFFIX SWAP, once.)
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


def twin(x1base_unused):        # placeholder so no one copies the old shape
    raise AssertionError("do not use; see pair_of()")


def pair_of(n):
    r"""n is a basename WITHOUT .sld, ending in _x1.  -> [n.sld, n_with_x2.sld]"""
    assert n.endswith("_x1"), n
    return [n + ".sld", n[:-3] + "_x2.sld"]


def stem_of(name):
    if not (name.endswith("_x1") or name.endswith("_x2")):
        return None
    body = name[:-3]
    return body.rsplit("_", 1)[0] if "_" in body else None


def anim_of(name):
    return name[:-3].rsplit("_", 1)[-1]


_stem_files = collections.defaultdict(set)
for fn in _on_disk:
    if fn.endswith("_x1.sld"):
        st = stem_of(fn[:-4])
        if st:
            _stem_files[st].add(fn[:-4])          # keeps the _x1 suffix


def bytes_of_x1bases(names):
    tot = 0
    for n in names:
        for rel in pair_of(n):
            p = os.path.join(GP, rel)
            if os.path.exists(p):
                tot += os.path.getsize(p)
    return tot


_id_stem = {}
_standing = {}
for c in tk._civs:
    for u in c["units"]:
        sg = u.get("standing_graphic")
        if not sg:
            continue
        f = fname(_by_id.get(sg[0]))
        if f and (f + ".sld") in _on_disk and stem_of(f):
            _id_stem.setdefault(u["id"], stem_of(f))
            _standing.setdefault(u["id"], f)

print("=" * 72)
print("T1  bytes: one animation vs the whole stem  (bug actually fixed)")
print("=" * 72)
print("  %-6s %-26s %5s %12s %12s %8s"
      % ("unit", "stem", "anim", "whole B", "standing B", "ratio"))
for uid in (4, 8, 74, 83, 93, 2550, 12, 21):
    st = _id_stem.get(uid)
    if not st:
        continue
    names = _stem_files.get(st, set())
    whole = bytes_of_x1bases(names)
    one = bytes_of_x1bases([_standing[uid]]) if uid in _standing else 0
    print("  %-6d %-26s %5d %12d %12d %7.1fx"
          % (uid, st, len(names), whole, one, whole / max(one, 1)))

print()
print("  sanity: pair_of('u_arc_archer_idleA_x1') ->", pair_of("u_arc_archer_idleA_x1"))
print("  disk bytes for that pair:",
      bytes_of_x1bases(["u_arc_archer_idleA_x1"]),
      "(both files exist:",
      all(os.path.exists(os.path.join(GP, r)) for r in pair_of("u_arc_archer_idleA_x1")), ")")

print()
print("=" * 72)
print("T2b  a unit's OWN record vs its neighbours: how many records a stem owns")
print("=" * 72)
_recs_by_stem = collections.defaultdict(list)
for rec in _gfx:
    f = fname(rec)
    if f and stem_of(f):
        _recs_by_stem[stem_of(f)].append(rec)
print("  total graphics records           : %d" % len(_gfx))
print("  records whose file has a stem     : %d"
      % sum(len(v) for v in _recs_by_stem.values()))
print("  distinct stems                    : %d" % len(_recs_by_stem))
print("  NOTE: records-per-stem here counts animation RECORDS, while the disk")
print("        census counts FILES.  They are different questions.")

print()
print("=" * 72)
print("T4  which unit-record fields index the graphics array")
print("=" * 72)
_ex = None
for c in tk._civs:
    for u in c["units"]:
        if u["id"] == 4:
            _ex = u
            break
    if _ex:
        break
print("  unit 4 keys (all):")
print("   ", sorted(_ex.keys()))
print()
_cand = [(k, v) for k, v in _ex.items()
         if isinstance(v, int) and not k.startswith("_") and 0 <= v < 21001]
print("  scalar int fields in range:")
for k, v in sorted(_cand):
    print("     %-26s %-8d" % (k, v))
print()
print("  list fields:")
for k, v in sorted(_ex.items()):
    if isinstance(v, (list, tuple)) and not k.startswith("_"):
        print("     %-26s %r" % (k, v))
print()
print("  resolved for each candidate graphic id:")
for gid in sorted(set(v for _, v in _cand)):
    rec = _by_id.get(gid)
    print("     gfx %-7d %s" % (gid, (fname(rec) if rec else None) or "<no file>"))
