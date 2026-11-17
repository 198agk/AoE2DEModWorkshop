# 模组工坊 UI · 逐条问题清单

审计对象：`<repo>\aoe2mod\ui\static\index.html`（2241 行）
审计时间：2026-10-26
方式：只读静态审计 + 数值统计。未改任何文件，未运行程序。

分级：
**P0** = 视觉失控根源，必须先修
**P1** = 一致性/可维护性缺陷
**P2** = 可留，将来顺手

---

## 一、总量统计（问题规模的证据）

| 指标 | 实测 | 契约要求 | 倍数 |
|---|---|---|---|
| CSS 字号档位 | **13 档**（9,10,10.5,11,11.5,12,12.5,13,13.5,14,15,16,18） | 4 档 | 3.25× |
| 圆角档位 | **7 档**（2,4,5,6,8,10,20） | 3（8/6/999） | 2.3× |
| 硬编码 hex 色 | **29 个**（去重后 27 个） | 0 | ∞ |
| 内联 `style=""` | **18 处** | 0 | ∞ |
| `padding` 数值 | **14 种**（1,3,4,5,6,7,8,9,10,11,12,14,18,20） | 9 种（2/4/6/8/12/16/20/24/32） | 1.6× |
| `gap` 数值 | **10 种**（2,3,4,6,8,10,12,14,16,20） | 同上 | 1.1× |
| `font-weight` | **5 档**（400,500,600,650,700） | 3 档 | 1.7× |
| `@container` | **0 个** | 组件内部布局必用 | — |
| `aria-*` 属性 | **0 个** | 关键控件必需 | — |
| `<label for=>` | **1 个 label，0 个 for** | 全部配对 | — |
| 空 CSS 规则 `{}` | 1 处 | 0 | — |
| 重复定义同一选择器 | 3 组 | 0 | — |

结论：这份 UI 的"丑"不是配色选错，是**没有任何一套尺度在约束它**。每个区块都是当场手调的，所以每个区块都略微不同，合起来就散。

---

## 二、P0 —— 必改

### P0-1　字号失控：13 档挤在同一屏

最大到最小是 **2 倍差**（18px / 9px），中间塞了 11 个中间值。

```
9px    index.html:273   .mod .move             ← 全站最小，一个移动按钮的箭头
10px   index.html:207   .tile .slot            ← 槽位徽章
10.5px index.html:214   .tile .cap             ← 图标名
10.5px index.html:229   .cell .nm              ← 网格里图标名
11px   index.html:348   #editor .edrow .id     ← 单位 id
11px   index.html:433   .id
11.5px index.html:286   .mod .state            ← 模组状态
12px   ×15 处（含 :182 :242 :260 :261 :348 :362 :365 :381 :395 :427 :430 …）
12.5px index.html:176   .clause .why           ← 拒绝理由
12.5px index.html:381   #editor table.f button
13px   ×19 处（主力正文）
13.5px ×5 处（index.html:190, 245, 259, 393, 400）
14px   index.html:40    body 默认
14px   index.html:173   .clause .main
15px   ×4 处（h1、h2×2、.noimg）
16px   index.html:361   #editor .edhead .t
18px   index.html:204   .tile .noimg
```

**危害**：12 / 12.5 / 13 / 13.5 这四个值肉眼几乎不可分，但它们让每个元素的"重量"都有一点点差别 —— 读的时候眼睛必须逐个确认层级，而不是靠节奏秒读。这正是"低级感"的来源。

**改法**：按 `DESIGN.md` §2 四档归并。
- 9 / 10 / 10.5 / 11 / 11.5 → `--fs-micro: 11px`
- 12 / 12.5 / 13 / 13.5 / 14 → `--fs-body: 13px`
- 15 → `--fs-title: 15px`
- 16 / 18 → 收回 `--fs-title`，只有编辑器头部保留 `--fs-display: 17px`

### P0-2　圆角 7 档，同一屏里 4 种并存

```
2px   index.html:210   .tile .bar          ← 进度条
4px   index.html:46    code/kbd
4px   index.html:492   select 内联（另一处 495）
5px   index.html:341   #editor .edrow .blank
6px   ×12 处（按钮、输入、chip、tab、图标框、cell…）
8px   ×5 处（#fpreview、.recipe、.edlist、.edpane、.tile .frame）
10px  ×3 处（.box、#banner、#toast）
20px  ×3 处（.stat、.switch）
```

**危害**：`.box` 是 10px，里面的按钮是 6px，里面的 `.recipe` 又是 8px，再里面的 `.tile .frame` 还是 8px —— 三层嵌套三个值，视觉上像三个不同系统的截图拼在一起。

**改法**：`--r-surface: 8` / `--r-control: 6` / `--r-pill: 999`。`.box` 10→8。

### P0-3　29 个硬编码 hex，token 形同虚设

`:root` 定义了 24 个变量，但界面里有 29 处绕过变量直接写色值：

| 色值 | 出现 | 行号 | 问题 |
|---|---|---|---|
| `#12386f` | 2 | `129`, `160` | 强调底上的文字色，未定义 token → 应加 `--accent-ink` |
| `#11151a` | 2 | `492`, `495` | **内联在 select 上**，深色底配 `color:inherit`，在浅色页里像一个黑洞 |
| `#7d4e00` | 2 | `393`, `395` | 警告底文字色，未定义 → `--warn-ink` |
| `#5f4d33` | 1 | `596` | 内联，一个只在右栏出现的褐棕色，**全站仅此一处** |
| `#d4a72c` | 1 | `389` | 警告描边 → `--warn-line` |
| `#1d4fd0` | 2 | `143` | 主按钮 hover → `--accent-hover` |
| `#24292f` | 1 | `400` | toast 底 → `--toast-bg` |
| `#ccd3da` | 2 | `49`, `299` | 滚动条 + 开关轨道 |
| `#b6bfc8` | 1 | `50` | 滚动条 hover |
| `#fff` / `#ffffff` | 5+1 | `141,207,294,400` | 深底上的白字 → `--on-dark` |

**危害**：改一次主题要 grep 全文件；`#5f4d33` 和 `#11151a` 这两处内联色，说明有人曾经临时加色、没回来收拾。

### P0-4　18 处内联 style

```
474  style="margin-top:12px"
477  style="display:none"
481  style="display:none;margin-top:10px"
502  style="margin-top:8px"
511  style="flex:1"
512  style="margin:0"
517  style="margin-top:8px"
531  style="flex:1"
543  style="margin-top:16px"
554  style="margin:0"
563  style="margin-top:16px"
568  style="display:none; border-top:1px solid var(--line)"
570  style="flex:1"
574  style="align-self:flex-end"
585  style="border-top:1px solid var(--line);margin-top:10px;padding-top:10px"
586  style="margin:0 0 8px"
594  style="margin-top:16px"
596  style="font-size:13px;color:#5f4d33"
```

其中 `margin-top:16px` 出现 **4 次**（543/563/594 + 一个 8px 变体），说明"卡片之间应该有 16px 间距"这件事本该由 `.box + .box` 定义一次，却手写了四次。

**改法**：`.box + .box { margin-top: 16px }`，其余归入工具类。

### P0-5　`--dim` 引用不存在

```css
index.html:277   color: var(--dim);      /* .mod .move */
```

`:root`（9–32 行）里没有 `--dim`。后果：这条声明被浏览器**静默丢弃**，`.mod .move` 的箭头颜色继承父级 —— 和 `.mod:hover` 时的 `--accent` 变化叠加，表现为 hover 时颜色跳变而不是渐变。

同时有两个变量**定义了从未使用**：`--gold`（28 行）、`--sunk`（29 行）。

### P0-6　组件内部布局用 `@media`，在真实窗口下失效

```css
index.html:319   @media (max-width: 860px) { #editor .edbody { grid-template-columns: minmax(0,1fr); } }
```

`#editor .edbody` 是 `244px minmax(0,1fr)` 双栏。它住在主区里，而主区在 1237px 窗口下宽度约 **833px**（1237 − 384 栏 − 20 gap − 48 padding）。`@media` 判断的是**窗口**，不是**卡片**。

后果：当右栏 384→340 后，编辑器仍按窗口宽度决定分栏 —— 卡片实际宽度已经不足以撑 244px 侧栏时，`@media` 不会触发，`edpane` 被挤压。这和 66–69 行注释里记录的 `min-width:0` 坑是同一类问题，只是换了个位置。

**改法**：给 `.box` 加 `container-type: inline-size`，把 319 行的 `@media` 改成 `@container (max-width: 700px)`。

---

## 三、P1 —— 一致性缺陷

### P1-1　`.box h2` 定义了两次，参数冲突

```css
index.html:100-106   .box > h2 { margin: 0 0 14px; font-size: 15px; font-weight: 650; letter-spacing:.01em }
index.html:108       .box h2  { font-size: 15px; font-weight: 650; margin: 0 0 10px; }
```

后者覆盖前者：**所有卡片标题的实际下边距是 10px，不是 14px**。前者是一段死代码。另外 `107` 行 `.box > h2::after { content: none }` 是清除一个从未设置的伪元素。

### P1-2　`.hint` 定义了三次

```
109   .box .hint        { margin-top: 10px }
112   .hint             { color: var(--text-2); font-size: 13px }
113   .hint code        { color: var(--text) }
109   .box .hint code   { color: var(--text) }   ← 与 113 完全重复
```
`112` 与 `109` 的包裹层级不同但声明相同。合并成一条。

### P1-3　`.stat` 的 `.ok` 是纯冗余

```css
index.html:179-180   .stat      { background: var(--ok-soft); color: var(--ok); }
index.html:182       .stat.ok   { background: var(--ok-soft); color: var(--ok); }   ← 与基类完全相同
```

### P1-4　toast 用 id 和 class 各写一套

```css
index.html:397-407   #toast { ... } #toast.show …  #toast.ok … #toast.bad … #toast.warn …
index.html:410-411   .toast { position: fixed; }  .toast.show { opacity: 1 }
```

410–411 行只补了 `position` 和 `opacity`，其余全靠 id 选择器。注释（408–409）自己写着"两半都不能单独改名"—— 这是把耦合写成了注释，而不是消除它。改成单一 class 选择器。

### P1-5　`.remove` 的圆角也重复了

```css
index.html:291   .remove { … border-radius: 6px }
index.html:295   .box .remove, .box .remove.armed { border-radius: 6px }   ← 重复
```

### P1-6　空规则块

```css
index.html:434   .cap, .bar, .frame, .slot, .noimg { }
```
五个类名，零条声明。历史遗留。

### P1-7　`.line` 类名被两个不相干的东西共用

```css
index.html:425   .line { font-size: 13px; }               ← 通用文本
index.html:393   #banner .line { font-size:13.5px; font-weight:600; color:#7d4e00 }  ← banner 标题
```
`#banner` 里那个 `.line` 是标题，外面那个 `.line` 是正文。同名不同义，改一个会连带另一个。

### P1-8　`body` 行高与 `.box` 内文本行高不一致

```css
index.html:40    body { font: 14px/1.6 … }
index.html:109   .box .body, .box .hint, .box p { font-size: 13px; line-height: 1.65 }
index.html:153   .box textarea { line-height: 1.7 }
index.html:191   .detailtext { line-height: 1.7 }
```
1.6 / 1.65 / 1.7 三档。13px 配 1.65 得到 21.45px 行高，落在 4px 网格之外。

### P1-9　`height: 460px` 是魔法数字

```css
index.html:317   #editor .edbody { … height: 460px }
```
在 1080p 窗口下勉强够用，在小窗口下编辑器会被压出滚动条，在大窗口下又浪费。改为 `min-height: 420px` + flex 撑满（**不要再写成 `max-height: calc(100dvh - 220px)`：220 这个减法常量与实际 chrome 272px 差 52px，2026-11-01 实测让真实 821px 窗口里的文档高 921px，玩家要拖滚动条才能看到字段表最后一行**，见 DESIGN.md §6）。

### P1-10　`font-weight` 五档，其中 650 是非标准值

```
400 ×1   500 ×2   600 ×8   650 ×4   700 ×1
```
`650` 在 Segoe UI / 微软雅黑的字重表里不存在，浏览器会四舍五入到最近可用档 —— 行为随系统字体变化。统一到 400/600/650（若坚持 650 就要接受它在部分字体下等同 600）。

### P1-11　`.mod .move` 用 9px 装箭头图标

```css
index.html:269-279   .mod .move { width: 22px; font-size: 9px; line-height: 1 }
```
9px 是肉眼极限，且它是**可点击控件**。命中区 22×约 11px，远低于 24×24 的最低可用尺寸。

---

## 四、P1 —— 可访问性

### P1-12　零 `aria-*` 属性

全文件 `grep 'aria-'` 结果为空。影响：
- `.switch`（297–309）是 `<div>` 或 `<span>` 加 CSS，没有 `role="switch"` / `aria-checked` → 屏幕阅读器读不出开关状态
- `#toast`（397）是纯视觉通知，没有 `role="status"` / `aria-live="polite"` → 状态变化不会播报
- `#banner`（386）是警告条，没有 `role="alert"`
- 图标按钮（`.mod .move`）只有箭头字符，没有 `aria-label`

### P1-13　1 个 `<label>`，0 个 `for`

```html
index.html:571   <label class="hint" data-i18n="title.label">模组名字（…）</label>
index.html:572   <input type="text" id="title">
```
标签与输入框相邻但未关联 —— 点击标签不会聚焦输入框，屏幕阅读器也不会把标签读给输入框。

其余 11 个输入/textarea/select（`#say`, `#fintent`, `#fshape`, `#pickq`, `#rname`, `#edq`, `#title` 等）**完全没有标签**，只有 placeholder。placeholder 会在输入时消失，等于输入到一半就失去了"这是填什么的"提示。

### P1-14　焦点可见性只覆盖了部分控件

```css
index.html:144   button, input, select, textarea:focus-visible { outline: 2px solid var(--accent) }
```
`.switch` 是 `<div>`/`<span>`，不在这条选择器里 → 键盘用户无法看到开关是否获得焦点。`.cell`（219，`cursor: grab`，可拖拽）同样没有焦点态。

---

## 五、P2 —— 可留

### P2-1　顶栏只有 h1 + 两个 `--text-3` 小字
`index.html:438-444`：`#ver` 和 `#datinfo` 都是 12px 灰字，右对齐靠 `spacer`。功能上够用，若将来加操作区再重排。

### P2-2　`.box` 阴影 `--shadow` 是双层 rgba(31,35,40)
`index.html:30`。这是对的（有色阴影而非纯黑），保留。

### P2-3　图标网格 `repeat(auto-fill, minmax(62px, 1fr))`
`index.html:218`。自适应写法正确，保留。但 `62px` 未与其他间距对齐，可改 64。

### P2-4　滚动条自定义色 `#ccd3da` / `#b6bfc8`
`index.html:48-50`。WebKit only，Firefox 会回落到系统滚动条（视觉不一致）。若在意，加 `scrollbar-color`。

### P2-5　`.cands button` 是 12px 内联在 `.box button`（13px）之上
`index.html:184`。级联正确，但意味卡片内的按钮分两种尺寸。若按 `DESIGN.md` §5 只有三档按钮，这里应归入 `.chip` 规格。

---

## 六、优先级路线

如果只做一件事，做 **P0-1（字号 13→4 档）**。它单项就能消除最大一部分"低质感"。

按性价比排序：

1. **P0-1 + P0-2**（字号 + 圆角归并）—— 纯 token 层改动，不碰结构，风险最低，收益最大
2. **P0-3 + P0-5**（颜色全走变量 + 修 `--dim`）—— 让后续所有改色变便宜
3. **P0-4**（内联 style 清零）—— 让 `@media`/`@container` 能生效
4. **P0-6**（`@media` → `@container`）—— 修真实窗口下的挤压
5. **P1-1~P1-7**（去重、删死代码）—— 让 CSS 从 429 行缩到约 360 行
6. **P1-12~P1-14**（可访问性）—— 键盘/读屏可用
7. P2 项按需

**P0-1~P0-4 全部集中在 `<style id="aoe2mod-legible">` 第 7–435 行内**，不触及任何 JS 逻辑（437 行之后）。这是一次可以完全回滚的改动。
