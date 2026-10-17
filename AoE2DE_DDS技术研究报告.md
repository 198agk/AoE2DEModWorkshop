# AoE2 DE DDS 技术需求研究报告

方法说明：本会话 `web_search` 完全不可用（`Error: DeepSeek search has no API key for "DEEPSEEK_API_KEY"`），
且 `web_fetch` 对 github.com / raw.githubusercontent.com / steamcommunity.com 一律报
`Error: URL hostname "..." resolves to a non-public IP address`。因此本报告的证据来源为：
① 本地游戏安装目录 2221 个 `.dds` 的逐字节解析；② 游戏自带的官方构建脚本；
③ `AoE2DE_s.exe` 的字符串挖掘；④ Pillow 12.3.0 源码与实测；⑤ 本机 `texconv.exe` 实测；
⑥ 本地存档的官方论坛帖子镜像。凡未经确认的一律标注 **UNCONFIRMED**。

---

## 1. AoE2 DE 引擎实际接受哪些 DDS 变体

### 1.1 未压缩 DDS 被接受 —— 而且是出厂内容的主力

对安装目录全部 2221 个 `.dds` 的头部普查（格式分布）：

| 格式 | 数量 |
|---|---|
| UNCOMPRESSED RGBA8 32bpp（mask 序为 `[0xff,0xff00,0xff0000,0xff000000]`） | 1318 |
| FOURCC `DXT5` | 509 |
| FOURCC `DXT1` | 276 |
| DX10 / `dxgiFormat=98`（BC7_UNORM） | 101 |
| UNCOMPRESSED RGBA8 32bpp（mask 序为 `[0xff0000,0xff00,0xff,0xff000000]`） | 14 |
| FOURCC `DXT3` | 2 |
| UNCOMPRESSED 8bpp（`resources\_common\fonts\basic_bold_16.dds`，2048x1024） | 1 |

**结论：未压缩 RGBA 完全被接受，且是出厂内容里最多的形式（1333/2221 占 60%）。**
不需要强制 DXT/BC 压缩。
证据：`D:\Games\Steam\steamapps\common\AoE2DE` 全目录头部解析（脚本 `dds_stats.py` / `hud_classify.py`）。

`widgetui\textures\ingame\units`（794 个文件）本身就是 **539 未压缩 + 255 DXT5** 的混合，
这证明同一目录下压缩与未压缩可以并存。

### 1.2 DXT1 / DXT3 / DXT5 / BC7 全部有效

四者都在出厂内容中实际出现，说明引擎端全部可解码：

- DXT5（BC3）509 个，包括全部 40 个 SD 图集（`widgetui\textures\atlas\SD\*.dds`）。
- DXT1（BC1）276 个，包括 5 个背景图和全部战役图。
- DXT3（BC2）2 个，`resources\_common\particles\textures\atlases\dust.dds`（512x1024，11 mip）为其中之一。
- BC7（DX10 / DXGI 98）101 个，包括 `widgetui\textures\atlas\HD\*` 与 `atlas\UHD\*` 全部 80 个图集。
- 未发现任何 BC1(显式 DX10) / BC4 / BC5 / BC6H 的出厂纹理。

游戏自己的构建脚本 `D:\Games\Steam\steamapps\common\AoE2DE\widgetui\build_atlas.ps1` 使用的就是这三种：

```powershell
$AtlasBuildTool        = Join-Path $ToolPath.Path "texassemble.exe"   # 行 8
$TextureConversionTool = Join-Path $ToolPath.Path "texconv.exe"       # 行 9
# UHD（qualityLevel 0 或 1，行 100-104）
& $TextureConversionTool @("-ft","dds") @("-f","BC7_UNORM","-bcmax") @("-m","1","-y",$atlasTempFile,"-o",$uhdAtlasOutputFolder)
# HD（qualityLevel 0 或 2，行 110-113）
& $TextureConversionTool @("-ft","dds") @("-f","BC7_UNORM") @("-m","1","-y",$atlasTempFile,"-o",$hdAtlasOutputFolder)
# SD（qualityLevel 0 或 3，行 122-125）
& $TextureConversionTool @("-ft","dds") @("-w",$atlasHalfWidth,"-h",$atlasHalfHeight) @("-f","BC3_UNORM") @("-m","1","-y",$atlasTempFile,"-o",$sdAtlasOutputFolder)
```

关键点：`-f BC3_UNORM` 的输出是**旧式 fourCC `'DXT5'`，不是 DX10 头**（texconv 实测确认）。
这正好解释了 40 个 SD 图集为什么全是 `'DXT5'`。

### 1.3 DX10 扩展头被接受 —— 但只在引擎侧保证；第三方读取器会炸

出厂 HD/UHD 图集就是 DX10/BC7，所以**引擎接受 DX10 头**。

但社区有一个可复现的第三方读取失败报告，原文错误串：
> **"Unsupported DXGI format (98)"**

来源：https://forums.ageofempires.com/t/implementing-custom-icons-solution-atlas-or-interface/226454
（p1 @freezer17，2023-03-08）—— 他对 UHD 图集做操作时读取器报此错。`98` 即 `DXGI_FORMAT_BC7_UNORM`。

微软官方 DDS 编程指南明确建议保守做法（原文）：
> "The standard DDS_PIXELFORMAT should be preferred for maximum compatibility to store RGB uncompressed
> data and DXT1-5 data as not all DDS tools support the DX10 extension."

来源：https://learn.microsoft.com/en-us/windows/win32/direct3ddds/dx-graphics-dds-pguide

**工程建议：工具应输出旧式 fourCC（`DXT1`/`DXT3`/`DXT5`）或未压缩头，绝不要依赖 DX10。**

### 1.4 `texconv.exe` 就是社区/官方的转换器，且随游戏发行

- 位置：`D:\Games\Steam\steamapps\common\AoE2DE\Tools_Builds\texconv.exe`（660480 字节）；
  同目录还有 `texassemble.exe`（263168 字节）。这是 Microsoft DirectXTex 的官方 CLI。
- 官方背书：论坛补丁说明（本地镜像 `aoe2docs\forums_search_widgetui.json`，@FloosWorld 2024-03-01 转述开发组）：
  > "Added the tool for building widgetui atlases to Tools_Builds folder. It can be used by executing
  > build_all_atlases.ps1 script located in widgetui folder"
- 官方示例命令（上面 1.2 已给完整原文）：
  ```
  texassemble.exe atlas -flist <图集文件清单> -atlas-width <W> -atlas-height <H> -o <临时.bmp>
  texconv.exe -ft dds -f BC7_UNORM -bcmax -m 1 -y <临时.bmp> -o <UHD目录>
  texconv.exe -ft dds -f BC7_UNORM -m 1 -y <临时.bmp> -o <HD目录>
  texconv.exe -ft dds -w <宽/2> -h <高/2> -f BC3_UNORM -m 1 -y <临时.bmp> -o <SD目录>
  ```
- 模组作者圈的实际做法更土：使用 **Paint.NET 内置 DDS 支持**，或在线转换器，或 Photoshop 的 NVTT 插件。
  论坛被采纳答案原文（https://forums.ageofempires.com/t/modding-issue-modding-ingame-unit-tech-icons-becomes-a-garbled-mess-cant-figure-out-exact-dds-export-settings/66389 ，p2 @StepS7578，2020-01-02）：
  > "As for the format - you need to use A8B8G8R8 as the export setting, no mipmaps."
- 同帖 p5：`"DDS is supported natively with Paint.NET."`；p6 @Zetnus（2021-04-14）：`"The game also accepts icons in the png format."`
- 另一个帖子（https://forums.ageofempires.com/t/guide-for-modding-terrain/67036 ，p4 @Zetnus，2020-01-13）推荐的 Photoshop 插件是
  https://developer.nvidia.com/nvidia-texture-tools-adobe-photoshop ，并说可用 https://www.aconvert.com/image/png-to-dds 在线转换。

### 1.5 模组实测的 DDS 头（本机唯一模组自带 DDS 证据）

模组 `550412_透明主题整合自用`（已启用）位于
`C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\subscribed\`：

| 文件 | 尺寸 | 格式 | mips | depth | dwFlags | linear |
|---|---|---|---|---|---|---|
| `widgetui\textures\backgrounds\mainmenu_bg.dds` | 5120x2160 | DXT1 | **0** | 0 | 0x081007 | 5529600 |
| `widgetui\textures\backgrounds\wide_default_background.dds` | 5120x2160 | DXT5 | 1 | 0 | 0x081007 | 11059200 |

注意第一个是 `mips=0` 且**没有** `DDSCAPS.MIPMAP` 标志，游戏照样加载。
而且这个形态并非只在模组里出现：出厂文件
`widgetui\textures\backgrounds\techtree_left.dds`（2240x2160 DXT1）同样是 **mips=0 depth=0 flags=0x081007**。
→ **单 mip 且不写 mipmap 计数的头，是游戏自己也在用的合法形态。**

---

## 2. mipmap 是否必需

**结论：不必需；HUD/UI 纹理一律单 mip。** 证据分四层：

1. **全目录统计**：2221 个 `.dds` 中 2123 个 mip 层数 ≤ 1（mips=0 → 118 个，mips=1 → 2005 个）。
   只有 98 个文件有真正的 mip 链（mips=3 → 64，mips=10 → 2，mips=11 → 3，mips=12 → 29）。
   `DDSCAPS.MIPMAP (0x400000)` 的出现与 `mips>1` **完全一致**（98/98），说明标志位和计数是配套写的。
2. **HUD 专项**：`D:\Games\Steam\steamapps\common\AoE2DE\widgetui` 全树 **没有任何一个纹理 mips>1**
   （mips=1 → 1573，mips=0 → 82）。mips>1 只出现在 `resources\_common` 的粒子图集等处。
3. **官方脚本**：`build_atlas.ps1` 对 UHD/HD/SD 三个分支**全部传 `-m 1`**，即出厂 HUD 图集在构造上就是单 mip。
4. **社区**：@Zetnus 在 https://forums.ageofempires.com/t/guide-for-modding-terrain/67036 原文：
   > "You don't need to include/generate mipmaps, but it looks better if you do."
   （语境是地形/世界内纹理；HUD 侧连"更好看"的余地都没有，因为没有距离缩放。）

**游戏会不会自己生成 mipmap？没有证据表明会。**
对 `AoE2DE_s.exe` 全部 280550 条 ASCII 字符串做挖掘，**没有** `mipmap` / `mip level` / `mipLevels` 任何字样
（只有若干巧合子串如 `pf C`、`xf C`、`NMDXt'`、`Bc76Lj`）。这不能证明引擎内部没有 mip 生成代码，
但足以说明没有相关的诊断/错误路径暴露出来。**引擎是否内部生成 mip 链：UNCONFIRMED。**

**单 mip 的后果**：不会有报错（#1.5 的模组文件已启用且在跑）。对 HUD 没有视觉差异，
因为 HUD 不做距离 LOD。对世界内 sprite/地形，单 mip 会产生远处的闪烁/噪点——这正是 @Zetnus 那句"有更好看"的意思。

**踩坑警告（texconv 特有）**：`texconv.exe` **默认生成完整 mip 链**。实测 300x200 源图：
- `texconv.exe -f DXT5 -y ...`（无 `-m`）→ `mipCount=9`，`dwCaps` 带 MIPMAP，文件 80784 字节，
  stdout 打印 `as (300x200,9 BC3_UNORM 2D ...)`。
- 要抑制必须显式 `-m 1`，输出 `mipCount=1`。

---

## 3. 正确的尺寸

**结论：既不需要 2 的幂，也不需要正方形。** 全目录 2221 个 `.dds`：

- **567 / 2221 两个维度都不是 2 的幂**。例：`2048x2104`（CivAsia.dds）、`1216x1140`（defaultwidgets_p.dds）、
  `832x728`（ingameicons_p.dds）、`1800x1560`（ingamepanels_p.dds）、`2940x1680`（mapicons_p.dds）、
  `740x600`（ScenarioEditor_p.dds）、`4800x5440`（campaignicons_p.dds）。
- **325 / 2221 是非正方形**（两维不同）。例：`widgetui\textures\atlas\SD\ingameicons.dds` 720x796、
  `chatatlas.dds` 768x448、`ingamecursor.dds` 256x128、`mainmenu_bg.dds` 5120x2160。
- `widgetui\textures\menu\mapicons`（220 个文件）**0/220 是 2 的幂**，全部非 POT。
- 反例：`widgetui\textures\ingame\units` 794/794 同时 POT 且正方形；`ingame\buildings` 109/109 同样。
  所以 POT 只是那些目录的**习惯**，不是引擎约束。

**小尺寸 HUD 图标**（重要：它们大多是**未压缩**的，不是 DXT）：
- `widgetui\textures\ingame\icons\` 下 `094_wood_trading_0x.dds`、`154_tyranny.dds` 等 80x80 未压缩 RGBA8。
- `MissingTexture.dds` 64x64 DXT1；`rope.dds` 24x64 DXT1。

**图集尺寸对齐规则**：`build_atlas.ps1` 行 33-42 把图集宽高向上取整到 8 的倍数：
```powershell
if (($atlasWidth % 8) -ne 0) { $atlasWidth = [Math]::Ceiling($atlasWidth / 8) * 8; $_.AtlasDef.MaxWidth = $atlasWidth; }
```
→ 打包图集时宽高必须是 8 的倍数。单张 HUD 纹理没有这个约束。

**替换时的实操规则（社区 + 技能库一致）**：
- @wonderhd11 自答（https://forums.ageofempires.com/t/guide-for-modding-terrain/67036 ，p3）：
  "Do i need to worry about the resolution of the textures?（**No need**）"；@Zetnus p4：
  "Yes / No, smaller resolution is fine"。
- 但 @Zetnus 对地形给了硬性路径约束（p7 原文）：
  > "The files in the 2x folder are (mostly) 2048x2048, in 1x they are 1024x1024 (mostly).
  > **IMPORTANT: the game only uses the 2x folder, so your modded files must also be in 2x (even if you do a smaller size).**"
- 技能库 `aoe2-de-ui-textures` 的护栏（针对 UI 替换）：
  > "**Keep the original pixel size when replacing.** 508 of 510 published replacement files do."
- 本机抽样 10/11 个模组覆盖文件与出厂文件**像素尺寸完全相同**（如 emblems `britons.png` 450x280→450x280、
  `menu-panel_full.png` 550x173、`chatbar_bg.png` 1235x270、`scroll\knot.png` 53x53）。
  唯一例外：`resources\_common\wpfg\resources\aoe_logo.png` 605x240 → 605x270（高度差 30px）且工作正常
  → **WPF/wpfg 层至少容忍改尺寸**。

---

## 4. Alpha 通道处理

**结论：HUD 透明度 = 纹理里的真实 alpha 通道 + `materials.json` 里的声明式 Blend 模式。
没有独立遮罩文件，没有 1-bit 调色板索引。**

### 4.1 Blend 枚举（引擎第一方）

`AoE2DE_s.exe` 偏移 `0x03217440`–`0x03217520` 的字符串块顺序（即枚举定义顺序）为：
`'Blend'` → `'AlphaTest'` → `'InverseAlpha'` → `'AlphaPlayerColor'` → `'Null'`。
所以 `MaterialDef.Blend` 的合法取值是 **`{AlphaTest, InverseAlpha, AlphaPlayerColor, Null}`**。
→ **`AlphaTest` 是一等公民**，说明 1-bit alpha 测试路径真实存在（不是只能靠遮罩）。

出厂 `widgetui\materials.json`（2494306 字节）的 Blend 直方图：
`InverseAlpha` 3208、`AlphaPlayerColor` 1205、`None` 141、`Null` 1。
（JSON 里用 `None`，exe 枚举里是 `Null`；两个词都被识别。）

### 4.2 实测 alpha 分布

| 文件 | 尺寸 | alpha 全 0 占比 | alpha 全 255 占比 |
|---|---|---|---|
| `widgetui\textures\atlas\SD\ingameicons.dds` | 720x796 | 44.3% | 48.8% |
| `widgetui\textures\atlas\SD\chatatlas.dds` | 768x448 | 42.4% | 42.4% |
| `widgetui\textures\atlas\SD\defaultwidgets.dds` | 2048x1716 | 42.9% | 46.5% |
| `widgetui\textures\ingame\units\000_50730.DDS` | 256x256 | 0.5% | 85.1% |
| `widgetui\textures\ingame\buildings\108_ant_tower_guard.dds` | 512x512 | 0% | 100%（全不透明）|
| `widgetui\textures\backgrounds\mainmenu_bg.dds` | 5120x2160 | 0% | 100%（全不透明）|
| `widgetui\textures\ingame\emblems\britons.png`（PNG 侧）| 450x280 | 80.7% | 1.3%（渐变 alpha）|

→ 图集是**硬边抠图 alpha**（二值化），单张图标可以完全不透明，PNG 侧允许渐变。

模组 `182654_Age of Anime` 的 `emblems\britons.png`：RGBA 450x280，**alpha 最大值只有 178**，
0.0% 的像素达到 255，80.8% 为 0 —— 引擎依然正常渲染。
→ **引擎容忍"从不达到全不透明"的 alpha**（当柔色调遮罩用）。

### 4.3 已知坑

- **不需要预乘 alpha。** 对 exe 搜索 `premultipl` 唯一的命中在 `0x03410710` 的 WPF/XAML 字符串簇里
  （邻居是 `'Opacity'` 0x03402410、`'OpacityMask'` 0x03402418、`'AllowsTransparency'` 0x0340EDC8、
  `'BlendMode'` 0x033FC250、`'AlphaBlendColor'` 0x03416CD8），是 WPF 属性，不是 DDS 写入要求。
- **没有 `alpharef`/`alphafunc`/alpha 阈值相关的可调参数**，除了 `AlphaTest` 这个 Blend 值本身。
- **通道顺序（必须搞对）**：对未压缩 32bpp 的 mask 普查——
  - R 在前的 mask `[0xff,0xff00,0xff0000,0xff000000]`（即字节序 R,G,B,A）：widgetui 1038 个、modes 278 个、resources 2 个。
  - B 在前的 mask `[0xff0000,0xff00,0xff,0xff000000]`（字节序 B,G,R,A）：**仅 widgetui 14 个**。
  - 实测两个读取器（Pillow 与 texconv）对两种排布的解码结果**逐像素完全一致**，说明 mask 与字节是自洽的：
    `000_50730.DDS`（R 在前）三点采样 Pillow (77,156,190)/(51,145,190)/(170,118,51) == texconv 输出；
    `108_ant_tower_guard.dds`（B 在前）三点 (69,124,241)/(237,242,248)/(153,130,106) == texconv 输出
    （texconv 还分别把它报成 `B8G8R8A8_UNORM` / `:Opaque` 与 `R8G8B8A8_UNORM`）。
  - → **工具若用 Pillow 写未压缩 RGBA，必须让 mask 与字节同时一致**。Pillow 自己写的是
    `[0x00FF0000,0x0000FF00,0x000000FF,0xFF000000]` + 磁盘字节 `B,G,R,A`，这是自洽的；
    而游戏最常见的形态是 `[0xff,0xff00,0xff0000,0xff000000]` + 磁盘字节 `R,G,B,A`。
    **千万不要把"游戏常见的 R 在前 mask"贴到 Pillow 的 B,G,R,A 字节上——那会红蓝互换。**
- 论坛原答案说的 `A8B8G8R8`，就是"B 在前的 32bpp + alpha"（即上面第二种 mask）。

---

## 5. Pillow DDS 写入器的限制

源文件：`C:\Users\26913\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\Lib\site-packages\PIL\DdsImagePlugin.py`
（632 行，19733 字节，Pillow 12.3.0）。以下全部经源码阅读 + 本机实测双重确认。

### 5.1 `_save` 支持的 `pixel_format`（`DdsImagePlugin.py:532` 起）

```python
# 入口模式门禁
raise OSError(f"cannot write mode {im.mode} as DDS")   # 仅允许 RGB / RGBA / L / LA
pixel_format = im.encoderinfo.get("pixel_format")      # DdsImagePlugin.py:539
```

| `pixel_format` 值 | 头部形态 | 允许的 `im.mode` |
|---|---|---|
| `"DXT1"` | 旧式 fourCC `'DXT1'` | L / LA / RGB / RGBA |
| `"DXT3"` | 旧式 fourCC `'DXT3'` | L / LA / RGB / RGBA |
| `"DXT5"` | 旧式 fourCC `'DXT5'` | L / LA / RGB / RGBA |
| `"BC2"` | **DX10** 头，`dxgiFormat=73`（BC2_TYPELESS）| RGB / RGBA |
| `"BC3"` | **DX10** 头，`dxgiFormat=76`（BC3_TYPELESS）| RGB / RGBA |
| `"BC5"` | **DX10** 头，`dxgiFormat=82`（BC5_TYPELESS）| **仅 RGB**（RGBA 报错）|
| 不传 | 未压缩（RGB/RGBA/L/LA）| L / LA / RGB / RGBA |

→ 提问中"BC2/BC3/BC5 用 `D3DFMT.DX10`，DXT1/DXT3/DXT5 用旧式 fourCC"**完全正确**，已确认。

本机实测头部（300x200 RGBA 源图，`dds_experiment.py`）：

```
default        → UNCOMPRESSED  pfFlags=0x41 fourCC=0 bitCount=32 masks=[0xff0000,0xff00,0xff,0xff000000] flags=0x00100F pitch=1200 mips=0 240128B
"DXT1"         → fourCC='DXT1' pfFlags=0x4 bitCount=32 flags=0x081007 linear=1212 mips=0 30128B
"DXT3"         → fourCC='DXT3' bitCount=32 flags=0x081007 linear=1212 mips=0 60128B
"DXT5"         → fourCC='DXT5' bitCount=32 flags=0x081007 linear=1212 mips=0 60128B
"BC2"          → fourCC='DX10' DXT10=(73,3,0,0,1) 60148B
"BC3"          → fourCC='DX10' DXT10=(76,3,0,0,1) 60148B
"BC5"+RGB      → fourCC='DX10' DXT10=(82,3,0,0,1) bitCount=24 60148B
```

### 5.2 Pillow **永远不写 mipmap**（已确认，看源码即知）

`DdsImagePlugin.py:599-616` 的头部写入把两个字段**硬编码为 0**：

```python
... struct.pack("<I", 0),      # dwDepth  → 恒为 0
    struct.pack("<I", 0),      # dwMipMapCount → 恒为 0
```
且 `dwCaps` 恒写 `DDSCAPS.TEXTURE (0x1000)`，从不设 `DDSCAPS.MIPMAP (0x400000)`。
扫描全部 12 个 Pillow 产出文件：**每一个都是 `mipCount=0`、`depth=0`、无 MIPMAPCOUNT 标志、无 MIPMAP cap**。

读取侧同样只支持 mip 0：`DdsImageFile._open` 读第一层就返回，
`exclamation_mark.dds`（512x512，10 mip）读出来 `n_frames=1`、`info` 字典为空 —— **读写都没有 mip 链接口**。

### 5.3 已知 bug / 陷阱（全部实测复现）

**(a) `encoderinfo` 被整体替换而不是合并 —— 这就是"高层封装丢掉 pixel_format"那一类 bug，且失败是静默的。**
```python
im.save(path, format="DDS", encoderinfo={"pixel_format": "DXT5"})   # ← 静默产出未压缩！
```
实测结果：`pfFlags=0x41, fourCC=0, pitch=1200`，**完全没有报错**。
`encoderinfo={}` 同样静默降级为未压缩。
原因：Pillow 的 `save()` 用调用方 kwargs 整体替换 `encoderinfo`，封装层自己拼 `encoderinfo` 就把调用者的
`pixel_format` 丢了。**任何中间封装都可能命中这个静默失败。**
（对比：直接 `im.save(path, format="DDS", pixel_format="DXT5")` 正常；
经 `BytesIO` 传 `pixel_format="DXT5"` 也正常 → 写入器本身是好的。）

**(b) `dwPitchOrLinearSize` 对压缩格式写错。**
Pillow 对压缩纹理写的是 `(im.width + 3) * 4`（`DdsImagePlugin.py:544`），
300x200 时 = **1212**。而正确值是 MS 规范 / 出厂文件用的块对齐顶层 mip 线性尺寸：
```
linear_size = max(1,(w+3)//4) * max(1,(h+3)//4) * block_bytes
block_bytes: 8  (DXT1/BC1/BC4)
            16  (DXT3/DXT5/BC2/BC3/BC5/BC6H/BC7)
```
实测对照（300x200 DXT5）：正确 = 75*50*16 = **60000**（texconv 写的正是 60000）；Pillow 写 1212。
出厂验证：`chatatlas.dds` 768x448 DXT5 → 192*112*16 = **344064**（文件里的实际值 ✓）；
`ingameicons.dds` 720x796 DXT5 → 180*199*16 = **573120** ✓；
`mainmenu_bg.dds` 5120x2160 DXT1 → 1280*540*8 = **5529600** ✓。

**(c) `dwRGBBitCount` 在 FOURCC 纹理上写成 32（或 RGB 时 24），而出厂文件和 texconv 都写 0。**

**(d) DX10 头的 `arraySize` 写成 0**（MS 规范要求 ≥ 1），且 DXGI 码用的是 `*_TYPELESS`。

**(e) Pillow 读不出自己的头缺陷**：raw DXT5、打补丁后的、`BC3 arraySize=0`、`BC3 arraySize=1` 四种，
Pillow 全部无错读回 RGBA (300,200) —— **不能拿 Pillow 的回读当作头部合法的证据**。

### 5.4 Pillow 不支持的格式（精确错误串，Pillow 12.3.0 实测）

```
BC1      → OSError: cannot write pixel format BC1
BC1_UNORM→ OSError: cannot write pixel format BC1_UNORM
BC4      → OSError: cannot write pixel format BC4
BC6H     → OSError: cannot write pixel format BC6H
BC7      → OSError: cannot write pixel format BC7      ← 关键：AoE2 HD/UHD 图集正是 BC7
ATI2     → OSError: cannot write pixel format ATI2
BC5U     → OSError: cannot write pixel format BC5U
DXT2     → OSError: cannot write pixel format DXT2
DXT4     → OSError: cannot write pixel format DXT4
BC5 + RGBA → OSError: only RGB mode can be written as BC5
mode "1"/"P"/"I"/"F" → OSError: cannot write mode {mode} as DDS   （由模式门禁先抛，与 pixel_format 无关）
```
→ **Pillow 只能写两种对 AoE2 有用的东西：旧式 fourCC 的 DXT1/DXT3/DXT5，以及未压缩 BGRA。**
它能**读** BC7（实测 `atlas\HD\campaignicons.dds` 读为 RGBA (5200,5200) `pixel_format=BC7`），
但**不能写 BC7**：`im.save(..., pixel_format="BC7")` 在已加载的 BC7 图像上直接抛 `cannot write pixel format BC7`。

### 5.5 Pillow 的块数据本身是合法的 —— 只需重写 128 字节头

用 `texconv.exe` 做交叉验证：
- `texconv.exe -f B8G8R8A8_UNORM -m 1 -y -o <目录> <Pillow写的DXT5.dds>` →
  打印 `reading ... (300x200 BC3_UNORM 2D) as (300x200 B8G8R8A8_UNORM 2D :NonPM)`，**无报错**。
  → 微软自家的 DirectXTex 解析器接受 Pillow 的旧式 fourCC 头。
  （随后 `writing ... FAILED (80070003)` 是 `ERROR_PATH_NOT_FOUND`，因为输出目录名含非 ASCII 的 `工作区2`，
   texconv 打成了 `???2` —— 与格式无关。）
- Pillow 的 DX10 输出则被拒：
  ```
  reading ...pil_bc3.dds FAILED (8007000d)          # ERROR_INVALID_DATA，原因是 arraySize=0
  手改 arraySize 0→1（偏移 128+12=140）后：
  reading ... FAILED due to Typeless format 76      # dxgiFormat=BC3_TYPELESS，非法
  ```
- 对照 texconv 自己的正确 DX10 形态：`-f DXT5 -m 1 -dx10` → `DXT10=(77, 3, 0, 1, 1)`
  （`BC3_UNORM`=77、`TEXTURE2D`=3、miscFlag=0、**arraySize=1**、miscFlags2=1）；
  `-f BC7_UNORM -m 1` → `(98, 3, 0, 1, 0)`。

**头部改写配方（已验证到字节级完全一致）**：
以 768x448 DXT5 目标为例，`widgetui\textures\atlas\SD\chatatlas.dds` 的头是
`{dwSize:124, w:768, h:448, mips:1, flags:0x000A1007, pitch:344064, depth:1, pfFlags:0x4, fourCC:'DXT5', bitCount:0, caps:0x1000, masks:(0,0,0,0), size:344192}`。
把 Pillow 自己重编码同一图集的结果（`mips=0, flags=0x00081007, pitch=3084, depth=0, bitCount=32`）
按如下改写：`dwFlags=0x000A1007`、`dwPitchOrLinearSize=ceil(w/4)*ceil(h/4)*block_bytes`、
`dwDepth=1`、`dwMipMapCount=1`、`dwRGBBitCount=0`、`dwCaps=0x1000`
→ 结果与出厂图集**头部与文件大小（344192）都逐字节一致**，且 texconv 读为合法 `BC3_UNORM`。

**编码器差异**：同一张 256x256 RGBA 源图，Pillow 的 DXT5 与 texconv 的 DXT5 体都是 65536 字节，
但 **46041 / 65536 字节不同（70.3%）** —— 两者都结构合法、都能解码，视觉质量不同。
**不要指望两条路径产出相同字节。**

### 5.6 官方文档佐证

https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html 原文：
> "Added in version 11.2.1: DXT1, DXT3, DXT5, BC2, BC3 and BC5 pixel formats can be saved:: `im.save(out, pixel_format="DXT1")`"

---

## 6. 其他能产出 AoE2 可用 DDS 的库/工具

### 6.1 `texconv.exe`（DirectXTex）—— 首选
- 本机就有：`D:\Games\Steam\steamapps\common\AoE2DE\Tools_Builds\texconv.exe`（660480 字节）。
- **可以打包进你的工具**：一个中文模组工具包已经这么干了 ——
  `D:\Software\DeepSeek Harness\工作区1\官方内容\AGE编辑器终极版V1【By RemonBo】\texconv.exe`
  与游戏内那份字节数完全相同（660480），是第三方发行版。
- **许可状态：UNCONFIRMED。** DirectXTex 上游是 MIT，但
  `D:\Games\Steam\steamapps\common\AoE2DE\SoftwareLicenses\NOTICE.txt`（53 个第三方组件）里
  **没有 DirectXTex 条目**（列了 `DirectXTK` 第 32 行、`D3D11TextureMediaSink` 第 30 行、`stb` 第 67 行）。
  即游戏发行 texconv.exe 时未附自己的声明文件。合法再分发与否需要自行核实上游 MIT 文本。
- 关键 flags（`texconv.exe -h` 实测）：`-w -h -m <n> -f <format> -if <filter> -ft dds -y -o <dir> -px -sx
  -pmalpha -alpha -pow2 -dx10 -srgb{i|o} -sepalpha -c <hex-RGB> -bcmax -bcquick -bcuniform -bcdither
  -nologo -gpu <adapter> -nogpu -fl <feature-level> -keepcoverage <ref> -vflip -hflip`。
  格式名含 `BC1_UNORM`/`BC2`/`BC3_UNORM`/`BC4`/`BC5`/`BC6H_UF16/SF16`/`BC7_UNORM(_SRGB)`/
  `B8G8R8A8_UNORM(_SRGB)`/`R8G8B8A8_UNORM(_SRGB)`/`B8G8R8X8_UNORM`/`A8_UNORM`/`R8_UNORM`，
  以及旧别名 `DXT1 DXT2 DXT3 DXT4 DXT5 RGBA BGRA FP16 FP32 BPTC BPTC_FLOAT`。
  滤镜 `POINT LINEAR CUBIC FANT BOX TRIANGLE`（可加 `_DITHER` / `_DITHER_DIFFUSION`）。
- **本机 BC7 需要 GPU**：texconv 报 `[Using DirectCompute on "NVIDIA GeForce RTX 5070"]`；
  adapter 3（Microsoft Basic Render Driver）无 DirectCompute。若目标环境无独显，BC7 可能失败
  → 实用上应提供 **DXT5 回退**。
- 注意 `-f BC3_UNORM` 产出**旧式 fourCC**；想要 DX10 必须显式 `-dx10`（不推荐，见 #1.3）。

### 6.2 `texassemble.exe`（同目录，263168 字节）
仅用于图集打包：`texassemble.exe atlas -flist <清单> -atlas-width <W> -atlas-height <H> -o <out.bmp>`。
命令集 `cube volume array cubearray atlas h-cross v-cross h-strip v-strip array-strip merge gif`。
**它不是 PNG→DDS 转换器**，而是多图拼图工具（拼完再交给 texconv）。

### 6.3 `DESpriteTool.exe`（精灵，见 #8）

### 6.4 NVTT / compressonator / basisu
- 本机**全盘搜索**（`LOCALAPPDATA`/`APPDATA`/`Program Files`/`D:\Games`/`D:\Software`/`C:\Users\26913`）
  找 `CompressonatorCLI.exe`、`nvcompress.exe`、`nvtt_export.exe`、`basisu.exe`、`bc7enc.exe`、`crunch.exe`
  → **一个都没有**。仅找到两份 texconv.exe（游戏内 + 中文工具包内）。
- 社区提到 NVTT 只作为 Photoshop 插件（`https://developer.nvidia.com/nvidia-texture-tools-adobe-photoshop`，
  @Zetnus，https://forums.ageofempires.com/t/guide-for-modding-terrain/67036 p4）。
  **NVTT / Compressonator / basisu 的产物是否被 AoE2 DE 接受：UNCONFIRMED（无法实测）。**

### 6.5 Python bindings
本机 Python（`C:\Users\26913\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe`）：
`PIL 12.3.0`、`numpy 2.3.5` 存在；
**`image_dds`、`ddsfile`、`pytexture`、`dds`、`texture2ddecoder`、`squish` 全部未安装**，
且本会话无网络可安装 → **这些库能否产出 AoE2 合法 DDS：UNCONFIRMED（未能实测）**。
（`image_dds` 基于 Rust `image_dds`，理论上能写 BC7；但对 AoE2 的头部细节——如
`dwPitchOrLinearSize` 用块对齐顶层尺寸、`depth=1`、`mipCount=1`——是否符合仍需实测。）

### 6.6 Go / Rust / C# 库
未在本机发现任何相关实现。**UNCONFIRMED。**

---

## 7. AoE2 DE 模组作者实际怎么替换 HUD 贴图

### 7.1 最重要的结论：他们基本**不做 DDS**

技能库 `aoe2-de-ui-textures` 的端到端证明：
> "**A loose PNG at the atlas source's `FileName` wins over the baked atlas DDS.** Proven end-to-end:
> a shipped mod containing zero `.dds` files replaces HUD emblems and the game renders the new art.
> Consequence: texture replacement = **copy a file**. No atlas rebuild, no `.dds` authoring, no mipmaps.
> Pillow's DDS limitations are irrelevant."

本机佐证：`widgetui` 目录里 `.json` 133 / `.ps1` 4 / `.dds` 1655 / `.png` 5977 / `.jpg` 206。
`.dds` 与 `.png` 的 stem 集合几乎是**不相交**的（7974 个 stem 中同时有两种扩展名的只有 1 个：
`widgetui\textures\menu\image\missingtexture`）。
`.dds` 集中在图集与图标目录（`ingame\units` 794、`ingame\tech` 308、`menu\mapicons` 220、
`ingame\buildings` 109、`atlas\{HD,SD,UHD}` 各 40、`campaign_selection\map_overlays` 8、`backgrounds` 5），
而真正的 HUD 界面贴图（`menu\usericons` 433、`ingame\icons` 133、`menu\buttons` 111、
`menu\techtree\{normal,hover}` 215、`ingame\panels` 51、`ingame\chat` 47 …）**全是 PNG**。

本机 5 个已订阅模组里 **4 个完全不含 `.dds`**，只有 `550412_透明主题整合自用` 含 2 个。

### 7.2 实际工作配方（按顺序）

**路线 A（推荐，UI 贴图替换）**
1. 在 `widgetui\materials.json` 里定位 widget → Material → `AtlasRef` → `AtlasTextures[].Textures[].FileName`。
   （`materials.json` 的路径基准是 `widgetui/`，不是游戏根目录。）
   例：`{ "MaterialDef": { "Name": "CivEmblemBritons", "Type": "Atlas", "Blend": "InverseAlpha",
   "TextureRef": "CivEmblemBritons", "AtlasRef": "ingamepanels" } }`
   以及 `"UHDSource"/"HDSource"/"DefaultSource": "textures/atlas/SD/mapicons.dds"`。
2. 做一个 `info.json` 的模组文件夹，镜像游戏根目录，把**同路径、同像素尺寸**的新 PNG 放进去。
3. 重启游戏（@OxDBAOE2：模组改动必须退出到桌面重开；只有**直接改游戏目录**才实时生效）。
4. 关闭会改同一文件的其它模组，或把自己的 `Priority` 调高
   （`mod-status.json` 里 `Priority` 升序 = 加载顺序）。

**路线 B（必须改 `.dds` 时）**
1. 用 Paint.NET 导出 **A8B8G8R8 + 无 mipmap**（论坛被采纳答案）；
   或用在线转换器 / Photoshop NVTT 插件 / texconv。
2. 命令（等价于游戏自己做图集的那条）：
   ```
   texconv.exe -ft dds -f BC3_UNORM -m 1 -y -o <输出目录> <输入.png>
   ```
   想要未压缩（论坛答案的 A8B8G8R8）：
   ```
   texconv.exe -ft dds -f B8G8R8A8_UNORM -m 1 -y -o <输出目录> <输入.png>
   ```
3. 用 Pillow 时，见 #5.5 的头部改写配方，否则 `dwPitchOrLinearSize` / mip 计数 / bitCount 都是错的。

**路线 C（图集，官方）**
```
widgetui\build_all_atlases.ps1  →  build_atlas.ps1 <atlas_name> [qualityLevel 0-3]
                                →  texassemble.exe atlas ... -o <tmp.bmp>
                                →  texconv.exe -f BC7_UNORM[-bcmax] | BC3_UNORM  -m 1
```
首次运行需要 `Set-ExecutionPolicy Unrestricted -Scope Process`。

### 7.3 硬性限制与坑

- **图集 `.dds` 不能通过模组覆盖。** @Zetnus 原话（https://forums.ageofempires.com/t/file-can-not-be-modded/117361 ，p2，2021-02-09）：
  > "There are all kinds of files that don't work in a mod. Some of the json files as well. All the fonts. **The texture atlases.**"
  同帖（https://forums.ageofempires.com/t/modding-the-icon-atlas-files/91310 ，p1）：
  > "This works if I replace the ingame files, but not as a mod. I realize that the *individual* icons work in a mod
  > (`widgetui\textures\ingame`) but for what I am doing, it much more efficient to edit the atlas itself."
- **但**：如果你在 `materials.json` 指向的 **`FileName` 上放 loose PNG**，它可以覆盖图集（见 7.1）。
  这两条不矛盾：被拒的是"图集 `.dds` 文件本身"，不是"图集素材的源文件"。
- **存档引用了 `materials.json` 的文件名时，覆盖常常不生效**：https://forums.ageofempires.com/t/problem-with-mods-overriding-files-linked-to-material-json/235688
  报 `066_scale_barding_armor.dds`、`104_50730.DDS`、`widgetui\textures\campaign\rcam2\suryavarnam.dds` 全部无效。
  原文："the background does not change. Yet again, 'suryavarnam.dds' appears in material.json."
- **数据模组里的自定义图标长期损坏**：https://forums.ageofempires.com/t/icons-json-and-materials-json-in-new-patch/231422
  （2023-05 起，2025-05 仍未修）；p3 "Apparently materials.json works in ROR, but not AOE2DE."
  同主题另帖（2026-08-23，topic 288998）：`TechIconsT141Durazzo` 曾工作，"After the recent update, the custom Durazzo icon no longer appears."
- **失败模式常常是静默 no-op，不是崩溃**：@marc0s141（https://forums.ageofempires.com/t/.../61109 的 p9，2020-05-09）：
  > "**My background image wasn't the right file type** it accepted the .dds file type I thought it had saved as one but when I fixed that it works now."
  → 主菜单背景 `.dds` 格式不对时游戏不报错，只是"没变化"。
- **引擎给的模组贴图错误串**（从 `AoE2DE_s.exe` `0x032062D0` 挖出，工具应当把它透出给用户）：
  ```
  Unable to load mod texture "%s". Check it is in a supported format.
  ```
  邻近的第一方诊断（`0x03205E88`–`0x03206xxx`）：
  ```
  Loading texture from file: %s                                    (0x03205E88)
  Texture asset %s failed to load                                  (0x03205F10)
  Failed to load texture: %s                                       (0x032D5548)
  Unable to allocate memory for texture asset: %s                  (0x03205EE0)
  StbImageLoader::LoadFromMemory failed when loading %s            (0x03205F30)
  textures/MissingTexture.dds                                      (0x03205F68, 回退常量)
  Selecting low fidelity mode for user content atlas due to %s.    (0x03206230)
  Cannot selecting low fidelity mode for user content atlas due to lack of format support.  (0x03206270)
  Out of space in atlas "%s" to mod texture "%s". The size set in "materials.json" is %d x %d  (0x032170A0)
  Mod atlas "%s" uses %d x %d texels                             (0x03217100)
  [ERROR][Effect: "%s" Sprite: %d] Failed to find image "%s" within atlas "%s"   (0x03202130)
  AtlasTextureBase::CreateFromJSON: Creating atlas "%s" from texture %s with user page %d x %d texels  (0x032063A0)
  The input doesn't provide a supported format                     (0x032F88C8)
  ```
- **引擎的图像解码器是 stb_image，不是专门的 DDS 验证器**：二进制里唯一的图像加载类名就是
  `StbImageLoader::LoadFromMemory failed when loading %s`，同一字符串群里还有完整的 stb_image 错误词汇
  （`bad png sig`、`not enough pixels`、`invalid filter`、`1/2/4/8/16-bit only`、`bad ctype`、`0-pixel image`、
  `first not IHDR`、`not BMP`、`not PSD`、`wrong version`、`not GIF`、`bad DRI len`、`bad DQT type`）。
  这也解释了为什么 HUD 贴图能是 PNG。
  **对 280550 条 ASCII 字符串搜索 `DDS ` magic、`fourCC`、`dxt1`/`dxt3`/`dxt5` 字面量、`DX10`/`dxgiFormat`
  → 全部没有命中**，也**没有** `texconv`/DirectXTex 引用。所以二进制里**不存在**一个专门的 DDS 校验器；
  格式接受走的是通用图像解码 + 上面那条 `Unable to load mod texture` 检查。
- 唯一泄漏的引擎源码路径：`F:\Agents\PhoenixBuilders-08\p4\portland_group\Aoc\Source\Engine\Resource\ResourceManager.cpp`（`0x032065C0`）。
- 与 BC7 相关的引擎开关（第一方字符串）：
  `ENABLE_BC7_ASSETS` / "Enable support for BC7 assets"（`0x03204BA8`/`0x03204B88`）——
  说明 BC7 支持是可开关的，且在低端 feature level 上会降级（配合 `Force a specific feature level
  (one of 11_0, 10_1, 10_0, 9_3, 9_2, 9_1)` `0x03201300` 与 SD 图集减半逻辑）。
  精灵层格式标记：`HDN_SLD_BC1`、`HDN_SLD_BC7`、`MOD_SLD`、`MOD_BC3`、`DMG_SLD_BC1`、`DMG_SLD_BC7`。
  → **工具用 DXT5/BC3 或未压缩比用 BC7 更安全。**

---

## 8. `.smx` / `.slp` 精灵

### 8.1 现状
- 出厂安装：`.sld` 17672、`.slp` 205、`.smp` 38、**`.smx` 0**。
- `.smx` 只是**模组内容**格式，本机在 `D:\Software\DeepSeek Harness\工作区1\mods\21400_Civilization Alliance备份\resources\_common\drs\graphics\`
  找到 4 个（`p_cannonball_x1.smx` 20687B、`p_herochakram_x1.smx` 44508B、`p_herochakram_shadow_x1.smx` 100028B、
  `u_inf_karambitwarrior_deathB_x1.smx` 1892828B）。
- openage 规范（本地镜像 `aoe2docs\openage_smx-files.md`）原文：
  > "**The current release of Age of Empires 2: Definitive Edition uses a different graphics format called SLD.**"
- 引擎仍支持旧格式（可开关）：`ENABLE_SMX_ASSETS` / "Enable support for SMX assets"（`0x03204B70`/`0x03204B50`）、
  `FORCE_SMX_ASSETS` / "Prioritise usage of SMX/SMP assets ahead of SLD"（`0x03203460`/`0x03203490`）。
- 社区佐证：@rjgt3838（https://forums.ageofempires.com/t/.../212760 p6，2022-09-02）：
  > "SLX studio can update the Frame counts (add, substract) but **doesn't currently support SLD format**.
  > However, Mods using old SMX file format still work. So find the original SMX files on Steam to edit."

### 8.2 `.smx` 二进制格式（实测 + 规范双向确认）

实测 4 个文件的头 32 字节前缀完全一致：`53 4d 50 58 02 00 1e 00 ...`，偏移 16 处是 ASCII `ArtDesk 1.00 SLP`。
openage 规范给出的结构（与实测吻合）：
```c
struct smx_header { char file_descriptor[4]; int16 version; int16 num_frames;
                    int32 file_size_comp; int32 file_size_uncomp; char comment[16]; };
// Python: Struct("< 4s 2H 2I 16s")   magic 'SMPX', version 2（少数为 1）, comment 恒空
struct smx_frame_header { uint8 frame_type; uint8 palette_number; uint32 uncomp_size; };
// Python: Struct("< 2B I")
```
`frame_type` 位域：bit7 = 主图形层，bit6 = 阴影层，bit5 = 轮廓层，bit4 = 压缩算法（`0` = 4plus1，`1` = 8to5），
bit3 = 阴影投射在动画之上，bit0-2 未使用。
规范还说："Compression is only used for pixel data"；"they do not define explicit offsets for each frame and its
layers, so the file has to be read sequentially."

引擎侧的校验字符串（`0x031FFB60`–`0x031FFED8`）：
```
SMX asset signature missing in %s
SMX asset %s too small (%d bytes) to be valid
SMX asset %s is version=%d (%s) Frame sizes: comp=%d uncomp=%d CRC=%08x
SMX asset: "%s" frame #%d %s layer is too large: %d x %d
Smx data absent in HDN layer of frame %d in asset %s
empty.smx / empty_x2.smx
```
`.sld` 侧：`SLDX` 魔数、`SLD asset %s too small (%d bytes) to be valid`、`SLD asset signature missing in %s`、
`SLD asset %s is using deprecated version %d`、`Looking to load non-SLD asset named %s`。
路径模板：`%s%s.sld`、`%s%s.smx`、`%s%s.smp`、`%s%s.slp`。
`openage_sld-files.md`（34757B）说明 SLD 图层用 DXT1（主图形、伤害遮罩）+ DXT4/BC4（阴影、玩家色遮罩）。

### 8.3 有没有 PNG 序列 → SMX 的转换器

**没有"跳过 PSD"的官方路径。** 官方工具 `DESpriteTool.exe`（`Tools_Builds\Sprites\DESpriteTool.exe`，
1038336 字节，Ver 4.20.1 Apr 26 2021，用法 banner 写的是 `Usage: DEAssetTool filename.psd [ options ]`）
的文档化输入是 **PSD 帧序列**：

`Tools_Builds\Sprites\readme.txt` 原文：
> "This tool lets you convert SLP and PSD files into SMP/SMX/SLD files."
> "## PSD to SLD conversion / Under one of the needed folders (buildings / nature / units), create a subfolder
> consisting of your PSD frames in filename_0000.psd format. Example: n_tree_bamboo_0000.psd,
> n_tree_bamboo_0001.psd... Each PSD requires the following layers: - Damage (for nature/buildings, clipping mask
> of Diffuse) OR Blood (for units, clipping mask of Diffuse) - AmbientOcclusion (clipping mask of Diffuse)
> - Diffuse (main layer, masked with white-on-black bitmap) - Decal - Background - Height - Normals.
> Then either run convert_psd.bat or drag and drop your specific folder(s) onto DESpriteTool.exe to begin the
> SLD conversion process."
> "settings.json files contain the conversion settings. Each subfolder containing an additional settings.json will
> amend the upper-level set of settings. It does not matter how deep the subfolder with graphics is - however the
> contents of any folder starting with an underscore will be ignored."

`Tools_Builds\Sprites\SLP\readme.txt` 原文：
> "To convert SLP to SMP/SMX format place .SLP files in this folder, then run convert_slp.bat."

`convert_psd.bat`：`start DESpriteTool.exe "buildings"` / `"nature"` / `"units"`。
`convert_slp.bat`：`DESpriteTool.exe "slp"` 然后 `DESpriteTool.exe -compress "slp\*.smp"`。

`DESpriteTool.exe` 完整选项（实测 `-h` 抓取）：
```
-p=diffuse_palette_file  -pc=player_color_palette_file  -pn=###（palettes.conf 里的编号）
-Hx=###  -Hy=###（hotspot）  -AT=###（alpha 阈值）  -PT=###（玩家色阈值）  -ST=###（阴影阈值）
-out（生成轮廓层）  -x1  -filterscale= -filtersize= -filteralpha= -filterblur= -filterringing= -filtersamples=
-algorithm=###（point, bilinear, bicubic, lanczos, mitchellnetravali）  -ao=###  -nopc  -fadepc  -ignoresubdirs
-individualsmp  -adjustmentlevel=##,##,##,##,##  -damage=###（on, off, bake, fade）  -damagestrength=###
-facetcount=###  -terrainobject  -i
-compress（把已有的 SMP 转成 SMX）  -deleteSMP  -InterleaveSMX  -disableSLD（改回产出 SMP/SMX 而不是 SLD）
-enableFrameReduction  -diffuseBC7  -damageBC7  -exhaustiveBC7  -multithreadCompress
```
`-diffuseBC7` 证明游戏自己的精灵管线在 diffuse 层用 BC7，否则用 BC1。

### 8.4 `.slp`
205 个出厂 `.slp` 全部是 `2.0N` 版本、`palette_offset == 0`、**不含内嵌 JASC-PAL**，
必须外挂调色板，默认 `<game>\resources\_common\drs\interface\50500.bina`（2888 字节的 256 色 JASC-PAL 文本）。
`interface\` 下 134 个 `.bina` 里有 32 个是 JASC-PAL
（`50243-50246, 50250, 50268, 50500-50509, 50519-50521, 50530-50534, 50563, 50588, 50589, 53016, 53111-53114`）。
SLP 头 32 字节：偏移 0 = 4 字节版本串（`2.0N`/`3.0`/`4.0`/`4.1`/`5.0`/`6.0`/`4.2P`）；偏移 4 = uint16 帧数；
偏移 6 = uint16 属性；偏移 8 = 24 字节注释（当 `version[0]=='4'` 时改解释为 uint64 + uint32 main_offset(==32)
+ uint32 shadow_offset + uint64）。版本串以 `P` 结尾表示 LZ4 压缩体。
帧头 32 字节：`cmd_table_offset / outline_table_offset / palette_offset / properties / width / height / hotspot_x / hotspot_y`。
注意 `.slp` 的**玩家色**由 `50500.bina` 这类外挂调色板 + `-pc` 处理，不是 DDS alpha。

---

## 附：可直接抄用的头部模板（出厂逐字节验证）

**A. DXT5 单 mip HUD（最安全的目标形态）** —— 例 `widgetui\textures\atlas\SD\chatatlas.dds` 768x448
```
dwMagic            = 'DDS '
dwSize             = 124
dwFlags            = 0x000A1007      # CAPS|HEIGHT|WIDTH|PIXELFORMAT|MIPMAPCOUNT|LINEARSIZE
dwHeight           = h
dwWidth            = w
dwPitchOrLinearSize= max(1,(w+3)//4) * max(1,(h+3)//4) * 16
dwDepth            = 1
dwMipMapCount      = 1
dwPFSize           = 32
dwPFFlags          = 0x4             # DDPF_FOURCC
dwFourCC           = 'DXT5'
dwRGBBitCount      = 0
masks              = (0,0,0,0)
dwCaps             = 0x1000          # DDSCAPS_TEXTURE
fileSize           = 128 + linear
```
（DXT1 时 `block_bytes = 8`、fourCC `'DXT1'`；DXT3 时 `16`、`'DXT3'`。）

**B. 未压缩 RGBA8（论坛答案的 A8B8G8R8 等价物，最常见的出厂形态）** —— 例 `widgetui\textures\ingame\units\000_50730.DDS` 256x256
```
dwFlags            = 0x0002100F      # CAPS|HEIGHT|WIDTH|PITCH|PIXELFORMAT|MIPMAPCOUNT
dwPitchOrLinearSize= w * 4
dwDepth            = 1
dwMipMapCount      = 1
dwPFFlags          = 0x41            # DDPF_RGB | DDPF_ALPHAPIXELS
dwFourCC           = 0
dwRGBBitCount      = 32
masks              = [0xff, 0xff00, 0xff0000, 0xff000000]   # 磁盘字节 R,G,B,A
dwCaps             = 0x1000
```
变体：`dwFlags = 0x00100F`（无 MIPMAPCOUNT）、`dwDepth = 0`、masks 为 B 在前 `[0xff0000,0xff00,0xff,0xff000000]`
—— 这两种在出厂内容和已启用模组里都存在且可用。

**C. BC7（能读不能写）** —— 例 `widgetui\textures\atlas\HD\ingameicons.dds` 1440x1592
```
dwFourCC = 'DX10'，随后 20 字节 DDS_HEADER_DXT10：
  dxgiFormat        = 98     (BC7_UNORM)
  resourceDimension = 3      (D3D10_RESOURCE_DIMENSION_TEXTURE2D)
  miscFlag          = 0
  arraySize         = 1      ← Pillow 会错写成 0
  miscFlags2        = 0      ← texconv 的 BC7 也是 0；texconv 的 BC3 -dx10 写 1
```
微软规范关于 `miscFlags2` 的原文警告：
> "The legacy D3DX 10 and D3DX 11 utility libraries will fail to load any .DDS file with miscFlags2 not equal to zero."

来源：https://learn.microsoft.com/en-us/windows/win32/direct3ddds/dds-header-dxt10

---

## 给工具实现者的最小风险路径

1. **优先不做 DDS。** 若目标是替换 HUD 元素，直接在 `materials.json` 找到对应 material 的 loose PNG `FileName`，
   把用户 PNG 以**同尺寸**写到模组目录的同路径即可。这是 5/5 已订阅模组的实际做法，且不需要 mipmap、
   不需要 texconv、不需要处理 Pillow 的头部缺陷。
2. **必须产出 DDS 时**，用随游戏发行的 `texconv.exe`，命令
   `texconv.exe -ft dds -f BC3_UNORM -m 1 -y -o <dir> <in.png>`（= 旧式 fourCC DXT5）；
   无 GPU 或保守场景可改用 `-f B8G8R8A8_UNORM`（未压缩，论坛答案的形态）。
   **不要用 BC7**，除非能接受 DX10 头（引擎能读，但生态里已有 `Unsupported DXGI format (98)` 这类失败）。
3. **只能用 Pillow 时**，用 `im.save(p, format="DDS", pixel_format="DXT5")`
   （**必须直接传 kwargs，绝不能经 `encoderinfo=`**），然后按 #5.5 改写 128 字节头；只支持 DXT1/DXT3/DXT5。
4. **所有 UI 替换都保持原始像素尺寸**；图集类尺寸必须是 8 的倍数。
5. 把引擎的原文错误串透出给用户：
   `Unable to load mod texture "%s". Check it is in a supported format.`
