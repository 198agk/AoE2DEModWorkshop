"""Locate the civ records and the starting-resource slots."""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _ROOT)

from aoe2mod import api as A  # noqa: E402
import aoe2mod.dat.parser as P  # noqa: E402
import aoe2mod.dat.locate as L  # noqa: E402

tk = A.open_toolkit()
tk._ensure()
print("parsed tuple:", tk._parsed)

st = tk._stats
print("stats keys:", sorted(st.keys())[:40])

civs = st.get("civs")
print("civs type:", type(civs), "len:", len(civs) if civs is not None else None)
c1 = civs[1]
print("civ[1] keys:", sorted(c1.keys()))

for k in sorted(c1.keys()):
    v = c1[k]
    if isinstance(v, list) and len(v) > 90:
        print("  long list field:", k, "len", len(v), "| 91..94 =", v[91:95])
