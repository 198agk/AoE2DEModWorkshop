# -*- coding: utf-8 -*-
r"""The observation card: what the user must look at, in Chinese, with numbers.

Picks the civilizations whose SHIPPED tree and panel contradict each other, so no
mod has to be installed or enabled at all.  Prints, per candidate, the on-screen
Chinese name of every contested unit and the building + age needed to see it.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"

# --- the game's own Chinese string table -------------------------------------
ZH = {}
kd = os.path.join(GAME, "resources", "zh", "strings", "key-value")
for fn in sorted(os.listdir(kd)):
    if not fn.endswith(".txt"):
        continue
    with open(os.path.join(kd, fn), "rb") as fh:
        for line in fh.read().decode("utf-8-sig", "replace").splitlines():
            line = line.strip()
            if not line or line.startswith("//") or "\t" not in line:
                continue
            k, _, v = line.partition("\t")
            if k.strip().isdigit() and v.startswith('"') and v.endswith('"'):
                ZH.setdefault(int(k.strip()), v[1:-1])


def zh_name(string_id):
    return ZH.get(string_id, "(no zh string)")


print("=" * 78)
print("零 mod 实验：出厂文件自己就互相矛盾")
print("=" * 78)

trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)

# --- what the game itself calls these units ---------------------------------
# `aoe2mod.semantic` is a PACKAGE: the entry point is
# `from aoe2mod.semantic.index import index`, and the returned index exposes
# `get(kind, uid)` (not a `.units` dict).  Calling `S.index()` on the package
# raises AttributeError because the package `__init__` re-exports nothing.
from aoe2mod.semantic.index import index as sem_index       # noqa: E402
idx = sem_index()


def unit_zh(uid):
    try:
        u = idx.get("unit", uid)
    except Exception:
        return None
    if u is None:
        return None
    # `Entity` carries the already-localized names as attributes (`zh`/`en`) and
    # the raw dict in `_extra`; there is no `.raw`.  Reading `getattr(u,"raw",{})`
    # yields {} for every unit and the card printed "?" for all of them -- a
    # lookup that fails silently into a printable value.
    return u.zh or u.en or u.internal


CASES = [
    # civ display name, unit id, panel sees it / tree sees it, building
    ("JURCHENS", "Jurchens", 77, "panel", 12),
    ("JURCHENS", "Jurchens", 473, "panel", 12),
    ("JURCHENS", "Jurchens", 567, "panel", 12),
    ("MUISCA", "Muisca", 359, "panel", 12),
    ("HUNS", "Huns", 532, "panel", 45),
    ("BULGARIANS", "Bulgarians", 569, "panel", 101),
    ("ARMENIANS", "Armenians", 569, "panel", 101),
    ("POLES", "Poles", 691, "panel", 45),
    ("WU", "Wu", 474, "panel", 87),
    ("MAPUCHE", "Mapuche", 528, "panel", 45),
    ("SHU", "Shu", 532, "panel", 45),
    ("GEORGIANS", "Georgians", 588, "tree", 49),
    ("SICILIANS", "Sicilians", 588, "tree", 49),
]

BLDING = {12: "兵营 Barracks", 45: "码头 Dock", 87: "靶场 Archery Range",
          101: "马厩 Stable", 49: "攻城武器厂 Siege Workshop"}
UNIT_BLDS = {}
for t in trees.values():
    for r in CT.unit_rows(t):
        if r.get("Node ID") is not None and r.get("Building ID") is not None:
            UNIT_BLDS.setdefault(r.get("Node ID"), set()).add(r.get("Building ID"))

for stem, disp, uid, who, bld in CASES:
    tree = trees.get(stem)
    if tree is None:
        continue
    pk = BP.panel_path_for(GAME, disp)
    obj = panels[pk[1]]["obj"]
    _bb, ent = BP.find_entry(obj, pk[1], uid, BP.UNITS_KEY)
    st = CT.node_status(tree, uid, CT.UNIT_USE_TYPES)
    row = CT.row_for(tree, uid, CT.UNIT_USE_TYPES) or {}
    print()
    print("  %-11s 单位 %-5s %s" % (stem, uid, unit_zh(uid) or "?"))
    print("     树 (CivTechTrees) 说：%-18s   面板 (futuravailableunits) 说：%s"
          % (st, ("列了，RequiredAge=%s" % ent.get("RequiredAge"))
             if ent else "没列"))
    print("     在 %s 里看；树行 Age ID = %s"
          % (BLDING.get(bld, "建筑 %s" % bld), row.get("Age ID")))
