"""Does the unit HEADER task list name the villager task variants?

The in-game test: villager id 83 shows 2500 while idle, then the panel becomes
`建筑者 25/25` once given a build order.  The engine clearly switched to another
unit record.  The parser already reads a per-header `tasks` array
(`read_task`, each entry carrying `task_type` and `id`).  If those ids are the
variant unit ids, the mapping is IN THE DATA and needs no heuristic.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))

from aoe2mod import api as A  # noqa: E402

tk = A.open_toolkit()
tk._ensure()

uh = tk._stats.get("unit_headers")
print("unit_headers:", type(uh).__name__, len(uh) if uh is not None else None)

if uh:
    e = uh[83]
    print("header[83] keys:", sorted(e.keys()) if isinstance(e, dict) else e)
    tasks = (e or {}).get("tasks") or []
    print("header[83] exists:", (e or {}).get("exists"), "task count:", len(tasks))
    for t in tasks:
        print("   task_type=%-4s id=%-6s" % (t.get("task_type"), t.get("id")))

    print()
    print("=== headers whose task ids overlap the villager family ===")
    VILL = {83, 118, 212, 156, 222, 120, 354, 122, 216, 123, 218, 124, 220,
            579, 581, 259, 214, 592, 590, 56, 57, 1810, 1891, 1892, 2333, 2334,
            2714, 2715, 293}
    for i, ent in enumerate(uh):
        ts = (ent or {}).get("tasks") or []
        ids = {t.get("id") for t in ts}
        hit = ids & VILL
        if hit and len(hit) >= 2:
            print("   header %-5d -> %s" % (i, sorted(hit)))

    print()
    print("=== ANY header with more than 8 tasks ===")
    for i, ent in enumerate(uh):
        ts = (ent or {}).get("tasks") or []
        if len(ts) > 8:
            print("   header %-5d tasks=%-3d ids=%s" % (i, len(ts), [t.get("id") for t in ts][:14]))
