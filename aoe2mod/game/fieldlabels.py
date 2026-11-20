# -*- coding: utf-8 -*-
"""What a unit field *means*, in Chinese, and what you may type into it.

WHY THIS FILE EXISTS
--------------------
`aoe2mod/dat/unitfields.py` can already point at all 190 fields of a unit and
read the value there.  That is enough for a hex editor and useless for a person:
`Type50.DisplayedAttack` is not a phrase anyone says, and `Creatable.ChargeType`
tells you nothing about what 0 and 1 do.

AGE has the same problem and solves it in the worst possible way: it prints the
raw field name in a flat 85-row list, in the order the struct happens to be laid
out, with the GameVersion branches interleaved.  You have to already know AoE2
data editing to find anything, and knowing whether 25 is a sane HitPoints is on
you.  This module is the part that makes the tool *easier than AGE* rather than
merely equal to it:

  * a Chinese label for every field worth touching,
  * the group it belongs to (战斗/生产/移动/图形…), so the UI can split 190 rows
    into seven screens instead of one wall,
  * the meaning of enum integers (`Class` 6 -> 步兵), and
  * the sane range and unit, so the form can refuse "-5 生命值" before it writes
    93 MB and ships a broken mod.

FIELDS NOT LISTED HERE
----------------------
Fall back to the raw name and an "unknown" group: the long tail (Wwise IDs,
scenario triggers, tooltip string ids) is real data that a modder occasionally
needs, and hiding it would be a lie about coverage.  The UI shows them under
"其他字段" with the technical name -- exactly the thing AGE does for everything,
done only for the 40% that deserves it.

RANGES ARE ADVICE, NOT A SANDBOX
--------------------------------
`lo`/`hi` here are what the *engine* behaves sanely with, not the storage limit:
HitPoints is an i16 (so -32768..32767 fits in the bytes) but a health pool of
-3 is a bug you can only debug by crashing the game.  The server checks these;
the raw byte width is checked separately and always.
"""

from __future__ import annotations

# Groups, in the order the editor shows them.  A player opens this file to change
# a fight or a price far more often than a scenario trigger id, so 基础 and 战斗
# lead; 其他字段 closes.
GROUPS = [
    ("basic", "基础"),
    ("combat", "战斗"),
    ("move", "移动与视野"),
    ("produce", "生产与造价"),
    ("task", "任务与行为"),
    ("projectile", "投射物与蓄力"),
    ("build", "建造"),
    ("corpse", "尸体与采集物"),
    ("graphic", "图形与音效"),
    ("misc", "其他字段"),
]

GROUP_ZH = dict(GROUPS)

# The 18 unit classes AoE2 actually ships, in Chinese.  Kept here rather than read
# from `_golden` because the page needs it before any file is parsed.
UNIT_CLASS_ZH = {
    0: "弓箭手", 1: "神器", 2: "贸易船", 3: "建筑", 4: "平民", 5: "海鱼",
    6: "步兵", 7: "浆果丛", 8: "石矿", 9: "猎物", 10: "掠食动物",
    11: "其他", 12: "骑兵", 13: "攻城武器", 14: "地形", 15: "树",
    16: "树桩", 17: "治疗者", 18: "牧师", 19: "贸易车", 20: "运输船",
    21: "渔船", 22: "战舰", 23: "战车弓手", 24: "战象", 25: "英雄",
    26: "象弓手", 27: "墙", 28: "方阵兵", 29: "家畜", 30: "旗帜",
    31: "深海鱼", 32: "金矿", 33: "岸边鱼", 34: "悬崖", 35: "火枪兵",
    36: "骑射手", 37: "分身", 38: "鸟", 39: "投石手", 40: "残骸",
    41: "资源堆", 42: "圣物", 43: "持圣物的僧侣", 44: "手炮兵",
    45: "双手剑士", 46: "长枪兵", 47: "侦察兵", 48: "矿脉", 49: "农田",
    50: "矛兵", 51: "打包单位", 52: "塔", 53: "登船", 54: "展开的攻城器",
    55: "弩炮", 56: "突袭者", 57: "骑兵突袭者", 58: "牲畜",
}

# A field's entry:
#   zh     Chinese label shown in the form
#   group  one of GROUPS' keys
#   hint   one sentence: what changes when you change this
#   lo/hi  sane bounds (inclusive); omitted means "the byte width only"
#   step   input step for the spinner
#   enum   {int: "中文"} when the number is a name
#   ro     True -> read-only (strings and their length prefixes)
BOOL = {0: "否", 1: "是"}

# ---------------------------------------------------------------------------
# Enums.  Every one of these is a table the逆向 already carries (AGE3NamesV0007.ini,
# dat-enums.json, ui-lists.json) -- the numbers were never the problem, the
# naming was.  A player reading 「29」 for 攻击类别 has to memorise a table; the
# same row reading 「鹰勇士」 is the thing they came to change.
#
# Values the shipped file stores that no table names are LEFT OUT on purpose:
# `ui/server.py` prints `#37` for those, and 37 really is an unnamed class in
# DE's data.  Inventing a word for it would be a wrong answer with a lookup
# behind it.
# ---------------------------------------------------------------------------

# 攻击 / 护甲类别。Order and wording from `AoE2DEArmorNames` in AGE3NamesV0007.ini,
# which is the same list AGE shows.
ATK_CLASS_ZH = {
    0: "未用", 1: "步兵", 2: "龟船", 3: "基础穿刺", 4: "基础近战",
    5: "战象", 6: "未用", 7: "未用", 8: "骑兵", 9: "未用",
    10: "未用", 11: "所有建筑（港除外）", 12: "未用", 13: "石墙/城门/塔",
    14: "掠食动物", 15: "弓箭手", 16: "船只与自爆单位",
    17: "冲车/投石机/攻城塔", 18: "树", 19: "特色单位（龟船除外）",
    20: "攻城武器", 21: "标准建筑", 22: "墙与城门", 23: "火药单位",
    24: "被猎的掠食动物", 25: "僧侣", 26: "城堡", 27: "长枪兵",
    28: "骑射手", 29: "鹰勇士", 30: "骆驼", 31: "立陶宛 Leitis",
    32: "佣兵队长", 33: "未用", 34: "渔船", 35: "马穆鲁克", 36: "英雄",
}

# 单位任务的动作类型。`ui-lists.json` idx 6 (func 0x0007da40) 的 53 条里有 5 个
# 重号（2/13/14/150/151 各有两个含义），这里取后来那个 -- 也就是 DE 实际在用的。
ACTION_ZH = {
    0: "无", 1: "移动", 2: "跟随", 3: "驻守", 4: "探索",
    5: "采集/重建", 6: "删除（吃草）", 7: "战斗", 8: "射击", 9: "攻击",
    10: "飞走", 11: "删除（受惊/被猎）", 12: "卸货（船只）", 13: "护卫",
    14: "隔墙卸货", 20: "删除（逃离）", 21: "生产",
    101: "建造", 102: "生产单位", 103: "研究科技", 104: "转化", 105: "治疗",
    106: "修理", 107: "被自动转化", 108: "发现神器", 109: "删除",
    110: "狩猎", 111: "贸易", 120: "产生奇观胜利",
    121: "被指派后取消选择（农田）", 122: "拾取（采集）", 123: "居住",
    124: "打包", 125: "展开并攻击", 130: "删除", 131: "地图外贸易",
    132: "拾起单位", 133: "冲锋攻击", 134: "变形单位", 135: "绑架单位",
    136: "卸载单位", 149: "剪羊毛", 150: "再生", 151: "大商站能力",
    152: "移动伤害", 153: "可移动投放点", 154: "拾取", 155: "光环",
}

# 任务能打谁。AGE 的原话是「0,7+ All objects / 1 Your objects only / 2 Neutral
# and enemy only / 3 Gaia only / 4 Gaia,your,ally / 5 Gaia,neutral,enemy /
# 6 All but your」-- 另一套编号，和「自己/盟友/中立/敌人」那种外交序不是一回事。
TARGET_DIPLO_ZH = {
    0: "所有对象", 1: "只打自己的", 2: "中立与敌人", 3: "只打 Gaia",
    4: "Gaia/自己/盟友", 5: "Gaia/中立/敌人", 6: "除自己以外全部",
    7: "所有对象",
}

FOG_ZH = {0: "不可见", 1: "始终可见", 2: "活着时可见", 3: "反相可见",
          4: "检查分身"}

OBSTRUCT_ZH = {0: "用默认", 1: "资源", 2: "单位", 3: "建筑", 4: "墙",
               5: "城门（可穿行）", 6: "悬崖（挡住围墙）"}

# AGE 把这个字段叫 Select Level，不是「交互模式」的字面意思。
INTERACTION_ZH = {0: "无交互", 1: "可点选对象",
                  2: "资源（可选，不能攻击或移动）",
                  3: "建筑（可选可攻击，不能移动）",
                  4: "单位（可选可攻击可移动）"}

# AGE 叫 Draw Level：小地图上画不画点、画什么点。
DRAWMAP_ZH = {0: "不画点", 1: "单位（方块点，选中变白）",
              2: "建筑（菱形点）", 3: "地形（菱形，保持本色）",
              4: "地形（更大的点）"}

# 血条。DE 把这一列当「有没有血条 / 有没有轮廓」用。
HPBAR_ZH = {0: "有血条", 1: "血条＋轮廓", 2: "都没有", 3: "只有轮廓"}

APPLY_MODE_ZH = {0: "叠加（着火的建筑）", 1: "随机叠加",
                 2: "替换图形（损坏的墙）"}

UNDEAD_ZH = {0: "默认", 1: "图形停在最高海拔", 2: "不受海拔影响"}

CANBUILD_ZH = {0: "否", 1: "是", 2: "在场景编辑器「其他」页显示"}

FLY_ZH = {0: "贴地", 1: "图形抬高（浮空）"}

# 任务的 Enabled 不是布尔：−1 是「无条件启用」，填资源槽号就变成条件启用。
TASK_ENABLED_ZH = {-1: "启用"}

# 造价 / 资源槽里出现的资源编号。只收这个文件真会出现的那些槽；601 个槽里
# 大半是「游戏没有给名字」，把它们全塞进下拉框只会把有用的那几行埋掉。
RES_SLOT_ZH = {
    -1: "空位",
    0: "食物", 1: "木材", 2: "石头", 3: "黄金", 4: "人口上限",
    9: "贸易货物", 11: "当前人口", 12: "尸体腐烂时间", 14: "已捕获遗迹",
    15: "肉类", 16: "浆果", 17: "鱼肉", 19: "单位总数", 32: "额外人口上限",
    56: "矿石", 214: "钦察佣兵数量", 215: "钦察佣兵上限",
    182: "建筑转化概率", 213: "掠夺效率", 219: "捕鱼效率",
    274: "步兵击杀奖励", 284: "骑兵击杀奖励",
    506: "未用（新版本追加）", 515: "未用（新版本追加）",
    520: "未用（新版本追加）", 550: "未用（新版本追加）",
}

FIELD_META = {
    # ---- 基础 -------------------------------------------------------------
    "Type": dict(zh="单位类型码", group="basic",
                 hint="决定这条记录按哪种结构解析：70 是可生产单位，80 是建筑，90 是森林。改它会改变整条记录的读法，不要动。",
                 ro=True),
    "ID": dict(zh="单位编号", group="basic",
               hint="这条记录在文明单位表里的位置。改它等于换一条记录。", ro=True),
    "Class": dict(zh="兵种类别", group="basic", enum=UNIT_CLASS_ZH,
                  hint="游戏用它决定谁能打谁、算什么兵。和「攻击加成」配合才有意义。"),
    "LanguageDLLName": dict(zh="名称文本编号", group="basic", soft=True,
                            hint="指向界面文本表里的名字。改它不会改名字，只会指错——"
                                 "要改显示的名请点记录上方的「改名字」，它会新分配一个"
                                 "文本编号（共用的那个不能动：编号 5079 是 57 条记录的名字）。"),
    "LanguageDLLCreation": dict(zh="创建文本编号", group="basic", soft=True,
                                hint="指向界面文本表里的「正在创建」提示。"),
    "HitPoints": dict(zh="生命值", group="basic", lo=0, hi=100000, step=1,
                      hint="单位的血量上限。改这一项就是最常见的「变肉」。"),
    "GarrisonCapacity": dict(zh="驻军容量", group="basic", lo=0, hi=255,
                             hint="能装进多少单位：城镇中心、城堡、运输船都靠它。"),
    "LineOfSight": dict(zh="视野", group="move", lo=0, hi=100, step=0.5,
                        hint="能看多远，单位是格。"),
    "SortNumber": dict(zh="排序号", group="basic", lo=0, hi=255,
                       hint="生产列表里的先后顺序。"),
    "IconID": dict(zh="图标编号", group="graphic", lo=-1, hi=32767,
                   hint="单位在按钮上显示的图标。-1 表示没设。"),
    "HideInEditor": dict(zh="编辑器里隐藏", group="basic", enum=BOOL,
                         hint="勾上之后场景编辑器里就找不到它了。"),
    "Enabled": dict(zh="已启用", group="basic", enum=BOOL,
                    hint="关掉等于这条记录不存在。"),
    "Disabled": dict(zh="已禁用", group="basic", enum=BOOL,
                     hint="反向开关，部分旧数据靠它下线单位。"),
    "CanBeBuiltOn": dict(zh="可建在其上", group="build", enum=CANBUILD_ZH,
                         hint="别的建筑能不能盖在它上面。"),
    "UndeadMode": dict(zh="亡灵模式", group="basic", enum=UNDEAD_ZH,
                       hint="死后不消失，用来做复活类单位。"),
    "UndeadGraphic": dict(zh="亡灵图形", group="graphic", lo=-1, hi=32767,
                          hint="亡灵模式下的站姿图形。"),
    "StandingGraphic.0": dict(zh="站姿图形", group="graphic", lo=-1, hi=32767,
                              hint="单位静止时播放的图形编号。"),
    "DyingGraphic": dict(zh="死亡图形", group="graphic", lo=-1, hi=32767,
                         hint="死亡动画。"),
    "CopyID": dict(zh="复制源编号", group="basic", lo=-1, hi=32767,
                   hint="显示用：这是从哪个单位复制来的。"),
    "BaseID": dict(zh="基准编号", group="basic", lo=-1, hi=32767,
                   hint="显示用：这条记录的原始出处。"),
    "Nothing": dict(zh="保留位", group="misc", ro=True,
                    hint="名字就叫 Nothing —— 数据里一个没用上的字段。"),
    "Trait": dict(zh="特性", group="basic", lo=0, hi=255, hint="单位的特性位标记，比如能不能被招降、算不算建筑。按位组合，改之前对照原版单位。"),
    "Civilization": dict(zh="文明编号", group="basic", lo=0, hi=255,
                         hint="这条记录属于哪个文明。全部改掉会让所有文明都拿同一份。"),

    # ---- 移动与视野 --------------------------------------------------------
    "Speed": dict(zh="移动速度", group="move", lo=0, hi=20, step=0.05,
                  hint="村民是 0.96，骑兵大约 1.5。填 0 就是不会动。"),
    "CollisionSize.0": dict(zh="体积 X", group="move", lo=0, hi=20, step=0.05,
                            hint="碰撞体积的横向半径。"),
    "CollisionSize.1": dict(zh="体积 Y", group="move", lo=0, hi=20, step=0.05, hint="碰撞体积的第二个横向半径（前后方向）。多数单位 X 和 Y 填同一个值，改的时候两个一起改，不然单位会被挤成扁的。"),
    "CollisionSize.2": dict(zh="体积 Z", group="move", lo=0, hi=20, step=0.05, hint="碰撞体积的高度。影响投射物能不能越过它、也影响选中框贴不贴合地形。"),
    "ClearanceSize.0": dict(zh="通行宽度 X", group="move", lo=0, hi=20, step=0.05,
                            hint="能不能从两个单位之间挤过去。"),
    "ClearanceSize.1": dict(zh="通行宽度 Y", group="move", lo=0, hi=20, step=0.05, hint="通行宽度的纵向尺寸。单位挤过窄口时，X 和 Y 一起跟地形和邻居的碰撞体比较。"),
    "OutlineSize.0": dict(zh="选择框宽 X", group="move", lo=0, hi=20, step=0.05,
                          hint="选中时框多大。"),
    "OutlineSize.1": dict(zh="选择框宽 Y", group="move", lo=0, hi=20, step=0.05, hint="选择框的纵向尺寸，和「选择框宽 X」一起决定框的长宽比例。"),
    "OutlineSize.2": dict(zh="选择框高 Z", group="move", lo=0, hi=20, step=0.05, hint="选择框的高度，影响选中时框往上撑多高，平地单位一般保持原值。"),
    "FogVisibility": dict(zh="战争迷雾可见", group="move", enum=FOG_ZH, hint="1 = 能看穿战争迷雾，侦察兵和建筑视野就是靠它；0 = 正常受迷雾限制。"),
    "TerrainRestriction": dict(zh="地形限制组", group="move", lo=0, hi=255,
                               hint="能走哪些地形，指向地形限制表。"),
    "FlyMode": dict(zh="飞行模式", group="move", enum=FLY_ZH,
                     hint="0 贴地：影子贴在地上；1 抬高：图形画在影子上面，"
                          "看起来像浮在空中。"),
    "HillMode": dict(zh="坡地模式", group="move", lo=0, hi=255,
                     hint="AGE 的字段表把这一列指到「刷怪区内的随机位置」那组枚举上，"
                          "但 AoE2 里 12 万个单位写 0、1.4 万写 3、2 千写 2，"
                          "那组枚举解释不了这个分布 —— 这里不猜，只标出范围。"),
    "OcclusionMode": dict(zh="遮挡模式", group="move", lo=0, hi=255,
                          hint="单位被建筑或树挡住时还画不画、画成什么样。"
                               "AGE 没给这一列出枚举表，游戏里 0 到 11 都有单位在写，"
                               "具体每个值画成什么样没有权威说明 —— 这里不猜。"),
    "ObstructionType": dict(zh="阻挡类型", group="move", enum=OBSTRUCT_ZH, hint="阻挡的具体类型：0 = 不阻挡，其余按原版数值填，填错单位会直接穿过建筑。"),
    "ObstructionClass": dict(zh="阻挡类别", group="move", lo=0, hi=255, hint="寻路时它属于哪一类障碍，同类障碍会被合并成一片不可走的区域。"),
    "PlacementTerrain.0": dict(zh="放置地形", group="build", lo=-1, hi=32767,
                               hint="场景里能放在哪种地形上。"),
    "PlacementSideTerrain.0": dict(zh="侧边地形", group="build", lo=-1, hi=32767, hint="建筑放下时这一侧自动铺上的地形编号，-1 表示不铺。"),
    "MinCollisionSizeMultiplier": dict(zh="最小碰撞倍率", group="move", lo=0,
                                       hi=10, step=0.05,
                                       hint="特定情况下按这个系数缩放碰撞体大小。"),

    # ---- 战斗 --------------------------------------------------------------
    "Type50.BaseArmor": dict(zh="基础护甲值", group="combat", lo=0, hi=100000,
                             hint="10000 是「没设」的哨兵值。"),
    "Type50.AttacksCount": dict(zh="攻击条目数", group="combat", lo=0, hi=255,
                                ro=True,
                                hint="下面「攻击加成」有几行。行数由数据本身决定，不能在这里改。"),
    "Type50.ArmoursCount": dict(zh="护甲条目数", group="combat", lo=0, hi=255,
                                ro=True,
                                hint="下面「护甲」有几行。"),
    "Type50.DefenseTerrainBonus": dict(zh="地形防御加成", group="combat",
                                       lo=-1, hi=32767, hint="站在特定地形上时额外得到的防御值。"),
    "Type50.BonusDamageResistance": dict(zh="附加伤害抗性", group="combat",
                                         lo=0, hi=1000, step=0.05,
                                         hint="按攻击类别给出的减伤百分比。它和「附加伤害」是一对："
                                              "那边按类别加伤害，这边按同一套类别编号减伤害。"),
    "Type50.MaxRange": dict(zh="最大射程", group="combat", lo=0, hi=100,
                            step=0.5, hint="0 表示只能贴身打。"),
    "Type50.MinRange": dict(zh="最小射程", group="combat", lo=0, hi=100,
                            step=0.5, hint="近身就打不到了，攻城器常用。"),
    "Type50.ReloadTime": dict(zh="装填时间", group="combat", lo=0, hi=100,
                              step=0.1, hint="两次攻击之间要等多久，秒。"),
    "Type50.AccuracyPercent": dict(zh="命中率", group="combat", lo=0, hi=100,
                                   hint="弹道类单位的命中百分比。"),
    "Type50.AccuracyDispersion": dict(zh="散布", group="combat", lo=0, hi=100,
                                      step=0.1, hint="攻击落点的随机偏移，单位是格。0 是弹无虚发，越大越容易打偏。"),
    "Type50.BlastWidth": dict(zh="溅射范围", group="combat", lo=0, hi=20,
                              step=0.1, hint="打中之后波及多宽。"),
    "Type50.BlastAttackLevel": dict(zh="溅射等级", group="combat", lo=0, hi=255, hint="溅射能波及到多高等级的单位，只有等级不高于它的单位才会被溅射打到。"),
    "Type50.BlastDamage": dict(zh="溅射伤害倍率", group="combat", lo=0, hi=10,
                               step=0.05,
                               hint="范围伤害。正数是按基础攻击乘的比例；"
                                    "填负数则是固定伤害值。"),
    "Type50.FriendlyFireDamage": dict(zh="友伤倍率", group="combat", lo=0, hi=10,
                                      step=0.05, hint="1 是全额误伤，0 是完全不伤自己人。"),
    "Type50.DamageReflection": dict(zh="伤害反弹", group="combat", lo=0, hi=10,
                                    step=0.05,
                                    hint="打它的人自己要吃多少百分比的伤害。"),
    "Type50.BreakOffCombat": dict(zh="脱战", group="combat", lo=0, hi=255, hint="1 = 目标跑远了就放弃追击；0 = 一直追到底。"),
    "Type50.FrameDelay": dict(zh="出招延迟帧", group="combat", lo=-1, hi=32767, hint="攻击动画开始后第几帧才真正结算伤害，调大就是抬手变慢。"),
    "Type50.InterruptFrame": dict(zh="打断帧", group="combat", lo=-1, hi=32767,
                                  hint="齐射时允许它改追目标或重新起手的那一帧。"),
    "Type50.GarrisonFirepower": dict(zh="驻军火力", group="combat", lo=0, hi=100,
                                     step=0.1, hint="里面驻军时这座建筑打多疼。"),
    "Type50.ProjectileUnitID": dict(zh="投射物单位", group="projectile",
                                    lo=-1, hi=32767,
                                    hint="射出去的那个东西是哪条单位记录。"),
    "Type50.AttackGraphic": dict(zh="攻击图形", group="graphic", lo=-1, hi=32767, hint="攻击动作的图形编号，-1 表示用默认攻击动画。"),
    "Type50.AttackGraphic2": dict(zh="攻击图形 2", group="graphic", lo=-1,
                                  hi=32767, hint="第二种攻击动画的图形编号，给第二攻击模式用；-1 表示没有。"),
    "Type50.DisplayedMeleeArmour": dict(zh="显示近战护甲", group="combat",
                                        lo=0, hi=1000,
                                        hint="界面上写的近战护甲，和真实计算值是两处。"),
    "Type50.DisplayedAttack": dict(zh="显示攻击力", group="combat", lo=0, hi=1000,
                                   hint="界面上写的攻击力。真正生效的是「攻击加成」表。"),
    "Type50.DisplayedRange": dict(zh="显示射程", group="combat", lo=0, hi=100,
                                  step=0.5, hint="界面上显示的那个射程数字。它只管显示，真正能打多远看「射程」。"),
    "Type50.DisplayedReloadTime": dict(zh="显示装填", group="combat", lo=0, hi=100,
                                       step=0.1, hint="界面上显示的那个装填时间。它只管显示，真正的冷却看「装填时间」。"),
    "Type50.GraphicDisplacement.0": dict(zh="图形位移 X", group="graphic", lo=-10,
                                         hi=10, step=0.05, hint="画单位图形时相对锚点的偏移，单位是像素，三项依次是 X、Y、Z。"),
    "Type50.GraphicDisplacement.1": dict(zh="图形位移 Y", group="graphic", lo=-10,
                                         hi=10, step=0.05, hint="图形位移的纵向分量，单位是像素，正值往上偏、负值往下压。"),
    "Type50.GraphicDisplacement.2": dict(zh="图形位移 Z", group="graphic", lo=-10,
                                         hi=10, step=0.05, hint="图形位移的深度分量，一般保持 0，调大只会让图形离地浮起来。"),

    # ---- 生产与造价 --------------------------------------------------------
    "Creatable.TrainLocationsCount": dict(zh="训练条目数", group="produce",
                                          lo=0, hi=255, ro=True,
                                          hint="这个单位能在几个地方造。"),
    "Creatable.TrainLocations.0.TrainTime": dict(zh="训练时间", group="produce",
                                                 lo=0, hi=3600,
                                                 hint="多少秒造出来。"),
    "Creatable.TrainLocations.0.UnitID": dict(zh="生产建筑", group="produce",
                                              lo=-1, hi=32767, soft=True,
                                              hint="这个单位在哪个建筑里生产，填的是建筑编号：82 城堡、12 兵营、87 靶场。改它就是把这个兵种挪到别的建筑去造。"),
    "Creatable.TrainLocations.0.ButtonID": dict(zh="按钮格号", group="produce",
                                                lo=0, hi=24,
                                                hint="在建筑命令面板上排第几格。"),
    "Creatable.TrainLocations.0.HotKeyID": dict(zh="热键编号", group="produce",
                                                lo=-1, hi=32767,
                                                hint="在哪个建筑里生产它时用的热键位置，决定按钮排在建筑面板的第几格。"
                                                     "后面能印出键位的（Q 键、S 键）是游戏自带热键表里记着的；"
                                                     "只印数字的是那张表里没有这个编号，不是本工具没读到。"
                                                     "同一个键会挂很多编号，因为游戏为每个文明各存了一份。"),
    "Creatable.ResourceCosts.0.Type": dict(zh="造价类型 1", group="produce",
                                           enum=RES_SLOT_ZH,
                                           hint="指向资源表：0 食物 1 木材 2 石头 3 黄金，"
                                                "−1 是空位。顺序是资源表的顺序，不是"
                                                "「金在石前」的直觉顺序。"),
    "Creatable.ResourceCosts.0.Amount": dict(zh="造价数量 1", group="produce",
                                             lo=0, hi=32767, hint="这条造价要扣多少。和「造价类型」配对看：类型填食物、这里填 50，就是 50 食物。"),
    "Creatable.ResourceCosts.1.Type": dict(zh="造价类型 2", group="produce",
                                           enum=RES_SLOT_ZH, hint="第二条造价指向哪种资源：0 食物 1 木材 2 石头 3 黄金，−1 表示这个槽空着。"),
    "Creatable.ResourceCosts.1.Amount": dict(zh="造价数量 2", group="produce",
                                             lo=0, hi=32767, hint="第二条造价要扣多少。用法和「造价数量 1」一样，具体扣哪种资源看在「造价类型 2」里选了什么。"),
    "Creatable.ResourceCosts.2.Type": dict(zh="造价类型 3", group="produce",
                                           enum=RES_SLOT_ZH, hint="第三条造价指向哪种资源：0 食物 1 木材 2 石头 3 黄金，−1 表示这个槽空着。"),
    "Creatable.ResourceCosts.2.Amount": dict(zh="造价数量 3", group="produce",
                                             lo=0, hi=32767, hint="第三条造价要扣多少。用法和「造价数量 1」一样，具体扣哪种资源看在「造价类型 3」里选了什么。"),
    "Creatable.CreatableType": dict(zh="可生产类型", group="produce", lo=0, hi=255,
                                    ro=True,
                                    hint="255 是「无」。改它会改变下面整段结构的解释方式。"),
    "Creatable.RearAttackModifier": dict(zh="背后攻击加成", group="combat", lo=0,
                                         hi=10, step=0.05, hint="从背后打目标时的伤害倍率，1 表示没有加成。"),
    "Creatable.FlankAttackModifier": dict(zh="侧翼攻击加成", group="combat", lo=0,
                                          hi=10, step=0.05, hint="从侧面打目标时的伤害倍率，1 表示没有加成。"),
    "Creatable.HeroMode": dict(zh="英雄模式", group="produce", lo=0, hi=255,
                               hint="1 = 死了不复活，2 = 复活，3 = 倒地可救。"),
    "Creatable.DisplayedPierceArmour": dict(zh="显示远程护甲", group="combat",
                                            lo=0, hi=1000,
                                            hint="界面上写的远程护甲。1000 常表示哨兵值。"),
    "Creatable.AttackPriority": dict(zh="攻击优先级", group="combat", lo=0, hi=255, hint="同时有好几个目标可选时先打哪个，数值越大越优先。"),
    "Creatable.InvulnerabilityLevel": dict(zh="无敌等级", group="combat", lo=0,
                                           hi=10, step=0.05, hint="大于 0 时普通攻击打不动它，只有等级不低于它的攻击才生效；0 表示正常吃伤害。"),
    "Creatable.MinConversionTimeMod": dict(zh="招降时间下限修正", group="combat",
                                           lo=0, hi=10, step=0.05,
                                           hint="招降它最快能多快的乘数。"),
    "Creatable.MaxConversionTimeMod": dict(zh="招降时间上限修正", group="combat",
                                           lo=0, hi=10, step=0.05,
                                           hint="招降它最慢会拖多久的乘数。"),
    "Creatable.ConversionChanceMod": dict(zh="招降概率修正", group="combat", lo=0,
                                          hi=10, step=0.05,
                                          hint="招降成功率的乘数。"),
    "Creatable.ButtonIconID": dict(zh="按钮图标", group="graphic", lo=-1, hi=32767, hint="它在生产面板上的按钮图标编号，对应界面图标表里的一格。"),
    "Creatable.ButtonShortTooltipID": dict(zh="短提示文本号", group="graphic",
                                           lo=-1, hi=2147483647, soft=True,
                                           hint="长提示关掉时，这个按钮上显示的"
                                                "那句文本的编号。"),
    "Creatable.ButtonExtendedTooltipID": dict(zh="长提示文本号", group="graphic",
                                              lo=-1, hi=2147483647, soft=True,
                                              hint="长提示打开时，这个按钮上显示"
                                                   "的那句文本的编号。"),
    "Creatable.ButtonHotkeyAction": dict(zh="按钮热键动作", group="produce",
                                         lo=-1, hi=32767,
                                         hint="这个按钮绑的热键动作，在 "
                                              "button_action_list 里的编号。"),
    # ---- 投射物 ------------------------------------------------------------
    "Creatable.ChargeEvent": dict(zh="蓄力触发", group="projectile", lo=0, hi=255,
                                  hint="1 = 攻击动画放完时扣掉 1 点蓄力。"),
    "Creatable.ChargeType": dict(zh="蓄力类型", group="projectile", lo=0, hi=255, hint="蓄力机制的类别，0 表示不蓄力。非 0 的不同取值对应不同的充能方式，改之前先看原版同类单位用的是哪个值。"),
    "Creatable.ChargeTarget": dict(zh="蓄力目标", group="projectile", lo=-1,
                                   hi=32767,
                                   hint="填 -1 表示用当前主动技能选中的目标。"),
    "Creatable.ChargeProjectileUnit": dict(zh="蓄力投射物", group="projectile",
                                           lo=-1, hi=2147483647,
                                           hint="打出去用它自己的攻击数值，"
                                                "不吃本单位的攻击。"),
    "Creatable.MaxCharge": dict(zh="蓄力上限", group="projectile", lo=0, hi=100,
                                step=0.1, hint="最多能攒多少点蓄力，配合「充能速度」和「齐射」一起用。"),
    "Creatable.RechargeRate": dict(zh="充能速度", group="projectile", lo=0, hi=100,
                                   step=0.1, hint="每秒回复多少点蓄力；0 表示不回充。"),
    "Creatable.TotalProjectiles": dict(zh="齐射数量", group="projectile", lo=0,
                                       hi=100, step=0.5, hint="一次攻击打出几发子弹，1 是单发。多发时用「齐射散布」控制散开的范围。"),
    "Creatable.MaxTotalProjectiles": dict(zh="齐射上限", group="projectile", lo=0,
                                          hi=255, hint="一次攻击最多能打出几发子弹，和「齐射数量」配合用。"),
    "Creatable.ProjectileSpawningArea.0": dict(zh="齐射散布 X", group="projectile",
                                               lo=0, hi=20, step=0.1, hint="齐射时子弹相对瞄准点的散布范围，单位是格，三项依次是横向、纵向、高度。填 0 就是所有子弹打在同一点。"),
    "Creatable.ProjectileSpawningArea.1": dict(zh="齐射散布 Y", group="projectile",
                                               lo=0, hi=20, step=0.1, hint="齐射散布的纵向范围，单位是格。想只让子弹左右散就把它填 0。"),
    "Creatable.ProjectileSpawningArea.2": dict(zh="齐射散布 Z", group="projectile",
                                               lo=0, hi=20, step=0.1, hint="齐射散布的高度范围，单位是格。一般填 0，只有攻城类需要按高度分层落点。"),
    "Creatable.SecondaryProjectileUnit": dict(zh="副投射物", group="projectile",
                                              lo=-1, hi=2147483647, hint="主子弹之外额外打出的那种子弹用的单位编号，-1 表示没有。"),
    "Creatable.SpecialGraphic": dict(zh="特殊图形", group="graphic", lo=-1,
                                     hi=2147483647, hint="特殊能力发动时显示的图形编号，-1 表示不显示。"),
    "Creatable.SpecialAbility": dict(zh="特殊能力", group="projectile", lo=0,
                                     hi=255, hint="给单位挂的特殊能力编号，0 表示没有。具体含义随版本变，改之前对照原版同类单位。"),

    # ---- 建造 --------------------------------------------------------------
    "Creatable.GarrisonGraphic": dict(zh="驻军图形", group="graphic", lo=-1,
                                      hi=2147483647, hint="单位进驻到建筑或载具里时显示的图形编号，-1 表示不显示。"),
    "Creatable.SpawningGraphic": dict(zh="产出图形", group="graphic", lo=-1,
                                      hi=32767, hint="单位被生产出来那一瞬间播的图形编号，-1 表示不播。"),
    "Creatable.UpgradeGraphic": dict(zh="升级图形", group="graphic", lo=-1,
                                     hi=32767, hint="单位升级时播的图形编号（比如兵营升到城堡兵营），-1 表示不播。"),
    "Creatable.HeroGlowGraphic": dict(zh="英雄光环", group="graphic", lo=-1,
                                      hi=32767, hint="英雄单位脚底光环的图形编号，-1 表示没有光环。"),
    "Creatable.IdleAttackGraphic": dict(zh="待机攻击图形", group="graphic",
                                        lo=-1, hi=32767, hint="站着不动又刚打完一发时用的图形编号，-1 表示用普通待机图形。"),

    # ---- 图形音效 ----------------------------------------------------------
    "TrainSound": dict(zh="训练音效", group="graphic", lo=-1, hi=32767, hint="生产完成时播的音效编号，-1 表示不出声。"),
    "DamageSound": dict(zh="受伤音效", group="graphic", lo=-1, hi=32767, hint="被打中时的音效编号，-1 表示不出声。"),
    "SelectionSound": dict(zh="选中音效", group="graphic", lo=-1, hi=32767, hint="被选中时播的音效编号，-1 表示不出声。"),
    "DyingSound": dict(zh="死亡音效", group="graphic", lo=-1, hi=32767, hint="死亡时的音效编号，-1 表示不出声。"),
    "WwiseTrainSoundID": dict(zh="Wwise 训练音", group="graphic", lo=0,
                              hi=4294967295, soft=True, hint="训练完成音的 Wwise 事件编号；0 表示改用老的 .wav 音效。"),
    "WwiseDamageSoundID": dict(zh="Wwise 受伤音", group="graphic", lo=0,
                               hi=4294967295, soft=True, hint="受伤音的 Wwise 事件编号；0 表示改用老的 .wav 音效。"),
    "WwiseSelectionSoundID": dict(zh="Wwise 选中音", group="graphic", lo=0,
                                  hi=4294967295, soft=True, hint="选中音的 Wwise 事件编号；0 表示改用老的 .wav 音效。"),
    "WwiseDyingSoundID": dict(zh="Wwise 死亡音", group="graphic", lo=0,
                              hi=4294967295, soft=True, hint="死亡音的 Wwise 事件编号；0 表示改用老的 .wav 音效。"),
    "DeadUnitID": dict(zh="尸体单位", group="corpse", lo=-1, hi=32767,
                       hint="死后留下哪条记录当尸体。"),
    "BloodUnitID": dict(zh="血渍单位", group="corpse", lo=-1, hi=32767, hint="单位受伤时在地上留下的血渍用的单位编号，-1 表示不留。"),
    "SelectionEffect": dict(zh="血条样式", group="graphic", enum=HPBAR_ZH,
                            hint="AGE 把它叫 Selection Effect，实际画的是这个单位头顶"
                                 "那根条和选中时的轮廓。"),
    "EditorSelectionColour": dict(zh="编辑器选中颜色", group="graphic", lo=0,
                                  hi=255, hint="在地图编辑器里选中它时描边用的颜色编号。"),
    "ConvertTerrain": dict(zh="改造地形", group="build", lo=0, hi=255, hint="建筑盖好后把脚下的地形改成哪个编号，-1 表示不改。"),
    "BlastDefenseLevel": dict(zh="爆炸防御等级", group="combat", lo=0, hi=255,
                              hint="溅射等级不高于它的单位，炸不动它。"),
    "CombatLevel": dict(zh="战斗等级", group="combat", lo=0, hi=255, hint="单位的战斗等级，用于胜负判定和一部分技能的目标筛选。等级差得多的单位之间不容易互相干扰。"),
    "InteractionMode": dict(zh="交互模式", group="misc", enum=INTERACTION_ZH, hint="单位和玩家、和其他单位互动的模式编号，没有把握就保持原值。"),
    "MinimapMode": dict(zh="小地图模式", group="graphic", enum=DRAWMAP_ZH, hint="它在小地图上怎么画：点、方块、图标。填 -1 表示不显示在小地图上。"),
    "InterfaceKind": dict(zh="界面种类", group="misc", lo=0, hi=255, hint="它用哪一套操作界面，比如建筑面板还是单位面板。改错会出现面板打不开。"),
    "MultipleAttributeMode": dict(zh="多属性模式", group="misc", lo=0, hi=10,
                                  step=0.05,
                                  hint="1 = 按活着的东西多少来生效"
                                       "（AGE 原文：1 on more or less living things）。"),
    "MinimapColor": dict(zh="小地图颜色", group="graphic", lo=0, hi=255,
                         hint="只在小地图模式 3 和 4 下生效。"),
    "Recyclable": dict(zh="可回收", group="misc", enum=BOOL, hint="1 = 死亡后回收到对象池里复用（省性能）；0 = 正常销毁。"),
    "EnableAutoGather": dict(zh="自动采集", group="produce", enum=BOOL, hint="1 = 空下来自动去找资源采集（村民类靠它）；0 = 不自动。"),
    "CreateDoppelgangerOnDeath": dict(zh="死后分身", group="corpse", enum=BOOL, hint="1 = 死亡时在旁边生成一个替身单位（少数战役单位用）；0 = 正常死亡。"),
    "ResourceGatherGroup": dict(zh="采集分组", group="produce", lo=0, hi=255, hint="采集时按哪个分组算资源，同一组里的资源可以互相顶替。"),
    "OldAttackReaction": dict(zh="旧攻击反应", group="combat", lo=0, hi=255, hint="老版本引擎的攻击反应行为，DE 里基本不用，保持原值。"),
    "ResourceCapacity": dict(zh="资源容量", group="produce", lo=0, hi=32767,
                             hint="渔船一次能装多少鱼、农民一次背多少。"),
    "ResourceDecay": dict(zh="资源腐烂", group="produce", lo=0, hi=100,
                          step=0.01, hint="它带着的资源会不会随时间减少：0 = 不腐烂，大于 0 就按这个速率往下掉。"),
    "ScenarioTrigger1": dict(zh="场景触发器 1", group="misc", soft=True, hint="给场景（战役）脚本用的触发器编号，普通对战不用，保持原值。"),
    "ScenarioTrigger2": dict(zh="场景触发器 2", group="misc", soft=True, hint="第二个场景触发器编号，普通对战不用，保持原值。"),
    "DamageGraphicsCount": dict(zh="受损图形数", group="graphic", lo=0, hi=255,
                                ro=True,
                                hint="受损时换几套图形。行数由数据决定。"),
    # ---- 尸体与鸟 ----------------------------------------------------------
    "DeadFish.TurnRadius": dict(zh="转身半径", group="corpse", lo=0, hi=100,
                                step=0.1, hint="尸体的转身半径，单位是格，影响它倒下的方向看着自不自然。"),
    "DeadFish.MinCollisionSizeMultiplier": dict(zh="最小碰撞倍率", group="corpse",
                                                lo=0, hi=10, step=0.05, hint="尸体状态下碰撞体缩到多小，按原体积乘这个系数。"),
    "Bird.DropSitesCount": dict(zh="投放点数", group="corpse", lo=0, hi=255,
                                ro=True, hint="鸟有几个可用的投放点，也就是觅食完落在哪里。"),
    "Bird.TaskSwapGroup": dict(zh="任务交换组", group="corpse", lo=0, hi=255, hint="鸟在不同行为之间切换时用的组号，保持原值即可。"),
    "Bird.AttackSound": dict(zh="鸟攻击音", group="corpse", lo=-1, hi=32767, hint="鸟攻击时的音效编号，-1 表示不出声。"),
    "Bird.MoveSound": dict(zh="鸟移动音", group="corpse", lo=-1, hi=32767, hint="鸟飞动时的音效编号，-1 表示不出声。"),
    "Bird.RunPattern": dict(zh="鸟跑动模式", group="corpse", lo=0, hi=255,
                            hint="猎物受惊后往哪跑。AGE 里这一列的枚举注释本身"
                                 "错位了（1 号写着「on more or less living things」），"
                                 "所以这里只给范围、不给名字。"),
    "Bird.TaskCount": dict(zh="鸟任务数", group="corpse", lo=0, hi=255, ro=True, hint="鸟的行为任务有几条。改它必须同时改下面的任务数组，否则会读到越界数据。"),

    # ---- 名字（三个地址合起来才是名字）-------------------------------------
    # `unitfields.Rec.s()` records the marker, the length and the text because a
    # writer that moves only the text leaves the length stale -- parser.py's own
    # docstring records a 2,656-byte drift from exactly that mistake.
    "Name": dict(zh="内部名称", group="basic", ro=True,
                 hint="数据里的名字（不是游戏里显示的名字）。它是三个地址：标记、长度、文本，"
                      "只写文本会留下过期的长度（解析器自己记录过这种错法造成的 2,656 字节漂移）。"
                      "要改请点记录上方的「改名字」。"),
    "Name.len": dict(zh="名称长度", group="basic", ro=True,
                     hint="紧跟名称的两个字节。跟着名称一起写，不能单独改。"),
    "Name.marker": dict(zh="名称标记", group="basic", ro=True,
                        hint="固定值 2656，名称段的起始标记。"),

    # ---- 资源容量（渔船、掉落的资源点）-------------------------------------
    "ResourceStorages.0.Type": dict(zh="资源槽 1 类型", group="produce",
                                    enum=RES_SLOT_ZH,
                                    hint="这个单位能装哪种资源，编号就是资源表里的槽号"
                                          "（0 食物 1 木材 2 石头 3 黄金，15 肉类 16 浆果 17 鱼肉）。"
                                          "渔船改这里就变成别的资源点。"),
    "ResourceStorages.0.Amount": dict(zh="资源槽 1 数量", group="produce", lo=0,
                                      hi=100000, step=1,
                                      hint="装满是多少。渔船改这里就变成无限鱼。"),
    "ResourceStorages.0.Mode": dict(zh="资源槽 1 模式", group="produce", lo=0,
                                    hi=255, hint="这个资源槽的工作模式：0 = 只接收，1 = 双向存取（可以当存放点用）。"),
    "ResourceStorages.1.Type": dict(zh="资源槽 2 类型", group="produce",
                                    enum=RES_SLOT_ZH, hint="第二个资源槽装哪种资源，编号就是资源表里的槽号（0 食物 1 木材 2 石头 3 黄金），−1 表示空位。"),
    "ResourceStorages.1.Amount": dict(zh="资源槽 2 数量", group="produce", lo=0,
                                      hi=100000, step=1, hint="第二个资源槽装满是多少。填 0 表示这个槽不起作用。"),
    "ResourceStorages.1.Mode": dict(zh="资源槽 2 模式", group="produce", lo=0,
                                    hi=255, hint="第二个资源槽的工作模式：0 = 只接收，1 = 双向存取（可以当存放点用）。"),
    "ResourceStorages.2.Type": dict(zh="资源槽 3 类型", group="produce",
                                    enum=RES_SLOT_ZH, hint="第三个资源槽装哪种资源，编号就是资源表里的槽号（0 食物 1 木材 2 石头 3 黄金），−1 表示空位。"),
    "ResourceStorages.2.Amount": dict(zh="资源槽 3 数量", group="produce", lo=0,
                                      hi=100000, step=1, hint="第三个资源槽装满是多少。填 0 表示这个槽不起作用。"),
    "ResourceStorages.2.Mode": dict(zh="资源槽 3 模式", group="produce", lo=0,
                                    hi=255, hint="第三个资源槽的工作模式：0 = 只接收，1 = 双向存取（可以当存放点用）。"),

    # ---- 尸体阶段（DeadFish 是 genieutils 的名字，其实是「可被吃掉的那几个数」）
    "DeadFish.0": dict(zh="尸体阶段 1 图形", group="corpse", lo=-1, hi=32767, hint="单位死后留下的尸体用的图形编号，同一具尸体的不同阶段依次排在这里。填 -1 表示死后不留尸体。"),
    "DeadFish.1": dict(zh="尸体阶段 1 时长", group="corpse", lo=-1, hi=32767, hint="尸体阶段 1 存在多久，单位是秒。填 0 表示这一阶段直接跳过、立刻进入下一阶段。"),
    "DeadFish.2": dict(zh="尸体阶段 1 采集量", group="corpse", lo=0, hi=100000,
                       step=1, hint="尸体阶段 1 里能被采集到的资源量，0 表示这一阶段采不到东西。三个阶段的采集量加起来决定尸体总共能采多少。"),
    "DeadFish.3": dict(zh="尸体阶段 1 动作", group="corpse", lo=0, hi=255, hint="尸体阶段 1 的动作编号，普通单位填 0。引擎基本不读这一项，保持数据原值即可。"),
    "DeadFish.4": dict(zh="尸体阶段 2 图形", group="corpse", lo=-1, hi=32767, hint="尸体阶段 2 用的图形编号，-1 表示沿用上一阶段的图形。"),
    "DeadFish.5": dict(zh="尸体阶段 2 时长", group="corpse", lo=-1, hi=32767, hint="尸体阶段 2 存在多久，单位是秒。填 0 表示这一阶段直接跳过。"),
    "DeadFish.6": dict(zh="尸体阶段 2 采集量", group="corpse", lo=0, hi=100000,
                       step=1, hint="尸体阶段 2 里能被采集到的资源量，0 表示这一阶段采不到东西。"),
    "DeadFish.7": dict(zh="尸体阶段 2 动作", group="corpse", lo=0, hi=255, hint="尸体阶段 2 的动作编号，普通单位填 0，保持数据原值即可。"),
    "DeadFish.8": dict(zh="尸体阶段 3 图形", group="corpse", lo=-1, hi=32767, hint="尸体阶段 3 用的图形编号，-1 表示沿用上一阶段的图形。"),
    "DeadFish.9": dict(zh="尸体阶段 3 时长", group="corpse", lo=-1, hi=32767, hint="尸体阶段 3 存在多久，单位是秒。三个阶段都填 0，尸体就立刻消失、不留残骸。"),
    "DeadFish.10": dict(zh="尸体阶段 3 采集量", group="corpse", lo=0, hi=100000,
                        step=1, hint="尸体阶段 3 里能被采集到的资源量，0 表示这一阶段采不到东西。"),
    "DeadFish.11": dict(zh="尸体阶段 3 动作", group="corpse", lo=0, hi=255, hint="尸体阶段 3 的动作编号，普通单位填 0，保持数据原值即可。"),

    # ---- 剩下的界面文本号 ------------------------------------------------
    "OldPortraitPict": dict(zh="旧版头像", group="graphic", lo=-1, hi=32767,
                            hint="HD 之前用的头像编号。"),
    "LanguageDLLHelp": dict(zh="帮助文本编号", group="graphic", lo=-1,
                            hi=2147483647, soft=True,
                            hint="通常等于 100000 加上语言文件里的名字编号。"),
    "LanguageDLLHotKeyText": dict(zh="热键文本编号", group="graphic", lo=-1,
                                  hi=2147483647, soft=True, hint="界面上显示的热键文本的字符串编号，通常等于 100000 加上语言文件里的位置。"),

    # ---- 最后 8 个（鸟的保留位、造价标记）---------------------------------
    "Creatable.ResourceCosts.0.Flag": dict(zh="造价标记 1", group="produce",
                                           lo=0, hi=255,
                                           hint="造价是否消耗。0 是消耗，1 是「只显示不扣」。"),
    "Creatable.ResourceCosts.1.Flag": dict(zh="造价标记 2", group="produce",
                                           lo=0, hi=255, hint="第二条造价是否真扣：0 是消耗，1 是只显示不扣。"),
    "Creatable.ResourceCosts.2.Flag": dict(zh="造价标记 3", group="produce",
                                           lo=0, hi=255, hint="第三条造价是否真扣：0 是消耗，1 是只显示不扣。"),
    "Bird.0": dict(zh="鸟保留位 1", group="corpse", lo=-1, hi=32767, hint="鸟结构里的一项，当前版本引擎不读它，保持数据原值即可。"),
    "Bird.1": dict(zh="鸟速度", group="corpse", lo=0, hi=20, step=0.05,
                   hint="鸟（鹰、火鸡）飞多快。"),
    "Bird.2": dict(zh="鸟保留位 2", group="corpse", lo=-100, hi=100, step=0.05, hint="鸟结构里的第二个保留位，当前版本引擎不读它，保持数据原值即可。"),
    "Bird.WwiseAttackSoundID": dict(zh="Wwise 鸟攻击音", group="corpse", lo=0,
                                    hi=4294967295, soft=True, hint="鸟攻击音的 Wwise 事件编号；0 表示改用老的 .wav 音效。"),
    "Bird.WwiseMoveSoundID": dict(zh="Wwise 鸟移动音", group="corpse", lo=0,
                                  hi=4294967295, soft=True, hint="鸟飞动音的 Wwise 事件编号；0 表示改用老的 .wav 音效。"),
}


# ---------------------------------------------------------------------------
# The list rows.  These are registered with an explicit `.0` because
# `meta_for()` resolves `Attacks.7.Class` by rewriting the index to 0 and looking
# up `Attacks.0.Class` -- so the `.0` spelling is the seed, not the parent path.
# ---------------------------------------------------------------------------
FIELD_META.update({
    # 攻击加成 / 护甲：这才是真正生效的战斗数值。`DisplayedAttack` 只是界面上
    # 那个数字，玩家改「攻击力」改了没效果，十次有九次是因为直接改错了这里。
    "Type50.Attacks.0.Class": dict(zh="攻击类别", group="combat", enum=ATK_CLASS_ZH,
                                   hint="这一条加的是「打哪一类」。类别名在右边的下拉里，"
                                        "29 鹰勇士、8 骑兵、15 弓箭手、21 标准建筑这些名字已经从游戏里读出来了。"),
    "Type50.Attacks.0.Amount": dict(zh="攻击加成值", group="combat", lo=-32768,
                                    hi=32767,
                                    hint="对上面那一类额外打多少。界面上的总攻击力＝各条相加。"),
    "Type50.Armours.0.Class": dict(zh="护甲类别", group="combat", enum=ATK_CLASS_ZH,
                                   hint="这一条挡的是「哪一类伤害」，和攻击表同一套类别编号。"
                                   "31 立陶宛 Leitis、16 船只与自爆单位这类有专门护甲，负值表示更怕。"),
    "Type50.Armours.0.Amount": dict(zh="护甲值", group="combat", lo=-32768,
                                    hi=32767,
                                    hint="挡多少。负数等于更怕这一类。"),

    # 建筑段。只在 Type=80 的记录上存在。
    "Building.TechID": dict(zh="研究科技", group="build", lo=-1, hi=32767,
                            hint="这座建筑能研究哪项科技（城镇中心、铁匠铺这类）。"),
    "Building.Annexes.0.UnitID": dict(zh="附属单位", group="build", lo=-1,
                                       hi=32767, soft=True,
                                       hint="贴着它自动生成的附属物（城门、墙的连接段）。"),
    "Building.Annexes.0.Misplacement": dict(zh="附属偏移", group="build", lo=-100,
                                            hi=100, step=0.05,
                                            hint="附属建筑相对主建筑的偏移量，里面装着 X、Y 两个数，单位是格。"),
    "Building.Annexes.0.Misplacement.0": dict(zh="附属偏移 X", group="build",
                                              lo=-100, hi=100, step=0.05, hint="附属建筑相对主建筑的偏移，单位是格，两项是 X、Y。要把附属挪到旁边就改这里。"),
    "Building.Annexes.0.Misplacement.1": dict(zh="附属偏移 Y", group="build",
                                              lo=-100, hi=100, step=0.05, hint="附属建筑相对主建筑的纵向偏移，单位是格，正数往后偏。想把附属挪到旁边就改这里。"),
    "Building.HeadUnit": dict(zh="头部单位", group="build", lo=-1, hi=32767,
                              hint="墙、城门这类连体建筑的主件。"),
    "Building.StackUnitID": dict(zh="堆叠单位", group="build", lo=-1, hi=32767, hint="建筑上堆放的东西用的单位编号，比如农田上的作物；-1 表示没有。"),
    "Building.PileUnit": dict(zh="堆放单位", group="build", lo=-1, hi=32767, hint="资源堆放时用的单位编号，比如伐木场旁边那堆木头。"),
    "Building.FoundationTerrainID": dict(zh="地基地形", group="build", lo=-1,
                                         hi=32767, hint="打地基时脚下铺的地形编号，-1 表示沿用原地形。"),
    "Building.ConstructionGraphicID": dict(zh="建造中图形", group="graphic",
                                           lo=-1, hi=32767, hint="建造过程中的图形编号（脚手架），-1 表示用默认的。"),
    "Building.DestructionGraphicID": dict(zh="摧毁图形", group="graphic", lo=-1,
                                          hi=32767, hint="倒塌动画的图形编号，-1 表示直接消失。"),
    "Building.DestructionRubbleGraphicID": dict(zh="废墟图形", group="graphic",
                                                lo=-1, hi=32767, hint="倒完以后留下的废墟图形编号，-1 表示不留废墟。"),
    "Building.SnowGraphicID": dict(zh="雪地图形", group="graphic", lo=-1,
                                   hi=32767, hint="下雪地图上替换用的图形编号，-1 表示不换。"),
    "Building.ResearchingGraphic": dict(zh="研究中图形", group="graphic", lo=-1,
                                        hi=32767, hint="正在研究科技时显示的图形编号，-1 表示不显示。"),
    "Building.ResearchCompletedGraphic": dict(zh="研究完成图形", group="graphic",
                                              lo=-1, hi=32767, hint="科技研究完成那一刻播的图形编号，-1 表示不播。"),
    "Building.DisappearsWhenBuilt": dict(zh="建成即消失", group="build",
                                         enum=BOOL,
                                         hint="农田、地基这类建完就换成别的单位。"),
    "Building.CanBurn": dict(zh="可被点燃", group="build", enum=BOOL, hint="1 = 会被火焰点着并持续掉血；0 = 不会。"),
    "Building.GarrisonType": dict(zh="驻军类型", group="build", lo=0, hi=255, hint="能让哪类单位进驻，按位组合（步兵 / 骑兵 / 弓箭手…）；0 表示不能驻军。"),
    "Building.GarrisonHealRate": dict(zh="驻军回血速度", group="build", lo=0,
                                      hi=100, step=0.01,
                                      hint="驻军在里面回血的速度系数。"),
    "Building.GarrisonRepairRate": dict(zh="驻军修理速度", group="build", lo=0,
                                        hi=100, step=0.01, hint="有人驻军时每秒自动回多少血；0 表示不自动修。"),
    "Building.GraphicsAngle": dict(zh="图形角度", group="graphic", lo=0, hi=255, hint="建筑图形整体旋转的角度，常见 0 / 90 / 180 / 270。填错会出现斜着的房子。"),
    "Building.AdjacentMode": dict(zh="相邻模式", group="build", lo=0, hi=255, hint="相邻判定模式，决定它算不算和其他建筑「挨着」。"),
    "Building.OldOverlayID": dict(zh="旧覆盖层", group="build", lo=-1, hi=32767, hint="老版本引擎的覆盖层编号，DE 里多数不用，保持原值。"),
    # LootingTable is six independent u8 switches (genieutils Building.cpp:105);
    # AGE names them Stone / Wood / Ore / Gold / Food / Goods (AGE_Frame/Units.cpp
    # :4928-4935), so each index gets its own label instead of one opaque "table".
    "Building.LootingTable.0": dict(zh="掉落·石头", group="build", lo=0, hi=255,
                                    hint="1 = 被摧毁时掉石头。这条记录实测 30,809 个建筑里只有 3 种取值组合。"),
    "Building.LootingTable.1": dict(zh="掉落·木材", group="build", lo=0, hi=255,
                                    hint="1 = 被摧毁时掉木材。"),
    "Building.LootingTable.2": dict(zh="掉落·矿石", group="build", lo=0, hi=255,
                                    hint="1 = 被摧毁时掉矿石。全库 30,809 个建筑这一位都是 0。"),
    "Building.LootingTable.3": dict(zh="掉落·黄金", group="build", lo=0, hi=255,
                                    hint="1 = 被摧毁时掉黄金。"),
    "Building.LootingTable.4": dict(zh="掉落·食物", group="build", lo=0, hi=255,
                                    hint="1 = 被摧毁时掉食物。"),
    "Building.LootingTable.5": dict(zh="掉落·货物", group="build", lo=0, hi=255,
                                    hint="1 = 被摧毁时掉货物。全库 30,809 个建筑这一位都是 0。"),
    "Building.TransformUnit": dict(zh="变形为单位", group="build", lo=-1,
                                   hi=2147483647,
                                   hint="给它「展开 / 收起」命令时变成哪个单位。"),
    "Building.ConstructionSound": dict(zh="建造音效", group="graphic", lo=-1,
                                       hi=32767, hint="建造过程中循环播的音效编号，-1 表示不出声。"),
    "Building.TransformSound": dict(zh="变形音效", group="graphic", lo=-1,
                                    hi=32767, hint="展开 / 收起（变形）时的音效编号，-1 表示不出声。"),
    "Building.WwiseConstructionSoundID": dict(zh="Wwise 建造音", group="graphic",
                                              lo=0, hi=4294967295, soft=True, hint="建造音的 Wwise 事件编号；0 表示改用老的 .wav 音效。"),
    "Building.WwiseTransformSoundID": dict(zh="Wwise 变形音", group="graphic",
                                           lo=0, hi=4294967295, soft=True, hint="变形音的 Wwise 事件编号；0 表示改用老的 .wav 音效。"),

    # 受损图形
    "DamageGraphics.0.Graphic": dict(zh="受损图形", group="graphic", lo=-1,
                                     hi=32767, hint="这个受损阶段用的图形编号。建筑按掉了多少血切换不同的「破损图」。"),
    "DamageGraphics.0.Percent": dict(zh="触发血量百分比", group="graphic", lo=0,
                                     hi=100,
                                     hint="掉到这么多血时换成这张图。"),
    "DamageGraphics.0.ApplyMode": dict(zh="叠加模式", group="graphic",
                                       enum=APPLY_MODE_ZH, hint="受损血图怎样叠到本体上（覆盖 / 混色 / 替换），按原版同类建筑的数值填。"),

    # 投射物（Type=60 的记录才有）
    "Projectile.ProjectileArc": dict(zh="弹道弧度", group="projectile", lo=0,
                                     hi=255,
                                     hint="弹道拱起来的程度，单位是格。0 是贴地平飞，数值越大抛物线越高。"),
    # Type=60 的弹道记录：五个 u8 加一个 float，写死顺序见 genieutils
    # `src/dat/unit/Projectile.cpp` 的 serializeObject()：ProjectileType、
    # SmartMode、HitMode、VanishMode、AreaEffectSpecials、ProjectileArc。
    # 这五个键在旧版里曾经整体错位一格（把 ProjectileType 漏了，照着 AGE 的
    # 显示顺序写），界面上就把「弹型」叫成了「智能模式」，改的是隔壁那个字节。
    "Projectile.0": dict(zh="弹型", group="projectile", lo=0, hi=255,
                         hint="这颗弹怎么飞：0 = 直线，1 = 垂直落到底图，"
                              "2 = 按速度追踪，3 = 瞬移。"),
    "Projectile.1": dict(zh="智能模式", group="projectile", lo=0, hi=255,
                         hint="瞄准点怎么算：0 = 打目标现在的位置，1 = 打目标将要去的位置。"
                              "效果属性 19 会改这个值。"),
    "Projectile.2": dict(zh="命中模式", group="projectile", lo=0, hi=255,
                         hint="撞到障碍之后怎么办：0 = 继续飞，1 = 消失，2 = 打到所有（目标加落点）。"),
    "Projectile.3": dict(zh="消失模式", group="projectile", lo=0, hi=255,
                         hint="只影响图形，不影响判定：0 = 图形停在目标处，1 = 图形穿过目标继续走。"),
    "Projectile.4": dict(zh="范围特效", group="projectile", lo=0, hi=255,
                         hint="0 = 普通，1 = 随机（箭矢那种），2 = 随机爆炸。"),

    # 鸟 / 可采集生物的任务表：任务决定它怎么被猎、被赶、被聚集。
    "Bird.DropSites.0": dict(zh="投放点", group="corpse", lo=-1, hi=32767,
                             hint="鸟被打死后掉到哪儿。"),
    "Bird.DropSites": dict(zh="投放点表", group="corpse", ro=True,
                           hint="往下掉的地点清单，行数由数据决定。"),
    "Bird.Tasks.0.ID": dict(zh="任务编号", group="task", lo=0, hi=255, hint="这条任务的编号，引擎用它在任务表里定位这一条。同一个单位的任务编号不要重复。"),
    "Bird.Tasks.0.TaskType": dict(zh="任务类型", group="task", lo=0, hi=255,
                                  hint="0 无、1 移动、3 驻守、5 采集、7 战斗、8 射击、10 飞走…"),
    "Bird.Tasks.0.ClassID": dict(zh="任务类别编号", group="task", lo=-1,
                                 hi=32767, hint="任务类别编号，决定这条任务算建造、采集还是攻击，引擎按类别做优先级判断。"),
    "Bird.Tasks.0.UnitID": dict(zh="任务目标单位", group="task", lo=-1,
                                hi=32767, hint="这条任务作用在哪个单位上，比如「采集农田」要填农田的单位编号；-1 表示不指定。"),
    "Bird.Tasks.0.TerrainID": dict(zh="任务地形", group="task", lo=-1,
                                   hi=32767,
                                   hint="建筑盖完后在脚下铺出的地形。"),
    "Bird.Tasks.0.ResourceMultiplier": dict(zh="资源倍率", group="task", lo=-32768,
                                            hi=32767, hint="这条任务每次结算乘上的倍率。1 是标准速度，2 就是两倍快。"),
    "Bird.Tasks.0.ActionType": dict(zh="动作类型", group="task", enum=ACTION_ZH, hint="这条任务做的是什么动作。编号对应 AGE 的 Unit Task / Command ID 列表，选错单位就会发呆或乱跑。"),
    "Bird.Tasks.0.IsDefault": dict(zh="默认任务", group="task", enum=BOOL, hint="1 = 空下来时默认做这条任务（村民默认去采集就是靠它）；0 = 不默认。"),
    "Bird.Tasks.0.Enabled": dict(zh="启用", group="task", enum=TASK_ENABLED_ZH,
                                  hint="−1 表示永远启用。填资源槽号则是条件启用："
                                       "那个资源 ≤0 时关掉这条任务、>0 时打开。"
                                       "（AGE 原文：If the value of this dropdown is -1, "
                                       "the task is enabled … if <=0 disable, if >0 enable.）"),
    "Bird.Tasks.0.EnableTargeting": dict(zh="可对目标", group="task", enum=BOOL,
                                        hint="0 不给这个单位自动选目标；1 允许它自己挑目标。"
                                             "（AGE：0 No targeting / 1 Allows units to "
                                             "select their targets）"),
    "Bird.Tasks.0.CombatLevelFlag": dict(zh="战斗等级标记", group="task", lo=0,
                                         hi=255, hint="1 = 这条任务算战斗行为，会进入战斗状态；0 = 不算。"),
    "Bird.Tasks.0.PickForConstruction": dict(zh="可被选去建造", group="task",
                                             enum=BOOL,
                                             hint="1 = 目标是建造时优先挑这条任务。"),
    "Bird.Tasks.0.AutoSearchTargets": dict(zh="自动寻找目标", group="task",
                                           enum=BOOL,
                                           hint="1 = 自己去找目标。"),
    "Bird.Tasks.0.CarryCheck": dict(zh="携带检查", group="task", enum=BOOL, hint="1 = 做这条任务前先确认身上带着东西；0 = 不检查。"),
    "Bird.Tasks.0.ResourceIn": dict(zh="资源输入", group="task",
                                    enum=RES_SLOT_ZH,
                                    hint="采集这条任务时拿到的是哪种资源。"),
    "Bird.Tasks.0.ResourceOut": dict(zh="资源输出", group="task", lo=-1,
                                     hi=32767,
                                     hint="送回存放点时记到哪种资源上。"),
    "Bird.Tasks.0.UnusedResource": dict(zh="未用资源", group="task", lo=-1,
                                        hi=32767, hint="引擎不读这个值，保持 0 就行。"),
    "Bird.Tasks.0.GatherType": dict(zh="采集类型", group="task", lo=-1,
                                    hi=32767, hint="采到的东西记成哪种资源：0 无 / 1 食物 / 2 木材 / 3 黄金 / 4 石头 / 5 兽肉 / 6 鱼 / 10 农田。"),
    "Bird.Tasks.0.WorkValue1": dict(zh="工作量 1", group="task", lo=-1,
                                    hi=32767, hint="这条任务的第一个工作量参数，含义随任务类型变：建造类是所需工作量，采集类是每次采集量。"),
    "Bird.Tasks.0.WorkValue2": dict(zh="工作量 2", group="task", lo=-1,
                                    hi=32767,
                                    hint="招降类任务里它是招降所需的最长时间。"),
    "Bird.Tasks.0.WorkRange": dict(zh="工作范围", group="task", lo=0, hi=100,
                                   step=0.5, hint="能做这条任务的距离，单位是格。0 表示必须贴上去，大于 0 可以隔空作业。"),
    "Bird.Tasks.0.WorkFlag2": dict(zh="工作标记 2", group="task", lo=0, hi=255, hint="工作行为的附加标记，按位组合；没有把握就保持数据里原来的值。"),
    "Bird.Tasks.0.SearchWaitTime": dict(zh="搜寻等待时间", group="task", lo=0,
                                        hi=255, hint="找不到目标时等多久再重新找一次，单位是秒。"),
    "Bird.Tasks.0.TargetDiplomacy": dict(zh="目标外交关系", group="task",
                                         enum=TARGET_DIPLO_ZH, hint="这条任务只对哪些外交关系生效，按位组合（自己 / 盟友 / 中立 / 敌人），见「目标外交」枚举。"),
    "Bird.Tasks.0.CarryingGraphic": dict(zh="携带图形", group="task", lo=-1,
                                         hi=32767, hint="手上拿着资源时替换用的图形编号，-1 表示沿用默认站立图形。"),
    "Bird.Tasks.0.MovingGraphic": dict(zh="移动图形", group="task", lo=-1,
                                       hi=32767, hint="执行这条任务时一边走一边用的图形，比如扛着木头的行走图；-1 表示用普通行走图。"),
    "Bird.Tasks.0.ProceedingGraphic": dict(zh="进行中图形", group="task",
                                           lo=-1, hi=32767, hint="任务进行中的图形，比如正在砍树；-1 表示用默认工作图形。"),
    "Bird.Tasks.0.WorkingGraphic": dict(zh="工作图形", group="task", lo=-1,
                                        hi=32767, hint="正在干活时用的图形编号，-1 表示沿用站立图形。"),
    "Bird.Tasks.0.DepositSoundID": dict(zh="存放音效", group="task", lo=-1,
                                        hi=32767, hint="把资源送回存放点时的音效编号，-1 表示不出声。"),
    "Bird.Tasks.0.ResourceGatheringSoundID": dict(zh="采集音效", group="task",
                                                  lo=-1, hi=32767, hint="采集时循环播放的音效编号，-1 表示不出声。"),
    "Bird.Tasks.0.WwiseDepositSoundID": dict(zh="Wwise 存放音", group="task",
                                             lo=0, hi=4294967295, soft=True, hint="存放资源音效的 Wwise 事件编号；0 表示改用老的 .wav 音效。"),
    "Bird.Tasks.0.WwiseGatherSoundID": dict(zh="Wwise 采集音", group="task",
                                            lo=0, hi=4294967295, soft=True, hint="采集音效的 Wwise 事件编号；0 表示改用老的 .wav 音效。"),
})

# Suffixes that mean "this row is a repeat of a list".  The editor still shows
# them (a modder legitimately wants enemy[3].Amount), but they inherit the label
# of their `.0` sibling so the form does not read "造价数量 1" 6 times.
_LIST_CAP = 12


# Values that ARE names, per task column.  The census in `ui/server.py` finds
# which of these the file actually contains and how often; this table supplies
# the Chinese word.  A value the census sees that is missing here is not hidden
# -- it is shown as `#42` and stays editable, which is the honest split between
# "we know the name" and "the data has it".
_TASK_NAMES = {
    # 动作类型：AGE「Unit Task / Command ID」列表的 46 个唯一编号，见上面的
    # `ACTION_ZH`。旧表把 109 写成「伐木」、110 写成「采金」、122 写成「采石」，
    # 村民的实测数据（slot 83：i=1 ActionType=110 打猎、i=5 ActionType=122 拾取）
    # 证明那是错的 —— 名字写错比不写更坏，因为玩家会照着它改。
    "ActionType": ACTION_ZH,
    # 目标外交。AGE 的原文是「0,7+ All objects / 1 Your objects only / ...」，
    # 跟「自己/盟友/中立/敌人」那种外交序完全不是一回事。
    "TargetDiplomacy": TARGET_DIPLO_ZH,
    # 采集类型：0 无、1 食物、2 木材、3 黄金、4 石头、5 兽肉、6 鱼、10 农田。
    # 只留这个文件真出现过的值；其余让页面印 `#23`。
    "GatherType": {0: "无", 1: "食物", 2: "木材", 3: "黄金", 4: "石头",
                   5: "兽肉", 6: "鱼", 10: "农田"},
    # 资源槽：和造价、存放用的是同一套 601 个槽号，共用一个表。
    "ResourceIn": RES_SLOT_ZH,
    "ResourceOut": RES_SLOT_ZH,
    "CarryCheck": {0: "不检查", 1: "检查"},
}


def value_name(tail, v):
    """`value_name("ActionType", 109)` -> "伐木"; unknown -> None.

    Returns None rather than "#109" so the caller decides how to show an
    unnamed value -- the editor prints `#109`, a tooltip can print the count.
    """
    m = _TASK_NAMES.get(tail)
    if not m:
        return None
    return m.get(v)


def meta_for(name):
    """`meta_for("Creatable.ResourceCosts.4.Amount")` -> the `.0` sibling's meta.

    Falls back to `{}`, which the UI reads as "no Chinese label" and shows the raw
    field name with no bounds -- the honest answer for the long tail.
    """
    m = FIELD_META.get(name)
    if m:
        return m
    parts = name.split(".")
    # Walk from the right, replacing the numeric index with 0 to find a sibling.
    for i in range(len(parts) - 1, -1, -1):
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


def order_key(name):
    """Sort key that keeps list members next to each other."""
    parts = name.split(".")
    return ".".join("0" if p.isdigit() else p for p in parts), name
