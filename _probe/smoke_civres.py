"""Examine civ Resources[91..94] (Starting Food/Wood/Stone/Gold)."""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _ROOT)

from aoe2mod import api as A  # noqa: E402

tk = A.open_toolkit()
tk._ensure()
civs = tk._stats["civs"]
print("num civs:", len(civs))

c1 = civs[1]
res = c1["resources"]
print("resources type:", type(res), "len:", len(res))
print("indices 88..96:", [(i, res[i]) for i in range(88, 97)])
nz = [(i, v) for i, v in enumerate(res) if v]
print("nonzero:", len(nz))
print("first 40 nonzero:", nz[:40])

# does any civ differ on 91..94?
print("--- 91..94 per civ (first 8 civs) ---")
for i, cv in enumerate(civs[:8]):
    r = cv["resources"]
    print("  civ[%d] %-14s %s" % (i, cv.get("name"), r[91:95]))

# how many civs have nonzero starting resources?
cnt = sum(1 for cv in civs if any(cv["resources"][91:95]))
print("civs with any nonzero 91..94:", cnt, "of", len(civs))
