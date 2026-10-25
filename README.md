# 帝国时代 2 决定版 · 本地模组工坊

用一句中文，改一份数据，生成一个能装进游戏的模组。

```
把不列颠村民的血量改成 1000
照织布机做一个新科技，叫铁匠学徒的手艺，研究时间 10，放在第 3 格
把锻造和步兵鳞甲做成只能研究其中一个
```

这不是编辑器插件，也不改游戏本体：它在 `D:\Games\Steam\...\AoE2DE` 那份出厂数据上
另写一份 `.dat`，装成普通的本地模组。游戏更新后随时重建。

---

## 三十秒上手

**双击根目录里的 `启动模组工坊.cmd`。** 就这一步。

它会自己找 python（先找已知的 DSH 运行时，再找 `py` 启动器，最后才用 PATH 上的
`python` —— 那个可能是应用商店的存根，一试就弹商店），然后在**一个窗口里**打开工坊。
出错时窗口会停住并留下原因，不会一闪就没。

> 窗口（2026-10-25 起）：页面在一个原生窗口里开，没有地址栏、不能误点走。它用的
> 是本机的 Edge WebView2 运行时（这台机器上已确认 156.0.4314.42），不需要打包、
> 不需要构建。万一某个环境装不了 `pywebview`，它会自己退回浏览器并说明原因 —— 
> 「要窗口」和「能开」是两件事，退回时也会讲清楚。
> 想强制只要窗口（开不了就报错而不是退回），加 `--window`；想回到浏览器老行为，加 `--browser`。

想从命令行启动（或者要给参数）：

```powershell
cd 'D:\Software\AI\帝国项目'

# PATH 上的 python 是商店存根，必须用这个绝对路径
$py = 'C:\Users\26913\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'

& $py -X utf8 -u 'tools\run_ui.py'
```

窗口里显示的就是本机服务发出来的页面（默认随机端口，控制台会打印地址；想固定就加 `--port 7792`）。
在框里打一句中文 → 「读一下」→ 看预览 → 「生成并安装」。

**开局前必须在「创建游戏」界面的「数据模组：」下拉框里选中它** ——
不是「模组」界面，那个界面没有这个下拉框。

---

## 能做什么（13 个意图）

| 说人话 | 意图 | 写哪里 |
|---|---|---|
| 改血量 / 攻击 / 护甲 / 移速 / 视野 … | `unit.stat` | `.dat` |
| 改某个单位对某类目标的攻击或护甲 | `unit.attack_class` | `.dat` |
| 改单位造价 | `unit.cost` | `.dat` |
| 改科技研究时间 / 造价 | `tech.research_time`、`tech.cost` | `.dat` |
| 改科技效果里的一条命令 | `tech.effect` | `.dat` |
| 让某个文明能 / 不能再造某单位 | `unit.availability` | 科技树 JSON + `.dat` |
| 让某个文明能 / 不能再研究某科技 | `tech.availability` | 科技树 JSON + `.dat` |
| 换掉单位的造型（借别人的动画） | `unit.sprite` | 松散 `.sld` |
| 给单位画一张新图 | `unit.art` | 松散 `.sld` |
| 照现成的单位做一个新单位，选格子 | `unit.create` | `.dat` + 文本 mod |
| 把几项科技做成只能研究其中一个 | `tech.toggle_group` | JSON + `.dat` |
| 做一项游戏里没有的科技 | `tech.create` | `.dat` + 文本 mod |

一句话可以是几条改动（`村民血量改成 1000。弓箭手攻击力加 2`），会打进同一个 mod。

---

## 想要 AI 帮你写那句中文

设三个环境变量再启动 `tools\run_ui.py`，页面会多一个「问问 AI」按钮：

```powershell
$env:AOE2MOD_AI_BASE  = 'https://api.openai.com/v1'   # 任何 OpenAI 兼容端点
$env:AOE2MOD_AI_KEY   = 'sk-...'
$env:AOE2MOD_AI_MODEL = 'gpt-4o-mini'
```

**它只会把你说的话换成这个工具认得的句子**，不产生任何改动。句子仍然要过「读一下」
那一关、仍然要看预览能不能构建 —— 模型说错了，你看到的是同一句拒绝，而不是一次你
没法审的字节编辑。没配这三个变量时按钮不出现（一个只会失败的框比没有更糟）；配置只
从环境变量读，项目不存任何 key。

---

## 能做什么，以及**做不到**什么

**实机验证过**（不是推测）：改数值、改可用性（v17 印加城堡时代没有蔷琵侦察兵）、
新建单位（v26/v49 屏幕上看得到造得出）、新建科技（v49 城镇中心研究卡上出现）、
互斥科技组（v47 研究一个后另一个消失）。

**做不到，且原因已经量过**：

- **改不了游戏界面**。EXE 是纯 native（无 CLR 头），WPF 由游戏自己的渲染器解析；
  能换的是磁盘上的图片与布局文件，控件类集是封闭的。
- **图标层能写**（2026-10-23 做出来了）：`unit.create` / `tech.create` 都能带一张
  自己的图 —— 单位走 `Units` 段 + 未压缩 DDS，科技走 `Techs` 段 + PNG，两段的
  `materials.json` 是同一份所以要共享一次合并。出厂 0..999 / 0..312 确实是满的，但
  模组能往上加（已发布的三国 UI 模组把 Units 扩到 2148），而记录里那个字段是 i16。
  **已经在一局真游戏里画出来过**（2026-10-24，v85）：产品自己的 `build_bundle`
  + `install` 发出去的图标，出现在城镇中心的命令卡上，用的就是 `unit.create`
  自动分配的新槽（1000）—— v74 那次空框不是槽号问题，而是它把 `.dat` 与 `widgetui`
  放进了同一个文件夹（那个组合五次空框，拆成两个 mod 就画出来）。所以这条链的形状是：
  **一次 build 产出两个 mod，两个都要在模组界面里勾上**，缺界面那一半图标就不出现
  （页面与 manifest 都会这么说）。**还没量过的一次**：数据那一半重装之后、两半同时
  启用时图标是否仍然出现（每次实机都是「关游戏 → 装 → 开」，没有覆盖安装后的读数）。
- **新科技不进科技树面板**（它出现在研究卡上，不在树里）。
- **科技的成本改不了**（成本槽是逐字节重放的，写不进去）。
- **「变灰」做不到**。禁掉一个科技的唯一机制是 `type 102`，它的表现是**按钮消失**。
- **`objreplacement.json` 的 chance 效果仍没有有效读数**（三次实验都被美术/场景
  模组污染，方法已记录在 `_probe/report_shipped_vs_modded_json.md`）。

诚实边界写在每个 manifest 的 `verification.not_proven` 里 —— 那几条是**故意**留着
的，不是漏做。

---

## 项目结构

```
aoe2mod/            产品代码
  api.py            Toolkit：plan / build / install / mods / browse / icon_for …
  intent/           compiler（把 intent 翻成字节编辑）、reskin、retarget、datgrant
  dat/              .dat 读写（parser / writer / locate 是 vendored，见下）
  game/             icons（图标链）、linkedtechs、civtechtrees、locations、ddstex
  mod/              emitter（写 mod 目录）、strings（名字随 mod 发货）、provenance
  repair.py         读回一个社区模组：改了什么、还能不能救（四档判决 + 重放）
  ai.py            AI 接入口：只把愿望换成句子，绝不产出 intent（见下）
  semantic/         名字索引、prose（科技描述；单位「没有描述」的诚实拒绝）
  schema/           intents.json（13 个意图）、dat_bindings.json、中文标签表
  ui/               server.py（本地 HTTP）、nl.py（中文句子 → intent）、static/
plugins/            <名字>/schema/intents.json 就多一个意图，不用写 Python
tools/              run_ui.py（唯一入口）、sync_engine.py（把 _probe 的源同步进 aoe2mod/dat/）
_probe/             研究层：110+ 条钉子、一次性探针、报告
```

### 两条环境铁律

1. `aoe2mod/dat/{parser,writer,locate}.py` 是 **vendored** —— 直接改无效，下次
   `tools/sync_engine.py` 会覆盖。要改就改 `_probe/datparse/` 与 `_probe/serializer/`
   里的源，再跑 `sync_engine.py --accept-source-change`。
2. **禁止在 pwsh 里内联长 Python**（here-string 会吞引号）。超过几句话就写成
   `.py` 文件再跑。

---

## 怎么验证它还好的

```powershell
& $py -X utf8 -u '_probe\run_suites.py'    # 116 条快套件，约 1 小时
& $py -X utf8 -u '_probe\run_long.py'      # 8 条长套件，约 2 小时
```

每条钉子断言什么、什么改动会让它红，见 **`_测试钉子清单.md`**。
现状与未决问题见 **`项目状态.md`**，动手前值得先读 **`_交接说明.md`**。

---

## 这个项目为什么有这么多测试

逆向一个闭源引擎没有文档可查。「建造菜单的按钮格由哪个字段决定」「新字符串 id
能不能渲染」「`.dat` 里多加一条记录会不会让 mod 静默不加载」—— 每一条都只能改一个
字节、请人开一局、看屏幕上有没有变。

所以 `_probe/` 是**实验记录本**：每条钉子对应一次被证实的结论，或一次被推翻的假设。
里面记录了大量「看起来对、实测是错」的例子，例如：

- 追加记录会不会阻止 mod 挂载 → 不会（真因是不列颠有五条「城镇中心」记录）
- 新字符串 id 会不会不被认 → 会认（v28 直接读出来了）
- 提示框正文挂在哪个字段 → `+7`，不是 `+3`（v33 之前全错）
- 科技树 JSON 里的「互斥组」会不会拦人 → **不会**，它只画红叉；拦人的是 `.dat`

这些写在 `_交接说明.md` §2 的表格里，动手前扫一眼能省一整天的实验。
