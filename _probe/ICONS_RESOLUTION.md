# `icons.json` 全段解析结案表

游戏版本 `101.103.54800.0` · `widgetui/icons.json` = 75,114 B · mtime **2026-09-23 13:04:45**
复现脚本：`_probe/icons_resolve.py`、`icons_files.py`、`wpfg_icons.py`、`icons_all.py`、`icons_verify*.py`、`icons_gap*.py`、`icons_dead*.py`、`icons_ext.py`
机器可读结果：`_probe/icons_report.json`

---

## 0. 一页结论

`icons.json` 是"**数字 → 贴图**"的**名字表**，14 个段落，共 **2,066 条有效值**（另有空值条目）。
**已解析 1,842 / 2,066 = 89.2%**；剩余 224 条全部带原因，无一处猜测。

| 段 | 有效条目 | 解析 | 机制 | 状态 |
|---|---|---|---|---|
| `Buildings` | 111 | **100%** | 值 = `materials.json` 的 `MaterialDef` 名 | ✅ |
| `Units` | 1,000 | 794 (79.4%) | 同左（**206 条是"号位超界"，见 §4**） | ⚠ |
| `Techs` | 313 | 307 (98.1%) | 同左（6 条是 `Xxx` 占位） | ✅ |
| `CivUniqueUnit` | 65 | **100%** | 同左（值是 `UnitIcons<NNN>50730`） | ✅ |
| `CivSecondaryUniqueUnit` | 65 | **100%** | 逗号分隔多材质 | ✅ |
| `StatIcons` | 24 | **100%** | 前 6 条直接是材质名；其余需 `stat_icon_x` → `StatIcons<Camel>` **+ 3 条键别名** | ✅ |
| `CivEmblem` | 65 | **100%** | → `wpfg/resources/civ_emblems/<name>.png`（**2 条单复数别名**） | ✅ |
| `InGameCivEmblem` | 62 | 61 (98.4%) | → `widgetui/textures/ingame/emblems/<name>.png`（1 条别名） | ✅ |
| `CivTechTree` | 66 | **100%** | → `wpfg/resources/civ_techtree/<value>.png` | ✅ |
| `History` | 87 | **100%** | → `wpfg/resources/history/<value>.png` | ✅ |
| `MapIcons` | 197 | **100%** | → `wpfg/resources/mapicons/<value>.png` | ✅ |
| `Notification` | 2 | **0%** | `wonder_icon` / `relic_icon` — **全树无对应文件、exe 内 0 命中** | ❌ 见 §5 |
| `MenuIcons` | 9 | **0%** | `submenu_*` / `mutually_exclusive_tech_unavailable` — 同上 | ❌ 见 §5 |

---

## 1. 三种寻址方式（按段分派）

`icons.json` 的段值**不是同一种东西**，必须按段分别路由：

### A. 材质名段（值 = `materials.json` 的 `MaterialDef.Name`）
`Buildings` / `Units` / `Techs` / `CivUniqueUnit` / `CivSecondaryUniqueUnit`
→ 取该材质的 `TextureRef`，**按 `TextureRef` 反查图集条目**（不可信 `AtlasRef`，见 §3）。

### B. 文件名段（值 = 磁盘文件名 stem，**且在 `resources/_common/wpfg/resources/` 下，不在 `widgetui/`**）
`CivTechTree` / `History` / `MapIcons`
→ 直接 `wpfg/resources/<子目录>/<value>.png`。

### C. 带前缀的文件名段（值有前缀，需剥离 + 别名修正）
| 段 | 段值形如 | 剥离规则 | 物理路径 |
|---|---|---|---|
| `CivEmblem` | `civ_emblems_britons` | 去 `civ_emblems_` | `wpfg/resources/civ_emblems/<name>.png` |
| `InGameCivEmblem` | `ingame_civ_emblems_britons` | 去 `ingame_civ_emblems_` | `widgetui/textures/ingame/emblems/<name>.png` |
| `StatIcons` | `stat_icon_armor` | 去 `stat_icon_` + TitleCase + 前缀 `StatIcons` | 材质名（再走 A 路由） |

**★ 别名表（必须硬编码，无法推导）**
```python
CIV_ALIAS = {"inca": "incas", "berber": "berbers"}      # 单数→复数（磁盘用复数）
STAT_ALIAS = {                                           # 键号→材质名（命名不规则）
  "008": "StatIconsHpRegeneration",   # 段值 stat_icon_hpregen
  "011": "StatIconsHpLoss",           # 段值 stat_icon_hploss
  "013": "StatIconsRange-Armor",      # 段值 stat_icon_range_armor（注意连字符！）
}
```

---

## 2. `wpfg/resources/` 图标目录实测（`_probe/wpfg_icons.py`）

`resources/_common/wpfg/resources/` 下的图标目录：

| 目录 | 文件数 | 命名 |
|---|---|---|
| `civ_emblems/` | 65 | `<civ>.png`，**全部 450×280 RGBA** |
| `civ_techtree/` | 232 | `menu_techtree_<civ>{,_hover,_pressed}.png` |
| `history/` | 94 | `history_<civ>.png` |
| `mapicons/` | 209 | `rm_*.png` / `P_rm_*.png` |
| `mappoolicon/` | 185 | `br_*.PNG` / `cm_generic.png` |
| `empireicons/` | 36 | `CR-001.png` |
| `Icons/` | 37 | `Rank_Shield_*`、`age-1..4.png` |
| `campaign/` | 44 | |
| `button_small/` | 94 | |
| `dialog/` `mainmenu/` `gamemode/` `news/` `credits/` | 15/13/11/11/1 | |

`wpfg/fonts/` 13 个 TTF（只服务 WPF 菜单层）；`wpfg/*.ps` + `*.ps.dx11` 是 D3D11 像素着色器源码对。

---

## 3. `StatIcons` 的真身：`widgetui/textures/ingame/staticons/`（29 个 PNG）

全段 24 条里有 21 条落在 **`textures/ingame/staticons/<name>.png`**（图集 `ingamepanels`）：

```
armor.png blastRadius.png convert.png damage.png damageBleed.png damageBypass.png
food.png garrison.png gold.png hp.png hpLoss.png hpRegen.png movementSpeed.png
pierceAttack.png pierceAttackBleed.png pierceAttackBypass.png powerup.png
powerup_armor.png powerup_range.png powerup_regeneration.png powerup_reload.png
powerup_speed.png range-armor.png range.png reloadTime.png stone.png transport.png
wood.png workrate.png
```
材质名对应表（`StatIcons*` → 文件）已实测，例如
`StatIconsHpRegeneration → hpRegen.png`、`StatIconsRange-Armor → range-armor.png`、
`StatIconsMovementSpeed → movementSpeed.png`、`stat_icon_powerup → powerup.png`（**这条段值本身就是材质名**）。

→ **"改属性图标"= 覆盖 `widgetui/textures/ingame/staticons/` 里的同名 PNG**，一张一改，无需碰图集。

---

## 4. `Units` 段 206 条失败 = **号位超界，不是解析失败**（`_probe/icons_dead.py`）

- 图集里形如 `UnitIcons<NNN>50730` 的 RefName：**794 条，号位范围 0..936**。
- `icons.json` 的 `Units` 有 **1,000** 条，键号 0..999。
- 失败 206 条，键号范围 **757..999**（非连续），**图集里根本没有这些号位**。
- `.dat` 实体实际引用的 `icon_id` 去重后 **725 个，最大 936**；其中 `>=757` 的只有 **26 个**，且都 ≤936（900–929 等）。

**结论**：`icons.json` 的 `Units` 段是"**号位空间的完整预留表**"，1,000 个槽位全部预写名字；图集只做了 794 个（0..936 里有空档）。**引用了却无图集的号位，在本机数据里一个都没有** → 对工具而言，`Units` 段应报"**声明了但无贴图**"而不是"解析失败"。

`Techs` 段的 6 条同类：`TechIconsT004Cartography`、`TechIconsT020Xxx`、`T024Xxx`、`T090Xxx`、`T102Xxx`、`T117Xxx` —— 后 5 条**名字尾巴就是字面 `Xxx`**（占位符），`Cartography` 是唯一真实缺口。

---

## 5. `Notification` / `MenuIcons` 两段：**查无实处**（诚实未解）

已排除的所有可能：

| 检验 | 结果 |
|---|---|
| 全树（25,807 个 stem）文件名含 `submenu` / `wonder_icon` / `relic_icon` / `stat_icon` | **各 0 命中** |
| `wpfg/resources/` 递归搜同 token | 0 |
| 237 个 `wpfg` 文本文件（`.xaml`/`.txt`/`.json`）含这些字面量 | **各 0** |
| `AoE2DE_s.exe`（72,166,200 B）含这些字面量 | **各 0** |
| 全树任何 `.icons` 生成文件 | **0 个** |
| 用户档案树里的 icon 缓存 | 无 |
| `materials.json` 里的形近材质 | `SubMenu*` 15 个 → 全是 `textures/menu/tabs/innertab_*.png`（**是菜单页签九宫格，与"submenu_*"无关**）；`ScorePanelWonder/ScorePanelRelic` → `indicator_wonder.png`/`indicator_relic.png`（**名字不同**） |

→ 这两段**在本机这一版游戏里没有可解析的落地**。可能解释（未定论）：① 已废弃的遗留段；② 由实时服务/活动下发（`AssetOverride` 机制）而非随包文件；③ 名字在运行时拼接。**工具应对这两段显示"未解析（无对应资源）"，绝不猜测。**

---

## 6. `icons.json` 是不是构建产物？（`_probe/icons_ext.py`、`icons_runtime.py`）

- 时间戳：`icons.json` = **2026-09-23 13:04:45**；`materials.json` = 同日 13:04:40；`stringreference.json` = 13:04:45；而源 PNG（`emblems/britons.png`）与 `commandpanel.json`/`palette.json` = **2026-09-16 18:37**。
  → `icons.json` 与 `materials.json`/`stringreference.json` **同属最后一次资源构建**，比源美术晚一周。
- exe 里 **`icons.json` 字面量 0 命中**；但字符串池 `0x32E6CA8` 起有一串紧密相邻的量：
  `...Writing file %s.icons...` `%03d` `StatIcons` `uiwidgetutils SendIconName` `DialogSelectIcon` `uiwidgetutils SendIconUnlockRequirements` `Setting up UI Widget Manager` `TimeLineTexture` `MapViewTexture` `combined` `basic_bold_16` `combined_sansserif` `Registering Json parsers` `PlayerIconBorderBronze/Silver/Gold` `MedalRankBronze/Silver/Gold` `Unspecified`
  → 引擎**有**"用 `%03d` 拼图标名"的机制，且有 `SendIconName` / `SendIconUnlockRequirements` 两个 UI 指令，还有 `Writing file %s.icons`（写出 `.icons` 的动作）。全树无 `.icons` 文件 → 该写出路径本机未触发。
- **诚实边界**：不能断言 `icons.json` 就是"由构建脚本从这些规则生成的名字表"，只能说**它、`materials.json`、`stringreference.json` 是同一批构建输出，且 exe 不按文件名引用它**（引擎按裸名 `icons` 找，与 `materials`/`stringreference` 同模式）。**这个推论未验证。**

---

## 7. 对工具的直接后果

1. **图标解析可以做到零猜测**：89.2% 已坐实，每条规则都有物理文件存在性作证。
2. **必须按段分派路由**（材质名 / 文件名 / 带前缀文件名），**不能统一处理**。
3. **必须硬编码两张小别名表**（`CIV_ALIAS` 2 条、`STAT_ALIAS` 3 条）—— 这些是数据里的不规则处，推导不出来。
4. **必须区分三类"失败"**：
   - `号位超界`（`Units` 206 条）→ 报"预留槽，本版无贴图"
   - `占位符`（`Techs` 5 条 `Xxx`）→ 报"未启用"
   - `真缺口`（`Techs` 1 条 `Cartography`、`InGameCivEmblem` 1 条 `berber`）→ 报"数据不一致"
   - `整段无落地`（`Notification`/`MenuIcons`）→ 报"本版不支持"
5. **改图标的落点**：
   - 属性图标 → `widgetui/textures/ingame/staticons/*.png`
   - 游戏内文明徽章 → `widgetui/textures/ingame/emblems/<civ>.png`
   - 菜单文明徽章/科技树/历史/地图图标 → `resources/_common/wpfg/resources/{civ_emblems,civ_techtree,history,mapicons}/`
   - 单位/建筑/科技图标 → 图集切片，走 `icons.json` 号位 → 材质 → 图集 UV

## 8. 未解项

- `Notification` / `MenuIcons` 两段（11 条）的落地机制未定论。
- `icons.json` 是否为构建产物未验证（只有时间戳与字符串池的间接证据）。
- `CivHero` 段（66 条，值 `civ_hero_<civ>`）**无对应贴图文件**；但全树有 **1,154 个含 `hero` 的文件**（如 `u_hero_pyrrhus_attackA_x1.sld`、`modes/Pompeii/...`）→ 有英雄**精灵**，无英雄**图标**。该段如何被消费未解。
