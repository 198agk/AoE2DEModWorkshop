# -*- coding: utf-8 -*-
"""Which effect vocabulary ids actually occur in BASE, and which are unnamed.

The vendored tables are AGE's own and are English (and incomplete for DE).  A
Chinese label can only be written for ids that really occur, so measure them
rather than translating all 89 blindly.
"""
import contextlib
import io
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for p in (ROOT, HERE, os.path.join(HERE, "datparse")):
    if p not in sys.path:
        sys.path.insert(0, p)

from aoe2mod import api as A                                # noqa: E402
from aoe2mod.dat import locate as L                         # noqa: E402
from aoe2mod.intent import compiler as C                    # noqa: E402

tk = A.open_toolkit()
tk._ensure()
effs, _s = L.locate_effects(tk._raw)
tables = C.load_effect_tables()
# The vendored files are NESTED: each holds its rows under its own slot name.
types = tables["types"].get("types") or {}
attrs = tables["attributes"].get("attributes") or {}
classes = tables["classes"].get("classes") or {}

t_all, a_all, c_all = Counter(), Counter(), Counter()
a_mod, t_mod = Counter(), Counter()
for e in effs:
    for c in e["commands"]:
        t, a, b, cc, d = c["type"], c["a"], c["b"], c["c"], c["d"]
        t_all[t] += 1
        if t in C._EFFECT_OPERATION:
            t_mod[t] += 1
            a_mod[cc] += 1
            if cc in C._PACKED_ATTRIBUTES:
                u = C._packed_u16(d)
                c_all[u >> 8] += 1
            if b is not None and b != -1:
                c_all[b] += 1

print("=== command types that occur ===")
for t, n in sorted(t_all.items()):
    zh = C._OPERATION_ZH.get((C._EFFECT_OPERATION.get(t) or [None])[0])
    lbl = (types.get(str(t)) or {}).get("label")
    print("  type %-4d n=%-5d %-12s %s"
          % (t, n, ("op=" + zh) if zh else "", lbl or "<<MISSING>>"))

print("\n=== attribute ids that occur in modifier commands ===")
for cc, n in sorted(a_mod.items(), key=lambda kv: -kv[1]):
    lbl = attrs.get(str(cc))
    print("  attr %-4d n=%-5d %s" % (cc, n, lbl or "<<MISSING>>"))

print("\n=== class ids that occur ===")
for b, n in sorted(c_all.items(), key=lambda kv: -kv[1]):
    print("  class %-4d n=%-5d %s" % (b, n, classes.get(str(b)) or "<<MISSING>>"))

print("\nmissing attribute labels: %s" % sorted(
    cc for cc in a_mod if not attrs.get(str(cc))))
print("missing type labels: %s" % sorted(
    t for t in t_all if not (types.get(str(t)) or {}).get("label")))
print("missing class labels: %s" % sorted(
    b for b in c_all if not classes.get(str(b))))
