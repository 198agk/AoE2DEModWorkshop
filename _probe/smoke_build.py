"""Build a deliberately OBVIOUS data mod for the in-game smoke test.

Goal: one glance at the running game answers "did the engine accept and render a
.dat that our writer produced?".

Chosen change: Villager (id 83) hit points 25 -> 2500.  Every game starts with
villagers on screen, they are the first thing anyone selects, and the HP number
is rendered large in the selection panel.  A 100x change cannot be mistaken for
a version difference.

Nothing is installed here -- this only writes to the workspace.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _ROOT)

from aoe2mod import api as A  # noqa: E402

OUT = os.path.join(_ROOT, "_smoke", "VillagerHP_smoke")

tk = A.open_toolkit()
tk._ensure()

print("=== before ===")
d = tk.describe(83, "unit")
print("  ", d["name"], "hp =", d["stats"].get("hit_points"))

intent = {"intent": "unit.stat", "unit": 83, "stat": "hit_points", "value": 2500}
p = tk.plan(intent)
print("=== plan ===")
print("   description :", p["description"])
print("   edit_count  :", p["edit_count"])
print("   mirror_count:", p.get("mirror_count"))
print("   civ_count   :", p["civ_count"])

man = tk.build(
    intent,
    OUT,
    title="Smoke Test Villager HP",
    author="aoe2mod smoke test",
    description="Temporary test mod built by the aoe2mod kernel. Villager hit points 25 -> 2500.",
    overwrite=True,
)

print("=== build ===")
for k in sorted(man.keys()):
    v = man[k]
    if isinstance(v, str) and len(v) > 90:
        v = v[:90] + "..."
    print("   %-16s %s" % (k, v))

print("=== files on disk ===")
for base, dirs, files in os.walk(OUT):
    for f in files:
        fp = os.path.join(base, f)
        print("   %10d  %s" % (os.path.getsize(fp), os.path.relpath(fp, OUT)))
