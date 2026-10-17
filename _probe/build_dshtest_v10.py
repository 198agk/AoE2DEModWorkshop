# -*- coding: utf-8 -*-
"""Build `dsh test v10` -- the first LOOSE .sld experiment.

Subject: unit 83 (Villager Male) <- unit 594 (Sheep).

Why this subject:
  * The player starts with three villagers, so the change is on screen at 0:00.
  * The mod ships ONLY .sld files and no .dat, so nothing else can explain it.
  * For the 57 standard civilizations all five shared animations have identical
    frame grids (60x16 / 30x16); only the six Chronicles civilizations differ on
    `attack` (45x16), so avoid playing one of those for this test.
"""
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import aoe2mod.api as A                                     # noqa: E402
import testmod_name as TN                                   # noqa: E402

V = 10
OUT = os.path.join(HERE, "out_dshtest_v%d" % V)
TARGET, DONOR = 83, 594

TITLE = TN.name_for(V, "村民变成绵羊")
DESC = TN.description_for(
    V,
    "全体村民（男性）的站立/行走/攻击/死亡/腐烂动画全部换成绵羊",
    "mod 里只有 .sld，没有 .dat",
    extra_lines=[
        "用法：进游戏前勾选本 mod，用任意普通文明开一局，开局就有三个村民。",
        "预期：三个村民长得像绵羊，走路也是绵羊的走路。",
        "注意：不要用六个 Chronicles 文明（阿契美尼德/雅典/斯巴达/马其顿/色雷斯/普鲁），"
        "他们的村民攻击动画帧数不同。",
    ])

tk = A.open_toolkit()
tk._ensure()

it = {"intent": "unit.sprite", "unit": TARGET, "donor": DONOR}
plan = tk.plan(it)
print("PLAN")
for k in ("editable", "description", "file_count", "civ_count",
          "target_stems", "donor_stems", "changes_dat", "mod_contains_dat",
          "edit_count", "writes", "warnings"):
    print("   %-16s %r" % (k, plan.get(k)))
assert plan["editable"], plan
assert plan["file_count"] == 20, plan["file_count"]

if os.path.isdir(OUT):
    shutil.rmtree(OUT)

man = tk.build(it, OUT, title=TITLE, author="aoe2mod test",
               description=DESC, overwrite=True)

print()
print("BUILD")
for k in ("edit_count", "changes_dat", "mod_contains_dat", "dat_is_carrier"):
    print("   %-16s %r" % (k, man.get(k)))
ver = man.get("verification") or {}
print("   verification ok  %r" % (ver.get("ok"),))
for k in ("checked", "missing_on_disk", "wrong_bytes", "identical_to_target"):
    print("   %-16s %r" % (k, ver.get(k)))
print("   proven           %r" % (ver.get("proven"),))
print("   not_proven       %r" % (ver.get("not_proven"),))

print()
print("ON DISK")
total = 0
for root, _d, fs in os.walk(OUT):
    for f in sorted(fs):
        p = os.path.join(root, f)
        rel = os.path.relpath(p, OUT)
        n = os.path.getsize(p)
        total += n
        print("   %-62s %9d" % (rel, n))
print("   total %d bytes (%.1f MB)" % (total, total / 1e6))

info = json.loads(open(os.path.join(OUT, "info.json"),
                       encoding="utf-8-sig").read())
print()
print("TITLE     %r  (%d UTF-8 bytes)" % (info["Title"],
                                           TN.utf8_len(info["Title"])))
print("DESCRIPTION")
for ln in info["Description"].split(" | "):
    print("   %s" % ln)
