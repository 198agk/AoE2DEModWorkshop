"""Find how the dat links a villager (id 83) to its task variants (Builder 118/212).

The in-game panel showed `村民 2500/2500` while idle but `建筑者 25/25` once the
villager started building.  Different name AND unedited HP => the engine is
showing a different unit record.  Look for a dat-level link.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _ROOT)

from aoe2mod import api as A  # noqa: E402

tk = A.open_toolkit()
tk._ensure()
civs = tk._stats["civs"]
c1 = civs[1]
byid = {}
for u in c1["units"]:
    byid.setdefault(u["id"], u)

print("British civ unit count:", len(c1["units"]), "distinct ids:", len(byid))
print()
print("=== all keys of unit 83 (村民 male) ===")
u83 = byid[83]
for k in sorted(u83):
    v = u83[k]
    s = repr(v)
    if len(s) > 160:
        s = s[:160] + "..."
    print("   %-26s %s" % (k, s))

print()
print("=== candidate variants ===")
for uid in (83, 293, 1810, 118, 212, 156, 222, 2714, 2715,
            120, 354, 122, 216, 123, 218, 124, 220, 214, 259,
            579, 581, 590, 592, 56, 57):
    u = byid.get(uid)
    if u is None:
        # maybe absent in this civ
        found = None
        for c in civs:
            for uu in c["units"]:
                if uu["id"] == uid:
                    found = uu
                    break
            if found:
                break
        if found is None:
            print("  id %-5d ABSENT FROM EVERY CIV" % uid)
            continue
        u = found
        tag = "(from another civ)"
    else:
        tag = ""
    print("  id %-5d type=%-4s class=%-5s hp=%-6s dll=%-6s name=%s %s"
          % (uid, u.get("type"), u.get("class"), u.get("hit_points"),
             u.get("_dll_name"), u.get("name"), tag))
