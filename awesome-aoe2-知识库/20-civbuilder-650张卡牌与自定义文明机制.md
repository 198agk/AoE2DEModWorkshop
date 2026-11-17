# 20 · civbuilder（krakenmeister）650 张卡牌与自定义文明机制全量

> 站点：<https://krakenmeister.com/civbuilder>（社区自定义文明构建器，仍在运营，有 FFA 赛事 "Civbuilder FFA 2"）

> 抓取：2026-11-08。页面 2328 B 空壳，数据全在 `/civbuilder/js/common.js`（95,052 B），用 node `vm` 执行后导出 `_probe/_tmp/civb/civb.json`。


## 0 这个站是什么

它把"做一个新文明"变成了**卡牌抽选**：5 个卡池（数量 [363, 88, 60, 59, 80]），每池抽固定张数（[363, 1, 1, 1, 80]），
抽到的卡牌自动翻译成 `.dat` 里的一堆 effect 记录，最后生成一个真正的 data mod 给你下载。
**这是全表里唯一一个"面向普通玩家、却真的在生成 dat mod"的站**——它的卡牌表因此等价于一份"effect 模组配方库"。


## 1 机制与数据结构

| 键 | 值 | 说明 |
|---|---|---|
| `num_cards` | [363, 88, 60, 59, 80] | 5 个卡池各有多少张卡 |
| `max_sizes` | [363, 1, 1, 1, 80] | 每池最多抽几张 |
| `numCivs` | 50 | 可改的文明数（含 Gaia） |
| `numEditions` | 2 | 2 个 dataset（DE / Chronicles 之类） |
| `rarities` | ['common', 'uncommon', 'rare', 'epic', 'legendary'] | 稀有度 5 档 |
| `rarityTexts` | ['Ordinary', 'Distinguished', 'Superior', 'Epic', 'Legendary'] | 稀有度的显示名 |
| `categories` | ['Color 1', 'Color 2', 'Color 3', 'Color 4', 'Color 5', 'Division', 'Overlay', 'Symbol'] | 徽章/旗帜的 8 个图层 |
| `palette_sizes` | [15, 15, 15, 15, 15, 12, 12, 84] | 各图层的调色板大小 |
| `colours` | 15 组 RGB | 徽章配色 |
| `architectures` | 11 种 | 建筑风格（Central European…Central Asian） |
| `languages` | 43 种 | 语音包 |
| `wonders` | 50 个 | 奇观（每文明一个） |
| `castles` | 50 个 | 城堡模型 |
| `treeMap` | 178 条 | 科技树节点映射 `[nodeIndex, techId]` |
| `unitStats` | 88 个 | 自定义单位的属性模板 |
| `classToName` | 26 条 | 单位 class → 人话（见 §4） |
| `card_descriptions` | [363, 88, 60, 59, 80] 张 | **核心：全部卡牌文案** |

### 1.1 卡牌记录的格式

每张卡是 4 元组：

```js
["Town Centers cost -50% wood starting in the Castle Age", 1, -1, 0]
//  ^文案                                        ^稀有度  ^位置/组  ^dataset(0=DE,1=第二套)
```

第 3 个字段实测范围：池1 `-53..1`、池2 `-53..1`、池3 `-53..1`、池4 `-53..1`、池5 `-53..1`，
是"卡池内的槽位序号"（负数表示整组替换），不是排序键。


### 1.2 `unitStats` 模板（自定义特色单位怎么定义）

```json
{
 "armors": {
  "basic": [
   0,
   0
  ],
  "elite": [
   0,
   1
  ]
 },
 "attacks": {
  "basic": [
   [
    27,
    2
   ],
   [
    3,
    6
   ]
  ],
  "elite": [
   [
    27,
    2
   ],
   [
    3,
    7
   ]
  ]
 },
 "cost": [
  0,
  35,
  0,
  40
 ],
 "hp": [
  35,
  40
 ],
 "range": [
  5,
  6
 ],
 "reload": [
  2
 ],
 "speed": [
  0.96
 ]
}
```

字段含义：`armors.basic/elite = [近防, 远防]`；`attacks = [[classId, 加成值], ...]`（`27`=建筑、`3`=鹰勇士、`4`=普通、`21`=船只、`15`=石墙…）；
`cost = [food, wood, gold, stone]`；`hp/range/reload/speed` 都是 `[普通, 精锐]` 二值数组。

这套结构跟 `.dat` 里 `Unit.attacks[]` / `Unit.armours[]` 的 `Class/Amount` 二元组**完全同构**，所以能直接翻译成 effect。


## 2 全部 650 张卡牌


### 2.1 经济/通用（363 张）

| # | 卡牌文案 | 稀有度 | 槽位 | 套 |
|---|---|---|---|---|
| 1 | Town Centers cost -50% wood starting in the Castle Age | Distinguished 优良 | -1 | 0 |
| 2 | Foot archers (except skirmishers) +1 range in Castle and Imperial Age (+2 total) | Epic 史诗 | -1 | 0 |
| 3 | Shepherds work 25% faster | Distinguished 优良 | -1 | 0 |
| 4 | Castles cost -15% in Castle, -25% in Imperial Age | Superior 精良 | -2 | 0 |
| 5 | Mounted units +20% hit points starting in Feudal Age | Epic 史诗 | -2 | 0 |
| 6 | Foragers work 10% faster | Distinguished 优良 | -2 | 0 |
| 7 | Loom can be researched instantly | Ordinary 普通 | -3 | 0 |
| 8 | Hunters carry +15 meat; hunt contains +20% meat | Distinguished 优良 | -3 | 0 |
| 9 | +10 population in Imperial Age | Ordinary 普通 | -3 | 0 |
| 10 | Infantry +1 attack vs. buildings per age (starting from Feudal Age) | Ordinary 普通 | -3 | 0 |
| 11 | Infantry cost -15% in Dark, -20% in Feudal, -25% in Castle, -30% in Imperial Age | Legendary 传说 | -3 | 0 |
| 12 | Monks double healing range | Ordinary 普通 | -4 | 0 |
| 13 | Towers garrison 2x units; Town Centers garrison +10 | Ordinary 普通 | -4 | 0 |
| 14 | Farms cost -40% | Superior 精良 | -4 | 0 |
| 15 | Barracks and Stable units +1 armor in Castle and Imperial Age (+2 total) | Distinguished 优良 | -4 | 0 |
| 16 | Economic drop-off buildings cost -50% | Distinguished 优良 | -5 | 0 |
| 17 | Fishing Ships 2x hit points; +2P armor; work rate +5% Dark, +10% Feudal, +15% Castle, +20% Imperial Age | Superior 精良 | -5 | 0 |
| 18 | Infantry attack 33% faster starting in Feudal Age | Distinguished 优良 | -5 | 0 |
| 19 | Start with +3 villagers, -50 wood, -200 food; Town Centers support 15 population and +7 LOS | Superior 精良 | -6 | 0 |
| 20 | Demolition ships +50% hit points | Ordinary 普通 | 1 | 0 |
| 21 | Technologies cost -5% Feudal, -10% Castle, -15% Imperial Age | Superior 精良 | -6 | 0 |
| 22 | Buildings +10% HP Dark, +20% Feudal, +30% Castle, +40% Imperial Age | Distinguished 优良 | -7 | 0 |
| 23 | Fire ships attack 25% faster | Ordinary 普通 | -7 | 0 |
| 24 | Camel Riders, Skirmishers, Pikemen, Halberdiers cost -25% | Superior 精良 | -7 | 0 |
| 25 | Start with +50 wood, food | Ordinary 普通 | -8 | 0 |
| 26 | Town Center, Dock 2x hit points | Ordinary 普通 | -8 | 0 |
| 27 | Town Center, Dock work rate +5% Dark, +10% Feudal, +15% Castle, +20% Imperial Age | Superior 精良 | -8 | 0 |
| 28 | Market costs -100 wood; market trade cost only 5% | Distinguished 优良 | -9 | 0 |
| 29 | Transport Ships 2x hit points, +20 carry capacity | Ordinary 普通 | -9 | 0 |
| 30 | Galleys attack 25% faster | Distinguished 优良 | -9 | 0 |
| 31 | Camel units +25% hit points | Superior 精良 | -9 | 0 |
| 32 | Gunpowder units +25% hit points | Superior 精良 | -10 | 0 |
| 33 | Gold miners work 25% faster | Distinguished 优良 | -10 | 0 |
| 34 | Scout Cavalry, Light Cavalry, Hussar +1 pierce armor | Distinguished 优良 | -10 | 0 |
| 35 | Warships cost -15% Feudal Age, -15% Castle Age, -20% Imperial Age | Superior 精良 | -11 | 0 |
| 36 | Infantry +20% hit points starting in Feudal Age | Distinguished 优良 | -11 | 0 |
| 37 | Cavalry archers fire 25% faster | Superior 精良 | -12 | 0 |
| 38 | Hunters work 40% faster | Epic 史诗 | -12 | 0 |
| 39 | Light Cavalry, Hussars, Steppe Lancers +20/30% hit points in Castle/Imperial Age | Distinguished 优良 | -12 | 0 |
| 40 | Infantry moves +5/10/15/20% faster in Dark/Feudal/Castle/Imperial Age | Distinguished 优良 | -13 | 0 |
| 41 | Lumberjacks work 15% faster | Superior 精良 | -13 | 0 |
| 42 | Siege units fire 25% faster | Superior 精良 | -13 | 0 |
| 43 | Can steal sheep, and sheep within one unit's LoS cannot be stolen | Ordinary 普通 | -13 | 0 |
| 44 | Missionaries can be trained in monasteries | Distinguished 优良 | -14 | 0 |
| 45 | Start with +50 gold | Ordinary 普通 | -15 | 0 |
| 46 | +5 Monk hit points for each Monastery technology | Epic 史诗 | -15 | 0 |
| 47 | Start with +1 villager, but -50 food | Distinguished 优良 | -16 | 0 |
| 48 | Cavalry Archers cost -10% Castle, -20% Imperial Age | Superior 精良 | -17 | 0 |
| 49 | Ranged Soldiers, Infantry, and Warships cost -50% wood | Superior 精良 | -18 | 0 |
| 50 | Archer armor upgrades free | Distinguished 优良 | -18 | 0 |
| 51 | Can train Turtle Ships in docks | Ordinary 普通 | -18 | 0 |
| 52 | Can recruit Longboats from docks | Superior 精良 | -11 | 0 |
| 53 | Gunpowder units cost -20% | Superior 精良 | -19 | 0 |
| 54 | Can upgrade Heavy Camel Riders to Imperial Camel Riders | Superior 精良 | -20 | 0 |
| 55 | Fishermen work 10% faster | Ordinary 普通 | 1 | 0 |
| 56 | Stable units +1P armor in Castle and Imperial Age (+2 total) | Superior 精良 | 1 | 0 |
| 57 | Villagers cost -8% Dark, -13% Feudal, -18% Castle, -23% Imperial Age | Superior 精良 | -20 | 0 |
| 58 | Military units cost -10, 15, 20, 25% food in Dark, Feudal, Castle, Imperial | Legendary 传说 | -21 | 0 |
| 59 | Buildings cost -15% stone | Distinguished 优良 | -21 | 0 |
| 60 | Houses support 10 population | Ordinary 普通 | -21 | 0 |
| 61 | Villagers affected by Blacksmith upgrades starting in the Castle Age | Ordinary 普通 | -21 | 0 |
| 62 | Can recruit slingers from Archery Ranges | Distinguished 优良 | -21 | 0 |
| 63 | Villagers kill wolves with 1 strike | Ordinary 普通 | -22 | 0 |
| 64 | Scout Cavalry, Light Cavalry, Hussar cost -15% | Distinguished 优良 | -22 | 0 |
| 65 | Siege Workshop units 15% cheaper | Distinguished 优良 | -23 | 0 |
| 66 | All units cost -20% gold | Legendary 传说 | -24 | 0 |
| 67 | Foragers generate a trickle of wood (33%) | Distinguished 优良 | -24 | 0 |
| 68 | Ships +10% HP | Distinguished 优良 | -24 | 0 |
| 69 | Can build Feitoria in Imperial Age | Epic 史诗 | -24 | 0 |
| 70 | Can build Caravels in docks | Distinguished 优良 | -24 | 0 |
| 71 | Foot archers fire 18% faster | Superior 精良 | -25 | 0 |
| 72 | Receive +100 gold, +100 food when advancing to the next age | Superior 精良 | -25 | 0 |
| 73 | Pikeman upgrade free | Ordinary 普通 | -25 | 0 |
| 74 | Buildings cost -15% wood | Distinguished 优良 | -26 | 0 |
| 75 | Barracks units +1 pierce armor per age (starting from Feudal Age) | Superior 精良 | -26 | 0 |
| 76 | Villagers drop off 10% more gold | Distinguished 优良 | -26 | 0 |
| 77 | Villagers move 5% faster in Dark Age, 10% faster in Feudal Age | Distinguished 优良 | -27 | 0 |
| 78 | Ships move 10% faster | Ordinary 普通 | -27 | 0 |
| 79 | Stable units cost -15% in Castle, -20% in Imperial Age | Epic 史诗 | -27 | 0 |
| 80 | Melee elephant units move 10% faster | Distinguished 优良 | -28 | 0 |
| 81 | Villagers can garrison in Houses | Ordinary 普通 | -28 | 0 |
| 82 | No buildings required to advance to the next age or to unlock other buildings | Superior 精良 | -28 | 0 |
| 83 | Advance to the next age 66% faster | Epic 史诗 | -29 | 0 |
| 84 | Elephant units cost -25% Castle, -35% in Imperial Age | Legendary 传说 | -29 | 0 |
| 85 | Fish Traps cost -33% and provide +200% food | Ordinary 普通 | -29 | 0 |
| 86 | Foot Archers and Condottieri +1 melee/+1 pierce armor | Distinguished 优良 | -19 | 0 |
| 87 | Lumber Camp upgrades free | Superior 精良 | -30 | 0 |
| 88 | Infantry +1 attack per age (starting in the Feudal Age) | Distinguished 优良 | -30 | 0 |
| 89 | Monastery technologies cost -50% | Distinguished 优良 | -30 | 0 |
| 90 | Enemy positions are revealed at the start of the game | Ordinary 普通 | -31 | 0 |
| 91 | Archery Range units and Fire Lancers +20% HP | Superior 精良 | -31 | 0 |
| 92 | Militia-line upgrades free | Epic 史诗 | -32 | 0 |
| 93 | Town Centers cost -50% stone starting in the Castle Age | Ordinary 普通 | -32 | 0 |
| 94 | Can build Krepost | Superior 精良 | -32 | 0 |
| 95 | Livestock animals last +50% longer | Ordinary 普通 | -33 | 0 |
| 96 | Units deal +25% damage when fighting from higher elevation | Ordinary 普通 | -33 | 0 |
| 97 | Thumb Ring, Parthian Tactics free | Distinguished 优良 | -33 | 0 |
| 98 | Mounted units 5% faster each age (starting in Feudal Age) | Superior 精良 | -34 | 0 |
| 99 | Additional Town Center can be built in the Feudal Age | Distinguished 优良 | -34 | 0 |
| 100 | Siege Workshop and Battering Ram available in the Feudal Age; Capped Ram upgrade available in Castle Age | Distinguished 优良 | -34 | 0 |
| 101 | Receive +100 food per Town Center | Distinguished 优良 | -35 | 0 |
| 102 | Spearmen and Skirmishers move 10% faster | Distinguished 优良 | -35 | 0 |
| 103 | Each garrisoned relic gives +1 attack to Knights and Unique Unit (maximum +4) | Superior 精良 | -35 | 0 |
| 104 | Cavalier upgrade available in Castle Age | Superior 精良 | -36 | 0 |
| 105 | Gunpowder units +25% attack | Superior 精良 | -36 | 0 |
| 106 | Economic upgrades cost -33% food and available one age earlier | Superior 精良 | -36 | 0 |
| 107 | Fortifications built 50%, Town Centers built 100% faster | Distinguished 优良 | -37 | 0 |
| 108 | Soldiers receive 40% less bonus damage | Legendary 传说 | -37 | 0 |
| 109 | Farm upgrades provide +125% additional food | Ordinary 普通 | -37 | 0 |
| 110 | Can build Donjon | Superior 精良 | -37 | 0 |
| 111 | Farm upgrades free (require Mill) | Distinguished 优良 | -2 | 0 |
| 112 | Forging, Iron Casting, Blast Furnace free | Distinguished 优良 | -22 | 0 |
| 113 | Arson and Gambesons free | Distinguished 优良 | -23 | 0 |
| 114 | Town Watch, Town Patrol free | Ordinary 普通 | -7 | 0 |
| 115 | Murder Holes, Herbal Medicine free | Ordinary 普通 | -4 | 0 |
| 116 | Chemistry free | Superior 精良 | -10 | 0 |
| 117 | Light Cavalry and Hussar upgrades free | Distinguished 优良 | -10 | 0 |
| 118 | Wheelbarrow, Hand Cart free | Epic 史诗 | -11 | 0 |
| 119 | Tower upgrades free (Bombard Tower requires Chemistry) | Superior 精良 | -18 | 0 |
| 120 | Conscription free | Ordinary 普通 | -31 | 0 |
| 121 | Farmers work 15% faster | Superior 精良 | -23 | 0 |
| 122 | Advancing to the next age costs -15% | Distinguished 优良 | -19 | 0 |
| 123 | Fishing Ships cost -15% | Distinguished 优良 | -19 | 0 |
| 124 | Dock and University technologies cost -33% | Ordinary 普通 | -19 | 0 |
| 125 | Advancing to Imperial Age costs -33% | Ordinary 普通 | -7 | 0 |
| 126 | Blacksmith upgrades don't cost gold | Distinguished 优良 | -14 | 0 |
| 127 | Gunpowder units fire 18% faster | Distinguished 优良 | -14 | 0 |
| 128 | Builders work 30% faster | Distinguished 优良 | -14 | 0 |
| 129 | Military units train +15% faster | Distinguished 优良 | -15 | 0 |
| 130 | Villagers carry +3 | Distinguished 优良 | -15 | 0 |
| 131 | Trebuchet units fire more accurately at units and small targets | Ordinary 普通 | -17 | 0 |
| 132 | Do not need houses, -100 wood | Distinguished 优良 | -17 | 0 |
| 133 | Resources last 15% longer | Distinguished 优良 | -16 | 0 |
| 134 | Foot archers and skirmishers cost -10% Feudal, -20% Castle, -30% Imperial Age | Epic 史诗 | -16 | 0 |
| 135 | Lumberjacks generate food in addition to wood | Superior 精良 | -49 | 0 |
| 136 | Stone miners work 20% faster | Distinguished 优良 | -18 | 0 |
| 137 | Economic upgrades cost no wood and research +100% faster | Ordinary 普通 | -31 | 0 |
| 138 | Blacksmith and Siege Workshop technologies cost -50% food | Distinguished 优良 | -32 | 0 |
| 139 | Stable technologies cost -50% | Distinguished 优良 | -36 | 0 |
| 140 | New Town Centers spawn 2 sheep starting in the Castle Age | Ordinary 普通 | -33 | 0 |
| 141 | Wonders don't cost wood and provide +50 to population limit (max 1) | Superior 精良 | 1 | 0 |
| 142 | Villagers +3 HP per economic tech researched | Distinguished 优良 | 1 | 0 |
| 143 | Villagers regenerate 10 HP/min in Feudal, 15 in Castle, 20 in Imperial Age | Distinguished 优良 | -38 | 0 |
| 144 | Military buildings built 100% faster | Ordinary 普通 | 1 | 0 |
| 145 | Resource drop-off buildings provide +5 population space | Ordinary 普通 | 1 | 0 |
| 146 | Ballistics researched instantly and costs no wood | Distinguished 优良 | 1 | 0 |
| 147 | Archer-line upgrades free | Superior 精良 | 1 | 0 |
| 148 | Skirmisher-line upgrades free | Distinguished 优良 | 1 | 0 |
| 149 | Camel-line upgrades free | Superior 精良 | 1 | 0 |
| 150 | Infantry Armor upgrades free | Distinguished 优良 | -29 | 0 |
| 151 | Cavalry Armor upgrades free | Epic 史诗 | 1 | 0 |
| 152 | Fletching, Bodkin Arrow, Bracer free | Legendary 传说 | 1 | 0 |
| 153 | Redemption free | Superior 精良 | 1 | 0 |
| 154 | Squires free | Ordinary 普通 | 1 | 0 |
| 155 | Eagle-line upgrades free | Epic 史诗 | 1 | 0 |
| 156 | Battle Elephant upgrades free | Epic 史诗 | 1 | 0 |
| 157 | Sanctity, Fervor free | Superior 精良 | 1 | 0 |
| 158 | Atonement, Illumination free | Distinguished 优良 | 1 | 0 |
| 159 | Theocracy, Block Printing free | Superior 精良 | 1 | 0 |
| 160 | Hoardings, Fortified Wall free | Ordinary 普通 | 1 | 0 |
| 161 | Masonry, Architecture free | Ordinary 普通 | 1 | 0 |
| 162 | Mining Camp technologies free | Superior 精良 | -39 | 0 |
| 163 | Sappers, Treadmill Crane free | Ordinary 普通 | 1 | 0 |
| 164 | Galleon free | Distinguished 优良 | 1 | 0 |
| 165 | Careening, Dry Dock free | Ordinary 普通 | 1 | 0 |
| 166 | Fast Fire Ship free | Distinguished 优良 | 1 | 0 |
| 167 | Heavy Demolition Ship free | Distinguished 优良 | 1 | 0 |
| 168 | Gillnets free | Distinguished 优良 | 1 | 0 |
| 169 | War Galley free | Distinguished 优良 | 1 | 0 |
| 170 | Heavy Cavalry Archer free | Superior 精良 | 1 | 0 |
| 171 | Ram-line upgrades free | Epic 史诗 | 1 | 0 |
| 172 | Trade units 20% faster | Superior 精良 | 1 | 0 |
| 173 | Squires affects foot archers and skirmishers | Distinguished 优良 | 1 | 0 |
| 174 | Shock Infantry +5% speed per age (starting in Feudal Age) | Superior 精良 | 1 | 0 |
| 175 | Start with +150 wood | Distinguished 优良 | 1 | 0 |
| 176 | Start with +100 stone | Distinguished 优良 | -37 | 0 |
| 177 | Start with +50 wood, +50 stone | Ordinary 普通 | 1 | 0 |
| 178 | Start with +70 food, +30 gold | Distinguished 优良 | 1 | 0 |
| 179 | Monk units train 66% faster | Distinguished 优良 | 1 | 0 |
| 180 | Trebuchet units train 50% faster | Ordinary 普通 | 1 | 0 |
| 181 | Cavalry Archers train 33% faster | Ordinary 普通 | 1 | 0 |
| 182 | Land explosive units train 200% faster | Ordinary 普通 | 1 | 0 |
| 183 | Land explosive units +8 pierce armor | Ordinary 普通 | 1 | 0 |
| 184 | Bloodlines free in Castle Age | Ordinary 普通 | 1 | 0 |
| 185 | Galleys +1 range | Distinguished 优良 | 1 | 0 |
| 186 | Receive +100 wood, +100 stone when advancing to the next age | Superior 精良 | 1 | 0 |
| 187 | Receive +400 food upon advancing to Castle Age | Superior 精良 | 1 | 0 |
| 188 | Receive +350 stone upon advancing to Castle Age | Superior 精良 | 1 | 0 |
| 189 | Receive +250 wood upon reaching Feudal Age | Superior 精良 | 1 | 0 |
| 190 | Receive +500 gold upon reaching Imperial Age | Superior 精良 | 1 | 0 |
| 191 | +100 HP and pierce armor for monks with relics | Ordinary 普通 | 1 | 0 |
| 192 | Land explosive units 2x HP | Ordinary 普通 | 1 | 0 |
| 193 | Town Centers spawn 2 villagers when the next Age is reached | Epic 史诗 | -41 | 0 |
| 194 | Can recruit Warrior Priests | Distinguished 优良 | -44 | 0 |
| 195 | Castles and Kreposts +2000 HP | Distinguished 优良 | 1 | 0 |
| 196 | Blacksmith upgrades are free an age after they become available | Distinguished 优良 | 1 | 0 |
| 197 | Barracks cost -75 wood | Distinguished 优良 | 1 | 0 |
| 198 | Stables cost -75 wood | Distinguished 优良 | -34 | 0 |
| 199 | Archery Ranges cost -75 wood | Distinguished 优良 | -34 | 0 |
| 200 | Monasteries cost -100 wood | Distinguished 优良 | 1 | 0 |
| 201 | Siege Workshops cost -100 wood | Distinguished 优良 | 1 | 0 |
| 202 | Military Buildings cost -50 wood | Distinguished 优良 | 1 | 0 |
| 203 | Blacksmiths and Universities cost -100 wood | Ordinary 普通 | -39 | 0 |
| 204 | Infantry +1 attack vs. villagers per age (starting in Dark Age) | Ordinary 普通 | 1 | 0 |
| 205 | Fishermen and Fishing Ships carry +15 | Distinguished 优良 | -40 | 0 |
| 206 | Galleys +1 attack | Distinguished 优良 | 1 | 0 |
| 207 | Steppe Lancers +10 attack vs. villagers | Superior 精良 | 1 | 0 |
| 208 | Steppe Lancers attack 33% faster | Distinguished 优良 | 1 | 0 |
| 209 | Elephant units attack 25% faster | Distinguished 优良 | 1 | 0 |
| 210 | Stone Walls available in Dark Age | Ordinary 普通 | 1 | 0 |
| 211 | Receive +50 food, +50 wood, +50 stone, +50 gold when advancing to the next age | Superior 精良 | 1 | 0 |
| 212 | Villagers return 25 food on death | Ordinary 普通 | 1 | 0 |
| 213 | Camel units attack 20% faster | Distinguished 优良 | -20 | 0 |
| 214 | Mangonels can cut trees | Distinguished 优良 | 1 | 0 |
| 215 | Can train a free Siege Tower in Feudal Age; Siege Towers cost -50% | Superior 精良 | 1 | 0 |
| 216 | Rams, Siege Towers x2 garrison space | Superior 精良 | 1 | 0 |
| 217 | Towers support 15 population | Ordinary 普通 | 1 | 0 |
| 218 | Gunpowder units move 20% faster | Superior 精良 | 1 | 0 |
| 219 | Completed castles provide 400 gold as long as they stay standing | Distinguished 优良 | 1 | 0 |
| 220 | Monk units move 20% faster | Superior 精良 | -23 | 0 |
| 221 | Melee Cavalry gain +2 bonus damage vs Skirmishers | Ordinary 普通 | 1 | 0 |
| 222 | Spearman- and Militia-line upgrades (except Man-at-Arms) available one age earlier | Distinguished 优良 | -44 | 0 |
| 223 | Can buy cows in mills | Distinguished 优良 | 1 | 0 |
| 224 | Start with an extra horse | Distinguished 优良 | -17 | 0 |
| 225 | Siege Towers 2x HP | Distinguished 优良 | 1 | 0 |
| 226 | Siege Towers train 100% faster | Ordinary 普通 | 1 | 0 |
| 227 | Siege units cost -33% wood | Distinguished 优良 | -40 | 0 |
| 228 | Cannon Galleons benefit from Ballistics (fire faster, more accurately) | Distinguished 优良 | -14 | 0 |
| 229 | Warships +10 attack vs. villagers | Ordinary 普通 | 1 | 0 |
| 230 | Rams generate stone by ramming | Epic 史诗 | 1 | 0 |
| 231 | Town Centers +50% work rate in Imperial Age | Superior 精良 | 1 | 0 |
| 232 | Feudal Age costs -25% | Distinguished 优良 | 1 | 0 |
| 233 | Spearmen and Skirmishers train 50% faster | Distinguished 优良 | 1 | 0 |
| 234 | Spearmen +25% HP | Distinguished 优良 | 1 | 0 |
| 235 | Market techs cost no gold | Ordinary 普通 | 1 | 0 |
| 236 | Trees contain double the amount of wood | Distinguished 优良 | 1 | 0 |
| 237 | Stone resources last 30% longer | Distinguished 优良 | 1 | 0 |
| 238 | Gold resources last 30% longer | Distinguished 优良 | 1 | 0 |
| 239 | Berries contain +35% more food | Distinguished 优良 | 1 | 0 |
| 240 | Can upgrade Fortified Walls to City Walls in Imperial Age | Superior 精良 | 1 | 0 |
| 241 | Fish contain +35% more food | Distinguished 优良 | 1 | 0 |
| 242 | Units garrisoned in buildings heal 2x faster | Ordinary 普通 | 1 | 0 |
| 243 | Repairers work 100% faster | Distinguished 优良 | 1 | 0 |
| 244 | Skirmishers +1 attack vs. infantry | Ordinary 普通 | 1 | 0 |
| 245 | Archery Range units +1 attack | Epic 史诗 | 1 | 0 |
| 246 | Archery range units +1 melee armor per age (starting in Feudal) | Superior 精良 | 1 | 0 |
| 247 | Siege units +1 pierce armor in Castle and Imperial (+2 total) | Distinguished 优良 | 1 | 0 |
| 248 | Parthian Tactics available in Castle Age | Distinguished 优良 | 1 | 0 |
| 249 | Castle Age costs -25% | Distinguished 优良 | 1 | 0 |
| 250 | Cavalry +1 attack | Distinguished 优良 | 1 | 0 |
| 251 | Forging, Iron Casting, Blast Furnace add +1 damage vs. buildings | Distinguished 优良 | 1 | 0 |
| 252 | All buildings +3 pierce armor | Ordinary 普通 | 1 | 0 |
| 253 | Foot archers +5% speed per age (starting in Feudal) | Superior 精良 | 1 | 0 |
| 254 | Foot archers and skirmishers +1 attack vs. villagers | Distinguished 优良 | 1 | 0 |
| 255 | Gunpowder +10 attack vs. camels | Ordinary 普通 | 1 | 0 |
| 256 | Shock Infantry +6 attack vs. stone defenses | Ordinary 普通 | 1 | 0 |
| 257 | Scouts, Light Cavalry, Hussar +4 attack vs. stone defenses | Ordinary 普通 | 1 | 0 |
| 258 | All villagers work 5% faster | Superior 精良 | -43 | 0 |
| 259 | Villagers +1 carry capacity per Town Center technology researched | Distinguished 优良 | 1 | 0 |
| 260 | Farms 10x HP | Ordinary 普通 | 1 | 0 |
| 261 | Militia-line +2 attack vs. cavalry | Distinguished 优良 | 1 | 0 |
| 262 | Steppe Lancer upgrades free | Distinguished 优良 | 1 | 0 |
| 263 | Steppe Lancers +2 pierce armor | Distinguished 优良 | 1 | 0 |
| 264 | Castles and Kreposts deal large damage against buildings | Superior 精良 | 1 | 0 |
| 265 | All villagers work 10% faster in Imperial Age | Superior 精良 | 1 | 0 |
| 266 | Outposts +5 garrison capacity | Ordinary 普通 | 1 | 0 |
| 267 | Villagers +10 pierce armor while building or repairing | Ordinary 普通 | 1 | 0 |
| 268 | Castles and Kreposts support 50 population | Ordinary 普通 | 1 | 0 |
| 269 | Bombard towers deal extra damage to rams | Distinguished 优良 | 1 | 0 |
| 270 | Towers deal extra damage to cavalry | Superior 精良 | 1 | 0 |
| 271 | Can build Monastery in Feudal Age; Monks recruited in Feudal Age have longer conversions and cannot pickup relics | Distinguished 优良 | 1 | 0 |
| 272 | Scorpions, Ballista Elephants, and War Wagons train 50% faster | Ordinary 普通 | 1 | 0 |
| 273 | Town Centers fire 25% faster | Ordinary 普通 | 1 | 0 |
| 274 | Trebuchet units cost -50% gold | Ordinary 普通 | 1 | 0 |
| 275 | All explosive units 2x blast radius | Ordinary 普通 | 1 | 0 |
| 276 | Gunpowder units +8 attack vs. buildings | Ordinary 普通 | 1 | 0 |
| 277 | Shock Infantry +1 pierce armor | Ordinary 普通 | 1 | 0 |
| 278 | Gunpowder units +5% attack per university technology researched (cumulative) | Epic 史诗 | 1 | 0 |
| 279 | Buildings +3% HP per university technology researched (cumulative) | Distinguished 优良 | 1 | 0 |
| 280 | Each monastery technology researched brings a monk to your cause | Epic 史诗 | 1 | 0 |
| 281 | Folwark replaces Mill | Distinguished 优良 | -38 | 0 |
| 282 | Stone Miners generate gold in addition to stone | Superior 精良 | -38 | 0 |
| 283 | Winged Hussar replaces Hussar | Distinguished 优良 | -38 | 0 |
| 284 | Chemistry and Hand Cannoneer available in Castle Age | Distinguished 优良 | -39 | 0 |
| 285 | Spearmen deals +25% bonus damage | Distinguished 优良 | -39 | 0 |
| 286 | Fervor and Sanctity affects villagers | Ordinary 普通 | -39 | 0 |
| 287 | Can upgrade Bombard Cannons to Houfnice | Epic 史诗 | -39 | 0 |
| 288 | Can build Caravanseri in Imperial Age | Distinguished 优良 | -20 | 0 |
| 289 | Gunpowder units +1/+1P armor | Distinguished 优良 | -20 | 0 |
| 290 | Receive +200 wood when advancing to the next age | Superior 精良 | -40 | 0 |
| 291 | Barracks technologies cost -50% | Distinguished 优良 | -40 | 0 |
| 292 | Skirmishers and Elephant Archers attack 25% faster | Distinguished 优良 | -40 | 0 |
| 293 | Elephant units receive 25% less bonus damage and are more resistant to conversion | Distinguished 优良 | -41 | 0 |
| 294 | Ships regenerate 15 HP per minute | Ordinary 普通 | -41 | 0 |
| 295 | Start with 2 Forage Bushes | Distinguished 优良 | -42 | 0 |
| 296 | Can garrison Mills with livestock to produce food | Distinguished 优良 | -42 | 0 |
| 297 | Mounted units deal +20% bonus damage Feudal, +30% Castle, +40% Imperial Age | Distinguished 优良 | -42 | 0 |
| 298 | Can garrison Docks with Fishing Ships | Distinguished 优良 | -42 | 0 |
| 299 | Can train Thirisadai in docks | Distinguished 优良 | -40 | 0 |
| 300 | Can recruit Shrivamsha Riders | Superior 精良 | -42 | 0 |
| 301 | Can recruit Camel Scouts in Feudal Age | Distinguished 优良 | -42 | 0 |
| 302 | Gain 20 gold for each technology researched | Distinguished 优良 | -14 | 0 |
| 303 | Galley-line and Dromons +1/+1 armor | Distinguished 优良 | -43 | 0 |
| 304 | Battle elephants +1/+1P armor | Superior 精良 | -30 | 0 |
| 305 | Monk units +3/+3P armor | Superior 精良 | -41 | 0 |
| 306 | Infantry receives double effect from Blacksmith armor upgrades | Epic 史诗 | -43 | 0 |
| 307 | Scorpions cost -50% gold and benefit from Ballistics research | Superior 精良 | -43 | 0 |
| 308 | Legionary replaces Two-Handed Swordsman / Champion | Ordinary 普通 | -43 | 0 |
| 309 | Can upgrade Heavy Scorpions to Imperial Scorpions | Epic 史诗 | 1 | 0 |
| 310 | Can upgrade Elite Battle Elephants to Royal Battle Elephants | Legendary 传说 | 1 | 0 |
| 311 | Can upgrade Elite Steppe Lancers to Royal Lancers | Epic 史诗 | 1 | 0 |
| 312 | Cavalry Archers +2 attack vs. Ranged Soldiers (except skirmishers) | Distinguished 优良 | -5 | 0 |
| 313 | Wood and mining upgrades are 40% more effective, economic drop-off buildings cost -25% | Legendary 传说 | -44 | 0 |
| 314 | First religious building receives a free relic | Distinguished 优良 | -44 | 0 |
| 315 | Savar replaces Paladin | Superior 精良 | -8 | 0 |
| 316 | Galley-line and Dromons fire an additional projectile | Distinguished 优良 | -44 | 0 |
| 317 | Fortified church replaces monastery | Superior 精良 | -44 | 0 |
| 318 | Mule Carts replace Lumber Camps and Mining Camps | Distinguished 优良 | -44 | 0 |
| 319 | Start with a Mule Cart | Superior 精良 | -45 | 0 |
| 320 | Religious buildings provide Villagers in an 8 tile radius with +10% work rate | Distinguished 优良 | -45 | 0 |
| 321 | Units and buildings receive -15% damage when fighting from higher elevation | Distinguished 优良 | -45 | 0 |
| 322 | Mounted units regenerate 2/8/14 HP per minute, in the Feudal, Castle, Imperial Age | Epic 史诗 | -45 | 0 |
| 323 | Flaming Camels available in Siege Workshops in Imperial Age | Ordinary 普通 | -33 | 0 |
| 324 | All buildings refund +1 stone per tile of foundation | Epic 史诗 | 1 | 0 |
| 325 | Villagers work faster when nearby other villagers | Superior 精良 | 1 | 0 |
| 326 | Husbandry affects attack speed | Distinguished 优良 | 1 | 0 |
| 327 | Trade yields 10% stone in addition to gold | Distinguished 优良 | 1 | 0 |
| 328 | Blacksmith upgrades affect bonus damage | Epic 史诗 | 1 | 0 |
| 329 | Cavalry archers can dodge one projectile | Distinguished 优良 | 1 | 0 |
| 330 | Farmers don't require Mills/Town Centers to drop off food | Distinguished 优良 | -28 | 0 |
| 331 | Farms are smaller | Distinguished 优良 | 1 | 0 |
| 332 | Archery range techs cost -50% | Ordinary 普通 | 1 | 0 |
| 333 | Knights available in Feudal Age with 30HP | Superior 精良 | 1 | 0 |
| 334 | Siege Towers can fire arrows | Superior 精良 | 1 | 0 |
| 335 | Fire Lancers and Fire Ships move +5/10% faster in Castle/Imperial Age | Distinguished 优良 | -6 | 0 |
| 336 | Archery Unit technologies at the Archery Range and Blacksmith cost -25% | Ordinary 普通 | -49 | 0 |
| 337 | Siege Weapons and Siege Warships move +10/15% faster in Castle/Imperial Age | Distinguished 优良 | -49 | 0 |
| 338 | Can recruit War Chariots | Superior 精良 | -49 | 0 |
| 339 | Gain access to Liu Bei | Epic 史诗 | -49 | 0 |
| 340 | Military production buildings and Docks provide +55 food | Distinguished 优良 | -50 | 0 |
| 341 | Infantry regenerates 10/20/30 HP per minute in Feudal/Castle/Imperial Age | Superior 精良 | -50 | 0 |
| 342 | Shock Infantry and Hei Guang Cavalry +2 attack in Imperial Age | Distinguished 优良 | -50 | 0 |
| 343 | Careening, Dry Dock available one age earlier, cost and research time -75% | Superior 精良 | -50 | 0 |
| 344 | Can recruit Jian Swordsmen | Superior 精良 | -50 | 0 |
| 345 | Gain access to Sun Jian | Epic 史诗 | -50 | 0 |
| 346 | Receive one free Villager for each economic upgrade researched | Epic 史诗 | -51 | 0 |
| 347 | Hei Guang Cavalry and Xianbei Raider +15/30% HP in Castle/Imperial Age | Distinguished 优良 | -51 | 0 |
| 348 | Trebuchet units cost -25% | Distinguished 优良 | -51 | 0 |
| 349 | Can recruit Xianbei Raiders | Superior 精良 | -51 | 0 |
| 350 | Gain access to Cao Cao | Epic 史诗 | -51 | 0 |
| 351 | Meat of hunted and livestock animals doesn't decay | Ordinary 普通 | -52 | 0 |
| 352 | Mounted units and Fire Lancers attack +25% faster starting in Feudal Age | Epic 史诗 | -52 | 0 |
| 353 | Siege Engineers available in Castle Age | Superior 精良 | -52 | 0 |
| 354 | Siege and Fortification upgrades cost -75% wood and research +100% faster | Distinguished 优良 | -52 | 0 |
| 355 | Units receive -50% friendly fire damage | Ordinary 普通 | -52 | 0 |
| 356 | Can recruit Grenadiers | Superior 精良 | -52 | 0 |
| 357 | Pastures replace Farms and Mill upgrades | Superior 精良 | -53 | 0 |
| 358 | REDACTED | Distinguished 优良 | -53 | 0 |
| 359 | Melee attack upgrade effects are doubled | Superior 精良 | -53 | 0 |
| 360 | Skirmishers, Spearman- and Scout Cavalry-line train and upgrade +15% faster | Distinguished 优良 | -53 | 0 |
| 361 | Heavy Cavalry Archer upgrade available in Castle Age and costs -50% | Distinguished 优良 | -53 | 0 |
| 362 | Can train Mounted Trebuchets | Superior 精良 | -53 | 0 |
| 363 | Dragon Ships replace Fast Fire Ships | Superior 精良 | -6 | 0 |

### 2.2 特色单位（88 张）

| # | 卡牌文案 | 稀有度 | 槽位 | 套 |
|---|---|---|---|---|
| 1 | Longbowmen | Superior 精良 | -1 | 0 |
| 2 | Throwing Axemen | Ordinary 普通 | -2 | 0 |
| 3 | Huskarls | Distinguished 优良 | -3 | 0 |
| 4 | Teutonic Knights | Superior 精良 | -4 | 0 |
| 5 | Samurai | Distinguished 优良 | -5 | 0 |
| 6 | Chu Ko Nu | Distinguished 优良 | -6 | 0 |
| 7 | Cataphracts | Distinguished 优良 | -7 | 0 |
| 8 | Mamelukes | Distinguished 优良 | -9 | 0 |
| 9 | War Elephants | Epic 史诗 | -8 | 0 |
| 10 | Janissaries | Superior 精良 | -10 | 0 |
| 11 | Berserks | Distinguished 优良 | -11 | 0 |
| 12 | Mangudai | Legendary 传说 | -12 | 0 |
| 13 | Woad Raiders | Ordinary 普通 | -13 | 0 |
| 14 | Conquistadors | Superior 精良 | -14 | 0 |
| 15 | Jaguar Warriors | Ordinary 普通 | -15 | 0 |
| 16 | Plumed Archers | Distinguished 优良 | -16 | 0 |
| 17 | Tarkans | Ordinary 普通 | -17 | 0 |
| 18 | War Wagons | Ordinary 普通 | -18 | 0 |
| 19 | Genoese Crossbowmen | Distinguished 优良 | -19 | 0 |
| 20 | Ghulam | Ordinary 普通 | -20 | 0 |
| 21 | Kamayuks | Ordinary 普通 | -21 | 0 |
| 22 | Magyar Huszars | Ordinary 普通 | -22 | 0 |
| 23 | Boyars | Superior 精良 | -23 | 0 |
| 24 | Organ Guns | Epic 史诗 | -24 | 0 |
| 25 | Shotel Warriors | Ordinary 普通 | -25 | 0 |
| 26 | Gbetos | Ordinary 普通 | -26 | 0 |
| 27 | Camel Archers | Epic 史诗 | -27 | 0 |
| 28 | Ballista Elephants | Legendary 传说 | -28 | 0 |
| 29 | Karambit Warriors | Ordinary 普通 | -29 | 0 |
| 30 | Arambai | Distinguished 优良 | -30 | 0 |
| 31 | Rattan Archers | Distinguished 优良 | -31 | 0 |
| 32 | Konniks | Distinguished 优良 | -32 | 0 |
| 33 | Keshiks | Ordinary 普通 | -33 | 0 |
| 34 | Kipchaks | Distinguished 优良 | -34 | 0 |
| 35 | Leitis | Legendary 传说 | -35 | 0 |
| 36 | Coustilliers | Distinguished 优良 | -36 | 0 |
| 37 | Serjeants | Ordinary 普通 | -37 | 0 |
| 38 | Obuch | Superior 精良 | -38 | 0 |
| 39 | Hussite Wagons | Superior 精良 | -39 | 0 |
| 40 | Crusader Knights | Superior 精良 | 1 | 0 |
| 41 | Xolotl Warriors | Distinguished 优良 | 1 | 0 |
| 42 | Saboteurs | Epic 史诗 | 1 | 0 |
| 43 | Ninjas | Ordinary 普通 | 1 | 0 |
| 44 | Flamethrowers | Epic 史诗 | 1 | 0 |
| 45 | Photonmen | Legendary 传说 | 1 | 0 |
| 46 | Centurions | Distinguished 优良 | -43 | 0 |
| 47 | Apukispay | Ordinary 普通 | 1 | 0 |
| 48 | Monkey Boys | Legendary 传说 | 1 | 0 |
| 49 | Amazon Warriors | Ordinary 普通 | 1 | 0 |
| 50 | Amazon Archers | Distinguished 优良 | 1 | 0 |
| 51 | Iroquois Warriors | Distinguished 优良 | 1 | 0 |
| 52 | Varangian Guards | Ordinary 普通 | 1 | 0 |
| 53 | Gendarmes | Distinguished 优良 | 1 | 0 |
| 54 | Cuahchiqueh | Ordinary 普通 | 1 | 0 |
| 55 | Ritterbruder | Distinguished 优良 | 1 | 0 |
| 56 | Kazaks | Ordinary 普通 | 1 | 0 |
| 57 | Szlachcic | Ordinary 普通 | 1 | 0 |
| 58 | Cuirassiers | Distinguished 优良 | 1 | 0 |
| 59 | Rajputs | Ordinary 普通 | 1 | 0 |
| 60 | Seljuk Archers | Superior 精良 | 1 | 0 |
| 61 | Numidian Javelinmen | Ordinary 普通 | 1 | 0 |
| 62 | Sosso Guards | Ordinary 普通 | 1 | 0 |
| 63 | Swiss Pikemen | Distinguished 优良 | 1 | 0 |
| 64 | Headhunters | Epic 史诗 | 1 | 0 |
| 65 | Teulu | Ordinary 普通 | 1 | 0 |
| 66 | Maillotins | Distinguished 优良 | 1 | 0 |
| 67 | Hashashin | Distinguished 优良 | 1 | 0 |
| 68 | Highlander | Ordinary 普通 | 1 | 0 |
| 69 | Stradiot | Distinguished 优良 | 1 | 0 |
| 70 | Ahosi | Distinguished 优良 | 1 | 0 |
| 71 | Landsknecht | Ordinary 普通 | 1 | 0 |
| 72 | Clibinarii | Ordinary 普通 | 1 | 0 |
| 73 | Silahtar | Ordinary 普通 | 1 | 0 |
| 74 | Jaridah | Superior 精良 | 1 | 0 |
| 75 | Wolf Warriors | Distinguished 优良 | 1 | 0 |
| 76 | Warrior Monks | Superior 精良 | 1 | 0 |
| 77 | Castellan | Distinguished 优良 | 1 | 0 |
| 78 | Wind Warriors | Distinguished 优良 | 1 | 0 |
| 79 | Chakram Throwers | Legendary 传说 | -42 | 0 |
| 80 | Urumi Swordsmen | Distinguished 优良 | -40 | 0 |
| 81 | Rathas | Distinguished 优良 | -41 | 0 |
| 82 | Composite Bowmen | Epic 史诗 | -44 | 0 |
| 83 | Monaspa | Superior 精良 | -45 | 0 |
| 84 | White Feather Guard | Superior 精良 | -49 | 0 |
| 85 | Fire Archers | Epic 史诗 | -50 | 0 |
| 86 | Tiger Cavalry | Superior 精良 | -51 | 0 |
| 87 | Iron Pagoda | Epic 史诗 | -52 | 0 |
| 88 | Liao Dao | Superior 精良 | -53 | 0 |

### 2.3 文明加成（60 张）

| # | 卡牌文案 | 稀有度 | 槽位 | 套 |
|---|---|---|---|---|
| 1 | Atlatl (Skirmishers +1 attack, +1 range) [400F 350G] | Ordinary 普通 | -15 | 0 |
| 2 | Kasbah (team Castles work 25% faster) [250F 250G] | Ordinary 普通 | -27 | 0 |
| 3 | Yeomen (+1 foot archer and skirmisher range, +2 tower attack) [750W 450G] | Superior 精良 | -1 | 0 |
| 4 | Stirrups (Cavalry attack 33% faster) [400F 200G] | Epic 史诗 | -32 | 0 |
| 5 | Burgundian Vineyards (Farmers slowly generate gold in addition to food) [400F 300G] | Superior 精良 | -36 | 0 |
| 6 | Manipur Cavalry (Cavalry +4 attack vs. Ranged Soldiers) [300F 300G] | Ordinary 普通 | -30 | 0 |
| 7 | Greek Fire (Fire ships +1 range, Bombard Towers and Dromons increased blast radius) [250F 300G] | Ordinary 普通 | -7 | 0 |
| 8 | Stronghold (Castles, Kreposts and Towers fire 33% faster, Castles and Kreposts heal allied infantry in a 7 tile radius) [250F 200G] | Distinguished 优良 | -13 | 0 |
| 9 | Great Wall (Walls and towers +30% HP) [400W 200S] | Ordinary 普通 | -6 | 0 |
| 10 | Steppe Husbandry (Light Cavalry, Steppe Lancers and Cavalry Archers trained 100% faster) [200F 300W] | Distinguished 优良 | -34 | 0 |
| 11 | Royal Heirs (Unique Unit and Camels receive -3 damage from Mounted Units) [300F 300G] | Distinguished 优良 | -25 | 0 |
| 12 | Bearded Axe (Unique Unit +1 range) [300F 300G] | Legendary 传说 | -2 | 0 |
| 13 | Anarchy (create Unique Unit at barracks) [450F 250G] | Superior 精良 | -3 | 0 |
| 14 | Marauders (create Unique Unit at stables) [300W 200G] | Superior 精良 | -17 | 0 |
| 15 | Andean Sling (Skirmishers and Slingers no minimum range, Slingers +1 attack) [200F 300G] | Ordinary 普通 | -21 | 0 |
| 16 | Grand Trunk Road (All gold income 10% faster, Market trading fee reduced to 10%) [250F 200W] | Distinguished 优良 | -20 | 0 |
| 17 | Pavise (Archer-line, Condottiero, and Unique Unit +1/+1 armor) [200W 150G] | Distinguished 优良 | 1 | 0 |
| 18 | Yasama (Towers shoot extra arrows) [300F 300W] | Superior 精良 | -5 | 0 |
| 19 | Tusk Swords (Melee elephant units +3 attack) [300W 450G] | Epic 史诗 | -28 | 0 |
| 20 | Eupseong (Watch Towers, Guard Towers, and Keeps +2 range) [300F 300W] | Distinguished 优良 | -18 | 0 |
| 21 | Hill Forts (Town Centers +3 range) [250F 250G] | Ordinary 普通 | -35 | 0 |
| 22 | Corvinian Army (Unique Unit gold cost converted to additional food/wood cost) [200F 300G] | Legendary 传说 | -22 | 0 |
| 23 | Thalassocracy (upgrades Docks to Harbors, which fire arrows) [300F 300G] | Distinguished 优良 | -29 | 0 |
| 24 | Tigui (Town Centers fire arrows when ungarrisoned) [200F 300W] | Ordinary 普通 | -26 | 0 |
| 25 | Hul'che Javelineers (Skirmishers throw a second projectile) [300F 300G] | Distinguished 优良 | -16 | 0 |
| 26 | Nomads (lost houses do not decrease population headroom) [300W 150G] | Ordinary 普通 | -12 | 0 |
| 27 | Kamandaran (Archer-line gold cost is replaced by additional wood cost) [400F 300G] | Epic 史诗 | -8 | 0 |
| 28 | Carrack (Ships +1/+1 armor) [200W 300G] | Distinguished 优良 | -24 | 0 |
| 29 | Madrasah (Monks return 50 gold when killed) [200F 100G] | Ordinary 普通 | 1 | 0 |
| 30 | First Crusade (Each Town Center (maxiumum 5) spawns a one-time batch of 5 of your Unique Unit; units are more resistant to conversion) [400F 300G] | Epic 史诗 | -37 | 0 |
| 31 | Orthodoxy (Monk units +3/+3P armor) [200F 300G] | Distinguished 优良 | 1 | 0 |
| 32 | Inquisition (Monk convert faster) [100F 300G] | Distinguished 优良 | -14 | 0 |
| 33 | Silk Armor (Light Cavalry, Steppe Lancers and Cavalry Archers receive +1/+1P armor) [400W 300G] | Distinguished 优良 | -33 | 0 |
| 34 | Ironclad (Siege units extra melee armor) [400W 350G] | Distinguished 优良 | -4 | 0 |
| 35 | Sipahi (Cavalry Archers +20 HP) [350F 150G] | Superior 精良 | -10 | 0 |
| 36 | Chatras (Elephant units +100 HP) [250F 250G] | Superior 精良 | -31 | 0 |
| 37 | Chieftains (Infantry deal bonus damage to cavalry, generate gold when killing villagers, trade units, and monks) [600F 450G] | Distinguished 优良 | -11 | 0 |
| 38 | Szlachta Privileges (Knight-line costs -60% gold) [500F 300G] | Epic 史诗 | -38 | 0 |
| 39 | Wagenburg Tactics (Gunpowder units move 15% faster) [300F 300G] | Distinguished 优良 | -39 | 0 |
| 40 | Deconstruction (Siege units fire 33% faster) [400W 400G] | Superior 精良 | 1 | 0 |
| 41 | Obsidian Arrows (Archer-line +6 attack vs. buildings) [300F 300G] | Epic 史诗 | 1 | 0 |
| 42 | Tortoise Engineers (Rams train 100% faster) [100W 200G] | Ordinary 普通 | 1 | 0 |
| 43 | Panoply (Infantry +1/+1P armor, +1 attack) [300F 200G] | Superior 精良 | 1 | 0 |
| 44 | Clout Archery (Archery Ranges work 50% faster) [150W 250G] | Distinguished 优良 | 1 | 0 |
| 45 | Medical Corps (Elephant units regenerate 30 HP per minute) [300F 200G] | Distinguished 优良 | -40 | 0 |
| 46 | Paiks (Unique Unit and elephant units attack 20% faster) [375W 275G] | Epic 史诗 | -41 | 0 |
| 47 | Kshatriyas (Military units cost -25% food) [500F 450G] | Epic 史诗 | -42 | 0 |
| 48 | Detinets (40% of Castle, Tower, Krepost, and Donjon stone cost replaced with wood) [400W 200G] | Superior 精良 | -23 | 0 |
| 49 | Zealotry (Camel units +20 hit points) [400F 400G] | Distinguished 优良 | 1 | 0 |
| 50 | Ballistas (Scorpions and Ballista Elephants fire 33% faster, Galleys +2 attack) [400W 300G] | Distinguished 优良 | -43 | 0 |
| 51 | Bimaristan (Monk units automatically heal multiple nearby units) [300W 200G] | Ordinary 普通 | -9 | 0 |
| 52 | Cilician Fleet (Demolition Ships +20% blast radius; Galley-line and Dromons +1 range) [350W 300G] | Ordinary 普通 | -44 | 0 |
| 53 | Svan Towers (Defensive buildings +2 attack; towers fire arrows that pierce multiple units) [300F 200G] | Superior 精良 | -45 | 0 |
| 54 | Replaceable Parts (Siege units +1/+1P armor, repairing siege is free) [400W 250G] | Superior 精良 | 1 | 0 |
| 55 | Silk Road (Trade units cost -50%) [250F 250G] | Ordinary 普通 | -19 | 0 |
| 56 | Coiled Serpent Array (Spearman-line and Unique Unit gain additional HP when near each other) [350F 300G] | Superior 精良 | -49 | 0 |
| 57 | Red Cliff Tactics (Demolition Ships and Fire Archers deal fire damage to ships and buildings) [400F 250G] | Distinguished 优良 | -50 | 0 |
| 58 | Tuntian (Soldiers passively produce food) [250F 300W] | Superior 精良 | -51 | 0 |
| 59 | Fortified Bastions (Fortifications regenerate 500 HP per minute) [350F 250W] | Distinguished 优良 | -52 | 0 |
| 60 | Lamellar Armor (Infantry and Skirmishers reflect 25% melee damage back to the attacker) [450F 300G] | Epic 史诗 | -53 | 0 |

### 2.4 独特科技（59 张）

| # | 卡牌文案 | 稀有度 | 槽位 | 套 |
|---|---|---|---|---|
| 1 | Garland Wars (Infantry +4 attack) [450F 750G] | Superior 精良 | -15 | 0 |
| 2 | Maghrebi Camels (Camel units regenerate) [700F 300G] | Distinguished 优良 | -27 | 0 |
| 3 | Warwolf (Trebuchet units do blast damage) [800W 400G] | Distinguished 优良 | -1 | 0 |
| 4 | Bagains (Militia-line gains +5 armor) [900F 450G] | Superior 精良 | -32 | 0 |
| 5 | Flemish Revolution (Upgrades all existing Villagers to Flemish Militia; create Flemish Militia at Town Centers) [200F 150G + 10F 5G per villager] | Ordinary 普通 | -36 | 0 |
| 6 | Howdah (Elephant units +1/+1P armor) [400F 300W] | Distinguished 优良 | -30 | 0 |
| 7 | Logistica (Unique Unit causes trample damage) [800F 600G] | Legendary 传说 | -7 | 0 |
| 8 | Furor Celtica (Siege Weapons units +40% HP) [750F 450G] | Distinguished 优良 | -13 | 0 |
| 9 | Rocketry (Scorpions, Rocket Carts and Lou Chuans +25% attack; Lou Chuans fire rockets) [1100W 900G] | Superior 精良 | -6 | 0 |
| 10 | Elite Mercenaries (team members can train 5 free elite versions of your Unique Unit per castle) [650F 400G] | Ordinary 普通 | -34 | 0 |
| 11 | Torsion Engines (increases blast radius of Siege Workshop units) [1000F 600G] | Epic 史诗 | -25 | 0 |
| 12 | Chivalry (Stables work 40% faster) [600W 500G] | Ordinary 普通 | -2 | 0 |
| 13 | Perfusion (Barracks work 100% faster) [400W 600G] | Distinguished 优良 | -3 | 0 |
| 14 | Atheism (+100 years for Relic, Wonder victories; enemy relics generate -50% resources) [500F 3OOW] | Ordinary 普通 | -17 | 0 |
| 15 | Fabric Shields (Shock Infantry, Slingers, Unique Unit +1/+2 armor) [600F 600G] | Distinguished 优良 | -21 | 0 |
| 16 | Shatagni (Hand Cannoneers +2 range) [500F 650G] | Ordinary 普通 | -20 | 0 |
| 17 | Pirotechnia (Hand cannoneers deal +15% pass through damage and are more accurate) [650F 500G] | Superior 精良 | -19 | 0 |
| 18 | Kataparuto (Trebuchet units fire, pack faster) [550W 300G] | Distinguished 优良 | -5 | 0 |
| 19 | Double Crossbow (Scorpion and Ballista units fire two projectiles) [700F 400G] | Distinguished 优良 | -28 | 0 |
| 20 | Shinkichon (Rocket Carts and Turtle Ships +1 range, fire additional rockets) [1100F 800G] | Ordinary 普通 | -18 | 0 |
| 21 | Tower Shields (Spearmen and Skirmishers +2P armor) [500F 200G] | Distinguished 优良 | -35 | 0 |
| 22 | Recurve Bow (Cavalry archers +1 range, +1 attack) [600W 400G] | Distinguished 优良 | -22 | 0 |
| 23 | Forced Levy (Militia-line gold cost is replaced by additional food cost) [850F 500G] | Epic 史诗 | -29 | 0 |
| 24 | Farimba (Cavalry +5 attack) [650F 400G] | Legendary 传说 | -26 | 0 |
| 25 | El Dorado (Shock Infantry have +40 hit points) [750F 450G] | Superior 精良 | -16 | 0 |
| 26 | Drill (Siege workshop units move 50% faster) [500W 450G] | Superior 精良 | -12 | 0 |
| 27 | Citadels (Castles and Kreposts fire Bullets [+4 attack, +3 vs Rams, +3 vs Infantry], receive -25% bonus damage) [600W 300G] | Epic 史诗 | -8 | 0 |
| 28 | Arquebus (gunpowder units more accurate) [700F 400G] | Ordinary 普通 | -24 | 0 |
| 29 | Counterweights (Trebuchet units and Mangonel-line +15% attack) [650F 500G] | Ordinary 普通 | -9 | 0 |
| 30 | Hauberk (Knights +1/+2P armor) [700F 600G] | Distinguished 优良 | -37 | 0 |
| 31 | Druzhina (Infantry damage adjacent units) [900F 500G] | Superior 精良 | -23 | 0 |
| 32 | Supremacy (Villagers stronger in combat) [400F 250G] | Ordinary 普通 | -14 | 0 |
| 33 | Timurid Siegecraft (Trebuchet units +2 range, enables Flaming Camels) [500W 400G] | Distinguished 优良 | -33 | 0 |
| 34 | Crenellations (+3 range Castles garrisoned infantry fire arrows) [600F 400S] | Distinguished 优良 | -4 | 0 |
| 35 | Artillery (+2 range Bombard Towers, Bombard Cannons, Cannon Galleons) [600F 650G] | Superior 精良 | -10 | 0 |
| 36 | Paper Money (Lumberjacks slowly generate gold in addition to wood) [550F 200W] | Superior 精良 | -31 | 0 |
| 37 | Bogsveigar (Foot Archers and Unique ships +1 attack) [650F 500G] | Ordinary 普通 | -11 | 0 |
| 38 | Lechitic Legacy (Light Cavalry deals trample damage) [750F 550G] | Epic 史诗 | -38 | 0 |
| 39 | Hussite Reforms (Monks and Monastery upgrades have their gold cost replaced by food) [500F 450G] | Distinguished 优良 | -39 | 0 |
| 40 | Brigandine Armor (Camels and Cavalry Archers +2/+1P armor) [500W 500G] | Distinguished 优良 | 1 | 0 |
| 41 | Field Repairmen (Rams regain HP) [350W 650G] | Ordinary 普通 | 1 | 0 |
| 42 | Golden Age (All buildings work 10% faster) [300S 600G] | Distinguished 优良 | 1 | 0 |
| 43 | Villager's Revenge (Dead villagers become Halberdiers) [500F 250G] | Distinguished 优良 | 1 | 0 |
| 44 | Gate Crashing (Ram gold cost is replaced by additional wood cost) [600W 700G] | Superior 精良 | 1 | 0 |
| 45 | Wootz Steel (Infantry and cavalry attacks ignore armor) [650F 550G] | Legendary 传说 | -40 | 0 |
| 46 | Mahayana (Villagers and monk units take 10% less population space) [800W 650G] | Superior 精良 | -41 | 0 |
| 47 | Frontier Guards (Camel units and Elephant Archers +4 melee armor) [800F 700G] | Distinguished 优良 | -42 | 0 |
| 48 | Comitatenses (Militia-line, Knight-line, and Unique Unit train 50% faster and receive a 5 damage charge attack) [700F 800G] | Distinguished 优良 | -43 | 0 |
| 49 | Fereters (Infantry except Spearmen +30 HP, Warrior Priests +100% heal speed) [550F 400G] | Superior 精良 | -44 | 0 |
| 50 | Aznauri Cavalry (Cavalry units take 20% less population space) [550F 250G] | Distinguished 优良 | -45 | 0 |
| 51 | Pila (Skirmisher attacks strip armour) [700F 600G] | Epic 史诗 | 1 | 0 |
| 52 | Enlistment (Infantry take 15% less population space) [700F 300G] | Distinguished 优良 | 1 | 0 |
| 53 | Marshalled Hunters (Foot archers and skirmishers take 15% less population space) [750W 250G] | Distinguished 优良 | 1 | 0 |
| 54 | Shigetō Yumi (Unique Unit, Mounted Archers, and Towers attack 15% faster and deal +2 anti-unique unit damage) [750F 350G] | Distinguished 优良 | 1 | 0 |
| 55 | Bolt Magazine (Archer-line, Lou Chans, and War Chariots fire additional projectiles) | Epic 史诗 | -49 | 0 |
| 56 | Sitting Tiger (Trebuchet units fire additional projectiles) [600W, 300G] | Legendary 传说 | -50 | 0 |
| 57 | Ming Guang Armor (Mounted units +4 melee armor) [600F 450G] | Legendary 传说 | -51 | 0 |
| 58 | Thunderclap Bombs (Rocket Carts, Grenadiers, and Lou Chuans detonate when defeated; projectiles produce additional explosions) [900F 600G] | Superior 精良 | -52 | 0 |
| 59 | Ordo Cavalry (Cavalry regenerates HP in combat) [600F 300G] | Superior 精良 | -53 | 0 |

### 2.5 团队加成（80 张）

| # | 卡牌文案 | 稀有度 | 槽位 | 套 |
|---|---|---|---|---|
| 1 | Relics generate +33% gold | Superior 精良 | -15 | 0 |
| 2 | Genitour available in the Archery Range starting in the Castle Age | Superior 精良 | -27 | 0 |
| 3 | Archery Ranges work 10% faster | Epic 史诗 | -1 | 0 |
| 4 | Blacksmiths work 80% faster | Distinguished 优良 | -32 | 0 |
| 5 | Relics generate both Gold and Food | Distinguished 优良 | -36 | 0 |
| 6 | Relics visible on the map at the start of the game | Distinguished 优良 | -30 | 0 |
| 7 | Monks +100% heal speed | Ordinary 普通 | -7 | 0 |
| 8 | Siege Workshops work 20% faster | Distinguished 优良 | -13 | 0 |
| 9 | Farms +10% food | Distinguished 优良 | -6 | 0 |
| 10 | Palisade Walls +33% HP | Ordinary 普通 | -34 | 0 |
| 11 | Outposts +3 LOS and cost no stone | Epic 史诗 | -25 | 0 |
| 12 | Knights +2 LOS | Ordinary 普通 | -2 | 0 |
| 13 | Barracks work 20% faster | Epic 史诗 | -3 | 0 |
| 14 | Stables work 20% faster | Epic 史诗 | -17 | 0 |
| 15 | Start with a free Llama | Superior 精良 | -21 | 0 |
| 16 | Camel and light cavalry units +2 attack vs. buildings | Distinguished 优良 | -20 | 0 |
| 17 | Condottiero available in the Barracks in Imperial Age | Superior 精良 | -19 | 0 |
| 18 | Galleys +4 LOS | Ordinary 普通 | -5 | 0 |
| 19 | Scorpions +1 range | Epic 史诗 | -28 | 0 |
| 20 | Villagers +3 LOS | Ordinary 普通 | -18 | 0 |
| 21 | Monasteries work 20% faster | Distinguished 优良 | -35 | 0 |
| 22 | Cavalry Archers trained 25% faster | Distinguished 优良 | -22 | 0 |
| 23 | Docks +6 LOS | Distinguished 优良 | -29 | 0 |
| 24 | Universities work 80% faster | Distinguished 优良 | -26 | 0 |
| 25 | Walls cost -50% | Superior 精良 | -16 | 0 |
| 26 | Scout Cavalry, Light Cavalry, Hussar +2 LOS | Epic 史诗 | -12 | 0 |
| 27 | Knights +2 attack vs. Archers | Distinguished 优良 | -8 | 0 |
| 28 | Technologies research 25% faster (excluding Age Up) | Ordinary 普通 | -24 | 0 |
| 29 | Foot archers and skirmisher-line +2 attack vs. buildings | Superior 精良 | -9 | 0 |
| 30 | Transport Ships +5 LOS and cost -50% | Ordinary 普通 | -37 | 0 |
| 31 | Military buildings provide +5 population room | Ordinary 普通 | -23 | 0 |
| 32 | Trade units generate +25% gold | Legendary 传说 | -14 | 0 |
| 33 | Cavalry Archers +2 LOS | Ordinary 普通 | -33 | 0 |
| 34 | Units resist conversion | Legendary 传说 | -4 | 0 |
| 35 | Gunpowder units created 25% faster | Ordinary 普通 | -10 | 0 |
| 36 | Imperial Skirmisher upgrade available in the Imperial Age | Epic 史诗 | -31 | 0 |
| 37 | Docks cost -15% | Ordinary 普通 | -11 | 0 |
| 38 | Scout Cavalry, Light Cavalry, Hussar +1 attack vs. Ranged Soldiers | Ordinary 普通 | -38 | 0 |
| 39 | Scorpion-line minimum range reduced | Ordinary 普通 | -43 | 0 |
| 40 | Trade units +50 HP | Ordinary 普通 | 1 | 0 |
| 41 | Houses built 100% faster | Ordinary 普通 | -50 | 0 |
| 42 | Monks +2 LOS | Ordinary 普通 | 1 | 0 |
| 43 | Herdables +2 LOS | Distinguished 优良 | 1 | 0 |
| 44 | Mills, Lumber Camps, Mining Camps built 100% faster | Ordinary 普通 | 1 | 0 |
| 45 | Unique Units +5% HP | Superior 精良 | 1 | 0 |
| 46 | Skirmishers, Spearmen, and Scout-lines train 20% faster | Distinguished 优良 | 1 | 0 |
| 47 | Fishing ships +2 LOS | Ordinary 普通 | 1 | 0 |
| 48 | Scout-line +2 attack vs. gunpowder units | Ordinary 普通 | 1 | 0 |
| 49 | Infantry +5 attack vs. Elephant units | Ordinary 普通 | 1 | 0 |
| 50 | Explosive units +20% speed | Ordinary 普通 | 1 | 0 |
| 51 | All resources last 5% longer | Superior 精良 | 1 | 0 |
| 52 | Castles, Kreposts, Donjons work 10% faster | Superior 精良 | 1 | 0 |
| 53 | Markets work 80% faster | Superior 精良 | -39 | 0 |
| 54 | Steppe Lancers +3 LOS | Ordinary 普通 | 1 | 0 |
| 55 | Spearmen +3 attack vs. cavalry | Distinguished 优良 | 1 | 0 |
| 56 | Elephant units +4 attack vs. buildings | Distinguished 优良 | 1 | 0 |
| 57 | Shock Infantry +2 LOS | Superior 精良 | 1 | 0 |
| 58 | Docks work 20% faster | Distinguished 优良 | 1 | 0 |
| 59 | Monasteries 3x HP | Ordinary 普通 | 1 | 0 |
| 60 | Markets 3x HP | Ordinary 普通 | 1 | 0 |
| 61 | Explosive units +6 LOS | Ordinary 普通 | 1 | 0 |
| 62 | Outposts and towers constructed faster | Ordinary 普通 | 1 | 0 |
| 63 | Siege towers +50% garrison capacity | Ordinary 普通 | 1 | 0 |
| 64 | Docks built 100% faster | Ordinary 普通 | 1 | 0 |
| 65 | Infantry +2 LOS | Superior 精良 | -44 | 0 |
| 66 | Trade carts 20% faster when empty | Superior 精良 | 1 | 0 |
| 67 | All explosive units +40% HP | Ordinary 普通 | 1 | 0 |
| 68 | Town Centers +4 LOS | Ordinary 普通 | 1 | 0 |
| 69 | Upgrading Unique Units to Elite costs -20% | Distinguished 优良 | 1 | 0 |
| 70 | Docks provide +5 population room | Ordinary 普通 | -40 | 0 |
| 71 | Trade units yield 10% food in addition to gold | Distinguished 优良 | -41 | 0 |
| 72 | Camel and elephant units created 25% faster | Distinguished 优良 | -42 | 0 |
| 73 | Can train spearmen from Town Centers | Superior 精良 | 1 | 0 |
| 74 | Can train Canoes from docks | Superior 精良 | 1 | 0 |
| 75 | Buildings cost 25% fewer resources to repair | Superior 精良 | -45 | 0 |
| 76 | Mounted archers -50% frame delay | Distinguished 优良 | 1 | 0 |
| 77 | Foot archers +2 LOS | Superior 精良 | -49 | 0 |
| 78 | Cavalry +2 attack vs. siege weapons | Superior 精良 | -51 | 0 |
| 79 | Gunpowder units +2 LOS | Ordinary 普通 | -52 | 0 |
| 80 | Infantry +2 attack vs. Ranged Soldiers | Distinguished 优良 | -53 | 0 |

## 3 `classToName`：Armor/Attack Class 的官方人话（26 条）

> 这份映射比 airef 的对象表更适合"给玩家看"，因为它用的就是游戏里 attack/armor class 的编号。

| Class | 名称 |
|---|---|
| 1 | infantry |
| 5 | elephants |
| 8 | cavalry |
| 10 | villagers |
| 11 | buildings |
| 13 | stone defenses |
| 14 | animals |
| 15 | archers |
| 16 | ships/saboteurs |
| 17 | rams/trebuchet |
| 19 | unique units |
| 20 | siege weapons |
| 21 | buildings |
| 22 | walls/gates |
| 23 | gunpowder |
| 25 | monks |
| 26 | castles |
| 27 | spearmen |
| 28 | cavalry archers |
| 29 | eagles |
| 30 | camels |
| 32 | condottiero |
| 34 | fishing ships |
| 35 | mamelukes |
| 36 | heroes/kings |
| 38 | skirmishers |

## 4 奇观与城堡（50 个文明建筑模型）

这些是生成自定义文明时要选的"外观"——每个原版文明对应一个奇观/城堡。

| # | 奇观 | 城堡 |
|---|---|---|
| 1 | Chichester Cathedral (Britons) | British Castle |
| 2 | Chartres Cathedral (Franks) | French Castle |
| 3 | Mausoleum of Theodoric (Goths) | Gothic Castle |
| 4 | Maria Laach Abbey (Teutons) | Teuton Castle |
| 5 | Great Buddha Hall (Japanese) | Japanese Castle |
| 6 | Temple of Heaven (Chinese) | Chinese Castle |
| 7 | Hagia Sophia (Byzantines) | Byzantine Castle |
| 8 | Taq Kasra (Persians) | Persian Castle |
| 9 | Great Mosque of Samarra (Saracens) | Saracen Castle |
| 10 | Selimiye Mosque (Turks) | Turk Castle |
| 11 | Borgund Stave Church (Vikings) | Viking Castle |
| 12 | Great Tent of Genghis Khan (Mongols) | Mongol Castle |
| 13 | Rock of Cashel (Celts) | Celtic Castle |
| 14 | Torre del Oro (Spanish) | Spanish Castle |
| 15 | Temple Mayor (Aztecs) | Aztec Castle |
| 16 | Temple of the Great Jaguar (Mayans) | Mayan Castle |
| 17 | Arch of Constantine (Huns) | Hunnic Castle |
| 18 | Pagoda of Hwangnyong Temple (Koreans) | Korean Castle |
| 19 | Genoa Cathedral (Italians) | Italian Castle |
| 20 | Humayun's Tomb (Hindustanis) | Indian Castle |
| 21 | Temple of the Sun (Inca) | Incan Castle |
| 22 | Corvin Castle (Magyars) | Magyar Castle |
| 23 | Kizhi Pogost (Slavs) | Slavic Castle |
| 24 | Belem Tower (Portuguese) | Portuguese Castle |
| 25 | Biete Amanuel (Ethiopians) | Ethiopian Castle |
| 26 | Great Mosque of Djenne (Malians) | Malian Castle |
| 27 | Hassan Tower (Berbers) | Berber Castle |
| 28 | Bakan of Angkor Wat (Khmer) | Khmer Castle |
| 29 | Kalasan Temple (Malay) | Malay Castle |
| 30 | Schwezigon Pagoda (Burmese) | Burmese Castle |
| 31 | But Thap Temple (Vietnamese) | Vietnamese Castle |
| 32 | Round Church (Bulgarians) | Bulgarian Castle |
| 33 | Ulugh Beg Observatory (Tatars) | Tatar Castle |
| 34 | Sarkel Fortress (Cumans) | Cuman Castle |
| 35 | Trakai Island Castle (Lithuanians) | Lithuanian Castle |
| 36 | Brussels Town Hall (Burgundians) | Burgundian Castle |
| 37 | Monreale Cathedral (Sicilians) | Sicilian Castle |
| 38 | Wawel Cathedral (Poles) | Polish Castle |
| 39 | Powder Tower (Bohemians) | Bohemian Castle |
| 40 | Brihadisvara Temple (Dravidians) | Dravidian Castle |
| 41 | Somapura Mahavihara (Bengalis) | Bengali Castle |
| 42 | Somnath Temple (Gurjaras) | Gurjaran Castle |
| 43 | Colosseum (Romans) | Roman Castle |
| 44 | Etchmiadzin Cathedral (Armenians) | Armenian Castle |
| 45 | Svetitskhoveli Cathedral (Georgians) | Georgian Castle |
| 46 | Wuhou Memorial (Shu) | Shu Castle |
| 47 | Jing'an Temple (Wu) | Wu Castle |
| 48 | Songyue Pagoda (Wei) | Wei Castle |
| 49 | Yinshan Pagoda Forest (Jurchens) | Jurchen Castle |
| 50 | Pagoda of Fogong Temple (Khitans) | Khitan Castle |

## 5 52 个文明名单（含 5 个新 DLC 文明）

`Gaia`, `Britons`, `Franks`, `Goths`, `Teutons`, `Japanese`, `Chinese`, `Byzantines`, `Persians`, `Saracens`, `Turks`, `Vikings`, `Mongols`, `Celts`, `Spanish`, `Aztecs`, `Mayans`, `Huns`, `Koreans`, `Italians`, `Hindustanis`, `Incas`, `Magyars`, `Slavs`, `Portuguese`, `Ethiopians`, `Malians`, `Berbers`, `Khmer`, `Malay`, `Burmese`, `Vietnamese`, `Bulgarians`, `Tatars`, `Cumans`, `Lithuanians`, `Burgundians`, `Sicilians`, `Poles`, `Bohemians`, `Dravidians`, `Bengalis`, `Gurjaras`, `Romans`, `Armenians`, `Georgians`, `Achaemenids`, `Athenians`, `Spartans`, `Shu`, `Wu`, `Wei`, `Jurchens`, `Khitans`


最后 8 个（Achaemenids / Athenians / Spartans / Shu / Wu / Wei / Jurchens / Khitans）是 Chronicles 与 Three Kingdoms 的新文明，
说明这个站的卡牌表**跟着官方 DLC 更新**——这是它仍在维护的硬证据。


## 6 对本工作区的用法

1. **查"某个加成怎么写"**：想做"城镇中心木材 -50%"，直接搜卡牌文案，然后看它的稀有度/槽位，就知道官方认为这属于强还是弱。
2. **拿 effect 配方**：卡牌文案 → effect 的翻译逻辑在 `client.js`（60,865 B）里，`tech.js`/`unit.js` 是 404（不存在），全部逻辑挤在 client.js。
3. **抄它的单位模板**：`unitStats` 的 88 个模板是"社区眼里的平衡单位"，做自定义单位时当 baseline 比自己拍脑袋好。
4. **`treeMap`**：178 条 `[nodeIndex, techId]` 映射，说明它改了科技树布局——想改科技树节点位置可以照抄这个索引规律。


## 7 复跑

```bash

curl -s https://krakenmeister.com/civbuilder/js/common.js -o _probe/_tmp/civb/common.js

D:/Software/nodejs/node.exe _probe/_tmp/dump_civb.js        # node vm 执行 -> civb.json

C:/Users/26913/AppData/Local/Python/bin/python.exe -X utf8 _probe/_tmp/gen_vol20.py

```


---
生成：2026-11-08 16:28　|　卡牌 650　|　套数 2　|　文明 50
