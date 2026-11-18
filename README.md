<p align="center">
  <img src="docs/screenshots/banner.png" alt="模组工坊" width="820">
</p>

<p align="center">
  <a href="https://github.com/198agk/AoE2DEModWorkshop/releases/latest"><img src="https://img.shields.io/github/v/release/198agk/AoE2DEModWorkshop?style=flat-square&color=2dd4bf&label=%E6%9C%80%E6%96%B0%E7%89%88" alt="最新版"></a>
  <img src="https://img.shields.io/badge/%E5%B9%B3%E5%8F%B0-Windows%2010%20%2F%2011-0078d4?style=flat-square&logo=windows" alt="平台">
  <img src="https://img.shields.io/badge/Python-3.12%20%E5%86%85%E7%BD%AE-3776ab?style=flat-square&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/%E8%AE%B8%E5%8F%AF-PolyForm%20NC%201.0.0-green?style=flat-square" alt="许可">
</p>

<p align="center">
  <b>用一句中文，改一份数据，生成一个能装进游戏的模组。</b>
</p>

<p align="center">
  <a href="#界面预览"><img src="docs/screenshots/home.png" alt="模组工坊首页" width="88%"></a>
</p>

## 安装

从 [Releases](https://github.com/198agk/AoE2DEModWorkshop/releases/latest) 下安装包，双击，下一步。
装到 `%LOCALAPPDATA%\Programs\AoE2ModWorkshop`，自带 Python 3.12，不需要管理员权限，
卸载在「设置 → 应用」里。不想装就下免安装包，解压后双击目录里的 `AoE2 DE Mod Workshop.exe`。

| 文件 | 怎么用 |
| --- | --- |
| `AoE2DEModWorkshop-1.0.0-setup.exe`（273 MB） | 双击安装 |
| `AoE2DEModWorkshop.zip`（351 MB） | 解压，双击 `AoE2 DE Mod Workshop.exe` |

装好之后还要在游戏里自己选一次，否则改动不生效：进「单人游戏 → 创建游戏」，在设置画面里找到「数据模组：」那一项，从下拉框里挑本软件生成的那个。它不是「模组」界面里的开关，别在那里找。

这个仓库装的是**源码**，不是给人拿去跑的东西：要用工坊请用上面两个文件。

## 功能

| | |
| --- | --- |
| **一句话改模组** | 「把不列颠村民的血量改成 1000」→ 预览 → 生成并安装。15 个意图，一句话里可以有好几件事 |
| **逐字段编辑器** | 13 个页签、约 116 万个数字，`.dat` 里每一个字段都能点进去改 |
| **多条少条** | 复制一条单位记录、追加一项科技，也能删回去 |
| **改完能验证** | 预览写清哪张表第几条、原值 → 新值、动了几个字节；救不回来的句子当场拒绝 |
| **一键装进游戏** | 写出模组目录、装进玩家 profile、勾上开关 |
| **补丁后一键适配** | 自带 54 份官方历史数据，可自动更新模组（测试版） |
| **读回别人的模组** | 打开一个社区模组，看它改了什么、还能不能救 |
| **AI 说人话** | 接任意 OpenAI 兼容端点，把愿望换成这个工具认得的句子 |

## 界面预览

| | |
| --- | --- |
| **首页** | **能做的事** |
| [![首页](docs/screenshots/home.png)](docs/screenshots/home.png) | [![能做的事](docs/screenshots/intents.png)](docs/screenshots/intents.png) |
| **模组一览** | **逐字段编辑器** |
| [![模组](docs/screenshots/mods.png)](docs/screenshots/mods.png) | [![编辑器](docs/screenshots/editor.png)](docs/screenshots/editor.png) |
| **命令面板** | **科技树** |
| [![命令面板](docs/screenshots/card.png)](docs/screenshots/card.png) | [![科技树](docs/screenshots/tree.png)](docs/screenshots/tree.png) |
| **界面语言** | **关于** |
| [![语言](docs/screenshots/lang.png)](docs/screenshots/lang.png) | [![关于](docs/screenshots/about.png)](docs/screenshots/about.png) |

## 能做什么（15 个意图）

```
把不列颠村民的血量改成 1000
照织布机做一个新科技，叫铁匠学徒的手艺，研究时间 10，放在第 3 格
把锻造和步兵鳞甲做成只能研究其中一个
```

| 说人话 | 意图 | 写哪里 |
|---|---|---|
| 改血量 / 攻击 / 护甲 / 移速 / 视野 | `unit.stat` | `.dat` |
| 改某单位对某类目标的攻击或护甲 | `unit.attack_class` | `.dat` |
| 改单位造价 | `unit.cost` | `.dat` |
| 改科技研究时间 / 造价 | `tech.research_time`、`tech.cost` | `.dat` |
| 改科技效果里的一条命令 | `tech.effect` | `.dat` |
| 让某文明能 / 不能再造某单位 | `unit.availability` | 科技树 JSON + `.dat` |
| 让某文明能 / 不能再研究某科技 | `tech.availability` | 科技树 JSON + `.dat` |
| 换掉单位的造型 | `unit.sprite` | 松散 `.sld` |
| 给单位画一张新图 | `unit.art` | 松散 `.sld` |
| 照现成单位做一个新单位 | `unit.create` | `.dat` + 文本 mod |
| 几项科技只能研究其中一个 | `tech.toggle_group` | JSON + `.dat` |
| 做一项游戏里没有的科技 | `tech.create` | `.dat` + 文本 mod |
| 开局时把某单位换成另一个 | `unit.replace_on_map` | `objreplacement.json` + `.dat` |
| 把单位挪到命令卡另一格 | `unit.card_move` | `.dat` |

## 编辑器页签

| 页签 | 记录数 | 字段 |
|---|---|---|
| 单位 | 挑选器 1,651 个；文件里 136,861 条（63 文明各一份） | 190 |
| 科技 | 1,510 条 | 34 |
| 图形 | 20,883 条 | 26 |
| 音效 | 930 条 | 5 |
| 效果 | 1,500 条 / 55,500 个数字 | 2 + 命令 5 槽 |
| 地形 | 200 条 | 19 |
| 通行 | 54 条 | 670 |
| 颜色 | 16 条 | 9 |
| 单位任务 | 2,329 条 | 32 |
| 文明 | 63 条 | 608 |
| 地图块 | 1 条 | 25 |
| 全局数值 | 7 条 | 1 |
| 科技树 | 550 条 | 44 到 66 |

## 做不到什么

- **「变灰」做不到**，禁科技的表现是按钮消失。
- **新科技不进科技树面板**，它出现在研究卡上。
- **改不动渲染器**，能换的是磁盘上的图片与布局文件。
- **同一文件夹里 `.dat` 与 `widgetui` 只有一个生效**，工具会拆成两个 mod，两个都要勾上。

每条的实测记录在 [RELEASE.md](RELEASE.md)。

## 使用须知

- 还在快速迭代，数值、造单位、造科技、生成模组已经实机走通。
- 有问题开 [issue](https://github.com/198agk/AoE2DEModWorkshop/issues)，带截图或录屏，说清在哪个页签。
- **它不会自己更新**，要新版就下新安装包覆盖，或「关于」页按「检查更新」。
- 不改游戏本体，改动写在本机 `.dat` 的副本上，卸载 = 删一个文件夹。
- 完全免费、完全开源。

## 开发

本软件借 AI 开发：方向和验收由人来做，模型是 **Deepseek-V4.1-Flash**。

需要 Python 3.10+。改完这样验：

```powershell
python -X utf8 -u '_probe\run_suites.py'    # 236 条快套件，约 100 分钟
python -X utf8 -u '_probe\run_long.py'      # 17 条长套件，约 2.8 小时
```

两条环境铁律：

1. `aoe2mod/dat/{parser,writer,locate}.py` 是 **vendored** —— 直接改无效，下次 `tools\sync_engine.py`
   会覆盖。要改就改 `_probe/datparse/` 与 `_probe/serializer/` 里的源，再跑一次同步。
2. 超过几句话的 Python 不要内联在 shell 里（here-string 会吞引号），写成 `.py` 再跑。

AI 那条口的地址、模型名和密钥在「设置」里填，也认三个环境变量：

```powershell
$env:AOE2MOD_AI_BASE  = 'https://api.openai.com/v1'
$env:AOE2MOD_AI_KEY   = 'sk-...'
$env:AOE2MOD_AI_MODEL = 'gpt-4o-mini'
```

**它只会把你说的话换成这个工具认得的句子**，不产生任何改动：句子仍然要过「读一下」那一关、
仍然要看预览能不能构建。配置只从环境变量读，项目不存任何 key。

## ☕ 请我们喝咖啡

如果 模组工坊 帮你省下了不少时间，不妨请开发者喝杯咖啡？

你的支持是我持续更新的最大动力！💖

<a href="https://afdian.com/a/RemonBo"><img src="https://img.shields.io/badge/%E5%9C%A8%E7%88%B1%E5%8F%91%E7%94%B5%E6%94%AF%E6%8C%81%E6%88%91-946ce6?style=for-the-badge&logoColor=white" alt="在爱发电支持我"></a>

## 许可

**可以**：私人使用、修改、分享、改自己的模组、视频展示、放进免费整合包。
**不可以**：任何商业用途 —— 收费下载、付费网盘、会员专享、付费整合包、企业生产使用。

正文是 **PolyForm Noncommercial License 1.0.0**，全文在 [LICENSE](LICENSE)。
二次发布须在 README 与产品「关于」页写明原作者与 <https://github.com/198agk>。

游戏素材不在许可范围内：本工具不包含、不分发游戏素材。

## 致谢

[genieutils](https://github.com/SiegeEngineers/genie-rs) 与社区版 Advanced Genie Editor。
