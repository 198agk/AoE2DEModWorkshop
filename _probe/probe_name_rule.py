# -*- coding: utf-8 -*-
r"""Pin the grouping rule, and find where it breaks.

Measured: the filename PREFIX rule over-merges badly (unit 15 `u_shp_junk`
resolves to prefix `u_shp`, which holds every ship in the game).  The graphics
record's own `name` field is what the engine calls the group
(`Archer (Attack)` / `Archer (Idle)` -> `Archer`), so the rule should be built
on it.  This measures the name rule's own failure modes:

  R1  how often a usable standing record has NO name to group by
  R2  are there name stems shared by DIFFERENT kinds of entity?
  R3  what does the name rule give for the cases the prefix rule got wrong
  R4  the final per-unit file set: size distribution
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


_stem_files = collections.defaultdict(set)
_stem_names = collections.defaultdict(set)
for x in _gfx:
    f, n = rec_file(x), rec_name(x)
    if not f or not n:
        continue
    s = stem(n)
    if s:
        _stem_files[s].add(f)
        _stem_names[s].add(n)

# R1 -------------------------------------------------------------------------
print("=" * 72)
print("R1  standing record with no name to group by")
print("=" * 72)
_n = _named = _noname = _nofile = 0
_seen = set()
for c in tk._civs:
    if c["name"] != "British":
        continue
    for u in c["units"]:
        sg = u.get("standing_graphic")
        if not sg or sg[0] < 0:
            continue
        _n += 1
        x = _by_id.get(sg[0])
        if rec_file(x) is None:
            _nofile += 1
        elif stem(rec_name(x)) is None:
            _noname += 1
        else:
            _named += 1
print("  British units with a standing id : %d" % _n)
print("     ...with a usable file         : %d" % _named)
print("     ...file present, NAME missing : %d" % _noname)
print("     ...no file string at all      : %d" % _nofile)

# R2 -------------------------------------------------------------------------
print()
print("=" * 72)
print("R2  name stems covering several DIFFERENT entity name-prefixes")
print("=" * 72)
_amb = []
for s, files in _stem_files.items():
    prefs = set(f.rpartition("_")[0] for f in files)
    if len(prefs) > 1:
        _amb.append((s, sorted(seen_pref := prefs)[:5], len(files)))
print("  stems whose files span >1 filename prefix: %d" % len(_amb))
for s, p, n in sorted(_amb, key=lambda t: -t[2])[:10]:
    print("     stem %-28s %d files, prefixes %s" % (s, n, p))

print()
print("  names behind the biggest stems (is one stem ever two entities?):")
for s, files in sorted(_stem_files.items(), key=lambda kv: -len(kv[1]))[:8]:
    print("     %-24s %3d files  names=%s" % (s, len(files), sorted(_stem_names[s])[:5]))

# R3 -------------------------------------------------------------------------
print()
print("=" * 72)
print("R3  the cases the prefix rule got wrong")
print("=" * 72)
for uid in (15, 6, 7, 10, 25, 11):
    for c in tk._civs:
        if c["name"] != "British":
            continue
        for u in c["units"]:
            if u["id"] != uid:
                continue
            sg = u.get("standing_graphic")
            x = _by_id.get(sg[0]) if sg else None
            f = rec_file(x)
            if not f:
                break
            print("  unit %-4d standing %-34s name=%r" % (uid, f, rec_name(x)))
            for n in sorted(_stem_files.get(stem(rec_name(x)), ())):
                mark = " <-- standing" if n == f else ""
                print("        %s%s" % (n, mark))
            break

# R4 -------------------------------------------------------------------------
print()
print("=" * 72)
print("R4  per-unit file set under the NAME rule")
print("=" * 72)
_sizes = collections.Counter()
_usable = 0
_unknown = 0
_sets = {}
for c in tk._civs:
    for u in c["units"]:
        sg = u.get("standing_graphic")
        x = _by_id.get(sg[0]) if sg else None
        f = rec_file(x)
        if not f or (f + ".sld") not in _on_disk:
            _unknown += 1
            continue
        s = stem(rec_name(x))
        if s is None:
            _sizes[1] += 1
            continue
        _usable += 1
        _sets[u["id"]] = frozenset(n for n in _stem_files[s]
                                   if (n + ".sld") in _on_disk)
        _sizes[len(_sets[u["id"]])] += 1
print("  unit records with resolvable art : %d" % _usable)
print("  unit records without             : %d" % _unknown)
print("  files-per-unit histogram: %s" % dict(sorted(_sizes.items())))
_distinct = collections.Counter(_sets.values())
_h = collections.Counter(_distinct.values())
print("  distinct file-sets: %d" % len(_distinct))
print("  units-per-fileset histogram: %s" % dict(sorted(_h.items())))
for fs, n in _distinct.most_common(4):
    print("     %2d units share %s" % (n, sorted(fs)))
