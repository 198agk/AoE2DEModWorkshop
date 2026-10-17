# -*- coding: utf-8 -*-
r"""Two complementary single-layer tests beat one ambiguous one.

Neither a same-building nor a cross-building search finds a civilization with
BOTH kinds of contradiction and distinguishable names: the disagreement is a
*variant-id substitution*, and the two variants usually share a display name
(GEORGIANS 320 vs 588 are both "Siege Onager"; SPARTANS 2147 vs 13 are both
"Fishing Ship").

But the two 2-to-1 tests are COMPLEMENTARY, and running both is injective:

    JURCHENS (kind P)  button present => panel or union ; absent => tree or other
    SICILIANS (kind T) button present => tree  or union ; absent => panel or other

    present / absent -> PANEL        absent / present -> TREE
    present / present -> UNION       absent / absent  -> neither

This checks SICILIANS really is the clean kind-T (the tree grants 588, the panel
lists neither 588 nor 320), and identifies unit 320 so the Georgians collision is
understood rather than assumed.
"""
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402
from aoe2mod.semantic.index import index as sem_index       # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
idx = sem_index()
trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)

ZH = {}
kd = os.path.join(GAME, "resources", "zh", "strings", "key-value")
for fn in sorted(os.listdir(kd)):
    if fn.endswith(".txt"):
        with open(os.path.join(kd, fn), "rb") as fh:
            for line in fh.read().decode("utf-8-sig", "replace").splitlines():
                k, _, v = line.strip().partition("\t")
                if k.strip().isdigit() and v.startswith('"') and v.endswith('"'):
                    ZH.setdefault(int(k.strip()), v[1:-1])


def uname(uid):
    u = idx.get("unit", uid)
    return (u and (u.zh or u.en)) or ("unit %s" % uid)


print("=" * 76)
print("A  SICILIANS must be a CLEAN kind-T (tree grants, panel lists neither)")
print("=" * 76)
sc = trees["SICILIANS"]
objc = panels[BP.panel_path_for(GAME, "Sicilians")[1]]["obj"]
disp = "Sicilians"
print("  tree rows at building 49 (Siege Workshop):")
for r in sorted(CT.unit_rows(sc), key=lambda r: r.get("Node ID") or 0):
    if r.get("Building ID") == 49:
        uid = r.get("Node ID")
        _b, e = BP.find_entry(objc, disp, uid, BP.UNITS_KEY)
        print("     %-6s %-22s %-18s Age=%-3s panel=%s"
              % (uid, r.get("Name"), r.get("Node Status"), r.get("Age ID"),
                 "listed" if e else "SILENT"))
print("  panel entries at building 49:")
for e in (BP.entries(objc, disp, 49, BP.UNITS_KEY) or []):
    print("     %-6s %-22s RequiredAge=%s" % (e.get("ID"), e.get("Name"),
                                              e.get("RequiredAge")))
_b588, _e588 = BP.find_entry(objc, disp, 588, BP.UNITS_KEY)
_b320, _e320 = BP.find_entry(objc, disp, 320, BP.UNITS_KEY)
print()
print("  panel lists 588 (the tree's own RC row) : %r" % (_e588,))
print("  panel lists 320 (the Georgians one)     : %r" % (_e320,))
print("  -> %s"
      % ("CLEAN: absent means the panel is driving"
         if _e588 is None and _e320 is None
         else "NOT CLEAN -- the panel also lists something here"))

print()
print("=" * 76)
print("B  what IS unit 320, so the Georgians collision is understood")
print("=" * 76)
for uid in (320, 588, 2147, 13):
    u = idx.get("unit", uid)
    print("  unit %-6s zh=%-22s en=%-22s internal=%s"
          % (uid, (u.zh if u else None), (u.en if u else None),
             (u.internal if u else None)))

print()
print("=" * 76)
print("C  the two-game injective protocol")
print("=" * 76)
j = trees["JURCHENS"]
objo = panels[BP.panel_path_for(GAME, "Jurchens")[1]]["obj"]
print("  GAME 1 -- 女真人 Jurchens, 城堡时代, 兵营 (12):")
print("     树 says 长剑士(77) NotAvailable; 面板 lists it RequiredAge=3.")
print("     see 长剑士? -> panel or union ;  no 长剑士? -> tree or other")
print()
print("  GAME 2 -- 西西里 Sicilians, 帝王时代, 攻城武器厂 (49):")
print("     树 says 重型投石车(588) ResearchedCompleted; 面板 silent.")
print("     see 重型投石车? -> tree or union ;  no 重型投石车? -> panel or other")
print()
print("  READING THE TWO TOGETHER:")
for a, b, verdict in (("有", "没有", "PANEL 驱动"),
                      ("没有", "有", "TREE 驱动"),
                      ("有", "有", "UNION（两层都读）"),
                      ("没有", "没有", "都不是（另有来源）")):
    print("     游戏1 %-3s  游戏2 %-3s  ->  %s" % (a, b, verdict))
