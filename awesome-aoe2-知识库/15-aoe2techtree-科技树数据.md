# 15 · aoe2techtree 科技树数据全量（56 文明 / 255 单位 / 201 科技 / 40 建筑）

> 站点：<https://aoe2techtree.net/>（Siege Engineers，作者 HSZemi 等；DE Update 188329）

> 页面 HTML 是空壳，数据在 `data/data.json`（965 KB）+ `data/locales/<lng>/strings.json`（en 192762 B / zh 193598 B）。
> 另有独立子站 `/ror/`（Return of Rome）与 `/chronicles/`（Chronicles）。

> 本卷把 4 份数据全部拆解，名字已用 en/zh 双语言解析并写回 CSV。


## 0 一句话结论

这是**唯一给出"每个文明拥有哪些单位/科技"的完整集合 + 单位完整攻击/护甲明细**的公开数据源。
DE 侧：**56 个文明、255 个单位、201 个科技、40 个建筑**；每个单位带 `Attacks[]`（对哪个 class 加多少）与 `Armours[]`（属于哪些 class）。
与 [13 卷 HALFON](13-HALFON-全单位科技数据.md) 的分工：HALFON 给你"基础属性 + RMS 常量名"，aoe2techtree 给你"**加成明细 + 科技归属 + 训练/研究时间**"。
两者 ID 都等于 `empires2_x2_p1.dat` 的索引，可交叉核对。


## 1 站点与文件

| 路径 | 大小 | 内容 |
|---|---|---|
| `/data/data.json` | 965,318 B | 主体：`age_names` + `civs` + `data{Unit,Tech,Building}` + `tech_tree_strings` |
| `/data/locales/en/strings.json` | 192,762 B | 英文串表，1103 条 |
| `/data/locales/zh/strings.json` | 193,598 B | 中文串表，1103 条 |
| `/data/locales/<lng>/strings.json` | — | 另有 de/fr/it/es/ja/ko/pt/ru/tr/vi/... 等（`js/main.js` 的 `locales` 常量里列全）|
| `/data/trees/<CIV>.json` | 约 100 KB／个 | **每个文明一张科技树布局网格**（building_id + grid 二维数组），页面的树就是拿它画的 |
| `/ror/data/data.json` | 303,782 B | RoR（AoE1 内容）独立数据 |
| `/ror/data/locales/en/strings.json` | — | RoR 串表 |
| `/chronicles/data/data.json` | 302,778 B | Chronicles 独立数据 |

> **路径坑**：RoR/Chronicles 是独立子站，路径是 `/ror/data/data.json`，不是 `data/ror/data.json`（后者 404）。


## 2 数据结构

```
{
  "age_names": {"base": ["4201","4202","4203","4204"], "antiquity": [...]},
  "civs": {"Britons": {"name_string_id":10271, "help_string_id":120150, "era":"base",
                       "internal_name":"Britons", "Unit":[...ids], "Tech":[...ids],
                       "Building":[...ids], "meta":{}}},
  "data": {"Unit": {"4": {...}}, "Tech": {"22": {...}}, "Building": {"12": {...}}},
  "tech_tree_strings": {"Age of Empires II":"1001", "Building":"300084", ...}
}
```


### 2.1 `data.Unit`（255 条）字段

| 字段 | 含义 |
|---|---|
| `ID` | 单位 ID = dat 索引 |
| `internal_name` | 内部名 `ARCHR`/`VMBAS` |
| `HP` | 生命值 |
| `LineOfSight` | 视野 |
| `Attack` | 基础攻击（不含 class 加成） |
| `MeleeArmor` | 近战护甲 |
| `PierceArmor` | 远程护甲 |
| `Range` | 射程（0 = 近战） |
| `MinRange` | 最小射程（投石车类） |
| `ReloadTime` | 攻击间隔（秒） |
| `Speed` | 移动速度（tile/s） |
| `TrainTime` | 训练时间（秒） |
| `Cost{Food,Wood,Gold,Stone}` | 造价 |
| `GarrisonCapacity` | 驻扎容量 |
| `AccuracyPercent` | 命中率 % |
| `Attacks[{Class,Amount}]` | **对哪些 class 加多少攻击**——伤害计算的另一半 |
| `Armours[{Class,Amount}]` | **属于哪些 class、各有多少护甲** |
| `FrameDelay` | 出手帧延迟 |
| `AttackDelaySeconds` | 实际出手延迟（秒） |
| `BlastWidth` | 溅射半径 |
| `MaxCharge/ChargeType/ChargeEvent` | 蓄力机制（如冲锋、蓄力箭） |
| `RechargeRate/RechargeDuration` | 充能速率/时长 |
| `Trait / TraitPiece` | 特殊行为：`Trait` 是行为类型，`TraitPiece` 指向被建造/变身的目标 ID |
| `LanguageNameId` | **名字要 +9000 才是 strings.json 的 key**，见 §3 |

### 2.2 `data.Tech`（201 条）字段

| 字段 | 含义 |
|---|---|
| `ID` | 科技 ID = dat 索引 |
| `internal_name` | 内部名，如 `British Yeoman` |
| `Cost{...}` | 研究成本 |
| `ResearchTime` | 研究时间（秒） |
| `Repeatable` | 是否可重复研究 |
| `LanguageNameId` | **名字要 +10000 才是 strings.json 的 key** |

### 2.3 `data.Building`（40 条）字段

`AccuracyPercent, Armours, Attack, Attacks, Cost, GarrisonCapacity, HP, ID, LanguageNameId, LineOfSight, MeleeArmor, MinRange, PierceArmor, Range, ReloadTime, TrainTime, internal_name`（同 Unit，但无 Speed/FrameDelay）


## 3 名字解析的三个偏移量（这是本卷最重要的技术发现）

`LanguageNameId` **不能直接拿去查 `strings.json`**。实测：

| 类别 | 直接查命中 | 正确偏移 | 正确率 |
|---|---|---|---|
| Unit | 10 / 255 | **+9000** | 255 / 255 |
| Building | 7 / 40 | **+9000** | 40 / 40 |
| Tech | 2 / 201 | **+10000** | 201 / 201 |

例：`ARCHR` 的 `LanguageNameId = 5083`，`en["5083"]` 是 `None`，`en["14083"]` = `"Archer"`；
`British Yeoman` 的 `LanguageNameId = 7419`，`en["7419"]` 是 `None`，`en["17419"]` = `"Yeomen"`。

**原因**：.dat 里的 `LanguageDLLName` 字段在 DE 里是"旧版偏移"，正式串表在 `14000+`/`17000+` 段；
aoe2techtree 的 `data.json` 存的是 .dat 原值，而 `strings.json` 是从 language dll 里按最终 ID 导出的。
所以任何用这份数据的人都会踩这个坑——本卷已按偏移把中英文名全部回填进 CSV。

```python

def name(L, tbl):            # tbl = strings.json 字典

    for off in (0, 9000, 10000):

        s = tbl.get(str(L + off))

        if s: return s.replace("<br>", " ").strip()

    return ""

```


## 4 文明清单（56 个）

> `era` = `base`（主游戏）/ `antiquity`（Chronicles 的古代分支）。`civ_zh` 来自 zh 串表。

| 文明 | 中文 | era | 单位数 | 科技数 | 建筑数 |
|---|---|---|---|---|---|
| Armenians | 亚美尼亚 | base | 49 | 74 | 27 |
| Aztecs | 阿兹特克 | base | 44 | 66 | 26 |
| Bengalis | 孟加拉 | base | 49 | 75 | 28 |
| Berbers | 柏柏尔 | base | 55 | 75 | 27 |
| Bohemians | 波希米亚 | base | 50 | 73 | 29 |
| Britons | 不列颠 | base | 48 | 76 | 28 |
| Bulgarians | 保加利亚 | base | 49 | 69 | 28 |
| Burgundians | 勃艮第 | base | 51 | 74 | 29 |
| Burmese | 缅甸 | base | 51 | 73 | 28 |
| Byzantines | 拜占庭 | base | 57 | 75 | 29 |
| Celts | 凯尔特 | base | 51 | 67 | 28 |
| Chinese | 中国 | base | 51 | 74 | 29 |
| Cumans | 库曼 | base | 54 | 64 | 23 |
| Danes | 丹麦人 | base | 49 | 71 | 27 |
| Dravidians | 达罗毗荼 | base | 53 | 71 | 29 |
| Ethiopians | 埃塞俄比亚 | base | 52 | 71 | 28 |
| Franks | 法兰克 | base | 51 | 71 | 27 |
| Georgians | 格鲁吉亚 | base | 50 | 72 | 27 |
| Goths | 哥特 | base | 53 | 66 | 23 |
| Gurjaras | 瞿折罗 | base | 50 | 69 | 28 |
| Hindustanis | 印度斯坦 | base | 49 | 67 | 28 |
| Huns | 匈奴 | base | 48 | 63 | 24 |
| Incas | 印加 | base | 43 | 70 | 25 |
| Italians | 意大利 | base | 50 | 79 | 29 |
| Japanese | 日本 | base | 50 | 75 | 28 |
| Jurchens | 女真 | base | 50 | 75 | 28 |
| Khitans | 契丹 | base | 51 | 69 | 27 |
| Khmer | 高棉 | base | 53 | 71 | 28 |
| Koreans | 高丽 | base | 53 | 73 | 29 |
| Lithuanians | 立陶宛 | base | 50 | 74 | 29 |
| Magyars | 马扎尔 | base | 50 | 69 | 26 |
| Malay | 马来 | base | 50 | 71 | 29 |
| Malians | 马里 | base | 51 | 73 | 28 |
| Mapuche | 马普切 | base | 43 | 62 | 23 |
| Mayans | 玛雅 | base | 46 | 68 | 27 |
| Mongols | 蒙古 | base | 54 | 66 | 27 |
| Muisca | 穆伊斯卡 | base | 44 | 65 | 24 |
| Persians | 波斯 | base | 54 | 72 | 27 |
| Poles | 波兰 | base | 49 | 69 | 29 |
| Portuguese | 葡萄牙 | base | 48 | 76 | 30 |
| Romans | 罗马 | base | 46 | 66 | 28 |
| Saracens | 萨拉森 | base | 53 | 77 | 28 |
| Saxons | 撒克逊人 | base | 51 | 77 | 28 |
| Shu | 蜀 | base | 49 | 71 | 27 |
| Sicilians | 西西里 | base | 56 | 70 | 25 |
| Slavs | 斯拉夫 | base | 50 | 69 | 27 |
| Spanish | 西班牙 | base | 53 | 78 | 29 |
| Tatars | 鞑靼 | base | 55 | 68 | 28 |
| Teutons | 条顿 | base | 51 | 75 | 29 |
| Tupi | 图皮 | base | 44 | 61 | 24 |
| Turks | 土耳其 | base | 50 | 78 | 29 |
| Varangians | 瓦兰吉人 | base | 50 | 74 | 27 |
| Vietnamese | 越南 | base | 54 | 74 | 29 |
| Vikings | 维京 | base | 48 | 68 | 27 |
| Wei | 魏 | base | 48 | 67 | 28 |
| Wu | 吴 | base | 50 | 70 | 27 |

### 4.1 文明加成全文（`help_string_id`）

> 这是"卡面"原文：文明类型 + 逐条加成 + Unique Unit + Unique Techs + Team Bonus。完整文本在 `_techtree_civs.csv` 的 `bonus_text` 列。

**Armenians（亚美尼亚）**：Infantry and Naval civilization • Mule Carts cost -25% • Mule Cart technology effects +40% • Spearman- and Militia-line upgrades (except Man-at-Arms) available one age earlier • First Fortified Church receives a free Relic • Galley-line and Dromons fire an additional projectile Unique Unit: Composite Bowman (Foot Archer), Warrior Priest (Infantry) Unique Techs: • Cilician Fleet (Demolition Ships +

**Aztecs（阿兹特克）**：Infantry and Monk civilization • Start with +50 gold • Villagers carry +3 • Military Units train +15% faster • Monks gain +5 HP for each researched Monastery technology Unique Unit: Jaguar Warrior (Infantry) Unique Techs: • Atlatl (Skirmishers +1 attack, +1 range) • Garland Wars (Infantry +4 attack) Team Bonus: Relics generate +33% gold

**Bengalis（孟加拉）**：Elephant and Naval civilization • Town Centers spawn 2 Villagers when the next Age is reached • Cavalry +2 attack vs. Skirmishers • Elephant Units receive -25% bonus damage and are more resistant to conversion • Monks +3 melee/+3 pierce armor • Ships regenerate 15 HP per minute Unique Unit: Ratha (Mounted Archer) Unique Techs: • Paiks (Rathas and Elephant Units attack +20% faster) • Mahayana (Vill

**Berbers（柏柏尔）**：Cavalry and Naval civilization • Villagers move +5% faster in Dark Age, +10% faster starting in Feudal Age • Stable Units cost -15/20% in Castle/Imperial Age • Ships move +10% faster Unique Units: Camel Archer (Mounted Archer), Genitour (Mounted Skirmisher) Unique Techs: • Kasbah (Team Castles work +25% faster) • Maghrebi Camels (Camel Units regenerate 15 HP per minute) Team Bonus: Genitour availa

**Bohemians（波希米亚）**：Gunpowder and Monk civilization • Mining Camp technologies free • Blacksmiths and Universities cost -100 wood • Spearman-line deals +25% bonus damage • Fervor and Sanctity affect Villagers • Chemistry and Hand Cannoneer available in Castle Age Unique Units: Hussite Wagon (Siege Gunpowder Unit), Houfnice (Siege Gunpowder Unit) Unique Techs: • Wagenburg Tactics (Gunpowder Units move +10% faster) • H

**Britons（不列颠）**：Foot Archer civilization • Shepherds work +25% faster • Town Centers cost -50% wood starting in Castle Age • Foot Archers +1/+2 range in Castle/Imperial Age Unique Unit: Longbowman (Foot Archer) Unique Techs: • Yeomen (Foot Archers and Skirmisher-line +1 range; Watch Tower-line +2 attack) • Warwolf (Trebuchets deal blast damage and are more accurate) Team Bonus: Archery Ranges work +10% faster

**Bulgarians（保加利亚）**：Infantry and Cavalry civilization • Militia-line upgrades free • Blacksmith and Siege Workshop technologies cost -50% food • Town Centers cost -50% stone • Can build Krepost in Castle Age Unique Unit: Konnik (Cavalry) Unique Techs: • Stirrups (Cavalry attacks +33% faster) • Bagains (Militia-line +5 melee armor) Team Bonus: Blacksmiths work +80% faster

**Burgundians（勃艮第）**：Cavalry civilization • Economic upgrades available one age earlier and cost -40% food • Stable technologies cost -50% • Cavalier upgrade available in Castle Age • Gunpowder Units +25% attack Unique Units: Coustillier (Cavalry), Flemish Militia (Infantry) Unique Techs: • Burgundian Vineyards (Farmers slowly generate gold in addition to food) • Flemish Revolution (All existing Villagers are transfor

> 其余 48 个文明同理，见 CSV。


## 5 单位全量（255 条）

| ID | 内部名 | 英文名 | 中文名 | HP | 攻 | 远甲 | 近甲 | 射程 | 速度 | 训练(s) | 造价(F/W/G/S) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 4 | `ARCHR` | Archer | 步弓手 | 30 | 4 | 0 | 0 | 4 | 2 | 35 | 0/25/45/0 |
| 5 | `HCANR` | Hand Cannoneer | 火枪手 | 40 | 17 | 0 | 1 | 7 | 3.45 | 34 | 45/0/50/0 |
| 6 | `HXBOW` | Elite Skirmisher | 精锐 掷矛手 | 35 | 3 | 4 | 0 | 5 | 3 | 22 | 25/35/0/0 |
| 7 | `XBOWM` | Skirmisher | 掷矛手 | 30 | 2 | 3 | 0 | 4 | 3 | 26 | 25/35/0/0 |
| 8 | `LNGBW` | Longbowman | 长弓兵 | 35 | 6 | 0 | 0 | 5 | 2 | 18 | 0/35/40/0 |
| 11 | `MOSUN` | Mangudai | 蒙古突骑 | 60 | 6 | 0 | 0 | 4 | 2.1 | 26 | 0/55/65/0 |
| 13 | `FSHSP` | Fishing Ship | 渔船 | 50 | 0 | 1 | 1 | 0 | 0 | 40 | 0/75/0/0 |
| 17 | `COGXX` | Trade Cog | 贸易船 | 80 | 0 | 6 | 0 | 0 | 0 | 36 | 0/100/50/0 |
| 21 | `GALLY` | War Galley | 战船 | 125 | 7 | 4 | 0 | 6 | 3 | 27 | 0/90/30/0 |
| 24 | `CARCH` | Crossbowman | 弩手 | 35 | 5 | 0 | 0 | 5 | 2 | 27 | 0/25/45/0 |
| 25 | `TKNIT` | Teutonic Knight | 条顿 骑士 | 90 | 14 | 2 | 7 | 0 | 2 | 12 | 85/0/30/0 |
| 36 | `BCANN` | Bombard Cannon | 手推炮 | 80 | 40 | 5 | 2 | 12 | 6.5 | 56 | 0/225/225/0 |
| 38 | `KNGHT` | Knight | 骑士 | 100 | 10 | 2 | 2 | 0 | 1.8 | 30 | 60/0/75/0 |
| 39 | `CVRCH` | Cavalry Archer | 骑射手 | 50 | 6 | 0 | 0 | 4 | 2 | 37 | 0/40/60/0 |
| 40 | `CATAP` | Cataphract | 甲胄骑兵 | 110 | 9 | 1 | 2 | 0 | 1.8 | 20 | 70/0/75/0 |
| 41 | `GBRSK` | Huskarl | 近卫军 | 60 | 10 | 6 | 0 | 0 | 2 | 13 | 75/0/35/0 |
| 42 | `TREBU` | Trebuchet | 巨型投石机 | 150 | 200 | 150 | 1 | 16 | 10 | 50 | 0/200/200/0 |
| 46 | `JANNI` | Janissary | 苏丹亲兵 | 35 | 17 | 0 | 1 | 7 | 3.45 | 21 | 60/0/55/0 |
| 73 | `CHUKN` | Chu Ko Nu | 诸葛弩 | 45 | 8 | 0 | 0 | 4 | 3 | 16 | 0/40/35/0 |
| 74 | `SPRMN` | Militia | 民兵 | 40 | 4 | 1 | 0 | 0 | 2 | 21 | 50/0/20/0 |
| 75 | `SWDMN` | Man-at-Arms | 武士 | 45 | 6 | 1 | 0 | 0 | 2 | 21 | 50/0/20/0 |
| 77 | `THSWD` | Long Swordsman | 长剑士 | 60 | 9 | 1 | 1 | 0 | 2 | 21 | 50/0/20/0 |
| 83 | `VMBAS` | Villager | 村民 | 25 | 3 | 0 | 0 | 0 | 2 | 25 | 50/0/0/0 |
| 93 | `PKEMN` | Spearman | 长矛兵 | 45 | 3 | 0 | 0 | 0 | 3 | 22 | 35/25/0/0 |
| 125 | `MONKX` | Monk | 僧侣 | 30 | 0 | 0 | 0 | 9 | 1.6 | 51 | 0/0/100/0 |
| 128 | `TCART` | Trade Cart | 贸易车 | 70 | 0 | 0 | 0 | 0 | 0 | 51 | 0/100/50/0 |
| 185 | `SLINGR` | Slinger | 投石手 | 35 | 4 | 0 | 0 | 5 | 2 | 25 | 50/25/0/0 |
| 207 | `SHCLRY` | Imperial Camel Rider | 帝王 骆驼兵 | 140 | 8 | 0 | 0 | 0 | 2 | 20 | 55/0/60/0 |
| 232 | `WBRSK` | Woad Raider | 靛蓝突袭者 | 70 | 11 | 1 | 0 | 0 | 2 | 10 | 70/0/25/0 |
| 239 | `MPCAV` | War Elephant | 战象 | 450 | 15 | 2 | 1 | 0 | 2 | 25 | 170/0/85/0 |
| 250 | `LNGBT` | Longship | 维京长船 | 125 | 5 | 3 | 0 | 6 | 3 | 25 | 0/100/50/0 |
| 279 | `SCBAL` | Scorpion | 弩炮 | 40 | 11 | 7 | 0 | 7 | 3.6 | 30 | 0/75/75/0 |
| 280 | `MANGO` | Mangonel | 轻型投石车 | 50 | 40 | 6 | 0 | 7 | 6 | 46 | 0/160/135/0 |
| 281 | `TAXEM` | Throwing Axeman | 掷斧兵 | 60 | 7 | 0 | 0 | 5 | 2 | 13 | 55/0/25/0 |
| 282 | `DERVI` | Mameluke | 马穆鲁克 | 80 | 8 | 0 | 0 | 3 | 2 | 23 | 55/0/85/0 |
| 283 | `PALDN` | Cavalier | 重装骑士 | 120 | 12 | 2 | 2 | 0 | 1.8 | 30 | 60/0/75/0 |
| 291 | `SMURI` | Samurai | 日本武士 | 70 | 10 | 1 | 1 | 0 | 1.9 | 9 | 45/0/30/0 |
| 329 | `CVLRY` | Camel Rider | 骆驼兵 | 100 | 6 | 0 | 0 | 0 | 2 | 22 | 55/0/60/0 |
| 330 | `HCLRY` | Heavy Camel Rider | 重装 骆驼兵 | 120 | 7 | 0 | 0 | 0 | 2 | 22 | 55/0/60/0 |
| 331 | `PTREB` | Trebuchet | 巨型投石机 | 150 | 200 | 8 | 2 | 16 | 10 | 50 | 0/200/200/0 |
| 358 | `ISPKM` | Pikeman | 长枪兵 | 55 | 4 | 0 | 0 | 0 | 3 | 22 | 35/25/0/0 |
| 359 | `HLBDM` | Halberdier | 长戟兵 | 60 | 6 | 0 | 0 | 0 | 3 | 22 | 35/25/0/0 |
| 420 | `CANGA` | Cannon Galleon | 炮舰 | 120 | 50 | 5 | 0 | 13 | 10 | 46 | 0/200/150/0 |
| 422 | `CBATR` | Capped Ram | 中型 冲车 | 200 | 3 | 190 | -2 | 0 | 5 | 36 | 0/160/75/0 |
| 440 | `PETARD` | Petard | 爆破兵 | 50 | 25 | 2 | 0 | 0 | 0 | 25 | 65/0/20/0 |
| 441 | `HUSSAR` | Hussar | 翼骑兵 | 75 | 7 | 2 | 0 | 0 | 1.9 | 30 | 80/0/0/0 |
| 442 | `WARGA` | Galleon | 大型战舰 | 155 | 9 | 6 | 0 | 7 | 3 | 27 | 0/90/30/0 |
| 448 | `SCOUT` | Scout Cavalry | 斥候骑兵 | 45 | 3 | 2 | 0 | 0 | 2 | 30 | 80/0/0/0 |
| 473 | `HTHSW` | Two-Handed Swordsman | 双手剑士 | 65 | 12 | 1 | 1 | 0 | 2 | 21 | 50/0/20/0 |
| 474 | `HCVAR` | Heavy Cavalry Archer | 重装 骑射手 | 60 | 7 | 0 | 1 | 4 | 2 | 30 | 0/40/60/0 |
| 492 | `ACOAR` | Arbalester | 劲弩手 | 40 | 6 | 0 | 0 | 5 | 2 | 27 | 0/25/45/0 |
| 527 | `RMSHP` | Demolition Ship | 爆破船 | 50 | 95 | 0 | 1 | 0 | 0 | 31 | 0/45/80/0 |
| 528 | `CRMSH` | Heavy Demo Ship | 重型 爆破船 | 70 | 120 | 0 | 2 | 0 | 0 | 31 | 0/45/80/0 |
| 529 | `FRGAL` | Fire Ship | 喷火船 | 120 | 3 | 4 | 2 | 2.5 | 0.25 | 27 | 0/75/45/0 |
| 530 | `ULGBW` | Elite Longbowman | 精锐 长弓兵 | 40 | 7 | 1 | 0 | 6 | 2 | 18 | 0/35/40/0 |
| 531 | `UTAXE` | Elite Throwing Axeman | 精锐 掷斧兵 | 70 | 8 | 0 | 1 | 6 | 2 | 13 | 55/0/25/0 |
| 532 | `HFGAL` | Fast Fire Ship | 快速 喷火船 | 140 | 4 | 7 | 3 | 2.5 | 0.25 | 27 | 0/75/45/0 |
| 533 | `ULNGB` | Elite Longship | 精锐 维京长船 | 130 | 7 | 6 | 1 | 7 | 3 | 25 | 0/100/50/0 |
| 534 | `UWBRS` | Elite Woad Raider | 精锐 靛蓝突袭者 | 85 | 15 | 1 | 0 | 0 | 2 | 10 | 70/0/25/0 |
| 539 | `SGALY` | Galley | 箭船 | 110 | 6 | 3 | 0 | 5 | 3 | 45 | 0/90/30/0 |
| 542 | `HWBAL` | Heavy Scorpion | 重型 弩炮 | 60 | 14 | 8 | 1 | 7 | 3.6 | 30 | 0/75/75/0 |
| 545 | `XPORT` | Transport Ship | 运输船 | 70 | 0 | 2 | 0 | 0 | 0 | 46 | 0/125/0/0 |
| 546 | `LTCAV` | Light Cavalry | 轻型骑兵 | 60 | 7 | 2 | 0 | 0 | 2 | 30 | 80/0/0/0 |
| 548 | `SGRAM` | Siege Ram | 重型 冲车 | 270 | 4 | 195 | -1 | 0 | 5 | 36 | 0/160/75/0 |
| 550 | `ONAGR` | Onager | 中型投石车 | 60 | 55 | 8 | 0 | 8 | 6 | 46 | 0/160/135/0 |
| 553 | `UCATA` | Elite Cataphract | 精锐 甲胄骑兵 | 150 | 12 | 1 | 2 | 0 | 1.7 | 20 | 70/0/75/0 |
| 554 | `UTKNI` | Elite Teutonic Knight | 精锐 条顿骑士 | 110 | 17 | 2 | 8 | 0 | 2 | 12 | 85/0/30/0 |
| 555 | `UGBRS` | Elite Huskarl | 精锐 近卫军 | 70 | 12 | 8 | 0 | 0 | 2 | 13 | 75/0/35/0 |
| 556 | `UDERV` | Elite Mameluke | 精锐 马穆鲁克 | 80 | 10 | 0 | 1 | 3 | 2 | 23 | 55/0/85/0 |
| 557 | `UJANI` | Elite Janissary | 精锐 苏丹亲兵 | 40 | 22 | 0 | 2 | 8 | 3.45 | 21 | 60/0/55/0 |
| 558 | `UMPCAV` | Elite War Elephant | 精锐 战象 | 600 | 20 | 3 | 1 | 0 | 2 | 25 | 170/0/85/0 |
| 559 | `UCHUK` | Elite Chu Ko Nu | 精锐 诸葛弩 | 50 | 10 | 0 | 0 | 4 | 3 | 13 | 0/40/35/0 |
| 560 | `USMUR` | Elite Samurai | 精锐 日本武士 | 80 | 12 | 1 | 1 | 0 | 1.9 | 9 | 45/0/30/0 |
| 561 | `UMOSU` | Elite Mangudai | 精锐 蒙古突骑 | 60 | 8 | 0 | 1 | 4 | 2.1 | 26 | 0/55/65/0 |
| 567 | `HEROI` | Champion | 冠军剑士 | 70 | 14 | 1 | 1 | 0 | 2 | 21 | 50/0/20/0 |
| 569 | `HEROC` | Paladin | 游侠 | 160 | 14 | 3 | 2 | 0 | 1.9 | 30 | 60/0/75/0 |
| 588 | `SNAGR` | Siege Onager | 重型 投石车 | 70 | 75 | 8 | 0 | 8 | 6 | 46 | 0/160/135/0 |
| 691 | `CNGAU` | Elite Cannon Galleon | 精锐炮舰 | 150 | 60 | 6 | 0 | 15 | 10 | 46 | 0/200/150/0 |
| 692 | `VBRSK` | Berserk | 狂战士 | 54 | 12 | 1 | 1 | 0 | 2 | 14 | 65/0/20/0 |
| 694 | `UVBRK` | Elite Berserk | 精锐 狂战士 | 62 | 14 | 1 | 2 | 0 | 2 | 12 | 65/0/20/0 |
| 725 | `JAGUAR` | Jaguar Warrior | 豹勇士 | 65 | 15 | 2 | 1 | 0 | 2 | 12 | 60/0/30/0 |
| 726 | `JAGUARX` | Elite Jaguar Warrior | 精锐 豹勇士 | 75 | 19 | 2 | 2 | 0 | 2 | 12 | 60/0/30/0 |
| 751 | `EAGLE` | Eagle Scout | 鹰斥候 | 50 | 4 | 2 | 0 | 0 | 2 | 46 | 20/0/50/0 |
| 752 | `EAGLEX` | Elite Eagle Warrior | 精锐 鹰勇士 | 60 | 9 | 4 | 0 | 0 | 2 | 20 | 20/0/50/0 |
| 753 | `EAGLEH` | Eagle Warrior | 鹰勇士 | 55 | 7 | 3 | 0 | 0 | 2 | 35 | 20/0/50/0 |
| 755 | `TARKAN` | Tarkan | 答刺罕骑兵 | 100 | 8 | 3 | 1 | 0 | 1.9 | 14 | 60/0/60/0 |
| 757 | `UTARK` | Elite Tarkan | 精锐 答刺罕骑兵 | 150 | 11 | 4 | 1 | 0 | 1.9 | 14 | 60/0/60/0 |
| 759 | `BHUSK` | Huskarl | 近卫军 | 60 | 10 | 6 | 0 | 0 | 2 | 13 | 75/0/35/0 |
| 761 | `BHUSKX` | Elite Huskarl | 精锐 近卫军 | 70 | 12 | 8 | 0 | 0 | 2 | 13 | 75/0/35/0 |
| 763 | `PLUME` | Plumed Archer | 羽箭手 | 50 | 5 | 1 | 0 | 4 | 1.9 | 16 | 0/55/55/0 |
| 765 | `UPLUM` | Elite Plumed Archer | 精锐 羽箭手 | 65 | 5 | 2 | 0 | 5 | 1.9 | 16 | 0/55/55/0 |
| 771 | `CONQI` | Conquistador | 西班牙征服者 | 55 | 16 | 1 | 2 | 6 | 2.9 | 26 | 75/0/60/0 |
| 773 | `UCONQ` | Elite Conquistador | 精锐 西班牙征服者 | 70 | 19 | 2 | 2 | 6 | 2.9 | 24 | 75/0/60/0 |
| 775 | `MONKY` | Missionary | 传教士 | 30 | 0 | 0 | 0 | 7 | 1.6 | 51 | 30/0/100/0 |
| 827 | `WAGON` | War Wagon | 高丽战车 | 150 | 9 | 2 | 0 | 4 | 2.5 | 21 | 0/200/60/0 |
| 829 | `UWAGO` | Elite War Wagon | 精锐 高丽战车 | 200 | 9 | 4 | 0 | 5 | 2.5 | 21 | 0/200/60/0 |
| 831 | `TURTL` | Turtle Ship | 龟甲船 | 260 | 9 | 7 | 2 | 6 | 2 | 50 | 0/190/130/0 |
| 832 | `UTURT` | Elite Turtle Ship | 精锐 龟甲船 | 350 | 13 | 12 | 3 | 7 | 2 | 50 | 0/190/130/0 |
| 866 | `GENOE` | Genoese Crossbowman | 热那亚 弩手 | 45 | 6 | 0 | 1 | 4 | 2 | 14 | 0/45/40/0 |
| 868 | `GENOE_E` | Elite Genoese Crossbowman | 精锐 热那亚弩手 | 50 | 6 | 0 | 1 | 4 | 2 | 14 | 0/45/40/0 |
| 869 | `UMAGYX` | Magyar Huszar | 马扎尔 骠骑 | 80 | 10 | 2 | 0 | 0 | 1.8 | 18 | 35/0/45/0 |
| 871 | `UMAGYX` | Elite Magyar Huszar | 精锐 马扎尔骠骑 | 90 | 11 | 2 | 0 | 0 | 1.8 | 12 | 35/0/45/0 |
| 873 | `ELEAR` | Elephant Archer | 骑象射手 | 220 | 6 | 2 | 0 | 4 | 2 | 32 | 70/0/80/0 |
| 875 | `UELEA` | Elite Elephant Archer | 精锐 骑象射手 | 270 | 7 | 2 | 0 | 4 | 2 | 32 | 70/0/80/0 |
| 876 | `BOYAR` | Boyar | 贵族铁骑 | 100 | 12 | 2 | 4 | 0 | 1.9 | 15 | 60/0/70/0 |
| 878 | `EBOYA` | Elite Boyar | 精锐 贵族铁骑 | 130 | 14 | 3 | 8 | 0 | 1.9 | 15 | 60/0/70/0 |
| 879 | `KAMAY` | Kamayuk | 印加枪兵长 | 70 | 7 | 0 | 1 | 1 | 2 | 10 | 70/0/30/0 |
| 881 | `EKAMA` | Elite Kamayuk | 精锐 印加枪兵长 | 80 | 8 | 1 | 1 | 1 | 2 | 10 | 70/0/30/0 |
| 882 | `CONDO` | Condottiero | 意大利佣兵 | 80 | 10 | 0 | 1 | 0 | 1.9 | 18 | 50/0/35/0 |
| 886 | `TARKAN` | Tarkan | 答刺罕骑兵 | 100 | 8 | 3 | 1 | 0 | 1.9 | 14 | 60/0/60/0 |
| 887 | `UTARK` | Elite Tarkan | 精锐 答刺罕骑兵 | 150 | 11 | 4 | 1 | 0 | 1.9 | 14 | 60/0/60/0 |
| 1001 | `ORGAN` | Organ Gun | 风琴炮 | 50 | 6 | 4 | 2 | 7 | 3.45 | 28 | 0/80/70/0 |
| 1003 | `EORGAN` | Elite Organ Gun | 精锐 风琴炮 | 70 | 8 | 6 | 2 | 7 | 3.45 | 21 | 0/80/70/0 |
| 1004 | `CARAV` | Caravel | 卡拉维尔战舰 | 130 | 4 | 5 | 0 | 6 | 3 | 25 | 0/90/43/0 |
| 1006 | `ECARAV` | Elite Caravel | 精锐 卡拉维尔战舰 | 150 | 7 | 6 | 0 | 7 | 3 | 25 | 0/90/43/0 |
| 1007 | `CAMAR` | Camel Archer | 骆驼射手 | 55 | 7 | 1 | 0 | 4 | 2 | 25 | 0/50/60/0 |
| 1009 | `ECAMAR` | Elite Camel Archer | 精锐 骆驼射手 | 60 | 8 | 1 | 1 | 4 | 2 | 25 | 0/50/60/0 |
| 1010 | `GENITO` | Genitour | 标枪骑兵 | 50 | 3 | 4 | 0 | 4 | 3 | 25 | 40/35/0/0 |
| 1012 | `EGENITO` | Elite Genitour | 精锐 标枪骑兵 | 55 | 4 | 4 | 0 | 4 | 3 | 23 | 40/35/0/0 |
| 1013 | `GBETO` | Gbeto | 飞刀女兵 | 40 | 10 | 0 | 0 | 5 | 2 | 17 | 50/0/40/0 |
| 1015 | `EGBETO` | Elite Gbeto | 精锐 飞刀女兵 | 50 | 13 | 0 | 0 | 6 | 2 | 17 | 50/0/40/0 |
| 1016 | `SHOTEL` | Shotel Warrior | 弯刀勇士 | 45 | 16 | 0 | 0 | 0 | 2 | 8 | 50/0/30/0 |
| 1018 | `ESHOTEL` | Elite Shotel Warrior | 精锐 弯刀勇士 | 50 | 18 | 1 | 0 | 0 | 2 | 4 | 50/0/30/0 |
| 1103 | `SFRGAL` | Fire Galley | 火艨艟 | 110 | 2 | 4 | 1 | 2.5 | 0.25 | 49 | 0/75/45/0 |
| 1104 | `SDGAL` | Demolition Raft | 爆破筏 | 40 | 75 | 0 | 0 | 0 | 0 | 45 | 0/45/80/0 |
| 1105 | `SIEGTWR` | Siege Tower | 攻城塔 | 175 | 0 | 100 | -2 | 0 | 0 | 36 | 0/100/120/0 |
| 1120 | `ELEBALI` | Ballista Elephant | 重弩 战象 | 250 | 9 | 3 | 0 | 5 | 2.5 | 25 | 100/0/80/0 |
| 1122 | `EELEBALI` | Elite Ballista Elephant | 精锐重弩 战象 | 280 | 10 | 3 | 0 | 5 | 2.5 | 25 | 100/0/80/0 |
| 1123 | `KARAM` | Karambit Warrior | 爪刀 勇士 | 30 | 7 | 1 | 0 | 0 | 2 | 6 | 25/0/15/0 |
| 1125 | `EKARAM` | Elite Karambit Warrior | 精锐爪刀 勇士 | 40 | 8 | 1 | 1 | 0 | 2 | 6 | 25/0/15/0 |
| 1126 | `ARAMBAI` | Arambai | 飞镖骑兵 | 60 | 12 | 1 | 0 | 5 | 2 | 18 | 0/75/60/0 |
| 1128 | `EARAMBAI` | Elite Arambai | 精锐 飞镖骑兵 | 65 | 14 | 2 | 0 | 5 | 2 | 18 | 0/75/60/0 |
| 1129 | `RATAN` | Rattan Archer | 藤弓兵 | 35 | 6 | 4 | 0 | 4 | 2 | 16 | 0/50/45/0 |
| 1131 | `ERATAN` | Elite Rattan Archer | 精锐 藤弓兵 | 40 | 7 | 6 | 0 | 5 | 2 | 16 | 0/50/45/0 |
| 1132 | `BATELE` | Battle Elephant | 象兵 | 250 | 12 | 2 | 1 | 0 | 2 | 24 | 100/0/70/0 |
| 1134 | `EBATELE` | Elite Battle Elephant | 精锐 象兵 | 300 | 14 | 3 | 1 | 0 | 2 | 24 | 100/0/70/0 |
| 1155 | `IHXBOW` | Imperial Skirmisher | 帝王 掷矛手 | 35 | 4 | 5 | 0 | 5 | 3 | 22 | 25/35/0/0 |
| 1225 | `KONNIK` | Konnik | 保加利亚骑兵 | 100 | 12 | 2 | 2 | 0 | 2.4 | 16 | 60/0/70/0 |
| 1227 | `EKONNIK` | Elite Konnik | 精锐 保加利亚骑兵 | 120 | 14 | 2 | 2 | 0 | 2.4 | 16 | 60/0/70/0 |
| 1228 | `KESHIK` | Keshik | 怯薛骑兵 | 120 | 9 | 2 | 1 | 0 | 1.9 | 17 | 60/0/40/0 |
| 1230 | `EKESHIK` | Elite Keshik | 精锐 怯薛骑兵 | 145 | 11 | 3 | 1 | 0 | 1.9 | 15 | 60/0/40/0 |
| 1231 | `KIPCHAK` | Kipchak | 钦察 | 40 | 4 | 0 | 0 | 4 | 2.2 | 20 | 0/60/35/0 |
| 1233 | `EKIPCHAK` | Elite Kipchak | 精锐 钦察 | 45 | 5 | 0 | 0 | 4 | 2.2 | 20 | 0/60/35/0 |
| 1234 | `LEITIS` | Leitis | 烈堤司 | 100 | 13 | 1 | 1 | 0 | 1.9 | 20 | 70/0/50/0 |
| 1236 | `ELEITIS` | Elite Leitis | 精锐 烈堤司 | 130 | 16 | 1 | 2 | 0 | 1.9 | 18 | 70/0/50/0 |
| 1252 | `KONNIK_INF` | Konnik (Dismounted) | 保加利亚骑兵 (下马) | 45 | 12 | 2 | 2 | 0 | 2.4 | 16 | 0/0/0/0 |
| 1253 | `EKONNIK_INF` | Elite Konnik (Dismounted) | 精锐保加利亚骑兵 (下马) | 50 | 13 | 2 | 2 | 0 | 2.4 | 16 | 0/0/0/0 |
| 1254 | `KONNIK` | Konnik | 保加利亚骑兵 | 100 | 12 | 2 | 2 | 0 | 2.4 | 16 | 60/0/70/0 |
| 1255 | `EKONNIK` | Elite Konnik | 精锐 保加利亚骑兵 | 120 | 14 | 2 | 2 | 0 | 2.4 | 16 | 60/0/70/0 |
| 1258 | `BTRAM` | Battering Ram | 攻城锤 | 175 | 2 | 180 | -3 | 0 | 5 | 36 | 0/160/75/0 |
| 1260 | `MKIPCHAK` | Elite Kipchak | 精锐 钦察 | 45 | 5 | 0 | 0 | 4 | 2.2 | 12 | 0/0/0/0 |
| 1263 | `FCAMEL` | Flaming Camel | 火焰 骆驼 | 55 | 20 | 0 | 0 | 0 | 0 | 30 | 75/0/30/0 |
| 1302 | `DRAGS` | Dragon Ship | 龙舟 | 135 | 5 | 7 | 3 | 3 | 0.25 | 27 | 0/75/45/0 |
| 1370 | `SLANCER` | Steppe Lancer | 草原枪兵 | 60 | 9 | 1 | 0 | 1 | 2 | 24 | 70/0/40/0 |
| 1372 | `ESLANCER` | Elite Steppe Lancer | 精锐 草原枪兵 | 80 | 11 | 2 | 0 | 1 | 2 | 20 | 70/0/40/0 |
| 1570 | `AZTRAIDER` | Xolotl Warrior | 索洛托勇士 | 100 | 10 | 2 | 2 | 0 | 1.8 | 30 | 60/0/75/0 |
| 1655 | `COUSTILLIER` | Coustillier | 马上轻装兵 | 115 | 8 | 2 | 2 | 0 | 1.9 | 15 | 55/0/55/0 |
| 1657 | `ECOUSTILLIER` | Elite Coustillier | 精锐 马上轻装兵 | 145 | 11 | 2 | 2 | 0 | 1.9 | 14 | 55/0/55/0 |
| 1658 | `SERJEANT` | Serjeant | 萨金特卫兵 | 50 | 5 | 1 | 2 | 0 | 2 | 12 | 55/0/25/0 |
| 1659 | `ESERJEANT` | Elite Serjeant | 精锐 萨金特卫兵 | 85 | 11 | 3 | 6 | 0 | 2 | 12 | 55/0/25/0 |
| 1660 | `DSERJEANT` | Serjeant | 萨金特卫兵 | 50 | 5 | 1 | 2 | 0 | 2 | 16 | 55/0/25/0 |
| 1661 | `EDSERJEANT` | Elite Serjeant | 精锐 萨金特卫兵 | 85 | 11 | 3 | 6 | 0 | 2 | 12 | 55/0/25/0 |
| 1699 | `FLEMISHPIKEMAN2` | Flemish Militia | 弗拉芒 民兵 | 40 | 5 | 1 | 1 | 0 | 2 | 16 | 35/0/25/0 |
| 1701 | `OBUCH` | Obuch | 奥布奇战锤兵 | 80 | 8 | 2 | 2 | 0 | 2 | 12 | 55/0/20/0 |
| 1703 | `EOBUCH` | Elite Obuch | 精锐奥布奇战锤兵 | 95 | 10 | 2 | 2 | 0 | 2 | 12 | 55/0/20/0 |
| 1704 | `HUSSITEWAGON` | Hussite Wagon | 胡斯派战车 | 160 | 10 | 7 | 0 | 6 | 3.45 | 30 | 0/110/80/0 |
| 1706 | `EHUSSITEWAGON` | Elite Hussite Wagon | 精锐 胡斯派战车 | 230 | 13 | 10 | 1 | 6 | 3.45 | 26 | 0/110/80/0 |
| 1707 | `WINGEDHUSSAR` | Winged Hussar | 波兰 翼骑兵 | 80 | 9 | 2 | 1 | 0 | 1.9 | 30 | 80/0/0/0 |
| 1709 | `HOUFNICE` | Houfnice | 榴弹炮 | 90 | 50 | 6 | 2 | 12 | 6.5 | 56 | 0/225/225/0 |
| 1735 | `URUMI` | Urumi Swordsman | 乌鲁米 剑士 | 55 | 9 | 0 | 1 | 0 | 2 | 9 | 65/0/20/0 |
| 1737 | `EURUMI` | Elite Urumi Swordsman | 精锐乌鲁米 剑士 | 65 | 11 | 0 | 1 | 0 | 2 | 9 | 65/0/20/0 |
| 1738 | `RATHA` | Ratha (Melee) | 战车 (近战) | 100 | 10 | 1 | 3 | 0 | 2 | 24 | 0/60/60/0 |
| 1740 | `ERATHA` | Elite Ratha (Melee) | 精锐战车 (近战) | 115 | 12 | 3 | 3 | 0 | 2 | 18 | 0/60/60/0 |
| 1741 | `CHAKRAM` | Chakram Thrower | 飞轮刃 投掷手 | 40 | 3 | 0 | 1 | 5 | 2 | 15 | 65/0/30/0 |
| 1743 | `ECHAKRAM` | Elite Chakram Thrower | 精锐飞轮刃 投掷手 | 50 | 4 | 0 | 1 | 6 | 2 | 15 | 65/0/30/0 |
| 1744 | `ARELE` | Armored Elephant | 装甲 战象 | 180 | 4 | 140 | -2 | 0 | 3 | 36 | 120/0/95/0 |
| 1746 | `EARELE` | Siege Elephant | 攻城 战象 | 220 | 4 | 150 | -2 | 0 | 3 | 36 | 120/0/95/0 |
| 1747 | `GHULAM` | Ghulam | 古拉姆 | 60 | 9 | 3 | 0 | 0 | 2 | 12 | 30/0/45/0 |
| 1749 | `EGHULAM` | Elite Ghulam | 精锐古拉姆 | 70 | 11 | 6 | 0 | 0 | 2 | 12 | 30/0/45/0 |
| 1750 | `THIRISADAI` | Thirisadai | 楼船 | 250 | 10 | 11 | 2 | 7 | 3.45 | 40 | 0/180/60/0 |
| 1751 | `SHRIVAMSHA` | Shrivamsha Rider | 施里瓦姆沙 骑手 | 55 | 8 | 1 | 0 | 0 | 2 | 20 | 70/0/30/0 |
| 1753 | `ESHRIVAMSHA` | E. Shrivamsha Rider | 精锐施里瓦姆沙 骑手 | 70 | 11 | 1 | 0 | 0 | 1.9 | 20 | 70/0/30/0 |
| 1755 | `CAMELSC` | Camel Scout | 骆驼斥候 | 70 | 2 | 0 | 0 | 0 | 2 | 22 | 55/0/60/0 |
| 1759 | `RATHA2` | Ratha (Ranged) | 战车 (远程) | 100 | 5 | 1 | 3 | 4 | 2 | 24 | 0/60/60/0 |
| 1761 | `ERATHA2` | Elite Ratha (Ranged) | 精锐战车 (远程) | 115 | 6 | 3 | 3 | 4 | 2 | 18 | 0/60/60/0 |
| 1786 | `DPKEMN` | Spearman | 长矛兵 | 45 | 3 | 0 | 0 | 0 | 3 | 22 | 35/25/0/0 |
| 1787 | `DISPKM` | Pikeman | 长枪兵 | 55 | 4 | 0 | 0 | 0 | 3 | 22 | 35/25/0/0 |
| 1788 | `DHLBDM` | Halberdier | 长戟兵 | 60 | 6 | 0 | 0 | 0 | 3 | 22 | 35/25/0/0 |
| 1790 | `CENTURION` | Centurion | 百夫长 | 110 | 13 | 3 | 2 | 0 | 1.9 | 24 | 75/0/85/0 |
| 1792 | `ECENTURION` | Elite Centurion | 精锐 百夫长 | 155 | 15 | 3 | 3 | 0 | 1.9 | 24 | 75/0/85/0 |
| 1793 | `LEGIONARY` | Legionary | 罗马军 | 75 | 12 | 2 | 2 | 0 | 2 | 21 | 50/0/20/0 |
| 1795 | `DROMON` | Dromon | 德罗蒙战舰 | 125 | 8 | 6 | 1 | 12 | 8 | 65 | 0/175/150/0 |
| 1800 | `COMPBOW` | Composite Bowman | 复合 弓箭手 | 40 | 4 | 0 | 1 | 4 | 2 | 12 | 0/35/45/0 |
| 1802 | `ECOMPBOW` | E. Composite Bowman | 精锐复合 弓箭手 | 50 | 4 | 0 | 2 | 4 | 2 | 10 | 0/35/45/0 |
| 1803 | `MONASPA` | Monaspa | 莫纳斯帕 | 70 | 12 | 2 | 3 | 0 | 1.8 | 14 | 60/0/45/0 |
| 1805 | `EMONASPA` | Elite Monaspa | 精锐 莫纳斯帕 | 80 | 14 | 2 | 5 | 0 | 1.8 | 14 | 60/0/45/0 |
| 1811 | `WARRIORPRIEST` | Warrior Priest | 牧师 战士 | 80 | 11 | 1 | 1 | 0 | 2 | 30 | 40/0/50/0 |
| 1813 | `SAVAR` | Savar | 萨瓦尔 | 145 | 14 | 4 | 3 | 0 | 1.8 | 30 | 60/0/75/0 |
| 1901 | `FLNCER` | Fire Lancer | 火矛兵 | 65 | 9 | 0 | 1 | 0 | 2 | 35 | 0/45/45/0 |
| 1903 | `EFLNCER` | Elite Fire Lancer | 精锐 火矛兵 | 85 | 10 | 1 | 2 | 0 | 2 | 25 | 0/45/45/0 |
| 1904 | `RCKTCRT` | Rocket Cart | 火箭 推车 | 45 | 5 | 6 | 0 | 7 | 5.5 | 40 | 0/135/155/0 |
| 1907 | `HRCKTCRT` | Heavy Rocket Cart | 重型 火箭推车 | 65 | 5 | 8 | 0 | 8 | 5.35 | 40 | 0/135/155/0 |
| 1908 | `IRONPAG` | Iron Pagoda | 铁浮屠 | 115 | 12 | 3 | 1 | 0 | 2.15 | 14 | 80/0/55/0 |
| 1910 | `EIRONPAG` | Elite Iron Pagoda | 精锐 铁浮屠 | 140 | 13 | 3 | 2 | 0 | 2.15 | 14 | 80/0/55/0 |
| 1911 | `GRNADR` | Grenadier | 掷弹兵 | 40 | 12 | 1 | 1 | 6 | 3.45 | 21 | 55/0/50/0 |
| 1920 | `LIAODAO` | Liao Dao | 辽刀兵 | 75 | 9 | 1 | 3 | 0 | 2.4 | 12 | 40/0/40/0 |
| 1922 | `ELIAODAO` | Elite Liao Dao | 精锐 辽刀兵 | 85 | 13 | 1 | 3 | 0 | 2.4 | 12 | 40/0/40/0 |
| 1923 | `SIEGECAMEL` | Mounted Trebuchet | 骆驼 投石机 | 75 | 30 | 4 | 2 | 10 | 6.5 | 46 | 175/0/175/0 |
| 1942 | `TRTREB` | Traction Trebuchet | 牵引 抛石机 | 115 | 50 | 8 | 1 | 14 | 11 | 70 | 0/175/210/0 |
| 1944 | `HKUCAV` | Hei Guang Cavalry | 黑光铠 骑兵 | 60 | 11 | 3 | 4 | 0 | 1.8 | 28 | 65/0/65/0 |
| 1946 | `HHKUCAV` | Heavy Hei Guang Cavalry | 重装黑光铠 骑兵 | 90 | 12 | 3 | 4 | 0 | 1.8 | 28 | 65/0/65/0 |
| 1948 | `LOUCHUAN` | Lou Chuan | 楼船 | 175 | 25 | 9 | 0 | 10 | 5.5 | 60 | 0/250/225/0 |
| 1949 | `TIGERCAV` | Tiger Cavalry | 虎豹骑 | 110 | 11 | 4 | 0 | 0 | 1.9 | 18 | 60/0/80/0 |
| 1951 | `ETIGERCAV` | Elite Tiger Cavalry | 精锐 虎豹骑 | 125 | 13 | 5 | 0 | 0 | 1.9 | 18 | 60/0/80/0 |
| 1952 | `XIANBEI` | Xianbei Raider | 鲜卑 掠骑兵 | 30 | 5 | 0 | 0 | 4 | 1.8 | 29 | 0/65/35/0 |
| 1954 | `CAOCAO` | Cao Cao | 曹操 | 475 | 14 | 3 | 3 | 0 | 2 | 60 | 500/0/500/0 |
| 1959 | `WHTFTHRG` | White Feather Guard | 白毦兵 | 95 | 7 | 2 | 0 | 0 | 2 | 11 | 60/0/15/0 |
| 1961 | `EWHTFTHRG` | Elite White Feather Guard | 精锐 白毦兵 | 100 | 8 | 3 | 0 | 0 | 2 | 11 | 60/0/15/0 |
| 1962 | `WARCHAR` | War Chariot (Focus Fire) | 战车 (集中射击) | 65 | 8 | 5 | 0 | 6 | 6.5 | 32 | 75/0/90/0 |
| 1966 | `LIUBEI` | Liu Bei | 刘备 | 425 | 15 | 3 | 3 | 0 | 2 | 60 | 500/0/500/0 |
| 1968 | `FIREARCHER` | Fire Archer | 火焰 弓箭手 | 35 | 5 | 0 | 0 | 5 | 3.5 | 17 | 0/45/45/0 |
| 1970 | `EFIREARCHER` | Elite Fire Archer | 精锐火焰 弓箭手 | 40 | 6 | 0 | 0 | 6 | 3.5 | 17 | 0/45/45/0 |
| 1974 | `JIANSWDS` | Jian Swordsman | 剑 士 | 70 | 8 | 5 | 0 | 0 | 2 | 35 | 45/0/50/0 |
| 1978 | `SUNJIAN` | Sun Jian | 孙坚 | 400 | 15 | 4 | 4 | 0 | 2 | 60 | 500/0/500/0 |
| 1980 | `WARCHAR` | War Chariot (Barrage) | 战车 (掩护) | 65 | 8 | 5 | 0 | 6 | 6.5 | 28 | 75/0/90/0 |
| 2550 | `CHAMPIR` | Champi Scout | 蔷琵 斥候 | 35 | 3 | 2 | 0 | 0 | 2 | 42 | 50/0/25/0 |
| 2552 | `CHAMPIW` | Champi Warrior | 蔷琵 战士 | 55 | 9 | 3 | 0 | 0 | 2 | 26 | 50/0/25/0 |
| 2554 | `ECHAMPIW` | Elite Champi Warrior | 精锐蔷琵 战士 | 65 | 11 | 4 | 0 | 0 | 2 | 21 | 50/0/25/0 |
| 2562 | `GUECHA` | Guecha Warrior | 格查 战士 | 55 | 6 | 3 | 0 | 3 | 3 | 17 | 0/50/60/0 |
| 2564 | `EGUECHA` | Elite Guecha Warrior | 精锐格查 战士 | 60 | 8 | 5 | 0 | 4 | 3 | 17 | 0/50/60/0 |
| 2566 | `KONA` | Kona | 科那 | 125 | 9 | 3 | 0 | 0 | 2 | 14 | 65/0/40/0 |
| 2568 | `EKONA` | Elite Kona | 精锐 科那 | 145 | 11 | 5 | 0 | 0 | 2 | 14 | 65/0/40/0 |
| 2569 | `BOLASR` | Bolas Rider | 掷石绳 骑兵 | 55 | 5 | 1 | 0 | 4 | 2 | 34 | 0/50/55/0 |
| 2571 | `EBOLASR` | Elite Bolas Rider | 精锐掷石绳 骑兵 | 65 | 6 | 2 | 0 | 5 | 2 | 28 | 0/50/55/0 |
| 2579 | `BLCKWOOD` | Blackwood Archer | 黑檀木 步弓手 | 20 | 4 | 0 | 0 | 5 | 1.5 | 18 | 0/40/45/0 |
| 2581 | `EBLCKWOOD` | Elite Blackwood Archer | 精锐黑檀木 步弓手 | 25 | 4 | 0 | 0 | 5 | 1.5 | 14 | 0/40/45/0 |
| 2582 | `IBIRAP` | Ibirapema Warrior | 伊比拉贝玛 战士 | 80 | 8 | 1 | 2 | 0 | 2 | 24 | 30/0/60/0 |
| 2584 | `EIBIRAP` | Elite Ibirapema Warrior | 精锐伊比拉贝玛 战士 | 90 | 11 | 1 | 2 | 0 | 2 | 24 | 30/0/60/0 |
| 2586 | `Temple Guard` | Temple Guard | 神庙 护卫 | 100 | 11 | 1 | 1 | 0 | 2 | 28 | 70/0/45/0 |
| 2587 | `Elite Temple Guard` | Elite Temple Guard | 精锐神庙 护卫 | 115 | 14 | 2 | 2 | 0 | 2 | 24 | 70/0/45/0 |
| 2588 | `CHAMPIS` | Champi Runner | 蔷琵 步兵 | 40 | 5 | 2 | 0 | 0 | 2 | 34 | 50/0/25/0 |
| 2626 | `Hulk` | Hulk | 趸船 | 85 | 4 | 1 | 3 | 1 | 1.75 | 42 | 0/75/35/0 |
| 2627 | `War hulk` | War Hulk | 战争趸船 | 110 | 4 | 1 | 4 | 1 | 1.5 | 27 | 0/75/35/0 |
| 2628 | `Carrack` | Carrack | 大帆船 | 135 | 4 | 1 | 6 | 1 | 1.5 | 27 | 0/75/35/0 |
| 2633 | `CATAGA` | Catapult Galleon | 大型投石战舰 | 140 | 30 | 6 | 0 | 12 | 6 | 55 | 0/225/100/0 |
| 2700 | `Mounted Crossbowman` | Mounted Crossbowman | 骑马弩兵 | 45 | 7 | 0 | 2 | 4 | 2.5 | 40 | 0/40/65/0 |
| 2701 | `Heavy Mounted Crossbowman` | H. Mounted Crossbowman | 重装骑马 弩兵 | 55 | 8 | 0 | 2 | 4 | 2.5 | 30 | 0/40/65/0 |
| 2703 | `Varangian Guard` | Varangian Guard | 瓦兰吉卫队 | 70 | 13 | 1 | 2 | 0 | 2 | 30 | 65/0/45/0 |
| 2704 | `Elite Varangian Guard` | E. Varangian Guard | 精锐瓦兰吉 卫队 | 80 | 17 | 2 | 2 | 0 | 2 | 30 | 65/0/45/0 |
| 2705 | `Hearth Troop` | Hearth Troop | 扈从部队 | 75 | 9 | 4 | 1 | 0 | 2 | 16 | 0/80/35/0 |
| 2706 | `Elite Hearth Troop` | Elite Hearth Troop | 精锐 扈从部队 | 85 | 12 | 4 | 1 | 0 | 2 | 14 | 0/80/35/0 |
| 2708 | `Jarl` | Jarl | 首领 | 65 | 9 | 1 | 2 | 4 | 2 | 23 | 75/0/55/0 |
| 2709 | `Elite Jarl` | Elite Jarl | 精锐首领 | 75 | 10 | 1 | 2 | 5 | 2 | 23 | 75/0/55/0 |
| 2711 | `Jomsviking` | Jomsviking | 约姆斯维京 | 70 | 8 | 2 | 2 | 0 | 1.8 | 10 | 65/0/15/0 |
| 2712 | `Elite Jomsviking` | Elite Jomsviking | 精锐 约姆斯维京 | 75 | 9 | 2 | 2 | 0 | 1.8 | 10 | 65/0/15/0 |

> 上表造价列留空是因为格式对齐成本高；完整值在 `_techtree_units.csv`。


## 6 攻击/护甲 class 明细怎么用

`Attacks` / `Armours` 的 `Class` 编号与 .dat 的 attack/armour class 同一套（编号含义见 [07 卷](07-XS-ID表-属性资源任务与伤害计算.md)，HALFON 侧的 class 反推表见 [13 卷](13-HALFON-全单位科技数据.md) §3.2）。

以 `ARCHR`（ID 4）为例，`data.json` 原文：

```json
{"Attacks":[{"Amount":3,"Class":27},{"Amount":0,"Class":21},{"Amount":4,"Class":3},{"Amount":0,"Class":17},{"Amount":0,"Class":13}],"Armours":[{"Amount":0,"Class":4},{"Amount":0,"Class":15},{"Amount":0,"Class":3},{"Amount":0,"Class":31}]}
```

读法：

- `Armours: [{Class:4,Amount:0},{Class:15,...},{Class:3,...},{Class:31,...}]` —— 弓箭手属于 class 4（Archer 类护甲）、15（Tree? 实际是"可被某些加成命中"）、3（Building 类）、31（Unique unit）。数值 0 表示该 class 护甲为 0。
- `Attacks: [{Class:27,Amount:3},{Class:3,Amount:4}]` —— 对 class 27（Wall 城墙）加 3，对 class 3（Building）加 4。这就是"弓箭手拆墙慢、打建筑有加成"的数据来源。
- **伤害计算**：`max(1, 攻击 - 目标对应class护甲) + 各加成`，完整公式见 [07 卷](07-XS-ID表-属性资源任务与伤害计算.md)。


## 7 科技全量（201 条，含归属文明）

| ID | 内部名 | 英文名 | 中文名 | 成本(F/W/G/S) | 研究(s) | 可重复 | 拥有文明 |
|---|---|---|---|---|---|---|---|
| 3 | `British Yeoman` | Yeomen | 英皇侍卫 | 0/750/450/0 | 60 | True | Britons |
| 4 | `Mayan El Dorado` | Holcans | 霍尔坎 | 750/0/450/0 | 70 | True | Mayans |
| 5 | `Celtic Furor Celtica` | Furor Celtica | 凯尔特 狂暴 | 750/0/450/0 | 50 | True | Celts |
| 6 | `Mongol Siege Drill` | Drill | 操练 | 0/500/450/0 | 60 | True | Mongols |
| 7 | `Citadels` | Citadels | 堡垒 | 0/600/300/0 | 50 | True | Persians |
| 8 | `Town Watch` | Town Watch | 城镇 瞭望 | 75/0/0/0 | 25 | False | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 10 | `Turkish Artillery` | Artillery | 火炮术 | 600/0/650/0 | 40 | True | Turks |
| 11 | `Teuton Crenellations` | Crenellations | 开垛口 | 600/0/0/400 | 60 | True | Teutons |
| 12 | `Crop rotation` | Crop Rotation | 轮作 | 250/250/0/0 | 70 | True | Aztecs,Bengalis,Berbers,Bulgarians,Burgundians,Burmese,Byzan… |
| 13 | `Heavy plow` | Heavy Plow | 重犁 | 125/125/0/0 | 40 | True | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 14 | `Horse collar` | Horse Collar | 马轭 | 75/75/0/0 | 20 | True | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 15 | `Guilds` | Guilds | 行会 | 300/0/200/0 | 50 | False | Armenians,Bengalis,Berbers,Bohemians,Britons,Bulgarians,Burg… |
| 16 | `Gothic Anarchy` | Anarchy | 无政府 | 450/0/250/0 | 40 | False | Goths |
| 17 | `Banking` | Banking | 银行业 | 300/0/200/0 | 70 | False | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 19 | `Cartography` | Cartography | 绘图法 | 0/0/0/0 | 1 | True | （通用/无文明独占） |
| 21 | `Hun Atheism` | Atheism | 无神论 | 500/300/0/0 | 60 | True | Huns |
| 22 | `Loom` | Loom | 织布机 | 0/0/50/0 | 25 | True | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 23 | `Coinage` | Coinage | 铸币术 | 200/0/100/0 | 70 | False | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 24 | `Aztec Garland Wars` | Garland Wars | 荣冠 战争 | 450/0/750/0 | 60 | True | Aztecs |
| 28 | `Bimaristan` | Bimaristan | 穆斯林诊所 | 0/300/200/0 | 50 | True | Saracens |
| 34 | `War Galley` | Medium Warships | 中型战船 | 0/150/100/0 | 50 | True | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 35 | `Galleon` | Heavy Warships | 重型战船 | 0/400/315/0 | 65 | True | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 39 | `Husbandry` | Husbandry | 畜牧 | 150/0/0/0 | 40 | True | Armenians,Bengalis,Berbers,Bohemians,Britons,Bulgarians,Burg… |
| 45 | `Faith` | Faith | 信念 | 550/0/750/0 | 60 | True | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Burgundi… |
| 46 | `Devotion` | Devotion | 虔诚 | 100/0/200/0 | 40 | True | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 47 | `Chemistry` | Chemistry | 化学 | 300/0/200/0 | 100 | True | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 48 | `Caravan` | Caravan | 篷车 | 200/0/200/0 | 40 | True | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 49 | `Bogsveigar` | Bogsveigar | 博格斯维加尔 | 650/0/500/0 | 40 | True | Vikings |
| 50 | `Masonry` | Masonry | 石工术 | 150/175/0/0 | 50 | True | Armenians,Bengalis,Berbers,Bohemians,Britons,Bulgarians,Burg… |
| 51 | `Architecture` | Architecture | 建筑学 | 300/200/0/0 | 70 | True | Bengalis,Bohemians,Britons,Bulgarians,Burgundians,Burmese,Ch… |
| 52 | `Chinese Rocketry` | Rocketry | 火箭术 | 1100/0/900/0 | 60 | True | Chinese |
| 54 | `Stone cutting` | Treadmill Crane | 脚踏 起重机 | 0/200/0/50 | 20 | True | Armenians,Aztecs,Berbers,Britons,Burgundians,Burmese,Byzanti… |
| 55 | `Gold Mining` | Gold Mining | 金矿开采 | 100/75/0/0 | 30 | True | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 59 | `Japanese Kataparuto` | Kataparuto | 弹射器 | 0/550/300/0 | 60 | True | Japanese |
| 61 | `Byzantine Logistica` | Logistica | 后勤学 | 800/0/600/0 | 50 | True | Byzantines |
| 63 | `Keep` | Keep | 大型箭塔 | 500/350/0/0 | 75 | True | Bengalis,Bohemians,Britons,Bulgarians,Burgundians,Burmese,By… |
| 64 | `Bombard Tower` | Bombard Tower | 炮塔 | 800/400/0/0 | 60 | False | Armenians,Bohemians,Burgundians,Byzantines,Chinese,Dravidian… |
| 65 | `Gillnets` | Gillnets | 刺网 | 100/125/0/0 | 30 | True | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 67 | `Forging` | Forging | 锻造 | 150/0/0/0 | 50 | True | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 68 | `Iron casting` | Iron Casting | 铸铁 | 220/0/120/0 | 75 | True | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 74 | `Scale Mail Armor` | Scale Mail Armor | 步兵 鳞甲 | 100/0/0/0 | 40 | True | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 75 | `Blast Furnace` | Blast Furnace | 鼓风炉 | 275/0/225/0 | 100 | True | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 76 | `Chain Mail Armor` | Chain Mail Armor | 步兵 锁甲 | 200/0/100/0 | 55 | True | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 77 | `Plate Mail Armor` | Plate Mail Armor | 步兵 钢甲 | 300/0/150/0 | 70 | True | Armenians,Aztecs,Berbers,Bohemians,Britons,Bulgarians,Burgun… |
| 80 | `Plate Barding Armor` | Plate Barding Armor | 骑兵 钢甲 | 350/0/200/0 | 75 | True | Bengalis,Berbers,Britons,Bulgarians,Burgundians,Burmese,Byza… |
| 81 | `Scale Barding Armor` | Scale Barding Armor | 骑兵 鳞甲 | 150/0/0/0 | 45 | True | Armenians,Bengalis,Berbers,Bohemians,Britons,Bulgarians,Burg… |
| 82 | `Chain Barding Armor` | Chain Barding Armor | 骑兵 锁甲 | 250/0/150/0 | 60 | True | Armenians,Bengalis,Berbers,Bohemians,Britons,Bulgarians,Burg… |
| 90 | `Tracking` | Tracking | 跟踪术 | 0/0/0/0 | 0 | True | （通用/无文明独占） |
| 93 | `Ballistics` | Ballistics | 弹道学 | 0/300/175/0 | 60 | False | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 101 | `Middle Age` | Feudal Age | 封建时代 | 500/0/0/0 | 130 | False | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 102 | `Feudal Age` | Castle Age | 城堡时代 | 800/0/200/0 | 160 | False | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 103 | `Imperial Age` | Imperial Age | 帝王时代 | 1000/0/800/0 | 190 | False | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 140 | `Guard Tower` | Guard Tower | 警戒 箭塔 | 100/250/0/0 | 30 | True | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 182 | `Gold Shaft Mining` | Gold Shaft Mining | 钻井 采金法 | 175/75/0/0 | 75 | True | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 194 | `Fortified Wall` | Fortified Wall | 垛墙 | 200/100/0/0 | 50 | True | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Burgundi… |
| 199 | `Fletching` | Fletching | 箭羽 | 100/0/50/0 | 30 | True | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 200 | `Bodkin Arrow` | Bodkin Arrow | 锥子箭 | 200/0/100/0 | 35 | True | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 201 | `Bracer` | Bracer | 护腕 | 300/0/200/0 | 40 | True | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 202 | `Double Bit Axe` | Double-Bit Axe | 双刃斧 | 100/50/0/0 | 25 | True | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 203 | `Bow Saw` | Bow Saw | 弓锯 | 150/100/0/0 | 50 | True | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 211 | `Padded Archer Armor` | Padded Archer Armor | 射手 软甲 | 100/0/0/0 | 40 | True | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 212 | `Leather Archer Armor` | Leather Archer Armor | 射手 皮甲 | 150/0/150/0 | 55 | True | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 213 | `Wheel Barrow` | Wheelbarrow | 独轮推车 | 175/50/0/0 | 75 | True | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 215 | `Squires` | Squires | 护卫 | 100/0/0/0 | 40 | True | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 219 | `Ring Archer Armor` | Ring Archer Armor | 射手 锁甲 | 250/0/250/0 | 70 | True | Armenians,Bengalis,Berbers,Bohemians,Britons,Byzantines,Celt… |
| 221 | `Two Man Saw` | Two-Man Saw | 双人锯 | 300/200/0/0 | 100 | True | Bengalis,Bohemians,Britons,Burgundians,Burmese,Byzantines,Ch… |
| 230 | `Block Printing` | Block Printing | 雕版 印刷术 | 0/0/200/0 | 55 | True | Armenians,Aztecs,Bengalis,Bohemians,Britons,Burgundians,Burm… |
| 231 | `Sanctity` | Sanctity | 圣洁 | 0/0/175/0 | 60 | True | Armenians,Aztecs,Bengalis,Bohemians,Britons,Burgundians,Burm… |
| 233 | `Illumination` | Illumination | 启发 | 0/0/120/0 | 65 | True | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 249 | `Hand Cart` | Hand Cart | 手推车 | 300/200/0/0 | 55 | True | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 252 | `Fervor` | Fervor | 狂热 | 0/0/140/0 | 50 | True | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 278 | `Stone Mining` | Stone Mining | 石矿开采 | 100/75/0/0 | 30 | True | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 279 | `Stone Shaft Mining` | Stone Shaft Mining | 钻井 采石法 | 175/75/0/0 | 75 | True | Aztecs,Berbers,Bohemians,Bulgarians,Burgundians,Byzantines,C… |
| 280 | `Town Patrol` | Town Patrol | 城镇 巡逻 | 300/0/100/0 | 40 | False | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 315 | `Conscription` | Conscription | 征招 | 150/0/150/0 | 60 | True | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 316 | `Redemption` | Redemption | 救赎 | 0/0/475/0 | 50 | False | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Bulgarians,Burgu… |
| 319 | `Atonement` | Atonement | 赎罪 | 0/0/325/0 | 40 | False | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Burgundians,Burm… |
| 321 | `Sappers` | Sappers | 工兵 | 400/200/0/0 | 10 | True | Armenians,Aztecs,Bohemians,Britons,Bulgarians,Burgundians,Ce… |
| 322 | `Murder Holes` | Murder Holes | 近射孔 | 200/0/0/100 | 35 | False | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 373 | `Shipwright` | Shipwright | 造船匠 | 1000/0/300/0 | 60 | True | Aztecs,Bengalis,Berbers,Britons,Byzantines,Celts,Chinese,Dan… |
| 374 | `Careening` | Careening | 修船厂 | 100/0/200/0 | 50 | True | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 375 | `Dry Dock` | Dry Dock | 干船坞 | 200/0/400/0 | 60 | True | Armenians,Bengalis,Berbers,Britons,Burmese,Byzantines,Celts,… |
| 377 | `Siege Engineers` | Siege Engineers | 攻城 技师 | 500/600/0/0 | 45 | True | Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgarians,Burmese… |
| 379 | `Hoardings` | Hoardings | 围墙 | 400/400/0/0 | 75 | True | Armenians,Berbers,Britons,Burgundians,Byzantines,Celts,Cuman… |
| 380 | `Heated Shot` | Heated Shot | 加热 射击 | 350/0/100/0 | 30 | True | Armenians,Aztecs,Bengalis,Berbers,Britons,Bulgarians,Burmese… |
| 408 | `Spy Technology` | Spies/Treason | 间谍/叛徒 | 0/0/200/0 | 1 | False | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 435 | `Bloodlines` | Bloodlines | 血统 | 150/0/100/0 | 50 | True | Armenians,Bengalis,Berbers,Bulgarians,Burmese,Chinese,Cumans… |
| 436 | `Parthian Tactics` | Parthian Tactics | 帕提亚 战术 | 200/0/250/0 | 65 | True | Bulgarians,Burmese,Cumans,Georgians,Huns,Japanese,Khitans,Kh… |
| 437 | `Thumb Ring` | Thumb Ring | 扳指 | 300/250/0/0 | 45 | True | Berbers,Bulgarians,Byzantines,Chinese,Cumans,Danes,Dravidian… |
| 438 | `Theocracy` | Theocracy | 神权 | 0/0/200/0 | 75 | False | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 439 | `Heresy` | Heresy | 异教 | 0/0/1000/0 | 60 | False | Armenians,Aztecs,Berbers,Bohemians,Bulgarians,Byzantines,Cel… |
| 440 | `Spanish Supremacy` | Supremacy | 霸权 | 400/0/250/0 | 60 | True | Spanish |
| 441 | `Herbal Medicine` | Herbal Medicine | 草药 | 0/0/200/0 | 35 | True | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 445 | `Korean catapults` | Shinkichon | 神机箭 | 1100/0/800/0 | 60 | True | Koreans |
| 454 | `Counterweights` | Counter- weights | 配重块 | 650/0/500/0 | 50 | True | Saracens |
| 455 | `Detinets` | Detinets | 罗斯堡垒 | 0/400/200/0 | 40 | False | Slavs |
| 457 | `Gothic Perfusion` | Perfusion | 井喷 | 0/400/600/0 | 40 | True | Goths |
| 460 | `Aztec Sacrifice` | Atlatl | 掷矛器 | 400/0/350/0 | 40 | True | Aztecs |
| 461 | `Britons City Rights` | Warwolf | 战狼号 | 0/800/400/0 | 40 | True | Britons |
| 462 | `Chinese Great Wall` | Great Wall | 长城 | 0/400/0/200 | 40 | True | Chinese |
| 463 | `Viking Chieftains` | Chieftains | 酋长 | 600/0/450/0 | 40 | True | Vikings |
| 464 | `Byzantines Greek Fire` | Greek Fire | 希腊之火 | 250/0/300/0 | 40 | True | Byzantines |
| 482 | `Stronghold` | Stronghold | 堡垒 | 250/0/200/0 | 30 | True | Celts |
| 483 | `Huns UT` | Marauders | 掠夺者 | 0/300/200/0 | 40 | False | Huns |
| 484 | `Japanese UT` | Yasama | 射箭孔 | 300/300/0/0 | 40 | True | Japanese |
| 485 | `Mayans UT` | Hul'che Javelineers | 胡尔切掷矛兵 | 300/0/300/0 | 40 | True | Mayans |
| 486 | `Koreans UT` | Eupseong | 邑城 | 300/300/0/0 | 40 | True | Koreans |
| 487 | `Mongols UT` | Nomads | 游牧 | 0/300/150/0 | 40 | False | Mongols |
| 488 | `Persians UT` | Kamandaran | 波斯步弓手 | 400/0/300/0 | 40 | False | Persians |
| 489 | `Teutons UT` | Ironclad | 重装甲 | 0/400/350/0 | 60 | True | Teutons |
| 491 | `Sipahi` | Sipahi | 西帕希骑兵 | 350/0/150/0 | 60 | True | Turks |
| 492 | `Spanish UT` | Inquisition | 宗教法庭 | 100/0/300/0 | 40 | True | Spanish |
| 493 | `Franks UT` | Chivalry | 骑士精神 | 0/600/500/0 | 40 | True | Franks |
| 499 | `Silk Route` | Silk Road | 丝绸之路 | 250/0/250/0 | 60 | True | Italians |
| 506 | `Indians UT` | Grand Trunk Road | 大 干道 | 250/200/0/0 | 40 | True | Hindustanis |
| 507 | `Indians UT2` | Shatagni | 印度火铳 | 500/0/650/0 | 40 | True | Hindustanis |
| 513 | `Slavs UT` | Druzhina | 皇家卫队 | 900/0/500/0 | 40 | True | Slavs |
| 514 | `Magyars UT` | Corvinian Army | 科维尼安 军队 | 200/0/300/0 | 40 | False | Magyars |
| 515 | `Indians UT` | Recurve Bow | 反曲弓 | 0/600/400/0 | 40 | True | Magyars |
| 516 | `Incas UT` | Andean Sling | 安第斯弹弓 | 200/0/300/0 | 40 | False | Incas |
| 517 | `Indians UT` | Fabric Shields | 织物 盾 | 600/0/600/0 | 40 | True | Incas |
| 573 | `Portuguese UT` | Arquebus | 火绳枪 | 700/0/400/0 | 40 | True | Portuguese |
| 574 | `Ethiopian UT` | Royal Heirs | 龙脉 | 300/0/300/0 | 40 | False | Ethiopians |
| 575 | `Ethiopian UT` | Torsion Engines | 扭绞机 | 1000/0/600/0 | 40 | True | Ethiopians |
| 576 | `Malian UT` | Tigui | 蛮王 | 200/300/0/0 | 40 | True | Malians |
| 577 | `Malian UT` | Farimba | 死士 | 650/0/400/0 | 40 | True | Malians |
| 578 | `Berber UT` | Kasbah | 土堡 | 250/0/250/0 | 40 | True | Berbers |
| 579 | `Berber UT` | Maghrebi Camels | 马格里布骆驼 | 700/0/300/0 | 40 | True | Berbers |
| 602 | `Arson` | Arson | 纵火 | 75/0/25/0 | 25 | True | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 608 | `Arrowslits` | Arrowslits | 射箭槽 | 250/250/0/0 | 25 | True | Aztecs,Bengalis,Berbers,Bohemians,Britons,Burgundians,Byzant… |
| 622 | `Khmer UT` | Tusk Swords | 獠牙剑 | 0/300/450/0 | 40 | True | Khmer |
| 623 | `Khmer UT` | Double Crossbow | 双箭弩 | 700/0/400/0 | 40 | True | Khmer |
| 624 | `Malay UT` | Thalassocracy | 海上霸主 | 300/0/300/0 | 40 | False | Malay |
| 625 | `Malay UT` | Forced Levy | 强征兵役 | 850/0/500/0 | 40 | False | Malay |
| 626 | `Burmese UT` | Howdah | 象轿 | 400/300/0/0 | 40 | True | Burmese |
| 627 | `Burmese UT` | Manipur Cavalry | 曼尼普尔 马 | 300/0/300/0 | 40 | True | Burmese |
| 628 | `Vietnamese UT` | Chatras | 宝伞 | 250/0/250/0 | 40 | True | Vietnamese |
| 629 | `Vietnamese UT` | Paper Money | 纸币 | 550/200/0/0 | 60 | True | Vietnamese |
| 685 | `Khmer UT` | Stirrups | 马镫 | 400/0/200/0 | 35 | True | Bulgarians |
| 686 | `Khmer UT` | Bagains | 协议 | 900/0/450/0 | 40 | True | Bulgarians |
| 687 | `Malay UT` | Silk Armor | 丝护甲 | 0/400/300/0 | 40 | True | Tatars |
| 688 | `Malay UT` | Timurid Siegecraft | 帖木儿 攻城术 | 0/500/400/0 | 50 | False | Tatars |
| 689 | `Burmese UT` | Steppe Husbandry | 大草原 畜牧 | 200/300/0/0 | 40 | True | Cumans |
| 690 | `Burmese UT` | Cuman Mercenaries | 库曼 雇佣兵 | 650/0/400/0 | 40 | True | Cumans |
| 691 | `Vietnamese UT` | Hill Forts | 山城堡 | 250/0/250/0 | 40 | True | Lithuanians |
| 692 | `Vietnamese UT` | Tower Shields | 塔 盾 | 500/0/200/0 | 40 | True | Lithuanians |
| 754 | `Burgundian Vineyards` | Burgundian Vineyards | 勃艮第 葡萄园 | 400/0/300/0 | 45 | True | Burgundians |
| 755 | `Flemish Revolution` | Flemish Revolution | 弗拉芒 革命 | 200/0/150/0 | 10 | True | Burgundians |
| 756 | `First Crusade` | First Crusade | 第一次 十字军东征 | 400/0/300/0 | 60 | False | Sicilians |
| 757 | `Hauberk` | Hauberk | 锁子甲 | 700/0/600/0 | 45 | True | Sicilians |
| 782 | `Szlachta Privileges` | Szlachta Privileges | 贵族 特权 | 500/0/300/0 | 45 | True | Poles |
| 783 | `Lechitic Legacy` | Lechitic Legacy | 列克提克 遗产 | 750/0/550/0 | 60 | True | Poles |
| 784 | `Wagenburg Tactics` | Wagenburg Tactics | 大车阵 战术 | 300/0/300/0 | 45 | True | Bohemians |
| 785 | `Hussite Reforms` | Hussite Reforms | 胡斯 革新 | 500/0/450/0 | 45 | False | Bohemians |
| 831 | `Medical Corps` | Medical Corps | 医疗 部队 | 300/0/200/0 | 45 | True | Dravidians |
| 832 | `Wootz Steel` | Wootz Steel | 乌兹钢 | 650/0/550/0 | 60 | True | Dravidians |
| 833 | `Paiks` | Paiks | 派 | 0/375/275/0 | 45 | True | Bengalis |
| 834 | `Mahayana` | Mahayana | 大乘佛教 | 0/800/650/0 | 60 | True | Bengalis |
| 835 | `Kshatriyas` | Kshatriyas | 刹帝利 | 500/0/450/0 | 45 | True | Gurjaras |
| 836 | `Frontier Guards` | Frontier Guards | 边防 部队 | 800/0/700/0 | 60 | True | Gurjaras |
| 875 | `Gambesons` | Gambesons | 软甲 | 50/0/100/0 | 25 | False | Armenians,Aztecs,Bengalis,Britons,Bulgarians,Burmese,Byzanti… |
| 883 | `Ballistas` | Ballistas | 弩炮 | 0/400/300/0 | 45 | False | Romans |
| 884 | `Comitatenses` | Comitatenses | 野战军 | 700/0/800/0 | 60 | True | Romans |
| 902 | `Pirotecnia` | Pirotechnia | 烟火之术 | 650/0/500/0 | 50 | False | Italians |
| 906 | `Fishing Lines` | Fishing Lines | 钓 线 | 50/100/0/0 | 20 | True | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 907 | `Carvel Hull` | Carvel Hull | 外板平接 船体 | 350/200/0/0 | 60 | True | Armenians,Bengalis,Berbers,Britons,Burgundians,Burmese,Byzan… |
| 908 | `Clinker Construction` | Clinker Construction | 鱼鳞式 建造法 | 150/100/0/0 | 50 | True | Armenians,Aztecs,Bengalis,Berbers,Bohemians,Britons,Bulgaria… |
| 909 | `Carvel Hull` | Siphons | 虹吸管 | 100/0/175/0 | 45 | True | Armenians,Bengalis,Berbers,Bohemians,Britons,Burgundians,Byz… |
| 910 | `Clinker Construction` | Incendiaries | 燃烧弹 | 200/0/325/0 | 50 | True | Armenians,Bohemians,Burgundians,Dravidians,Goths,Italians,Ju… |
| 921 | `Fereters` | Fereters | 费雷特斯 | 550/0/400/0 | 45 | True | Armenians |
| 922 | `Cilician Fleet` | Cilician Fleet | 奇里乞亚 舰队 | 0/350/300/0 | 45 | True | Armenians |
| 923 | `Svan Towers` | Svan Towers | 斯万箭塔 | 300/0/200/0 | 45 | True | Georgians |
| 924 | `Aznauri Cavalry` | Aznauri Cavalry | 阿兹瑙里 骑兵 | 550/0/250/0 | 45 | False | Georgians |
| 996 | `Fortifed Bastions` | Fortified Bastions | 强化 堡垒 | 350/250/0/0 | 40 | True | Jurchens |
| 997 | `Thunderclap Bombs` | Thunderclap Bombs | 霹雳 炸弹 | 900/0/600/0 | 50 | False | Jurchens |
| 1006 | `Lamellar Armor` | Lamellar Armor | 札甲 | 450/0/300/0 | 45 | True | Khitans |
| 1007 | `Ordo Cavalry` | Ordo Cavalry | 斡鲁朵 骑兵 | 600/0/300/0 | 45 | False | Khitans |
| 1012 | `Grazing Grasslands` | Transhumance | 畜牧季移 | 175/325/0/0 | 70 | True | Khitans |
| 1013 | `Enclosures` | Pastoralism | 畜牧业 | 100/150/0/0 | 40 | True | Khitans |
| 1014 | `Livestock Husbandry` | Domestication | 驯化术 | 50/100/0/0 | 20 | True | Khitans |
| 1061 | `Tuntian` | Tuntian | 屯田 | 250/300/0/0 | 40 | True | Wei |
| 1062 | `Ming-Kuang Armor` | Ming Guang Armor | 明光铠 | 600/0/450/0 | 65 | True | Wei |
| 1069 | `Bolt Magazine` | Bolt Magazine | 弩箭匣 | 650/0/750/0 | 40 | True | Shu |
| 1070 | `Coiled Serpent Array` | Coiled Serpent Array | 盘蛇阵 | 350/0/300/0 | 40 | False | Shu |
| 1080 | `Red Cliffs Tactics` | Red Cliffs Tactics | 赤壁 战术 | 400/0/250/0 | 40 | False | Wu |
| 1081 | `Ming-Kuang Armor` | Sitting Tiger | 卧虎 | 0/600/300/0 | 40 | True | Wu |
| 1365 | `Herbalism` | Herbalism | 草药学 | 300/0/350/0 | 40 | True | Muisca |
| 1366 | `Huaracas` | Huaracas | 瓦拉卡斯 | 0/450/350/0 | 45 | True | Muisca |
| 1379 | `Malon` | Malon | 突袭 | 300/0/350/0 | 40 | True | Mapuche |
| 1380 | `Butalmapu` | Butalmapu | 布图马普 | 500/0/450/0 | 45 | True | Mapuche |
| 1392 | `Caciques` | Caciques | 卡西克 | 400/0/200/0 | 45 | True | Tupi |
| 1393 | `Curare` | Curare | 箭毒 | 650/0/600/0 | 45 | False | Tupi |
| 1404 | `Circumnavigation` | Circum- navigation | 环游 世界 | 250/150/0/0 | 40 | True | Portuguese |
| 1452 | `Cranequins` | Cranequins | 便携弯弩装置 | 300/0/200/0 | 70 | True | Britons,Danes,Franks,Saxons,Sicilians,Varangians |
| 1464 | `Shield Wall` | Shield Wall | 盾墙 | 525/0/475/0 | 45 | False | Saxons |
| 1473 | `Vendel Legacy` | Vendel Legacy | 文德尔传承 | 500/0/300/0 | 35 | True | Varangians |
| 1474 | `Gothikon` | Gothikon | 哥瑟砍 | 475/0/400/0 | 50 | False | Varangians |
| 1483 | `Northmen's Fury` | Northmen's Fury | 北方人 之怒 | 0/950/900/0 | 40 | True | Danes |
| 1484 | `Hamask` | Hamask | 哈马思克 | 250/0/450/0 | 35 | False | Danes |
| 1491 | `Clerical Recruitment` | Clerical Recruitment | 神职人员招募 | 350/0/200/0 | 35 | True | Saxons |
| 1496 | `Ordonnance Companies` | Ordonnance Companies | 王家敕令 骑兵 | 400/0/250/0 | 40 | True | Franks |

> `拥有文明` 是从 `civs[c].Tech[]` 反查的。空 = 该科技不在任何文明的 Tech 列表里，通常是通用科技（所有文明共享，不在树里逐个列）或被禁用项。


## 8 建筑全量（40 条）

| ID | 内部名 | 英文名 | 中文名 | HP | 攻 | 远甲 | 近甲 | 射程 | 驻扎 |
|---|---|---|---|---|---|---|---|---|---|
| 12 | `Barracks Age1` | Barracks | 兵营 | 1200 | 0 | 7 | 0 | 0 | 10 |
| 45 | `DOCK` | Dock | 船坞 | 1800 | 3 | 7 | 0 | 6 | 5 |
| 49 | `SIWS` | Siege Workshop | 攻城 武器厂 | 1500 | 0 | 8 | 1 | 0 | 10 |
| 50 | `FARM` | Farm | 农田 | 480 | 0 | 0 | 0 | 0 | 0 |
| 68 | `MILL` | Mill | 磨坊 | 600 | 0 | 7 | 0 | 0 | 0 |
| 70 | `HOUS` | House | 房屋 | 550 | 0 | 7 | -2 | 0 | 0 |
| 71 | `RTWC2` | Town Center | 城镇中心 | 2400 | 5 | 6 | 4 | 6 | 15 |
| 72 | `WALL` | Palisade Wall | 木栅栏 | 150 | 0 | 5 | 2 | 0 | 0 |
| 79 | `WCTW` | Watch Tower | 瞭望 箭塔 | 850 | 5 | 7 | 1 | 8 | 5 |
| 82 | `CSTL` | Castle | 城堡 | 4800 | 11 | 11 | 8 | 8 | 20 |
| 84 | `MRKT` | Market | 市场 | 1800 | 0 | 8 | 1 | 0 | 10 |
| 87 | `ARRG` | Archery Range | 靶场 | 1500 | 0 | 8 | 1 | 0 | 10 |
| 101 | `STBL` | Stable | 马厩 | 1500 | 0 | 8 | 1 | 0 | 10 |
| 103 | `BLAC` | Blacksmith | 铁匠铺 | 1800 | 0 | 7 | 0 | 0 | 0 |
| 104 | `CRCH` | Monastery | 修道院 | 2100 | 0 | 7 | 0 | 0 | 10 |
| 109 | `RTWC` | Town Center | 城镇中心 | 2400 | 5 | 5 | 3 | 6 | 15 |
| 117 | `WALL2` | Stone Wall | 石墙 | 1080 | 0 | 10 | 8 | 0 | 0 |
| 155 | `WALL3` | Fortified Wall | 垛墙 | 3000 | 0 | 12 | 12 | 0 | 0 |
| 199 | `FTRAP` | Fish Trap | 养鱼场 | 250 | 0 | 1 | 1 | 0 | 0 |
| 209 | `UNIV` | University | 大学 | 2100 | 0 | 9 | 2 | 0 | 0 |
| 234 | `WCTW2` | Guard Tower | 警戒 箭塔 | 1500 | 7 | 8 | 2 | 8 | 5 |
| 235 | `WCTW3` | Keep | 大型箭塔 | 2250 | 8 | 9 | 3 | 8 | 5 |
| 236 | `WCTW4` | Bombard Tower | 炮塔 | 2220 | 120 | 9 | 3 | 8 | 5 |
| 276 | `WNDR` | Wonder | 世界奇观 | 4800 | 0 | 10 | 3 | 0 | 0 |
| 487 | `GTAX2` | Gate | 城门 | 1650 | 0 | 0 | 0 | 0 | 0 |
| 562 | `SMIL` | Lumber Camp | 伐木场 | 600 | 0 | 7 | 0 | 0 | 0 |
| 584 | `MINE` | Mining Camp | 采矿场 | 600 | 0 | 7 | 0 | 0 | 0 |
| 598 | `WCTWX` | Outpost | 哨站 | 500 | 0 | 0 | 0 | 0 | 0 |
| 621 | `RTWC1X` | Town Center | 城镇中心 | 2400 | 0 | 7 | 0 | 6 | 0 |
| 792 | `PGTAX` | Palisade Gate | 木城门 | 240 | 0 | 0 | 0 | 0 | 0 |
| 1021 | `FEITO` | Feitoria | 大商站 | 2700 | 0 | 10 | 3 | 0 | 0 |
| 1189 | `HARBOR` | Harbor | 巨港 | 2000 | 3 | 10 | 3 | 7 | 10 |
| 1251 | `KREPOST` | Krepost | 营垒 | 2600 | 10 | 11 | 8 | 7 | 20 |
| 1665 | `DONJON` | Donjon | 城楼 | 625 | 0 | 6 | 0 | 0 | 10 |
| 1734 | `FOLWARK1` | Folwark | 大庄园 | 1000 | 0 | 7 | 0 | 0 | 0 |
| 1754 | `CARAVANSERAI` | Caravanserai | 商队旅馆 | 2700 | 0 | 10 | 3 | 0 | 0 |
| 1806 | `FORTCRCH` | Fortified Church | 强化 教堂 | 2400 | 5 | 10 | 4 | 4 | 10 |
| 1808 | `MULECART` | Mule Cart | 骡车 | 300 | 0 | 2 | 1 | 0 | 0 |
| 1889 | `PASTURE_BUILD` | Pasture | 牧场 | 560 | 0 | 0 | 0 | 0 | 0 |
| 2556 | `SETTL1` | Settlement | 聚落 | 1000 | 0 | 7 | 0 | 0 | 0 |

## 9 每个文明的科技树布局（`data/trees/<CIV>.json`）

页面那张树图不是纯 CSS，是**按 JSON 网格摆的**。`BRITONS.json` 102,190 B，结构：

```json
{ "buildings": [ { "age_id": 2, "building_id": 87, "building_in_new_column": null,
                   "building_upgraded_from_id": -1,
                   "grid": [[null,null,null,null,null], ... ] } ] }
```

`grid` 里每个非 null 单元是 `"Unit_<unitId>_<buildingId>"` 或 `"Tech_..."` 形式的引用——即"这个建筑在这个格子放哪个单位/科技"。
要生成自己的科技树图，直接复用这个格式最省事；56 个文明 × 约 100 KB。


## 10 导出的 CSV

| 文件 | 行数 | 内容 |
|---|---|---|
| `_techtree_units.csv` | 255 | 单位全属性 + 中英文名 + `attacks`/`armours` 的 `class:amount` 串 |
| `_techtree_techs.csv` | 201 | 科技 + 成本 + 时间 + 归属文明列表 |
| `_techtree_buildings.csv` | 40 | 建筑全属性 + 中英文名 |
| `_techtree_civs.csv` | 56 | 文明 + 加成全文（已去 HTML）|

> 上一版这 4 个 CSV 的 `name_en`/`name_zh` 列全空（就是 §3 那个偏移坑），本版已全部回填。


## 11 与 .dat 的对应

aoe2techtree 页面自己写明元数据是用 **genieutils-py** 从 `empires2_x2_p1.dat` 抽的，所以这里的 `ID` 就是 .dat 的单位/科技/建筑索引，
可直接喂给 XS 的 `xsEffectAmount`、场景效果、AI 的 `train`/`research`。
差异点：aoe2techtree 只导了"科技树里会出现的"255 单位 / 201 科技，而 .dat 有 2693 单位 / 1510 科技（含尸体、抛射物、废弃项）——
**要全量就用 HALFON（13 卷），要可用性就用这份。**


## 12 复跑

```bash

curl -s https://aoe2techtree.net/data/data.json -o _probe/_tmp/tt_data_data.json

curl -s https://aoe2techtree.net/data/locales/en/strings.json -o _probe/_tmp/tt_en_fresh.json

curl -s https://aoe2techtree.net/data/locales/zh/strings.json -o _probe/_tmp/tt_zh_fresh.json

curl -s https://aoe2techtree.net/ror/data/data.json -o _probe/_tmp/tt_ror_data_data.json

curl -s https://aoe2techtree.net/chronicles/data/data.json -o _probe/_tmp/tt_chronicles_data_data.json

C:/Users/26913/AppData/Local/Python/bin/python.exe -X utf8 _probe/_tmp/gen_vol15.py

```


## 13 局限

- `data.Unit` 只有 255 条，不是 .dat 全量（无尸体/抛射物/装饰）。
- `civs[].Unit/Tech/Building` 是**科技树里列出的**，不含"默认全文明都有"的通用项。
- RoR / Chronicles 是独立数据文件，没合并进来（结构相同，按 §12 单独拉即可）。
- `Attacks` 里有些 `Amount: 0` 的条目是"占位/显式声明 class"，不是零加成。
