# -*- coding: utf-8 -*-
"""Build `dsh test v11` -- the villager WHOLE FAMILY, with filling.

v10 replaced unit 83's stem only, and the user reported the villager was a sheep
while standing and attacking but a human while chopping, mining and building
(m31530).  The cause: the engine re-points a task-swapping unit to a sibling
record and every sibling names its own art, so unit 83's family is 27 records
over 18 stems.

v11 asks for `whole_family`, which now also fills: no entity in the game owns all
ten animations the family needs (`seed` on 4 unit ids, `task` on 6, `carry` on 36,
`work` on 61), so a nearby sheep animation stands in for the five the sheep does
not have.  A stand-in must match the angle count and have at least as many frames.

Subject stays unit 83 <- unit 594 (sheep), so v10 and v11 are comparable.
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

V = 11
OUT = os.path.join(HERE, "out_dshtest_v%d" % V)
TARGET, DONOR = 83, 594

TITLE = TN.name_for(V, "全体村民连干活都是绵羊")
DESC = TN.description_for(
    V,
    "村民的 27 条记录 / 18 套图全部换成绵羊，包括砍树、挖矿、种田、建造",
    "mod 里只有 .sld，没有 .dat",
    extra_lines=[
        "用法：进游戏前勾选本 mod，用任意普通文明开一局。",
        "预期：村民无论站着、走路、攻击，还是砍树/挖矿/种田/建造/搬运，"
        "看到的都是绵羊。",
        "说明：绵羊没有「干活」这一套图，所以干活时借用它的攻击动画，"
        "搬运时借用走路动画——这是能做的最近似的替代，不是原图。",
        "注意：不要用六个 Chronicles 文明（阿契美尼德/雅典/斯巴达/马其顿/"
        "色雷斯/普鲁），他们的村民攻击动画帧数不同。",
    ])

tk = A.open_toolkit()
tk._ensure()

it = {"intent": "unit.sprite", "unit": TARGET, "donor": DONOR,
      "whole_family": True}
plan = tk.plan(it)
print("PLAN")
for k in ("editable", "file_count", "civ_count", "changes_dat",
          "mod_contains_dat", "edit_count", "fill", "target_count"):
    print("   %-16s %r" % (k, plan.get(k)))
fam = plan.get("family") or {}
for k in ("member_count", "distinct_stems", "stems_replaced",
          "members_with_art", "members_covered", "family_needs",
          "donor_supplies", "never_replaced", "filled"):
    print("   %-16s %r" % (k, fam.get(k)))
print("   warnings")
for w in plan.get("warnings") or []:
    print("      -", w)
assert plan["editable"], plan
assert fam["never_replaced"] == [], fam["never_replaced"]
assert fam["stems_replaced"] == fam["distinct_stems"], fam

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

print()
print("ON DISK")
total, n_sld, n_other = 0, 0, 0
for root, _d, fs in os.walk(OUT):
    for f in sorted(fs):
        p = os.path.join(root, f)
        total += os.path.getsize(p)
        if f.endswith(".sld"):
            n_sld += 1
        else:
            n_other += 1
print("   %d .sld + %d other, total %d bytes (%.1f MB)"
      % (n_sld, n_other, total, total / 1e6))
print("   has .dat: %s" % os.path.isfile(
    os.path.join(OUT, "resources", "_common", "dat", "empires2_x2_p1.dat")))

info = json.loads(open(os.path.join(OUT, "info.json"),
                       encoding="utf-8-sig").read())
print()
print("TITLE     %r  (%d UTF-8 bytes)" % (info["Title"],
                                           TN.utf8_len(info["Title"])))
