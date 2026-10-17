"""How often does a plausible reskin change the animation GRID?

The record's own `frame_count` and `angle_count` are what the engine pairs with
the art, and the earlier survey of this layer found that a frame-count mismatch
"plays the wrong frames rather than erroring" -- a silent failure.  The planner
currently says nothing about it.

This measures, over every (target, donor) pair of units that the planner accepts,
how often at least one shared animation has a different (frame_count,
angle_count).  It uses only record fields: no file is opened.
"""
import collections
import itertools
import aoe2mod.api as A

tk = A.open_toolkit()
tk._ensure()
idx = tk._reskin_art()
civs = tk._parsed[1]
graphics = tk._stats["graphics"]

by_id = {}
for g in graphics:
    if g.get("id") is not None:
        by_id.setdefault(g["id"], g)


def grid_of(file_name):
    g = None
    for rec in graphics:
        if (rec.get("file") or "").strip() == file_name:
            g = rec
            break
    if g is None:
        return None
    return (g.get("frame_count"), g.get("angle_count"))


# one representative unit record per id (the first civilization that has it)
units = {}
for c in civs:
    for u in c.get("units", ()):
        if u.get("id") is not None and u["id"] not in units:
            units[u["id"]] = u
print("unit ids: %d" % len(units))

arts = {}
for uid, u in units.items():
    a = idx.art(u)
    if not a or a.get("kind") != "loose":
        continue
    grid = {}
    for anim, fname in a["tokens"].items():
        g = grid_of(fname)
        if g is not None:
            grid[anim] = g
    if grid:
        arts[uid] = (a, grid)
print("unit ids with a usable art grid: %d" % len(arts))

# how many animations carry a grid at all
sizes = collections.Counter(len(g) for _a, g in arts.values())
print("animations per unit: %s" % dict(sorted(sizes.items())))

ids = sorted(arts)
print("sampling all %d x %d ordered pairs would be %d; sampling targets only"
      % (len(ids), len(ids), len(ids) * (len(ids) - 1)))
TARGETS = ids[:120]
no_shared = same = differs = 0
worst = []
for t in TARGETS:
    _ta, tg = arts[t]
    for d in ids:
        if d == t:
            continue
        _da, dg = arts[d]
        shared = set(tg) & set(dg)
        if not shared:
            no_shared += 1
            continue
        bad = [k for k in shared if tg[k] != dg[k]]
        if bad:
            differs += 1
            if len(worst) < 12:
                worst.append((t, d, sorted(bad)[:3],
                              {k: (tg[k], dg[k]) for k in sorted(bad)[:2]}))
        else:
            same += 1
tot = no_shared + same + differs
print()
print("targets sampled          : %d" % len(TARGETS))
print("  pairs with no shared anim: %d (%.1f%%)" % (no_shared, 100.0 * no_shared / tot))
print("  pairs, every grid equal  : %d (%.1f%%)" % (same, 100.0 * same / tot))
print("  pairs, SOME grid differs : %d (%.1f%%)" % (differs, 100.0 * differs / tot))
print()
for w in worst:
    print("  %s -> %s  %s" % (w[0], w[1], w[2]))
    for k, v in w[3].items():
        print("      %-8s target %s donor %s" % (k, v[0], v[1]))
