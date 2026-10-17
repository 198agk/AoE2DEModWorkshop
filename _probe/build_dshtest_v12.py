# -*- coding: utf-8 -*-
"""Build `dsh test v12` -- the villager whole family, with the stone miner fixed.

v11 made every villager job a sheep except one: the user reported (m32098)
"石矿工搬运的变回了人，其他的好像都没问题都是羊" -- the STONE MINER while
carrying still showed a human.

The cause is the last layer of the same idea.  The engine picks a villager's art
three ways, and only two of them walk the unit table:

  1. the record's standing graphic      -> Villager Male, Builder Male, ...
  2. a sibling record by TaskSwapGroup  -> the 27-record family (v11's fix)
  3. the RESOURCE being carried         -> StoneMiner Male, named by NO record

`StoneMiner Male` owns exactly one file of its own,
`u_vil_male_miner_stone_carrywalkA_x1`, and it is not listed anywhere in the
`.dat`.  So a reskin that walks the records ships 458 files and still leaves that
one picture human.

v12 differs from v11 in ONE way: `plan_swap` now also carries the resource
variants of every stem it touches, so those 8 files are in the mod.  Everything
else -- the subject, the donor, the 27 records -- is identical, so v11 and v12
are directly comparable.
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

V = 12
OUT = os.path.join(HERE, "out_dshtest_v%d" % V)
TARGET, DONOR = 83, 594

TITLE = TN.name_for(V, "全体村民连干活都是绵羊含石矿搬运")
DESC = TN.description_for(
    V,
    "村民 27 条记录 / 18 套图 + 矿工搬运石的 4 套隐藏图，全部换成绵羊",
    "mod 里只有 .sld，没有 .dat",
    extra_lines=[
        "用法：进游戏前勾选本 mod，用任意普通文明开一局。",
        "预期：村民站着、走路、攻击、砍树、挖矿、种田、建造、搬石头，"
        "看到的都是绵羊。",
        "说明：绵羊没有「干活」和「搬运」这两套图，所以干活时借用攻击动画、"
        "搬运时借用走路动画——这是最近似的替代，不是原图。",
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
          "members_with_art", "members_covered", "never_replaced"):
    print("   %-16s %r" % (k, fam.get(k)))
variants = plan.get("resource_variants") or []
print("   resource_variants  %d" % len(variants))
for v in variants:
    print("      %s" % v["file"])
if plan.get("resource_variant_unmatched"):
    print("   UNMATCHED %s" % (plan["resource_variant_unmatched"],))
print("   warnings")
for w in plan.get("warnings") or []:
    print("      -", w)

assert plan["editable"], plan
assert fam["never_replaced"] == [], fam["never_replaced"]
assert fam["stems_replaced"] == fam["distinct_stems"], fam
# The whole point of v12 versus v11: the stone-carrying pictures are in the plan.
assert len(variants) == 4, variants
assert any("stone" in v["file"] for v in variants), variants
assert not plan.get("resource_variant_unmatched"), plan.get(
    "resource_variant_unmatched")

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
stone = []
for root, _d, fs in os.walk(OUT):
    for f in sorted(fs):
        p = os.path.join(root, f)
        total += os.path.getsize(p)
        if f.endswith(".sld"):
            n_sld += 1
            if "miner_stone" in f:
                stone.append(f)
        else:
            n_other += 1
print("   %d .sld + %d other, total %d bytes (%.1f MB)"
      % (n_sld, n_other, total, total / 1e6))
print("   stone-carrying pictures shipped: %d" % len(stone))
for f in sorted(stone):
    print("      %s" % f)
print("   has .dat: %s" % os.path.isfile(
    os.path.join(OUT, "resources", "_common", "dat", "empires2_x2_p1.dat")))

assert len(stone) == 8, stone

info = json.loads(open(os.path.join(OUT, "info.json"),
                       encoding="utf-8-sig").read())
print()
print("TITLE     %r  (%d UTF-8 bytes)" % (info["Title"],
                                           TN.utf8_len(info["Title"])))
assert TN.utf8_len(info["Title"]) <= TN.TITLE_MAX_BYTES
