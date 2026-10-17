# -*- coding: utf-8 -*-
"""What separates the age variants of one building name?

70/191/192/463/464/465 all display as "House".  Dump every discriminating field
the .dat carries -- including the ones the walker reads and throws away -- so the
grouping is derived from data rather than guessed from the ids.
"""
import os
import sys
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod import api as A          # noqa: E402
from aoe2mod.dat import locate as L   # noqa: E402
from aoe2mod.semantic import index as S  # noqa: E402

tk = A.open_toolkit()
tk._ensure()
ix = S.index()

GROUPS = {
    "House":       [70, 191, 192, 463, 464, 465],
    "Barracks":    [12, 20, 132, 498],
    "Castle":      [82, 2418],
    "Archer":      [4],
}

for label, ids in GROUPS.items():
    print("=== %s ===" % label)
    for uid in ids:
        _, _, u = L.find_units(tk._civs, uid)[0]
        e = ix.get("unit", uid)
        print("  id %-6s internal=%-24s en=%-26s dll=%-8s "
              "hp=%-5s type=%-3s class=%-4s icon=%-5s"
              % (uid, repr(e.internal)[:24], e.en, e.name_string_id,
                 u.get("hit_points"), u.get("type"), u.get("class"), u.get("icon_id")))
        print("        speed=%-8s los=%-6s costs=%-40s n_atk=%s n_arm=%s"
              % (u.get("speed"), u.get("line_of_sight"),
                 [(c["type"], c["amount"], c.get("flag")) for c in (u.get("costs") or [])],
                 len((u.get("type50") or {}).get("attacks") or []),
                 len((u.get("type50") or {}).get("armors") or [])))
    print()

print("=== how many .dat unit ids resolve to each of these display names? ===")
for label in ("House", "Barracks", "Castle", "Town Center", "Archer", "Villager"):
    hits = tk.search(label, kind="unit", limit=50)
    print("  %-12s %2d hits" % (label, len(hits)))
