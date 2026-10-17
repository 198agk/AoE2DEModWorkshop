# -*- coding: utf-8 -*-
r"""The prefix rule, refuted by a contradiction it cannot escape.

Claim under test (P): "the files drawing entity E are every .sld whose name
starts with E's standing file minus its last token".

If P were true, any two entities whose standing files share that prefix would
draw the SAME pictures.  Ships make this easy to check: `u_shp_junk_x1`,
`u_shp_canoe_x1`, `u_shp_caravel_x1`, `u_shp_carrack_x1` all live under
`u_shp`, but each belongs to a DIFFERENT unit.  Two different units drawing
identical art is not what this game ships, so P is refuted the moment those
units exist and their .sld files differ.

  C1  the units that own the files P would merge into one group
  C2  are those files distinct on disk (so the merge would be visibly wrong)?
  C3  the same check for a building family
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


def stem(n):
    if n is None:
        return None
    i = n.find(" (")
    return (n[:i] if i > 0 else n).strip() or None


def strip1(f):
    nr = f[:-3] if f.endswith("_x1") else f
    return nr.rpartition("_")[0]


# which unit(s) own each standing file
_owner = collections.defaultdict(set)
_seen = set()
for c in tk._civs:
    for u in c["units"]:
        if u["id"] in _seen:
            continue
        _seen.add(u["id"])
        sg = u.get("standing_graphic")
        f = rec_file(_by_id.get(sg[0])) if sg else None
        if f:
            _owner[f].add(u["id"])

print("=" * 72)
print("C1  the units that the PREFIX rule would merge under 'u_shp'")
print("=" * 72)
_fam = sorted(f for f in _owner if strip1(f) == "u_shp")
print("  files under the prefix u_shp that some unit stands on: %d" % len(_fam))
_multi = [f for f in _fam if len(_owner[f]) > 1]
print("  ...already shared by >1 unit: %d" % len(_multi))
for f in _fam[:14]:
    nm = rec_name([x for x in _gfx if rec_file(x) == f][0]) if any(
        rec_file(x) == f for x in _gfx) else None
    print("     %-30s units %-12s name=%r" % (f, sorted(_owner[f]), nm))

print()
print("=" * 72)
print("C2  prefix-rule group vs name-rule group, for the ship units")
print("=" * 72)
_stem_files = collections.defaultdict(set)
for x in _gfx:
    f, n = rec_file(x), rec_name(x)
    if f and stem(n):
        _stem_files[stem(n)].add(f)
for uid in (13, 15, 17, 21, 106):
    for c in tk._civs:
        if c["name"] != "British":
            continue
        hit = [u for u in c["units"] if u["id"] == uid]
        if not hit:
            continue
        sg = hit[0].get("standing_graphic")
        f = rec_file(_by_id.get(sg[0])) if sg else None
        if not f:
            print("  unit %-4d no resolvable art" % uid)
            continue
        P = sorted(x for x in _fam if strip1(x) == strip1(f))
        N = sorted(_stem_files.get(stem(rec_name(_by_id.get(sg[0]))), ()))
        print("  unit %-4d %-26s name=%r" % (uid, f, rec_name(_by_id.get(sg[0]))))
        print("        prefix rule -> %d file(s): %s" % (len(P), P[:5]))
        print("        name   rule -> %d file(s): %s" % (len(N), N[:5]))

print()
print("=" * 72)
print("C3  do P and N differ in CONTENT of the .sld on disk?")
print("=" * 72)
import hashlib


def sha(fn):
    p = os.path.join(GP, fn)
    if not os.path.exists(p):
        return None
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:16]


for fn in ("u_shp_junk_x1.sld", "u_shp_canoe_x1.sld", "u_shp_caravel_x1.sld",
           "u_shp_carrack_x1.sld", "u_shp_dreki_x1.sld"):
    print("  %-32s %s  %s bytes" % (fn, sha(fn),
          os.path.getsize(os.path.join(GP, fn)) if os.path.exists(os.path.join(GP, fn)) else "-"))
