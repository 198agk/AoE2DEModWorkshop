# -*- coding: utf-8 -*-
"""Is the Displayed* family a set of UI mirrors of the real fields?

read_type50 stores, in order: MaxRange, BlastWidth, ReloadTime,
DisplayedMeleeArmour, DisplayedAttack, DisplayedRange, DisplayedReloadTime.

If DisplayedRange always equals MaxRange and DisplayedReloadTime always equals
ReloadTime in shipped data, then "Displayed* = the number the panel shows, real
field = the number the engine uses" is a structural fact about the format, not
a guess -- and displayed_attack's relationship to the attacks[] list follows the
same pattern.
"""
import sys
from collections import Counter
root = r"D:\Software\DeepSeek Harness\工作区2"
sys.path.insert(0, root)
from aoe2mod import api as A

tk = A.open_toolkit()
tk.version
civs = tk._civs

seen = set()
units = []
for c in civs:
    for u in c["units"]:
        key = (u["id"], u.get("name"))
        if key in seen:
            continue
        seen.add(key)
        units.append(u)

print("distinct units: %d | with type50: %d"
      % (len(units), sum(1 for u in units if u.get("type50"))))

def compare(label, a_key, b_key, only50=True):
    eq = ne = miss = 0
    examples = []
    for u in units:
        t50 = u.get("type50")
        if only50 and not t50:
            continue
        t50 = t50 or {}
        a, b = t50.get(a_key), t50.get(b_key)
        if a is None or b is None:
            miss += 1
            continue
        if a == b:
            eq += 1
        else:
            ne += 1
            if len(examples) < 10:
                examples.append((u["id"], u.get("name"), a, b))
    print()
    print("%-46s equal %-5d different %-4d (%.1f%% agree)  absent %d"
          % ("%s vs %s" % (a_key, b_key), eq, ne,
             100.0 * eq / (eq + ne) if (eq + ne) else 0.0, miss))
    for e in examples:
        print("      id %-6s %-32s %s=%-8s %s=%s" % (e[0], e[1], a_key, e[2], b_key, e[3]))

compare("DisplayedRange", "displayed_range", "max_range")
compare("DisplayedReloadTime", "displayed_reload_time", "reload_time")

# And: is displayed_range nonzero only when max_range is nonzero?
print()
print("=== displayed_range where max_range == 0 ===")
n = 0
for u in units:
    t50 = u.get("type50")
    if not t50:
        continue
    if (t50.get("max_range") or 0) == 0 and (t50.get("displayed_range") or 0) != 0:
        n += 1
        if n <= 10:
            print("      id %-6s %-32s max_range=%s displayed_range=%s"
                  % (u["id"], u.get("name"), t50.get("max_range"), t50.get("displayed_range")))
print("   count:", n)

print()
print("keys present on a type50 block:")
sample = next(u for u in units if u.get("type50"))
print("   ", sorted(sample["type50"].keys()))
