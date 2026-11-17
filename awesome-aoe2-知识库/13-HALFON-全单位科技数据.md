# 13 · HALFON 数据集：全单位 / 全建筑 / 全科技（4 个版本，直取原始 JSON）

> 出处：<https://halfon.aoe2.se/>（Siege Engineers，作者 HALFON）。页面 HTML 只有空表壳，
> 数据由 `fetch("data/units_buildings_techs.<ver>.json")` 载入——所以直接抓 JSON 就行，不用爬表。

> 4 个原始文件：de 1.58 MB / ror 1.24 MB / hd 0.78 MB / wk 0.78 MB，全部 200。

> 用途：**游戏内 id 的权威对照表**——写 .dat 补丁、XS `xsEffectAmount`、场景效果、AI 的 `train`/`research` 都要查它。


## 0 一句话结论

这是**唯一一个把 4 个游戏版本（DE / RoR / HD / WK）按同一格式并列导出的单位·建筑·科技全量表**。
DE 那份有 **2693 个单位+建筑、1510 个科技**，每个条目 17 个字段，其中最值钱的是 `rms_const`——
**626 个条目带官方 RMS 常量名**（`ARCHER`、`TOWN_CENTER`、`FISH_TRAP`…），写 RMS 时直接抄，不用猜拼写。


## 1 规模

| 版本 | 版本号 | 单位+建筑 | 科技 | 带 rms_const |
|---|---|---|---|---|
| AoE2 DE | Update 188329 | 2693 | 1510 | 626 |
| Return of Rome | Update 185872 | 2737 | 191 | 0 |
| HD Edition | Patch 5.8 | 1390 | 801 | 0 |
| WololoKingdoms | Patch 5.8.1 | 1390 | 804 | 0 |

RoR 的单位数最多（2737）是因为它把 AoE1 的整套单位也放进来了；HD/WK 是同一份 1390，只是科技数不同（801 vs 804）。


## 2 字段定义

### 2.1 单位/建筑（`_halfon_units_<ver>.csv`）

| 字段 | 类型 | 含义 |
|---|---|---|
| `id` | int | 游戏内对象 ID，等于 `empires2_x2_p1.dat` 的 units 索引 |
| `name` | str | 内部名（`ARCHR`、`RTWC`、`VMBAS`），即 dat 里的 name 字段 |
| `localised_name` | str | 英文显示名（`Archer`、`Town Center`、`Villager (Male)`） |
| `hit_points` | int | HP |
| `line_of_sight` | int | 视野 |
| `attack` | int | 基础攻击（不含对特定 class 的加成） |
| `melee_armor` | int | 近战护甲 |
| `pierce_armor` | int | 远程护甲 |
| `garrison_capacity` | int | 驻扎容量（建筑驻军数 / 单位可被驻扎容量） |
| `cost_wood` | int | 木材 |
| `cost_food` | int | 食物 |
| `cost_gold` | int | 黄金 |
| `cost_stone` | int | 石头 |
| `type` | int | 对象大类，见 §3.1 |
| `class` | int | 护甲/攻击 class，见 §3.2 |
| `base_id` | int | 基础单位 ID（升级形态指回原形，如精锐指回普通） |
| `rms_const` | str | **RMS 脚本里可直接用的常量名**，626 条有值 |

> 字段实际语义说明：`type` 决定"这是不是能动的单位"，`class` 决定"被什么兵种加成克制"。两者都不是文档里公开的枚举，下面的表是从 2693 条数据反推的。

### 2.2 科技（`_halfon_techs_<ver>.csv`）

| 字段 | 含义 |
|---|---|
| `id` | 科技 ID，等于 `empires2_x2_p1.dat` 的 techs 索引 |
| `name` | 内部名（`Feudal Age`、`Crossbowman`、`Conscription`）|
| `localised_name` | 英文显示名 |
| `cost_wood/food/gold/stone` | 研究成本 |
| `help_converter` | 帮助文本转换器 ID（负值表示特殊处理；用于从 language dll 里定位说明文字）|
| `language_file_name` / `language_file_help` | language dll 里的字符串 ID；**0 表示没有该项文本** |

注意：科技表**没有** research_time / 前置科技 / 文明限制——那些在 .dat 的 `techs[].research_time`、`required_techs`、`civ` 字段里，HALFON 没导出。需要完整科技依赖图就用 [15 卷](15-aoe2techtree-科技树数据.md) 的 aoe2techtree 数据。


## 3 反推出来的枚举表

### 3.1 `type` 对象大类（7 个值，DE）

| type | 条目数 | 含义 | 示例 |
|---|---|---|---|
| 70 | 869 | 可移动单位（人/船/动物） | OLD-ACADEMY(0), LEGION(1), ARCHR(4), HCANR(5) |
| 10 | 660 | 资源/地形物件（金矿、树、FORAGE 等） | FORAG(59), GOLDM(66), STONM(102), FLARE(112) |
| 80 | 491 | 建筑 | ARRG3(10), Barracks Age1(12), ARRG4(14), BLAC3(18) |
| 30 | 401 | 死亡残骸（`*_D` 后缀，尸体/废墟） | LEGION_D(2), ARCHR_D(3), BCANN_D(16), BRSRK_D(22) |
| 60 | 170 | 抛射物（箭、弩炮弹、投石） | ARROW(9), Projectile VOL(54), ARROW1(97), Projectile Slinger(187) |
| 20 | 101 | 装饰/特效（旗帜、火把、烟雾） | FLAGX(162), Trail Smoke(247), BONFI(304), TORCH(499) |
| 25 | 1 | 特殊单例 | DOPL(243) |

**判定依据**：type 70 的都是会走动的（`ARCHR`/`VMBAS`/`SHEEPG`）；type 80 的都是能建的（`Barracks Age1`/`RTWC`）；
type 30 全部是 `*_D` 后缀的死亡残骸；type 60 全是 `ARROW`/`BOLTX`/`TREBST` 抛射物。

### 3.2 `class` 护甲/攻击 class（DE 里实际出现的 57 个值）

| class | 条目数 | 判断含义 | 代表条目 |
|---|---|---|---|
| -1 | 91 | 无 class（空条目/占位）| — |
| 0 | 56 | Archer 弓箭手 | ARCHR, HXBOW, XBOWM, LNGBW |
| 1 | 9 | Artifact/装饰 | ARTCT, KOH-FLAG, TORCH2, ARTCT |
| 2 | 3 | Trade ship 贸易船 | JUNKX, COGXX, Merchant Ship |
| 3 | 215 | Building 建筑 | ARRG3, Barracks Age1, ARRG4, BLAC3 |
| 4 | 28 | Villager 村民 | VMFIS, VFFIS, VMBAS, VMBLD |
| 5 | 13 | Fish 鱼 | FISHX, DOLP3, DOLP1, DOLP2 |
| 6 | 217 | Infantry 步兵 | LEGION, TKNIT, GBRSK, SPRMN |
| 7 | 5 | Forage bush 果丛 | FORAG, FORAGM, FORAGGURJ, PAPAYA |
| 8 | 2 | Stone mine 石矿 | STONM, ROCKSX |
| 9 | 28 | Prey animal 猎物 | DEERX, HORSW, HORSW, ZEBRA |
| 10 | 30 | Predator animal 掠食动物 | BOARX, DWOLF, WOLFX, OUTLW |
| 11 | 599 | Misc/其它（尸体、抛射物、无效） | OLD-ACADEMY, LEGION_D, ARCHR_D, ARROW |
| 12 | 189 | Cavalry 骑兵 | LANCE, KNGHT, CATAP, HRLION |
| 13 | 23 | Siege weapon 攻城器 | BTRAM, BCANN, MPCAV, MANGO |
| 14 | 517 | Terrain/装饰（ rubble、地形块） | RUBL1, RUBL2, RUBL3, RUBL4 |
| 15 | 54 | Tree 树 | TREETD, BUSH, FBAM, FOAK |
| 16 | 1 | ? | FACAHOLE |
| 18 | 15 | Monk 僧侣 | MONKX, HFRIAR, HARCH, MONKY |
| 19 | 3 | Trade cart 贸易车 | TCART, TCARTF, TDONK |
| 20 | 2 | Transport 运输船 | XPORT, XPORT |
| 21 | 5 | Fishing ship 渔船 | FSHSP, FSHSP, Oystering Ship, Antiquity Mode Fishing Ship |
| 22 | 54 | Warship 战船 | GALLY, HLEIF, HVASCO, LNGBT |
| 23 | 7 | Conquistador 类（火药骑兵） | HFORE, HGPIZ, CONQI, UCONQ |
| 27 | 39 | Wall 城墙 | WALL, WALL2, WALL4, WALL3 |
| 28 | 2 | Wardog 战犬 | WARDOG, EWARDOG |
| 30 | 74 | Flag/标记物 | FLARE, FLAGX, FLR_R, BONFI |
| 32 | 2 | Gold mine 金矿 | GOLDM, ROCKGX |
| 33 | 2 | ? | FISHS, TURTLES |
| 34 | 96 | Cliff 悬崖（装饰） | Cliff (Default) 01, Cliff (Default) 02, Cliff (Default) 03, Cliff (Default) 04 |
| 35 | 4 | Petard 类（自爆） | PETARD, HDSQD, FCAMEL, Removed |
| 36 | 53 | Unique unit 城堡特色兵 | MOSUN, CVRCH, HTAME, HPRITH |
| 37 | 1 | DOPL 单例 | DOPL |
| 38 | 9 | Invisible/占位物 | FLDOG, Invisible object that keeps player alive, DUMMY, GOAT |
| 39 | 97 | Gaia terrain 装饰（GTAA/GTAB） | GTAA3, GTAA2, GTAB3, GTAB2 |
| 40 | 6 | Relic pile 遗物堆 | PILE1, PILE2, PILE3, PILE4 |
| 41 | 5 | Pile 资源堆 | PSTON, POREX, PGOLD, PWOOD |
| 42 | 12 | Relic 遗物 | RELIC, RLIC1, RLIC2, RLIC3 |
| 43 | 9 | Regional monk 地域僧侣 | RMONK, RMNK0, RMONKM, RPRIEST |
| 44 | 7 | Gunpowder infantry 火药步兵 | HCANR, JANNI, RJANI, UJANI |
| 47 | 1 | Scout 侦察 | SCOUT |
| 48 | 1 | Ore mine 矿 | OREMN |
| 49 | 11 | Farm 农田 | FARM, FTRAP, RFARM, FARMDROP |
| 51 | 6 | ? | PTREB, PTWC, PMANG, HGOSP |
| 52 | 11 | Wonder 奇观 | WCTW, WCTW3, WCTW2, WCTW3 |
| 53 | 4 | ? | HSTOER, BDGAL, ABGAL, MONKBT |
| 54 | 4 | Trebuchet 类 | TREBU, HBNB, HGOS, TREBU |
| 55 | 4 | Bombard 类 | SCBAL, HWBAL, HUSSITEWAGON, EHUSSITEWAGON |
| 56 | 2 | ? | RFARC, RFSWD |
| 57 | 2 | ? | RCSWD, RCARC |
| 58 | 16 | Herdable 家畜 | LLAMAA, SHEEPG, Cow Black and White, TURKYG |
| 59 | 20 | Hero/King 英雄与国王 | HBELA, KINGX, HSHAH, HPIKL |
| 60 | 1 | Projectile 抛射物 | PROJMTREB_D |
| 61 | 12 | Rideable horse 坐骑 | HORSE, CAMEL, DROME, HORSEHVY |
| 63 | 2 | Whale/Oyster 鲸与牡蛎 | Oysters, WHALE |
| 64 | 10 | Explosion 爆炸特效 | Bolt explosion, LCHUAN_EXP, LCHUAN_DELAY_EXP, GREN_DELAY_EXP |
| 65 | 2 | Fox 狐狸 | REDFOX, ARCTICFOX |

> `class` 与 .dat 的 `Attack`/`Armour` 数组里的 `Class` 是同一套编号（见 [07 卷](07-XS-ID表-属性资源任务与伤害计算.md) 的伤害计算章节）。
> 例：长枪兵对 class 12（Cavalry）有加成，所以 `Attacks` 里会出现 `{Class:12, Amount:32}`。


## 4 `rms_const` 全量：626 条可直接抄的 RMS 常量

> 这是本卷最实用的部分。RMS 里写 `create_object TOWN_CENTER` 而不是写数字 ID，可读性和兼容性都好得多。

共 626 条，按常量名字典序。完整清单同时存在于 `_halfon_units_de.csv` 的 `rms_const` 列（空值表示无常量）。

| RMS 常量 | ID | 内部名 | 显示名 | type |
|---|---|---|---|---|
| `ADMIRAL_YI_SUN_SHIN` | 844 | HYI | Admiral Yi Sun-shin | 70 |
| `AETHELFIRTH` | 169 | HAETH | Aethelfrith | 70 |
| `ALARIC_THE_GOTH` | 223 | HALARIC | Alaric the Goth | 70 |
| `ALEXANDER_NEVSKI` | 197 | HWILL | Alexander Nevski | 70 |
| `ALPACA` | 2614 | ALPACA | Alpaca | 70 |
| `ARABIAN_WOLF` | 2091 | AWOLF | Arabian Wolf | 70 |
| `ARBALEST` | 492 | ACOAR | Arbalester | 70 |
| `ARCHBISHOP` | 177 | HARCH | Archbishop | 70 |
| `ARCHER` | 4 | ARCHR | Archer | 70 |
| `ARCHERS_OF_THE_EYES` | 686 | HAOE | Archer of the Eyes | 70 |
| `ARCHERY_CANNON_CLASS` | 944 | ARTCT | Relic Cart | 70 |
| `ARCHERY_CLASS` | 900 | RAIN |  | 20 |
| `ARCHERY_RANGE` | 87 | ARRG | Archery Range | 80 |
| `ARCHERY_RANGE_C` | 10 | ARRG3 | Archery Range | 80 |
| `ARCHERY_RANGE_I` | 14 | ARRG4 | Archery Range | 80 |
| `ARCTIC_FOX` | 1958 | ARCTICFOX | Arctic Fox | 70 |
| `ARCTIC_HARE` | 2100 | ARCTICHARE | Arctic Hare | 70 |
| `ARCTIC_WOLF` | 1965 | ARCTICWOLF | Arctic Wolf | 70 |
| `ARGALI` | 1896 | ARGALI | Argali | 70 |
| `ARTIFACT_CLASS` | 901 | FLAGF | Flag F | 20 |
| `ASIAN_MAPLE_AUTUMN_TREE` | 2028 | FASIANMAPLEA | Tree (Asian Maple, Autumn) | 10 |
| `ASIAN_MAPLE_GREEN_TREE` | 2027 | FASIANMAPLEG | Tree (Asian Maple, Green) | 10 |
| `ASIAN_PINE_TREE` | 2016 | FASIANPINE | Tree (Asian Pine) | 10 |
| `ATTILA_THE_HUN` | 777 | HATTILA | Attila the Hun | 70 |
| `BAD_NEIGHBOR` | 682 | HBNB | Bad Neighbor | 80 |
| `BAD_NEIGHBOR_PACKED` | 730 | HBNBP | Bad Neighbor (Packed) | 80 |
| `BAMBOO_STUMP` | 1536 | STUMPB2 | Bamboo Stump | 10 |
| `BAMBOO_TREE` | 348 | FBAM | Tree (Bamboo Forest) | 10 |
| `BAOBAB_STUMP` | 1537 | STUMBAO2 | Baobab Stump | 10 |
| `BARRACKS` | 12 | Barracks Age1 | Barracks | 80 |
| `BARRACKS_C` | 132 | Barracks Age3 | Barracks | 80 |
| `BARRACKS_F` | 498 | Barracks Age2 | Barracks | 80 |
| `BARRACKS_I` | 20 | Barracks Age4 | Barracks | 80 |
| `BATTERING_RAM` | 35 | BTRAM | Battering Ram | 70 |
| `BELISARIUS` | 167 | HBELIS | Belisarius | 70 |
| `BERSERK` | 692 | VBRSK | Berserk | 70 |
| `BIRCH_TREE` | 1717 | BIRCH | Tree (Birch) | 10 |
| `BIRD_CLASS` | 938 | DRAGS | Dragon Ship | 70 |
| `BLACKSMITH` | 103 | BLAC | Blacksmith | 80 |
| `BLACKSMITH_C` | 18 | BLAC3 | Blacksmith | 80 |
| `BLACKSMITH_F` | 105 | BLAC2 | Blacksmith | 80 |
| `BLACKSMITH_I` | 19 | BLAC4 | Blacksmith | 80 |
| `BLACK_BEAR` | 2089 | BLACKBEAR | Black Bear | 70 |
| `BLACK_PANTHER` | 2595 | PANTHER | Black Panther | 70 |
| `BLEDA_THE_HUN` | 779 | HBLEDA | Bleda the Hun | 70 |
| `BOAR` | 48 | BOARX | Wild Boar | 70 |
| `BOARDING_SHIP_CLASS` | 953 |  |  | 10 |
| `BOMBARD_CANNON` | 36 | BCANN | Bombard Cannon | 70 |
| `BOMBARD_TOWER` | 236 | WCTW4 | Bombard Tower | 80 |
| `BRITISH_RELIC` | 287 | RLIC1 |  | 70 |
| `BROKEN_CART` | 858 | BCART | Broken Cart | 10 |
| `BUSH_GORSE` | 2733 | BUSH4 | Bush D | 10 |
| `BYZANTINE_RELIC` | 288 | RLIC2 |  | 70 |
| `CACTUS` | 709 | FCAC | Cactus | 30 |
| `CAIMAN` | 2594 | CAIMAN | Caiman | 70 |
| `CAMEL` | 329 | CVLRY | Camel Rider | 70 |
| `CANNON_GALLEON` | 420 | CANGA | Cannon Galleon | 70 |
| `CAPPED_RAM` | 422 | CBATR | Capped Ram | 70 |
| `CAPYBARA` | 2590 | CAPYBARA | Capybara | 70 |
| `CARAVAN` | 275 | CENTU | Imperial Centurion | 70 |
| `CASTLE` | 82 | CSTL | Castle | 80 |
| `CATAPHRACT` | 40 | CATAP | Cataphract | 70 |
| `CATHEDRAL` | 599 | SPECR | Cathedral | 80 |
| `CAVALIER` | 283 | PALDN | Cavalier | 70 |
| `CAVALRY_ARCHER` | 39 | CVRCH | Cavalry Archer | 70 |
| `CAVALRY_ARCHER_CLASS` | 936 | WELEF | Elephant | 70 |
| `CAVALRY_CANNON_CLASS` | 923 | QUEEN | Queen | 70 |
| `CAVALRY_CLASS` | 912 | BGAB |  | 80 |
| `CAVALRY_RAIDER_CLASS` | 957 |  |  | 10 |
| `CHAMPION` | 567 | HEROI | Champion | 70 |
| `CHARLEMAGNE` | 165 | HCHARL | Charlemagne | 70 |
| `CHARLES_MARTEL` | 424 | HCMAR | Charles Martel | 70 |
| `CHICKEN_A` | 2083 | CHICKENA | Chicken A | 70 |
| `CHICKEN_B` | 2085 | CHICKENB | Chicken B | 70 |
| `CHICKEN_C` | 2087 | CHICKENC | Chicken C | 70 |
| `CHINESE_RELIC` | 289 | RLIC3 |  | 70 |
| `CHU_KO_NU` | 73 | CHUKN | Chu Ko Nu | 70 |
| `CLIFF_CLASS` | 934 | ALFRED | Alfred the Alpaca | 70 |
| `CONDOR` | 2593 | CONDOR | Condor | 70 |
| `CONQUISTADOR` | 771 | CONQI | Conquistador | 70 |
| `CONSTABLE_RICHEMONT` | 646 | HRICH | Constable Richemont | 70 |
| `CONTROLLED_ANIMAL_CLASS` | 961 |  |  | 10 |
| `CRACKS` | 241 | TERRG | Cracks | 10 |
| `CRATER` | 723 | CRATR | Crater | 10 |
| `CROSSBOWMAN` | 24 | CARCH | Crossbowman | 70 |
| `CRUSADER_KNIGHT` | 1723 | CRUSADERKNIGHT | Crusader Knight | 70 |
| `CYPRESS_TREE` | 1347 | CYPRESS | Tree (Cypress) | 10 |
| `DEEP_SEA_FISH_CLASS` | 931 | JARL | Norse Chieftain | 70 |
| `DEER` | 65 | DEERX | Deer | 70 |
| `DEMOLITION_SHIP` | 527 | RMSHP | Demolition Ship | 70 |
| `DIRE_WOLF` | 89 | DWOLF | Dire Wolf | 70 |
| `DLC_ABRAHAELEPHANT` | 1071 | HABRAHA | Abraha Elephant | 70 |
| `DLC_ACACIATREE` | 1063 | FACA | Tree (Acacia) | 10 |
| `DLC_AFRICANBUSH` | 1053 | BUSH2 | Bush B | 10 |
| `DLC_AFRICANHUT_A` | 1082 | AHUTA | Hut A | 80 |
| `DLC_AFRICANHUT_B` | 1083 | AHUTB | Hut B | 80 |
| `DLC_AFRICANHUT_C` | 1084 | AHUTC | Hut C | 80 |
| `DLC_AFRICANHUT_D` | 1085 | AHUTD | Hut D | 80 |
| `DLC_AFRICANHUT_E` | 1086 | AHUTE | Hut E | 80 |
| `DLC_AFRICANHUT_F` | 1087 | AHUTF | Hut F | 80 |
| `DLC_AFRICANHUT_G` | 1088 | AHUTG | Hut G | 80 |
| `DLC_ANIMALSKELETON` | 1091 | SKELA | Animal Skeleton | 10 |
| `DLC_ARAMBAI` | 1126 | ARAMBAI | Arambai | 70 |
| `DLC_AUTUMNSNOWTREE` | 1249 | FAUTUMS | Tree (Oak Autumn Snow) | 10 |
| `DLC_AUTUMNTREE` | 1248 | FAUTUM | Tree (Oak Autumn) | 10 |
| `DLC_BABUR` | 1070 | HBABUR | Babur | 70 |
| `DLC_BALLISTAELEPHANT` | 1120 | ELEBALI | Ballista Elephant | 70 |
| `DLC_BAOBABTREE` | 1052 | FBAO | Tree (Baobab) | 10 |
| `DLC_BARRICADE` | 1090 | BARRICADE | Barricade A | 80 |
| `DLC_BATTLEELEPHANT` | 1132 | BATELE | Battle Elephant | 70 |
| `DLC_BAYINNAUNG` | 1165 | HBAYIN | Bayinnaung | 70 |
| `DLC_BEAR` | 486 | BROWNBEAR | Brown Bear | 70 |
| `DLC_BOULDER_A` | 1048 | ROCKF1 | Rock Formation 1 | 10 |
| `DLC_BOULDER_B` | 1049 | ROCKF2 | Rock Formation 2 | 10 |
| `DLC_BOULDER_C` | 1050 | ROCKF3 | Rock Formation 3 | 10 |
| `DLC_BOXTURTLE` | 1141 | TURTLES | Box Turtles | 30 |
| `DLC_BUDDHA_STATUE_A` | 1171 | BSTATUE1 | Buddha Statue A | 10 |
| `DLC_BUDDHA_STATUE_B` | 1172 | BSTATUE2 | Buddha Statue B | 10 |
| `DLC_BUDDHA_STATUE_C` | 1173 | BSTATUE3 | Buddha Statue C | 10 |
| `DLC_BUDDHA_STATUE_D` | 1174 | BSTATUE4 | Buddha Statue D | 10 |
| `DLC_BUIBI` | 1183 | HBUIBI | Bui Bi | 70 |
| `DLC_CAMELARCHER` | 1007 | CAMAR | Camel Archer | 70 |
| `DLC_CARAVEL` | 1004 | CARAV | Caravel | 70 |
| `DLC_COW` | 705 | Cow Black and White | Cow A | 70 |
| `DLC_COW_B` | 1596 | Cow Black | Cow B | 70 |
| `DLC_COW_C` | 1598 | Cow Brown and White | Cow C | 70 |
| `DLC_COW_D` | 1600 | Cow Brown | Cow D | 70 |
| `DLC_CROCODILE` | 1031 | CROCO | Crocodile | 70 |
| `DLC_DAGNAJAN` | 1106 | HDAGNA | Dagnajan | 70 |
| `DLC_DEADTREE` | 1250 | FDEAD | Tree (Dead) | 10 |
| `DLC_DEMOLITIONRAFT` | 1104 | SDGAL | Demolition Raft | 70 |
| `DLC_DINHLE` | 1184 | HDINHLE | Dinh Le | 70 |
| `DLC_DRAGONTREE` | 1051 | FDRA | Tree (Dragon) | 10 |
| `DLC_DROMEDARY` | 1237 | DROME | Bactrian Camel | 70 |
| `DLC_ELEPHANT` | 1301 | WELEF | Elephant | 70 |
| `DLC_ELITEARAMBAI` | 1128 | EARAMBAI | Elite Arambai | 70 |
| `DLC_ELITEBALLISTAELEPHANT` | 1122 | EELEBALI | Elite Ballista Elephant | 70 |
| `DLC_ELITEBATTLEELEPHANT` | 1134 | EBATELE | Elite Battle Elephant | 70 |
| `DLC_ELITECAMELARCHER` | 1009 | ECAMAR | Elite Camel Archer | 70 |
| `DLC_ELITECARAVEL` | 1006 | ECARAV | Elite Caravel | 70 |
| `DLC_ELITEGBETO` | 1015 | EGBETO | Elite Gbeto | 70 |
| `DLC_ELITEGENITOUR` | 1012 | EGENITO | Elite Genitour | 70 |
| `DLC_ELITEKARAMBIT` | 1125 | EKARAM | Elite Karambit Warrior | 70 |
| `DLC_ELITEORGANGUN` | 1003 | EORGAN | Elite Organ Gun | 70 |
| `DLC_ELITERATTANARCHER` | 1131 | ERATAN | Elite Rattan Archer | 70 |
| `DLC_ELITESHOTELWARRIOR` | 1018 | ESHOTEL | Elite Shotel Warrior | 70 |
| `DLC_ENVOY` | 1186 | HENVOY | Envoy | 70 |
| `DLC_FEITORIA` | 1021 | FEITO | Feitoria | 80 |
| `DLC_FENCE` | 1062 | FENCE | Fence | 80 |
| `DLC_FERN_PATCH` | 1175 | GRSSP3 | Fern Patch | 10 |
| `DLC_FIREGALLEY` | 1103 | SFRGAL | Fire Galley | 70 |
| `DLC_FORTIFIED_PALISADE_WALL` | 119 | WALL4 | Fortified Palisade Wall | 80 |
| `DLC_FORTIFIED_TOWER` | 1102 | SEAFORF | Fortified Tower | 80 |
| `DLC_GAJAH_MADA` | 1157 | HGADJAH | Gajah Mada | 70 |
| `DLC_GALLOW` | 1095 | GALLOW | Gallow | 10 |
| `DLC_GBETO` | 1013 | GBETO | Gbeto | 70 |
| `DLC_GENITOUR` | 1010 | GENITO | Genitour | 70 |
| `DLC_GIDAJAN` | 1109 | HGIDAJ | Gidajan | 70 |
| `DLC_GOAT` | 1060 | GOAT | Goat | 70 |
| `DLC_GOOSE` | 1243 | GOOSE | Goose | 70 |
| `DLC_GRANARY` | 1089 | GRANARY | Granary | 10 |
| `DLC_GUGLIELMO` | 1072 | HGUGLIE | Guglielmo Embriaco | 70 |
| `DLC_HUAYNA_CAPAC` | 1075 | HHUAYNA | Huayna Capac | 70 |
| `DLC_IBEX` | 1239 | IBEX | Ibex | 70 |
| `DLC_IMPERIALSKIRMISHER` | 1155 | IHXBOW | Imperial Skirmisher | 70 |
| `DLC_ITZCOATL` | 1067 | HITZCOATL | Itzcoatl | 70 |
| `DLC_JAYANEGARA` | 1158 | HJAYANEGARA | Jayanegara | 70 |
| `DLC_JAYAVIRAVARMAN` | 1164 | HJAYA | Jayaviravarman | 70 |
| `DLC_KARAMBIT` | 1123 | KARAM | Karambit Warrior | 70 |
| `DLC_KOMODO` | 1135 | KOMODO | Komodo Dragon | 70 |
| `DLC_LELOI` | 1178 | HLELOI | Le Loi | 70 |
| `DLC_LETRIEN` | 1181 | HLETRIEN | Le Trien | 70 |
| `DLC_LION` | 1029 | LION | Lion | 70 |
| `DLC_LITTLEJOHN` | 1077 | HLJOHN | Little John | 70 |
| `DLC_LLAMA` | 305 | LLAMAA | Llama A | 70 |
| `DLC_LUUNHANCHU` | 1182 | HLUUNHANCHU | Luu Nhan Chu | 70 |
| `DLC_MANGROVE_TREE` | 1144 | FMANGRO | Tree (Mangrove) | 10 |
| `DLC_MIKLOSTOLDI` | 1076 | HMIKLOS | Miklos Toldi | 70 |
| `DLC_MUSA` | 1034 | HMUSA | Musa ibn Nusayr | 70 |
| `DLC_MUSTAFA` | 1068 | HPASHA | Mustafa Pasha | 70 |
| `DLC_ORANGEBUSH` | 1059 | FORAGM | Fruit Bush | 10 |
| `DLC_ORGANGUN` | 1001 | ORGAN | Organ Gun | 70 |
| `DLC_OSTRICH` | 1026 | OSTRICH | Ostrich | 70 |
| `DLC_PACHACUTI` | 1074 | HPACHAC | Pachacuti | 70 |
| `DLC_PENGUIN` | 639 | PENGUI | War Penguin | 70 |
| `DLC_PIG` | 1245 | PIG | Pig | 70 |
| `DLC_RADEN_WIJAYA` | 1159 | HRADEN | Raden Wijaya | 70 |
| `DLC_RAINTREE` | 1146 | FRAIN | Tree (Rainforest) | 10 |
| `DLC_RATTANARCHER` | 1129 | RATAN | Rattan Archer | 70 |
| `DLC_RHINO` | 1139 | RHINO | Rhinoceros | 70 |
| `DLC_RICHARDDECLARE` | 1037 | HRDCLARE | Richard de Clare | 70 |
| `DLC_ROCKBEACH` | 1148 | ROCKB1 | Rock (Beach) | 10 |
| `DLC_ROCKJUNGLE` | 1149 | ROCKJ1 | Rock (Jungle) | 10 |
| `DLC_SAVANNAHPATCH` | 1033 | GRSSP2 | Grass Patch, Dry | 10 |
| `DLC_SHOTELWARRIOR` | 1016 | SHOTEL | Shotel Warrior | 70 |
| `DLC_SIEGETOWER` | 1105 | SIEGTWR | Siege Tower | 70 |
| `DLC_SNOWLEOPARD` | 1241 | SLEOPA | Snow Leopard | 70 |
| `DLC_STELAE_A` | 1092 | STELAEA | Stelae A | 10 |
| `DLC_STELAE_B` | 1093 | STELAEB | Stelae B | 10 |
| `DLC_STELAE_C` | 1094 | STELAEC | Stelae C | 10 |
| `DLC_STORAGE` | 1081 | STORAGE | Storage | 80 |
| `DLC_STORK` | 1028 | STORK | Stork | 70 |
| `DLC_SUMANGURU` | 1080 | HSUMANGURU | Sumanguru | 70 |
| `DLC_SUNDA_ROYAL_FIGHTER` | 1160 | HSUNDA | Sunda Royal Fighter | 70 |
| `DLC_SUNDJATA` | 1035 | HSUNDJATA | Sundjata | 70 |
| `DLC_SURYAVARMAN_I` | 1162 | HSURYA | Suryavarman I | 70 |
| `DLC_SU_DINGFANG` | 1073 | HSUDING | Su Dingfang | 70 |
| `DLC_TABINSHWEHTI` | 1166 | UELEA | Tabinshwehti | 70 |
| `DLC_TARIQ` | 1036 | HTARIQ | Tariq ibn Ziyad | 70 |
| `DLC_TIGER` | 1137 | TIGER | Tiger | 70 |
| `DLC_TRISTAN` | 1038 | HTRISTAN | Tristan | 70 |
| `DLC_TROWULAN_GATE` | 1176 | TROWUG | Trowulan Gate | 10 |
| `DLC_UDAYADITYAVARMAN_I` | 1163 | HUDAYA | Udayadityavarman I | 70 |
| `DLC_VASES` | 1177 | VASES | Vases | 10 |
| `DLC_VULTURE` | 1305 | VULTURE | Vulture | 70 |
| `DLC_WANGTONG` | 1185 | HTRANTRI | Wang Tong | 70 |
| `DLC_WARRIORYODIT` | 1066 | HYODIT | Yodit | 70 |
| `DLC_WATERBUFFALO` | 1142 | BUFFALO | Water Buffalo | 70 |
| `DLC_WILD_CAMEL` | 884 | HORSW | Wild Camel | 70 |
| `DLC_WILD_DROMEDARY` | 1247 | HORSW | Wild Bactrian Camel | 70 |
| `DLC_YEKUNOAMLAK` | 1064 | HSHOTEL | Yekuno Amlak | 70 |
| `DLC_YODIT` | 1039 | HPYODIT | Princess Yodit | 70 |
| `DLC_ZAWISZATHEBLACK` | 1078 | HZAWISZA | Zawisza the Black | 70 |
| `DLC_ZEBRA` | 1019 | ZEBRA | Zebra | 70 |
| `DOCK` | 45 | DOCK | Dock | 80 |
| `DOCK_C` | 47 | DOCK3 | Dock | 80 |
| `DOCK_F` | 133 | DOCK2 | Dock | 80 |
| `DOCK_I` | 51 | DOCK4 | Dock | 80 |
| `DOMESTIC_ANIMAL_CLASS` | 929 | HSALAD | Saladin | 70 |
| `DOME_OF_THE_ROCK` | 690 | HDOR | Dome of the Rock | 80 |
| `DOPPELGANGER_CLASS` | 937 | WELEF_D |  | 30 |
| `DORADO` | 455 | FISH1 | Fish (Dorado) | 30 |
| `DUKE_D_ALENCON` | 638 | HALEN | Duke D'Alençon | 70 |
| `EAGLE_WARRIOR` | 751 | EAGLE | Eagle Scout | 70 |
| `ELEPHANT_ARCHER_CLASS` | 926 | HPRIT | Prithvi | 70 |
| `ELITE_BERSERK` | 694 | UVBRK | Elite Berserk | 70 |
| `ELITE_CANNON_GALLEON` | 691 | CNGAU | Elite Cannon Galleon | 70 |
| `ELITE_CATAPHRACT` | 553 | UCATA | Elite Cataphract | 70 |
| `ELITE_CHU_KO_NU` | 559 | UCHUK | Elite Chu Ko Nu | 70 |
| `ELITE_CONQUISTADOR` | 773 | UCONQ | Elite Conquistador | 70 |
| `ELITE_EAGLE_WARRIOR` | 752 | EAGLEX | Elite Eagle Warrior | 70 |
| `ELITE_GENITOUR` | 596 | GENITX | Elite Genitour | 70 |
| `ELITE_HUSKARL` | 555 | UGBRS | Elite Huskarl | 70 |
| `ELITE_JAGUAR_WARRIOR` | 726 | JAGUARX | Elite Jaguar Warrior | 70 |
| `ELITE_JANISSARY` | 557 | UJANI | Elite Janissary | 70 |
| `ELITE_LONGBOAT` | 533 | ULNGB | Elite Longship | 70 |
| `ELITE_LONGBOWMAN` | 530 | ULGBW | Elite Longbowman | 70 |
| `ELITE_MAMELUKE` | 556 | UDERV | Elite Mameluke | 70 |
| `ELITE_MANGUDAI` | 561 | UMOSU | Elite Mangudai | 70 |
| `ELITE_PLUMED_ARCHER` | 765 | UPLUM | Elite Plumed Archer | 70 |
| `ELITE_SAMURAI` | 560 | USMUR | Elite Samurai | 70 |
| `ELITE_SKIRMISHER` | 6 | HXBOW | Elite Skirmisher | 70 |
| `ELITE_TARKAN` | 757 | UTARK | Elite Tarkan | 70 |
| `ELITE_TEUTONIC_KNIGHT` | 554 | UTKNI | Elite Teutonic Knight | 70 |
| `ELITE_THROWING_AXEMAN` | 531 | UTAXE | Elite Throwing Axeman | 70 |
| `ELITE_TURTLE_SHIP` | 832 | UTURT | Elite Turtle Ship | 70 |
| `ELITE_WAR_ELEPHANT` | 558 | UMPCAV | Elite War Elephant | 70 |
| `ELITE_WAR_WAGON` | 829 | UWAGO | Elite War Wagon | 70 |
| `ELITE_WOAD_RAIDER` | 534 | UWBRS | Elite Woad Raider | 70 |
| `ELK` | 2737 | ELK | Elk | 70 |
| `EL_CID` | 198 | HELCID | El Cid | 70 |
| `EL_CID_CAMPEADOR` | 824 | HELCIDC | El Cid Campeador | 70 |
| `EMPEROR_IN_A_BARREL` | 733 | HPIKL | Emperor in a Barrel | 70 |
| `ERIK_THE_RED` | 171 | HERIK | Erik the Red | 70 |
| `ES_FLAG` | 851 | ESFLAG | ES Flag | 20 |
| `FARM` | 50 | FARM | Farm | 80 |
| `FARM_CLASS` | 949 |  |  | 10 |
| `FAST_FIRE_SHIP` | 532 | HFGAL | Fast Fire Ship | 70 |
| `FELLED_TREE` | 1539 | TREEAFELL | Felled Tree | 10 |
| `FELLED_TREE_BAMBOO` | 1540 | FBAMFELL | Felled Tree (Bamboo) | 10 |
| `FELLED_TREE_BAOBAB` | 1541 | FBAOFELL | Felled Tree (Baobab) | 10 |
| `FELLED_TREE_LUSH_BAMBOO` | 1542 | FLBAMFELL | Felled Tree (Lush Bamboo) | 10 |
| `FIRE_SHIP` | 529 | FRGAL | Fire Ship | 70 |
| `FIRE_TOWER` | 190 | WCTW3 | Fire Tower | 80 |
| `FISH` | 53 | FISHX | Fish (Perch) | 30 |
| `FISHING_BOAT_CLASS` | 921 | MONKM_D |  | 30 |
| `FISHING_SHIP` | 13 | FSHSP | Fishing Ship | 70 |
| `FISH_TRAP` | 199 | FTRAP | Fish Trap | 80 |
| `FLAG_A` | 600 | FLAGA | Flag A | 20 |
| `FLAG_B` | 601 | FLAGB | Flag B | 20 |
| `FLAG_C` | 602 | FLAGC | Flag C | 20 |
| `FLAG_CLASS` | 930 | HKOSHRAU | Khosrau | 70 |
| `FLAG_D` | 603 | FLAGD | Flag D | 20 |
| `FLAG_E` | 604 | FLAGE | Flag E | 20 |
| `FLAMINGO` | 2596 | FLAMINGO | Flamingo | 70 |
| `FLAMING_BIRD` | 2742 | FLAMINGBIRD | Flaming Bird | 70 |
| `FLOWER_BED` | 859 | FLWRB | Flower Bed | 10 |
| `FORAGE` | 59 | FORAG | Forage Bush | 10 |
| `FORAGE_BUSH_CLASS` | 907 | BGBA | Wooden Bridge B--Top | 80 |
| `FOREST_TREE` | 411 | FORTR | Tree (Oak Forest) | 10 |
| `FORTIFIED_WALL` | 155 | WALL3 | Fortified Wall | 80 |
| `FRANKISH_PALADIN` | 632 | HEROF | Frankish Paladin | 70 |
| `FRANKISH_RELIC` | 290 | RLIC4 |  | 70 |
| `FRIAR_TUCK` | 163 | HFRIAR | Friar Tuck | 70 |
| `GALLEON` | 442 | WARGA | Galleon | 70 |
| `GALLEY` | 539 | SGALY | Galley | 70 |
| `GATE_CLASS` | 939 | FLAME1 | Flame 1 | 20 |
| `GAWAIN` | 175 | HGAWA | Gawain | 70 |
| `GAZELLE` | 1796 | GAZELLE | Gazelle | 70 |
| `GENGHIS_KHAN` | 731 | HKHAN | Genghis Khan | 70 |
| `GENITOUR` | 583 | GENIT | Genitour | 70 |
| `GODS_OWN_SLING` | 683 | HGOS | God's Own Sling | 80 |
| `GODS_OWN_SLING_PACKED` | 729 | HGOSP | God's Own Sling (Packed) | 80 |
| `GOLD` | 66 | GOLDM | Gold Mine | 10 |
| `GOLD_FISH_CLASS` | 963 |  |  | 10 |
| `GOLD_HUNTABLE_CLASS` | 965 |  |  | 10 |
| `GOLD_MINE_CLASS` | 932 | SOGDIAN | Sogdian Cataphract | 70 |
| `GOTHIC_RELIC` | 292 | RLIC5 |  | 70 |
| `GRAVE` | 820 | GRAVES | Grave | 10 |
| `GREAT_FISH_MARLIN` | 450 | DOLP1 | Great Fish (Marlin) | 30 |
| `GREAT_PYRAMID` | 696 | HGPR | Great Pyramid | 80 |
| `GUANACO` | 2591 | GUANACO | Guanaco | 70 |
| `GUARD_TOWER` | 234 | WCTW2 | Guard Tower | 80 |
| `GUY_JOSSELYNE` | 648 | HJOSS | Guy Josselyne | 70 |
| `HALBERDIER` | 359 | HLBDM | Halberdier | 70 |
| `HAND_CANNONEER` | 5 | HCANR | Hand Cannoneer | 70 |
| `HARALD_HARDRAADE` | 426 | HHAHA | Harald Hardrada | 70 |
| `HARE_A` | 2098 | HAREA | Hare A | 70 |
| `HARE_B` | 2099 | HAREB | Hare B | 70 |
| `HAWK` | 96 | HAWKX | Hawk | 70 |
| `HAY_STACK` | 857 | HSTAC | Hay Stack | 10 |
| `HEAD` | 821 | HEADS | Head | 10 |
| `HEALER_CLASS` | 917 | VULTURE | Vulture | 70 |
| `HEAVY_CAMEL` | 330 | HCLRY | Heavy Camel Rider | 70 |
| `HEAVY_CAVALRY_ARCHER` | 474 | HCVAR | Heavy Cavalry Archer | 70 |
| `HEAVY_DEMOLITION_SHIP` | 528 | CRMSH | Heavy Demolition Ship | 70 |
| `HEAVY_SCORPION` | 542 | HWBAL | Heavy Scorpion | 70 |
| `HENRY_V` | 847 | HENRY | Henry V | 70 |
| `HERO_CLASS` | 925 | HQUEEN | Sanyogita | 70 |
| `HORSE` | 814 | HORSE | Horse A | 70 |
| `HORSE_B` | 1356 | HORSEHVY | Horse B | 70 |
| `HORSE_C` | 1602 | HORSEGBL | Horse C | 70 |
| `HORSE_D` | 1604 | HORSEGBR | Horse D | 70 |
| `HORSE_E` | 1606 | HORSEWBR | Horse E | 70 |
| `HOUSE` | 70 | HOUS | House | 80 |
| `HOUSE_C` | 464 | HOUS3 | House | 80 |
| `HOUSE_F` | 463 | HOUS2 | House | 80 |
| `HOUSE_I` | 465 | HOUS4 | House | 80 |
| `HOUSE_NOMADS_C` | 191 | HOUS3m | House | 80 |
| `HOUSE_NOMADS_I` | 192 | HOUS4m | House | 80 |
| `HROLF_THE_GANGER` | 428 | HHRTG | Hrolf the Ganger | 70 |
| `HUNTING_WOLF` | 700 | HWOLF | Hunting Wolf | 70 |
| `HUSKARL` | 41 | GBRSK | Huskarl | 70 |
| `HUSSAR` | 441 | HUSSAR | Hussar | 70 |
| `IMAM` | 842 | HIMAM | Imam | 70 |
| `INFANTRY_CLASS` | 906 | BGAC | Wooden Bridge A--Bottom | 80 |
| `IRON_BOAR` | 810 | HEROBOAR | Iron Boar | 70 |
| `ITALIAN_PINETREE` | 1348 | ITPINE | Tree (Italian Pine) | 10 |
| `JAGUAR` | 812 | GJAGR | Jaguar | 70 |
| `JAGUAR_WARRIOR` | 725 | JAGUAR | Jaguar Warrior | 70 |
| `JANISSARY` | 46 | JANNI | Janissary | 70 |
| `JAPANESE_RELIC` | 294 | RLIC6 |  | 70 |
| `JAVELINA` | 822 | BOARJ | Javelina | 70 |
| `JEAN_BUREAU` | 650 | HBURE | Jean Bureau | 70 |
| `JEAN_DE_LORRAIN` | 644 | HLORR | Jean de Lorrain | 70 |
| `JOAN_OF_ARC` | 629 | HJOKT | Joan of Arc | 70 |
| `JOAN_THE_MAID` | 430 | HJODA | Joan the Maid | 70 |
| `JUNGLETREE` | 414 | FJUN | Tree (Jungle) | 10 |
| `KEEP` | 235 | WCTW3 | Keep | 80 |
| `KING` | 434 | KINGX | King | 70 |
| `KING_ALFONSO` | 840 | HALFON | King Alfonso | 70 |
| `KING_ARTHUR` | 173 | HKARTH | King Arthur | 70 |
| `KING_CLASS` | 959 |  |  | 10 |
| `KING_SANCHO` | 838 | HSANC | King Sancho | 70 |
| `KITABATAKE` | 195 | HKITA | Kitabatake | 70 |
| `KNIGHT` | 38 | KNGHT | Knight | 70 |
| `KUSHLUK` | 702 | HKUSH | Kushluk | 70 |
| `LANCELOT` | 174 | HLANCE | Lancelot | 70 |
| `LAND_MINE_CLASS` | 964 |  |  | 10 |
| `LA_HIRE` | 640 | HHIRE | La Hire | 70 |
| `LIGHT_CAVALRY` | 546 | LTCAV | Light Cavalry | 70 |
| `LIVESTOCK_CLASS` | 958 |  |  | 10 |
| `LLAMA_B` | 1963 | LLAMAB | Llama B | 70 |
| `LONGBOAT` | 250 | LNGBT | Longship | 70 |
| `LONGBOWMAN` | 8 | LNGBW | Longbowman | 70 |
| `LONG_SWORDSMAN` | 77 | THSWD | Long Swordsman | 70 |
| `LORD_DE_GRAVILLE` | 642 | HGRAV | Lord de Graville | 70 |
| `LUMBER_CAMP` | 562 | SMIL | Lumber Camp | 80 |
| `LUMBER_CAMP_C` | 564 | SMIL3 | Lumber Camp | 80 |
| `LUMBER_CAMP_F` | 563 | SMIL2 | Lumber Camp | 80 |
| `LUMBER_CAMP_I` | 565 | SMIL4 | Lumber Camp | 80 |
| `LUSH_BAMBOO_STUMP` | 1538 | STUMLB2 | Lush Bamboo Stump | 10 |
| `LUSH_BAMBOO_TREE` | 1984 | FLBAM | Tree (Lush Bamboo Forest) | 10 |
| `LYNX` | 2736 | LYNX | Lynx | 70 |
| `MACAW` | 816 | MACAW | Macaw | 70 |
| `MAMELUKE` | 282 | DERVI | Mameluke | 70 |
| `MANGONEL` | 280 | MANGO | Mangonel | 70 |
| `MANGUDAI` | 11 | MOSUN | Mangudai | 70 |
| `MAN_AT_ARMS` | 75 | SWDMN | Man-at-Arms | 70 |
| `MAP_REVEALER` | 837 | REVEAL | Map Revealer | 20 |
| `MARKET` | 84 | MRKT | Market | 80 |
| `MARKET_C` | 116 | MRKT3 | Market | 80 |
| `MARKET_I` | 137 | MRKT4 | Market | 80 |
| `MASTER_OF_THE_TEMPLAR` | 680 | HMOT | Master of the Templar | 70 |
| `MILITIA` | 74 | SPRMN | Militia | 70 |
| `MILL` | 68 | MILL | Mill | 80 |
| `MILL_C` | 130 | MILL3 | Mill | 80 |
| `MILL_F` | 129 | MILL2 | Mill | 80 |
| `MILL_I` | 131 | MILL4 | Mill | 80 |
| `MINAMOTO` | 196 | HMINA | Minamoto | 70 |
| `MINING_CAMP` | 584 | MINE | Mining Camp | 80 |
| `MINING_CAMP_C` | 586 | MINE3 | Mining Camp | 80 |
| `MINING_CAMP_F` | 585 | MINE2 | Mining Camp | 80 |
| `MINING_CAMP_I` | 587 | MINE4 | Mining Camp | 80 |
| `MISCELLANEOUS_CLASS` | 911 | BGAA |  | 80 |
| `MISC_BUILDING_CLASS` | 960 |  |  | 10 |
| `MISSIONARY` | 775 | MONKY | Missionary | 70 |
| `MONASTERY` | 104 | CRCH | Monastery | 80 |
| `MONASTERY_C` | 31 | CRCH3 | Monastery | 80 |
| `MONASTERY_CLASS` | 918 | ROCKX2 | Rock 2 | 10 |
| `MONASTERY_F` | 30 | CRCH2 | Monastery | 80 |
| `MONASTERY_I` | 32 | CRCH4 | Monastery | 80 |
| `MONK` | 125 | MONKX | Monk | 70 |
| `MONK_WITH_RELIC_CLASS` | 943 | HOSMAN | Osman | 70 |
| `MONUMENT` | 826 | KOH-FLAG | Monument | 80 |
| `MORDRED` | 176 | HMORD | Mordred | 70 |
| `MOSQUE` | 655 | MSQUE | Mosque | 80 |
| `NINE_BANDS` | 720 | FLAGM | Nine Bands | 20 |
| `NOBUNAGA` | 845 | HNOB | Nobunaga | 70 |
| `OAKTREE` | 349 | FOAK | Tree (Oak) | 10 |
| `OCEAN_FISH_CLASS` | 905 | BGAB | Wooden Bridge A--Middle | 80 |
| `OLD_STONE_HEAD` | 855 | SHEAD | Old Stone Head | 10 |
| `OLIVE_TREE` | 1349 | OLIVE | Tree (Olive) | 10 |
| `ONAGER` | 550 | ONAGR | Onager | 70 |
| `ORE_MINE_CLASS` | 948 |  |  | 10 |
| `ORNLU_THE_WOLF` | 707 | HORNL | Ornlu the Wolf | 70 |
| `OUTPOST` | 598 | WCTWX | Outpost | 80 |
| `OYSTERS` | 2170 | Oysters | Oysters | 10 |
| `PACKED_TREBUCHET_CLASS` | 951 |  |  | 10 |
| `PALADIN` | 569 | HEROC | Paladin | 70 |
| `PALISADE_WALL` | 72 | WALL | Palisade Wall | 80 |
| `PALMTREE` | 351 | FPAL | Tree (Palm Forest) | 10 |
| `PAPAYA_TREE` | 2599 | PAPAYA | Papaya Tree | 10 |
| `PAVILION` | 624 | PAV1 | Pavilion A | 80 |
| `PEACH_BLOSSOM_TREE` | 2017 | FPEACHBLOSSOM | Tree (Peach Blossom) | 10 |
| `PERSIAN_RELIC` | 295 | RLIC7 |  | 70 |
| `PETARD` | 440 | PETARD | Petard | 70 |
| `PETARD_CLASS` | 935 | ALFRED_D |  | 30 |
| `PHALANX_CLASS` | 928 | MONKF_D |  | 30 |
| `PHEASANT` | 2739 | PHEASANT | Pheasant | 70 |
| `PIECE_OF_THE_TRUE_CROSS` | 688 | HPTC | Piece of the True Cross | 70 |
| `PIKEMAN` | 358 | ISPKM | Pikeman | 70 |
| `PIKEMAN_CLASS` | 946 |  |  | 10 |
| `PINEAPPLE_BUSH` | 2650 | FORAGPINEAPPLE | Pineapple Bush | 10 |
| `PINETREE` | 350 | FPIN | Tree (Pine Forest) | 10 |
| `PLANTS` | 818 | PLANTS | Plant | 10 |
| `PLANT_HEATHER` | 2743 | Plant Heather | Plant (Heather) | 10 |
| `PLUMED_ARCHER` | 763 | PLUME | Plumed Archer | 70 |
| `POLAR_BEAR` | 2090 | POLARBEAR | Polar Bear | 70 |
| `POPE_LEO_I` | 781 | HPOPE | Pope Leo I | 70 |
| `PREDATOR_ANIMAL_CLASS` | 910 | IMPALED | Impaled Corpse | 10 |
| `PREY_ANIMAL_CLASS` | 909 | BGBC | Wooden Bridge B--Bottom | 80 |
| `PYRAMID` | 689 | HPYR | Pyramid | 80 |
| `RABID_WOLF` | 202 | WOLF2 | Rabid Wolf | 70 |
| `RAIDER_CLASS` | 956 |  |  | 10 |
| `RAVEN` | 2578 | RAVEN | Raven | 70 |
| `RED_FOX` | 1955 | REDFOX | Red Fox | 70 |
| `RELIC` | 285 | RELIC | Relic | 70 |
| `RELIC_CLASS` | 942 | FLAME4 | Flame 4 | 20 |
| `RESOURCE_PILE_CLASS` | 941 | FLAME3 | Flame 3 | 20 |
| `REYNALD_DE_CHATILLON` | 678 | HREY | Reynald de Chatillon | 70 |
| `RHEA` | 2597 | RHEA | Rhea | 70 |
| `RICHARD_THE_LIONHEARTED` | 160 | HRLION | Richard the Lionheart | 70 |
| `ROBIN_HOOD` | 200 | HROBN | Robin Hood | 70 |
| `ROCK` | 623 | ROCKX | Rock 1 | 10 |
| `ROCK_MOSSY` | 1967 | ROCKMOSSY | Rock (Mossy) | 10 |
| `ROCK_SNOW` | 2734 | ROCKSNOW | Rock (Snow) | 10 |
| `ROLAND` | 166 | HROLAN | Roland | 70 |
| `ROMAN_RUINS` | 856 | RUINS | Roman Ruins | 10 |
| `RUGS` | 711 | RUGS | Rugs | 10 |
| `RUINS` | 345 | TERRX | Ruins | 80 |
| `SABOTEUR` | 706 | HDSQD | Saboteur | 70 |
| `SALMON` | 456 | FISH2 | Fish (Salmon) | 30 |
| `SALVAGE_PILE_CLASS` | 940 | FLAME2 | Flame 2 | 20 |
| `SAMURAI` | 291 | SMURI | Samurai | 70 |
| `SARACEN_RELIC` | 296 | RLIC8 |  | 70 |
| `SCORPION` | 279 | SCBAL | Scorpion | 70 |
| `SCORPION_CLASS` | 955 |  |  | 10 |
| `SCOUT` | 448 | SCOUT | Scout Cavalry | 70 |
| `SCOUT_CAVALRY_CLASS` | 947 |  |  | 10 |
| `SCYTHIAN_SCOUT` | 852 | HSCOUT | Scythian Scout | 70 |
| `SCYTHIAN_WILD_WOMAN` | 783 | HWITCH | Scythian Wild Woman | 70 |
| `SEAL` | 2735 | SEAL | Seal | 70 |
| `SEA_TOWER` | 785 | STWR | Sea Tower | 80 |
| `SHAH` | 704 | HSHAH | Shah | 70 |
| `SHEEP` | 594 | SHEEPG | Sheep | 70 |
| `SHERIFF_OF_NOTTINGHAM` | 164 | HSHERN | Sheriff of Nottingham | 70 |
| `SHIPWRECK` | 721 | SPWK1 | Shipwreck A | 20 |
| `SHORE_FISH` | 69 | FISHS | Shore Fish | 30 |
| `SHORE_FISH_CLASS` | 933 | BARRELS | Barrels | 10 |
| `SIEGE_ONAGER` | 588 | SNAGR | Siege Onager | 70 |
| `SIEGE_RAM` | 548 | SGRAM | Siege Ram | 70 |
| `SIEGE_WEAPON_CLASS` | 913 | BGAC |  | 80 |
| `SIEGE_WORKSHOP` | 49 | SIWS | Siege Workshop | 80 |
| `SIEGE_WORKSHOP_I` | 150 | SIWS4 | Siege Workshop | 80 |
| `SIEGFRIED` | 170 | HSIEG | Siegfried | 70 |
| `SIEUR_BERTRAND` | 636 | HBERT | Sieur Bertrand | 70 |
| `SIEUR_DE_METZ` | 634 | HMETZ | Sieur de Metz | 70 |
| `SIGN` | 819 | SIGN | Sign | 10 |
| `SIR_JOHN_FASTOLF` | 652 | HFALS | Sir John Fastolf | 70 |
| `SKELETON` | 710 | SKELETON | Skeleton | 10 |
| `SKIRMISHER` | 7 | XBOWM | Skirmisher | 70 |
| `SNAKE` | 2592 | SNAKE | Snake | 70 |
| `SNAPPER` | 458 | FISH4 | Fish (Snapper) | 30 |
| `SNOWPINETREE` | 413 | FSNO | Tree (Snow Pine) | 10 |
| `SPEARMAN` | 93 | PKEMN | Spearman | 70 |
| `SPEARMAN_CLASS` | 950 |  |  | 10 |
| `STABLE` | 101 | STBL | Stable | 80 |
| `STABLE_C` | 86 | STBL3 | Stable | 80 |
| `STABLE_I` | 153 | STBL4 | Stable | 80 |
| `STATUE` | 817 | Statue A |  | 10 |
| `STONE` | 102 | STONM | Stone Mine | 10 |
| `STONE_MINE_CLASS` | 908 | BGBB | Wooden Bridge B--Middle | 80 |
| `STUMP` | 809 | STUMP2 | Stump | 10 |
| `SUBOTAI` | 698 | HSUBO | Subotai | 70 |
| `TAMERLANE` | 172 | HTAME | Tamerlane | 70 |
| `TAPIR` | 2589 | TAPIR | Tapir | 70 |
| `TARKAN` | 755 | TARKAN | Tarkan | 70 |
| `TERRAIN_CLASS` | 914 | QUARRY | Quarry | 10 |
| `TEUTONIC_KNIGHT` | 25 | TKNIT | Teutonic Knight | 70 |
| `TEUTONIC_RELIC` | 297 | RLIC9 |  | 70 |
| `THEODORIC_THE_GOTH` | 168 | HTHEOD | Theodoric the Goth | 70 |
| `THE_ACCURSED_TOWER` | 684 | HTAT | The Accursed Tower | 80 |
| `THE_BLACK_PRINCE` | 161 | HBLACK | The Black Prince | 70 |
| `THE_TOWER_OF_FLIES` | 685 | HTOF | The Tower of Flies | 80 |
| `THROWING_AXEMAN` | 281 | TAXEM | Throwing Axeman | 70 |
| `TORCH` | 499 | TORCH | Torch A | 20 |
| `TORCH_CONVERTING` | 854 | TORCH2 | Torch A (Convertable) | 70 |
| `TOWER_CLASS` | 952 |  |  | 10 |
| `TOWN_CENTER` | 109 | RTWC | Town Center | 80 |
| `TOWN_CENTER_C` | 141 | RTWC3 | Town Center | 80 |
| `TOWN_CENTER_F` | 71 | RTWC2 | Town Center | 80 |
| `TOWN_CENTER_FOUNDATION` | 621 | RTWC1X | Town Center | 80 |
| `TOWN_CENTER_FOUNDATION_C` | 484 | RTWC3X | Town Center | 80 |
| `TOWN_CENTER_FOUNDATION_F` | 617 | RTWC2X | Town Center | 80 |
| `TOWN_CENTER_FOUNDATION_I` | 597 | RTWC4X | Town Center | 80 |
| `TOWN_CENTER_I` | 142 | RTWC4 | Town Center | 80 |
| `TRADE_BOAT_CLASS` | 902 | SMOKE | Smoke | 20 |
| `TRADE_CART` | 128 | TCART | Trade Cart (Empty) | 70 |
| `TRADE_CART_CLASS` | 919 | AAGUAR_D |  | 30 |
| `TRADE_COG` | 17 | COGXX | Trade Cog | 70 |
| `TRADE_WORKSHOP` | 110 | TDWS | Trade Workshop | 80 |
| `TRANSPORT_SHIP` | 545 | XPORT | Transport Ship | 70 |
| `TRANSPORT_SHIP_CLASS` | 920 | AARCH_D |  | 30 |
| `TREBUCHET` | 42 | TREBU | Trebuchet | 80 |
| `TREBUCHET_PACKED` | 331 | PTREB | Trebuchet (Packed) | 80 |
| `TREE_A` | 399 | TREEA | Tree A | 10 |
| `TREE_B` | 400 | TREEB | Tree B | 10 |
| `TREE_BRAZILWOOD` | 2580 | BRAZILWOOD | Tree (Brazilwood) | 10 |
| `TREE_C` | 401 | TREEC | Tree C | 10 |
| `TREE_CLASS` | 915 | LUMBER | Lumber | 10 |
| `TREE_D` | 402 | TREED | Tree D | 10 |
| `TREE_E` | 403 | TREEE | Tree E | 10 |
| `TREE_F` | 404 | TREEF | Tree F | 10 |
| `TREE_G` | 405 | TREEG | Tree G | 10 |
| `TREE_GREEN_OAK` | 2567 | GREENOAK | Tree (Oak Green) | 10 |
| `TREE_H` | 406 | TREEH | Tree H | 10 |
| `TREE_I` | 407 | TREEI | Tree I | 10 |
| `TREE_J` | 408 | TREEJ | Tree J | 10 |
| `TREE_K` | 409 | TREEK | Tree K | 10 |
| `TREE_L` | 410 | TREEL | Tree L | 10 |
| `TREE_MONKEY_PUZZLE` | 2570 | MONKEYPUZZLE | Tree (Monkey Puzzle) | 10 |
| `TREE_SPRUCE` | 2731 | SPRUCE | Tree (Spruce) | 10 |
| `TREE_SPRUCE_SNOW` | 2732 | SPRUCESNOW | Tree (Spruce Snow) | 10 |
| `TREE_STUMP_CLASS` | 916 | GOODS | Goods | 10 |
| `TREE_TD` | 284 | TREETD | Tree TD | 10 |
| `TREE_WAX_PALM` | 2583 | WAXPALM | Tree (Wax Palm) | 10 |
| `TUNA` | 457 | FISH3 | Fish (Tuna) | 30 |
| `TURKEY` | 833 | TURKYG | Turkey | 70 |
| `TURKISH_RELIC` | 298 | RLIC0 |  | 70 |
| `TURTLE_SHIP` | 831 | TURTL | Turtle Ship | 70 |
| `TWO_HANDED_SWORDSMAN` | 473 | HTHSW | Two-Handed Swordsman | 70 |
| `TWO_HANDED_SWORDSMAN_CLASS` | 945 | SHAHX_D |  | 30 |
| `UNIVERSITY` | 209 | UNIV | University | 80 |
| `UNIVERSITY_I` | 210 | UNIV4 | University | 80 |
| `UNPACKED_TREBUCHET_CLASS` | 954 |  |  | 10 |
| `VILLAGER` | 83 | VMBAS | Villager (Male) | 70 |
| `VILLAGER_BASE_F` | 293 | VFBAS | Villager (Female) | 70 |
| `VILLAGER_BUILDER_F` | 212 | VFBLD | Builder | 70 |
| `VILLAGER_BUILDER_M` | 118 | VMBLD | Builder | 70 |
| `VILLAGER_CLASS` | 904 | BGAA | Wooden Bridge A--Top | 80 |
| `VILLAGER_FARMER_F` | 214 | VFFAR | Farmer | 70 |
| `VILLAGER_FARMER_M` | 259 | VMFAR | Farmer | 70 |
| `VILLAGER_FISHER_F` | 57 | VFFIS | Fisherman | 70 |
| `VILLAGER_FISHER_M` | 56 | VMFIS | Fisherman | 70 |
| `VILLAGER_FORAGER_F` | 354 | VFFOR | Forager | 70 |
| `VILLAGER_FORAGER_M` | 120 | VMFOR | Forager | 70 |
| `VILLAGER_GOLD_F` | 581 | VFGLD | Gold Miner | 70 |
| `VILLAGER_GOLD_M` | 579 | VMGLD | Gold Miner | 70 |
| `VILLAGER_HUNTER_F` | 216 | VFHUN | Hunter | 70 |
| `VILLAGER_HUNTER_M` | 122 | VMHUN | Hunter | 70 |
| `VILLAGER_REPAIRER_F` | 222 | VFREP | Repairer | 70 |
| `VILLAGER_REPAIRER_M` | 156 | VMREP | Repairer | 70 |
| `VILLAGER_SHEPHERD_F` | 590 | VFSHE | Shepherd | 70 |
| `VILLAGER_SHEPHERD_M` | 592 | VMSHE | Shepherd | 70 |
| `VILLAGER_STONE_F` | 220 | VFMIN | Stone Miner | 70 |
| `VILLAGER_STONE_M` | 124 | VMMIN | Stone Miner | 70 |
| `VILLAGER_WOOD_F` | 218 | VFLUM | Lumberjack | 70 |
| `VILLAGER_WOOD_M` | 123 | VMLUM | Lumberjack | 70 |
| `WALL` | 117 | WALL2 | Stone Wall | 80 |
| `WALL_CLASS` | 927 | HCHAND | Chand Bardai | 70 |
| `WALRUS` | 1924 | WALRUS | Walrus | 70 |
| `WARSHIP_CLASS` | 922 | RMONKM | Monk with Relic | 70 |
| `WAR_ELEPHANT` | 239 | MPCAV | War Elephant | 70 |
| `WAR_ELEPHANT_CLASS` | 924 | QUEEN_D |  | 30 |
| `WAR_GALLEY` | 21 | GALLY | War Galley | 70 |
| `WAR_WAGON` | 827 | WAGON | War Wagon | 70 |
| `WATCH_TOWER` | 79 | WCTW | Watch Tower | 80 |
| `WILD_ALPACA` | 2615 | WALPACA | Wild Alpaca | 70 |
| `WILD_CHICKEN_A` | 2084 | WCHICKENA | Wild Chicken A | 70 |
| `WILD_CHICKEN_B` | 2086 | WCHICKENB | Wild Chicken B | 70 |
| `WILD_CHICKEN_C` | 2088 | WCHICKENC | Wild Chicken C | 70 |
| `WILD_HORSE` | 835 | HORSW | Wild Horse A | 70 |
| `WILD_HORSE_B` | 2092 | HORSWC | Wild Horse B | 70 |
| `WILD_HORSE_C` | 2093 | HORSWD | Wild Horse C | 70 |
| `WILD_HORSE_D` | 2094 | HORSWE | Wild Horse D | 70 |
| `WILD_HORSE_E` | 2095 | HORSWF | Wild Horse E | 70 |
| `WILD_MONKEY` | 2096 | WMONKEY | Monkey | 70 |
| `WILD_PENGUIN` | 2097 | WPENGUI | Penguin | 70 |
| `WILLIAM_THE_CONQUEROR` | 849 | HWIL | William the Conqueror | 70 |
| `WILLIAM_WALLACE` | 432 | HWIWA | William Wallace | 70 |
| `WILLOW_TREE` | 2025 | FWILLOW | Tree (Willow) | 10 |
| `WOAD_RAIDER` | 232 | WBRSK | Woad Raider | 70 |
| `WOLF` | 126 | WOLFX | Grey Wolf | 70 |
| `WONDER` | 276 | WNDR | Wonder | 80 |
| `YURT` | 712 | Yurt A | Yurt A | 80 |

## 5 值得单独记住的条目（DE）

| ID | 内部名 | 显示名 | 说明 |
|---|---|---|---|
| 83 | `VMBAS` | Villager (Male) | 男村民（83 是"村民"这个单位的 ID，不是 4） |
| 4 | `ARCHR` | Archer | 弓箭手基线 |
| 109 | `RTWC` | Town Center | 城镇中心 |
| 12 | `Barracks Age1` | Barracks | 兵营（黑暗时代形态） |
| 594 | `SHEEPG` | Sheep | 羊 |
| 199 | `FTRAP` | Fish Trap | 渔网 |
| 434 | `KINGX` | King | 国王（genieutils-py README 用它演示"禁止进驻"） |
| 315 | `ARROW3` |  | 征兵（城堡科技） |

> 注意 ID 与直觉不符：村民是 **83**，弓箭手是 **4**，城镇中心是 **109**。写 XS/场景效果前一定查表，别猜。


## 6 导出的 CSV

| 文件 | 行数 | 内容 |
|---|---|---|
| `_halfon_units_de.csv` | 2693 | DE 全单位+建筑 |
| `_halfon_units_ror.csv` | 2737 | RoR 全单位+建筑 |
| `_halfon_units_hd.csv` | 1390 | HD 全单位+建筑 |
| `_halfon_units_wk.csv` | 1390 | WK 全单位+建筑 |
| `_halfon_techs_de.csv` | 1510 | DE 全科技 |
| `_halfon_techs_ror.csv` | 191 | RoR 全科技 |
| `_halfon_techs_hd.csv` | 801 | HD 全科技 |
| `_halfon_techs_wk.csv` | 804 | WK 全科技 |

## 7 复跑

```bash
curl -s https://halfon.aoe2.se/data/units_buildings_techs.de.json  -o _probe/_tmp/halfon_de.json
curl -s https://halfon.aoe2.se/data/units_buildings_techs.ror.json -o _probe/_tmp/halfon_ror.json
curl -s https://halfon.aoe2.se/data/units_buildings_techs.hd.json  -o _probe/_tmp/halfon_hd.json
curl -s https://halfon.aoe2.se/data/units_buildings_techs.wk.json  -o _probe/_tmp/halfon_wk.json
C:/Users/26913/AppData/Local/Python/bin/python.exe -X utf8 _probe/_tmp/gen_vol13.py
```


## 8 局限（要知道它不给你什么）

- **不给科技依赖**：前置科技、文明专属、时代要求都没有。要科技树结构用 [15 卷](15-aoe2techtree-科技树数据.md)。
- **不给攻击加成明细**：只有 `attack` 基础值，`Attacks[]`（对哪个 class 加多少）在 aoe2techtree 那边才有。
- **不给训练时间/研究时间**：aoe2techtree 的 `TrainTime`/`ResearchTime` 才完整。
- **`class` 有个 -1**：91 条空名条目，是 .dat 里的占位槽，别当有效数据。
- **HD/WK 数据可能过时**：WK 最后更新在 5.8.1，之后再没动。
