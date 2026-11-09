# -*- coding: utf-8 -*-
"""What a technology field *means*, in Chinese, and which object its number points at.

WHY THIS FILE EXISTS
--------------------
`aoe2mod/dat/techfields.py` can point at all 34 fields of a technology and read
the value there.  That is the same offer AGE makes: 34 rows of
`ResearchLocations.0.ResearchTime` with a text box.  A player who wants 织布机 to
be researched at the 兵营 instead of the 城镇中心 has to know that
`ResearchLocations.0.LocationID` means "the building", and that 109 is a 城镇中心.

The unit editor got the first half of the answer (`fieldlabels.py`: labels,
groups, ranges).  This module is the second half, and it is the half AGE cannot
do at all: **every number that points at another object is named, and carried to
the page as a reference it can open.**  `EffectID: 22` becomes
`效果 22 · Loom`, `Civ: 1` becomes `不列颠`, `RequiredTechs.0: 104` becomes
`前置 · 黑暗时代`.  AGE prints the integer in all four cases and stops.

WHY A SEPARATE TABLE FROM `fieldlabels.py`
------------------------------------------
The two records share field names -- `Name`, `Type`, `IconID` -- and they mean
different things in each.  A unit's `Type` is the struct discriminator (70/80/90);
a technology's `Type` is 0 for any ordinary tech and 2 for an age-up.  Keying both
into one dict would silently give one of them the other's label, which is worse
than no label: a wrong Chinese name reads as authority.

RANGES ARE ADVICE, NOT A SANDBOX
--------------------------------
`lo`/`hi` are what the engine behaves sanely with, not the byte width.  The byte
width is checked separately and always (`server.set_tech_field`).  A research time
of 0 is legal and means "instant"; a negative one is a hang.
"""

from __future__ import annotations

# The order the panel shows.  A player opens a technology to change what it costs,
# how long it takes or which building researches it -- those three lead.  The
# string ids close, because almost nobody touches them and a wrong one points the
# tooltip at another technology's text.
GROUPS = [
    ("basic", "基础"),
    ("cost", "造价"),
    ("location", "研究地点与时间"),
    ("effect", "效果与前置"),
    ("text", "文本与图形"),
    ("misc", "其他字段"),
]

GROUP_ZH = dict(GROUPS)

# Resource ids as they appear in `ResourceCosts.N.Type`, proven against retail
# values rather than copied from a table: 织布机 is 50 gold and stores type 3;
# 射孔 (Murder Holes) is 200 food / 100 stone and stores (0, 200) (2, 100);
# 采石技术 (Stone Cutting) is 200 wood / 50 stone and stores (1, 200) (2, 50).
# The three agree on 0 食物 / 1 木材 / 2 石头 / 3 黄金 in a way a mis-numbered
# table could not.
#
# WHAT IS DELIBERATELY ABSENT: ids 7 and 506/508/513 do occur (7 on the relic
# bonus techs, 506 on the Satrapy branch picks, 508 on Fortified Outpost, 513 on
# the Emplacements).  None of the four appears in a cost a player would reason
# about as a resource -- they look like DE's newer "this is a pick, not a price"
# bookkeeping -- and I have no retail value to check a name against.  Naming them
# would be a guess wearing a Chinese label, so they fall through to `#7`.
RESOURCE_ZH = {
    -1: "（空位）",
    0: "食物",
    1: "木材",
    2: "石头",
    3: "黄金",
}

# `Tech.Type`.  0/2 are proven by the records themselves: every ordinary tech is 0
# and the three age-ups (Middle/Feudal/Imperial Age) are 2.  The 32/33 records
# are all DLC branch mechanics (Satrapy picks, Oligarchy/Democracy/Tyranny, the
# Trade N% wood ladder, Castle/TC Built) -- they are labelled by what they ARE,
# not by a meaning I would be inventing, and the hint says so.
TECH_TYPE_ZH = {
    0: "普通科技",
    2: "时代升级",
    32: "分支选择（资料片）",
    33: "分支触发（资料片）",
}

REQ_TYPE_ZH = {
    0: "不需要",
    1: "需要",
    2: "禁止",
}

FIELD_META = {
    # ---- 基础 -------------------------------------------------------------
    "Name": dict(zh="科技名", group="basic", ro=False,
                 hint="记录里存的字符串本身。游戏界面显示的是「名称文本编号」指向的文本，"
                      "改这里只改 .dat 里的名字，玩家在游戏里仍看到原来那句。"),
    "Name.len": dict(zh="科技名长度", group="basic", ro=True,
                     hint="字符串的长度前缀。改它会让后面的字节整体错位。"),
    "Name.marker": dict(zh="名字分隔标记", group="basic", ro=True,
                        hint="字符串写入时用的占位标记，写回时要一起改。"),
    "Civ": dict(zh="限定文明", group="basic", enum=None,
                hint="−1 是通用科技（每个文明都能研究）；其他数字是文明下标，"
                     "0 是 Gaia，1 是不列颠。"),
    "FullTechMode": dict(zh="全科技模式", group="basic",
                         hint="这一列在零售数据里 1227 条是 0、243 条是 1，另有少量"
                              "零散取值（−13、13、−3…）。它控制「全科技模式」下这条科技"
                              "怎么算，具体每一位的含义没有可验证的资料，所以这里不给选单，"
                              "只给数字输入。"),
    "Type": dict(zh="科技类别", group="basic", enum=TECH_TYPE_ZH,
                 hint="0 是普通科技，2 是时代升级。32/33 只出现在资料片的分支机制里。"),
    "Repeatable": dict(zh="可重复研究", group="misc", enum={0: "否", 1: "是"},
                       hint="同一条科技能不能研究第二次。关闭后按钮研究一次就消失。"),
    "IconID": dict(zh="图标编号", group="text", lo=-1, hi=32767,
                   hint="研究按钮上的图标，取自科技的图标表。−1 表示没设。"),

    # ---- 造价 -------------------------------------------------------------
    "ResourceCosts.0.Type": dict(zh="第 1 项造价资源", group="cost", enum=RESOURCE_ZH,
                                 lo=-1, hi=255,
                                 hint="指向资源表：0 食物 1 木材 2 石头 3 黄金，−1 是空位。"
                                      "顺序是资源表的顺序，不是「金在石前」的直觉顺序。"),
    "ResourceCosts.0.Amount": dict(zh="第 1 项造价数量", group="cost", lo=0, hi=32767,
                                   hint="这一项资源要花多少。填 0 仍是「列出但不花」。"),
    "ResourceCosts.1.Type": dict(zh="第 2 项造价资源", group="cost", enum=RESOURCE_ZH,
                                 lo=-1, hi=255),
    "ResourceCosts.1.Amount": dict(zh="第 2 项造价数量", group="cost", lo=0, hi=32767),
    "ResourceCosts.2.Type": dict(zh="第 3 项造价资源", group="cost", enum=RESOURCE_ZH,
                                 lo=-1, hi=255),
    "ResourceCosts.2.Amount": dict(zh="第 3 项造价数量", group="cost", lo=0, hi=32767),
    "ResourceCosts.0.Flag": dict(zh="第 1 项造价标记", group="cost", lo=0, hi=255,
                                 hint="零售数据里几乎全是 1。0 的含义没有可验证的资料。"),
    "ResourceCosts.1.Flag": dict(zh="第 2 项造价标记", group="cost", lo=0, hi=255),
    "ResourceCosts.2.Flag": dict(zh="第 3 项造价标记", group="cost", lo=0, hi=255),

    # ---- 研究地点与时间 ---------------------------------------------------
    "ResearchLocationCount": dict(zh="研究地点数量", group="location", ro=True,
                                  hint="后面 ResearchLocations 数组的长度。改它会改变整条"
                                       "记录的长度，必须和数组一起改。"),
    "ResearchLocations.0.LocationID": dict(zh="研究建筑", group="location",
                                           lo=-1, hi=32767,
                                           hint="在哪栋建筑（或单位）里研究这条科技。"
                                                "−1 表示没有地点，只能靠触发器或效果给出。"),
    "ResearchLocations.0.ResearchTime": dict(zh="研究时间（秒）", group="location",
                                             lo=0, hi=32767,
                                             hint="在这个地点研究要多少秒。同一科技的多个"
                                                  "地点各有自己的一份时间，只改一处会不一致。"),
    "ResearchLocations.0.ButtonID": dict(zh="按钮位置", group="location", lo=0, hi=255,
                                         hint="在这栋建筑的按钮网格里排第几格。"),
    "ResearchLocations.0.HotKeyID": dict(zh="热键编号", group="location", lo=-1,
                                         hi=32767),

    # ---- 效果与前置 -------------------------------------------------------
    "EffectID": dict(zh="挂的效果", group="effect", lo=-1, hi=32767,
                     hint="研究完成后执行哪一组效果（改血量、改攻击、解锁单位…）。"
                          "改这里等于换掉整条科技的作用。"),
    "RequiredTechCount": dict(zh="前置科技数量", group="effect", ro=True,
                              hint="前置数组里前几项算数。改它会让多余的项被读成下一条字段。"),
    "RequiredTechs.0": dict(zh="前置科技 1", group="effect", lo=-1, hi=32767,
                            hint="研究这条科技之前必须先研究的科技。−1 是空位。"),
    "RequiredTechs.1": dict(zh="前置科技 2", group="effect", lo=-1, hi=32767),
    "RequiredTechs.2": dict(zh="前置科技 3", group="effect", lo=-1, hi=32767),
    "RequiredTechs.3": dict(zh="前置科技 4", group="effect", lo=-1, hi=32767),
    "RequiredTechs.4": dict(zh="前置科技 5", group="effect", lo=-1, hi=32767),
    "RequiredTechs.5": dict(zh="前置科技 6", group="effect", lo=-1, hi=32767),

    # ---- 文本与图形 -------------------------------------------------------
    "LanguageDLLName": dict(zh="名称文本编号", group="text", ro=True,
                            hint="指向界面文本表里这条科技的名字。改它不会改名字，只会指错。"),
    "LanguageDLLDescription": dict(zh="说明文本编号", group="text", ro=True,
                                   hint="指向研究按钮下面的说明文字。"),
    "LanguageDLLHelp": dict(zh="帮助文本编号", group="text", ro=True,
                            hint="指向鼠标悬停时的长说明。"),
    "LanguageDLLTechTree": dict(zh="科技树文本编号", group="text", ro=True,
                                hint="指向科技树面板里那一格显示的文字。"),

    # ---- 其他 -------------------------------------------------------------
    "HotKeyID": dict(zh="热键编号", group="misc", lo=-1, hi=32767),
}


def meta_for(name):
    """`meta_for("ResearchLocations.1.ResearchTime")` -> the `.0` sibling's meta.

    A list member carries the same meaning as its first sibling, so one entry
    labels `ResearchLocations.0..2` and `ResourceCosts.0..2`.  The index is added
    to the label so two rows never read the same ("研究时间" three times tells the
    player nothing about which one they are editing).

    Falls back to `{}`, which the page reads as "no Chinese label" and shows the
    raw field name with no bounds -- the honest answer for anything not listed.
    """
    m = FIELD_META.get(name)
    if m:
        return m
    parts = name.split(".")
    for i in range(len(parts) - 1, 0, -1):
        if parts[i].isdigit():
            probe = parts[:]
            probe[i] = "0"
            m = FIELD_META.get(".".join(probe))
            if m:
                out = dict(m)
                out["zh"] = "%s（第 %s 项）" % (m["zh"], int(parts[i]) + 1)
                return out
    return {}


def group_of(name):
    return meta_for(name).get("group", "misc")


def label_of(name):
    """Chinese label, or the technical name when nothing is known."""
    return meta_for(name).get("zh") or name


def value_name(name, v):
    """`value_name("Civ", 1)` -> "不列颠".  Unknown / unmapped -> None.

    Only the enumerations above are answered.  Everything else returns None so
    the caller prints the integer -- a lookup miss must not look like a name.
    """
    meta = FIELD_META.get(name) or meta_for(name)
    enum = meta.get("enum")
    if not enum:
        return None
    return enum.get(v)


def order_key(name):
    """Sort key that keeps list members next to each other."""
    parts = name.split(".")
    return ".".join("0" if p.isdigit() else p for p in parts), name
