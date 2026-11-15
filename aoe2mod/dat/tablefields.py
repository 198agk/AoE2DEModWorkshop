# -*- coding: utf-8 -*-
"""Named, addressed fields for the .dat tables that are NOT units or techs.

WHY THIS EXISTS
---------------
`unitfields` and `techfields` make two record families addressable, which is why
the editor can show 434 fields of a unit and 34 of a technology.  Everything else
in the file had no address, so 20,883 graphics records and 930 sounds records --
Graphics and Sounds in AGE3's own tree -- could not be opened at all.  Measured
2026-11-02: `AGE3-全量数据/schema/schema.json` has 620 fields across 43 structs;
this product covered 190 + 34 of them.

WHY IT WALKS INSTEAD OF COPYING THE PARSER
------------------------------------------
`unitfields` re-states `parser.read_unit` line for line, because a unit record has
434 fields and a single wrong width corrupts every later one.  A graphic record is
different: the interesting numbers all sit at a FIXED offset from the record
start (the three length-prefixed strings are the only variable part, and they
come first), so the addresses can be derived from the record start plus a table
of offsets.  That is less code and it cannot drift from a read order, because it
does not have one.

THE PROOF IT IS FAITHFUL
------------------------
`scan()` walks the same stage boundaries `Parser.parse()` records
(`stage_offsets`), so the records it returns are the records the engine reads.
Every record is sliced by the NEXT record's start, which means a wrong width
shows up as a non-zero `leftover` at the end of the table instead of as
plausible-looking wrong offsets.

WHAT IT DOES NOT DO
-------------------
Strings.  `name`/`file`/`particle_effect` carry a 2-byte length prefix, so a
fixed-width write is meaningless (shortening leaves stale bytes, lengthening
overwrites `slp`).  They are REPORTED -- a player needs to see which .slp a
record points at -- and refused for writing, in one sentence, by `plan()`.
"""
from __future__ import annotations

import contextlib
import io
import struct

from . import parser as P

__all__ = ["TABLES", "scan", "record_name", "fields_at", "plan", "apply",
           "KINDS", "meta_for", "TABLE_ZH", "CIV_META"]

#: Scalar shapes these records use.
KINDS = {"u8": 1, "u16": 2, "i16": 2, "i32": 4, "u32": 4, "f32": 4}

FMT = {"u8": "<B", "u16": "<H", "i16": "<h", "i32": "<i", "u32": "<I",
       "f32": "<f"}
WIDTH = {"u8": (0, 255), "u16": (0, 65535), "i16": (-32768, 32767),
         "i32": (-2147483648, 2147483647), "u32": (0, 4294967295),
         "f32": (-3.4e38, 3.4e38)}

#: The parser stage each table lives in, and the key `Parser.parse` stores its
#: count under.  A table that is not listed here has no address, and
#: `plan()` refuses rather than guessing.
TABLES = {
    "graphic": {"stage": "3 Graphics", "count": "graphic_count",
                "list": "graphics", "zh": "图形"},
    "sound": {"stage": "2 Sounds", "count": "sound_count",
              "list": "sounds", "zh": "音效"},
    # Effects are reachable from the technology editor, but only through a
    # technology: measured 2026-11-03, 1,500 effect records hold 10,500
    # commands and only 8,005 of them sit behind a tech that points at them.
    # The other 487 records (2,795 numbers) point at nothing, so no screen could
    # reach them at all.  This table makes every record addressable on its own.
    "effect": {"stage": "5 Effects", "count": "effect_count",
               "list": "effects", "zh": "效果"},
    # The three below are the 15,816 numbers that existed in the file and had
    # no screen at all (measured 2026-11-03 against AGE3's 13 tabs: we had 5).
    # They cost no new parser -- `Parser.parse` already reads all of them by
    # name -- so the only thing missing was an address per record.
    "terrain": {"stage": "4 TerrainBlock+RandomMaps", "count": "terrains_used2",
                "list": "terrains", "zh": "地形"},
    "restriction": {"stage": "1 FileVersion+TerrainRestr+Colours",
                    "count": "terrain_restriction_count",
                    "list": "terrain_restrictions", "zh": "地形通行表"},
    "colour": {"stage": "1 FileVersion+TerrainRestr+Colours",
               "count": "player_colour_count",
               "list": "player_colours", "zh": "玩家颜色"},
    # UnitHeaders: 1,701 headers holding 2,329 tasks, each task 32 fields.  This
    # is the last record family with no address.  A task is where a unit's JOB is
    # defined -- gather, build, heal, attack -- so this is the only screen from
    # which "what can this unit do, and to what" is anything but a number hunt.
    # AGE3 reaches it as structs UnitHeader (2) + Task (32) = 34 of its 620
    # fields; measured 2026-11-03 this file holds 2,329 x 29 writable numbers.
    "task": {"stage": "7 UnitHeaders", "count": "unit_header_count",
             "list": "unit_headers", "zh": "单位任务"},
    # Civs: 63 records, each six scalars, 601 floats and a pointer array to its
    # units.  This is the last family with no screen, and the only one whose
    # cost had to be designed away rather than paid: walking the block costs
    # 9.15 s because it contains all 136,861 unit records.  Measured 2026-11-04,
    # each record's START is the byte after the previous civ's last unit end,
    # and that end is already in the unit index the editor builds anyway --
    # 62/62 computed starts agree with an honest walk.  So this table costs
    # 0.0006 s once the unit tab has been opened, and says so on screen.
    "civ": {"stage": "7 UnitHeaders", "count": "civ_count",
            "list": "civs", "zh": "文明"},
    # The three below are not record families: they are the structures that sit
    # BETWEEN the record families, and until now not one of their numbers had an
    # address on any screen.  AGE3 shows them under TerrainBlock (General tab)
    # and TechTrees, which is why they are the last three of its thirteen tabs
    # this tool could not reach.
    #
    # "map" is the 25 scalars that follow the 200 terrain records -- the tile
    # grid the game uses to convert between map cells and screen pixels.
    # Measured 2026-11-12: 63 bytes at 3588524, all 25 values named.
    "map": {"stage": "4 TerrainBlock+RandomMaps", "count": "terrains_used2",
            "list": "terrains", "zh": "地图块"},
    # "tail" is the seven i32 counters between the last technology and the tech
    # tree (DatFile.h calls them History totals).  Measured: stage 10 begins at
    # 93206865 and the seven values are 30/7/14/700/1400/5/10.
    "tail": {"stage": "10 Tail+TechTree", "count": "time_slice",
             "list": "tech_tree", "zh": "全局数值"},
    # "techtree" is 550 connection lines -- 4 ages, 37 buildings, 269 units,
    # 240 researches -- and every line carries an 84-byte Common block the game
    # reads to lay out the tech tree.  This is the one table AGE3 gives four
    # tabs to (TechTrees: Ages / Buildings / Units / Research).
    "techtree": {"stage": "10 Tail+TechTree", "count": "total_unit_tech_groups",
                 "list": "tech_tree", "zh": "科技树连线"},
}

#: Every scalar of a graphic record, as (name, kind, offset-from-somewhere).
#: `_after_strings` entries are measured from the byte AFTER the third string,
#: because the three strings are length-prefixed and variable; everything else
#: in a graphic record is fixed-width, so one base offset names them all.
#:
#: Measured against the shipped file (2026-11-02): the first record at 286465
#: has three empty strings (6 bytes of prefixes) and is 62 bytes long, which is
#: what `_GRAPHIC_TAIL` expects.
_GRAPHIC_TAIL = (
    ("SlpID", "i32", 0),
    ("IsLoaded", "u8", 4),
    ("OldColorFlag", "u8", 5),
    ("Layer", "u8", 6),
    ("PlayerColor", "i16", 7),
    ("TransparentSelection", "u8", 9),
    ("Coordinates.0", "i16", 10),
    ("Coordinates.1", "i16", 12),
    ("Coordinates.2", "i16", 14),
    ("Coordinates.3", "i16", 16),
    # DeltaCount comes next and is NOT settable: it says how many 16-byte deltas
    # follow, so changing it moves every later field.  It is reported so the
    # record count adds up on screen.
    ("DeltaCount", "i16", 18),
    ("SoundID", "i16", 20),
    ("WwiseSoundID", "u32", 22),
    ("AngleSoundsUsed", "u8", 26),
    ("FrameCount", "i16", 27),
    ("AngleCount", "i16", 29),
    ("SpeedMultiplier", "f32", 31),
    ("FrameDuration", "f32", 35),
    ("ReplayDelay", "f32", 39),
    ("SequenceType", "u8", 43),
    ("ID", "i16", 44),
    ("MirroringMode", "u8", 46),
    ("EditorFlag", "u8", 47),
)

#: Width of the fixed-width block that follows the three strings: 48 bytes,
#: ending with `EditorFlag` at byte 47.  Derived from the table rather than typed
#: twice, and asserted below so a new field cannot silently overrun it.
_GRAPHIC_SCALARS = max(off + KINDS[kind] for _n, kind, off in _GRAPHIC_TAIL)
assert _GRAPHIC_SCALARS == 48, _GRAPHIC_SCALARS

#: What each graphic field means, in words a player can act on, plus the sane
#: range.  A name is not enough: `SlpID` is "which .slp file this record draws",
#: and `Layer` decides whether the sprite sits under or over the terrain.
GRAPHIC_META = {
    "SlpID": dict(zh="图形文件编号", lo=-1, hi=2147483647,
                  hint="这条记录画的是哪一个 .slp 动画文件。-1 表示不画。"
                       "把它指向另一个编号就能让一个单位用另一个单位的图。"),
    "IsLoaded": dict(zh="载入", lo=0, hi=1,
                     hint="1 = 启动时就加载这个图形；0 = 用到才加载。"),
    "OldColorFlag": dict(zh="旧调色板", lo=0, hi=1,
                         hint="1 = 用老版本的调色方式上色。"),
    "Layer": dict(zh="图层", lo=0, hi=255,
                  hint="画在谁上面：0 普通、1 地面、2 阴影、3 单位上方。"
                       "同一条记录画两次就是因为图层不同。"),
    "PlayerColor": dict(zh="玩家颜色", lo=0, hi=100,
                        hint="多少个像素用玩家颜色（0 = 完全不用，"
                             "100 = 整个图形都用队伍色）。"),
    "TransparentSelection": dict(zh="选中透视", lo=0, hi=1,
                                 hint="1 = 被遮挡时也能看到轮廓。"),
    "Coordinates.0": dict(zh="偏移 X", lo=-32768, hi=32767,
                          hint="图形相对锚点左右挪多少像素。正数往右，负数往左。"),
    "Coordinates.1": dict(zh="偏移 Y", lo=-32768, hi=32767,
                          hint="图形相对锚点上下挪多少像素。正数往下，负数往上。"),
    "Coordinates.2": dict(zh="偏移 Z", lo=-32768, hi=32767,
                          hint="图形离地多高，用来把飞行单位、旗帜之类抬到空中。"),
    "Coordinates.3": dict(zh="锚点", lo=-32768, hi=32767,
                          hint="单位站在图形上的哪个像素，决定它看起来"\
                               "贴不贴地。"),
    "DeltaCount": dict(zh="帧偏移条数", ro=True,
                       hint="后面跟多少条 16 字节的帧偏移。改它会让整条记录读不下去。"),
    "SoundID": dict(zh="音效编号", lo=-1, hi=32767,
                    hint="播放这个图形时用的音效（指向「音效」表）。-1 = 没声音。"),
    "WwiseSoundID": dict(zh="Wwise 音效编号", lo=0, hi=4294967295,
                         hint="决定版新增的音频事件编号。0 = 不用。"),
    "AngleSoundsUsed": dict(zh="带方向音效", lo=0, hi=1,
                            hint="1 = 按角度播不同音效（那一串 24 字节×N 会跟在后面）。"),
    "FrameCount": dict(zh="帧数", lo=0, hi=32767,
                       hint="这个动画有几帧。改小了画面会提前结束。"),
    "AngleCount": dict(zh="方向数", lo=0, hi=32767,
                       hint="这个动画有几个朝向（一般 8 或 16）。"),
    "SpeedMultiplier": dict(zh="播放速度倍数", lo=0.0, hi=100.0,
                            hint="动画快慢。1 = 正常，0.5 = 慢一半。"),
    "FrameDuration": dict(zh="每帧时长", lo=0.0, hi=100.0,
                          hint="一帧停多久（秒）。越大越慢。"),
    "ReplayDelay": dict(zh="循环间隔", lo=0.0, hi=100.0,
                        hint="循环播放时两轮之间停多久。"),
    "SequenceType": dict(zh="播放方式", lo=0, hi=255,
                         hint="0 = 循环，1 = 播一次就停。"),
    "ID": dict(zh="图形编号", ro=True,
               hint="这条记录在图形表里的位置。单位记录靠它找到这张图，"
                    "改它等于把两个单位的图对调。"),
    "MirroringMode": dict(zh="镜像方式", lo=0, hi=8,
                          hint="向左走时怎么翻图：0 不翻，1/2 水平翻，3 用单独的镜像帧。"),
    "EditorFlag": dict(zh="编辑器标记", lo=0, hi=255,
                        hint="只给地图编辑器看的分类标记，游戏运行时不用它。保持原值即可。"),
    # 图形记录最前面是三个带长度前缀的字符串。名字必须在这里登记，否则字段表
    # 会把内部英文名直接倒给玩家。三条都只读：改了长度会挤掉后面的字段。
    "Name": dict(zh="图形名字", ro=True,
                 hint="这条图形自己的名字（例如 Barracks ORIE Age3）。字符串，只读。"),
    "FileName": dict(zh="源文件名", ro=True,
                     hint="生成这条图形时用的 .slp 文件名。多数记录这里是空的，只读。"),
    "ParticleEffect": dict(zh="粒子特效名", ro=True,
                           hint="挂在这条图形上的粒子特效名。大多数记录是空的，只读。"),
}

SOUND_META = {
    "ID": dict(zh="音效编号", ro=True,
               hint="这条记录在音效表里的位置，单位/图形记录靠它找到这段声音。"),
    "PlayDelay": dict(zh="延迟", lo=-32768, hi=32767,
                      hint="触发后等多久才响（毫秒）。"),
    "CacheTime": dict(zh="缓存时长", lo=0, hi=2147483647,
                      hint="这段声音在内存里留多久（毫秒）。"),
    "TotalProbability": dict(zh="总概率", lo=0, hi=100,
                             hint="下面几条文件概率加起来应该等于它。"),
    "FileCount": dict(zh="文件条数", ro=True,
                      hint="这段音效由几个文件组成。改它会改变后面每一条的读法。"),
}

#: Effect records are a LIST of 11-byte commands, so one record's fields are
#: named `#3.d` (record 3, the number) rather than by a fixed field name.  The
#: four slots are the game's own `(type, a, b, c, d)` tuple; only `d` is a plain
#: number a player can reason about, and the other three decide what `d` MEANS
#: (which unit, class or attribute) -- which is exactly why AGE prints them as
#: `4 -1 4 0 15.0` and expects you to know the code.
_SLOT_META = {
    "type": dict(zh="命令类型", ro=True, lo=0, hi=255,
                 hint="决定这条命令是「改属性」还是「改资源」。改错类型，同一个数字"
                      "会变成完全不同的效果，所以这里只读：要另一种效果就到科技那边"
                      "新建一条命令。"),
    "a": dict(zh="参数1（单位或资源）", ro=True, lo=-32768, hi=32767,
              hint="多数命令里这是目标单位编号；资源类命令里这是资源编号。"
                   "-1 表示不指定。改它等于把这条效果挪到另一个目标上，"
                   "所以只读。"),
    "b": dict(zh="参数2（类别）", ro=True, lo=-32768, hi=32767,
              hint="多数命令里这是目标类别编号（步兵/骑兵…）。-1 表示不指定。"),
    "c": dict(zh="参数3（属性）", ro=True, lo=-32768, hi=32767,
              hint="改属性时这是属性编号（0 生命值、8/9 护甲…）；资源类命令里"
                   "这是「乘以哪项资源」。换一个编号就等于换一种效果，所以只读。"),
    "d": dict(zh="数值", lo=-3.4e38, hi=3.4e38,
              hint="这条命令真正写下去的那个数。护甲/攻击类命令的值被压进一个"
                   "字节（0..255），高位存的是类别。"),
}

EFFECT_META = {
    "Name": dict(zh="名字", ro=True,
                 hint="效果记录自己的名字，游戏用它做说明；改它要改字符串长度，"
                      "会挤到后面的记录。"),
    "CommandCount": dict(zh="命令条数", ro=True,
                         hint="这条记录下面有几条命令。改它会把后面每条命令的"
                              "位置都挪掉。"),
}

#: `Task` is the last addressless record family.  A unit does not "have"
#: behaviour -- it has a LIST of tasks, and each task says: for this action
#: (gather / build / heal / attack), on this target (a unit id, a class, a
#: resource, a terrain), do this much work within this range.  The order is not
#: decoration: `parser.read_task` and AGE3's `src/dat/UnitCommand.cpp` agree field
#: for field, and the measured width is 69 bytes for all 2,329 tasks in the
#: shipped file (leftover 0), which is the proof no field is mis-sized.
#:
#: Offsets are FIXED inside a task -- there is no variable part -- so unlike a
#: graphic record these can be read straight off the table below.  The two
#: conditionals (`Wwise*` from GV_C4, `Enabled` from GV_C28) depend only on the
#: file version, never on the task, so `task_slots(gv)` resolves them once.
TASK_SLOTS = (
    ("TaskType", "i16", 0),
    ("ID", "i16", 2),
    ("IsDefault", "u8", 4),
    ("ActionType", "i16", 5),
    ("ClassID", "i16", 7),
    ("UnitID", "i16", 9),
    ("TerrainID", "i16", 11),
    ("ResourceIn", "i16", 13),
    ("ResourceMultiplier", "i16", 15),
    ("ResourceOut", "i16", 17),
    ("UnusedResource", "i16", 19),
    ("WorkValue1", "f32", 21),
    ("WorkValue2", "f32", 25),
    ("WorkRange", "f32", 29),
    ("AutoSearchTargets", "u8", 33),
    ("SearchWaitTime", "f32", 34),
    ("EnableTargeting", "u8", 38),
    ("CombatLevelFlag", "u8", 39),
    ("GatherType", "i16", 40),
    ("WorkFlag2", "i16", 42),
    ("TargetDiplomacy", "u8", 44),
    ("CarryCheck", "u8", 45),
    ("PickForConstruction", "u8", 46),
    ("MovingGraphicID", "i16", 47),
    ("ProceedingGraphicID", "i16", 49),
    ("WorkingGraphicID", "i16", 51),
    ("CarryingGraphicID", "i16", 53),
    ("ResourceGatheringSoundID", "i16", 55),
    ("ResourceDepositSoundID", "i16", 57),
    ("WwiseResourceGatheringSoundID", "u32", 59),
    ("WwiseResourceDepositSoundID", "u32", 63),
    ("Enabled", "i16", 67),
)

#: A task is 69 bytes wide on EVERY shipped file version this product opens,
#: because the two conditional fields are the only variable part and they are
#: always present for DE.  Asserted at import so a future format bump fails
#: loudly here instead of writing into a neighbour's bytes.
TASK_BYTES = 69
assert max(off + KINDS[kind] for _n, kind, off in TASK_SLOTS) == TASK_BYTES, (
    "TASK_SLOTS no longer sums to %d bytes; the table below has drifted from "
    "parser.read_task and every write would land in the neighbouring task"
    % (TASK_BYTES,))


def task_slots(gv):
    """The fields a task carries for this file version, as (name, kind, offset).

    `Wwise*` appears from GV_C4 and `Enabled` from GV_C28 (UnitCommand.cpp:76/81).
    Both are true for every DE file, so `TASK_BYTES` is 69 either way -- but the
    walk asks this function rather than assuming, so an old file reads its own
    shape instead of four bytes of the next task.
    """
    g = 54 if gv is None else gv
    out = []
    for name, kind, off in TASK_SLOTS:
        if name in ("WwiseResourceGatheringSoundID",
                    "WwiseResourceDepositSoundID") and not (P.GV_C4 <= g
                                                            <= P.GV_LatestDE2):
            continue
        if name == "Enabled" and g < P.GV_C28:
            continue
        out.append((name, kind, off))
    return out


#: One task's worth of Chinese, written as what the number DOES in game terms.
#: The honesty rule from the rest of this file applies: a field whose real
#: meaning nobody verified says so, instead of inventing a label that reads
#: authoritative.
TASK_META = {
    "TaskType": dict(zh="任务类型", ro=True,
                     hint="引擎用它区分「这一条是任务」还是「这一条是别的表」。"
                          "零售文件里 2,329 条全是 1，改它等于让引擎读错这张表。"),
    "ID": dict(zh="第几格", ro=True,
               hint="这条任务在单位的命令卡上是第几格。要挪格子请用"
                    "「把单位放在某座建筑的第几格」那句，它会同时改这里和单位记录，"
                    "只改这里游戏会认不出来。"),
    "IsDefault": dict(zh="默认选中", ro=True, lo=0, hi=1,
                      hint="0 = 这一格不是玩家右键时的默认动作。零售文件里"
                           "2,329 条全是 0，改它会让右键行为变掉而又没有任何画面"
                           "能验证，所以只读。"),
    "ActionType": dict(zh="动作", lo=0, hi=32767,
                       hint="这条任务是什么动作：3 = 走到某处、7 = 攻击、"
                            "110 = 采集/放置、122 = 治疗、109 = 交付、13 = 建。"
                            "最常改的一条 —— 把一个单位的某个动作换成另一个。"),
    "ClassID": dict(zh="目标类别", lo=-1, hi=32767,
                    hint="这条任务对哪一类目标有效（-1 = 不限）。改它能把"
                         "「对野猪」变成「对所有猎物」。"),
    "UnitID": dict(zh="目标单位", lo=-1, hi=32767,
                   hint="这条任务对哪一个单位有效（-1 = 不限）。"
                        "村民那 11 条采集任务就是靠这里指向 1 棵果树、89 只鹿、"
                        "812 头野猪……"),
    "TerrainID": dict(zh="限定地形", lo=-1, hi=32767,
                      hint="只在这种地形上有效（-1 = 任何地形）。"),
    "ResourceIn": dict(zh="携带资源", lo=-1, hi=32767,
                       hint="执行时身上带着哪种资源（15 是一类标记值，不是资源号）。"
                            "-1 = 不看携带。"),
    "ResourceMultiplier": dict(zh="资源倍率", lo=-1, hi=32767,
                               hint="同一类资源下的细分乘数，-1 = 不用。"),
    "ResourceOut": dict(zh="产出资源", lo=-1, hi=32767,
                        hint="这条任务结束时给出哪种资源（0..3 = 食物/木材/石头/黄金）。"
                             "-1 = 不产出。"),
    "UnusedResource": dict(zh="未用资源槽", lo=-1, hi=32767,
                           hint="引擎保留了位置但没用到的字段。-1 = 空。"),
    "WorkValue1": dict(zh="工作量 1", lo=-3.4e38, hi=3.4e38,
                       hint="这条任务的工作量/倍率。注意：它**不是**采集速度 —— "
                            "村民各条采集任务这里都是 1.0，而游戏里每种资源的采集"
                            "速度是引擎写死的，不在这份文件里。"),
    "WorkValue2": dict(zh="工作量 2", lo=-3.4e38, hi=3.4e38,
                       hint="第二个工作量，多数任务是 0。"),
    "WorkRange": dict(zh="工作范围", lo=-3.4e38, hi=3.4e38,
                      hint="要走到多近才算到了。0.1 = 贴近，1.0 = 隔一格也能做。"
                           "这是最直观的一个：改大这个人就能隔空采集。"),
    "AutoSearchTargets": dict(zh="自动找目标", lo=0, hi=1,
                              hint="1 = 站着不动也会自己找附近的活干。"),
    "SearchWaitTime": dict(zh="寻找间隔", lo=-3.4e38, hi=3.4e38,
                           hint="多久找一次目标（秒）。3 = 每次找完等 3 秒。"),
    "EnableTargeting": dict(zh="自动选目标", lo=0, hi=1,
                            hint="1 = 攻击类任务自动挑打谁。"),
    "CombatLevelFlag": dict(zh="战斗等级标记", lo=0, hi=255,
                            hint="引擎用它在战斗动作之间取舍，具体语义没有权威文档，"
                                 "改之前先备份。"),
    "GatherType": dict(zh="采集类型", lo=0, hi=32767,
                       hint="0/1 两种采集大类，零售村民任务里两种都出现。"),
    "WorkFlag2": dict(zh="工作标记", lo=0, hi=32767,
                      hint="采集/建造的附加标记，零售文件里几乎全是 0。"),
    "TargetDiplomacy": dict(zh="对谁", lo=0, hi=255,
                            hint="0 任何人、1/3 自己那边、4 中立（猎物、树）。"
                                 "改错这一条会让村民去打自己的城镇中心。"),
    "CarryCheck": dict(zh="需要携带", lo=0, hi=1,
                       hint="1 = 只有身上带着东西时这条任务才成立（比如回仓库存)。"),
    "PickForConstruction": dict(zh="施工优先", lo=0, hi=1,
                                hint="1 = 建造时优先挑这条。"),
    "MovingGraphicID": dict(zh="移动图形", lo=-1, hi=32767,
                            hint="做这个动作时换用哪条图形记录（-1 = 用单位自己的）。"),
    "ProceedingGraphicID": dict(zh="行走图形", lo=-1, hi=32767,
                                hint="赶往目标的路上用哪条图形（-1 = 用单位自己的）。"),
    "WorkingGraphicID": dict(zh="工作图形", lo=-1, hi=32767,
                             hint="干活时用哪条图形（-1 = 用单位自己的）。"
                                  "村民砍树时会换成拿斧头的图，就是靠这里。"),
    "CarryingGraphicID": dict(zh="搬运图形", lo=-1, hi=32767,
                              hint="搬东西时用哪条图形（-1 = 用单位自己的）。"),
    "ResourceGatheringSoundID": dict(zh="采集音效", lo=-1, hi=32767,
                                     hint="采集时的音效（指向「音效」表）。-1 = 没声音。"),
    "ResourceDepositSoundID": dict(zh="存入音效", lo=-1, hi=32767,
                                   hint="把资源存进建筑时的音效。-1 = 没声音。"),
    "WwiseResourceGatheringSoundID": dict(zh="Wwise 采集音效", lo=0,
                                          hi=4294967295,
                                          hint="决定版新增的音频事件编号。0 = 不用。"),
    "WwiseResourceDepositSoundID": dict(zh="Wwise 存入音效", lo=0,
                                        hi=4294967295,
                                        hint="决定版新增的音频事件编号。0 = 不用。"),
    "Enabled": dict(zh="启用", lo=-1, hi=32767,
                    hint="零售文件里 2,329 条全是 -1（表示「跟随默认」）。"),
}

#: `ActionType` values that occur in the shipped file, in words.  Only the ones
#: with a name that is verifiable from the data itself are listed; a value not
#: listed still edits, it just shows as a bare number rather than a guess.
ACTION_ZH = {
    3: "走到某处",
    5: "攻击地面",
    6: "守卫",
    7: "攻击单位",
    10: "跟随",
    11: "巡逻",
    13: "建造/修理",
    105: "投放",
    107: "组装",
    109: "交付资源",
    110: "采集/放置",
    122: "治疗",
    151: "搬起",
}

#: Terrain was the biggest single hole: 200 records x 19 named fields, all of
#: them already read by `Parser.parse`, none of them reachable from a screen.
#: Names follow genieutils `src/dat/Terrain.cpp`, which is what AGE labels on.
TERRAIN_META = {
    "Enabled": dict(zh="启用", lo=0, hi=1,
                    hint="0 = 这个地形在游戏里不存在，画不出来也走不上去。"),
    "Random": dict(zh="随机绘图", lo=0, hi=1,
                   hint="1 = 每次地图生成时随机挑一个变体来画。"),
    "IsWater": dict(zh="水域类型", lo=0, hi=255,
                    hint="0 = 陆地；非 0 = 水，数字决定船只怎么走、"
                         "渔民能不能下水。"),
    "HideInEditor": dict(zh="编辑器里隐藏", lo=0, hi=1,
                         hint="1 = 地图编辑器不给玩家选这个地形。"),
    # The three strings come first in the record.  They are shown and refused
    # for writing (`kind == "str"`), and they need an entry here or the field
    # list has three rows labelled with their internal English names --
    # measured 2026-11-03 by a pin that required every row to have a Chinese
    # label.
    "Name": dict(zh="地形名字", ro=True,
                 hint="游戏里显示的名字，改短会留下残字、改长会覆盖下一个字段。"),
    "Name2": dict(zh="内部名字", ro=True,
                  hint="程序内部用的短名（例如 g_wtr），字符串，只读。"),
    "OverlayMaskName": dict(zh="叠加贴图", ro=True,
                            hint="叠在这个地形上的贴图文件名，字符串，只读。"),
    "StringID": dict(zh="名字编号", lo=-2147483648, hi=2147483647,
                     hint="指向语言文件里的显示名字。-1 = 没有名字。"),
    "Slp": dict(zh="图形文件编号", lo=-1, hi=2147483647,
                hint="这个地形用哪一个 .slp 来画。-1 = 不画。"),
    "ShapePtr": dict(zh="形状指针", ro=True,
                     hint="运行时的内存指针，存在文件里也没有意义。"),
    "SoundID": dict(zh="音效编号", lo=-1, hi=2147483647,
                    hint="走在这个地形上的脚步声（指向「音效」表）。"),
    "WwiseSoundID": dict(zh="Wwise 音效编号", lo=0, hi=4294967295,
                         hint="走在这个地形上的脚步声的 Wwise 事件编号。0 = 不用新版音频，"
                         "改走上面那条老音效。"),
    "WwiseSoundStopID": dict(zh="Wwise 停止编号", lo=0, hi=4294967295,
                             hint="离开这个地形时用来停掉上面那段声音。"),
    "BlendPriority": dict(zh="混合优先级", lo=-2147483648, hi=2147483647,
                          hint="两个地形接壤时谁盖住谁。数字大的先画。"),
    "BlendType": dict(zh="混合方式", lo=-2147483648, hi=2147483647,
                      hint="接壤处怎么过渡。0 = 硬边，越大越柔。"),
    "PassableTerrain": dict(zh="可通行", lo=0, hi=255,
                            hint="这个地形允许哪一类单位走上去。"
                                 "255 = 全部，0 = 谁都不能走。"),
    "ImpassableTerrain": dict(zh="不可通行", lo=0, hi=255,
                              hint="上面那一项的反面，两者按位组合。"),
    "IsAnimated": dict(zh="动画", lo=0, hi=1,
                       hint="1 = 会动（水面波纹、岩浆翻滚）。"),
    "Phantom": dict(zh="幻影", lo=-32768, hi=32767,
                    hint="只画出来但不参与碰撞。0 = 正常地形。"),
}

#: One restriction record is 134 floats of damage multiplier followed by 134
#: four-number pass graphics: 2,680 bytes, x54 records.  The multiplier says how
#: much damage a building takes while standing on terrain N, which is the number
#: behind "why did my castle melt on that hill".
RESTRICTION_META = {
    "Mult": dict(zh="伤害倍率", lo=0.0, hi=1000.0,
                 hint="站在这种地形上，建筑受到的伤害乘多少。"
                      "1 = 正常，0 = 完全免疫（岩浆上放城堡不会烧）。"
                      "列表顺序就是地形编号，第 N 项对应「地形」页签的第 N 条。"),
    "Pass.Exit": dict(zh="离开图形", lo=-1, hi=2147483647,
                      hint="单位从这种地形走出去时脚底下画的那个动画。"),
    "Pass.Enter": dict(zh="进入图形", lo=-1, hi=2147483647,
                       hint="单位走进这种地形时画的动画（踩水花）。"),
    "Pass.Walk": dict(zh="行走图形", lo=-1, hi=2147483647,
                      hint="单位在上面走时持续画的动画。"),
    "Pass.Rate": dict(zh="播图速度", lo=0.0, hi=1000.0,
                      hint="上面那个动画每走一格播几次。0 = 不播。"),
}

#: Nine 32-bit numbers per player colour, x16.  This is where the game gets the
#: blue/red/green a player sees; a mod that recolours teams edits exactly these.
COLOUR_META = {
    "ID": dict(zh="颜色编号", ro=True,
               hint="第几个玩家颜色。单位记录里存的就是这个编号。"),
    "MinimapColour": dict(zh="小地图颜色", lo=0, hi=2147483647,
                          hint="小地图上这个玩家用的颜色值（0xAABBGGRR 之外的"
                               "游戏自有编号）。"),
    "PlayerColorBase": dict(zh="队伍色基色", lo=0, hi=2147483647,
                            hint="单位身上那块队伍颜色的主色。改这一个数字就能"
                                 "换掉整个文明的颜色。"),
    "UnitOutlineColor": dict(zh="单位轮廓色", lo=0, hi=2147483647,
                             hint="单位被描边时用的颜色。"),
    "UnitSelectionColor1": dict(zh="选中色 1", lo=0, hi=2147483647,
                                hint="选中单位时闪的第一种颜色。"),
    "UnitSelectionColor2": dict(zh="选中色 2", lo=0, hi=2147483647,
                                hint="选中单位时闪的第二种颜色。"),
    "MinimapColor2": dict(zh="小地图副色", lo=0, hi=2147483647,
                          hint="小地图上给这个玩家画第二层标记时用的颜色。原版多数是 -1，表示不用。"),
    "MinimapColor3": dict(zh="小地图副色 2", lo=0, hi=2147483647,
                          hint="小地图上的第三个颜色，同样多数是 -1。"),
    "StatisticsText": dict(zh="统计文字颜色", lo=-1, hi=2147483647,
                           hint="计分板上一行文字的颜色编号。-1 = 不指定。"),
}

#: The 25 scalars that follow the 200 terrain records.  Names come from
#: `genieutils/include/genie/dat/TerrainBlock.h`; the values quoted in the hints
#: are measured on the shipped file (2026-11-12) and the wording follows AGE3
#: General tab (`General.cpp`), which prints the same 25 under "Tile Sizes" and
#: "Miscellaneous useless terrain data".
_MAP_META = {
    "MapMinX": dict(zh="地图最小 X",
                     hint="整块地图的左边界（像素）。引擎靠这六个值把格子换算成屏幕位置。"),
    "MapMinY": dict(zh="地图最小 Y", hint="整块地图的上边界（像素）。"),
    "MapMaxX": dict(zh="地图最大 X", hint="整块地图的右边界（像素）。"),
    "MapMaxY": dict(zh="地图最大 Y", hint="整块地图的下边界（像素）。"),
    "MapMaxXplus1": dict(zh="地图最大 X + 1",
                         hint="右边界再往右一格，画格子时用来算整块宽度。"),
    "MapMaxYplus1": dict(zh="地图最大 Y + 1",
                         hint="下边界再往下一格，画多层地形时用来算高度。"),
    "TerrainsUsed2": dict(zh="实际用地形数", lo=0, hi=32767,
                          hint="200 个地形槽里真正被用到的数量，这份数据是 134。"),
    "BordersUsed": dict(zh="实际用边界数", lo=0, hi=32767,
                        hint="地形边界（TerrainBorder）用了几个，这份数据是 0。"),
    "MaxTerrain": dict(zh="最大地形编号", lo=0, hi=32767,
                       hint="地图上出现过的最大的地形编号，这份数据是 0。"),
    "TileWidth": dict(zh="瓦片宽", lo=0, hi=32767,
                      hint="一个菱形瓦片的像素宽度，这份数据是 96。"),
    "TileHeight": dict(zh="瓦片高", lo=0, hi=32767,
                       hint="一个菱形瓦片的像素高度，这份数据是 48。"),
    "TileHalfHeight": dict(zh="瓦片半高", lo=0, hi=32767,
                           hint="TileHeight 的一半，这份数据是 24。"),
    "TileHalfWidth": dict(zh="瓦片半宽", lo=0, hi=32767,
                          hint="TileWidth 的一半，这份数据是 48。"),
    "ElevHeight": dict(zh="抬高一级差多少", lo=0, hi=32767,
                       hint="地面抬高一级差多少像素，这份数据是 24。"),
    "CurRow": dict(zh="当前行", hint="存档时停在哪一行；新建的地图是 0。"),
    "CurCol": dict(zh="当前列", hint="存档时停在哪一列；新建的地图是 0。"),
    "BlockBegRow": dict(zh="分块起始行", hint="地图分块渲染的起始行，这份数据是 0。"),
    "BlockEndRow": dict(zh="分块结束行", hint="地图分块渲染的结束行，这份数据是 0。"),
    "BlockBegCol": dict(zh="分块起始列", hint="地图分块渲染的起始列，这份数据是 0。"),
    "BlockEndCol": dict(zh="分块结束列", hint="地图分块渲染的结束列，这份数据是 0。"),
    "SearchMapPtr": dict(zh="寻路图指针", ro=True,
                         hint="内存里寻路数组的地址，文件里留的是残值，改它只会让下一次存档更奇怪。"),
    "SearchMapRowsPtr": dict(zh="寻路图行指针", ro=True,
                             hint="同上，内存地址的残值，不是一个能读懂的数值。"),
    "AnyFrameChange": dict(zh="是否每帧重画", lo=0, hi=255,
                           hint="0 = 地形只在变化时更新，1 = 每帧重画。这份数据是 0。"),
    "MapVisibleFlag": dict(zh="地图可见标记", lo=0, hi=255,
                           hint="0 = 不可见，1 = 可见。这份数据是 0（这就是为什么打开地图编辑器之前它什么都不画）。"),
    "FogFlag": dict(zh="迷雾标记", lo=0, hi=255,
                    hint="1 = 开战争迷雾。这份数据是 1。"),
}

#: The seven i32 counters that sit between the last tech and the tech tree.
#: Order and names from `genieutils/include/genie/dat/DatFile.h` (/// History
#: totals); the labels are AGE3 TechTrees tab History Totals, the values are
#: measured on the shipped file.
_TAIL_FIELDS = (
    ("TimeSlice", "时间切片", "一回合被切成多少份，引擎用它给历史统计算速率。这份数据是 30。"),
    ("UnitKillRate", "单位击杀率", "历史统计里每击杀一个单位记多少分。这份数据是 7。"),
    ("UnitKillTotal", "单位击杀总分", "击杀分数的封顶。这份数据是 14。"),
    ("UnitHitPointRate", "单位生命率", "历史统计里每一点生命记多少分。这份数据是 700。"),
    ("UnitHitPointTotal", "单位生命总分", "生命分数的封顶。这份数据是 1400。"),
    ("RazingKillRate", "拆建筑率", "拆掉一座建筑记多少分。这份数据是 5。"),
    ("RazingKillTotal", "拆建筑总分", "拆建筑分数的封顶。这份数据是 10。"),
)
_TAIL_META = dict((n, dict(zh=z, hint=h)) for n, z, h in _TAIL_FIELDS)

#: Fields every tech-tree connection has.  The Status / LocationInAge /
#: LineMode enumerations are copied verbatim from AGE3 `TechTrees.cpp`
#: (StatusHelp / LocationInAgeHelp / LineModeHelp, lines 2519-2524).
_TECHTREE_META = {
    "ID": dict(zh="编号",
               hint="这条连线指向的东西的编号：时代是 1 到 4，建筑、单位、科技各自是它自己的编号。"),
    "Status": dict(zh="状态", lo=0, hi=255,
                   hint="0 无 / 1 无 / 2 玩家可用 / 3 玩家不可用 / 4 正在研究或建造 / 5 已完成 / 6 结束。文件里存的多数是 2。"),
    "CommonSlotsUsed": dict(zh="用掉的连线槽", lo=0, hi=10,
                            hint="后面的 20 个槽填了几个。画科技树时从这个节点引出的线就这么多。"),
    "NumBuildingLevels": dict(zh="建筑层数", lo=0, hi=255,
                              hint="这个时代在建筑页上占几层，原版是 0。"),
    "MaxAgeLength": dict(zh="这个时代最长连线", lo=0, hi=255,
                         hint="时代之间连线的最大长度，原版是 0。"),
    "LineMode": dict(zh="连线模式",
                     hint="0 科技：第一个时代 / 1 时代 / 2 单位：竖线第一个 / 3 单位：不是第一个 / 4 科技 / 5 建筑：有一条以上连线 / 6 建筑：没有连线。"),
    "LocationInAge": dict(zh="在时代里的位置",
                          hint="0 隐藏 / 1 第一个 / 2 第二个。AGE3 的 LocationInAgeHelp 就是这三个。"),
    "UpperBuilding": dict(zh="挂在哪座建筑下",
                          hint="这条连线从哪座建筑引出来；-1 表示没有上层建筑。"),
    "VerticalLine": dict(zh="竖线编号",
                         hint="同一条升级链上的竖线序号，越大越靠右。"),
    "RequiredResearch": dict(zh="需要先研究哪个科技",
                             hint="单位升级链上用：-1 表示它是链上第一个，否则填上一步的科技编号。"),
    "EnablingResearch": dict(zh="哪个科技解锁它",
                             hint="-1 表示一开始就有；否则要研究了这个科技才出现在科技树上。"),
    # The three group-count bytes.  They say how many i32 IDs follow, so
    # changing one changes the width of this record and of every record after
    # it -- AGE3 lets you type over them, this screen does not.
    "BuildingsCount": dict(zh="后面有几座建筑", lo=0, hi=255, ro=True,
                            hint="这条记录后面跟着几个建筑编号。改它会改变整条记录的长度，所以只读。"),
    "UnitsCount": dict(zh="后面有几个单位", lo=0, hi=255, ro=True,
                        hint="这条记录后面跟着几个单位编号。改它会改变整条记录的长度，所以只读。"),
    "TechsCount": dict(zh="后面有几个科技", lo=0, hi=255, ro=True,
                        hint="这条记录后面跟着几个科技编号。改它会改变整条记录的长度，所以只读。"),
}

#: Per-slot families: the name is `<head>.<n>`, so the Chinese label has to be
#: built from the head instead of written 10 times per connection (550
#: connections x 20 slots would be 11,000 hand-written entries).
_TECHTREE_FAMILY = {
    "Buildings": ("建筑组第 %s 个", "这个时代能建的建筑编号之一。"),
    "Units": ("单位组第 %s 个", "这个时代能出的单位编号之一。"),
    "Techs": ("科技组第 %s 个", "这个时代能研究的科技编号之一。"),
    "BuildingsPerZone": ("第 %s 个区域几座建筑",
                         "AGE3 里叫 Buildings per zone：时代页按区域分栏，这里写每栏放几座建筑。"),
    "GroupLengthPerZone": ("第 %s 个区域多长",
                           "AGE3 里叫 Group length per zone：每栏的分组长度。"),
    "UnitsTechsTotal": ("第 %s 个时代的总数",
                        "AGE3 里叫 Units & Techs by Age：这个时代画出来的单位加科技总数。"),
    "UnitsTechsFirst": ("第 %s 个时代的首项",
                        "AGE3 里叫 Units & Techs @ 1st by Age：这个时代第一个画出来的编号。"),
    "CommonUnitResearch": ("第 %s 个连线槽指向",
                           "槽里填的是单位或科技的编号，画科技树时从它引线。"),
    "CommonMode": ("第 %s 个槽的类型",
                   "0 时代或科技层级 / 1 建筑 / 2 单位 / 3 科技。决定引线连到哪一栏。"),
}

#: Human name for each table, for a refusal sentence.
TABLE_ZH = {k: v["zh"] for k, v in TABLES.items()}

#: Which stage the walk has to reach before this table's records are addressable.
#: Graphics and sounds live in stages 3 and 2; effects live in stage 5, and the
#: 89 MB civ block that costs 10 s is stage 8 -- so one constant per table is the
#: difference between a 0.4 s index and a 10 s one.
_TABLES_STOP = {"graphic": "3 ", "sound": "3 ", "effect": "5 ",
                # Restrictions and colours are inside stage 1; the terrain block
                # is stage 4.  Both sit before the 3.2 MB graphic table, so the
                # walk is cheaper than the graphic one, not dearer.
                "restriction": "2 ", "colour": "2 ", "terrain": "5 ",
                # UnitTasks are stage 7.  Stopping at "8 " made the walk enter
                # stage 8 -- the 89 MB civ block, read_civ x 63 -- and threw the
                # answer away.  Measured on two files (2026-11-12): "7 " gives
                # 2329 records, leftover 0, in 0.19 s / 0.24 s; "8 " gives the
                # same 2329 records in 5.04 s / 6.47 s.  Same answer, 25x the
                # price, and it was the freeze the progress bar could not fill.
                "task": "7 ",
                # Civs stops at stage 7 on purpose: stage 7's END is the civ
                # block's first byte, so the 89 MB block is never entered.  Its
                # record starts come from the unit index -- see TABLES["civ"].
                # Stopping at "8 " instead cost 4.43 s for the same answer.
                "civ": "7 ",
                # The terrain block's own scalars sit after the 200 terrain
                # records, inside stage 4 -- the same stop the terrain table
                # uses, so the walk is already paid for.
                "map": "5 ",
                # The seven global counters and the tech tree are the whole of
                # stage 10, which is the END of the file -- there is no cheaper
                # stop.  Measured 2026-11-12: 5.5 s, and 5.4 s of that is the
                # 89 MB civ block that has to be stepped over to reach it.
                "tail": "10 ", "techtree": "10 "}


def _meta(table):
    if table == "graphic":
        return GRAPHIC_META
    if table == "sound":
        return SOUND_META
    if table == "effect":
        return EFFECT_META
    if table == "terrain":
        return TERRAIN_META
    if table == "restriction":
        return RESTRICTION_META
    if table == "colour":
        return COLOUR_META
    if table == "task":
        return TASK_META
    if table == "civ":
        return CIV_META
    if table == "map":
        return _MAP_META
    if table == "tail":
        return _TAIL_META
    if table == "techtree":
        return _TECHTREE_META
    return {}


def _meta_for(table, name):
    """Meta for one field name, including the effect `#N.slot` spelling."""
    tbl = _meta(table)
    if name in tbl:
        return tbl[name]
    if table == "restriction":
        # 670 fields named `Mult.7` / `Pass.7.Walk` -- one family per terrain
        # slot.  Matching them by suffix would look each one up under "7" and
        # find nothing, so the family is matched by prefix and the per-slot
        # Chinese label is built here instead of 670 hand-written entries.
        head, _dot, rest = name.partition(".")
        if head == "Mult" and rest.isdigit():
            out = dict(RESTRICTION_META["Mult"])
            out["zh"] = "地形 %s 的伤害倍率" % rest
            return out
        if head == "Pass" and "." in rest:
            slot, _dot2, what = rest.partition(".")
            key = "Pass." + what
            if key in RESTRICTION_META and slot.isdigit():
                out = dict(RESTRICTION_META[key])
                out["zh"] = "地形 %s 的%s" % (slot, out["zh"])
                return out
        return {}
    if table == "civ" and name.startswith("Resource."):
        # 601 slots share one family.  Hand-writing 601 entries would be 601
        # chances for a typo, and `civlabels` already carries the name the game
        # itself uses -- generated from the AGE3 research dump, so both tools
        # call slot 189 the same thing instead of disagreeing about it.
        from aoe2mod.game import civlabels as CL
        rest = name.partition(".")[2]
        if rest.isdigit():
            slot = int(rest)
            out = dict(CIV_META["Resource"])
            out["zh"] = CL.label(slot)
            out["hint"] = _civ_slot_hint(slot)
            if not CL.is_live(slot):
                # Nothing in the shipped file puts a value here, so a player who
                # types one is experimenting rather than editing.  Saying that is
                # the difference between "this tool is broken" and "this number
                # is unused by the game".
                out["hint"] = (out["hint"] + "（这份数据里 63 个文明全是 0）"
                               if out["hint"] else "这份数据里 63 个文明全是 0")
            return out
        return {}
    if table == "techtree":
        # 550 connections x 20 slots: the label has to be built from the
        # head, not written 11,000 times.
        head, _dot, rest = name.partition(".")
        if head in _TECHTREE_FAMILY and rest.isdigit():
            zh, hint = _TECHTREE_FAMILY[head]
            return dict(zh=zh % rest, hint=hint)
        return {}
    if "." in name:
        slot = name.rsplit(".", 1)[-1]
        if slot in _SLOT_META:
            return _SLOT_META[slot]
    return {}


def meta_for(table, name):
    """The label table entry for one field, or `{}`."""
    return _meta_for(table, name)


class _StageStop(Exception):
    """Stop the stage walk early.  One class for the whole module, on purpose.

    Defined at module level rather than inside `stage_offsets()` so that a
    wrapper installed by one call can be caught by the `except` of another:
    a per-call class object is a different class, and the mismatch shows up as
    an uncaught `_Stop: 没有说明` on screen instead of a stopped walk.
    """


def stage_offsets(raw, upto="3 ", quiet=False):
    """`{stage name: (start, end)}` from one pass over stages 1..`upto`.

    Measured 2026-11-02: stopping after stage 3 costs 0.35 s on a 93 MB file,
    because stages 1-3 only cover the first 3.5 MB.  Everything after that (the
    89 MB Civs stage) is not needed to address a graphic or a sound, so this does
    NOT pay the 10 s the unit index costs.

    Effects sit in stage 5, so they stop one stage later: measured 2026-11-03,
    stages 1-5 cover the first 3.7 MB and still finish in well under a second,
    because the expensive Civs stage is stage 8 and is never reached.
    """
    def stage(self, name, fn, stop_after=None):
        start = self.r.pos
        orig(self, name, fn, stop_after)
        if name.startswith(upto):
            raise _StageStop()

    # The patch is module-wide, so it takes the same lock `Parser.parse` and the
    # two field scanners take.  A second thread parsing inside this window would
    # run the un-patched `stage` of whoever captured it last, and the `_Stop`
    # would then be raised by a wrapper that is no longer installed -- a silent
    # partial parse reported as a complete one.
    #
    # `orig` is read INSIDE the lock, and `_StageStop` is one module-level class.
    # Both are load-bearing, and both were wrong until 2026-11-06:
    #
    #   * read outside the lock, a waiter snapshots the CURRENT holder's wrapper
    #     as "the original", so when its turn comes it calls a wrapper whose
    #     `except _Stop` (a per-call class object) can never match the class the
    #     inner wrapper raises.  Reproduced with three threads on `scan()`: every
    #     one of them died with `_Stop()` and the screen showed
    #     `读不到字段：_Stop: 没有说明`, because the exception carries no message.
    #   * a class defined inside the function is a NEW class per call, so even
    #     one wrapper nested inside another cannot be caught by the outer
    #     `except`.  One module-level class makes every nesting depth catchable.
    with P._PARSE_LOCK:
        orig = P.Parser._stage
        P.Parser._stage = stage
        try:
            # `quiet` silences the per-stage banner `Parser._stage` prints.
            # The page editor asks for this window once per dropped icon, and
            # five lines of stage arithmetic per click is not log, it is noise.
            # Still inside the lock: stdout is process wide.
            sink = io.StringIO() if quiet else None
            if sink is None:
                p = P.Parser(raw)
                try:
                    p.parse()
                except _StageStop:
                    pass
            else:
                with contextlib.redirect_stdout(sink):
                    p = P.Parser(raw)
                    try:
                        p.parse()
                    except _StageStop:
                        pass
        finally:
            P.Parser._stage = orig
    return {name: (start, end) for name, start, end in p.stage_offsets}, p.stats


_TERRAIN_NAMES = (
    # (name, kind) in the exact order `parser.read_terrain` reads them.  The
    # unnamed reads in the middle (the 19 tile frames, the 30-entry unit masks)
    # are walked but not reported: they are fixed-size padding the game itself
    # never shows, and naming them would add 300 rows of noise to a 19-row page.
    ("enabled", "u8"), ("random", "u8"), ("is_water", "u8"),
    ("hide_in_editor", "u8"), ("string_id", "i32"), ("name", "str"),
    ("name2", "str"), ("slp", "i32"), ("shape_ptr", "i32"),
    ("sound_id", "i32"), ("wwise_sound_id", "u32"),
    ("wwise_sound_stop_id", "u32"), ("blend_priority", "i32"),
    ("blend_type", "i32"), ("overlay_mask_name", "str"),
)

_TERRAIN_LABEL = {
    "enabled": "Enabled", "random": "Random", "is_water": "IsWater",
    "hide_in_editor": "HideInEditor", "string_id": "StringID", "name": "Name",
    "name2": "Name2", "slp": "Slp", "shape_ptr": "ShapePtr",
    "sound_id": "SoundID", "wwise_sound_id": "WwiseSoundID",
    "wwise_sound_stop_id": "WwiseSoundStopID",
    "blend_priority": "BlendPriority", "blend_type": "BlendType",
    "overlay_mask_name": "OverlayMaskName",
    "passable_terrain": "PassableTerrain",
    "impassable_terrain": "ImpassableTerrain",
    "is_animated": "IsAnimated", "phantom": "Phantom",
}


def _walk_terrain(r, want_fields):
    """Replay `parser.read_terrain`, recording only what a screen shows.

    Returns `{name: (offset, kind, value)}`.  The fixed-size middle (19 tile
    frames, and three 30-entry unit tables plus a 30-byte centering mask) is
    skipped by the same widths `read_terrain` uses, so the offsets of the two
    named scalars that come AFTER it (`PassableTerrain`, `ImpassableTerrain`)
    stay honest.  Getting that arithmetic wrong would silently name a padding
    byte as a terrain attribute -- which the leftover check on the whole block
    catches, but only because the walker is shared with the index.
    """
    out = {}

    def take(name, kind, fn):
        pos = r.pos
        val = fn()
        if want_fields:
            out[name] = (pos, kind, val)
        return val

    take("enabled", "u8", r.u8)
    take("random", "u8", r.u8)
    take("is_water", "u8", r.u8)
    take("hide_in_editor", "u8", r.u8)
    take("string_id", "i32", r.i32)
    pos = r.pos
    text = r.debug_string()[1]
    if want_fields:
        out["name"] = (pos, "str", text)
    pos = r.pos
    text2 = r.debug_string()[1]
    if want_fields:
        out["name2"] = (pos, "str", text2)
    take("slp", "i32", r.i32)
    take("shape_ptr", "i32", r.i32)
    take("sound_id", "i32", r.i32)
    take("wwise_sound_id", "u32", r.u32)
    take("wwise_sound_stop_id", "u32", r.u32)
    take("blend_priority", "i32", r.i32)
    take("blend_type", "i32", r.i32)
    pos = r.pos
    mask = r.debug_string()[1]
    if want_fields:
        out["overlay_mask_name"] = (pos, "str", mask)
    r.skip(3)                                             # Colors[3]
    r.skip(2)                                             # CliffColors pair
    take("passable_terrain", "u8", r.u8)
    take("impassable_terrain", "u8", r.u8)
    take("is_animated", "u8", r.u8)
    r.i16()                                               # AnimationFrames
    r.i16()                                               # PauseFames
    r.f32()                                               # Interval
    r.f32()                                               # PauseBetweenLoops
    r.i16()                                               # Frame
    r.i16()                                               # DrawFrame
    r.f32()                                               # AnimateLast
    r.u8()                                                # FrameChanged
    r.u8()                                                # Drawn
    for _ in range(P.TILE_TYPE_COUNT):
        P.read_frame_data(r)
    r.i16()                                               # TerrainToDraw
    r.i16_array(2)                                        # TerrainDimensions
    r.i16_array(P.TERRAIN_UNITS_SIZE)                     # UnitMaskedDensity
    r.i16_array(P.TERRAIN_UNITS_SIZE)                     # UnitID
    r.i16_array(P.TERRAIN_UNITS_SIZE)                     # UnitDensity
    r.skip(P.TERRAIN_UNITS_SIZE)                          # UnitCentering
    r.i16()                                               # NumberOfUnitsUsed
    take("phantom", "i16", r.i16)
    return out


def _scan_terrains(raw, gv):
    """Every terrain record's byte range, walked from the real record reader.

    The count in the file (`terrains_used2`, 134) is NOT the number of records
    stored (`TERRAIN_COUNT_FOR_TERRAINBLOCK`, 200).  Both numbers are real: the
    block always carries 200 slots, of which 134 are in use.  Indexing all 200
    is deliberate -- a mod that turns terrain 150 on needs its address, and a
    table that hid the unused slots would report "no such record" for a record
    that is right there in the file.
    """
    r = P.Reader(raw, P.GV_C32 if gv is None else gv)
    r.pos = 0
    r.fixed_string(P.FILE_VERSION_SIZE)
    trc = r.i16()
    tu1 = r.i16()
    r.i32_array(trc)
    r.i32_array(trc)
    for _ in range(trc):
        r.f32_array(tu1)
        for _ in range(tu1):
            P.read_terrain_pass_graphic(r)
    n = r.i16()
    r.i32_array(9 * n)
    # stage 2 + 3
    n = r.i16()
    for _ in range(n):
        P.read_sound(r)
    n = r.i16()
    ptrs = r.i32_array(n)
    for p in ptrs:
        if p:
            P.read_graphic(r)
    # stage 4: skip the 33-key header verbatim, then walk the terrains
    r.u32(); r.u32(); r.i32(); r.i32(); r.i32(); r.i32()
    for _ in range(P.TILE_TYPE_COUNT):
        r.i16_array(3)
    r.i16()                                               # PaddingTS
    recs = []
    for i in range(P.TERRAIN_COUNT_FOR_TERRAINBLOCK):
        start = r.pos
        _walk_terrain(r, False)
        recs.append({"index": i, "start": start, "end": r.pos})
    return recs, r.pos


def scan(raw, table="graphic", civ_starts=None, civ_ends=None,
         civ_units=None):
    """`(records, leftover_bytes)` for one table.

    Each record is ``{"index", "start", "end", "fields": {name: {...}}}``.  A
    record's `end` is the NEXT record's `start`, so a wrong width cannot hide:
    it shows up as a non-zero leftover at the end of the table.
    """
    if table not in TABLES:
        raise ValueError("没有叫 %r 的表（只有 %s）"
                         % (table, "、".join(sorted(TABLES))))
    bounds, stats = stage_offsets(raw, _TABLES_STOP.get(table, "3 "))
    spec = TABLES[table]
    start, end = bounds[spec["stage"]]
    recs = stats.get(spec["list"]) or []

    if table == "effect":
        return _scan_effects(raw, start, end, recs)
    if table == "sound":
        return _scan_sounds(raw, start, end, recs)

    if table == "task":
        return _scan_tasks(raw, stats.get("game_version"), start, end)

    if table == "civ":
        # `civ_starts` comes from the caller (the unit index).  Without it the
        # honest walk is 9.15 s, which is why it is not the default: a caller
        # that has not built the unit index gets a sentence, not a silent
        # ten-second pause.
        starts = civ_starts
        if not starts:
            raise ValueError("文明表要用单位索引给出的记录起点，"
                             "先打开一次「单位」页签再来")
        # `start` here is stage 7's boundary; the civ block begins at its END.
        return _scan_civs(raw, stats.get("game_version"), starts,
                          civ_ends or [], civ_units)

    if table == "terrain":
        recs, after = _scan_terrains(raw, stats.get("game_version"))
        # The 33 trailing scalars and the RandomMaps block share stage 4 with the
        # records, so "what is left" has to be measured against them.  They are
        # consumed by the parser's own readers rather than by arithmetic here:
        # a wrong trailing width is exactly the bug that ran the graphic walk off
        # the end of the file, and restating a layout is how it happened.
        r = P.Reader(raw, P.GV_C32)
        r.pos = after
        _terrain_block_tail(r)
        P.read_random_maps(r)
        return recs, end - r.pos

    if table == "restriction":
        # Stage 1: two pointer arrays, then 54 fixed-width records of
        # 134 floats + 134 x 16-byte pass graphics (2,680 bytes each).
        pos = _stage1_records_at(raw, stats)
        per = 20 * (stats.get("terrains_used1") or 134)
        n = stats.get("terrain_restriction_count") or 0
        out = [{"index": i, "start": pos + per * i, "end": pos + per * (i + 1)}
               for i in range(n)]
        # The colour table follows inside the same stage, so the leftover for a
        # restriction record set is "nothing may sit between the last record and
        # the colour count" -- checked by re-deriving the colour start below.
        # `_colour_count_at` returns the offset of the count FIELD, which sits
        # in front of the colour records -- not of the records themselves.  The
        # first version added 2 here and got a leftover of -1 on a table that
        # walks perfectly, which is the check working: it refused to report
        # "done" for a walk whose end it had measured wrong.
        colour_at = pos + per * n
        return out, 0 if colour_at == _colour_count_at(raw, stats) else -1

    if table == "colour":
        n = stats.get("player_colour_count") or 0
        pos = _colour_count_at(raw, stats) + 2
        out = [{"index": i, "start": pos + 36 * i, "end": pos + 36 * i + 36}
               for i in range(n)]
        return out, start + (end - start) - (pos + 36 * n)


    if table == "map":
        # Stage 4 is 200 terrain records, then these 25 scalars, then the
        # RandomMaps block.  The walk is shared with the terrain table on
        # purpose: two copies of "where do the records end" is how a layout
        # drifts, and a drifted width here would name a padding byte.
        _recs, after = _scan_terrains(raw, stats.get("game_version"))
        r = P.Reader(raw, P.GV_C32)
        r.pos = after
        _terrain_block_tail(r, True)
        stop = r.pos
        P.read_random_maps(r)
        return [{"index": 0, "start": after, "end": stop}], end - r.pos

    if table == "tail":
        # Seven i32 counters between the last technology and the tech tree.
        # One record each, so the picker says 「单位击杀率」 instead of
        # 「全局数值 · 第 2 个字段」.
        out = [{"index": i, "start": start + 4 * i, "end": start + 4 * i + 4}
               for i in range(len(_TAIL_FIELDS))]
        r = P.Reader(raw, P.GV_C32)
        r.pos = start + 4 * len(_TAIL_FIELDS)
        P.read_tech_tree(r)
        return out, end - r.pos

    if table == "techtree":
        # Stage 10 begins with the seven counters, not with the tree:
        # the tree header starts 4 * 7 = 28 bytes in.  Reading from
        # `start` would take the first counter as the age count and
        # report 30 ages.
        gv = stats.get("game_version")
        r = P.Reader(raw, P.GV_C32 if gv is None else gv)
        r.pos = start + 4 * len(_TAIL_FIELDS)
        out = _techtree_walk(r, False)
        return out, end - r.pos

    # Graphics: walk the same stream the parser walked, using the record count
    # it reported, and derive each record's end from the next record's start.
    #
    # The pointer array comes FIRST and is skipped, not followed: `stage3` reads
    # `graphic_count` pointers and then walks the records in stream order,
    # ignoring the pointers (`for p in ptrs if p != 0`).  Measured 2026-11-02:
    # 21,001 pointers but 20,883 records, so the pointers are read for their
    # non-zero COUNT only.  Starting the walk at the pointer array instead of
    # after it would read the first pointer as a string marker.
    n = stats.get(spec["count"]) or 0
    r = P.Reader(raw, P.GV_C32)
    r.pos = start + 2 + 4 * n               # count, then the pointer array
    starts, ends = [], []
    for i in range(len(recs)):
        rec_start = r.pos
        # Three length-prefixed strings, in this exact order.
        for _ in range(3):
            r.debug_string()
        base = r.pos                            # first fixed-width field
        delta_count = struct.unpack_from("<h", raw, base + 18)[0]
        angle_used = raw[base + 26]
        angle_count = struct.unpack_from("<h", raw, base + 29)[0]
        # 48, not `len(_GRAPHIC_TAIL)`: the table has 24 ENTRIES but the scalar
        # block is 48 BYTES (i32 + three u8 ... ).  Using the entry count as a
        # width walked 24 bytes short per record and ran off the end of the file
        # at 93,613,524 -- measured, then fixed.
        tail = base + _GRAPHIC_SCALARS
        tail += delta_count * 16
        if angle_used:
            tail += angle_count * 24
        starts.append(rec_start)
        ends.append(tail)
        r.pos = tail
    out = []
    for i, (s, e) in enumerate(zip(starts, ends)):
        out.append({"index": i, "start": s, "end": e})
    leftover = end - (ends[-1] if ends else start)
    return out, leftover


def _stage1_records_at(raw, stats):
    """Byte offset of the first terrain-restriction record inside stage 1."""
    r = P.Reader(raw, P.GV_C32)
    r.pos = 0
    r.fixed_string(P.FILE_VERSION_SIZE)
    trc = r.i16()
    r.i16()                                        # terrains_used1
    r.i32_array(trc)                               # float pointers
    r.i32_array(trc)                               # pass-graphic pointers
    return r.pos


def _colour_count_at(raw, stats):
    """Byte offset of the `player_colour_count` field (two bytes before colours)."""
    r = P.Reader(raw, P.GV_C32)
    r.pos = _stage1_records_at(raw, stats)
    trc = stats.get("terrain_restriction_count") or 0
    tu1 = stats.get("terrains_used1") or 134
    for _ in range(trc):
        r.f32_array(tu1)
        for _ in range(tu1):
            P.read_terrain_pass_graphic(r)
    return r.pos


_MAP_TAIL = (
    ("MapMinX", "f32"), ("MapMinY", "f32"),
    ("MapMaxX", "f32"), ("MapMaxY", "f32"),
    ("MapMaxXplus1", "f32"), ("MapMaxYplus1", "f32"),
    ("TerrainsUsed2", "i16"), ("BordersUsed", "i16"),
    ("MaxTerrain", "i16"),
    ("TileWidth", "i16"), ("TileHeight", "i16"),
    ("TileHalfHeight", "i16"), ("TileHalfWidth", "i16"),
    ("ElevHeight", "i16"),
    ("CurRow", "i16"), ("CurCol", "i16"),
    ("BlockBegRow", "i16"), ("BlockEndRow", "i16"),
    ("BlockBegCol", "i16"), ("BlockEndCol", "i16"),
    ("SearchMapPtr", "u32"), ("SearchMapRowsPtr", "u32"),
    ("AnyFrameChange", "u8"), ("MapVisibleFlag", "u8"), ("FogFlag", "u8"),
)

#: `TileSize` is 19 x (Width, Height, DeltaY) and sits BEFORE the 200 records,
#: so it is not part of this block; `General.cpp` prints it under "Tile Sizes".
assert len(_MAP_TAIL) == 25
assert set(_MAP_META) == set(n for n, _k in _MAP_TAIL), (_MAP_META.keys() ^ set(n for n, _k in _MAP_TAIL))


def _terrain_block_tail(r, want_fields=False):
    """The 25 named scalars `read_terrain_block` reads AFTER the 200 records.

    Copied from `parser.read_terrain_block` line for line, for the same reason
    `unitfields` copies `read_unit`: the proven reader is the layout, and this
    module measures its own walk against it.

    The walk used to throw its values away -- it existed only to move `r.pos`
    past the block.  `want_fields=True` keeps them, because these scalars are
    the tile grid the engine uses to convert between map cells and pixels, and
    until now not one of them had an address on any screen.
    """
    out = {}
    for name, kind in _MAP_TAIL:
        pos = r.pos
        val = getattr(r, kind)()
        if want_fields:
            out[name] = {"offset": pos, "kind": kind, "value": val}
    return out



def _techtree_record(r, want_fields, kind):
    """One tech-tree connection, read the way `parser.read_*_connection` does.

    Returns `(id, fields)`.  `kind` picks the layout and it has to: the four
    families disagree about field order (a unit connection carries
    UpperBuilding + VerticalLine, a research connection carries three ID
    groups), so one reader per family is the honest shape.  A single generic
    walker would have to guess at widths, which is the bug that once ran the
    graphic walk off the end of the file.
    """
    out = {}

    def put(name, fkind, fn, **extra):
        pos = r.pos
        val = fn()
        if want_fields:
            row = {"offset": pos, "kind": fkind, "value": val}
            row.update(extra)
            out[name] = row
        return val

    def group(head):
        # `<count byte>` then that many i32.  The count is a read-only FIELD,
        # not a decoder: it is the record's own width, so a screen that let a
        # player type over it would rewrite the rest of the table.
        n = put(head + "Count", "u8", r.u8, ro=True)
        for i in range(n):
            put("%s.%d" % (head, i), "i32", r.i32)

    def common():
        # techtree::Common, 84 bytes: SlotsUsed, 10 x UnitResearch, 10 x Mode.
        put("CommonSlotsUsed", "i32", r.i32)
        for i in range(10):
            put("CommonUnitResearch.%d" % i, "i32", r.i32)
        for i in range(10):
            put("CommonMode.%d" % i, "i32", r.i32)

    ident = put("ID", "i32", r.i32)
    put("Status", "u8", r.u8)
    if kind == "age":
        group("Buildings")
        group("Units")
        group("Techs")
        common()
        put("NumBuildingLevels", "u8", r.u8)
        for i in range(10):
            put("BuildingsPerZone.%d" % i, "u8", r.u8)
        for i in range(10):
            put("GroupLengthPerZone.%d" % i, "u8", r.u8)
        put("MaxAgeLength", "u8", r.u8)
        put("LineMode", "i32", r.i32)
    elif kind == "building":
        group("Buildings")
        group("Units")
        group("Techs")
        common()
        put("LocationInAge", "u8", r.u8)
        for i in range(P.AGES):
            put("UnitsTechsTotal.%d" % i, "u8", r.u8)
        for i in range(P.AGES):
            put("UnitsTechsFirst.%d" % i, "u8", r.u8)
        put("LineMode", "i32", r.i32)
        put("EnablingResearch", "i32", r.i32)
    elif kind == "unit":
        put("UpperBuilding", "i32", r.i32)
        common()
        put("VerticalLine", "i32", r.i32)
        group("Units")
        put("LocationInAge", "i32", r.i32)
        put("RequiredResearch", "i32", r.i32)
        put("LineMode", "i32", r.i32)
        put("EnablingResearch", "i32", r.i32)
    else:
        put("UpperBuilding", "i32", r.i32)
        group("Buildings")
        group("Units")
        group("Techs")
        common()
        put("VerticalLine", "i32", r.i32)
        put("LocationInAge", "i32", r.i32)
        put("LineMode", "i32", r.i32)
    return ident, out


def _techtree_walk(r, want_fields):
    """All the tech-tree connections in file order, each with its byte range.

    The 550 records are four families in one run: 4 ages, 37 buildings, 269
    units, 240 technologies on the shipped file.  `read_tech_tree` keeps only
    the five counts, so this walk is the only thing that knows where each
    connection starts -- which is what makes it editable at all.
    """
    age_count = r.u8()
    building_count = r.u8()
    # TechTree.cpp guards the unit count with an inline getGameVersion() call,
    # so it is int16 only from C32 onward; the research count is int16 only
    # for the CCV2 build.  Same two guards as `parser.read_tech_tree`.
    unit_count = r.i16() if r.gv >= P.GV_C32 else r.u8()
    research_count = r.i16() if r.gv == P.GV_CCV2 else r.u8()
    r.i32()                                        # total_unit_tech_groups
    out = []
    for kind, n in (("age", age_count), ("building", building_count),
                    ("unit", unit_count), ("research", research_count)):
        for _ in range(n):
            at = r.pos
            ident, flds = _techtree_record(r, want_fields, kind)
            row = {"index": len(out), "start": at, "end": r.pos,
                   "kind": kind, "id": ident}
            if want_fields:
                row["fields"] = flds
            out.append(row)
    return out


def _scan_effects(raw, start, end, recs):
    """Walk the effect table once, recording where each record begins and ends.

    Measured 2026-11-03: 1,500 records, 10,500 commands, 149,458 bytes, 0.00 s.
    A record is `debug_string` (its name) + `i16 count` + `count * 11` bytes, and
    the walk mirrors `read_effect` field for field because a single wrong width
    here shifts every later record's offset.

    Command indices are reported alongside the record boundaries: `fields_at`
    needs them to name `#3.2` (record 3, command 2) without re-walking the whole
    table, and a picker needs the record's byte span to show its size.
    """
    r = P.Reader(raw, P.GV_C32)
    r.pos = start
    r.i32()                                    # effect_count
    out = []
    for i in range(len(recs)):
        s = r.pos
        r.debug_string()                       # name
        n = r.i16()                            # command count
        cmds = []
        for _ in range(n):
            cmds.append({"at": r.pos})
            r.pos += 11                        # (u8, i16, i16, i16, f32)
        out.append({"index": i, "start": s, "end": r.pos,
                    "commands": cmds, "command_count": n})
    return out, end - (out[-1]["end"] if out else start)


def _scan_sounds(raw, start, end, recs):
    """Walk the sound table once, recording where each record begins and ends.

    Measured 2026-11-02: 930 records in 140,711 bytes.  The walk mirrors
    `read_sound` field for field, because a single wrong width here shifts every
    later record's offset -- and unlike graphics, the end of one sound record is
    not recoverable from a length field, so the walk IS the definition.
    """
    r = P.Reader(raw, P.GV_C32)
    r.pos = start
    r.i16()                                   # sound_count
    out = []
    for i in range(len(recs)):
        s = r.pos
        r.i16()                                # id
        r.i16()                                # play_delay
        n = r.i16()                            # file_count
        r.i32()                                # cache_time
        r.i16()                                # total_probability
        for _ in range(n):
            r.debug_string()
            r.i32()                            # resource_id
            r.i16()                            # probability
            r.i16()                            # civilization
            r.i16()                            # iconset
        out.append({"index": i, "start": s, "end": r.pos})
    return out, end - (out[-1]["end"] if out else start)


#: The sixteen colours the game ships, as the lobby names them.  Kept here
#: rather than in the .dat because the file only stores numbers: colour 2 is
#: `48/241/241`, and nothing in the file says that is "blue".  Measured
#: 2026-11-03 against the main-menu colour list.
_COLOUR_PALETTE = ("蓝", "红", "绿", "黄", "青", "紫", "灰", "橙",
                   "浅蓝", "浅红", "浅绿", "浅黄", "浅青", "浅紫", "白", "黑")


def _colour_zh(index):
    """Chinese name for a player-colour slot, or "" when out of range."""
    if 0 <= index < len(_COLOUR_PALETTE):
        return "%s（颜色 %d）" % (_COLOUR_PALETTE[index], index)
    return ""


# ---------------------------------------------------------------------------
# Civilizations
# ---------------------------------------------------------------------------
# A civ record is six scalars and a 601-entry float array, then a pointer array
# to its units.  Measured on the shipped file 2026-11-04:
#
#   civ_count 63, every record n == 601, every pointer array m == 2,750,
#   non-zero pointers 136,861 in total (== the unit scan's record count).
#
# The header is variable-width because the name is a length-prefixed string, so
# `res_at - start` runs 13..22 bytes.  Every offset below is therefore computed
# from the decoded header, never from a constant.
CIV_META = {
    "PlayerType": {
        "zh": "玩家类型", "ro": True,
        "hint": "63 条记录全是 1（人类玩家）。改它不会让文明变成别的东西，"
                "只会让这个记录长得不像一条正常数据。"},
    "Name": {
        "zh": "内部名字", "ro": True,
        "hint": "带字节数的字符串，改短会留下残字、改长会覆盖后面的数字。"
                "文明的中文名来自游戏的语言表，不在这里改。"},
    "TechTreeID": {
        "zh": "科技树编号", "lo": 0, "hi": 32767,
        "hint": "指向科技树文件里的一行。63 个文明各有一个，改错会让这个文明"
                "用上别人的科技树。"},
    "TeamBonusID": {
        "zh": "团队加成编号", "lo": -1, "hi": 32767,
        "hint": "指向效果表里的一个团队加成。盖亚是 -1（没有加成）。"},
    "Resource": {
        "zh": "资源槽", "kind": "f32",
        "hint": "一个 float 槽位。名字来自 AGE3 的研究数据，"
                "所以两个工具对同一个槽位的叫法一致。"},
    "IconSet": {
        "zh": "界面皮肤", "lo": 1, "hi": 13,
        "hint": "决定这个文明用哪一套界面贴图（建造按钮的样式）。"
                "这是 63 个文明里唯一会变的第六个标量。"},
    "UnitCount": {
        "zh": "单位指针个数", "ro": True,
        "hint": "这条记录后面有 2,750 个指针，其中非零的才是真的单位记录。"
                "这个数一个都不能少，否则整条记录会读歪。"},
    "UnitRecords": {
        "zh": "真实单位记录数", "ro": True,
        "hint": "非零指针的个数。它必须等于单位索引里属于这个文明的记录数，"
                "两个数对不上就说明起点推错了。"},
}


def _civ_slot_hint(slot):
    """One sentence about what a resource slot means, from measurement alone."""
    from aoe2mod.game import civlabels as CL
    if not CL.is_live(slot):
        return ""
    if CL.differs(slot):
        return "63 个文明里这一格不全一样，所以改它真的会改变某个文明。"
    return "63 个文明全是同一个值，改一个就得改全部 63 个才看得出差别。"


def _civ_header(raw, gv, at):
    """Decode one civ record's header.  Returns (dict, res_at, after_icon)."""
    r = P.Reader(raw, P.GV_C32 if gv is None else gv)
    r.pos = at
    player_type = r.u8()
    _marker, name = r.debug_string()
    n = r.i16()
    tech_tree = r.i16()
    team_bonus = r.i16()
    res_at = r.pos
    resources = r.f32_array(n)
    icon = r.u8()
    return ({"player_type": player_type, "name": name, "n": n,
             "tech_tree_id": tech_tree, "team_bonus_id": team_bonus,
             "resources": resources, "icon_set": icon},
            res_at, r.pos)


def _scan_civs(raw, gv, starts, ends, units_seen=None):
    """One record per civilization, addressed by bounds the caller derived.

    Why the caller: a civ's first byte is the byte after the previous civ's last
    unit, and the unit index already knows every unit's end.  Walking this block
    the honest way means re-reading all 136,861 unit records -- 9.15 s -- to
    learn something the app paid for on its first tab.

    `units_seen` is `{civ_index: record count}` from that same index, and it is
    optional only so this module stays usable without one.  When it IS passed,
    the pointer array's non-zero count must equal it: a derived start that is off
    by a byte makes those two disagree, so a wrong start cannot pass silently.
    The returned leftover is negative to say exactly which civilization failed,
    because "the civ table did not walk" with no index is unusable on 63 records.
    """
    out = []
    for i, at in enumerate(starts):
        head, res_at, after = _civ_header(raw, gv, at)
        end = ends[i] if i < len(ends) else len(raw)
        r = P.Reader(raw, P.GV_C32 if gv is None else gv)
        r.pos = after
        m = r.i16()
        ptrs = r.i32_array(m) if m > 0 else []
        nonzero = sum(1 for p in ptrs if p)
        out.append({"index": i, "start": at, "end": end,
                    "civ_name": head["name"], "resources_at": res_at,
                    "header_end": after, "pointer_count": m,
                    "unit_count": nonzero})
        if units_seen is not None:
            want = units_seen.get(i)
            if want is not None and want != nonzero:
                return out, -(i + 1)
    return out, 0


def _civ_fields(raw, gv, rec):
    """Every number in one civilization record, named, ordered by usefulness.

    601 floats is not a field table, it is a haystack.  Measured: 65 slots are
    non-zero somewhere, 24 differ between civilizations, 536 are zero in all 63.
    So the rows are ordered by what a player can actually observe changing --
    the ones that differ, then the ones that have a value, then the named ones
    that are always zero, then the 89 slots the game never named and never
    fills.  The last group is still listed: hiding it would make `Resource.503`
    unreachable, and "it is empty" is a fact, not an absence.
    """
    from aoe2mod.game import civlabels as CL
    head, res_at, _after = _civ_header(raw, gv, rec["start"])
    # rank -1: the six scalars that ARE the record's identity.  Without an
    # explicit rank they default to the worst tier and land among the 536 dead
    # resource slots, which is where the first version put them.
    out = {}
    out["PlayerType"] = {"offset": rec["start"], "kind": "u8",
                         "value": head["player_type"], "rank": -1}
    out["Name"] = {"offset": rec["start"] + 1, "kind": "str",
                   "value": head["name"], "rank": -1}
    # tech_tree / team_bonus sit right after the count, i.e. 4 bytes past the
    # end of the name string.
    name_end = res_at - 4
    out["TechTreeID"] = {"offset": name_end, "kind": "i16",
                         "value": head["tech_tree_id"], "rank": -1}
    out["TeamBonusID"] = {"offset": name_end + 2, "kind": "i16",
                          "value": head["team_bonus_id"], "rank": -1}
    for slot in range(head["n"]):
        name = "Resource.%d" % (slot,)
        if CL.differs(slot):
            rank = 0
        elif CL.is_live(slot):
            rank = 1
        elif slot in CL.RESOURCE_EN or slot in CL.RESOURCE_ZH:
            rank = 2
        else:
            rank = 3
        out[name] = {"offset": res_at + 4 * slot, "kind": "f32",
                     "value": head["resources"][slot], "rank": rank}
    out["IconSet"] = {"offset": _after - 1, "kind": "u8",
                      "value": head["icon_set"], "rank": -1}
    # rank 4: not stored fields.  Both are counted from the pointer array that
    # follows, and `UnitRecords` is the check on this record's derived start --
    # useful to read, meaningless to type over.
    out["UnitCount"] = {"offset": _after, "kind": "i16",
                        "value": rec.get("pointer_count", 0), "rank": 4}
    out["UnitRecords"] = {"offset": _after, "kind": "i16",
                          "value": rec.get("unit_count", 0), "rank": 4,
                          "_reason": "这是从指针数组数出来的，不是文件里的一个格子"}
    return out


def record_name(raw, gv, rec, table="graphic", names=None):
    """What to call one record in a picker.  Never raises.

    A graphic names itself: record 100 is `Barracks ORIE Age3 (Destruction)`, and
    that string is the only thing in the file that says what the record is for.
    Measured 2026-11-02: 17,363 of 20,883 carry a name; the 3,520 that do not are
    entries nothing points at, and a picker listing them is 17% noise.

    A sound record has NO name field at all -- only the files it plays, so the
    first file IS the name (`BLAC.wav`, `HallOfHeroes.wav`).  A record with no
    files returns "" like an unnamed graphic, which keeps the picker's filter
    honest instead of inventing 「音效 47」 for a record that has nothing to say.
    """
    try:
        if table == "task":
            # A task is not a thing with its own name: it is one line of a unit's
            # job list.  So it is named by the unit it belongs to plus which line
            # it is, and `names` (supplied by the caller, which owns the name
            # tables) fills in the Chinese unit name.  Without it the row still
            # says which unit id it came from, which is honest and greppable.
            unit = rec.get("unit")
            who = (names or {}).get(unit) or ("单位 %s" % (unit,))
            act = ACTION_ZH.get(rec.get("action"))
            tail = (" · %s" % act) if act else ""
            return "%s · 第 %d 条%s" % (who, rec.get("task", 0) + 1, tail)
        if table == "terrain":
            # A terrain names itself (`Water, Shallow`).  Measured 2026-11-03:
            # 200 records, all 200 carry a name, so this picker has no noise.
            r = P.Reader(raw, P.GV_C32 if gv is None else gv)
            r.pos = rec["start"]
            r.u8(); r.u8(); r.u8(); r.u8(); r.i32()
            _m, name = r.debug_string()
            name = (name or "").strip()
            return name or ("地形 %d" % rec["index"])
        if table == "restriction":
            # A restriction record is not a thing with a name -- it is one
            # damage table, and the only way to tell 54 of them apart is which
            # units use it.  Naming it by its index is therefore honest, not a
            # fallback: 「第 3 张」 is what AGE calls it too.
            return "第 %d 张通行表" % (rec["index"] + 1)
        if table == "colour":
            zh = _colour_zh(rec["index"])
            return zh or ("颜色 %d" % rec["index"])
        if table == "civ":
            # A civ names itself (`British`, `Aztecs`), and the game's own
            # Chinese name for it is one lookup away -- `civnames.chinese` takes
            # all three spellings the game uses.  Gaia is not a playable civ and
            # comes back as `Gaia`, which is what the file calls it too.
            from aoe2mod.game import civnames as CN
            zh = CN.chinese(rec.get("civ_name") or "")
            return zh or ("第 %d 号文明" % rec["index"])
        if table == "effect":
            r = P.Reader(raw, P.GV_C32 if gv is None else gv)
            r.pos = rec["start"]
            _m, name = r.debug_string()
            return (name or "").strip()
        if table == "sound":
            r = P.Reader(raw, P.GV_C32 if gv is None else gv)
            r.pos = rec["start"]
            r.i16()                                    # id
            r.i16()                                    # play_delay
            n = r.i16()                                # file_count
            if n <= 0:
                return ""
            r.i32()                                    # cache_time
            r.i16()                                    # total_probability
            _m, name = r.debug_string()
            return (name or "").strip()
        if table == "map":
            return "地图块标量"
        if table == "tail":
            i = rec.get("index")
            if isinstance(i, int) and 0 <= i < len(_TAIL_FIELDS):
                return _TAIL_FIELDS[i][1]
            return "全局数值 %s" % (i,)
        if table == "techtree":
            who = {"age": "时代", "building": "建筑",
                   "unit": "单位", "research": "科技"}.get(
                       rec.get("kind"), "连线")
            return "%s %s" % (who, rec.get("id"))
        r = P.Reader(raw, P.GV_C32 if gv is None else gv)
        r.pos = rec["start"]
        _m, name = r.debug_string()
        return (name or "").strip()
    except Exception:                                  # noqa: BLE001
        # A picker row with no label is a smaller failure than a route that
        # raises for 20,883 records; the rest of the walk is unaffected.
        return ""


def fields_at(raw, gv, rec, table="graphic"):
    """`{name: {"offset","kind","value"}}` for one record, decoded on demand."""
    if table == "effect":
        return _effect_fields(raw, rec)
    if table == "sound":
        return _sound_fields(raw, rec)
    if table == "terrain":
        return _terrain_fields(raw, gv, rec)
    if table == "restriction":
        return _restriction_fields(raw, gv, rec)
    if table == "colour":
        return _colour_fields(raw, gv, rec)
    if table == "task":
        return _task_fields(raw, gv, rec)
    if table == "civ":
        return _civ_fields(raw, gv, rec)
    if table == "map":
        r = P.Reader(raw, P.GV_C32 if gv is None else gv)
        r.pos = rec["start"]
        return _terrain_block_tail(r, True)
    if table == "tail":
        i = rec["index"]
        name = _TAIL_FIELDS[i][0]
        return {name: {"offset": rec["start"], "kind": "i32",
                       "value": struct.unpack_from("<i", raw,
                                                   rec["start"])[0]}}
    if table == "techtree":
        # Re-read this one record from its own start.  550 records cost 1 ms,
        # and it keeps ONE walker instead of a second, derived copy of four
        # layouts.
        rr = P.Reader(raw, P.GV_C32 if gv is None else gv)
        rr.pos = rec["start"]
        _ident, flds = _techtree_record(rr, True,
                                        rec.get("kind") or "unit")
        return flds
    base = _strings_end(raw, rec["start"])
    out = {}
    for name, kind, off in _GRAPHIC_TAIL:
        out[name] = {"offset": base + off, "kind": kind,
                     "value": struct.unpack_from(FMT[kind], raw,
                                                 base + off)[0]}
    # The three strings are reported, not writable: their 2-byte length prefix
    # makes a fixed-width write meaningless.  `kind == "str"` is what `plan()`
    # refuses on, so the refusal is one sentence and not a special case per
    # caller.
    r = P.Reader(raw, P.GV_C32 if gv is None else gv)
    r.pos = rec["start"]
    for i, name in enumerate(("Name", "FileName", "ParticleEffect")):
        pos = r.pos
        _marker, text = r.debug_string()
        out[name] = {"offset": pos, "kind": "str", "value": text}
    return out


def _strings_end(raw, start):
    """Byte offset just after a graphic record's three length-prefixed strings."""
    r = P.Reader(raw, P.GV_C32)
    r.pos = start
    for _ in range(3):
        r.debug_string()
    return r.pos


def _effect_fields(raw, rec):
    """Every number in one effect record, named the way the screen reads it.

    A record is a list of 11-byte commands, not a struct, so there is no fixed
    field name to show.  Each command becomes five fields: the four slots the
    game stores (`type/a/b/c`) and the number `d`.  Only `d` is writable, and
    whether it is writable at all comes from ``compiler.effect_rows`` -- the same
    function the technology editor and the build path ask.  Re-deciding it here
    would let this screen offer an edit the build then refuses, which is the
    divergence this project has already paid for three times.

    The row's own label (`平民 生命值`) is carried onto the field so a list of
    five numbers per command still says what each one does.
    """
    from aoe2mod.intent import compiler as C
    from aoe2mod.game import effectlabels as EL

    r = P.Reader(raw, P.GV_C32)
    r.pos = rec["start"]
    _m, name = r.debug_string()
    _count_at = r.pos                          # the i16 that says how many follow
    n = r.i16()
    cmds = []
    for _ in range(n):
        at = r.pos                             # u8 type, then a/b/c as i16
        t = r.u8()
        a = r.i16()
        b = r.i16()
        c = r.i16()
        d = r.f32()
        cmds.append({"type": t, "a": a, "b": b, "c": c, "d": d,
                     "_at": at, "_off_d": at + 7})
        r.pos = at + 11
    out = {"Name": {"offset": rec["start"], "kind": "str", "value": name or ""},
           "CommandCount": {"offset": _count_at, "kind": "i16", "value": n}}
    fake = {"effect_id": 0, "name": name or ""}
    try:
        rows = C.effect_rows([{"name": name or "", "commands": cmds}], fake)
    except Exception:                                  # noqa: BLE001
        rows = []
    _cls_zh = ((C.load_effect_tables().get("zh") or {}).get("classes") or {})
    # Slot name -> (offset within the command, kind).  `d` is the one at +7
    # because a u8 plus three i16 come before it; getting this wrong points a
    # read-only display at a neighbour's bytes, and the offsets are what the
    # screen shows as `offset`.
    _SLOT_AT = (("type", 0, "u8", "类型"), ("a", 1, "i16", "参数1"),
                ("b", 3, "i16", "参数2"), ("c", 5, "i16", "参数3"))
    for i, cmd in enumerate(cmds):
        row = rows[i] if i < len(rows) else {}
        label = EL.row_label(row, class_zh=_cls_zh) if row else ""
        head = ("第 %d 条：%s" % (i + 1, label)) if label else ("第 %d 条" % (i + 1))
        for slot, rel, kind, zh in _SLOT_AT:
            out["#%d.%s" % (i, slot)] = {
                "offset": cmd["_at"] + rel, "kind": kind,
                "value": cmd[slot], "label": "%s · %s" % (head, zh)}
        _slot_d = _SLOT_META["d"]
        out["#%d.d" % (i,)] = {
            "offset": cmd["_off_d"], "kind": "f32",
            "value": (row.get("value") if row else cmd["d"]),
            "label": "%s · %s" % (head, _slot_d["zh"]),
            # Writing d re-encodes it when the attribute is packed (8/9): the low
            # byte is the number, the high byte is the class the command is aimed
            # at.  Dropping the high byte would silently retarget the command.
            "_packed": bool(row.get("packed_class") is not None),
            "_raw_d": cmd["d"],
            "_c": cmd["c"],
            "_reason": (None if row.get("editable") else
                        (row.get("reason") or "这条命令的这几个参数各有各的用处，"
                                              "这里没有可以改的数字。"))}
    return out


_COLOUR_NAMES = ("ID", "MinimapColour", "PlayerColorBase", "UnitOutlineColor",
                 "UnitSelectionColor1", "UnitSelectionColor2", "MinimapColor2",
                 "MinimapColor3", "StatisticsText")

_COLOUR_ZH = ("颜色编号", "小地图颜色", "队伍色基色", "单位轮廓色",
              "选中色 1", "选中色 2", "小地图副色", "小地图副色 2",
              "统计文字颜色")

_TERRAIN_KIND = dict(_TERRAIN_NAMES)
_TERRAIN_KIND.update({"overlay_mask_name": "str", "phantom": "i16",
                      "passable_terrain": "u8", "impassable_terrain": "u8",
                      "is_animated": "u8"})


def _terrain_fields(raw, gv, rec):
    """`{AGE name: {"offset","kind","value"}}` for one terrain record."""
    r = P.Reader(raw, P.GV_C32 if gv is None else gv)
    r.pos = rec["start"]
    got = _walk_terrain(r, True)
    out = {}
    for key, (off, kind, val) in got.items():
        name = _TERRAIN_LABEL.get(key, key)
        out[name] = {"offset": off, "kind": kind, "value": val}
    return out


def _restriction_slots(rec):
    """How many terrains one restriction record covers.

    Derived from the record's own measured width (20 bytes per terrain: one
    float of damage multiplier plus a 16-byte pass graphic) rather than from a
    constant, because the count lives in the file and a hard-coded 134 would
    silently mis-slice a dat from a different game version.  The first version
    of this function asked `parser` for a constant that does not exist and the
    whole table refused to open, which is the failure mode to keep: an
    `AttributeError` on screen beats a read of 134 misaligned floats.
    """
    width = rec["end"] - rec["start"]
    slots = width // 20
    return slots if slots > 0 else 134


def _restriction_fields(raw, gv, rec):
    """134 damage multipliers + 134 pass graphics, both named by terrain index."""
    base = rec["start"]
    out = {}
    r = P.Reader(raw, P.GV_C32 if gv is None else gv)
    r.pos = base
    mult = r.f32_array(_restriction_slots(rec))
    for i, v in enumerate(mult):
        out["Mult.%d" % i] = {"offset": base + 4 * i, "kind": "f32", "value": v}
    pos = base + 4 * len(mult)
    for i in range(len(mult)):
        exit_id = struct.unpack_from("<i", raw, pos)[0]
        enter_id = struct.unpack_from("<i", raw, pos + 4)[0]
        walk_id = struct.unpack_from("<i", raw, pos + 8)[0]
        rate = struct.unpack_from("<f", raw, pos + 12)[0]
        out["Pass.%d.Exit" % i] = {"offset": pos, "kind": "i32", "value": exit_id}
        out["Pass.%d.Enter" % i] = {"offset": pos + 4, "kind": "i32",
                                    "value": enter_id}
        out["Pass.%d.Walk" % i] = {"offset": pos + 8, "kind": "i32",
                                   "value": walk_id}
        out["Pass.%d.Rate" % i] = {"offset": pos + 12, "kind": "f32",
                                   "value": rate}
        pos += 16
    return out


def _colour_fields(raw, gv, rec):
    base = rec["start"]
    out = {}
    for i, name in enumerate(_COLOUR_NAMES):
        out[name] = {"offset": base + 4 * i, "kind": "i32",
                     "value": struct.unpack_from("<i", raw, base + 4 * i)[0]}
    return out


def _sound_fields(raw, rec):
    """The five scalars of a sound record, plus how many files it names."""
    r = P.Reader(raw, P.GV_C32)
    r.pos = rec["start"]
    out = {}
    p = r.pos
    out["ID"] = {"offset": p, "kind": "i16", "value": r.i16()}
    p = r.pos
    out["PlayDelay"] = {"offset": p, "kind": "i16", "value": r.i16()}
    p = r.pos
    n = r.i16()
    out["FileCount"] = {"offset": p, "kind": "i16", "value": n}
    p = r.pos
    out["CacheTime"] = {"offset": p, "kind": "i32", "value": r.i32()}
    p = r.pos
    out["TotalProbability"] = {"offset": p, "kind": "i16", "value": r.i16()}
    return out


def _scan_tasks(raw, gv, start, end):
    """`(records, leftover)` where each record is ONE task, not one header.

    The header is only a container: 1,213 of the 1,701 headers hold no tasks at
    all, and a picker listing them would be 71% rows a player can only stare at.
    A task is the thing with numbers in it, so a task is a record.

    The walk counts headers from `unit_header_count` and reads each header's own
    task count, which is the only way to stay in step: an absent header is a
    single byte, so assuming a fixed stride would desynchronise on the first one.
    """
    slots = task_slots(gv)
    width = max(off + KINDS[kind] for _n, kind, off in slots)
    r = P.Reader(raw, P.GV_C32 if gv is None else gv)
    r.pos = start
    headers = r.i32()
    out = []
    for h in range(headers):
        if not r.u8():
            continue
        n = r.i16()
        for k in range(n):
            at = r.pos
            action = struct.unpack_from("<h", raw, at + 5)[0]
            out.append({"index": len(out), "start": at, "end": at + width,
                        "unit": h, "task": k, "action": action})
            r.pos = at + width
    return out, end - r.pos


def _task_fields(raw, gv, rec):
    """`{name: {"offset","kind","value"}}` for one task, decoded on demand."""
    out = {}
    base = rec["start"]
    for name, kind, off in task_slots(gv):
        o = base + off
        out[name] = {"offset": o, "kind": kind,
                     "value": struct.unpack_from(FMT[kind], raw, o)[0]}
        if name == "ActionType":
            zh = ACTION_ZH.get(out[name]["value"])
            if zh:
                out[name]["label"] = "动作：%s" % zh
    return out


def plan(table, raw, gv, rec, name, value):
    """May this value be written to this field?  Pack it if so.

    Same four refusals as `fieldwrite.plan`, and for the same reasons -- a typo
    must not resolve to a neighbour, a read-only count must not be moved, a
    string cannot be rewritten at a fixed width, and a value outside the byte
    width is the neighbouring field rather than a clamp.
    """
    where = TABLE_ZH.get(table, "这条记录")
    flds = fields_at(raw, gv, rec, table=table)
    f = flds.get(name)
    if f is None:
        close = [k for k in flds if name.lower() in k.lower()][:6]
        return {"ok": False, "error": "%s里没有叫 %s 的字段" % (where, name),
                "did_you_mean": close}
    meta = meta_for(table, name)
    label = meta.get("zh") or f.get("label") or name
    if f.get("_reason"):
        return {"ok": False, "error": "「%s」改不了：%s" % (name, f["_reason"])}
    if meta.get("ro"):
        return {"ok": False,
                "error": "「%s」是只读的：%s"
                         % (label, meta.get("hint") or "改它会让整条记录读不下去。")}
    fkind = f["kind"]
    if fkind == "str":
        return {"ok": False,
                "error": "「%s」是字符串（前面带字节数），不能用定宽方式改写："
                         "改短会留下残字、改长会覆盖下一个字段。"
                         "要换图请改「图形文件编号」。" % (label,)}
    old = f["value"]
    try:
        new = float(value) if fkind == "f32" else int(value)
    except (TypeError, ValueError):
        return {"ok": False,
                "error": "%s 要填%s，收到的是 %r"
                         % (label, "小数" if fkind == "f32" else "整数", value)}
    if f.get("_packed"):
        # Armour/attack numbers live in the LOW BYTE of the stored float, with the
        # target class in the high byte.  So the legal range is 0..255 (an
        # unsigned byte, not a float), and the value actually written has to carry
        # the class through -- `encode_effect_value` is the only function that
        # knows that, and the technology editor already shares it.
        from aoe2mod.intent import compiler as C
        if float(new) != int(new) or not (0 <= int(new) <= 255):
            return {"ok": False,
                    "error": "「%s」被压进一个字节里，只能是 0..255 的整数"
                             "（收到的是 %s）" % (label, new)}
        packed64 = float(C.encode_effect_value(f["_c"], f["_raw_d"], int(new)))
        if int(new) == int(old):
            return {"ok": False, "error": "值没变，还是 %s" % (old,),
                    "unchanged": True}
        packed = struct.pack("<f", packed64)
        off = f["offset"]
        before = bytes(raw[off:off + 4])
        return {"ok": True, "field": name, "label": label, "kind": fkind,
                "offset": off, "before": old, "value": int(new), "packed": packed,
                "before_bytes": before,
                "changed": sum(1 for a, b in zip(before, packed) if a != b)}
    W = WIDTH.get(fkind)
    if W and not (W[0] <= new <= W[1]):
        return {"ok": False,
                "error": "「%s」在文件里只占 %s，装不下 %s（范围 %s..%s）"
                         % (label, fkind, new, W[0], W[1])}
    if "lo" in meta and new < meta["lo"]:
        return {"ok": False, "error": "%s 不能小于 %s（%s）"
                % (label, meta["lo"], meta.get("hint") or "这是引擎里合理的下限")}
    if "hi" in meta and new > meta["hi"]:
        return {"ok": False, "error": "%s 不能大于 %s（%s）"
                % (label, meta["hi"], meta.get("hint") or "这是引擎里合理的上限")}
    same = (new == old) if fkind == "f32" else (int(new) == old)
    if same:
        return {"ok": False, "error": "值没变，还是 %s" % (old,), "unchanged": True}
    packed = struct.pack(FMT[fkind], new)
    off = f["offset"]
    before = bytes(raw[off:off + len(packed)])
    return {"ok": True, "field": name, "label": label, "kind": fkind,
            "offset": off, "before": old, "value": new, "packed": packed,
            "before_bytes": before,
            "changed": sum(1 for a, b in zip(before, packed) if a != b)}


def apply(buf, offset, packed):
    """Put `packed` at `offset`; return how many bytes actually changed."""
    before = bytes(buf[offset:offset + len(packed)])
    changed = sum(1 for a, b in zip(before, packed) if a != b)
    if changed:
        buf[offset:offset + len(packed)] = packed
    return {"before_bytes": before, "changed": changed}
