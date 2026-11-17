# awesome-aoe2 全站内容知识库 · 总索引

> 起点：<https://github.com/Arkanosis/awesome-aoe2>（111 条链接 / 116 个 URL）
> 目标：不是"这个链接还活着吗"，而是**把这些站内部的东西全部挖出来，变成能直接查、直接用的表**。
> 抓取与实测时间：2026-11-08。全部数字都是当天真跑出来的，不是抄 README。
>
> 姊妹文件：`../awesome-aoe2-链接审计-2026-11-08.md`（存活/维护状态/死链审计，469 行）  
> 两个重点站的全量对账：`00-两个站的全量对账.md`（airef 与 ugc.aoe2.rocks 各自"站里有什么、卷里在哪、什么是真空的"）

---

## 0 怎么用这份东西

**不要从头读。** 按下面第 1 节查表，直接跳到你需要的卷。

三句话概括这套东西的价值：

1. **AI 脚本 / XS / 场景 / RMS 这四类"游戏内脚本"，文档站本身是空壳 HTML**（数据全在 JS 里），
   网上抄来的片段大多过期。本库是**从站点 JS 里反解出来的全量结构化数据**（386 条命令、100 个参数、
   313 个 SN、全部 load-if 符号、295 条 RMS 指令、678 份真实地图脚本）。
2. **单位/科技/建筑的数值**有三个互相独立的来源（HALFON 的 dat 导出、aoe2techtree 的 genieutils 导出、
   aoe2.is 的手工矩阵、civbuilder 的模板），本库把它们都落成 CSV，可以交叉验证。
3. **写模组的三条代码管线**（`.dat` / `.aoe2scenario` / `.aoe2record`）我逐个装起来跑过，
   第 23 卷记录的是真实成功率与版本坑 —— 包括"mgz 对 2026 年的录像完全失效"这种没人写在 README 里的事。

---

## 1 快速查表：我要做什么 → 读哪一卷

| 我要做的事 | 卷 | 具体入口 |
|---|---|---|
| 写一个 AI（`.per`）脚本，查命令怎么用 | **01** | 386 条命令按 Fact / Action / Command / Other 分组，每条带参数表、示例、相关 SN |
| 查 AI 参数的取值域（`object-data` 能填什么） | **02** | 100 个参数，每个附完整 `valueList` 表 |
| 改某个 SN（比如 `sn-maximum-food-drop-distance`） | **03** | 313 条 SN，含默认值 / AoC / UP / DE 四代可用性 |
| 写 `#load-if-defined` / 查某张图、某个文明的条件符号 | **04** | 17 组共 **430** 个符号，每组带官方说明（197 张 AoE2 图 / 28 张 RoR 图 / 57 个 AoE2 文明 / 18 个 RoR 文明 / 6 个编年史文明） |
| 查某个 AI 命令的历史 bug，避免踩坑 | **04** / **14** | 84 条已知 bug（含 2026-11-04 新报） |
| 查单位/科技 ID 在 **编年史(DLC)** 或 **罗马归来** 下是多少 | **04** | 三套平行表：AoE2 809 对象/326 科技、Chronicles 238/161、RoR 184/79 |
| 写 XS（`.xs`）脚本，查函数签名 | **05** | 全部 XS 函数（含返回类型、原型、参数说明）+ 常量全表 + 官方库 |
| 场景编辑器里配 effect / condition 的每个字段 | **06** | 每条 effect 的配置项表格 + 全部 condition |
| 查属性 ID（`xsEffectAmount` 的 attribute 填几） | **07** | **211 条**属性全表 + Resources + Tasks + 伤害计算公式推导 |
| 学 XS（从零 / 有编程基础） | **08** | For Beginners + For Programmers + Tricks + 7 类已知 bug |
| 打包 / 发布一个 mod | **09** | `info.json` 格式、目录镜像规则、in-game 与 zip 两条发布路径 |
| 做 RMS 随机地图 | **12** → **16** → **10** | 先读 Zetnus 指南全文，再看 678 份真实脚本的统计，最后看热键 |
| 改造一个现成 RMS | **16** | 769 张图的索引 + 295 条指令的语料频次 + 每条的示例片段 |
| 用 Python 改 `.dat`（单位数值） | **23** §1 | genieutils-py，含**字节级无损往返**验证与 `Type50` 字段全表 |
| 用 Python 改 `.aoe2scenario` | **23** §2 → **11** | 先看版本坑（必须 0.9.9），再看 18 页官方文档 |
| 查 AoE2ScenarioParser 的类 / 方法签名 / 枚举 ID | **24** | 84 页 pdoc API 全量：3922 个枚举成员 + 260 个方法签名 |
| 写 trigger 时要填的 effect 字段名（`message` 还是 `string_id`） | **24** | 搜 `Attributes for the <name> effect are:` |
| 解析 `.aoe2record` 录像 | **23** §3 | 真实成功率 29%，含容错封装写法 |
| 查某单位/科技的精确数值（DE / RoR / HD / WK） | **13** | 2693 单位 + 1510 科技的四个版本 CSV |
| 查科技树 / 某文明有什么 | **15** | 56 文明 + 255 单位 + 201 科技 + 40 建筑，含归属文明 |
| 查某文明能造什么（缺什么） | **19** | 10 个页签的可用性矩阵，56 文明 × 全项目 |
| 找一张现成地图 / 找某作者的作品 | **16** | 769 张图 + 70 个合集 + 291 个标签 |
| 找现成 mod / 看某类 mod 的下载量 | **17** | 模组目录抓取进度与 16 个分类的榜单；样本口径在卷内标明 |
| 看官方论坛里别人怎么解决某个 modding 问题 | **21** | 6382 个主题索引 + 30 篇关键技术帖全文 |
| 造自定义文明（civbuilder 机制） | **20** | 650 张卡牌 + 8 个类别 + `unitStats` 模板 |
| 单位克制 / 造价 / 战斗模拟 | **22** | 144 单位战斗参数 + 109 单位成本 + 采集速率 |
| 找教程（build order / 新手 / 策略） | **18** | Age of Notes 309 篇有内容的文章全索引 |

---

## 2 卷册清单

| 卷 | 标题 | 字节 | 行数 | 主要数据源 | 形态 |
|---|---|---|---|---|---|
| 01 | AI脚本-命令全量386条 | 445 KB | 9679 | airef.github.io `js/commands.js`（2.0 MB，node vm 反解） | 数据全量 |
| 02 | AI脚本-参数全量100个 | 201 KB | 2900 | 同上 | 数据全量 |
| 03 | AI脚本-战略数字SN全量313条 | 121 KB | 1384 | 同上 | 数据全量 |
| 04 | AI脚本-数据表与已知bug | 259 KB | 3352 | 同上（loadIf 430 符号 / objects 三版本 / techs 三版本 / bugs 84 / events / res-index） | 数据全量 |
| 05 | XS-函数与常量全量 | 311 KB | 11643 | `Divy1211/AoE2DE_UGC_Guide` 仓库原始 Markdown（函数 288 / 常量 1170 / 45 类） | 数据全量 |
| 06 | 场景-触发器效果条件全量 | 99 KB | 2177 | 同上（`triggers/{effects,conditions}`） | 数据全量 |
| 07 | XS-ID表-属性资源任务与伤害计算 | 190 KB | 7697 | 同上（attributes 211 / resources / tasks / damage_calculation） | 数据全量 + 公式推导 |
| 08 | XS-教学技巧与坑 | 99 KB | 2563 | 同上（beginner / programmer / tricks / bugs 9 篇含 Fixed） | 教程全文 |
| 09 | Mod打包与发布规范 | 7.4 KB | 177 | 同上（`mods/` 章节） | 规范全文 |
| 10 | 场景AI音频RMS与热键 | 33 KB | 622 | 同上（scenarios / ai / audio / rms / hotkeys）+ 空页清单附录 | 全文 + 缺口清单 |
| 11 | AoE2ScenarioParser全文档 | 88 KB | 2637 | docsify `_sidebar.md` → 18 页原始 Markdown | 文档全文 |
| 12 | RMS随机地图脚本指南全文 | 281 KB | 6361 | Zetnus 的 Google Docs（`export?format=txt`） | 指南全文 |
| 13 | HALFON-全单位科技数据 | 43 KB | 835 | `halfon.aoe2.se/data/units_buildings_techs.{de,ror,hd,wk}.json` | 数据全量 + 枚举反推 |
| 14 | AI脚本-深度教程13篇 | 194 KB | 3383 | `airef.github.io/resources/articles/*.html` | 长文全文 |
| 15 | aoe2techtree-科技树数据 | 65 KB | 805 | `aoe2techtree.net/data/data.json`（965 KB） | 数据全量 + 偏移坑 |
| 16 | RMS地图库-769张与678份脚本语料 | 39 KB | 695 | `aoe2map.net` + 678 份 `.rms` 原文（241 MB） | 索引 + 语料统计 |
| 17 | 模组目录-61832个mod全量统计 | 19 KB | 358 | `mods.aoe2.se` 的 `POST /api/v1/mods` | 样本 + 全站口径 |
| 18 | AgeOfNotes-309篇教程全索引 | 116 KB | 1428 | WordPress REST API | 索引 + 40 篇摘录 |
| 19 | aoe2.is-文明可用性矩阵 | 94 KB | 858 | 10 个页签的静态 HTML 表 | 数据全量 |
| 20 | civbuilder-650张卡牌与自定义文明机制 | 60 KB | 915 | `krakenmeister.com/civbuilder/js/common.js`（node vm） | 数据全量 |
| 21 | 社区实战-官方论坛模组区6382帖索引 | 144 KB | 3561 | Discourse `/c/109.json` + `/c/258.json` + 30 篇全帖 | 索引 + 全文 |
| 22 | 计算器与数值工具-战斗模拟器与成本表 | 37 KB | 478 | `aoe-combatsim.com` Angular bundle + `grishrl.github.io/constants.js` | 数据反解 |
| 23 | 开发库实测-三条数据管线的真实可用性 | 17 KB | 460 | 本机真跑（genieutils-py / AoE2ScenarioParser / aoe2rec-py / mgz） | 实测报告 |
| 24 | AoE2ScenarioParser-API参考全量 | 541 KB | 15601 | `ksneijders.github.io/AoE2ScenarioParser/api/`（84 页 pdoc HTML，17.95 MB） | 文档全量 |

合计 **3.42 MB Markdown / 80569 行**，另附 28 个 CSV（**84133 行、8.25 MB**，详见第 4 节）。

---

## 3 数据形态分类（判断可信度用）

**A 类：官方/权威数据源的机器导出** —— 直接来自 dat 或站点导出 JSON，可信度最高
`13`（HALFON，源自 dat）、`15`（aoe2techtree，用 genieutils-py 从 dat 导出）、`22`（combatsim）
—— 但注意 `13` 和 `15` 的数字**不完全一致**（不同游戏版本、不同导出时段），交叉验证时以各自版本标称为准。

**B 类：站点 JS 反解出的结构化全量** —— 站点 HTML 是空壳，数据在 JS 里
`01`–`04`（airef，2.0 MB JS）、`20`（civbuilder，95 KB JS）、`22`（combatsim，1.5 MB Angular bundle）
—— 这些是本库最大的增量。**用浏览器爬页面永远拿不到**，必须 node vm 执行 JS。

**C 类：站点文档的全文搬运** —— 内容本身质量取决于原作者
`05`–`08`、`11`、`12`、`14`、`18`、`21`、`24`（`05`–`10` 用的是**仓库原始 Markdown**，不是渲染后 HTML，因此没有 MkDocs 页脚噪音）

**D 类：我实跑出来的结论** —— 无法从任何文档获得
`16`（678 份真实脚本的指令频次）、`23`（成功率与版本坑）

**E 类：手工/半自动采集，有明确覆盖率上限**
`17`（模组目录，抓取进度见卷内）、`19`（100% 但源站 2021 年的数据）

---

## 4 CSV 附件（可直接 import）

| 文件 | 数据行 | 大小 | 内容 | 卷 |
|---|---|---|---|---|
| `_asp_enums.csv` | 3932 | 149 KB | AoE2ScenarioParser 全部枚举：enum,member,id,icon_id,line（TechInfo 600 / UnitInfo 518 / EffectId 103 / Civilization 67 …） | 24 |
| `_civ_availability.csv` | 10528 | 341 KB | long 格式 page/civ/item/has（10 页签 × 56 文明） | 19 |
| `_civbuilder_cards.csv` | 650 | 55 KB | 卡牌：池/文案/稀有度/槽位/edition | 20 |
| `_combatsim_units.csv` | 144 | 22 KB | 战斗模拟器 144 单位的 17 个字段（含攻击/护甲 class 表） | 22 |
| `_forum_topics.csv` | 6382 | 626 KB | 论坛主题：id/title/分类/浏览量/回复数/日期/url | 21 |
| `_grishrl_unitcost.csv` | 109 | 3 KB | 单位造价与训练时间 | 22 |
| `_halfon_techs_de.csv` | 1510 | 74 KB | DE 全科技：四项造价 + help_converter + 语言键 | 13 |
| `_halfon_techs_hd.csv` | 801 | 36 KB | HD | 13 |
| `_halfon_techs_ror.csv` | 191 | 9 KB | RoR | 13 |
| `_halfon_techs_wk.csv` | 804 | 36 KB | WK | 13 |
| `_halfon_units_de.csv` | 2693 | 159 KB | DE 全单位：HP/LOS/攻/远近防/驻守/四项造价/type/class/base_id/rms_const | 13 |
| `_halfon_units_hd.csv` | 1390 | 71 KB | HD 同上 | 13 |
| `_halfon_units_ror.csv` | 2737 | 130 KB | RoR 同上 | 13 |
| `_halfon_units_wk.csv` | 1390 | 72 KB | WK 同上 | 13 |
| `_loadifs.csv` | 430 | 33 KB | load-if 全符号：group_no,group,type,symbol,description | 04 |
| `_maps_index.csv` | 769 | 162 KB | 769 张图：id,name,author,versions,tags,collections,script_bytes,desc,url | 16 |
| `_mods_index.csv` | 47043 | 6.16 MB | mod 目录：id/name/tags/creator/created/updated/downloads/installs/likes/rating/fileSize/version | 17 |
| `_objects.csv` | 809 | 98 KB | **AoE2 主表**全部对象（按 id 去重后）：id,name,aiName,line,class,cmdId,building,age,deadUnit,projectile,chemProjectile,civ,weirdName,notes,categories | 04 |
| `_objects_chr.csv` | 238 | 32 KB | **Chronicles: Battle for Greece** 对象，同字段 | 04 |
| `_objects_ror.csv` | 184 | 22 KB | **Return of Rome** 对象，同字段（无 projectile 列） | 04 |
| `_techs.csv` | 326 | 22 KB | **AoE2 主表**科技：id,name,aiName,building,age,civ,notes | 04 |
| `_techs_chr.csv` | 161 | 7.6 KB | **Chronicles** 科技，同字段 | 04 |
| `_techs_ror.csv` | 79 | 5.9 KB | **Return of Rome** 科技：id,name,building,age,cost,time,description,notes | 04 |
| `_techtree_buildings.csv` | 40 | 2.6 KB | 建筑 | 15 |
| `_techtree_civs.csv` | 56 | 28 KB | 文明 + 完整加成文本 | 15 |
| `_techtree_techs.csv` | 201 | 43 KB | 科技 + **被哪些文明拥有**（第 11 列） | 15 |
| `_techtree_units.csv` | 255 | 35 KB | aoe2techtree 单位（含中英文名、完整 attacks/armours） | 15 |
| `_unitlines.csv` | 117 | 12 KB | 单位线（117 条）：name,id,deId,description | 04 |

> 行数是**数据行**（不含表头）。合计 **84133 行 / 8.25 MB / 28 个文件**。

---

## 5 本库证明不了的事（诚实边界）

写报告最怕把"没抓到"说成"不存在"。以下是确知的缺口：

1. **Fandom wiki 一篇都没抓到。** `ageofempires.fandom.com` 在本机四条路全断
   （系统代理 ProxyError、直连 ConnectTimeout、r.jina.ai ConnectionError、
   allorigins/codetabs 522、corsproxy.io 需要 API key）。
   所以"哪个单位叫什么、哪个战役怎么打"这类**叙事性内容**本库没有，只有结构化数值。
2. **mod 目录是全站 61832 条里的一部分，卷内标了样本口径。**
   曾经判「深分页 page>900 直接 HTTP 500、永久抓不动」，**这个判断错了**：真因是并发太高。
   单线程串行实测 page 598/620/700/900 全部 200、各 50 条（23–41 s/页），
   所以 `_probe/_tmp/mod_crawl4.py`（3 线程、timeout 240 s、10 次退避）能一路翻到最后一页。
   卷 17 的分类占比、作者榜、下载榜**按卷内标注的样本量读**，不要把样本数当全站数。
3. **Liquipedia 的赛事数据没进库。** 站点本身能连（`api.php` 需自定义 UA、间隔 ≥2 s），
   15872 个条目标题已抓到 `_probe/_tmp/lq_titles.json`，但 AoE2 的文明页基本是空的
   （`Mongols` 的 wikitext 只有 21 字节），价值在赛事/选手数据上 —— 那部分与"做模组"无关，没展开。
4. **aoe2recs 的 spectators dashboard 是下线状态。** 页面明写 "Spectator Dashboard Temporarily Offline"。
5. **mgz 对新录像完全不能用**，别照 README 试。
6. **UGC Guide 里有 10 个页面本身是空的，不是漏抓。**
   已用仓库原文验证：`docs/rms/basics.md`、`docs/scenarios/tricks.md`、
   `docs/scenarios/advanced/byte_structure.md`、`docs/scenarios/triggers/variables.md`、
   `docs/scenarios/useful_tools/age/{unhide,uses}.md`、`docs/mods/age/basics.md`、
   `docs/publishing_ugc/publish.md`、`docs/general/xs/bugs/{Task,Effect Amount}.md`
   —— **这 10 个文件在 `Divy1211/AoE2DE_UGC_Guide` 仓库里就是 0 字节**。
   完整清单与站点 URL 见 10 卷附录 A。
7. **aoe2-de-tools.herokuapp.com 在本轮已连不上**（http/https/.js 全 ConnectionError）。
   之前抓到的 `/villagers-required/` 单页 2.6 MB 就是它的全部数据，已进 22 卷。

---

## 6 复跑

所有脚本在 `../_probe/_tmp/`，中间数据也在那里（`rms/` 241 MB、`mods_pages/`（断点续传，每页一个 JSON）、`forum/` 等）。

```bash
# 环境
PY=C:/Users/26913/AppData/Local/Python/bin/python.exe
NODE=D:/Software/nodejs/node.exe

# 站点 JS 反解（airef 386 条命令）
$NODE _probe/_tmp/dump_airef3.js          # → airef_flat.json (2.52 MB)
$PY  -X utf8 _probe/_tmp/gen_airef.py      # → 01/02/03 卷
$PY  -X utf8 _probe/_tmp/gen_vol04.py      # → 04 卷 + _objects{,_chr,_ror}.csv / _techs{,_chr,_ror}.csv / _loadifs.csv

# UGC Guide（从 GitHub 仓库原始 Markdown 重建 05–10 卷）
$PY  -X utf8 _probe/_tmp/gen_ugc2.py       # → 05/06/07/08/09/10 卷

# civbuilder 卡牌
$NODE _probe/_tmp/dump_civb.js             # → civb.json
$PY  -X utf8 _probe/_tmp/gen_vol20.py      # → 20 卷 + _civbuilder_cards.csv

# AoE2ScenarioParser API 参考（pdoc，84 页）
$PY  -X utf8 _probe/_tmp/asp_crawl.py      # → _probe/_tmp/site/asp_api/ + asp_api_sizes.json
$PY  -X utf8 _probe/_tmp/asp_parse2.py     # → _probe/_tmp/asp_md2/*.md（545647 字符）
$PY  -X utf8 _probe/_tmp/gen_vol24.py      # → 24 卷

# 科技树（注意 LanguageNameId 偏移：单位/建筑 +9000，科技 +10000，文明 0）
$PY  -X utf8 _probe/_tmp/gen_vol15.py

# RMS 语料（先有 _probe/_tmp/rms/ 里的 678 份原文）
$PY  -X utf8 _probe/_tmp/gen_vol16.py

# mod 目录（3 线程；深分页单页 20–45 s，别开高并发，开了就 500）
$PY  -X utf8 _probe/_tmp/mod_crawl4.py 3     # → _probe/_tmp/mods_pages/*.json
$PY  -X utf8 _probe/_tmp/gen_vol17.py

# 论坛
$PY  -X utf8 _probe/_tmp/forum_cat2.py 109 48
$PY  -X utf8 _probe/_tmp/forum_cat2.py 258 166
$PY  -X utf8 _probe/_tmp/gen_vol21.py
```

**三个必踩的坑**（省你几小时）：
- `requests` 必须 `Session().trust_env=False`，否则本地代理会掐长连接；
- `raw.githubusercontent.com` 走 `https://gh-proxy.com/` 前缀；
- 站点 JS 里 `var x = new SomeClass(...)` 这种构造式数据，**不要用 WeakSet 去重**
  （会把对象压成 `@name` 字符串），要按 `constructor.name` 判断。

---

## 7 一句话收尾

111 条链接里，真正**有内部数据可挖**的是 20 个站；**有内容但站已死/半死**的 6 个；
剩下 80 多个是导航、社区、录像站、视频频道，价值在"知道它在"而不在"挖它"。

那 20 个站的内部数据，现在都在这 24 卷里了。

其中 **airef 与 ugc.aoe2.rocks 两个站已经做到「站点有什么，卷里就有什么」**：
airef 的 6 个 `tables/*` 页是纯 JS 渲染的空壳，数据全部从 `js/commands.js` 反解（三套 objects/techs 平行表 + 430 个 load-if 符号）；
ugc.aoe2.rocks 的 51 个 URL 里 41 个有正文、10 个在仓库里就是 0 字节，这两类都已在卷内标明。

*生成：2026-11-08 · 24 卷 + 28 CSV · 3.42 MB Markdown + 8.25 MB CSV*
