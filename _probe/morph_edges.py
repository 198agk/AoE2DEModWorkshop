"""Every engine replacement edge, split into AGE VARIANTS vs TASK MORPHS.

The in-game smoke test proved the gap: editing unit 83 (Villager) showed
2500/2500 while idle, but the panel became `建筑者 25/25` the moment the
villager was given a build task.  The engine had swapped the object onto a
different unit record.

`families.py` collects the same edges but keeps only those whose endpoints share
a nonzero display name (age variants).  This probe enumerates ALL of them and
classifies the remainder, to size the problem the product must handle.
"""
import collections
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _ROOT)

from aoe2mod import api as A            # noqa: E402
from aoe2mod.dat import families as F   # noqa: E402

tk = A.open_toolkit()
tk._ensure()
stats = tk._stats
# ★ NOT stats["civs"]: the parser's own civ records carry only
# ['class','hit_points','id','name','type'], so every display-name set is empty
# and the age/morph split silently collapses to "all morphs" (observed 0/406).
# families.py needs the LOCATOR records, which carry _dll_name/_dll_names.
civs = tk._civs

edges = F.warm(stats, tk.game_root)
print("total replacement edges (type-3 commands, both ids > 0):", len(edges))

# record lookup + name sets across every civ
by_id, names = {}, {}
for civ in civs:
    for u in civ.get("units") or ():
        uid = u.get("id")
        if uid is None:
            continue
        by_id.setdefault(uid, u)
        ns = names.setdefault(uid, set())
        ns.update(d for d in (u.get("_dll_names") or ()) if d)
        if u.get("_dll_name"):
            ns.add(u["_dll_name"])


def label(uid):
    u = by_id.get(uid)
    if u is None:
        return "<absent>"
    return u.get("name") or "?"


age, morph, weird = [], [], []
for src, dst in edges:
    a, b = by_id.get(src), by_id.get(dst)
    if a is None or b is None:
        weird.append((src, dst, "endpoint missing from civs"))
        continue
    if a.get("type") != b.get("type"):
        weird.append((src, dst, "type %s -> %s" % (a.get("type"), b.get("type"))))
        continue
    na, nb = names.get(src, set()), names.get(dst, set())
    if na and nb and (na & nb):
        age.append((src, dst))
    else:
        morph.append((src, dst))

print()
print("=== classified ===")
print("  AGE VARIANTS (shared nonzero display name):", len(age))
print("  TASK MORPHS  (no shared name):            ", len(morph))
print("  rejected for other reasons:               ", len(weird))

print()
print("=== the morph edges (what an edit to these ids would NOT follow) ===")
for src, dst in sorted(morph):
    print("   %-6d %-22s -> %-6d %-22s  type %s->%s  dll %s->%s"
          % (src, label(src), dst, label(dst),
             by_id[src].get("type"), by_id[dst].get("type"),
             by_id[src].get("_dll_name"), by_id[dst].get("_dll_name")))

print()
print("=== morph edges whose SOURCE is a villager-class unit (class 4, type 70) ===")
vills = [(s, d) for s, d in morph
         if by_id[s].get("type") == 70 and by_id[s].get("class") == 4]
for s, d in sorted(vills):
    print("   %-6d %-16s -> %-6d %-16s" % (s, label(s), d, label(d)))
print("   count:", len(vills))

print()
print("=== how many DISTINCT source ids do morph edges have? ===")
print("  ", len({s for s, _ in morph}))

print()
print("=== would a 'same stat signature' heuristic catch the villager case? ===")
# signature: every stat a user could edit, minus identity
STAT_KEYS = ("type", "class", "hit_points", "line_of_sight", "speed",
             "garrison_capacity", "sort_number")


def sig(uid):
    u = by_id.get(uid)
    if u is None:
        return None
    t50 = u.get("type50") or {}
    return (u.get("type"), u.get("class"), u.get("hit_points"),
            u.get("line_of_sight"), u.get("speed"),
            t50.get("max_range"), t50.get("reload_time"))


buckets = collections.defaultdict(set)
for uid in by_id:
    s = sig(uid)
    if s is not None:
        buckets[s].add(uid)

big = {s: ids for s, ids in buckets.items() if len(ids) > 1}
print("  distinct signatures:", len(buckets))
print("  signatures shared by >1 id:", len(big))
print("  ids inside a shared signature:", sum(len(v) for v in big.values()))

# does 83 sit with 118?
s83 = sig(83)
print("  signature(83):", s83)
print("  same-signature ids as 83:", sorted(buckets[s83]) if s83 in buckets else None)
print("  118 in that set:", 118 in (buckets.get(s83) or set()))
print("  293 (female) in that set:", 293 in (buckets.get(s83) or set()))
