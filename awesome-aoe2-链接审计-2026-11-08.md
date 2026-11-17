# awesome-aoe2 全链接审计报告

- 审计对象：<https://github.com/Arkanosis/awesome-aoe2>
- 审计时间：2026-11-08（全部状态码、标题、正文摘要均为当日实测）
- 覆盖范围：README 内 **111 条条目 / 116 个唯一 URL**，另加 README 开头推荐的 AOE Library，以及用户截图里的 13 条收藏夹
- 探测方式：`requests` 并发 GET（12 线程）+ 必要处 Playwright 真渲染（Cloudflare / JS SPA / 反爬站点）+ GitHub REST API（stars / pushed / archived / license / release / 改名）+ YouTube 页面内嵌 JSON 校验频道与视频 + Google Docs·Sheets 与 Play Store 的 og:title 实读

---

## 0. 一句话结论

**这个列表整体是健康的**：116 个 URL 里 101 个直接 200，4 个只是被 Cloudflare / 反爬挡住（站点活着），真正死掉的是 4 个（3×404 + 1×522），另有 1 个（aoe2database.com）源站 DNS 已经没了（530 Error 1016）、1 个服务已下线但域名还在（aoe2recs.com）。

**但「活着」≠「还能用」**：至少 7 个站点处于「页面在、内容停更一至四年」状态（tlgs 评分分布停在 2023-05-21、SenseiDE 停在 2022-04、aoe-twools 停在 2023-12、freeaoe 停在 2022-12、aoe2calc 明说不支持 DE、McMinimap 已 archived、aoe2-de-macos 停在 2023-08）。列表本身最后一次提交是 2026-10-25，作者仍在维护，但**只加新条目、不清理旧条目**。

**对本工作区（aoe2mod 模组工坊 / AGE 逆向 / DAT·SLD·UI 贴图 / AI+XS）真正有用的就 9 条左右**，其余是玩家侧工具。见第 5 节。

---

## 1. 总览统计

### 1.1 条目分布

| 章节 | 条目数 | 说明 |
|---|---|---|
| Websites / Profiles | 7 | 玩家档案、对局分析 |
| Websites / Documentation | 10 | 科技树、单位表、数据库 |
| Websites / Civilization pickers | 5 | BP / 抽文明 |
| Websites / Tools | 16 | 计算器、模拟器、lobby、回放 |
| Websites / Statistics | 7 | 胜率、ELO 分布 |
| Websites / Guides | 7 | build order、上城时间、平台指南 |
| Websites / User Generated Content | 3 | RMS 指南、UGC 指南、AI 脚本百科 |
| Websites / Tournaments | 4 | 赛事面板、赛事 ELO、回放打包 |
| Websites / Wikis | 2 | Fandom、Liquipedia |
| Websites / Communities | 4 | Reddit、AoEZone、官方论坛、SE |
| Websites / Blogs | 1 | Age of Notes（+ RSS 附加链接） |
| Websites / Information | 2 | 术语表、缩写表 |
| Programs | 6 | 含 1 条**无链接**条目（AGE） |
| Mods | 2 | mod 目录 + 一个具体 mod |
| Smartphone apps | 2 | |
| Games | 3 | 每日小游戏 |
| Streaming tools | 2 | 直播用 |
| Programming tools | 7 | 解析库 / 场景库 / 小地图 |
| YouTube channels | 20 | Theory 7 / Casting 2 / Humor 1 / Interviews 2 / Music 4 / History 2 |
| Similar games | 3 | openage / freeaoe / 0 A.D. |
| **合计** | **111** | 另有 7 条 "source code" / "RSS" 附加链接 |

### 1.2 存活状态（按条目主链接，110 条有 URL）

| 状态 | 条数 | 占比 | 含义 |
|---|---|---|---|
| 200 | 101 | 91.8% | 正常 |
| 403 | 4 | 3.6% | Cloudflare 人机验证 / 反爬挡爬虫，站点活着 |
| 404 | 3 | 2.7% | 真死 |
| 522 | 1 | 0.9% | Cloudflare 源站超时，事实死亡 |
| 530 | 1 | 0.9% | Cloudflare Error 1016，源站 DNS 消失 |

### 1.3 需要区分的三类「异常」

1. **真死（5 处 / 4 个域名 + 1 个双死）**：aoestats.io（522）、aoepulse.com（404）、aoe2.up.railway.app（404）、gowerc/aoecps 页面 + 仓库（双 404）、aoe2database.com（530，源站 DNS 没了）。
2. **只是挡爬虫（4）**：aoe2insights.com、aoe2.gg、ageofempires.fandom.com、liquipedia.net —— 全部 403，浏览器正常可看。
3. **域名活着但业务下线 / 停更（1 + 7）**：aoe2recs.com（"Spectator Dashboard Temporarily Offline"）属下线；其余属停更（见 3.3）。

---

## 2. 逐条审计

图例：**状态** = 实测 HTTP 码；**维护** = 最后实质更新（GitHub 看 pushed_at，网站看页面自述或数据时间戳）。

### 2.1 Websites / Profiles（7）

| # | 名称 | URL | 状态 | 是什么 | 维护 |
|---|---|---|---|---|---|
| 1 | AoE2Insights | https://www.aoe2insights.com/ | 403 CF 验证 | 对局分析 + 玩家档案，最知名的 match 分析站 | 活着，反爬严格（Playwright 也过不去） |
| 2 | AoE II Companion | https://aoe2companion.com/leaderboard → `www.aoe2companion.com/(main)/statistics/leaderboard` | 200（2 跳） | 追战绩的 App 后端 | 活跃 |
| 3 | AoE2.GG | https://aoe2.gg/ | 403 CF 验证 | 玩家档案 + ELO | 活着，全站挡自动化 |
| 4 | AgeOfEmpires.com | https://www.ageofempires.com/stats/ageiide | 200 | 官方天梯榜（World's Edge Studio） | 官方，随赛季更新 |
| 5 | MultiProfile | https://aoe2.arkanosis.net/mp/ | 200 | 把上面几家档案聚合到一页，v0.2.2，ISC | 作者 Arkanosis（即本列表维护者）自建 |
| 6 | AoCRec | https://aocrec.com | 200 | **中文站「帝国时代档案库」**：上传/下载/解析/搜索存档，出玩家档案与 ELO；支持 AoC10a / UP15 / AoC10c | 活跃，实测有 2026-10-28 的对局 |
| 7 | AoE2 Analysis | https://aoe2analysis.com/ | 200 | 分析开局与胜负策略，专门抓 smurf / Elo tanking | ©2025–2026，数据来自公开 API |

> aocrec.com 是全表唯一的中文社区站点；它的「按版本筛选（AoC10a / UP15 / AoC10c）」说明它面向**老版本录象**，与 DE 的 `.aoe2record` 不是一回事。

### 2.2 Websites / Documentation（10）

| # | 名称 | URL | 状态 | 是什么 | 维护 |
|---|---|---|---|---|---|
| 8 | aoe2techtree.net | https://aoe2techtree.net/ | 200（5.3 KB 壳，JS 渲染） | 浏览器版完整科技树；版本 `DE Update 188329 / Chronicles / RoR`；元数据由 **genieutils-py** 提取 | 活跃，源码 SiegeEngineers/aoe2techtree **284★ / 2026-10-27 / MIT**（HSZemi/aoe2techtree 是旧仓，0★ / 2021-01-08） |
| 9 | Simplified tech tree | https://aoe2-de-tools.herokuapp.com/civ-ranking.html → `/civ-ranking/` | 200（1 跳） | 只列「1v1 Arabia 相关且非全文明共有」的单位与升级 | Heroku 免费层早已取消仍在线，说明作者自费续着 |
| 10 | aoe-twools | https://aoetwools.firebaseapp.com/ | 200（纯 JS，正文只有标题） | 按单位/科技反查文明 | **作者自述「游戏更新太快跟不上了」**，源码 Kheyzell/aoe-twools 3★ / **2023-12-24** 后停更，无 license |
| 11 | AoE 2 Database | https://www.aoe2database.com/ | **530 Error 1016** | 单位/建筑/科技/文明数据库（曾是主力站） | **源站 DNS 已消失**，`/technologies/en` 同样 530；搜索引擎缓存里还有正文 |
| 12 | AoE2.is | https://aoe2.is/ | 200 | 双文明科技树差异对比，定位「第二屏」工具，可隐藏码头等 | 活跃；同域 `/AOE%20Unit%20costs.pdf` 是 281 KB 真 PDF（单页「维持持续产兵所需农民数」速查表） |
| 13 | Halfon | https://halfon.aoe2.se/ | 200 | 单位/建筑/科技数值参考表，可切 `DE 188329 / ROR 185872 / HD 5.8 / WK 5.8.1`；列 ID / Name / Localised / HP / LOS / ATK / MA / PA / GC / 木食金石 / Type / Class | 活跃（Siege Engineers） |
| 14 | AoE Unit Counters | https://age-of-empires-unit-counters.vercel.app/ | 200 | 单位克制关系查询 | 源码 lukethacoder/... 5★ / **2022-03-12** / GPL-3.0，事实停更 |
| 15 | AoE II Infographic Gallery | https://aoe2tournaments.com/images | 200 | 作者自制信息图（升级链、克制关系） | 与 #56 同站同源 |
| 16 | Counters matrix | https://docs.google.com/spreadsheets/d/12-xJ4ePJfGlyUNpmLwkYBsLLB2qM1ZdokABrZuZgL1Q/edit#gid=0 | 200 | 克制矩阵（标题 "AOE 2"） | Google Sheets 直读可开 |
| 17 | Civilization Tool | https://tiny.cc/CivilizationTool | 200（302 → Power BI） | 文明强弱，Power BI 报告 | 能开 |

### 2.3 Websites / Civilization pickers（5）

| # | 名称 | URL | 状态 | 是什么 | 维护 |
|---|---|---|---|---|---|
| 18 | Captains Mode | https://aoe2cm.net/ | 200（2.2 KB SPA，Playwright 可读） | BP（Ban/Pick）站，每轮 30 秒、支持选/禁/偷/狙击；Private Drafts、公开 Draft 列表、API 给起始时间戳；**界面已本地化到简体中文** | 源码 SiegeEngineers/aoe2cm2 **62★ / 2026-10-08 / TypeScript / 16 open issues**（旧仓 aoe2cm 0★ / 2021-01-27） |
| 19 | Civpicker | https://aoe2.arkanosis.net/civpicker/ | 200 | 勾「想玩什么」（Barracks / Archery / Stable / Others / Strategy）→ 推荐文明 | 作者自建 |
| 20 | Random Civ Selector | https://aoe-rcs.com/ | 200 | 预设池随机抽 | 页面只有标题，纯前端 |
| 21 | Fresh Random Civ Picker | https://github.com/cnordenb/Fresh-Random-Civ-Picker_GUI | 200 | 不重复抽取的抽文明 GUI | 4★ / 2026-10-18 / MIT / v1.4.2 |
| 22 | Civ Explorer | https://frcp.net/civexplorer/ | 200（**已迁移**） | 列出拥有所选全部科技的文明 | 老页只剩一句 "Moved to new domain"，真站 **https://civexplorer.net/**（需 JS） |

### 2.4 Websites / Tools（16）

| # | 名称 | URL | 状态 | 是什么 | 维护 |
|---|---|---|---|---|---|
| 23 | aoe2recs | https://aoe2recs.com/ | 200 但**服务下线** | 「Spectator Dashboard」，观战用回放面板 | 页面明写 **"Spectator Dashboard Temporarily Offline"**；Vite 构建，数据源 Liquipedia + Tournament Elo |
| 24 | Wololo rating distribution | https://tlgs.github.io/wololo/ | 200 | 1v1 RM 天梯 ELO 直方图 | **数据停在 2023-05-21**（47026 活跃玩家、中位 998），三年未更新 |
| 25 | aoe2map | https://aoe2map.net/ | 200 | RMS（随机地图脚本）分享站：Map Collections / Mappack Creator / Snippets / Contests（Holy Cup 2021、World Desert Championship 2021、Masters of RMS 2020、24 Hours 2018） | 源码 SiegeEngineers/aoe2map 13★ / **2024-11-12** / GPL-3.0 / 13 open issues |
| 26 | Hotkey Editor | https://aokhotkeys.appspot.com/ | 200 | 热键编辑器，带 TheViper / AoC / HD 预设（web2py 后端） | 老站，GAE 上还能跑 |
| 27 | Villagers required | https://aoe2-de-tools.herokuapp.com/villagers-required.html → `/villagers-required/` | 200（1 跳） | 维持持续产兵所需农民数 | 同 #9 |
| 28 | Unit production cheatsheet | https://aoe2.is/AOE%20Unit%20costs.pdf | 200 `application/pdf` 281 KB | 单页速查表 | 见 #12 |
| 29 | aoe2calc | https://gbts.github.io/aoe2calc/ | 200 | 单位/科技计算器 | **README 与列表原文都标 "does not support DE yet!"** → 事实上只对 HD / AoC 有效 |
| 30 | AoE Combat Simulator | https://aoe-combatsim.com/ | 200（纯 JS） | 战斗模拟器 | 页面只有标题，长期未变 |
| 31 | AoE2 Analyzer | https://aoe2.up.railway.app/ | **404** | 战斗模拟 + 队伍分析 + 文明强弱 | **已下线** |
| 32 | Sage of Empires | https://sage-of-empires.web.app/ | 200（Firebase SPA） | 1v1 时看的文明信息与 build order | meta "Knowledge and Wisdom when you need it." |
| 33 | Random Rating Match Retriever | https://thbrown.github.io/aoe2-de-random-elo/ | 200 | 在指定分数段里「随机」挑一场正在进行的对局 | 纯前端 |
| 34 | Civilization Builder | https://krakenmeister.com/civbuilder | 200（1 跳 → `/civbuilder/`） | **自定义文明生成器**（combine civs / create draft / events） | **活跃**：页面挂着 "Civbuilder FFA 2! Registrations open now!"，接受付费定制 |
| 35 | Aoe2 Army Composition Calculator | https://conorbronsdon.github.io/aoe2-troop-calculator/ | 200 | 军队组成与成本计算器（100+ 单位、51 文明） | 仓库 **archived=true**（2★ / 2026-07-31），只读 |
| 36 | AOE2Lobby | https://aoe2lobby.com/ → `/lobby` | 200 | 实时 lobby 列表 + 筛选 + 关注玩家在线 | Vue SPA，已多语言（含中文），活跃 |
| 37 | AoE2 Replay Viewer | https://liouh.com/aoe2/ | 200 | 浏览器内回放：minimap 播放 + 关键数据 + build timeline；支持本地 `.aoe2record` 或 URL | 页面直接写出三平台存档路径（Win / Mac 原生 / Mac Steam·CrossOver `compatdata/813780`） |

### 2.5 Websites / Statistics（7）

| # | 名称 | URL | 状态 | 是什么 | 维护 |
|---|---|---|---|---|---|
| 38 | aoestats | https://aoestats.io/ | **522** | 按 ELO / 地图 / 时长 / 补丁拆分的文明胜率（曾是最核心的统计站） | **死亡**（Cloudflare 源站超时；搜索引擎仍有缓存页） |
| 39 | AoE Pulse | https://www.aoepulse.com/ | **404 "Coming Soon"** | 开局使用率、文明统计、科技时间点 | **死亡**（PythonAnywhere 停托管，证书还是 `*.pythonanywhere.com`） |
| 40 | Rating charts | https://ratings.aoe2.se/ | 200 | 玩家/队伍 ELO 在总体分布里的位置；combo = √(RM² + TRM²)；只算近 28 天有局且总场次 ≥10 | **活跃**：`__NEXT_DATA__` 里 timestamp=1794106482661（2026-11-08），**94563 名玩家、中位 1015、最高 2996** |
| 41 | Civilisation 1v1 Performance | https://gowerc.github.io/aoecps/outputs（+ github.com/gowerc/aoecps） | **404 ×2** | 文明 1v1 表现统计 | **双死**：页面 "Site not found"，仓库也不存在；作者名下只剩 age-of-statistics / cran-images / diffdf / dotfiles |
| 42 | AOE2 Civ Overlap | https://docs.google.com/spreadsheets/d/1zMp6tkaJOR12xApt7F4UT3Rkm7bx3Y2o_dl41qfjmHA | 200 | 文明两两相似度（共有 / 缺失的非独特单位与科技占比） | 静态表 |
| 43 | Civilization Matchups | https://bookdown.org/gmcirco42/aoe_bayes/aoe_bayes.html | 200 | 用贝叶斯给 1v1 对位建模的一本在线书 | 静态 |
| 44 | AoE Companion | https://aoecompanion.com/stats | 200 | 当前版本哪些文明最强 | 同 #2 |

### 2.6 Websites / Guides（7）

| # | 名称 | URL | 状态 | 是什么 | 维护 |
|---|---|---|---|---|---|
| 45 | Build order guide | https://buildorderguide.com → `www.` | 200（1 跳） | build order 库 + uptime 计算（Builds / Uptime / Builder / Login） | 动态加载，活跃 |
| 46 | AoE2 Guide | https://aoe2.guide/ | 200 | build order + 文明概览 | **自报只有 4 个文明、10+ BO、167 术语、2 地图** —— 体量极小，AI 生成站点特征明显，参考价值低 |
| 47 | AoE Companion | https://aoecompanion.com/ | 200 | build 指南 + 单位克制 + 文明概览（Vue + vue-material + animate.css 4.1.0） | 活跃 |
| 48 | AoE Builds | https://www.aoebuilds.com/ | 200 | **商业付费教练站**（10-day training / Expert Videos / Pricing） | 活跃，收费 |
| 49 | PerfectTime | https://aoe2.arkanosis.net/pt/ | 200 | 完美上城时间计算：选 build order / 地图（Arabia、Arena、BF、Hideout）/ 文明 / loom / 卖石 | 作者自建 |
| 50 | AoE2 on Linux | https://aoe2.arkanosis.net/linux/ | 200 | 在 Linux 上跑 DE 的完整步骤 | **last updated 2026-01-01**，2025-05-10 补了 Kjir 的 CaptureAge 用法 |
| 51 | AoE2 on macOS | https://github.com/mnapoli/aoe2-de-macos | 200 | CrossOver 跑 DE（Big Sur 11.1+、Win10 bottle、DXVK、DirectX for modern games） | 148★ 但 **2023-08-17** 后未动，无 license |

### 2.7 Websites / User Generated Content（3）—— 本节对模组开发最关键

| # | 名称 | URL | 状态 | 是什么 | 维护 |
|---|---|---|---|---|---|
| 52 | Random Map Scripting Guide | https://docs.google.com/document/d/1jnhZXoeL9mkRUJxcGlKnO98fIwFKStP_OBozpr0CHXo | 200（5.9 MB） | "Definitive Random Map Scripting Guide"，RMS 权威指南 | 静态文档 |
| 53 | AoE2DE UGC Guide | https://ugc.aoe2.rocks/ | 200 | **自制场景 / 数据 mod / RM 脚本**三大块的指南；源码 Divy1211/AoE2DE_UGC_Guide **36★ / 2026-11-05 / GPL-3.0 / 无 release**；本地构建需 Python 3.6+ 与 mkdocs；Discord `rNa6cUC76W` | 活跃（自述 WIP，但一直在更） |
| 54 | AoE2 AI Scripting Encyclopedia | https://airef.github.io/ | 200 | AI 脚本百科：**全量 AI 命令**与**全量参数**清单；DE 为主，兼容 UserPatch / HD / CD（同一 AI 引擎） | 静态站，权威 |

### 2.8 Websites / Tournaments（4）

| # | 名称 | URL | 状态 | 是什么 | 维护 |
|---|---|---|---|---|---|
| 55 | Captains Mode | https://aoe2cm.net/ | 200 | 与 #18 **完全重复** | 同 #18 |
| 56 | AoE 2 Tournaments | https://aoe2tournaments.com/ | 200 | 赛事面板：upcoming / ongoing 分开、按时间排序、按 ELO 门槛过滤、主办方提交；另有 Images / Resources / Create Event（外链 Google Form 人工审核） | 源码 watermullins/Tournaments-Board 7★ / 2025-12-29 / 无 license |
| 57 | Tournament Elo | https://aoe-elo.com/ | 200 | 只算赛事对局的替代 ELO | **活跃**：56315 局 / 19049 系列 / 892 赛事，Update **Feb 22, 2026**，每小时从公开 API 同步 |
| 58 | Replay Packer | https://replaypacker.zeta-two.com/ | 200 | 整理、改名、打包 `.aoe2record` 提交赛事 | 源码已改名 ZetaTwo/aoe2-replay-packer（3★ / 2026-11-07） |

### 2.9 Websites / Wikis（2）

| # | 名称 | URL | 状态 | 是什么 |
|---|---|---|---|---|
| 59 | Fandom | https://ageofempires.fandom.com/wiki/Age_of_Empires_II:Portal | 403 "Just a moment..." | 官方 wiki 社区，内容最全，**只是挡爬虫** |
| 60 | liquipedia | https://liquipedia.net/ageofempires/Main_Page | 403 "Verify you are human" | 赛事 / 选手维基，**只是挡爬虫** |

### 2.10 Websites / Communities（4）

| # | 名称 | URL | 状态 | 是什么 |
|---|---|---|---|---|
| 61 | r/aoe2 | https://www.reddit.com/r/aoe2/ | 200（8.4 KB 骨架，JS 渲染） | 最大社区 |
| 62 | AoEZone | https://www.aoezone.net/ | 200 但落到 `.stile/challenge?rung=js&band=suspect` | 老牌论坛，**反爬挑战页**，人肉可过 |
| 63 | Official AoE forums | https://forums.ageofempires.com/ | 200（327 KB） | 官方论坛 |
| 64 | Siege Engineers | https://aoe2.se/ | 200（302 → **siegeengineers.org**） | 「围绕 AoE2 电竞的开发集体」—— 本列表一半工具的产出方 |

### 2.11 Websites / Blogs（1）

| # | 名称 | URL | 状态 | 是什么 |
|---|---|---|---|---|
| 65 | Age of Notes | https://ageofnotes.com/（+ RSS `/feed/` 200） | 200 | WordPress 博客，**但功能远超博客**：AoE2 Tech Tree、**SLD Extractor（在线 SLD 拆图）**、**DERM Tool**、Graphics Fix、Campaign Fix、AoE2 Switcher；英 / 法 / 德三语 |

> 本条的 SLD Extractor 与 DERM 是与本工作区最接近的外部工具（`aoe2-de-sprites` 技能正好处理 `.sld`），但只在线，不能进离线管线。

### 2.12 Websites / Information（2）

| # | 名称 | URL | 状态 | 是什么 |
|---|---|---|---|---|
| 66 | AoE2 Glossary | https://www.forgottenempires.net/strategy/aoe2-glossary | 200 | 官方工作室（Forgotten Empires）的术语表，写给新玩家 |
| 67 | Names, Abbreviations and Acronyms | https://docs.google.com/spreadsheets/d/1EX_2Cmem6fj4z_x2WWR0-g6Ljt6CKNewO_xk9_2EJLg | 200 | 全量缩写表 |

### 2.13 Programs（6，含 1 条无链接）

| # | 名称 | URL | 状态 | 是什么 | 维护 |
|---|---|---|---|---|---|
| 68 | CaptureAge | https://captureage.com/ | 200 | 观战客户端 + 数据 overlay | 自述「从 AoE 社区长出来，现在提供 AAA 级外包开发服务」——已转型工作室，产品仍在 |
| 69 | DE Replays Manager | https://github.com/gregstein/DE-Replays-Manager | 200 | 管理 DE 回放（C#） | 37★ / 2025-09-07 / GPL-3.0 / 1.6.2 |
| 70 | Wololo Downgrader | https://cyanide-aoe2.github.io/wololo-downgrader/ | 200 | 降版本以便看旧补丁的录象 | 6★ / **2021-05-07** / Python；页面有重要声明：**被 Windows Defender 报 `Trojan:Win32:Fuerboos.E!cl`，作者说明是 PyInstaller 打包导致** |
| 71 | AoE2 DE Patcher | https://github.com/DJSchaffner/aoe2de_patcher | 200 | 同上（降版本看旧录象） | **28★ / 2026-11-06 / GPL-2.0 / v3.3 —— 全表最活跃的桌面程序**；用 badge 动态读 `remote/patches.json` 的 `$.patches[-1:].version` 显示支持的版本，另有 `steam-manifest-watch.yml` 盯 Steam manifest |
| 72 | SenseiDE | https://github.com/gregstein/SenseiDE | 200 | 给 DE 做「性能释放 / 优化」 | 52★ / **2022-04-20** / MIT / 3.0 → **三年未动，已不可用于当前版本** |
| 73 | **Advanced Genie Editor** | **无 URL** | — | 查看 / 编辑游戏数据；README 明说随游戏自带：`Tools_Builds\AdvancedGenieEditor3.exe` | 随游戏更新；本工作区已有 `AdvancedGenieEditor20261022x86/` 与专题分析文档 |

> 第 73 条是全表唯一没有链接的条目，也是**唯一直接改 DAT 的官方工具**，却是列表里最不起眼的一行。

### 2.14 Mods（2）

| # | 名称 | URL | 状态 | 是什么 |
|---|---|---|---|---|
| 74 | Mod Directory | https://mods.aoe2.se/ | 200（curl 永远只给 412 字节壳，**必须 JS 渲染**） | Siege Engineers 做的 DE mod 索引：**61832 个 mod**，16 个类别（AI / Campaign / Data Mod / Graphics / Movie / Music / Random Maps / Scenarios / Sounds / Speech / Taunt / Terrain / Menu Background / UI / Text / Other）+「排除 civbuilder mod」+ Compact View + 按 Created / Updated 排序；每条给官方 `ageofempires.com/mods/details/<id>` 与 `cdn.ageofempires.com` 直链 zip；源码 SiegeEngineers/mod-directory 3★ / 2025-08-31 / MIT / Svelte |
| 75 | Interactive Build Order Guide | https://mods.aoe2.se/2359 | 200（需 JS） | mod 详情：20 个教学场景、文字 + 语音分步、A+~F 评分，语音由 ZeroEmpires 配音，作者 Cicero7800 |

### 2.15 Smartphone apps（2）

| # | 名称 | URL | 状态 | 是什么 |
|---|---|---|---|---|
| 76 | AoE 2 Database | https://play.google.com/store/apps/details?id=com.aoedb | 200（og:title "AoE 2 Database - Apps on Google Play"） | Android 版数据查询（网页版 #11 已死，App 还在） |
| 77 | AoE II Companion | https://aoe2companion.com/ | 200 | Android + iOS |

### 2.16 Games（3）

| # | 名称 | URL | 状态 | 是什么 |
|---|---|---|---|---|
| 78 | AoE 2 Database | https://play.google.com/store/apps/details?id=com.aoedb | 200 | **与 #76 完全同一 URL**，本节描述却是 "quizzes on Android" —— 列表内归类冲突 |
| 79 | AoE2Grid | https://aoe2grid.robomeow.org/ | 200 | 每日 3×3 猜谜（实测已到 Board #569，说明每天在推进） |
| 80 | AoE2Win | https://aoe2.win/ | 200 | 社区出题的十题一局测验，有 XP 与段位，免账号 |

### 2.17 Streaming tools（2）

| # | 名称 | URL | 状态 | 是什么 |
|---|---|---|---|---|
| 81 | AoE II Companion API | https://www.aoe2companion.com/more/api | 200 | 给 Nightbot 的 `!rank` / `!match` 接口文档 |
| 82 | RTS Overlay | https://github.com/CraftySalamander/RTS_Overlay | 200 | 把 build order 叠在游戏上（单屏可用），手动按键 / 热键 / 计时推进 | **113★ / 2026-10-31 / GPL-3.0 / 2.16.0**；README 明写 **"RTS Overlay does not interact with the game (no screen analysis, no controller interaction)"** —— 不是外挂 |

### 2.18 Programming tools（7）—— 真正的技术底座

| # | 名称 | URL | 状态 | 是什么 | 维护 |
|---|---|---|---|---|---|
| 83 | mgz / aoc-mgz | https://github.com/happyleavesaoc/aoc-mgz | 200 | Python3 录象解析：`.mgl / .mgx / .mgz(UP1.4/1.5) / .aoe2record(HD≥4.6) / DE`；fast（约 80–90% 字段）与 full 两套 parser，summary 层自动 fast→full 回退 | **235★ / 2026-10-19 / MIT / 1.8.26 —— 全表最活跃的库** |
| 84 | genie-rs | https://github.com/SiegeEngineers/genie-rs | 200 | Rust 读写 AoE1/2 文件；examples: `extractcpx` / `convertscx`（HD→WololoKingdoms）/ `displaylang` / `wolololang` | 18★ / **2023-04-04** / GPL-3.0 / v0.5.0 / MSRV 1.64 |
| 85 | genieutils | https://github.com/sandsmark/genieutils | 200 | C++ 读写 Genie 引擎数据：`empires*.dat`、`genie*.dat`、drs / slp / smp / smx / blendomatic / pal、scn / scx / cpx / bln / sin / wav、`language*.dll`；命令行 `cpxtool / genie-datextract / drstool / pcriotool / genie-bindiff` | 29★ / 2024-06-02 / LGPL-3.0；README 自述 API 会变、建议先备份 |
| 86 | AoE2 Scenario Parser | https://ksneijders.github.io/AoE2ScenarioParser/ | 200（页面正文只有 "Document"，真内容在 GitHub Pages 文档里） | Python 库，`pip install AoE2ScenarioParser`，可编辑**每个版本**的 `.aoe2scenario` | **105★ / 2026-11-05 / GPL-3.0 / Python / 3 open issues —— 活跃** |
| 87 | aoe2rec | https://github.com/aoe2ct/aoe2rec/ | 200 | Rust（+ WASM + Python）读写 DE 录象，明显改编自 aoc-mgz | 11★ / 2026-10-05 / MIT / `aoe2rec-py-v0.1.24` |
| 88 | McMinimap | https://github.com/UnluckyForSome/McMinimap → `AOE2-McMinimap-py-legacy` | 200（1 跳改名） | 从存档生成小地图 | **archived=true**；README 明说被 `aoe2-mcminimap` 取代，本仓只剩 Python/Pillow 老实现兼 parity oracle |
| 89 | AoE2 minimap generator | https://github.com/Marfullsen/AoE2-minimap-generator | 200 | 从存档生成小地图（Python 3.7.7 / Pillow 12.3.0 / **mgz 1.8.51**，即依赖 #83） | 13★ / 2026-07-18 / 无 license / v1.0 |

### 2.19 YouTube channels（20）

全部 200，且能从页面内嵌 JSON 读出频道真名，确认没换人。脚本里 "VIDEO_GONE" 为误报（页面文本含 "Video unavailable" 字样即命中），频道与视频实际都在。

| 分类 | 频道 | 状态 / 真名 |
|---|---|---|
| Theory | Spirit Of The Law | 200 / Spirit Of The Law |
| Theory | Empirant_AOE | 200 / Empirant_AOE |
| Theory | T-West | 200 / T-West |
| Theory | Hjörleif | 200 / Hjörleif - Age of Empires 2 |
| Theory | TechnoFeudGamingTV | 200 / **现名 TFGTV - AoE2** |
| Theory | HumzaCrumza | 200 |
| Theory | Poop Lord | 200 |
| Casting | Hera | 200 / Hera - Age of Empires 2 |
| Casting | T90 | 200 / T90Official - Age Of Empires 2 |
| Humor | Parsa Animations | 200（`/c/Parsaw` 旧式链接仍可用） |
| Interviews | Kings & Plebeians | 200 / Masmorra_AoE |
| Interviews | Bored With Nelly | 200 |
| Music | Gonza Muñoz | 200 / Gonza Muñoz |
| Music | Alex Heflin | 200 / video `ilFEmE_9lB0` = "Shamburger - Age of Empires II [Acoustic] (ft. insaneintherainmusic)" |
| Music | Jon V Audio | 200 / video `sKuAcFYmJ9s` = "choppa.wav - AoE2 remix, ONLY using game sounds" |
| Music | 4Hardy | 200 / video `q879j3ydfw8` = "MBL - Auto Everything (Official Video)"，带播放列表 `PLWq0TTc6_9JjaE6XRZGfATd1H6PsvP_8D` |
| History | Armchair Saurus | 200 |
| History | Tiramis | 200 |

> 列表里 Twitch channels 章节**只有标题没有内容**，是空的。

### 2.20 Similar games（3）

| # | 名称 | URL | 状态 | 是什么 | 维护 |
|---|---|---|---|---|---|
| 108 | openage | https://openage.sft.mx/ → **openage.sft.lol** | 200（1 跳，**域名已换**） | 自由 / 开源 RTS 引擎，复刻 AoE 机制；C++20 / OpenGL-GLSL / Python / Qt / CMake | 活跃 |
| 109 | freeaoe | https://github.com/sandsmark/freeaoe | 200 | 能「跑」AoE2 的自由引擎（也能加载 SW:GB），需原始数据文件（可用试玩版数据） | **242★ / 2022-12-08 / GPL-3.0 / release "1" —— 全表第二高星但已停更近四年** |
| 110 | 0 A.D. | https://play0ad.com/ | 200 | 古代战争题材的自由游戏 | 活跃（与 AoE2 无技术关系） |

---

## 3. 死链 / 半死 / 停更 / 改名 四张清单

### 3.1 真死（建议从列表删除或标注）

| 条目 | URL | 证据 |
|---|---|---|
| aoestats | https://aoestats.io/ | 522 Connection timed out（web_fetch 与 Playwright 均是），源站已无响应 |
| AoE Pulse | https://www.aoepulse.com/ | 404 "Coming Soon"，证书 altname `*.pythonanywhere.com`，托管已终止 |
| AoE2 Analyzer | https://aoe2.up.railway.app/ | 404 |
| Civilisation 1v1 Performance | https://gowerc.github.io/aoecps/outputs | 页面 404，且 https://github.com/gowerc/aoecps 仓库 404 —— **链接与源码双死** |
| AoE 2 Database（网页版） | https://www.aoe2database.com/ | **530 Error 1016 Origin DNS error**，源站 DNS 记录已删；App 版（#76）仍活 |

### 3.2 域名在、业务下线

| 条目 | 证据 |
|---|---|
| aoe2recs / Spectator Dashboard | 页面正文："**Spectator Dashboard Temporarily Offline**" |

### 3.3 停更 ≥1 年（内容已与当前版本脱节）

| 条目 | 最后实质更新 | 后果 |
|---|---|---|
| Wololo rating distribution | 页面写 **2023-05-21** | 分母（活跃玩家）与中位数已严重过时 |
| aoe-twools | 源码 **2023-12-24**，作者自述跟不动更新 | 缺新文明 |
| SenseiDE | **2022-04-20** | 对当前 DE 版本无效 |
| freeaoe | **2022-12-08** | 仅作技术参考 |
| aoe2calc | 明文 "does not support DE yet" | 只适用 HD / AoC |
| McMinimap | archived，改名 `*-py-legacy` | 已被后继项目取代 |
| AoE Unit Counters（vercel） | 源码 **2022-03-12** | 数值过时 |
| aoe2-de-macos | **2023-08-17** | CrossOver 步骤可能已变 |
| aoe2map | **2024-11-12** | 仍可用，13 open issues 无人处理 |
| genie-rs | **2023-04-04** | 仍可用，但已落后于 DE 新版格式 |
| wololo-downgrader | **2021-05-07** | 基本被 aoe2de_patcher 取代 |

### 3.4 已改名 / 已换域（列表未跟进，点了会 302）

| 列表里的写法 | 现在的真身 |
|---|---|
| https://aoe2.se/ | https://siegeengineers.org/ |
| https://aoe2lobby.com/ | https://aoe2lobby.com/lobby |
| https://buildorderguide.com | https://www.buildorderguide.com/ |
| https://aoe2companion.com/leaderboard | https://www.aoe2companion.com/(main)/statistics/leaderboard |
| https://aoe2-de-tools.herokuapp.com/`civ-ranking.html` | `/civ-ranking/`（`villagers-required.html` 同理） |
| https://frcp.net/civexplorer/ | **https://civexplorer.net/**（老页只剩一句 "Moved to new domain"） |
| https://openage.sft.mx/ | **https://openage.sft.lol/** |
| https://tiny.cc/CivilizationTool | app.powerbi.com 的 Power BI 报告 |
| github.com/UnluckyForSome/McMinimap | github.com/UnluckyForSome/AOE2-McMinimap-py-legacy |
| github.com/ZetaTwo/aoe2replaypacker | github.com/ZetaTwo/aoe2-replay-packer |
| youtube.com/@TechnoFeudGamingTV | 现频道名 TFGTV - AoE2 |
| aoe2cm 的源码（列表未给） | SiegeEngineers/aoe2cm2（不是旧的 aoe2cm） |
| aoe2techtree 的主仓（列表未给） | SiegeEngineers/aoe2techtree（284★），非 HSZemi/aoe2techtree（0★） |

### 3.5 列表自身的结构问题

1. **重复条目**：Captains Mode 出现 2 次（#18、#55）；AoE II Companion 出现 **5 次**（#2、#44、#47、#77、#81）；AoE 2 Database 出现 **3 次**，其中 #78「Games / quizzes on Android」与 #76 是**同一个 Play Store URL**，描述却不同 —— 归类错误。
2. **唯一无链接的条目**（#73 Advanced Genie Editor）恰恰是改数据的官方工具，普通读者会以为漏了链接。
3. **Twitch channels 章节为空**（只有标题）。
4. **只增不删**：最近三次提交是 "Add Civ Explorer"(2026-10-25) / "Add AoE2Win"(2026-04-01) / "Add AoE2 Replay Viewer"(2026-03-22)，全是新增；上述死链一个都没清。
5. README 里 `[an issue](.../pulls)` 指向的是 pulls 页而非 issues 页（小 bug）。

---

## 4. 用户截图那批收藏夹（13 条）核验

这些**不在** awesome list 里，是独立的收藏夹条目，实测全部可达（除一条 curl 证书问题）：

| 名称 | URL | 状态 | 是什么 |
|---|---|---|---|
| 帝国时代II 文明 | https://seicing.com/html/aoe2/index-aoe2.html | 200（31 KB） | 中文文明资料站，非官方 |
| 帝国时代II: 终极版（Fandom） | https://ageofempires.fandom.com/wiki/Age_of_Empires_II:_Definitive_Edition | 403（CF 验证） | 同 #59 |
| AoE2DE UGC 指南 | https://ugc.aoe2.rocks/ | 200 | 同 #53 |
| 《帝国时代2》AI 脚本百科全书 | https://airef.github.io/ | 200 | 同 #54 |
| Document（ScenarioParser） | https://ksneijders.github.io/AoE2ScenarioParser/#/ | 200 | 同 #86 的文档根 |
| AOE2DE-FontGenerator | https://github.com/sgjsakura/AOE2DE-FontGenerator/tree/master | 200（curl 得 000 是证书问题，requests 直连 226 KB） | **30★ / 2024-01-03 / MIT / C#**：换 DE 字体（`key-value-modded-strings` 那套）的生成器，本工作区做 UI 文本替换时会用到 |
| Mods All（官方） | https://www.ageofempires.com/mods/ | 200（172 KB） | 官方 mod 站 |
| 3DM 字体帖 | https://bbs.3dmgame.com/thread-6496818-1-1.html | 200（119 KB） | 中文决定版字体替换教程 |
| Openage v0.4.0 中文文档 | https://simonsan.github.io/openage-webdocs/sphinx/index.html | 200（313 KB） | openage 中文文档 |
| AoK Heaven · AGE 下载 | https://aok.heavengames.com/blacksmith/showfile.php?fileid=11058 | 200（22 KB） | Advanced Genie Editor 的第三方下载页（版本旧，优先用游戏自带） |
| 帝国时代 II 科技树（中文） | https://aoe2techtree.net/?lng=zh#Chinese | 200 | 同 #8，带 `?lng=zh` |
| AOE2Lobby | https://aoe2lobby.com/lobby | 200 | 同 #36 |
| awesome-aoe2 | https://github.com/Arkanosis/awesome-aoe2 | 200 | 本次审计对象（173★ / CC0-1.0 / 7 open issues） |

> 这批里**真正有工程价值的只有两条**：`AOE2DE-FontGenerator`（字体 / 字符串替换的现成实现）和 `aoe2techtree ?lng=zh`（中文名映射来源）。其余是资料 / 社区页。

---

## 5. 与本工作区（aoe2mod / AGE / DAT / SLD / UI / AI+XS）的关联度排序

本工作区技术栈：`empires2_x2_p1.dat` 读写、`.sld` 精灵读写、UI 贴图与字符串替换、`.per` / `.xs` 脚本、Tauri 桌面壳 + 本地 Python 后端。按「能不能直接拿来用」排：

### 第一档：直接可用 / 直接对标

| 资源 | 为什么 |
|---|---|
| **#73 Advanced Genie Editor**（游戏自带 `Tools_Builds\AdvancedGenieEditor3.exe`） | 唯一官方 DAT 编辑器。本工作区已有 `AdvancedGenieEditor20261022x86/` 与 `AGE-20261022x86-全面解析.md` / `AGE-AI与XS-全面解析.md`，AGE 就是我们的字段真值来源 |
| **#85 genieutils**（C++ / LGPL-3.0） | `empires*.dat` / `genie*.dat` / slp / drs / scn / language dll 全套读写 + `genie-bindiff`。写 DAT 时当**交叉校验器**：同一份数据用 genieutils 读一遍、和自家 parser 字段对齐，能抓出偏移 / 宽度错误 |
| **#86 AoE2ScenarioParser**（Python / 105★ / 2026-11-05） | `.aoe2scenario` 全版本读写。做场景类 mod 或生成教学场景时，比自己啃二进制快一个数量级 |
| **#83 aoc-mgz**（Python / 235★ / 2026-10-19） | 回放 / 存档解析的事实标准；`mgz 1.8.51` 已是生态公共依赖（#89 就依赖它）。读对局数据、验证 mod 在实局里的表现走这条 |
| **#53 AoE2DE UGC Guide** + **#52 RMS 指南** | 数据 mod / 场景 / RMS 三条产线的**规范文档**。做 mod 打包结构、`resources/_common` 路径、RMS 语法时先查这里，能少踩「文件位置对但游戏不认」的坑 |
| **#54 AI Scripting Encyclopedia** | `.per` 命令与参数全量表；与 `aoe2-de-ai-scripting` 技能互补（那个讲结构，这个讲全集） |

### 第二档：数据 / 结构参考

| 资源 | 用途 |
|---|---|
| **#13 Halfon** | 按版本（DE 188329 / ROR / HD / WK）分列的数值表，含 `ID / Type / Class / LOS / ATK / MA / PA / GC` —— **校验自家 DAT 解析结果时最方便的对照表** |
| **#8 aoe2techtree**（284★） | 元数据由 genieutils-py 提取，说明它的 JSON 与我们 DAT 解析同源；中文科技树 `?lng=zh` 可作本地化名对照 |
| **#42 AOE2 Civ Overlap** / **#16 Counters matrix** | 文明独有 / 共有单位科技的现成矩阵，做「63 文明复制规则」校验时能快速判断某单位该不该在某文明出现 |
| **#40 ratings.aoe2.se** | 唯一还活着的统计站，`__NEXT_DATA__` 里直接给 9.4 万玩家的分数 JSON，可当「大规模外部数据 → 结构化」的样例 |

### 第三档：工具链 / 工作流可借鉴

| 资源 | 借鉴点 |
|---|---|
| **#74 Mod Directory**（Svelte / MIT） | 官方 mod 库的索引方式：`ageofempires.com/mods/details/<id>` + `cdn.ageofempires.com` 直链 zip。要抓 mod 元数据、给自家工坊做「在线 mod 浏览」，它的字段结构就是模板 |
| **#71 aoe2de_patcher** | **本表最值得抄的工程实践**：badge 动态读 `remote/patches.json` 的 `$.patches[-1:].version` 显示「支持到哪个游戏版本」，加一个 `steam-manifest-watch.yml` 工作流盯 Steam manifest —— 正是「游戏一更新就失效」类工具该有的自监控 |
| **#65 Age of Notes 的 SLD Extractor / DERM** | 在线 SLD 拆图与 DERM 工具。做 `.sld` 校验时可当第二意见（但只在线，不能进离线管线） |
| **#82 RTS Overlay** | README 里「不读屏、不注入、手动推进」是**合规 overlay 的边界声明写法**，我们做 overlay 类功能时可直接引用这个口径 |
| **#37 liouh.com/aoe2 回放查看器** | 三平台存档路径写法（含 CrossOver `compatdata/813780`）可直接抄进我们的「打开存档」对话框 |

### 第四档：与本工作区无关（玩家侧）

Profiles 全部 7 条、Civilization pickers 全部 5 条、Tools 里的计算器 / 模拟器 / lobby / hotkey（#26–#36）、Statistics 大部分、Guides 全部、Tournaments 全部、Wikis / Communities / Blogs、Smartphone / Games、全部 20 个 YouTube 频道、Similar games —— 约 80 条。它们的价值是「社区在哪、玩家在意什么」，不是技术参考。

---

## 6. 建议动作

### 6.1 如果目标是给这个列表提 PR（作者未 archive，CC0 授权，门槛低）

1. 删除 5 条死链：#38 aoestats、#39 aoepulse、#31 aoe2.up.railway.app、#41 aoecps（页 + 仓库）、#11 aoe2database 网页版。
2. 把 #23 aoe2recs 标注为「服务暂停」或移出 Tools。
3. 修 6 处跳转：aoe2.se→siegeengineers.org、frcp.net/civexplorer→civexplorer.net、openage.sft.mx→openage.sft.lol、buildorderguide→www、aoe2lobby→/lobby、aoe2cm 源码指到 aoe2cm2。
4. 去重：Captains Mode ×2、AoE II Companion ×5、AoE 2 Database ×3（#78 属归类错误）。
5. 给 #73 AGE 补一条说明性链接（AoK Heaven 的下载页或官方 docs），避免「唯一无链接条目」的观感。
6. 清空或删除空的 Twitch channels 章节。
7. 修 `[an issue](.../pulls)` 指向错误。

### 6.2 如果目标只是「给本工作区建一份可用的外部资料索引」

按第 5 节第一档 / 第二档建 9 条书签即可：AGE、genieutils、AoE2ScenarioParser、aoc-mgz、UGC Guide、RMS Guide、AI Scripting Encyclopedia、Halfon、Mod Directory。

### 6.3 已核实但**不要**依赖的东西

- `aoestats.io` 的胜率数据（已死）—— 改用 `aoecompanion.com/stats` 或 `ratings.aoe2.se`。
- `tlgs/wololo` 的 ELO 分布（2023 年的快照）—— 用 `ratings.aoe2.se` 现算（它有实时 JSON）。
- `aoe2database` 网页版（DNS 没了）—— 数值以 AGE 直读 DAT 为准。
- `SenseiDE`（2022 停更）—— 不要装，对当前版本无意义。
- `wololo-downgrader` 的 exe —— Defender 会报 `Trojan:Win32:Fuerboos.E!cl`（作者说是 PyInstaller 误报），要用就从源码跑；功能上已被 `aoe2de_patcher` 取代。

---

## 附录：本次审计的原始数据

全部落在 `_probe/_tmp/`（临时文件区），可复现：

| 文件 | 内容 |
|---|---|
| `awesome.md` | README 原文（14 KB / 13776 字符 / 114 处 http） |
| `parse_awesome.py` → `entries.json` | 111 条结构化条目（section / name / url / extra / note） |
| `urls.txt` | 116 个唯一 URL |
| `probe_links.py` → `probe1.json` | 每条的 status / final / title / ms / bytes / ctype / hops |
| `gh_meta.py` → `github.json` | 20 个仓库的 stars / forks / archived / pushed / license / release |
| `describe.py` → `describe.json` | 每页 meta description + h1 |
| `get_readmes.py` → `readmes.json` | 各仓库 README 正文 |
| `yt_check.py` → `youtube.json` | 20 个 YouTube 目标的频道名 / 视频标题 |
| `snippets.py` | 30 个重点站点的可见正文前 520 字 |

复跑命令（本机只有 `python`，无 `py` / `python3`，路径必须是绝对路径）：

```bash
C:/Users/26913/AppData/Local/Python/bin/python.exe -X utf8 -u _probe/_tmp/probe_links.py
```

解析脚本里踩过的两个坑（已修）：

1. 条目前无 `[...](...)` 链接时（#73 "Advanced Genie Editor" 这种纯文本行）会 IndexError —— 需先判 `if not links:` 再走 text 分支。
2. 只用 `## ` 作为章节切分会把 Programs / Mods 等 `# ` 一级章节吞掉 —— 需三级 top / h1 / h2 切分（第一个 `# ` 是标题，之后到 `# Contents` 的 `# ` 才是 h1）。
