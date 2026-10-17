# -*- coding: utf-8 -*-
r"""Final decision card: the ZERO-MOD experiment, verified end to end.

The mod-based test is unusable as built (identical `.dat` control with a sibling
mod; the sibling ships the same three engine paths with different content).  But
the shipped files ALREADY disagree, so no mod is needed at all.

This prints, for the best candidate civilizations, the full building menu as the
two files would draw it, and names the ONE button whose presence or absence
answers the question.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402
from aoe2mod.semantic.index import index as sem_index       # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
ZH = {}
kd = os.path.join(GAME, "resources", "zh", "strings", "key-value")
for fn in sorted(os.listdir(kd)):
    if fn.endswith(".txt"):
        with open(os.path.join(kd, fn), "rb") as fh:
            for line in fh.read().decode("utf-8-sig", "replace").splitlines():
                k, _, v = line.strip().partition("\t")
                if k.strip().isdigit() and v.startswith('"') and v.endswith('"'):
                    ZH.setdefault(int(k.strip()), v[1:-1])

idx = sem_index()
AGE = {1: "黑暗", 2: "封建", 3: "城堡", 4: "帝王"}
trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)

# Building names from the game's own string table (node -> Name String ID).
nodes = {}
for t in trees.values():
    for r in CT.rows_of(t):
        if r.get("Use Type") == "Building" and r.get("Node ID") is not None:
            sid = r.get("Name String ID")
            if sid and sid in ZH:
                nodes.setdefault(r.get("Node ID"), ZH[sid])


def uname(uid):
    u = idx.get("unit", uid)
    return (u and (u.zh or u.en)) or ("unit %s" % uid)


def card(stem, disp, bld):
    tree = trees[stem]
    pk = BP.panel_path_for(GAME, disp)
    obj = panels[pk[1]]["obj"]
    tr = {}
    for r in CT.unit_rows(tree):
        if r.get("Building ID") == bld and r.get("Node ID") is not None:
            tr[r["Node ID"]] = (r.get("Node Status"), r.get("Age ID"))
    pe = {}
    for e in (BP.entries(obj, pk[1], bld, BP.UNITS_KEY) or []):
        pe[e.get("ID")] = e.get("RequiredAge")
    print("=" * 78)
    print("%s（%s） —— 建筑 %s（%s）" % (disp, stem, bld, nodes.get(bld, "?")))
    print("=" * 78)
    ids = sorted(set(tr) | set(pe), key=lambda i: (pe.get(i) or 9, i))
    print("  %-7s %-22s %-6s %-20s %s" % ("单位", "中文名", "时代",
                                          "树 CivTechTrees", "面板"))
    for i in ids:
        st, age = tr.get(i, (None, None))
        p = pe.get(i)
        a = p or age
        print("  %-7s %-22s %-6s %-20s %s"
              % (i, uname(i), AGE.get(a, "?"),
                 st if st else "（无行）", "列了" if p else "没列"))
    diff = [i for i in ids
            if (tr.get(i) and tr[i][0] != "NotAvailable" and i not in pe)
            or (i in pe and tr.get(i) and tr[i][0] == "NotAvailable")
            or (i in pe and i not in tr)]
    print()
    for i in diff:
        st = (tr.get(i) or ("（无行）",))[0]
        p = pe.get(i)
        print("  ★ 分歧：%s（%d）  树=%s  面板=%s  时代=%s"
              % (uname(i), i, st, "列了" if p else "没列",
                 AGE.get(p or (tr.get(i) or (None, None))[1], "?")))
    return diff


d1 = card("JURCHENS", "Jurchens", 12)
print()
d2 = card("BRITONS", "Britons", 12)
