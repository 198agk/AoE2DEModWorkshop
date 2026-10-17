# -*- coding: utf-8 -*-
"""Audit probe 6: unitlines.json as a THIRD supplier of the Barracks menu,
and .dat-level tech enablement for tech 1350."""
import json, os, sys
sys.path.insert(0, r"D:\Software\DeepSeek Harness\工作区2")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

import aoe2mod.api as A
from aoe2mod.game import buildpanel as BP
from aoe2mod.game import civtechtrees as CT

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
D = os.path.join(GAME, "resources", "_common", "dat")


def head(t):
    print(); print("=" * 78); print(t); print("=" * 78)


head("6a: unitlines.json -- what is it, and which chains carry 74 / 2550?")
o = json.load(open(os.path.join(D, "unitlines.json"), encoding="utf-8-sig"))
print("   top keys:", list(o))
print("   Hint:", o.get("Hint"))
lines = o["UnitLines"]
print("   UnitLines: %d" % len(lines))
print("   sample[0] keys:", sorted(lines[0]) if isinstance(lines[0], dict) else lines[0])
for i, ln in enumerate(lines):
    s = json.dumps(ln)
    if "2550" in s or '"IDChain": [74' in s or (isinstance(ln, dict) and 74 in (ln.get("IDChain") or [])):
        print("   [%d] %s" % (i, json.dumps(ln, ensure_ascii=False)[:300]))

head("6b: does unitlines.json name buildings? (would it place buttons?)")
import collections
keys = collections.Counter()
for ln in lines:
    if isinstance(ln, dict):
        keys.update(ln.keys())
print("   per-line key histogram:", dict(keys))

head("6c: .dat tech records -- is tech 1350 present and per-civ enabled?")
tk = A.open_toolkit(); tk._ensure()
data, civs, civs_start, gv, tail, how = tk._parsed
print("   gv=%s civs=%d" % (gv, len(civs)))
print("   civ record keys:", sorted(civs[0]))
# tech records live where?
techs = getattr(tk, "_techs", None)
print("   tk._techs type: %s" % type(techs))
recs = tk._tech_records() if hasattr(tk, "_tech_records") else None
print("   tk._tech_records() -> %s" % (len(recs) if recs is not None else None))
if recs:
    print("   sample tech rec:", json.dumps(recs[0], ensure_ascii=False)[:300] if isinstance(recs[0], dict) else recs[0])
    for tid in (1350, 1351, 1352):
        m = [r for r in recs if (r.get("id") if isinstance(r, dict) else None) == tid]
        if m:
            print("   tech %d: %s" % (tid, json.dumps(m[0], ensure_ascii=False)[:400]))

head("6d: does any civ NAME appear inside unitlines.json?")
print("   'Britons' in file  : %r" % ("Britons" in json.dumps(o)))
print("   'BRITONS' in file  : %r" % ("BRITONS" in json.dumps(o)))
print()
for n in ("civilizations.json",):
    p = os.path.join(D, n)
    c = json.load(open(p, encoding="utf-8-sig"))
    cl = c.get("civilization_list")
    print("   %s civilization_list: %d entries" % (n, len(cl) if cl else 0))
    if cl:
        print("   sample:", json.dumps(cl[0], ensure_ascii=False)[:400])
        br = [x for x in cl if "brit" in json.dumps(x).lower()]
        print("   Britons record:", json.dumps(br[0], ensure_ascii=False)[:600] if br else None)
