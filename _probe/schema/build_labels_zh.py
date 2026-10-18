# -*- coding: utf-8 -*-
"""build_labels_zh.py -- generate the Chinese label table for effect vocabulary.

The engine's own vocabulary is English and lives in three vendored tables
(effect_command_types / effect_attributes / armor_classes).  The product's
users read Chinese, but hardcoding translations in Python would violate the
project rule that the format description is external DATA -- a game version or
a wording change must be a JSON edit, never a code change.

So this generator writes ``effect_labels_zh.json``: the same ids, with Chinese
names.  It is generated rather than hand-typed so an id can never be mistyped,
and so the id set provably matches the English tables.

MISSING IS MEANINGFUL.  Only ids we can name honestly are translated.  Anything
else falls back to AGE's English label, and anything AGE does not name at all
renders as a bare number ("Class 251", "attribute 158") -- the product must
never invent a name for a field it cannot explain.

Run:  python _probe/schema/build_labels_zh.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Attributes (the C parameter of a modifier command).
# ---------------------------------------------------------------------------
ATTRIBUTES = {
    0: "生命值",
    1: "视野",
    2: "驻扎容量",
    3: "单位尺寸 X",
    4: "单位尺寸 Y",
    5: "移动速度",
    6: "转向速度",
    7: "未使用",
    8: "护甲",
    9: "攻击力",
    10: "攻击间隔",
    11: "命中率",
    12: "最大射程",
    13: "工作效率",
    14: "携带量",
    15: "基础护甲",
    16: "弹射物单位",
    17: "图标/图形角度",
    18: "地形防御加成",
    19: "启用智能弹道",
    20: "最小射程",
    21: "第一种资源存储量",
    22: "溅射范围",
    23: "搜索半径",
    24: "隐藏伤害减免",
    25: "图标",
    26: "第二种资源存储量",
    27: "第三种资源存储量",
    28: "迷雾可见性",
    29: "遮挡模式",
    30: "驻扎类型",
    31: "未知",
    32: "单位尺寸 Z",
    33: "可建造于",
    34: "地基地形",
    40: "英雄状态",
    41: "帧延迟",
    42: "训练地点",
    43: "训练按钮",
    44: "溅射攻击等级",
    45: "溅射防御等级",
    46: "面板攻击力",
    47: "面板射程",
    48: "面板近战护甲",
    49: "面板远程护甲",
    50: "单位名称字符串",
    51: "单位简介字符串",
    52: "未使用",
    53: "地形限制",
    54: "单位特性",
    55: "单位文明",
    56: "单位特性片段",
    57: "死亡单位",
    58: "快捷键",
    59: "最大充能",
    60: "充能速率",
    61: "充能事件",
    62: "充能类型",
    63: "战斗能力",
    64: "攻击散布",
    65: "副弹射物单位",
    66: "血液单位",
    67: "弹道命中模式",
    68: "弹道消失模式",
    69: "弹道弧线",
    70: "攻击图形",
    71: "站立图形",
    72: "第二站立图形",
    73: "死亡图形",
    74: "尸变图形",
    75: "行走图形",
    76: "奔跑图形",
    77: "特殊图形",
    100: "全部资源成本",
    101: "训练时间",
    102: "弹丸总数",
    103: "食物成本",
    104: "木材成本",
    105: "黄金成本",
    106: "石料成本",
    107: "最大弹丸总数",
    108: "驻扎治疗速率",
    109: "再生速率",
    110: "人口占用",
    111: "最短招降时间修正",
    112: "最长招降时间修正",
    113: "招降成功率修正",
    114: "阵型类别",
    115: "范围伤害",
}

# ---------------------------------------------------------------------------
# Classes (the B parameter, and the packed high byte of attribute 8/9).
# ---------------------------------------------------------------------------
CLASSES = {
    0: "弓箭手",
    1: "神器",
    2: "贸易船",
    3: "建筑",
    4: "平民",
    5: "海鱼",
    6: "步兵",
    7: "浆果丛",
    8: "石矿",
    9: "猎物",
    10: "猛兽",
    11: "杂项",
    12: "骑兵",
    13: "攻城武器",
    14: "地形",
    15: "树木",
    16: "树桩",
    17: "治疗者",
    18: "僧侣",
    19: "贸易车",
    20: "运输船",
    21: "渔船",
    22: "战舰",
    23: "征服者",
    24: "战象",
    25: "英雄",
    26: "象射手",
    27: "城墙",
    28: "方阵兵",
    29: "家畜",
    30: "旗帜",
    31: "深海鱼",
    32: "金矿",
    33: "浅滩鱼",
    34: "悬崖",
    35: "爆破兵",
    36: "骑射手",
    37: "分身",
    38: "鸟类",
    39: "城门",
    40: "残骸",
    41: "资源堆",
    42: "圣物",
    43: "持圣物的僧侣",
    44: "火枪手",
    45: "双手剑士",
    46: "长枪兵",
    47: "侦察兵",
    48: "矿场",
    49: "农田",
    50: "长矛兵",
    51: "打包单位",
    52: "塔",
    53: "接舷船",
    54: "展开的攻城器",
    55: "弩炮",
    56: "劫掠者",
    57: "骑兵劫掠者",
    58: "牲畜",
    59: "国王",
    60: "其他建筑",
    61: "受控动物",
}

# ---------------------------------------------------------------------------
# Command types.  Built by composing a scope prefix with a base verb phrase so
# the 7 scopes x 3 attribute families cannot drift apart.
# ---------------------------------------------------------------------------
TYPE_BASES = {
    "Attribute Modifier (Set)": "设置属性",
    "Resource Modifier (Set/+/-)": "设置/增减资源",
    "Enable/Disable Unit": "启用/禁用单位",
    "Upgrade Unit": "升级单位",
    "Attribute Modifier (+/-)": "增减属性",
    "Attribute Modifier (Multiply)": "乘算属性",
    "Resource Modifier (Multiply)": "乘算资源",
    "Spawn Unit": "生成单位",
    "Modify Tech": "修改科技",
    "Tech Cost Modifier (Set/+/-)": "修改科技成本",
    "Disable Tech": "禁用科技",
    "Tech Time Modifier (Set/+/-)": "修改科技研究时间",
    "Transform Selected Unit": "转化选中单位",
}

SCOPE_PREFIX = {
    "": "",
    "Team ": "队伍：",
    "Enemy ": "敌方：",
    "Neutral ": "中立：",
    "Gaia ": "盖亚：",
    "Own Master Objects ": "主人单位：",
    "Selected Unit ": "选中单位：",
}


def zh_types(types):
    """Compose a Chinese name for every type the English table names."""
    out = {}
    for key, entry in types.items():
        raw_label = (entry or {}).get("label") if isinstance(entry, dict) else entry
        if not raw_label:
            continue
        for prefix, zh_prefix in SCOPE_PREFIX.items():
            if prefix and raw_label.startswith(prefix):
                base = raw_label[len(prefix):]
                if base in TYPE_BASES:
                    out[key] = zh_prefix + TYPE_BASES[base]
                break
        else:
            if raw_label in TYPE_BASES:
                out[key] = TYPE_BASES[raw_label]
    # the three scoped families that AGE writes without a matching base
    for key, zh in (("206", "转化选中单位"),):
        out.setdefault(key, zh)
    return out


def main():
    types = json.load(open(os.path.join(HERE, "effect_command_types.json"),
                           encoding="utf-8"))["types"]
    attrs = json.load(open(os.path.join(HERE, "effect_attributes.json"),
                          encoding="utf-8"))["attributes"]
    classes = json.load(open(os.path.join(HERE, "armor_classes.json"),
                             encoding="utf-8"))["classes"]

    # Refuse to ship a translation for an id the engine does not have: that
    # means the English table moved and this file is now describing a ghost.
    for label, table, ours in (("attribute", attrs, ATTRIBUTES),
                               ("class", classes, CLASSES)):
        ghosts = sorted(str(k) for k in ours if str(k) not in table)
        if ghosts:
            raise SystemExit("FATAL: %s ids translated but absent from the "
                             "engine table: %s" % (label, ghosts))

    zh_types_map = zh_types(types)
    doc = {
        "source": "human translation of AGE's own vocabulary",
        "note": "ids absent here fall back to AGE's English label; ids absent "
                "from the English tables are not translated at all and must "
                "render as a bare number ('Class 251', 'attribute 158').  "
                "Deliberately partial: guessing a name for a DE-only id would "
                "be worse than showing a number.",
        "attributes": {k: v for k, v in sorted(ATTRIBUTES.items())},
        "classes": {k: v for k, v in sorted(CLASSES.items())},
        "types": zh_types_map,
    }
    out = os.path.join(HERE, "effect_labels_zh.json")
    with open(out, "w", newline="\n") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
        fh.write("\n")

    missing_attr = sorted(set(attrs) - set(str(k) for k in ATTRIBUTES), key=int)
    missing_cls = sorted(set(classes) - set(str(k) for k in CLASSES), key=int)
    print("wrote %s (%d B)" % (os.path.basename(out), os.path.getsize(out)))
    print("  attributes %d of %d translated | untranslated %s"
          % (len(ATTRIBUTES), len(attrs), missing_attr))
    print("  classes    %d of %d translated | untranslated %s"
          % (len(CLASSES), len(classes), missing_cls))
    print("  types      %d of %d translated" % (len(zh_types_map), len(types)))
    untranslated_types = sorted((set(types) - set(zh_types_map)), key=int)
    print("  types untranslated %s" % untranslated_types)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
