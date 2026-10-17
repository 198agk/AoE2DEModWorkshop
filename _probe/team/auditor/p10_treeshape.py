# -*- coding: utf-8 -*-
"""Audit probe 10: what IS the tree object's shape? (p9's 9b/9d zeros may be vacuous)"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import json, os, sys, collections
sys.path.insert(0, _HERE_PATH("..", "..", ".."))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from aoe2mod.game import buildpanel as BP
from aoe2mod.game import civtechtrees as CT

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"

def head(t):
    print(); print("=" * 78); print(t); print("=" * 78)

trees = CT.load_trees(GAME)
brit = trees["BRITONS"]
print("type(brit) =", type(brit))
print("keys:", list(brit) if hasattr(brit, "keys") else "n/a")
for k, v in (brit.items() if hasattr(brit, "items") else []):
    print("   %-20s %s  len=%s" % (k, type(v).__name__, len(v) if hasattr(v, "__len__") else "-"))

head("10a: raw file keys (what the JSON on disk actually holds)")
p = os.path.join(GAME, CT.CIVTECHTREES_REL, "BRITONS.json")
raw = json.load(open(p, encoding="utf-8-sig"))
print("   disk keys:", list(raw))
for k, v in raw.items():
    print("   %-20s %s len=%s" % (k, type(v).__name__, len(v) if hasattr(v, "__len__") else "-"))

head("10b: CT.row_for / node_status internals -- which key do they scan?")
import inspect
for fn in (CT.row_for, CT.node_status, CT.can_build, CT.donor_row, CT.grant):
    try:
        src = inspect.getsource(fn)
    except Exception as e:
        src = "?? %s" % e
    print("-" * 70)
    print("### %s" % fn.__name__)
    print("\n".join(src.splitlines()[:45]))

head("10c: how many rows does each key actually hold (Britons + Incas)")
for ck in ("BRITONS", "INCAS"):
    t = trees[ck]
    for k, v in (t.items() if hasattr(t, "items") else []):
        if isinstance(v, list):
            print("   %-10s %-20s %d rows" % (ck, k, len(v)))
