"""Check what the age-variant family expands to for the Town Center and the
Villager, so the smoke test knows how many records a single intent moves."""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _ROOT)

from aoe2mod import api as A  # noqa: E402
from aoe2mod.intent import compiler as C  # noqa: E402

tk = A.open_toolkit()
tk._ensure()
sch, bindings = C.load_schema()

for uid in (71, 83, 12):
    d = tk.describe(uid, "unit")
    print("=== unit %d  %s   hp=%s ===" % (uid, d["name"], d["stats"].get("hit_points")))
    fam, hits = C.unit_targets(tk._civs, uid, ("hit_points",), tk._stats)
    print("   hits:", type(hits), len(hits) if hasattr(hits, "__len__") else "?")
    if hits:
        t0 = hits[0]
        print("   first hit:", type(t0), (len(t0) if hasattr(t0, "__len__") else t0))
    ids = sorted({h[2] for h in hits})
    print("   distinct record ids:", ids)
    for i in ids:
        vals = {}
        for h in hits:
            if h[2] == i:
                hp = h[3].get("hit_points")
                vals[hp] = vals.get(hp, 0) + 1
        print("      id %-6d hp -> civ count %s" % (i, vals))
