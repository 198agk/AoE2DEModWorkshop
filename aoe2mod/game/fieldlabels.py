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

FIELD_META = {
    # ---- 基础 -------------------------------------------------------------
    "Type": dict(zh="单位类型码", group="basic",
                 hint="决定这条记录按哪种结构解析：70 是可生产单位，80 是建筑，90 是森林。改它会改变整条记录的读法，不要动。",
                 ro=True),
    "ID": dict(zh="单位编号", group="basic",
               hint="这条记录在文明单位表里的位置。改它等于换一条记录。", ro=True),
    "Class": dict(zh="兵种类别", group="basic", enum=UNIT_CLASS_ZH,
                  hint="游戏用它决定谁能打谁、算什么兵。和「攻击加成」配合才有意义。"),
    "LanguageDLLName": dict(zh="名称文本编号", group="basic", ro=True,
                            hint="指向界面文本表里的名字。改它不会改名字，只会指错——"
                                 "要改显示的名请点记录上方的「改名字」，它会新分配一个"
                                 "文本编号（共用的那个不能动：编号 5079 是 57 条记录的名字）。"),
    "LanguageDLLCreation": dict(zh="创建文本编号", group="basic", ro=True,
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
    "CanBeBuiltOn": dict(zh="可建在其上", group="build", enum=BOOL,
                         hint="别的建筑能不能盖在它上面。"),
    "UndeadMode": dict(zh="亡灵模式", group="basic", enum=BOOL,
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
    "Trait": dict(zh="特性", group="basic", lo=0, hi=255),
    "Civilization": dict(zh="文明编号", group="basic", lo=0, hi=255,
                         hint="这条记录属于哪个文明。全部改掉会让所有文明都拿同一份。"),

    # ---- 移动与视野 --------------------------------------------------------
    "Speed": dict(zh="移动速度", group="move", lo=0, hi=20, step=0.05,
                  hint="村民是 0.96，骑兵大约 1.5。填 0 就是不会动。"),
    "CollisionSize.0": dict(zh="体积 X", group="move", lo=0, hi=20, step=0.05,
                            hint="碰撞体积的横向半径。"),
    "CollisionSize.1": dict(zh="体积 Y", group="move", lo=0, hi=20, step=0.05),
    "CollisionSize.2": dict(zh="体积 Z", group="move", lo=0, hi=20, step=0.05),
    "ClearanceSize.0": dict(zh="通行宽度 X", group="move", lo=0, hi=20, step=0.05,
                            hint="能不能从两个单位之间挤过去。"),
    "ClearanceSize.1": dict(zh="通行宽度 Y", group="move", lo=0, hi=20, step=0.05),
    "OutlineSize.0": dict(zh="选择框宽 X", group="move", lo=0, hi=20, step=0.05,
                          hint="选中时框多大。"),
    "OutlineSize.1": dict(zh="选择框宽 Y", group="move", lo=0, hi=20, step=0.05),
    "OutlineSize.2": dict(zh="选择框高 Z", group="move", lo=0, hi=20, step=0.05),
    "FogVisibility": dict(zh="战争迷雾可见", group="move", enum=BOOL),
    "TerrainRestriction": dict(zh="地形限制组", group="move", lo=0, hi=255,
                               hint="能走哪些地形，指向地形限制表。"),
    "FlyMode": dict(zh="飞行模式", group="move", lo=0, hi=255),
    "HillMode": dict(zh="坡地模式", group="move", lo=0, hi=255),
    "OcclusionMode": dict(zh="遮挡模式", group="move", lo=0, hi=255),
    "ObstructionType": dict(zh="阻挡类型", group="move", lo=0, hi=255),
    "ObstructionClass": dict(zh="阻挡类别", group="move", lo=0, hi=255),
    "PlacementTerrain.0": dict(zh="放置地形", group="build", lo=-1, hi=32767,
                               hint="场景里能放在哪种地形上。"),
    "PlacementSideTerrain.0": dict(zh="侧边地形", group="build", lo=-1, hi=32767),
    "MinCollisionSizeMultiplier": dict(zh="最小碰撞倍率", group="move", lo=0,
                                       hi=10, step=0.05),

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
                                       lo=-1, hi=32767),
    "Type50.BonusDamageResistance": dict(zh="附加伤害抗性", group="combat",
                                         lo=0, hi=1000, step=0.05,
                                         hint="挨额外伤害时减免多少。"),
    "Type50.MaxRange": dict(zh="最大射程", group="combat", lo=0, hi=100,
                            step=0.5, hint="0 表示只能贴身打。"),
    "Type50.MinRange": dict(zh="最小射程", group="combat", lo=0, hi=100,
                            step=0.5, hint="近身就打不到了，攻城器常用。"),
    "Type50.ReloadTime": dict(zh="装填时间", group="combat", lo=0, hi=100,
                              step=0.1, hint="两次攻击之间要等多久，秒。"),
    "Type50.AccuracyPercent": dict(zh="命中率", group="combat", lo=0, hi=100,
                                   hint="弹道类单位的命中百分比。"),
    "Type50.AccuracyDispersion": dict(zh="散布", group="combat", lo=0, hi=100,
                                      step=0.1),
    "Type50.BlastWidth": dict(zh="溅射范围", group="combat", lo=0, hi=20,
                              step=0.1, hint="打中之后波及多宽。"),
    "Type50.BlastAttackLevel": dict(zh="溅射等级", group="combat", lo=0, hi=255),
    "Type50.BlastDamage": dict(zh="溅射伤害倍率", group="combat", lo=0, hi=10,
                               step=0.05),
    "Type50.FriendlyFireDamage": dict(zh="友伤倍率", group="combat", lo=0, hi=10,
                                      step=0.05, hint="1 是全额误伤，0 是完全不伤自己人。"),
    "Type50.DamageReflection": dict(zh="伤害反弹", group="combat", lo=0, hi=10,
                                    step=0.05),
    "Type50.BreakOffCombat": dict(zh="脱战", group="combat", lo=0, hi=255),
    "Type50.FrameDelay": dict(zh="出招延迟帧", group="combat", lo=-1, hi=32767),
    "Type50.InterruptFrame": dict(zh="打断帧", group="combat", lo=-1, hi=32767),
    "Type50.GarrisonFirepower": dict(zh="驻军火力", group="combat", lo=0, hi=100,
                                     step=0.1, hint="里面驻军时这座建筑打多疼。"),
    "Type50.BonusDamageResistance": dict(zh="附加伤害抗性", group="combat",
                                         lo=0, hi=1000, step=0.05),
    "Type50.ProjectileUnitID": dict(zh="投射物单位", group="projectile",
                                    lo=-1, hi=32767,
                                    hint="射出去的那个东西是哪条单位记录。"),
    "Type50.AttackGraphic": dict(zh="攻击图形", group="graphic", lo=-1, hi=32767),
    "Type50.AttackGraphic2": dict(zh="攻击图形 2", group="graphic", lo=-1,
                                  hi=32767),
    "Type50.DisplayedMeleeArmour": dict(zh="显示近战护甲", group="combat",
                                        lo=0, hi=1000,
                                        hint="界面上写的近战护甲，和真实计算值是两处。"),
    "Type50.DisplayedAttack": dict(zh="显示攻击力", group="combat", lo=0, hi=1000,
                                   hint="界面上写的攻击力。真正生效的是「攻击加成」表。"),
    "Type50.DisplayedRange": dict(zh="显示射程", group="combat", lo=0, hi=100,
                                  step=0.5),
    "Type50.DisplayedReloadTime": dict(zh="显示装填", group="combat", lo=0, hi=100,
                                       step=0.1),
    "Type50.GraphicDisplacement.0": dict(zh="图形位移 X", group="graphic", lo=-10,
                                         hi=10, step=0.05),
    "Type50.GraphicDisplacement.1": dict(zh="图形位移 Y", group="graphic", lo=-10,
                                         hi=10, step=0.05),
    "Type50.GraphicDisplacement.2": dict(zh="图形位移 Z", group="graphic", lo=-10,
                                         hi=10, step=0.05),

    # ---- 生产与造价 --------------------------------------------------------
    "Creatable.TrainLocationsCount": dict(zh="训练条目数", group="produce",
                                          lo=0, hi=255, ro=True,
                                          hint="这个单位能在几个地方造。"),
    "Creatable.TrainLocations.0.TrainTime": dict(zh="训练时间", group="produce",
                                                 lo=0, hi=3600,
                                                 hint="多少秒造出来。"),
    "Creatable.TrainLocations.0.UnitID": dict(zh="训练出的单位", group="produce",
                                              lo=-1, hi=32767, ro=True,
                                              hint="这条训练项产出谁。"),
    "Creatable.TrainLocations.0.ButtonID": dict(zh="按钮格号", group="produce",
                                                lo=0, hi=24,
                                                hint="在建筑命令面板上排第几格。"),
    "Creatable.TrainLocations.0.HotKeyID": dict(zh="热键编号", group="produce",
                                                lo=-1, hi=32767),
    "Creatable.ResourceCosts.0.Type": dict(zh="造价类型 1", group="produce",
                                           lo=-1, hi=255,
                                           hint="指向资源表：0 食物 1 木材 2 石头 3 黄金，"
                                                "−1 是空位。顺序是资源表的顺序，不是"
                                                "「金在石前」的直觉顺序。"),
    "Creatable.ResourceCosts.0.Amount": dict(zh="造价数量 1", group="produce",
                                             lo=0, hi=32767),
    "Creatable.ResourceCosts.1.Type": dict(zh="造价类型 2", group="produce",
                                           lo=-1, hi=255),
    "Creatable.ResourceCosts.1.Amount": dict(zh="造价数量 2", group="produce",
                                             lo=0, hi=32767),
    "Creatable.ResourceCosts.2.Type": dict(zh="造价类型 3", group="produce",
                                           lo=-1, hi=255),
    "Creatable.ResourceCosts.2.Amount": dict(zh="造价数量 3", group="produce",
                                             lo=0, hi=32767),
    "Creatable.CreatableType": dict(zh="可生产类型", group="produce", lo=0, hi=255,
                                    ro=True,
                                    hint="255 是「无」。改它会改变下面整段结构的解释方式。"),
    "Creatable.RearAttackModifier": dict(zh="背后攻击加成", group="combat", lo=0,
                                         hi=10, step=0.05),
    "Creatable.FlankAttackModifier": dict(zh="侧翼攻击加成", group="combat", lo=0,
                                          hi=10, step=0.05),
    "Creatable.HeroMode": dict(zh="英雄模式", group="produce", lo=0, hi=255,
                               hint="1 = 死了不复活，2 = 复活，3 = 倒地可救。"),
    "Creatable.DisplayedPierceArmour": dict(zh="显示远程护甲", group="combat",
                                            lo=0, hi=1000,
                                            hint="界面上写的远程护甲。1000 常表示哨兵值。"),
    "Creatable.AttackPriority": dict(zh="攻击优先级", group="combat", lo=0, hi=255),
    "Creatable.InvulnerabilityLevel": dict(zh="无敌等级", group="combat", lo=0,
                                           hi=10, step=0.05),
    "Creatable.MinConversionTimeMod": dict(zh="招降时间下限修正", group="combat",
                                           lo=0, hi=10, step=0.05),
    "Creatable.MaxConversionTimeMod": dict(zh="招降时间上限修正", group="combat",
                                           lo=0, hi=10, step=0.05),
    "Creatable.ConversionChanceMod": dict(zh="招降概率修正", group="combat", lo=0,
                                          hi=10, step=0.05),
    "Creatable.ButtonIconID": dict(zh="按钮图标", group="graphic", lo=-1, hi=32767),
    "Creatable.ButtonShortTooltipID": dict(zh="短提示文本号", group="graphic",
                                           lo=-1, hi=2147483647, ro=True),
    "Creatable.ButtonExtendedTooltipID": dict(zh="长提示文本号", group="graphic",
                                              lo=-1, hi=2147483647, ro=True),
    "Creatable.ButtonHotkeyAction": dict(zh="按钮热键动作", group="produce",
                                         lo=-1, hi=32767),
    # ---- 投射物 ------------------------------------------------------------
    "Creatable.ChargeEvent": dict(zh="蓄力触发", group="projectile", lo=0, hi=255),
    "Creatable.ChargeType": dict(zh="蓄力类型", group="projectile", lo=0, hi=255),
    "Creatable.ChargeTarget": dict(zh="蓄力目标", group="projectile", lo=-1,
                                   hi=32767),
    "Creatable.ChargeProjectileUnit": dict(zh="蓄力投射物", group="projectile",
                                           lo=-1, hi=2147483647),
    "Creatable.MaxCharge": dict(zh="蓄力上限", group="projectile", lo=0, hi=100,
                                step=0.1),
    "Creatable.RechargeRate": dict(zh="充能速度", group="projectile", lo=0, hi=100,
                                   step=0.1),
    "Creatable.TotalProjectiles": dict(zh="齐射数量", group="projectile", lo=0,
                                       hi=100, step=0.5),
    "Creatable.MaxTotalProjectiles": dict(zh="齐射上限", group="projectile", lo=0,
                                          hi=255),
    "Creatable.ProjectileSpawningArea.0": dict(zh="齐射散布 X", group="projectile",
                                               lo=0, hi=20, step=0.1),
    "Creatable.ProjectileSpawningArea.1": dict(zh="齐射散布 Y", group="projectile",
                                               lo=0, hi=20, step=0.1),
    "Creatable.ProjectileSpawningArea.2": dict(zh="齐射散布 Z", group="projectile",
                                               lo=0, hi=20, step=0.1),
    "Creatable.SecondaryProjectileUnit": dict(zh="副投射物", group="projectile",
                                              lo=-1, hi=2147483647),
    "Creatable.SpecialGraphic": dict(zh="特殊图形", group="graphic", lo=-1,
                                     hi=2147483647),
    "Creatable.SpecialAbility": dict(zh="特殊能力", group="projectile", lo=0,
                                     hi=255),

    # ---- 建造 --------------------------------------------------------------
    "Creatable.GarrisonGraphic": dict(zh="驻军图形", group="graphic", lo=-1,
                                      hi=2147483647),
    "Creatable.SpawningGraphic": dict(zh="产出图形", group="graphic", lo=-1,
                                      hi=32767),
    "Creatable.UpgradeGraphic": dict(zh="升级图形", group="graphic", lo=-1,
                                     hi=32767),
    "Creatable.HeroGlowGraphic": dict(zh="英雄光环", group="graphic", lo=-1,
                                      hi=32767),
    "Creatable.IdleAttackGraphic": dict(zh="待机攻击图形", group="graphic",
                                        lo=-1, hi=32767),

    # ---- 图形音效 ----------------------------------------------------------
    "TrainSound": dict(zh="训练音效", group="graphic", lo=-1, hi=32767),
    "DamageSound": dict(zh="受伤音效", group="graphic", lo=-1, hi=32767),
    "SelectionSound": dict(zh="选中音效", group="graphic", lo=-1, hi=32767),
    "DyingSound": dict(zh="死亡音效", group="graphic", lo=-1, hi=32767),
    "WwiseTrainSoundID": dict(zh="Wwise 训练音", group="graphic", lo=0,
                              hi=4294967295, ro=True),
    "WwiseDamageSoundID": dict(zh="Wwise 受伤音", group="graphic", lo=0,
                               hi=4294967295, ro=True),
    "WwiseSelectionSoundID": dict(zh="Wwise 选中音", group="graphic", lo=0,
                                  hi=4294967295, ro=True),
    "WwiseDyingSoundID": dict(zh="Wwise 死亡音", group="graphic", lo=0,
                              hi=4294967295, ro=True),
    "DeadUnitID": dict(zh="尸体单位", group="corpse", lo=-1, hi=32767,
                       hint="死后留下哪条记录当尸体。"),
    "BloodUnitID": dict(zh="血渍单位", group="corpse", lo=-1, hi=32767),
    "SelectionEffect": dict(zh="选中特效", group="graphic", lo=0, hi=255),
    "EditorSelectionColour": dict(zh="编辑器选中颜色", group="graphic", lo=0,
                                  hi=255),
    "ConvertTerrain": dict(zh="改造地形", group="build", lo=0, hi=255),
    "BlastDefenseLevel": dict(zh="爆炸防御等级", group="combat", lo=0, hi=255),
    "CombatLevel": dict(zh="战斗等级", group="combat", lo=0, hi=255),
    "InteractionMode": dict(zh="交互模式", group="misc", lo=0, hi=255),
    "MinimapMode": dict(zh="小地图模式", group="graphic", lo=0, hi=255),
    "InterfaceKind": dict(zh="界面种类", group="misc", lo=0, hi=255),
    "MultipleAttributeMode": dict(zh="多属性模式", group="misc", lo=0, hi=10,
                                  step=0.05),
    "MinimapColor": dict(zh="小地图颜色", group="graphic", lo=0, hi=255),
    "Recyclable": dict(zh="可回收", group="misc", enum=BOOL),
    "EnableAutoGather": dict(zh="自动采集", group="produce", enum=BOOL),
    "CreateDoppelgangerOnDeath": dict(zh="死后分身", group="corpse", enum=BOOL),
    "ResourceGatherGroup": dict(zh="采集分组", group="produce", lo=0, hi=255),
    "OldAttackReaction": dict(zh="旧攻击反应", group="combat", lo=0, hi=255),
    "ResourceCapacity": dict(zh="资源容量", group="produce", lo=0, hi=32767,
                             hint="渔船一次能装多少鱼、农民一次背多少。"),
    "ResourceDecay": dict(zh="资源腐烂", group="produce", lo=0, hi=100,
                          step=0.01),
    "ScenarioTrigger1": dict(zh="场景触发器 1", group="misc", ro=True),
    "ScenarioTrigger2": dict(zh="场景触发器 2", group="misc", ro=True),
    "DamageGraphicsCount": dict(zh="受损图形数", group="graphic", lo=0, hi=255,
                                ro=True,
                                hint="受损时换几套图形。行数由数据决定。"),
    # ---- 尸体与鸟 ----------------------------------------------------------
    "DeadFish.TurnRadius": dict(zh="转身半径", group="corpse", lo=0, hi=100,
                                step=0.1),
    "DeadFish.MinCollisionSizeMultiplier": dict(zh="最小碰撞倍率", group="corpse",
                                                lo=0, hi=10, step=0.05),
    "Bird.DropSitesCount": dict(zh="投放点数", group="corpse", lo=0, hi=255,
                                ro=True),
    "Bird.TaskSwapGroup": dict(zh="任务交换组", group="corpse", lo=0, hi=255),
    "Bird.AttackSound": dict(zh="鸟攻击音", group="corpse", lo=-1, hi=32767),
    "Bird.MoveSound": dict(zh="鸟移动音", group="corpse", lo=-1, hi=32767),
    "Bird.RunPattern": dict(zh="鸟跑动模式", group="corpse", lo=0, hi=255),
    "Bird.TaskCount": dict(zh="鸟任务数", group="corpse", lo=0, hi=255, ro=True),

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
    "ResourceStorages.0.Type": dict(zh="资源槽 1 类型", group="produce", lo=-1,
                                    hi=32767,
                                    hint="这个单位能装哪种资源：0 食物 1 木材 2 金 3 石 4 兽肉 5 鱼。"),
    "ResourceStorages.0.Amount": dict(zh="资源槽 1 数量", group="produce", lo=0,
                                      hi=100000, step=1,
                                      hint="装满是多少。渔船改这里就变成无限鱼。"),
    "ResourceStorages.0.Mode": dict(zh="资源槽 1 模式", group="produce", lo=0,
                                    hi=255),
    "ResourceStorages.1.Type": dict(zh="资源槽 2 类型", group="produce", lo=-1,
                                    hi=32767),
    "ResourceStorages.1.Amount": dict(zh="资源槽 2 数量", group="produce", lo=0,
                                      hi=100000, step=1),
    "ResourceStorages.1.Mode": dict(zh="资源槽 2 模式", group="produce", lo=0,
                                    hi=255),
    "ResourceStorages.2.Type": dict(zh="资源槽 3 类型", group="produce", lo=-1,
                                    hi=32767),
    "ResourceStorages.2.Amount": dict(zh="资源槽 3 数量", group="produce", lo=0,
                                      hi=100000, step=1),
    "ResourceStorages.2.Mode": dict(zh="资源槽 3 模式", group="produce", lo=0,
                                    hi=255),

    # ---- 尸体阶段（DeadFish 是 genieutils 的名字，其实是「可被吃掉的那几个数」）
    "DeadFish.0": dict(zh="尸体阶段 1 图形", group="corpse", lo=-1, hi=32767),
    "DeadFish.1": dict(zh="尸体阶段 1 时长", group="corpse", lo=-1, hi=32767),
    "DeadFish.2": dict(zh="尸体阶段 1 采集量", group="corpse", lo=0, hi=100000,
                       step=1),
    "DeadFish.3": dict(zh="尸体阶段 1 动作", group="corpse", lo=0, hi=255),
    "DeadFish.4": dict(zh="尸体阶段 2 图形", group="corpse", lo=-1, hi=32767),
    "DeadFish.5": dict(zh="尸体阶段 2 时长", group="corpse", lo=-1, hi=32767),
    "DeadFish.6": dict(zh="尸体阶段 2 采集量", group="corpse", lo=0, hi=100000,
                       step=1),
    "DeadFish.7": dict(zh="尸体阶段 2 动作", group="corpse", lo=0, hi=255),
    "DeadFish.8": dict(zh="尸体阶段 3 图形", group="corpse", lo=-1, hi=32767),
    "DeadFish.9": dict(zh="尸体阶段 3 时长", group="corpse", lo=-1, hi=32767),
    "DeadFish.10": dict(zh="尸体阶段 3 采集量", group="corpse", lo=0, hi=100000,
                        step=1),
    "DeadFish.11": dict(zh="尸体阶段 3 动作", group="corpse", lo=0, hi=255),

    # ---- 剩下的界面文本号 ------------------------------------------------
    "OldPortraitPict": dict(zh="旧版头像", group="graphic", lo=-1, hi=32767,
                            hint="HD 之前用的头像编号。"),
    "LanguageDLLHelp": dict(zh="帮助文本编号", group="graphic", lo=-1,
                            hi=2147483647, ro=True),
    "LanguageDLLHotKeyText": dict(zh="热键文本编号", group="graphic", lo=-1,
                                  hi=2147483647, ro=True),

    # ---- 最后 8 个（鸟的保留位、造价标记）---------------------------------
    "Creatable.ResourceCosts.0.Flag": dict(zh="造价标记 1", group="produce",
                                           lo=0, hi=255,
                                           hint="造价是否消耗。0 是消耗，1 是「只显示不扣」。"),
    "Creatable.ResourceCosts.1.Flag": dict(zh="造价标记 2", group="produce",
                                           lo=0, hi=255),
    "Creatable.ResourceCosts.2.Flag": dict(zh="造价标记 3", group="produce",
                                           lo=0, hi=255),
    "Bird.0": dict(zh="鸟保留位 1", group="corpse", lo=-1, hi=32767),
    "Bird.1": dict(zh="鸟速度", group="corpse", lo=0, hi=20, step=0.05,
                   hint="鸟（鹰、火鸡）飞多快。"),
    "Bird.2": dict(zh="鸟保留位 2", group="corpse", lo=-100, hi=100, step=0.05),
    "Bird.WwiseAttackSoundID": dict(zh="Wwise 鸟攻击音", group="corpse", lo=0,
                                    hi=4294967295, ro=True),
    "Bird.WwiseMoveSoundID": dict(zh="Wwise 鸟移动音", group="corpse", lo=0,
                                  hi=4294967295, ro=True),
}


# ---------------------------------------------------------------------------
# The list rows.  These are registered with an explicit `.0` because
# `meta_for()` resolves `Attacks.7.Class` by rewriting the index to 0 and looking
# up `Attacks.0.Class` -- so the `.0` spelling is the seed, not the parent path.
# ---------------------------------------------------------------------------
FIELD_META.update({
    # 攻击加成 / 护甲：这才是真正生效的战斗数值。`DisplayedAttack` 只是界面上
    # 那个数字，玩家改「攻击力」改了没效果，十次有九次是因为直接改错了这里。
    "Type50.Attacks.0.Class": dict(zh="攻击类别", group="combat", lo=0, hi=255,
                                   hint="打谁加成：3 步兵、4 骑兵、5 弓箭手、13 攻城武器、21 建筑…"),
    "Type50.Attacks.0.Amount": dict(zh="攻击加成值", group="combat", lo=-32768,
                                    hi=32767,
                                    hint="对上面那一类额外打多少。界面上的总攻击力＝各条相加。"),
    "Type50.Armours.0.Class": dict(zh="护甲类别", group="combat", lo=0, hi=255,
                                   hint="挡哪一类伤害，类别和攻击表同一套编号。"),
    "Type50.Armours.0.Amount": dict(zh="护甲值", group="combat", lo=-32768,
                                    hi=32767,
                                    hint="挡多少。负数等于更怕这一类。"),

    # 建筑段。只在 Type=80 的记录上存在。
    "Building.TechID": dict(zh="研究科技", group="build", lo=-1, hi=32767,
                            hint="这座建筑能研究哪项科技（城镇中心、铁匠铺这类）。"),
    "Building.Annexes.0.UnitID": dict(zh="附属单位", group="build", lo=-1,
                                       hi=32767, ro=True,
                                       hint="贴着它自动生成的附属物（城门、墙的连接段）。"),
    "Building.Annexes.0.Misplacement": dict(zh="附属偏移", group="build", lo=-100,
                                            hi=100, step=0.05),
    "Building.Annexes.0.Misplacement.0": dict(zh="附属偏移 X", group="build",
                                              lo=-100, hi=100, step=0.05),
    "Building.Annexes.0.Misplacement.1": dict(zh="附属偏移 Y", group="build",
                                              lo=-100, hi=100, step=0.05),
    "Building.HeadUnit": dict(zh="头部单位", group="build", lo=-1, hi=32767,
                              hint="墙、城门这类连体建筑的主件。"),
    "Building.StackUnitID": dict(zh="堆叠单位", group="build", lo=-1, hi=32767),
    "Building.PileUnit": dict(zh="堆放单位", group="build", lo=-1, hi=32767),
    "Building.FoundationTerrainID": dict(zh="地基地形", group="build", lo=-1,
                                         hi=32767),
    "Building.ConstructionGraphicID": dict(zh="建造中图形", group="graphic",
                                           lo=-1, hi=32767),
    "Building.DestructionGraphicID": dict(zh="摧毁图形", group="graphic", lo=-1,
                                          hi=32767),
    "Building.DestructionRubbleGraphicID": dict(zh="废墟图形", group="graphic",
                                                lo=-1, hi=32767),
    "Building.SnowGraphicID": dict(zh="雪地图形", group="graphic", lo=-1,
                                   hi=32767),
    "Building.ResearchingGraphic": dict(zh="研究中图形", group="graphic", lo=-1,
                                        hi=32767),
    "Building.ResearchCompletedGraphic": dict(zh="研究完成图形", group="graphic",
                                              lo=-1, hi=32767),
    "Building.DisappearsWhenBuilt": dict(zh="建成即消失", group="build",
                                         enum=BOOL,
                                         hint="农田、地基这类建完就换成别的单位。"),
    "Building.CanBurn": dict(zh="可被点燃", group="build", enum=BOOL),
    "Building.GarrisonType": dict(zh="驻军类型", group="build", lo=0, hi=255),
    "Building.GarrisonHealRate": dict(zh="驻军回血速度", group="build", lo=0,
                                      hi=100, step=0.01),
    "Building.GarrisonRepairRate": dict(zh="驻军修理速度", group="build", lo=0,
                                        hi=100, step=0.01),
    "Building.GraphicsAngle": dict(zh="图形角度", group="graphic", lo=0, hi=255),
    "Building.AdjacentMode": dict(zh="相邻模式", group="build", lo=0, hi=255),
    "Building.OldOverlayID": dict(zh="旧覆盖层", group="build", lo=-1, hi=32767),
    "Building.LootingTable": dict(zh="掠夺表", group="build", lo=0, hi=255),
    "Building.TransformUnit": dict(zh="变形为单位", group="build", lo=-1,
                                   hi=2147483647),
    "Building.ConstructionSound": dict(zh="建造音效", group="graphic", lo=-1,
                                       hi=32767),
    "Building.TransformSound": dict(zh="变形音效", group="graphic", lo=-1,
                                    hi=32767),
    "Building.WwiseConstructionSoundID": dict(zh="Wwise 建造音", group="graphic",
                                              lo=0, hi=4294967295, ro=True),
    "Building.WwiseTransformSoundID": dict(zh="Wwise 变形音", group="graphic",
                                           lo=0, hi=4294967295, ro=True),

    # 受损图形
    "DamageGraphics.0.Graphic": dict(zh="受损图形", group="graphic", lo=-1,
                                     hi=32767),
    "DamageGraphics.0.Percent": dict(zh="触发血量百分比", group="graphic", lo=0,
                                     hi=100,
                                     hint="掉到这么多血时换成这张图。"),
    "DamageGraphics.0.ApplyMode": dict(zh="叠加模式", group="graphic", lo=0,
                                       hi=255),

    # 投射物（Type=60 的记录才有）
    "Projectile.ProjectileArc": dict(zh="弹道弧度", group="projectile", lo=0,
                                     hi=255),
    # Type=60 的弹道记录：0 是「智能模式」「命中模式」「消失模式」「范围特效」四
    # 个 u8，取的是 genieutils `src/dat/unit/Projectile.cpp` 的顺序。
    "Projectile.0": dict(zh="智能模式", group="projectile", lo=0, hi=255),
    "Projectile.1": dict(zh="命中模式", group="projectile", lo=0, hi=255),
    "Projectile.2": dict(zh="消失模式", group="projectile", lo=0, hi=255),
    "Projectile.3": dict(zh="范围特效", group="projectile", lo=0, hi=255),

    # 鸟 / 可采集生物的任务表：任务决定它怎么被猎、被赶、被聚集。
    "Bird.DropSites.0": dict(zh="投放点", group="corpse", lo=-1, hi=32767,
                             hint="鸟被打死后掉到哪儿。"),
    "Bird.DropSites": dict(zh="投放点表", group="corpse", ro=True,
                           hint="往下掉的地点清单，行数由数据决定。"),
    "Bird.Tasks.0.ID": dict(zh="任务编号", group="task", lo=0, hi=255),
    "Bird.Tasks.0.TaskType": dict(zh="任务类型", group="task", lo=0, hi=255,
                                  hint="0 无、1 移动、3 驻守、5 采集、7 战斗、8 射击、10 飞走…"),
    "Bird.Tasks.0.ClassID": dict(zh="任务类别编号", group="task", lo=-1,
                                 hi=32767),
    "Bird.Tasks.0.UnitID": dict(zh="任务目标单位", group="task", lo=-1,
                                hi=32767),
    "Bird.Tasks.0.TerrainID": dict(zh="任务地形", group="task", lo=-1,
                                   hi=32767),
    "Bird.Tasks.0.ResourceMultiplier": dict(zh="资源倍率", group="task", lo=-32768,
                                            hi=32767),
    "Bird.Tasks.0.ActionType": dict(zh="动作类型", group="task", lo=0, hi=255),
    "Bird.Tasks.0.IsDefault": dict(zh="默认任务", group="task", enum=BOOL),
    "Bird.Tasks.0.Enabled": dict(zh="启用", group="task", enum=BOOL),
    "Bird.Tasks.0.EnableTargeting": dict(zh="可对目标", group="task", enum=BOOL),
    "Bird.Tasks.0.CombatLevelFlag": dict(zh="战斗等级标记", group="task", lo=0,
                                         hi=255),
    "Bird.Tasks.0.PickForConstruction": dict(zh="可被选去建造", group="task",
                                             enum=BOOL),
    "Bird.Tasks.0.AutoSearchTargets": dict(zh="自动寻找目标", group="task",
                                           enum=BOOL),
    "Bird.Tasks.0.CarryCheck": dict(zh="携带检查", group="task", enum=BOOL),
    "Bird.Tasks.0.ResourceIn": dict(zh="资源输入", group="task", lo=-1,
                                    hi=32767),
    "Bird.Tasks.0.ResourceOut": dict(zh="资源输出", group="task", lo=-1,
                                     hi=32767),
    "Bird.Tasks.0.UnusedResource": dict(zh="未用资源", group="task", lo=-1,
                                        hi=32767),
    "Bird.Tasks.0.GatherType": dict(zh="采集类型", group="task", lo=-1,
                                    hi=32767),
    "Bird.Tasks.0.WorkValue1": dict(zh="工作量 1", group="task", lo=-1,
                                    hi=32767),
    "Bird.Tasks.0.WorkValue2": dict(zh="工作量 2", group="task", lo=-1,
                                    hi=32767),
    "Bird.Tasks.0.WorkRange": dict(zh="工作范围", group="task", lo=0, hi=100,
                                   step=0.5),
    "Bird.Tasks.0.WorkFlag2": dict(zh="工作标记 2", group="task", lo=0, hi=255),
    "Bird.Tasks.0.SearchWaitTime": dict(zh="搜寻等待时间", group="task", lo=0,
                                        hi=255),
    "Bird.Tasks.0.TargetDiplomacy": dict(zh="目标外交关系", group="task", lo=0,
                                         hi=255),
    "Bird.Tasks.0.CarryingGraphic": dict(zh="携带图形", group="task", lo=-1,
                                         hi=32767),
    "Bird.Tasks.0.MovingGraphic": dict(zh="移动图形", group="task", lo=-1,
                                       hi=32767),
    "Bird.Tasks.0.ProceedingGraphic": dict(zh="进行中图形", group="task",
                                           lo=-1, hi=32767),
    "Bird.Tasks.0.WorkingGraphic": dict(zh="工作图形", group="task", lo=-1,
                                        hi=32767),
    "Bird.Tasks.0.DepositSoundID": dict(zh="存放音效", group="task", lo=-1,
                                        hi=32767),
    "Bird.Tasks.0.ResourceGatheringSoundID": dict(zh="采集音效", group="task",
                                                  lo=-1, hi=32767),
    "Bird.Tasks.0.WwiseDepositSoundID": dict(zh="Wwise 存放音", group="task",
                                             lo=0, hi=4294967295, ro=True),
    "Bird.Tasks.0.WwiseGatherSoundID": dict(zh="Wwise 采集音", group="task",
                                            lo=0, hi=4294967295, ro=True),
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
    "TaskType": {0: "无", 1: "移动/攻击", 2: "??", 3: "驻守", 4: "??",
                 5: "采集/建造", 6: "??", 7: "战斗", 8: "射击",
                 9: "??", 10: "飞走", 11: "??", 12: "??", 13: "??",
                 20: "返程卸货", 21: "??", 22: "??"},
    "ActionType": {
        0: "无", 1: "移动", 2: "跟随", 3: "攻击", 4: "??", 5: "采集",
        6: "??", 7: "建造", 8: "??", 9: "治疗", 10: "转换",
        11: "??", 12: "??", 13: "??", 14: "??", 15: "??",
        20: "??", 21: "??", 100: "??", 101: "狩猎", 102: "??",
        103: "采果", 104: "??", 105: "??", 106: "??", 107: "??",
        108: "??", 109: "伐木", 110: "采金", 111: "??", 112: "??",
        113: "??", 114: "??", 115: "??", 116: "??", 117: "??",
        118: "??", 119: "??", 120: "??", 121: "??", 122: "采石",
        123: "??", 124: "??", 125: "??", 130: "??", 131: "??",
        132: "??", 133: "??", 134: "??", 135: "??", 136: "??",
        150: "??", 151: "??", 152: "??", 153: "??", 154: "??",
        155: "??", 159: "??",
    },
    "GatherType": {0: "无", 1: "食物", 2: "木材", 3: "黄金", 4: "石头",
                   5: "兽肉", 6: "鱼", 10: "农田", 23: "??"},
    "TargetDiplomacy": {0: "自己", 1: "盟友", 2: "中立", 3: "敌人",
                        4: "任何人", 5: "??"},
    "ResourceIn": {-1: "无", 0: "食物", 1: "木材", 2: "黄金", 3: "石头",
                   4: "兽肉", 5: "鱼", 9: "??", 15: "食物", 16: "木材",
                   17: "黄金", 56: "??"},
    "ResourceOut": {-1: "无", 0: "食物", 1: "木材", 2: "黄金", 3: "石头"},
    "CarryCheck": {0: "不检查", 1: "检查", 2: "??"},
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
