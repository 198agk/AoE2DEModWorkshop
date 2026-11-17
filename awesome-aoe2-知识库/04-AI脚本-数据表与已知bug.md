# AI 脚本侧数据表（对象 / 科技 / 单位线 / load-if / SN 编号 / 赛事 / 已知 bug）

> 出处：https://airef.github.io/ —— `tables/*`、`strategic-numbers/sn-index-by-id`、`events/events-index`、`resources/res-index`
> 数据源：站点是纯静态壳，全部数据在 `js/commands.js`（2,023,772 B / 56727 行）里以 `var x = new Command(...)` 构造。
> 本卷由 `_probe/_tmp/airef_flat.json`（node vm 执行 commands.js 后导出，115 个数组）生成。
> 抓取：2026-11-08

---

## 0. 怎么用这一卷

| 你要做的事 | 查哪一节 |
|---|---|
| 在 `.per` 里写 `(load-if ...)` 需要确切符号名 | §1 |
| 想按「兵营/靶场/马厩」找单位 ID | §3（`building` 列） |
| 查某个 AI 命令里的 `aiName`（如 `archer`、`knight`） | §3 / §4 的 `aiName` 列 |
| 查科技 ID 与研究所 | §4 |
| 查 `.per` 里的单位线（`unit-line` 参数） | §2 |
| 想找空闲 SN 当自定义 goal 用 | §5 |
| 找 AI 脚本赛事的对手/规则 | §6 |
| 找外部工具与教程 | §7 |
| 避开已报的引擎 bug | §8 |

> **重要更正**：页面文件名里的 `bfg` 不是 Star Wars Galactic Battlegrounds，而是 **Chronicles: Battle for Greece**（编年史 DLC）。对应数组后缀 `Chr`。
> `ROR` = Return of Rome（罗马归来 DLC）。

---

## 1. load-if 符号（17 组 / 430 个）

`load-if` 是 `.per` 里的**编译期条件**：写在 `#load-if-defined` / `#load-if-not-defined` 后面，只在条件成立的局里编译进 AI。
符号之间不能互换组（例如时代符号不能当文明符号用）。

| # | 组名 | type 字段 | 符号数 |
|---|---|---|---|
| 1 | Game Type | `Game Type` | 20 |
| 2 | Starting/Ending Age | `Start/End Age` | 9 |
| 3 | Starting Resources | `Starting Resources` | 6 |
| 4 | Map Size | `Map Size` | 22 |
| 5 | Victory | `Victory` | 6 |
| 6 | Difficulty | `Difficulty` | 6 |
| 7 | Population Cap | `Pop Cap` | 10 |
| 8 | Game Version | `Game Version` | 13 |
| 9 | Players & Teams | `Players & Teams` | 16 |
| 10 | Custom RMS | `Custom RMS` | 5 |
| 11 | Reveal Map | `Reveal Map` | 4 |
| 12 | Other | `Other` | 7 |
| 13 | Civs (AoE2) | `AoE2 Civs` | 57 |
| 14 | Civs (Chronicles) | `Chronicles Civs` | 6 |
| 15 | Civs (Return of Rome) | `RoR Civs` | 18 |
| 16 | Map Type (AoE2) | `AoE2 Maps` | 197 |
| 17 | Map Type (Return of Rome) | `RoR Maps` | 28 |

### 1.x 各组全部符号（含官方说明）

#### 1.1 Game Type（20）

| 符号 | 说明 |
|---|---|
| `DEATH-MATCH` | Death Match game. |
| `RANDOM-MAP` | Random Map game. |
| `REGICIDE` | Regicide game. |
| `KING-OF-THE-HILL` | King of the Hill game. CPSB incorrectly states "KING". |
| `WONDER-RACE` | Wonder Race game. CPSB incorrectly states "WONDER RACE". |
| `DEFEND-WONDER` | Defend the Wonder game. CPSB incorrectly states "DEFEND THE WONDER". |
| `TURBO-RANDOM-MAP` | Turbo random map game. |
| `SUDDEN-DEATH` | Sudden death game. HD/DE only. |
| `CAPTURE-THE-RELIC` | Capture the Relic game. HD/DE only. |
| `BATTLE-ROYALE` | Battle Royale game. DE only. |
| `EMPIRE-WARS` | Empire Wars game. DE only. |
| `TURBO-MODE` | A game where the Turbo Mode checkbox is checked. |
| `SUB-GAME-MODE-EMPIRE-WARS` | A game where the Empire Wars Mode checkbox is checked. |
| `SUB-GAME-MODE-SUDDEN-DEATH` | A game where the Sudden Death Mode checkbox is checked. |
| `SUB-GAME-MODE-REGICIDE` | A game where the Regicide Mode checkbox is checked. |
| `SUB-GAME-MODE-KING-OF-THE-HILL` | A game where the King of the Hill Mode checkbox is checked. |
| `GAME-SPEED-LOCKED` | Game speed is locked. |
| `ALL-TECHS-ENABLED` | All techs enabled. |
| `LAST-MAN-STANDING` | Last Man Standing checked. |
| `BATTLE-ROYALE-TIME-X-MINUTES` | Battle Royale Time Limit, where X is the number of minutes. |


#### 1.2 Starting/Ending Age（9）

`DARK-AGE-START`, `FEUDAL-AGE-START`, `CASTLE-AGE-START`, `IMPERIAL-AGE-START`, `POST-IMPERIAL-AGE-START`, `DARK-AGE-END`, `FEUDAL-AGE-END`, `CASTLE-AGE-END`, `IMPERIAL-AGE-END`


#### 1.3 Starting Resources（6）

| 符号 | 说明 |
|---|---|
| `LOW-RESOURCES-START` | Low resources start (Standard). |
| `MEDIUM-RESOURCES-START` | Medium resources start. |
| `HIGH-RESOURCES-START` | High resources start. |
| `ULTRA-RESOURCES-START` | Ultra resources start. DE only. |
| `INFINITE-RESOURCES-START` | Infinite resources start. DE only. |
| `RANDOM-RESOURCES-START` | Random resources start. DE only. |


#### 1.4 Map Size（22）

| 符号 | 说明 |
|---|---|
| `MINIATURE-MAP-SIZE` | Miniature size map. 80x80 tiles. Requires MORE_MAP_SIZES Steam launch parameter. |
| `TINY-MAP` | Tiny size (2 player) map. 120x120 tiles. |
| `TINY-MAP-SIZE` | Tiny size (2 player) map. 120x120 tiles. |
| `SMALL-MAP` | Small size (3 player) map. 144x144 tiles. |
| `SMALL-MAP-SIZE` | Small size (3 player) map. 144x144 tiles. |
| `MEDIUM-MAP` | Medium size (4 player) map. 168x168 tiles. |
| `MEDIUM-MAP-SIZE` | Medium size map. 168x168 tiles. |
| `NORMAL-MAP` | Normal size (6 player) map. 200x200 tiles. |
| `NORMAL-MAP-SIZE` | Normal size map. 200x200 tiles. |
| `LARGE-MAP` | Large size (8 player) map. 220x220 tiles. |
| `LARGE-MAP-SIZE` | Large size map. 220x220 tiles. |
| `GIANT-MAP` | Huge size map. 240x240 tiles. DE changed the name of 240x240 tile map to Huge. GIANT-MAP refers to the Huge map for backwards compatibility with old AIs. |
| `HUGE-MAP-SIZE` | Huge size map. 240x240 tiles. |
| `GIANT-MAP-SIZE` | Giant size map. 252x252 tiles. Requires MORE_MAP_SIZES Steam launch parameter. |
| `MASSIVE-MAP-SIZE` | Massive size map. 276x276 tiles. Requires MORE_MAP_SIZES Steam launch parameter. |
| `ENORMOUS-MAP-SIZE` | Enormous size map. 300x300 tiles. Requires MORE_MAP_SIZES Steam launch parameter. |
| `COLOSSAL-MAP-SIZE` | Colossal size map. 320x320 tiles. Requires MORE_MAP_SIZES Steam launch parameter. |
| `INCREDIBLE-MAP-SIZE` | Incredible size map. 360x360 tiles. Requires MORE_MAP_SIZES Steam launch parameter. |
| `MONSTROUS-MAP-SIZE` | Monstrous size map. 400x400 tiles. Requires MORE_MAP_SIZES Steam launch parameter. |
| `LUDIKRIS-MAP` | Ludicrous size map (notice the spelling!). 480x480 tiles. |
| `LUDICROUS-MAP` | Ludicrous size map. 480x480 tiles. |
| `LUDICROUS-MAP-SIZE` | Ludicrous size map. 480x480 tiles. |


#### 1.5 Victory（6）

| 符号 | 说明 |
|---|---|
| `VICTORY-STANDARD` | Standard victory by Conquest, wonders, or relics. |
| `VICTORY-CONQUEST` | Victory by Conquest only. |
| `VICTORY-TIME-LIMIT` | Victory by having the best score by the time limit. |
| `VICTORY-SCORE` | Victory by reaching a certain score. |
| `VICTORY-CUSTOM` | Custom victories, such as scenarios. Probably |
| `VICTORY-RELICS` | Victory by Relics only. |


#### 1.6 Difficulty（6）

| 符号 | 说明 |
|---|---|
| `DIFFICULTY-EASIEST` | Easiest difficulty. |
| `DIFFICULTY-EASY` | Standard difficulty. |
| `DIFFICULTY-MODERATE` | Moderate difficulty. |
| `DIFFICULTY-HARD` | Hard difficulty. |
| `DIFFICULTY-HARDEST` | Hardest difficulty. |
| `DIFFICULTY-EXTREME` | Extreme difficulty. DE only. |


#### 1.7 Population Cap（10）

| 符号 | 说明 |
|---|---|
| `POPULATION-CAP-25` | 25 population cap. |
| `POPULATION-CAP-50` | 50 population cap. |
| `POPULATION-CAP-75` | 75 population cap. |
| `POPULATION-CAP-100` | 100 population cap. |
| `POPULATION-CAP-125` | 125 population cap. |
| `POPULATION-CAP-150` | 150 population cap. |
| `POPULATION-CAP-175` | 175 population cap. |
| `POPULATION-CAP-200` | 200 population cap <strong>or higher</strong>. |
| `POPULATION-CAP-X` | Population cap = X, substitute X for the desired pop cap. |
| `POPULATION-CAP-EXTENDED` | Population cap > 200. |


#### 1.8 Game Version（13）

| 符号 | 说明 |
|---|---|
| `UP-GAME-[NAME]` | Substitute [NAME] with the expansion name. |
| `UP-GAME-AGE2-X1` | The Conquerors expansion. |
| `UP-GAME-AGE2-X2` | The Age of Forgotten Empires mod (not the official AoF expansion). |
| `UP-GAME-WK` | Wololo Kingdoms expansion. Also defined for DE. |
| `UP-AVAILABLE` | Userpatch version 1.1 and later. Also defined for DE. |
| `UP-VERSION-1.5` | Userpatch version 1.5. Also defined for DE. |
| `UP-VERSION-1.4` | Userpatch version 1.4 and later. Also defined for DE. |
| `UP-VERSION-1.3` | Userpatch version 1.3 and later. Also defined for DE. |
| `UP-VERSION-1.2` | Userpatch version 1.2 and later. Also defined for DE. |
| `UP-VERSION-1.1` | Userpatch version 1.1 and later. Also defined for DE. |
| `DE-AVAILABLE` | Definitive Edition game version. |
| `DE-GAME-AGE2` | The AoE2 mode (always loaded in DE unless playing the AoE1 mode of Return of Rome). |
| `DE-GAME-ROME` | The AoE1 mode of the Return of Rome DLC. |


#### 1.9 Players & Teams（16）

| 符号 | 说明 |
|---|---|
| `TEAMS-LOCKED` | Locked teams. |
| `TEAM-TOGETHER` | Team Together option is selected. |
| `UP-PLAYER-[1-8]` | Likely defined only if the AI's player slot number matches the [1-8]. |
| `UP-[NAME]-CIV-ALLY` | Defined if the player has an ally of the given civ at the start of the game. Replace [NAME] with a civ name, like UP-TEUTONIC-CIV-ALLY. |
| `UP-[NAME]-CIV-ENEMY` | Defined if the player has an enemy (or neutral) of the given civ at the start of the game. Replace [NAME] with a civ name. Also defined for neutral players. |
| `UP-[1-8]-PLAYER-GAME` | Total number of players in the game. Replace [1-8] with the number of players you want to specify. |
| `UP-[1-8]-PLAYER-TEAM` | Number of players on the AI's team. Replace [1-8] with the number of players you want to specify. |
| `UP-ALLY-IN-GAME` | Defined if the player has an ally at the start of the game. |
| `UP-MULTIPLE-ENEMIES` | Defined if the player has more than one enemy. |
| `UP-TEAM-DISADVANTAGE` | Defined if an enemy team is larger. |
| `UP-POCKET-POSITION` | The player is a pocket (positioned between two allied players). |
| `UP-HUMAN-IN-GAME` | Defined if there is a human player in the game. |
| `UP-HUMAN-ALLY` | Defined if the player has a human ally. |
| `UP-HUMAN-ENEMY` | Defined if the player has a human enemy. |
| `UP-COMPUTER-ALLY` | Defined if the player has a computer ally. |
| `UP-COMPUTER-ENEMY` | Defined if the player has a computer enemy. |


#### 1.10 Custom RMS（5）

| 符号 | 说明 |
|---|---|
| `CUSTOM-MAP` | Any custom random map that doesn't use ai_info_map_type. |
| `UP-NOMAD-STYLE` | Custom maps that define the map style as Nomad with ai_info_map_type. |
| `UP-MICHI-STYLE` | Custom maps that define the map style as Michi with ai_info_map_type. |
| `UP-NOMAD-RESOURCES` | Custom maps that set nomad_resources to give players extra wood and stone (extra resources in built-in Nomad is hard-coded and does not set this). |
| `UP-GROUPED-BY-TEAM` | Custom maps that set grouped_by_team to start team players in close proximity to each other. |


#### 1.11 Reveal Map（4）

| 符号 | 说明 |
|---|---|
| `REVEAL-NORMAL` | Normal reveal start. |
| `REVEAL-EXPLORED` | Explored reveal start. |
| `REVEAL-ALL-VISIBLE` | All Visible reveal start. |
| `REVEAL-NO-FOG` | There is no fog of war, but the AI still has to explore the map. |


#### 1.12 Other（7）

| 符号 | 说明 |
|---|---|
| `UP-MULTIPLAYER-GAME` | Multiplayer game. |
| `UP-PROCESS-60FPS` | 60 frames per second enabled (instead of the 20 fps in AoC). |
| `SCENARIO-MAP` | Use UP-SCENARIO-GAME instead since scenarios have the option of setting a map type (Arabia, etc.). |
| `UP-SCENARIO-GAME` | Defined for custom scenario games, even if the scenario sets the AI Info Map Type. |
| `FE-CAMPAIGN-GAME` | Defined for scenarios that are part of official game campaigns that are released with the game. |
| `FE-CUSTOM-CAMPAIGN` | Defined for scenarios that are part of a custom campaign mod. |
| `DE-SOLID-FARMS` | Defined if a game version is loaded that has unwalkable farms (i.e. Return of Rome). |


#### 1.13 Civs (AoE2)（57）

| 符号 | 说明 |
|---|---|
| `GAIA` | Gaia civ. |
| `ARMENIANS-CIV` | Armenians civ. |
| `AZTEC-CIV` | Aztecs civ. |
| `BENGALIS-CIV` | Bengalis civ. |
| `BERBERS-CIV` | Berbers civ. |
| `BRITON-CIV` | Britons civ. |
| `BOHEMIANS-CIV` | Bohemians civ. |
| `BULGARIANS-CIV` | Bulgarians civ. |
| `BURGUNDIANS-CIV` | Burgundians civ. |
| `BURMESE-CIV` | Burmese civ. |
| `BYZANTINE-CIV` | Byzantines civ. |
| `CELTIC-CIV` | Celts civ. |
| `CHINESE-CIV` | Chinese civ. |
| `CUMANS-CIV` | Cumans civ. |
| `DANES-CIV` | Danes civ. |
| `DRAVIDIANS-CIV` | Dravidians civ. |
| `ETHIOPIAN-CIV` | Ethiopians civ. |
| `FRANKISH-CIV` | Franks civ. |
| `GEORGIANS-CIV` | Georgians civ. |
| `GOTHIC-CIV` | Goths civ. |
| `GURJARAS-CIV` | Gurjaras civ. |
| `HUN-CIV` | Huns civ. |
| `INCAN-CIV` | Incas civ. |
| `INDIAN-CIV` | Indians civ. Also defined for Hindustanis civ. |
| `ITALIAN-CIV` | Italians civ. |
| `JAPANESE-CIV` | Japanese civ. |
| `JURCHENS-CIV` | Jurchens civ. |
| `KHITANS-CIV` | Khitans civ. |
| `KHMER-CIV` | Khmer civ. |
| `KOREAN-CIV` | Koreans civ. |
| `LITHUANIANS-CIV` | Lithuanians civ. |
| `MAGYAR-CIV` | Magyars civ. |
| `MALAY-CIV` | Malay civ. |
| `MALIAN-CIV` | Malians civ. |
| `MAPUCHE-CIV` | Mapuche civ. |
| `MAYAN-CIV` | Mayans civ. |
| `MONGOL-CIV` | Mongols civ. |
| `MUISCA-CIV` | Muisca civ. |
| `PERSIAN-CIV` | Persians civ. |
| `POLES-CIV` | Poles civ. |
| `PORTUGUESE-CIV` | Portuguese civ. |
| `ROMANS-CIV` | Romans civ. |
| `SARACEN-CIV` | Saracens civ. |
| `SAXONS-CIV` | Saxons civ. |
| `SHU-CIV` | Shu civ. |
| `SICILIANS-CIV` | Sicilians civ. |
| `SLAVIC-CIV` | Slavs civ. |
| `SPANISH-CIV` | Spanish civ. |
| `TATARS-CIV` | Tatars civ. |
| `TEUTONIC-CIV` | Teutons civ. |
| `TUPI-CIV` | Tupi civ. |
| `TURKISH-CIV` | Turks civ. |
| `VARANGIANS-CIV` | Varangians civ. |
| `VIETNAMESE-CIV` | Vietnamese civ. |
| `VIKING-CIV` | Vikings civ. |
| `WEI-CIV` | Wei civ. |
| `WU-CIV` | Wu civ. |


#### 1.14 Civs (Chronicles)（6）

| 符号 | 说明 |
|---|---|
| `ACHAEMENIDS-CIV` | Achaemenids civ. |
| `ATHENIANS-CIV` | Athenians civ. |
| `MACEDONIANS-CIV` | Macedonians civ. |
| `PURU-CIV` | Puru civ. |
| `SPARTANS-CIV` | Spartans civ. |
| `THRACIANS-CIV` | Macedonians civ. |


#### 1.15 Civs (Return of Rome)（18）

`GAIA`, `ASSYRIAN-CIV`, `BABYLONIAN-CIV`, `CARTHAGIAN-CIV`, `CHOSON-CIV`, `EGYPTIAN-CIV`, `GREEK-CIV`, `HITTITE-CIV`, `LAC-VIET-CIV`, `MACEDONIAN-CIV`, `MINOAN-CIV`, `PALMYRAN-CIV`, `PERSIAN-CIV`, `PHOENICIAN-CIV`, `ROMAN-CIV`, `SHANG-CIV`, `SUMERIAN-CIV`, `YAMATO-CIV`


#### 1.16 Map Type (AoE2)（197）

| 符号 | 说明 |
|---|---|
| `ACCLIVITY-MAP` | Acclivity map. Defined only in DE. |
| `ACROPOLIS-MAP` | Acropolis map. Defined only in DE. |
| `AFRICAN-CLEARING-MAP` | African Clearing map. Defined only in DE. |
| `AFTERMATH-MAP` | Aftermath map. Defined only in DE. |
| `ALPINE-LAKES-MAP` | Alpine Lakes map. Defined only in DE. |
| `AMAZON-TUNNEL-MAP` | Amazon Tunnel map. Defined only in DE. |
| `AQUARENA-MAP` | Aquarena map. Defined only in DE. |
| `ARABIA-MAP` | Arabia map. |
| `ARABIAN-DESERT-MAP` | Arabian Desert map. |
| `ARCHIPELAGO-MAP` | Archipelago map. |
| `ARENA-MAP` | Arena map. |
| `ATACAMA-MAP` | Acatama map. Defined only in DE. |
| `BALTIC-MAP` | Baltic map. |
| `BLACK-FOREST-MAP` | Black Forest map. |
| `BOG-ISLANDS-MAP` | Bog Islands map. Defined only in DE. |
| `BOGLAND-MAP` | Bogland map. Defined only in DE. |
| `BORDER-DISPUTE-MAP` | Border Dispute map. Defined only in DE. |
| `BUDAPEST-MAP` | Budapest map. Defined only in DE. |
| `CENOTES-MAP` | Cenotes map. Defined only in DE. |
| `CHAOS-PIT-MAP` | Chaos Pit map. Defined only in DE. |
| `CITYOFLAKES-MAP` | City of Lakes map. Defined only in DE. |
| `CLIFFBOUND-MAP` | Cliffbound map. Defined only in DE. |
| `COASTAL-MAP` | Coastal map. |
| `COASTAL-FOREST-MAP` | Coastal Forest map. Defined only in DE. |
| `CONTINENTAL-MAP` | Continental map. |
| `CRATER-MAP` | Crater map. Defined only in DE. |
| `CRATER-LAKE-MAP` | Crater Lake map. |
| `CROSSROADS-MAP` | Crossroads map. Defined only in DE. |
| `CROWNWOOD-MAP` | Crownwood map. Defined only in DE. |
| `DUNESPRINGS-MAP` | Dunesprings map. Defined only in DE. |
| `DOROTHEA-QUARRY-MAP` | Dorothea Quarry map. Defined only in DE. |
| `ENCLOSED-MAP` | Enclosed map. Defined only in DE. |
| `ERUPTION-MAP` | Eruption map. Defined only in DE. |
| `FORTIFIED-CLEARING-MAP` | Fortified Clearing map. Defined only in DE. |
| `FORTRESS-MAP` | Fortress map. |
| `FOUR-LAKES-MAP` | Four Lakes map. Defined only in DE. |
| `FRIGID-LAKE-MAP` | Frigid Lake map. Defined only in DE. |
| `GHOST-LAKE-MAP` | Ghost Lake map. |
| `GLACIS-MAP` | Glacis map. Defined only in DE. |
| `GLADE-MAP` | Glade map. Defined only in DE. |
| `GOLD-RUSH-MAP` | Gold Rush map. |
| `GOLDENPIT-MAP` | Golden Pit map. Defined only in DE. |
| `GOLDEN-STREAM-MAP` | Golden Stream map. Defined only in DE. |
| `GOLDEN-SWAMP-MAP` | Golden Swamp map. Defined only in DE. |
| `GRAUPEL-MAP` | Graupel map. Defined only in DE. |
| `GREENLAND-MAP` | Greenland map. Defined only in DE. |
| `HABOOB-MAP` | Haboob map. Defined only in DE. |
| `HAMBURGER-MAP` | Hamburger map. Defined only in DE. |
| `HENGEHOLD-MAP` | Hengehold map. Defined only in DE. |
| `HIDEOUT-MAP` | Hideout map. Defined only in DE. |
| `HIGHLAND-MAP` | Highland map. |
| `HILLFORT-MAP` | Hill Fort map. Defined only in DE. |
| `HOLLOW-WOODLANDS-MAP` | Hollow Woodlands map. Defined only in DE. |
| `ISLANDS-MAP` | Islands map. |
| `ISTHMUS-MAP` | Isthmus map. Defined only in DE. |
| `KARSTS-MAP` | Karsts map. Defined only in DE. |
| `KAWASAN-MAP` | Kawasan map. Defined only in DE. |
| `KILIMANJARO-MAP` | Kilimanjaro map. Defined only in DE. |
| `LAND-MADNESS-MAP` | Land Madness map. Defined only in DE. |
| `LAND-NOMAD-MAP` | Land Nomad map. Defined only in DE. |
| `LOCH-NESS-MAP` | Loch Ness map. Defined only in DE. |
| `LOMBARDIA-MAP` | Lombardia map. Defined only in DE. |
| `LOWLAND-MAP` | Lowland map. Defined only in DE. |
| `MANGROVE-JUNGLE-MAP` | Mangrove Jungle map. Defined only in DE. |
| `MARKETPLACE-MAP` | Marketplace map. Defined only in DE. |
| `MEADOW-MAP` | Meadow map. Defined only in DE. |
| `MEDITERRANEAN-MAP` | Mediterranean map. |
| `MEGARANDOM-MAP` | MegaRandom map. Defined only in DE. |
| `MICHI-MAP` | Michi map. Defined only in DE. |
| `MIGRATION-MAP` | Migration map. |
| `MIRED-MAP` | Mired map. Defined only in DE. |
| `MONGOLIA-MAP` | Mongolia map. |
| `MORASS-MAP` | Morass map. Defined only in DE. |
| `MOUNTAIN-DUNES-MAP` | Mountain Dunes map. Defined only in DE. |
| `MOUNTAIN-PASS-MAP` | Mountain Pass map. Defined only in DE. |
| `MOUNTAIN-RANGE-MAP` | Mountain Range map. Defined only in DE. |
| `MOUNTAIN-RIDGE-MAP` | Mountain Ridge map. Defined only in DE. |
| `MURKWOOD-MAP` | Murkwood map. Defined only in DE. |
| `NILE-DELTA-MAP` | Nile Delta map. Defined only in DE. |
| `NOMAD-MAP` | Nomad map. |
| `NORTHERN-ISLES-MAP` | Northern Isles map. Defined only in DE. |
| `OASIS-MAP` | Oasis map. |
| `PACIFIC-ISLANDS-MAP` | Pacific Islands map. Defined only in DE. |
| `PASSAGE-MAP` | Passage map. Defined only in DE. |
| `RAMPART-MAP` | Rampart map. Defined only in DE. |
| `RAVINES-MAP` | Ravines map. Defined only in DE. |
| `RING-FORTRESS-MAP` | Ring Fortress map. Defined only in DE. |
| `RIVER-DIVIDE-MAP` | River Divide map. Defined only in DE. |
| `RIVERS-MAP` | Rivers map. |
| `RUNESTONES-MAP` | Runestones map. Defined only in DE. |
| `SACRED-SPRINGS-MAP` | Sacred Springs map. Defined only in DE. |
| `SALT-MARSH-MAP` | Salt Marsh map. |
| `SANDBANK-MAP` | Sandbank map. Defined only in DE. |
| `SANDRIFT-MAP` | Sandrift map. Defined only in DE. |
| `SARDIS-MAP` | Sardis map. Defined only in DE. |
| `SCANDANAVIA-MAP` | Scandinavia map. Notice the spelling! |
| `SEIZE-THE-MOUNTAIN-MAP` | Seize The Mountain map. Defined only in DE. |
| `SERENGETI-MAP` | Serengeti map. Defined only in DE. |
| `SHOALS-MAP` | Shoals map. Defined only in DE. |
| `SHRUBLAND-MAP` | Shrubland map. Defined only in DE. |
| `SOCOTRO-MAP` | Socotra map. Defined only in DE. Notice the spelling! |
| `STEPPE-MAP` | Steppe map. Defined only in DE. |
| `STONEFRONT-MAP` | Stonefront map. Defined only in DE. |
| `STRANDED-MAP` | Stranded map. Defined only in DE. |
| `TEAM-ISLANDS-MAP` | Team Islands map. |
| `TEAM-MOATS-MAP` | Team Moats map. Defined only in DE. |
| `THAMES-MAP` | Thames map. Defined only in DE. |
| `VALLEY-MAP` | Valley map. Defined only in DE. |
| `VOLCANIC-ISLAND-MAP` | Volcanic Island map. Defined only in DE. |
| `VULPINE-MAP` | Vulpine map. Defined only in DE. |
| `WADE-MAP` | Wade map. Defined only in DE. |
| `WATER-NOMAD-MAP` | Water Nomad map. Defined only in DE. |
| `WOLF-HILL-MAP` | Wolf Hill map. Defined only in DE. |
| `YUCATAN-MAP` | Yucatan map. |
| `CANALS-MAP` | Canals ES map. |
| `CAPRICIOUS-MAP` | Capricious ES map. |
| `DINGOS-MAP` | Dingos ES map. |
| `GRAVEYARDS-MAP` | Graveyards ES map. |
| `METROPOLIS-MAP` | Metropolis ES map. |
| `MOATS-MAP` | Moats ES map. |
| `PARADISE-ISLAND-MAP` | Paradise Island ES map. |
| `PILGRIMS-MAP` | Pilgrims ES map. |
| `PRAIRIE-MAP` | Prairie ES map. |
| `SEASONS-MAP` | Seasons ES map. |
| `SHERWOOD-FOREST-MAP` | Sherwood Forest ES map. |
| `SHERWOOD-HEROES-MAP` | Sherwood Heroes ES map. |
| `SHIPWRECK-MAP` | Shipwreck ES map. |
| `TEAM-GLACIERS-MAP` | Team Glaciers ES map. |
| `THE-UNKNOWN-MAP` | The Unknown ES map. |
| `QUICKPLAY_ARABIA-MAP` | Quick Play Arabia map. Defined only in DE. Notice the underscore after QUICKPLAY. |
| `QUICKPLAY_ARENA-MAP` | Quick Play Arena map. Defined only in DE. Notice the underscore after QUICKPLAY. |
| `QUICKPLAY_BLACK-FOREST-MAP` | Quick Play Black Forest map. Defined only in DE. Notice the underscore after QUICKPLAY. |
| `QUICKPLAY_FORTIFIED-CLEARING-MAP` | Quick Play Fortified Clearing map. Defined only in DE. Notice the underscore after QUICKPLAY. |
| `QUICKPLAY_GLADE-MAP` | Quick Play Glade map. Defined only in DE. Notice the underscore after QUICKPLAY. |
| `QUICKPLAY_NOMAD-MAP` | Quick Play Nomad map. Defined only in DE. Notice the underscore after QUICKPLAY. |
| `QUICKPLAY_RUNESTONES-MAP` | Quick Play Runestones map. Defined only in DE. Notice the underscore after QUICKPLAY. |
| `CTR_RANDOM-MAP` | Capture the Relic random map. Notice the underscore after CTR. |
| `CTR_MONSOON-MAP` | Capture the Relic Monsoon map. Notice the underscore after CTR. |
| `CTR_PYRAMID-DESCENT-MAP` | Capture the Relic Pyramid Descent map. Notice the underscore after CTR. |
| `CTR_SPIRAL-MAP` | Capture the Relic Spiral map. Notice the underscore after CTR. |
| `BATTLE-ON-THE-ICE-MAP` | Battle on the Ice Battle Royale map. |
| `EL-DORADO-MAP` | El Dorado Battle Royale map. |
| `FALL-OF-AXUM-MAP` | Fall of Axum Battle Royale map. |
| `FALL-OF-ROME-MAP` | Fall of Rome Battle Royale map. |
| `THE-MAJAPHIT-EMPIRE-MAP` | The Majapahit Empire Battle Royale map. Notice the spelling! |
| `REAL-WORLD-AMAZON-MAP` | Real World Amazon map. Defined only in DE. |
| `REAL-WORLD-ANTARCTICA-MAP` | Real World Antarctica map. Defined only in DE. |
| `REAL-WORLD-ARAL-SEA-MAP` | Real World Aral Sea map. Defined only in DE. |
| `REAL-WORLD-AUSTRALIA-MAP` | Real World Australia map. Defined only in DE. |
| `REAL-WORLD-BLACK-SEA-MAP` | Real World Black Sea map. Defined only in DE. |
| `REAL-WORLD-BOHEMIA-MAP` | Real World Bohemia map. Defined only in DE. |
| `REAL-WORLD-BYZANTIUM-MAP` | Real World Byzantium map. |
| `REAL-WORLD-CARIBBEAN-MAP` | Real World Central America map. |
| `REAL-WORLD-CAUCASUS-MAP` | Real World Caucasus map. Defined only in DE. |
| `REAL-WORLD-CHINA-MAP` | Real World China map. Defined only in DE. |
| `REAL-WORLD-ENGLAND-MAP` | Real World Britain map. |
| `REAL-WORLD-FRANCE-MAP` | Real World France map. |
| `REAL-WORLD-HORN-OF-AFRICA-MAP` | Real World Horn of Africa map. Defined only in DE. |
| `REAL-WORLD-INDIA-MAP` | Real World India map. Defined only in DE. |
| `REAL-WORLD-INDOCHINA-MAP` | Real World Indochina map. Defined only in DE. |
| `REAL-WORLD-INDONESIA-MAP` | Real World Indonesia map. Defined only in DE. |
| `REAL-WORLD-ITALY-MAP` | Real World Italy map. |
| `REAL-WORLD-JUTLAND-MAP` | Real World Norse Lands map. |
| `REAL-WORLD-MADAGASCAR-MAP` | Real World Madagascar map. Defined only in DE. |
| `REAL-WORLD-MALACCA-MAP` | Real World Malacca map. Defined only in DE. |
| `REAL-WORLD-MANCHURIA-MAP` | Real World Manchuria map. Defined only in DE. |
| `REAL-WORLD-MIDEAST-MAP` | Real World Mideast map. |
| `REAL-WORLD-NIPPON-MAP` | Real World Sea of Japan (East Sea) map. |
| `REAL-WORLD-PHILIPPINES-MAP` | Real World Philippines map. Defined only in DE. |
| `REAL-WORLD-SIBERIA-MAP` | Real World Siberia map. Defined only in DE. |
| `REAL-WORLD-SPAIN-MAP` | Real World Iberia map. |
| `REAL-WORLD-STRAIT-OF-MALACCA-MAP` | Real World Strait of Malacca map. Defined only in DE. |
| `REAL-WORLD-TEXAS-MAP` | Real World Texas map. |
| `REAL-WORLD-WEST-AFRICA-MAP` | Real World West Africa map. Defined only in DE. |
| `REAL-WORLD-WORLD-MAP` | Real World Earth map. Defined only in DE. |
| `BORDER-STONES-SPECIAL-MAP` | Border Stones special map. |
| `CANYONS-SPECIAL-MAP` | Canyons special map. |
| `ENEMY-ARCHIPELAGO-SPECIAL-MAP` | Enemy Archipelago special map. |
| `ENEMY-ISLANDS-SPECIAL-MAP` | Enemy Islands special map. |
| `FAR-OUT-SPECIAL-MAP` | Far Out special map. |
| `FOREST-BREACH-SPECIAL-MAP` | Forest Breach special map. |
| `FRONT-LINE-SPECIAL-MAP` | Front Line special map. |
| `HOLY-LINE-SPECIAL-MAP` | Holy Line special map. |
| `INNER-CIRCLE-SPECIAL-MAP` | Inner Circle special map. |
| `JOURNEY-SOUTH-SPECIAL-MAP` | Journey South special map. |
| `JUNGLE-ISLANDS-SPECIAL-MAP` | Jungle Islands special map. |
| `JUNGLE-LANES-SPECIAL-MAP` | Jungle Lanes special map. |
| `MOTHERLAND-SPECIAL-MAP` | Motherland special map. |
| `OPEN-PLAINS-SPECIAL-MAP` | Open Plains special map. |
| `RING-OF-WATER-SPECIAL-MAP` | Ring of Water special map. |
| `SNAKE-FOREST-SPECIAL-MAP` | Snake Forest special map. |
| `SNAKE-PIT-SPECIAL-MAP` | Snake Pit special map. |
| `SPRAWLING-STREAMS-SPECIAL-MAP` | Sprawling Streams special map. |
| `SWIRLING-RIVER-SPECIAL-MAP` | Swirling River special map. |
| `THE-EYE-SPECIAL-MAP` | The Eye special map. |
| `TWIN-FORESTS-SPECIAL-MAP` | Twin Forests special map. |
| `YIN-YANG-SPECIAL-MAP` | Yin Yang special map. |


#### 1.17 Map Type (Return of Rome)（28）

| 符号 | 说明 |
|---|---|
| `ALLIANCE-MAP` | Alliance map. |
| `CITADEL-MAP` | Citadel map. |
| `CLEARING-MAP` | Clearing map. |
| `POMPEIICOASTAL-MAP` | Coastal map (Return of Rome version). |
| `POMPEIICONTINENTAL-MAP` | Continental map (Return of Rome version). |
| `DARKFOREST-MAP` | Dark Forest map. |
| `DESERTRIDGE-MAP` | Desert Ridge map. |
| `GOLDMOUNTAIN-MAP` | Gold Mountain map. |
| `POMPEIIHIGHLAND-MAP` | Highland map (Return of Rome version). |
| `HILLCOUNTRY-MAP` | Hill Country map. |
| `INLAND-MAP` | Inland map. |
| `INSIDEOUT-MAP` | Inside Out map. |
| `POMPEIILANDNOMAD-MAP` | Land Nomad map (Return of Rome version). |
| `LARGEISLANDS-MAP` | Large Islands map. |
| `POMPEIIMEDITERRANEAN-MAP` | Mediterranean map (Return of Rome version). |
| `POMPEIIMEGARANDOM-MAP` | MegaRandom map (Return of Rome version). |
| `MUDDYWATERS-MAP` | Muddy Waters map. |
| `NARROWS-MAP` | Narrows map. |
| `POMPEIINOMAD-MAP` | Nomad map (Return of Rome version). |
| `POMPEIIOASIS-MAP` | Oasis map (Return of Rome version). |
| `OCEANCHANNEL-MAP` | Ocean Channel map. |
| `OCEANRING-MAP` | Ocean Ring map. |
| `PLATEAUS-MAP` | Plateaus map. |
| `RIVERCROSSING-MAP` | River Crossing map. |
| `POMPEIIRIVERS-MAP` | Rivers map (Return of Rome version). |
| `SAHARA-MAP` | Sahara map. |
| `SMALLISLANDS-MAP` | Small Islands map. |
| `TWINSETTLEMENTS-MAP` | Twin Settlements map. |


---

## 2. 单位线 Unit Lines（117）

`.per` 里凡是吃 `unit-line` 的命令（`unit-type-count-total` 的线变体、`up-train` 的线参数等）都用这里的名字。
**负数是 DE 新增线的内部线 ID**，`id` 为 `NA` 表示只在 DE 里有、AoC 时代没有对应编号。

| # | 线名 | id | DE id | 说明 |
|---|---|---|---|---|
| 1 | `stone-wall-line` | -399 | -399 | Stone Wall line. In Return of Rome, it includes Medium Wall and Fortified Wall, but not Small Wall. |
| 2 | `watch-tower-line` | -398 | -398 | Watch Tower line. Bugged. Won't include Guard Tower or Keep in counting commands. "watch-tower" by itself usually works in non-counting commands. In Return of Rome, it includes Watch Tower, Sentry Tower, Guard Tower, but not Ballista Tower. |
| 3 | `outpost-line` | NA | -310 | Outpost line. Includes Outpost and Fortified Outpost (Chronicles only). |
| 4 | `mounted-crossbowman-line` | NA | -315 | DE only. Includes Mounted Crossbowman and Heavy Mounted Crossbowman. |
| 5 | `jomsviking-line` | NA | -314 | DE only. Includes Jomsviking and Elite Jomsviking. |
| 6 | `jarl-line` | NA | -313 | DE only. Includes Jarl and Elite Jarl. |
| 7 | `hearth-troop-line` | NA | -312 | DE only. Includes Hearth Troop and Elite Hearth Troop. |
| 8 | `varangian-guard-line` | NA | -311 | DE only. Includes Varangian Guard and Elite Varangian Guard. |
| 9 | `war-dog-line` | NA | -309 | DE only. Includes War Dog and Elite War Dog. |
| 10 | `hulk-line` | NA | -308 | DE only. Includes Hulk, War Hulk, and Carrack. |
| 11 | `blackwood-archer-line` | NA | -307 | DE only. Includes Blackwood Archer and Elite Blackwood Archer. |
| 12 | `kona-line` | NA | -306 | DE only. Includes Kona and Elite Kona. |
| 13 | `guecha-warrior-line` | NA | -305 | DE only. Includes Guecha Warrior and Elite Guecha Warrior. |
| 14 | `ibirapema-warrior-line` | NA | -304 | DE only. Includes Ibirapema Warrior and Elite Ibirapema Warrior. |
| 15 | `temple-guard-line` | NA | -303 | DE only. Includes Temple Guard and Elite Temple Guard. |
| 16 | `bolas-rider-line` | NA | -302 | DE only. Includes Bolas Rider and elite Bolas Rider. |
| 17 | `champi-line` | NA | -301 | DE only. Includes Champi Scout, Champi Runner, Champi Warrior, and Elite Champi Warrior. |
| 18 | `sannahya-line` | NA | -300 | Chronciles only. Includes Sannahya and Elite Sannahya. |
| 19 | `archer-line` | -299 | -299 | Includes archer, crossbowman, and arbalest. In Return of Rome, it includes Bowman. |
| 20 | `cavalry-archer-line` | -298 | -298 | Includes cavalry-archer and heavy-cavalry-archer. In Return of Rome, -298 is the improved bowman line, including Improved Bowman and Composite Bowman. |
| 21 | `skirmisher-line` | -297 | -297 | Includes skirmisher and elite-skirmisher. DE also includes imperial-skirmisher. WK does not. |
| 22 | `militiaman-line` | -296 | -296 | Includes militiaman, man-at-arms, long-swordsman, two-handed-swordsman, and champion. DE also includes legionary. |
| 23 | `spearman-line` | -295 | -295 | Includes spearman, pikeman, and halberdier. In Return of Rome, -295 is the cavalry line, including Cavalry, Heavy Cavalry, and Cataphract. |
| 24 | `demolition-ship-line` | -294 | -294 | Includes demolition-raft (WK and DE), demolition-ship (not WK), and heavy-demolition-ship. In Return of Rome, -294 is the swordsmen line, including Short Swordsman, Broad Swordsman, Long Swordsman, and Legionary. |
| 25 | `fire-ship-line` | -293 | -293 | Includes fire-galley (WK and DE), fire-ship (not WK), fast-fire-ship. In Return of Rome, -293 is the horse archer line, including Horse Archer and Heavy Horse Archer. |
| 26 | `galley-line` | -292 | -292 | Includes galley, war-galley, and galleon. In Return of Rome, -292 is the war elephant line, including War Elephant and Armored Elephant. |
| 27 | `battering-ram-line` | -291 | -291 | Includes battering-ram, capped-ram, and siege-ram. Also includes feudal-battering-ram in DE. In Return of Rome, -291 is the chariot line, including Chariot and Scythe Chariot. |
| 28 | `mangonel-line` | -290 | -290 | Includes mangonel, onager (not WK), and siege-onager. In Return of Rome, -290 is the hoplite line, including Hoplite, Phalangite, and Centurion. |
| 29 | `scorpion-line` | -289 | -289 | Includes scorpion and heavy-scorpion. In Return of Rome, -289 is the ballista line, including Ballista and Helepolis. |
| 30 | `camel-line` | -288 | -288 | Includes camel and heavy-camel. DE also includes camel-scout and imperial-camel. In Return of Rome, -288 is the stone thrower line, including Stone Thrower, Catapult, and Heavy Catapult. |
| 31 | `knight-line` | -287 | -287 | Includes knight, cavalier, paladin, and savar. In Return of Rome, -287 is the fishing boat line, including Fishing Boat and Fishing Ship. |
| 32 | `scout-cavalry-line` | -286 | -286 | Includes scout-cavalry, light-cavalry, and hussar. DE also includes winged-hussar. In Return of Rome, -286 is the transport line, including Light Transport and Heavy Transport. |
| 33 | `cannon-galleon-line` | -285 | -284 | Includes cannon-galleon and elite-cannon-galleon. In Return of Rome, -285 is the scout ship line, including Scout Ship, War Galley, and Trireme. |
| 34 | `longboat-line` | -284 | -283 | Includes longboat and elite-longboat. In Return of Rome, -284 is the catapult trireme line, including Catapult Trireme and Juggernaut. |
| 35 | `turtle-ship-line` | -283 | -282 | Includes turtle-ship and elite-turtle-ship. In Return of Rome, -283 is the trade boat line, including Trade Boat and Merchant Ship. |
| 36 | `berserk-line` | -282 | -281 | Includes berserk and elite-berserk. |
| 37 | `cataphract-line` | -281 | -280 | Includes cataphract and elite-cataphract. |
| 38 | `chu-ko-nu-line` | -280 | -279 | Includes chu-ko-nu and elite-chu-ko-nu. |
| 39 | `huskarl-line` | -279 | -278 | Includes huskarl and elite-huskarl. Doesn't include huskarls trained at the Barracks. |
| 40 | `janissary-line` | -278 | -277 | Includes janissary and elite-janissary. |
| 41 | `longbowman-line` | -277 | -276 | Includes longbowman and elite-longbowman. |
| 42 | `mameluke-line` | -276 | -275 | Includes mameluke and elite-mameluke. |
| 43 | `mangudai-line` | -275 | -274 | Includes mangudai and elite-mangudai. |
| 44 | `samurai-line` | -274 | -273 | Includes samurai and elite-samurai. |
| 45 | `teutonic-knight-line` | -273 | -272 | Includes teutonic-knight and elite-teutonic-knight. |
| 46 | `throwing-axeman-line` | -272 | -271 | Includes throwing-axeman and elite-throwing-axeman. |
| 47 | `war-elephant-line` | -271 | -270 | Includes war-elephant and elite-war-elephant. |
| 48 | `war-wagon-line` | -270 | -269 | Includes war-wagon and elite-war-wagon. |
| 49 | `woad-raider-line` | -269 | -268 | Includes woad-raider and elite-woad-raider. |
| 50 | `jaguar-man-line` | -268 | -267 | Note the spelling! jaguar-warrior-line can also be used in DE. Includes jaguar-warrior and elite-jaguar-warrior. |
| 51 | `eagle-warrior-line` | -267 | -266 | Includes eagle-warrior (the Eagle Scout in WK and DE) and elite-eagle-warrior. DE also includes heavy-eagle-warrior (the Castle Age Eagle Warrior). WK does not. |
| 52 | `plumed-archer-line` | -266 | -265 | Includes plumed-archer and elite-plumed-archer. In Return of Rome, -266 is the clubman line, including Clubman and Axeman. |
| 53 | `tarkan-line` | -265 | -264 | Includes tarkan and elite-tarkan. Does not include tarkans trained at the Stable. |
| 54 | `conquistador-line` | -264 | -263 | Includes conquistador and elite-conquistador. |
| 55 | `camel-archer-line` | NA | -285 | DE only. Includes camel-archer and elite-camel-archer. |
| 56 | `genoese-crossbowman-line` | NA | -262 | DE only. Includes genoese-crossbowman and elite-genoese-crossbowman. |
| 57 | `elephant-archer-line` | NA | -261 | DE only. Includes elephant-archer and elite-elephant-archer. |
| 58 | `boyar-line` | NA | -260 | DE only. Includes boyar and elite-boyar. |
| 59 | `magyar-huszar-line` | NA | -259 | DE only. Includes magyar-huszar and elite-magyar-huszar. |
| 60 | `kamayuk-line` | NA | -258 | Includes kamayuk and elite-kamayuk. |
| 61 | `caravel-line` | NA | -257 | DE only. Includes caravel and elite-caravel. |
| 62 | `organ-gun-line` | NA | -256 | DE only. Includes organ-gun and elite-organ-gun. |
| 63 | `gbeto-line` | NA | -255 | DE only. Includes gbeto and elite-gbeto. |
| 64 | `shotel-warrior-line` | NA | -254 | DE only. Includes shotel-warrior and elite-shotel-warrior. |
| 65 | `genitour-line` | NA | -253 | DE only. Includes genitour and elite-genitour. |
| 66 | `ballista-elephant-line` | NA | -252 | DE only. Includes ballista-elephant and elite-ballista-elephant. |
| 67 | `rattan-archer-line` | NA | -251 | DE only. Includes rattan-archer and elite-rattan-archer. |
| 68 | `arambai-line` | NA | -250 | DE only. Includes arambai and elite-arambai. |
| 69 | `battle-elephant-line` | NA | -249 | DE only. Includes battle-elephant and elite-battle-elephant. |
| 70 | `karambit-warrior-line` | NA | -248 | DE only. Includes karambit-warrior and elite-karambit-warrior. |
| 71 | `konnik-line` | NA | -247 | DE only. Includes konnik and elite-konnik. Does not include dismounted konniks or konniks trained from Kreposts. |
| 72 | `krepost-konnik-line` | NA | -246 | No longer used. Technically includes krepost-konnik and elite-krepost-konnik, but these unit IDs are only used to tell the AI to train konniks from the krepost. Standard konniks, not krepost konniks will actually be trained. Does not include konniks trained at the castle or dismounted konniks. |
| 73 | `foot-konnik-line` | NA | -245 | DE only. Includes foot-konnik and elite-foot-konnik. Does not include mounted konniks. |
| 74 | `leitis-line` | NA | -244 | DE only. Includes leitis and elite-leitis. |
| 75 | `kipchak-line` | NA | -243 | DE only. Includes kipchak and elite-kipchak. Does not include kipchaks that allies can train after Cuman Mercenaries is researched. |
| 76 | `keshik-line` | NA | -242 | DE only. Includes keshik and elite-keshik. |
| 77 | `steppe-lancer-line` | NA | -241 | DE only. Includes steppe-lancer and elite-steppe-lancer. |
| 78 | `coustillier-line` | NA | -240 | DE only. Includes coustillier and elite-coustillier. |
| 79 | `serjeant-line` | NA | -239 | DE only. Includes serjeant and elite-serjeant. |
| 80 | `donjon-serjeant-line` | NA | -238 | No longer used. Technically includes donjon-serjeant and elite-donjon-serjeant, but these unit IDs are only used to tell the AI to train serjeants from the donjon. Standard serjeants, not donjon serjeants will actually be trained. |
| 81 | `obuch-line` | NA | -237 | DE only. Includes obuch and elite-obuch. |
| 82 | `hussite-wagon-line` | NA | -236 | DE only. Includes hussite-wagon and elite-hussite-wagon. |
| 83 | `bombard-cannon-line` | NA | -235 | DE only. Includes bombard-cannon and houfnice. |
| 84 | `urumi-swordsman-line` | NA | -234 | DE only. Includes urumi-swordsman and elite-urumi-swordsman. |
| 85 | `ratha-melee-line` | NA | -233 | DE only. Includes ratha-melee and elite-ratha-melee. Does not include rathas in ranged mode. Use ratha-set to include ranged rathas. |
| 86 | `chakram-thrower-line` | NA | -232 | DE only. Includes chakram-thrower and elite-chakram-thrower. |
| 87 | `armored-elephant-line` | NA | -231 | DE only. Includes armored-elephant and siege-elephant. |
| 88 | `ghulam-line` | NA | -230 | DE only. Includes ghulam and elite-ghulam. |
| 89 | `shrivamsha-rider-line` | NA | -229 | DE only. Includes shrivamsha-rider and elite-shrivamsha-rider. |
| 90 | `ratha-ranged-line` | NA | -228 | DE only. Includes ratha-ranged and elite-ratha-ranged. Does not include rathas in melee mode. Use ratha-set to include melee rathas. |
| 91 | `donjon-spearman-line` | NA | -227 | No longer used. Technically includes donjon-spearman, donjon-pikeman, and donjon-halberdier, but these unit IDs are only used to tell the AI to train spearmen from the donjon. Standard spearmen, not donjon spearmen will actually be trained. |
| 92 | `centurion-line` | NA | -226 | DE only. Includes centurion and elite-centurion. |
| 93 | `composite-bowman-line` | NA | -225 | DE only. Includes composite-bowman and elite-composite-bowman. |
| 94 | `monaspa-line` | NA | -224 | DE only. Includes monaspa and elite-monaspa. |
| 95 | `qizilbash-warrior-line` | NA | -223 | DE only. Includes qizilbash-warrior and elite-qizilbash-warrior. The unit line and individual units aren't defined in the AI engine. |
| 96 | `immortal-line` | NA | -222 | Chronicles only. Includes immortal and elite-immortal. Does not include ranged immortals. |
| 97 | `strategos-line` | NA | -221 | Chronicles only. Includes strategos and elite-strategos. |
| 98 | `hippeus-line` | NA | -220 | Chronicles only. Includes hippeus and elite-hippeus. |
| 99 | `hoplite-line` | NA | -219 | Chronicles only. Includes hoplite and elite-hoplite. |
| 100 | `war-chariot-line` | NA | -218 | Chronicles only. Includes war-chariot and elite-war-chariot. |
| 101 | `lembos-line` | NA | -217 | Chronicles only. Includes lembos, war-lembos, heavy-lembos, and elite-lembos. |
| 102 | `monoreme-line` | NA | -216 | Chronicles only. Includes monoreme, bireme, and trireme. |
| 103 | `ancient-galley-line` | NA | -215 | Chronicles only. Includes galley (antiquity), war-galley (antiquity), and elite-galley. |
| 104 | `incendiary-ship-line` | NA | -214 | Chronicles only. Includes incendiary-raft, incendiary-ship, and heavy-incendiary-ship. |
| 105 | `catapult-ship-line` | NA | -213 | Chronicles only. Includes catapult-ship and onager-ship. |
| 106 | `hei-guang-cavalry-line` | NA | -211 | DE only. Includes hei-guang-cavalry and heavy-hei-guang-cavalry. |
| 107 | `tiger-cavalry-line` | NA | -210 | DE only. Includes tiger-cavalry and elite-tiger-cavalry. |
| 108 | `white-feather-guard-line` | NA | -209 | DE only. Includes white-feather-guard and elite-white-feather-guard. |
| 109 | `fire-archer-line` | NA | -208 | DE only. Includes fire-archer and elite-fire-archer. |
| 110 | `fire-lancer-line` | NA | -207 | DE only. Includes fire-lancer and elite-fire-lancer. |
| 111 | `rocket-cart-line` | NA | -206 | DE only. Includes rocket-cart and heavy-rocket-cart. |
| 112 | `iron-pagoda-line` | NA | -205 | DE only. Includes iron-pagoda and elite-iron-pagoda. |
| 113 | `liao-dao-line` | NA | -204 | DE only. Includes liao-dao and elite-liao-dao. |
| 114 | `companion-cavalry-line` | NA | -203 | Chronicles only. Includes companion-cavalry and elite-companion-cavalry. |
| 115 | `phalangite-line` | NA | -202 | Chronicles only. Includes phalangite and elite-phalangite. |
| 116 | `rhomphaia-warrior-line` | NA | -201 | Chronicles only. Includes rhomphaia-warrior and elite-rhomphaia-warrior. |
| 117 | `paddiyodha-longbowman-line` | NA | -200 | Chronicles only. Includes paddiyodha-longbowman and elite-paddiyodha-longbowman. |

另有 `unitLinesArray` 单列 114 条，其中 **78 条 `id` 为 `NA`**（纯 DE 线，没有 AoE2 老编号）；这些已经包含在上表里。

---

## 3. 对象表 Objects

三套平行表：**AoE2 主表**、**Chronicles（`Chr` 后缀）**、**Return of Rome（`ROR` 后缀）**。同一 ID 在三套里含义不同，不能混用。

字段：`id` / `name` / `aiName`（`.per` 里写的名字）/ `line`（单位线）/ `class`（护甲-攻击类，含 class 编号）/ `cmdId` / `building`（生产建筑）/ `age` / `deadUnit`（尸体 ID）/ `projectile`（抛射物 ID）/ `chemProjectile` / `civ`（专属文明）/ `weirdName`（0=正常）/ `notes`。

`aok/tc/wk/de` 四列是版本标记（1=存在）。只有在版本间 ID 变过的对象才带这几列。

### 3.1 AoE2（主表）（19 个分类数组）

原始行 **1596** 条（同一对象会出现在多个分类数组里），按 ID 去重后 **809** 个对象。`分类` 列出它出现过的所有分类。

| ID | 名称 | aiName | 线 | 类 | 建筑 | 时代 | 专属文明 | 分类 |
|---|---|---|---|---|---|---|---|---|
| 4 | Archer | archer | archer-line | archery-class (900) | Archery Range | 2 |  | Range |
| 24 | Crossbowman | crossbowman | archer-line | archery-class (900) | Archery Range | 3 |  | Range |
| 492 | Arbalest | arbalest, arbalester (DE only) | archer-line | archery-class (900) | Archery Range | 4 |  | Range |
| 7 | Skirmisher | skirmisher | skirmisher-line | archery-class (900) | Archery Range | 2 |  | Range |
| 6 | Elite Skirmisher | elite-skirmisher | skirmisher-line | archery-class (900) | Archery Range | 3 |  | Range |
| WK: 762 / DE: 1155 | Imperial Skirmisher | imperial-skirmisher | skirmisher-line | archery-class (900) | Archery Range | 4 | Vietnamese | Range |
| 39 | Cavalry Archer | cavalry-archer | cavalry-archer-line | cavalry-archer-class (936) | Archery Range | 3 |  | Range |
| 474 | Heavy Cavalry Archer | heavy-cavalry-archer | cavalry-archer-line | cavalry-archer-class (936) | Archery Range | 4 |  | Range |
| 2700 | Mounted Crossbowman |  | mounted-crossbowman-line | cavalry-archer-class (936) | Archery Range | 3 |  | Range |
| 2701 | Heavy Mounted Crossbowman |  | mounted-crossbowman-line | cavalry-archer-class (936) | Archery Range | 4 |  | Range |
| 873 | Elephant Archer | elephant-archer | elephant-archer-line | cavalry-archer-class (936) | Archery Range | 3 |  | Range, Castle |
| 875 | Elite Elephant Archer | elite-elephant-archer | elephant-archer-line | cavalry-archer-class (936) | Archery Range | 4 |  | Range, Castle |
| 2569 | Bolas Rider |  | bolas-rider-line | cavalry-archer-class (936) | Archery Range | 3 | Mapuche | Range |
| 2571 | Elite Bolas Rider |  | bolas-rider-line | cavalry-archer-class (936) | Archery Range | 4 | Mapuche | Range |
| 1952 | Xianbei Raider |  |  | cavalry-archer-class (936) | Archery Range | 3 |  | Range |
| WK: 223 / DE: 1010 | Genitour | genitour | genitour-line | cavalry-archer-class (936) | Archery Range | 3 | Berbers | Range |
| WK: 230 / DE: 1012 | Elite Genitour | elite-genitour | genitour-line | cavalry-archer-class (936) | Archery Range | 4 | Berbers | Range |
| 732 | Genitour (Placeholder) |  |  | cavalry-archer-class (936) | Archery Range | 3 |  | Range |
| 185 | Slinger | slinger |  | archery-class (900) | Archery Range | 3 |  | Range |
| 1911 | Grenadier |  |  | archery-cannon-class (944) | Archery Range | 3 | Jurchens | Range |
| 5 | Hand Cannoneer | hand-cannoneer |  | archery-cannon-class (944) | Archery Range | 4 |  | Range |
| 74 | Militia | militiaman, militia (DE only) | militiaman-line | infantry-class (906) | Barracks | 1 |  | Barracks |
| 75 | Man-at-Arms | man-at-arms | militiaman-line | infantry-class (906) | Barracks | 2 |  | Barracks |
| 77 | Long Swordsman | long-swordsman | militiaman-line | infantry-class (906) | Barracks | 3 |  | Barracks |
| 473 | Two-Handed Swordsman | two-handed-swordsman | militiaman-line | infantry-class (906) | Barracks | 4 |  | Barracks |
| 567 | Champion | champion | militiaman-line | infantry-class (906) | Barracks | 4 |  | Barracks |
| 1793 | Legionary | legionary | militiaman-line | infantry-class (906) | Barracks | 4 | Romans | Barracks |
| 2550 | Champi Scout |  | champi-line | infantry-class (906) | Barracks | 1 |  | Barracks |
| 2588 | Champi Runner |  | champi-line | infantry-class (906) | Barracks | 2 |  | Barracks |
| 2552 | Champi Warrior |  | champi-line | infantry-class (906) | Barracks | 3 |  | Barracks |
| 2554 | Elite Champi Warrior |  | champi-line | infantry-class (906) | Barracks | 4 |  | Barracks |
| 93 | Spearman | spearman | spearman-line | infantry-class (906) | Barracks | 2 |  | Barracks |
| 358 | Pikeman | pikeman | spearman-line | infantry-class (906) | Barracks | 3 |  | Barracks |
| 359 | Halberdier | halberdier | spearman-line | infantry-class (906) | Barracks | 4 |  | Barracks |
| 751 | Eagle Scout (non-TC)/ / Eagle Warrior (TC) | eagle-warrior | eagle-warrior-line | infantry-class (906) | Barracks | 2/3 |  | Barracks |
| 753 | Eagle Warrior | heavy-eagle-warrior | eagle-warrior-line | infantry-class (906) | Barracks | 3 |  | Barracks |
| 752 | Elite Eagle Warrior | elite-eagle-warrior | eagle-warrior-line | infantry-class (906) | Barracks | 4 |  | Barracks |
| 1901 | Fire Lancer |  | fire-lancer-line | infantry-class (906) | Barracks | 3 |  | Barracks |
| 1903 | Elite Fire Lancer |  | fire-lancer-line | infantry-class (906) | Barracks | 4 |  | Barracks |
| 2703 | Varangian Guard |  | varangian-guard-line | infantry-class (906) | Barracks | 3 |  | Barracks |
| 2704 | Elite Varangian Guard |  | varangian-guard-line | infantry-class (906) | Barracks | 4 |  | Barracks |
| 2586 | Temple Guard |  | temple-guard-line | infantry-class (906) | Barracks | 3 | Muisca | Barracks |
| 2587 | Elite Temple Guard |  | temple-guard-line | infantry-class (906) | Barracks | 4 | Muisca | Barracks |
| 2582 | Ibirapema Warrior |  | ibirapema-warrior-line | infantry-class (906) | Barracks | 3 | Tupi | Barracks |
| 2584 | Elite Ibirapema Warrior |  | ibirapema-warrior-line | infantry-class (906) | Barracks | 4 | Tupi | Barracks |
| 1699 | Flemish Militia (Train) | town-center-flemish-pikeman |  | infantry-class (906) | Barracks | 2 | Burgundians | Barracks |
| 1974 | Jian Swordsman (Healthy) |  |  | infantry-class (906) | Barracks | 3 | Wu | Barracks |
| 1976 | Jian Swordsman (Injured) |  |  | infantry-class (906) | Barracks | 3 | Wu | Barracks |
| 882 | Condottiero | condottiero |  | infantry-class (906) | Barracks | 4 | Italians | Barracks |
| 184 | Condottiero (Placeholder) |  |  | infantry-class (906) | Barracks | 4 | Italians | Barracks |
| 759 | Huskarl (Barracks) |  |  | infantry-class (906) | Barracks | 3 | Goths | Barracks |
| 761 | Elite Huskarl (Barracks) |  |  | infantry-class (906) | Barracks | 4 | Goths | Barracks |
| 2612 | War Dog |  | war-dog-line | infantry-class (906) | Barracks | 1 |  | Barracks |
| 2613 | Elite War Dog |  | war-dog-line | infantry-class (906) | Barracks | 4 |  | Barracks |
| 331 | Trebuchet (Packed) | trebuchet |  | packed-trebuchet-class (951) | Castle | 4 |  | Castle, Fort |
| 42 | Trebuchet (Unpacked) |  |  | unpacked-trebuchet-class (954) | Castle | 4 |  | Castle, Fort |
| 440 | Petard | petard |  | petard-class (935) | Castle | 3 |  | Castle |
| 1800 | Composite Bowman | composite-bowman | composite-bowman-line | archery-class (900) | Castle | 3 | Armenians | Castle |
| 1802 | Elite Composite Bowman | elite-composite-bowman | composite-bowman-line | archery-class (900) | Castle | 4 | Armenians | Castle |
| 725 | Jaguar Warrior | jaguar-man, jaguar-warrior (DE only) | jaguar-man-line | infantry-class (906) | Castle | 3 | Aztecs | Castle |
| 726 | Elite Jaguar Warrior | elite-jaguar-man, elite-jaguar-warrior (DE only) | jaguar-man-line | infantry-class (906) | Castle | 4 | Aztecs | Castle |
| 1759 | Ratha (Ranged) | ratha-ranged | ratha-ranged-line | cavalry-archer-class (936) | Castle | 3 | Bengalis | Castle |
| 1738 | Ratha (Melee) | ratha-melee | ratha-melee-line | cavalry-class (912) | Castle | 3 | Bengalis | Castle |
| 1761 | Elite Ratha (Ranged) | elite-ratha-ranged | ratha-ranged-line | cavalry-archer-class (936) | Castle | 4 | Bengalis | Castle |
| 1740 | Elite Ratha (Melee) | elite-ratha-melee | ratha-melee-line | cavalry-class (912) | Castle | 4 | Bengalis | Castle |
| WK: 203 / DE: 1007 | Camel Archer | camel-archer | camel-archer-line | cavalry-archer-class (936) | Castle | 3 | Berbers | Castle |
| WK: 208 / DE: 1009 | Elite Camel Archer | elite-camel-archer | camel-archer-line | cavalry-archer-class (936) | Castle | 4 | Berbers | Castle |
| 8 | Longbowman | longbowman | longbowman-line | archery-class (900) | Castle | 3 | Britons | Castle |
| 530 | Elite Longbowman | elite-longbowman | longbowman-line | archery-class (900) | Castle | 4 | Britons | Castle |
| 1704 | Hussite Wagon | hussite-wagon | hussite-wagon-line | scorpion-class (955) | Castle | 3 | Bohemians | Castle |
| 1706 | Elite Hussite Wagon | elite-hussite-wagon | hussite-wagon-line | scorpion-class (955) | Castle | 4 | Bohemians | Castle |
| 1225 | Konnik | konnik | konnik-line | cavalry-class (912) | Castle | 3 | Bulgarians | Castle |
| 1227 | Elite Konnik | elite-konnik | konnik-line | cavalry-class (912) | Castle | 4 | Bulgarians | Castle |
| 1252 | Konnik (Dismounted) | foot-konnik | foot-konnik-line | infantry-class (906) | Castle | 3 | Bulgarians | Castle |
| 1253 | Elite Konnik (Dismounted) | elite-foot-konnik | foot-konnik-line | infantry-class (906) | Castle | 4 | Bulgarians | Castle |
| 1655 | Coustillier | coustillier | coustillier-line | cavalry-class (912) | Castle | 3 | Burgundians | Castle |
| 1657 | Elite Coustillier | elite-coustillier | coustillier-line | cavalry-class (912) | Castle | 4 | Burgundians | Castle |
| WK: 823 / DE: 1126 | Arambai | arambai | arambai-line | cavalry-cannon-class (923) | Castle | 3 | Burmese | Castle |
| WK: 811 / DE: 1128 | Elite Arambai | elite-arambai | arambai-line | cavalry-cannon-class (923) | Castle | 4 | Burmese | Castle |
| 40 | Cataphract | cataphract | cataphract-line | cavalry-class (912) | Castle | 3 | Byzantines | Castle |
| 553 | Elite Cataphract | elite-cataphract | cataphract-line | cavalry-class (912) | Castle | 4 | Byzantines | Castle |
| 232 | Woad Raider | woad-raider | woad-raider-line | infantry-class (906) | Castle | 3 | Celts | Castle |
| 534 | Elite Woad Raider | elite-woad-raider | woad-raider-line | infantry-class (906) | Castle | 4 | Celts | Castle |
| 73 | Chu Ko Nu | chu-ko-nu | chu-ko-nu-line | archery-class (900) | Castle | 3 | Chinese | Castle |
| 559 | Elite Chu Ko Nu | elite-chu-ko-nu | chu-ko-nu-line | archery-class (900) | Castle | 4 | Chinese | Castle |
| 1231 | Kipchak | kipchak | kipchak-line | cavalry-archer-class (936) | Castle | 3 | Cumans | Castle |
| 1233 | Elite Kipchak | elite-kipchak | kipchak-line | cavalry-archer-class (936) | Castle | 4 | Cumans | Castle |
| 1260 | Elite Kipchak (Mercenary) | mercenary-kipchak |  | cavalry-archer-class (936) | Castle | 4 |  | Castle |
| 1259 | Elite Kipchak (Mercenary Placeholder) |  |  | cavalry-archer-class (936) | Castle | 4 |  | Castle |
| 2711 | Jomsviking |  | jomsviking-line | infantry-class (906) | Castle | 3 | Danes | Castle |
| 2712 | Elite Jomsviking |  | jomsviking-line | infantry-class (906) | Castle | 4 | Danes | Castle |
| 1735 | Urumi Swordsman | urumi-swordsman | urumi-swordsman-line | infantry-class (906) | Castle | 3 | Dravidians | Castle |
| 1737 | Elite Urumi Swordsman | elite-urumi-swordsman | urumi-swordsman-line | infantry-class (906) | Castle | 4 | Dravidians | Castle |
| WK: 453 / DE: 1016 | Shotel Warrior | shotel, shotel-warrior | shotel-warrior-line | infantry-class (906) | Castle | 3 | Ethiopians | Castle |
| WK: 459 / DE: 1018 | Elite Shotel Warrior | elite-shotel, elite-shotel-warrior | shotel-warrior-line | infantry-class (906) | Castle | 4 | Ethiopians | Castle |
| 281 | Throwing Axeman | throwing-axeman | throwing-axeman-line | infantry-class (906) | Castle | 3 | Franks | Castle |
| 531 | Elite Throwing Axeman | elite-throwing-axeman | throwing-axeman-line | infantry-class (906) | Castle | 4 | Franks | Castle |
| 1803 | Monaspa | monaspa | monaspa-line | cavalry-class (912) | Castle | 3 | Georgians | Castle |
| 1805 | Elite Monaspa | elite-monaspa | monaspa-line | cavalry-class (912) | Castle | 4 | Georgians | Castle |
| 41 | Huskarl | huskarl | huskarl-line | infantry-class (906) | Castle | 3 | Goths | Castle |
| 555 | Elite Huskarl | elite-huskarl | huskarl-line | infantry-class (906) | Castle | 4 | Goths | Castle |
| 1741 | Chakram Thrower | chakram-thrower | chakram-thrower-line | infantry-class (906) | Castle | 3 | Gurjaras | Castle |
| 1743 | Elite Chakram Thrower | elite-chakram-thrower | chakram-thrower-line | infantry-class (906) | Castle | 4 | Gurjaras | Castle |
| 1747 | Ghulam | ghulam | ghulam-line | infantry-class (906) | Castle | 3 | Hindustanis | Castle |
| 1749 | Elite Ghulam | elite-ghulam | ghulam-line | infantry-class (906) | Castle | 4 | Hindustanis | Castle |
| 755 | Tarkan | tarkan | tarkan-line | cavalry-class (912) | Castle | 3 | Huns | Castle |
| 757 | Elite Tarkan | elite-tarkan | tarkan-line | cavalry-class (912) | Castle | 4 | Huns | Castle |
| 879 | Kamayuk | kamayuk | kamayuk-line | infantry-class (906) | Castle | 3 | Incas | Castle |
| 881 | Elite Kamayuk | elite-kamayuk | kamayuk-line | infantry-class (906) | Castle | 4 | Incas | Castle |
| 866 | Genoese Crossbowman | genoese-crossbowman | genoese-crossbowman-line | archery-class (900) | Castle | 3 | Italians | Castle |
| 868 | Elite Genoese Crossbowman | elite-genoese-crossbowman | genoese-crossbowman-line | archery-class (900) | Castle | 4 | Italians | Castle |
| 291 | Samurai | samurai | samurai-line | infantry-class (906) | Castle | 3 | Japanese | Castle |
| 560 | Elite Samurai | elite-samurai | samurai-line | infantry-class (906) | Castle | 4 | Japanese | Castle |
| 1908 | Iron Pagoda | iron-pagoda | iron-pagoda-line | cavalry-class (912) | Castle | 3 | Jurchens | Castle |
| 1910 | Elite Iron Pagoda | elite-iron-pagoda | iron-pagoda-line | cavalry-class (912) | Castle | 4 | Jurchens | Castle |
| 1920 | Liao Dao | liao-dao | liao-dao-line | infantry-class (906) | Castle | 3 | Khitans | Castle |
| 1922 | Elite Liao Dao | elite-liao-dao | liao-dao-line | infantry-class (906) | Castle | 4 | Khitans | Castle |
| WK: 760 / DE: 1120 | Ballista Elephant | ballista-elephant | ballista-elephant-line | cavalry-class (912) | Castle | 3 | Khmer | Castle |
| WK: 891 / DE: 1122 | Elite Ballista Elephant | elite-ballista-elephant | ballista-elephant-line | cavalry-class (912) | Castle | 4 | Khmer | Castle |
| 827 | War Wagon | war-wagon | war-wagon-line | cavalry-archer-class (936) | Castle | 3 | Koreans | Castle |
| 829 | Elite War Wagon | elite-war-wagon | war-wagon-line | cavalry-archer-class (936) | Castle | 4 | Koreans | Castle |
| 1234 | Leitis | leitis | leitis-line | cavalry-class (912) | Castle | 3 | Lithuanians | Castle |
| 1236 | Elite Leitis | elite-leitis | leitis-line | cavalry-class (912) | Castle | 4 | Lithuanians | Castle |
| 869 | Magyar Huszar | magyar-huszar | magyar-huszar-line | cavalry-class (912) | Castle | 3 | Magyars | Castle |
| 871 | Elite Magyar Huszar | elite-magyar-huszar | magyar-huszar-line | cavalry-class (912) | Castle | 4 | Magyars | Castle |
| WK: 836 / DE: 1123 | Karambit Warrior | karambit-warrior | karambit-warrior-line | infantry-class (906) | Castle | 3 | Malay | Castle |
| WK: 830 / DE: 1125 | Elite Karambit Warrior | elite-karambit-warrior | karambit-warrior-line | infantry-class (906) | Castle | 4 | Malay | Castle |
| WK: 260 / DE: 1013 | Gbeto | gbeto | gbeto-line | infantry-class (906) | Castle | 3 | Malians | Castle |
| WK: 418 / DE: 1015 | Elite Gbeto | elite-gbeto | gbeto-line | infantry-class (906) | Castle | 4 | Malians | Castle |
| 2566 | Kona |  | kona-line | cavalry-class (912) | Castle | 3 | Mapuche | Castle |
| 2568 | Elite Kona |  | kona-line | cavalry-class (912) | Castle | 4 | Mapuche | Castle |
| 763 | Plumed Archer | plumed-archer | plumed-archer-line | archery-class (900) | Castle | 3 | Mayans | Castle |
| 765 | Elite Plumed Archer | elite-plumed-archer | plumed-archer-line | archery-class (900) | Castle | 4 | Mayans | Castle |
| 11 | Mangudai | mangudai | mangudai-line | cavalry-archer-class (936) | Castle | 3 | Mongols | Castle |
| 561 | Elite Mangudai | elite-mangudai | mangudai-line | cavalry-archer-class (936) | Castle | 4 | Mongols | Castle |
| 2562 | Guecha Warrior |  | guecha-warrior-line | archery-class (900) | Castle | 3 | Muisca | Castle |
| 2564 | Elite Guecha Warrior |  | guecha-warrior-line | archery-class (900) | Castle | 4 | Muisca | Castle |
| 239 | War Elephant | war-elephant | war-elephant-line | cavalry-class (912) | Castle | 3 | Persians | Castle |
| 558 | Elite War Elephant | elite-war-elephant | war-elephant-line | cavalry-class (912) | Castle | 4 | Persians | Castle |
| 1701 | Obuch | obuch | obuch-line | infantry-class (906) | Castle | 3 | Poles | Castle |
| 1703 | Elite Obuch | elite-obuch | obuch-line | infantry-class (906) | Castle | 4 | Poles | Castle |
| WK: 106 / DE: 1001 | Organ Gun | organ-gun | organ-gun-line | siege-weapon-class (913) | Castle | 3 | Portuguese | Castle |
| WK: 114 / DE: 1003 | Elite Organ Gun | elite-organ-gun | organ-gun-line | siege-weapon-class (913) | Castle | 4 | Portuguese | Castle |
| 1790 | Centurion | centurion | centurion-line | cavalry-class (912) | Castle | 3 | Romans | Castle |
| 1792 | Elite Centurion | elite-centurion | centurion-line | cavalry-class (912) | Castle | 4 | Romans | Castle |
| 282 | Mameluke | mameluke | mameluke-line | cavalry-class (912) | Castle | 3 | Saracens | Castle |
| 556 | Elite Mameluke | elite-mameluke | mameluke-line | cavalry-class (912) | Castle | 4 | Saracens | Castle |
| 2705 | Hearth Troop |  | hearth-troop-line | infantry-class (906) | Castle | 3 | Saxons | Castle |
| 1961 | Elite Hearth Troop |  | white-feather-guard-line | infantry-class (906) | Castle | 4 | Saxons | Castle |
| 1959 | White Feather Guard |  | white-feather-guard-line | infantry-class (906) | Castle | 3 | Shu | Castle |
| 1658 | Serjeant | serjeant | serjeant-line | infantry-class (906) | Castle | 2 | Sicilians | Castle |
| 1659 | Elite Serjeant | elite-serjeant | serjeant-line | infantry-class (906) | Castle | 4 | Sicilians | Castle |
| 876 | Boyar | boyar | boyar-line | cavalry-class (912) | Castle | 3 | Slavs | Castle |
| 878 | Elite Boyar | elite-boyar | boyar-line | cavalry-class (912) | Castle | 4 | Slavs | Castle |
| 771 | Conquistador | conquistador | conquistador-line | cavalry-cannon-class (923) | Castle | 3 | Spanish | Castle |
| 773 | Elite Conquistador | elite-conquistador | conquistador-line | cavalry-cannon-class (923) | Castle | 4 | Spanish | Castle |
| 1228 | Keshik | keshik | keshik-line | cavalry-class (912) | Castle | 3 | Tatars | Castle |
| 1230 | Elite Keshik | elite-keshik | keshik-line | cavalry-class (912) | Castle | 4 | Tatars | Castle |
| 1263 | Flaming Camel | flaming-camel |  | petard-class (935) | Castle | 4 | Tatars | Castle |
| 25 | Teutonic Knight | teutonic-knight | teutonic-knight-line | infantry-class (906) | Castle | 3 | Teutons | Castle |
| 554 | Elite Teutonic Knight | elite-teutonic-knight | teutonic-knight-line | infantry-class (906) | Castle | 4 | Teutons | Castle |
| 2579 | Blackwood Archer |  | blackwood-archer-line | archery-class (900) | Castle | 3 | Tupi | Castle |
| 2581 | Elite Blackwood Archer |  | blackwood-archer-line | archery-class (900) | Castle | 4 | Tupi | Castle |
| 46 | Janissary | janissary | janissary-line | archery-cannon-class (944) | Castle | 3 | Turks | Castle |
| 557 | Elite Janissary | elite-janissary | janissary-line | archery-cannon-class (944) | Castle | 4 | Turks | Castle |
| 2708 | Jarl |  | jarl-line | cavalry-class (912) | Castle | 3 | Varangians | Castle |
| 2720 | Elite Jarl |  | jarl-line | cavalry-class (912) | Castle | 4 | Varangians | Castle |
| WK: 784 / DE: 1129 | Rattan Archer | rattan-archer | rattan-archer-line | archery-class (900) | Castle | 3 | Vietnamese | Castle |
| WK: 782 / DE: 1131 | Elite Rattan Archer | elite-rattan-archer | rattan-archer-line | archery-class (900) | Castle | 4 | Vietnamese | Castle |
| 692 | Berserk | berserk | berserk-line | infantry-class (906) | Castle | 3 | Vikings | Castle |
| 694 | Elite Berserk | elite-berserk | berserk-line | infantry-class (906) | Castle | 4 | Vikings | Castle |
| 1949 | Tiger Cavalry | tiger-cavalry | tiger-cavalry-line | cavalry-class (912) | Castle | 3 | Wei | Castle |
| 1951 | Elite Tiger Cavalry | elite-tiger-cavalry | tiger-cavalry-line | cavalry-class (912) | Castle | 4 | Wei | Castle |
| 1968 | Fire Archer | fire-archer | fire-archer-line | archery-class (900) | Castle | 3 | Wu | Castle |
| 1970 | Elite Fire Archer | elite-fire-archer | fire-archer-line | archery-class (900) | Castle | 4 | Wu | Castle |
| 1817 | Qizilbash Warrior |  |  | cavalry-class (912) | Castle | 1 |  | Castle |
| 1829 | Elite Qizilbash Warrior |  |  | cavalry-class (912) | Castle | 1 |  | Castle |
| 2101 | Immortal |  | immortal-line | infantry-class (906) | Fort | 3 | Achaemenids | Fort |
| 2102 | Elite Immortal |  | immortal-line | infantry-class (906) | Fort | 4 | Achaemenids | Fort |
| 2174 | Immortal (Ranged) |  |  | archery-class (900) | Fort | 3 | Achaemenids | Fort |
| 2175 | Elite Immortal (Ranged) |  |  | archery-class (900) | Fort | 4 | Achaemenids | Fort |
| 2104 | Strategos |  | strategos-line | infantry-class (906) | Fort | 3 | Athenians | Fort |
| 2105 | Elite Strategos |  | strategos-line | infantry-class (906) | Fort | 4 | Athenians | Fort |
| 2227 | Strategos (with Taxiarchs) |  | strategos-line | infantry-class (906) | Fort | 3 | Athenians | Fort |
| 2228 | Elite Strategos (with Taxiarchs) |  | strategos-line | infantry-class (906) | Fort | 4 | Athenians | Fort |
| 2382 | Companion Cavalry |  | companion-cavalry-line | cavalry-class (912) | Fort | 3 | Macedonians | Fort |
| 2383 | Elite Companion Cavalry |  | companion-cavalry-line | cavalry-class (912) | Fort | 4 | Macedonians | Fort |
| 2388 | Pattiyodha Longbowman |  | pattiyodha-longbowman-line | archery-class (900) | Fort | 3 | Puru | Fort |
| 2389 | Elite Pattiyodha Longbowman |  | pattiyodha-longbowman-line | archery-class (900) | Fort | 4 | Puru | Fort |
| 2107 | Hippeus |  | hippeus-line | infantry-class (906) | Fort | 3 | Spartans | Fort |
| 2108 | Elite Hippeus |  | hippeus-line | infantry-class (906) | Fort | 4 | Spartans | Fort |
| 2386 | Rhomphaia Warrior |  | rhomphaia-warrior-line | infantry-class (906) | Fort | 3 | Thracians | Fort |
| 2387 | Elite Rhomphaia Warrior |  | rhomphaia-warrior-line | infantry-class (906) | Fort | 4 | Thracians | Fort |
| 13 | Fishing Ship | fishing-ship |  | fishing-ship-class (921) | Dock | 1 |  | Dock |
| 2171 | Oystering Ship |  |  | fishing-ship-class (921) | Dock | 1 |  | Dock, Port |
| 2630 | Whaling Ship |  |  | fishing-ship-class (921) | Dock | 1 |  | Dock, Port |
| 17 | Trade Cog | trade-cog |  | trade-cog-class (902) | Dock | 2 |  | Dock |
| 545 | Transport Ship | transport-ship |  | transport-ship-class (920) | Dock | 2 |  | Dock |
| 539 | Galley | galley | galley-line | warship-class (922) | Dock | 2 |  | Dock |
| 21 | War Galley | war-galley | galley-line | warship-class (922) | Dock | 3 |  | Dock |
| 442 | Galleon | galleon | galley-line | warship-class (922) | Dock | 4 |  | Dock |
| WK: 529 / DE: 1103 | Fire Galley | fire-galley | fire-ship-line | warship-class (922) | Dock | 2 |  | Dock |
| 529 | Fire Ship (non-WK) | fire-ship | fire-ship-line | warship-class (922) | Dock | 3 |  | Dock |
| 467 | Fire Ship (WK) |  |  | warship-class (922) | Dock | 3 |  | Dock |
| 532 | Fast Fire Ship | fast-fire-ship | fire-ship-line | warship-class (922) | Dock | 4 |  | Dock |
| 1302 | Dragon Ship |  | fire-ship-line | warship-class (922) | Dock | 4 | Chinese | Dock |
| WK: 527 / DE: 1104 | Demolition Raft | demo-raft | demolition-ship-line | warship-class (922) | Dock | 2 |  | Dock |
| 527 | Demolition Ship (non-WK) | demolition-ship | demolition-ship-line | warship-class (922) | Dock | 3 |  | Dock |
| 653 | Demolition Ship (WK) |  |  | warship-class (922) | Dock | 3 |  | Dock |
| 528 | Heavy Demolition Ship | heavy-demolition-ship | demolition-ship-line | warship-class (922) | Dock | 4 |  | Dock |
| 2626 | Hulk |  | hulk-line | warship-class (922) | Dock | 2 |  | Dock |
| 2627 | War Hulk |  | hulk-line | warship-class (922) | Dock | 3 |  | Dock |
| 2628 | Carrack |  | hulk-line | warship-class (922) | Dock | 4 |  | Dock |
| 420 | Cannon Galleon | cannon-galleon | cannon-galleon-line | warship-class (922) | Dock | 4 |  | Dock |
| 691 | Elite Cannon Galleon | elite-cannon-galleon | cannon-galleon-line | warship-class (922) | Dock | 4 |  | Dock |
| 1795 | Dromon | dromon |  | warship-class (922) | Dock | 4 |  | Dock |
| 1948 | Lou Chuan |  |  | warship-class (922) | Dock | 4 |  | Dock |
| 2633 | Catapult Galleon |  |  | warship-class (922) | Dock | 4 |  | Dock |
| 1750 | Thirisadai | thirisadai |  | warship-class (922) | Dock | 4 | Dravidians | Dock |
| 831 | Turtle Ship | turtle-ship | turtle-ship-line | warship-class (922) | Dock | 3 | Koreans | Dock |
| 832 | Elite Turtle Ship | elite-turtle-ship | turtle-ship-line | warship-class (922) | Dock | 4 | Koreans | Dock |
| WK: 861 / DE: 1004 | Caravel | caravel | caravel-line | warship-class (922) | Dock | 3 | Portuguese | Dock |
| WK: 183 / DE: 1006 | Elite Caravel | elite-caravel | caravel-line | warship-class (922) | Dock | 4 | Portuguese | Dock |
| 250 | Longboat | longboat | longboat-line | warship-class (922) | Dock | 3 | Vikings | Dock |
| 533 | Elite Longboat | elite-longboat | longboat-line | warship-class (922) | Dock | 4 | Vikings | Dock |
| 2147 | Fishing Ship (Antiquity) |  |  | fishing-ship-class (921) | Port | 1 |  | Port |
| 2149 | Merchant Ship |  |  | trade-cog-class (902) | Port | 2 |  | Port |
| 2148 | Transport Ship (Antiquity) |  |  | transport-ship-class (920) | Port | 1 |  | Port |
| 2123 | Lembos |  | lembos-line | warship-class (922) | Shipyard | 1 |  | Shipyard |
| 2124 | War Lembos |  | lembos-line | warship-class (922) | Shipyard | 2 |  | Shipyard |
| 2125 | Heavy Lembos |  | lembos-line | warship-class (922) | Shipyard | 3 |  | Shipyard |
| 2126 | Elite Lembos |  | lembos-line | warship-class (922) | Shipyard | 4 |  | Shipyard |
| 2127 | Monoreme |  | monoreme-line | warship-class (922) | Shipyard | 2 |  | Shipyard |
| 2128 | Bireme |  | monoreme-line | warship-class (922) | Shipyard | 3 |  | Shipyard |
| 2129 | Trireme |  | monoreme-line | warship-class (922) | Shipyard | 4 |  | Shipyard |
| 2130 | Galley (Antiquity) |  | ancient-galley-line | warship-class (922) | Shipyard | 2 |  | Shipyard |
| 2131 | War Galley (Antiquity) |  | ancient-galley-line | warship-class (922) | Shipyard | 3 |  | Shipyard |
| 2132 | Elite Galley |  | ancient-galley-line | warship-class (922) | Shipyard | 4 |  | Shipyard |
| 2133 | Incendiary Raft |  | incendiary-raft-line | warship-class (922) | Shipyard | 2 |  | Shipyard |
| 2134 | Incendiary Ship |  | incendiary-raft-line | warship-class (922) | Shipyard | 3 |  | Shipyard |
| 2135 | Heavy Incendiary Ship |  | incendiary-raft-line | warship-class (922) | Shipyard | 4 |  | Shipyard |
| 2138 | Catapult Ship |  | catapult-ship-line | warship-class (922) | Shipyard | 3 |  | Shipyard |
| 2139 | Onager Ship |  | catapult-ship-line | warship-class (922) | Shipyard | 4 |  | Shipyard |
| 2140 | Leviathan |  |  | warship-class (922) | Shipyard | 4 |  | Shipyard |
| 1660 | Serjeant (Donjon) | donjon-serjeant | donjon-serjeant-line | infantry-class (906) | Donjon | 2 | Sicilians | Donjon |
| 1661 | Elite Serjeant (Donjon) | elite-donjon-serjeant | donjon-serjeant-line | infantry-class (906) | Donjon | 4 | Sicilians | Donjon |
| 1786 | Spearman (Donjon) |  | donjon-spearman-line | infantry-class (906) | Donjon | 2 | Sicilians | Donjon |
| 1787 | Pikeman (Donjon) |  | donjon-spearman-line | infantry-class (906) | Donjon | 3 | Sicilians | Donjon |
| 1788 | Halberdier (Donjon) |  | donjon-spearman-line | infantry-class (906) | Donjon | 4 | Sicilians | Donjon |
| 1254 | Konnik (Krepost) | krepost-konnik | krepost-konnik-line | cavalry-class (912) | Krepost | 3 | Bulgarians | Krepost |
| 1255 | Elite Konnik (Krepost) | elite-krepost-konnik | krepost-konnik-line | cavalry-class (912) | Krepost | 4 | Bulgarians | Krepost |
| 128 | Trade Cart (Empty) | trade-cart |  | trade-cart-class (919) | Market | 2 |  | Market |
| 204 | Trade Cart (Full) | trade-cart |  | trade-cart-class (919) | Market | 2 |  | Market |
| 125 | Monk | monk |  | monastery-class (918) | Monastery | 3 |  | Monastery |
| 286 | Monk with Relic | monk-with-relic |  | monk-with-relic-class (943) | Monastery | 3 |  | Monastery |
| 775 | Missionary | missionary |  | monastery-class (918) | Monastery | 3 | Spanish | Monastery |
| 2557 | Missionary with Relic |  |  | monk-with-relic-class (943) | Monastery | 3 |  | Monastery |
| 1811 | Warrior Priest | warrior-priest |  | infantry-class (906) | Monastery | 3 | Armenians | Monastery |
| 1831 | Warrior Priest with Relic |  |  | monk-with-relic-class (943) | Monastery | 3 |  | Monastery |
| 1258 | Battering Ram (Feudal) | feudal-battering-ram | battering-ram-line | siege-weapon-class (913) | Siege Workshop | 2 |  | SiegeWorkshop |
| 35 | Battering Ram | battering-ram | battering-ram-line | siege-weapon-class (913) | Siege Workshop | 3 |  | SiegeWorkshop |
| 422 | Capped Ram | capped-ram | battering-ram-line | siege-weapon-class (913) | Siege Workshop | 4 |  | SiegeWorkshop |
| 548 | Siege Ram | siege-ram | battering-ram-line | siege-weapon-class (913) | Siege Workshop | 4 |  | SiegeWorkshop |
| 1744 | Armored Elephant | armored-elephant | armored-elephant-line | cavalry-class (912) | Siege Workshop | 3 |  | SiegeWorkshop |
| 1746 | Siege Elephant | siege-elephant | armored-elephant-line | cavalry-class (912) | Siege Workshop | 4 |  | SiegeWorkshop |
| 280 | Mangonel | mangonel | mangonel-line | siege-weapon-class (913) | Siege Workshop | 3 |  | SiegeWorkshop |
| 550 | Onager (non-WK) | onager | mangonel-line | siege-weapon-class (913) | Siege Workshop | 4 |  | SiegeWorkshop |
| 701 | Onager (WK) |  |  | siege-weapon-class (913) | Siege Workshop | 4 |  | SiegeWorkshop |
| 588 | Siege Onager | siege-onager | mangonel-line | siege-weapon-class (913) | Siege Workshop | 4 |  | SiegeWorkshop |
| 1904 | Rocket Cart |  | rocket-cart-line | siege-weapon-class (913) | Siege Workshop | 3 |  | SiegeWorkshop |
| 1907 | Heavy Rocket Cart |  | rocket-cart-line | siege-weapon-class (913) | Siege Workshop | 4 |  | SiegeWorkshop |
| 279 | Scorpion | scorpion | scorpion-line | scorpion-class (955) | Siege Workshop | 3 |  | SiegeWorkshop |
| 542 | Heavy Scorpion | heavy-scorpion | scorpion-line | scorpion-class (955) | Siege Workshop | 4 |  | SiegeWorkshop |
| 1962 | War Chariot (Focus Fire) |  |  | cavalry-class (912) | Siege Workshop | 3 | Shu | SiegeWorkshop |
| 1980 | War Chariot (Barrage) |  |  | cavalry-class (912) | Siege Workshop | 3 | Shu | SiegeWorkshop |
| 36 | Bombard Cannon | bombard-cannon | bombard-cannon-line | siege-weapon-class (913) | Siege Workshop | 4 |  | SiegeWorkshop |
| 1709 | Houfnice | houfnice | bombard-cannon-line | siege-weapon-class (913) | Siege Workshop | 4 | Bohemians | SiegeWorkshop |
| 1942 | Traction Trebuchet |  |  | siege-weapon-class (913) | Siege Workshop | 4 |  | SiegeWorkshop |
| 1923 | Mounted Trebuchet |  |  | cavalry-class (912) | Siege Workshop | 4 | Khitans | SiegeWorkshop |
| WK: 494 / DE: 1105 | Siege Tower |  |  | siege-weapon-class (913) | Siege Workshop | 3 |  | SiegeWorkshop |
| 448 | Scout Cavalry | scout-cavalry | scout-cavalry-line | scout-cavalry-class (947) | Stable | 2 |  | Stable |
| 546 | Light Cavalry | light-cavalry | scout-cavalry-line | scout-cavalry-class (947) | Stable | 3 |  | Stable |
| 441 | Hussar | hussar | scout-cavalry-line | scout-cavalry-class (947) | Stable | 4 |  | Stable |
| 1707 | Winged Hussar | winged-hussar | scout-cavalry-line | scout-cavalry-class (947) | Stable | 4 |  | Stable |
| 38 | Knight | knight | knight-line | cavalry-class (912) | Stable | 3 |  | Stable |
| 283 | Cavalier | cavalier | knight-line | cavalry-class (912) | Stable | 4 |  | Stable |
| 569 | Paladin | paladin | knight-line | cavalry-class (912) | Stable | 4 |  | Stable |
| 1813 | Savar | savar | knight-line | cavalry-class (912) | Stable | 4 | Persians | Stable |
| 1755 | Camel Scout | camel-scout | camel-line | cavalry-class (912) | Stable | 2 | Gurjaras | Stable |
| 329 | Camel [Rider] | camel, camel-rider (DE only) | camel-line | cavalry-class (912) | Stable | 3 |  | Stable |
| 330 | Heavy Camel [Rider] | heavy-camel, heavy-camel-rider (DE only) | camel-line | cavalry-class (912) | Stable | 3 |  | Stable |
| 207 | Imperial Camel [Rider] | imperial-camel, imperial-camel-rider | camel-line | cavalry-class (912) | Stable | 4 | Hindustanis/Indians | Stable |
| WK: 774 / DE: 1132 | Battle Elephant | battle-elephant | battle-elephant-line | cavalry-class (912) | Stable | 3 |  | Stable |
| WK: 766 / DE: 1134 | Elite Battle Elephant | elite-battle-elephant | battle-elephant-line | cavalry-class (912) | Stable | 4 |  | Stable |
| 1370 | Steppe Lancer | steppe-lancer | steppe-lancer-line | cavalry-class (912) | Stable | 3 |  | Stable |
| 1372 | Elite Steppe Lancer | elite-steppe-lancer | steppe-lancer-line | cavalry-class (912) | Stable | 4 |  | Stable |
| 1944 | Hei Guang Cavalry | hei-guang-cavalry | hei-guang-cavalry-line | cavalry-class (912) | Stable | 3 |  | Stable |
| 1946 | Heavy Hei Guang Cavalry | heavy-hei-guang-cavalry | hei-guang-cavalry-line | cavalry-class (912) | Stable | 4 |  | Stable |
| 1751 | Shrivamsha Rider | shrivamsha-rider | shrivamsha-rider-line | cavalry-class (912) | Stable | 3 | Gurjaras | Stable |
| 1753 | Elite Shrivamsha Rider | elite-shrivamsha-rider | shrivamsha-rider-line | cavalry-class (912) | Stable | 4 | Gurjaras | Stable |
| 886 | Tarkan (Stable) | stable-tarkan |  | cavalry-class (912) | Stable | 3 | Huns | Stable |
| 887 | Elite Tarkan (Stable) | stable-elite-tarkan |  | cavalry-class (912) | Stable | 4 | Huns | Stable |
| 1570 | Xolotl Warrior |  |  | cavalry-class (912) | Stable | 3 |  | Stable |
| 83 | Villager (Male) | villager |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 293 | Villager (Female) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 212 | Builder (Female) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 118 | Builder (Male) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 214 | Farmer (Female) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 259 | Farmer (Male) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 57 | Fisherman (Female) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 56 | Fisherman (Male) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 354 | Forager (Female) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 120 | Forager (Male) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 581 | Gold Miner (Female) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 579 | Gold Miner (Male) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 216 | Hunter (Female) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 122 | Hunter (Male) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 218 | Lumberjack (Female) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 123 | Lumberjack (Male) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 222 | Repairer (Female) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 156 | Repairer (Male) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 590 | Shepherd (Female) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 592 | Shepherd (Male) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 220 | Stone Miner (Female) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 124 | Stone Miner (Male) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 1891 | Herder (Female) |  |  | villager-class (904) | Town Center | 1 | Khitans | TownCenter |
| 1892 | Herder (Male) |  |  | villager-class (904) | Town Center | 1 | Khitans | TownCenter |
| 2334 | Oyster Gatherer (Female) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 2333 | Oyster Gatherer (Male) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 1663 | Flemish Militia (Male) | flemish-pikeman |  | infantry-class (906) |  | 4 | Burgundians | TownCenter |
| 1697 | Flemish Militia (Female) | flemish-pikeman-female |  | infantry-class (906) |  | 4 | Burgundians | TownCenter |
| 109 | Town Center (Dark Age) | town-center |  | building-class (903) | Buildings | 1 |  | Buildings |
| 71 | Town Center (Feudal Age) |  |  | building-class (903) | Buildings | 2 |  | Buildings |
| 141 | Town Center (Castle Age) |  |  | building-class (903) | Buildings | 3 |  | Buildings |
| 142 | Town Center (Imperial Age) |  |  | building-class (903) | Buildings | 4 |  | Buildings |
| 621 | Town Center (Foundation) | town-center-foundation |  | building-class (903) | Buildings | 1 |  | Buildings |
| 618 | Town Center (Annex 1, Dark Age) |  |  | building-class (903) | Buildings | 1 |  | Buildings |
| 614 | Town Center (Annex 1, Feudal Age) |  |  | building-class (903) | Buildings | 2 |  | Buildings |
| 481 | Town Center (Annex 1, Castle Age) |  |  | building-class (903) | Buildings | 3 |  | Buildings |
| 611 | Town Center (Annex 1, Imperial Age) |  |  | building-class (903) | Buildings | 4 |  | Buildings |
| 619 | Town Center (Annex 2, Dark Age) |  |  | building-class (903) | Buildings | 1 |  | Buildings |
| 615 | Town Center (Annex 2, Feudal Age) |  |  | building-class (903) | Buildings | 2 |  | Buildings |
| 482 | Town Center (Annex 2, Castle Age) |  |  | building-class (903) | Buildings | 3 |  | Buildings |
| 612 | Town Center (Annex 2, Castle Age) |  |  | building-class (903) | Buildings | 1 |  | Buildings |
| 620 | Town Center (Annex 3, Dark Age) |  |  | building-class (903) | Buildings | 1 |  | Buildings |
| 616 | Town Center (Annex 3, Feudal Age) |  |  | building-class (903) | Buildings | 2 |  | Buildings |
| 483 | Town Center (Annex 3, Castle Age) |  |  | building-class (903) | Buildings | 3 |  | Buildings |
| 613 | Town Center (Annex 3, Imperial Age) |  |  | building-class (903) | Buildings | 4 |  | Buildings |
| 70 | House (Dark Age) | house |  | building-class (903) | Buildings | 1 |  | Buildings |
| 463 | House (Feudal Age) |  |  | building-class (903) | Buildings | 2 |  | Buildings |
| 464 | House (Castle Age) |  |  | building-class (903) | Buildings | 3 |  | Buildings |
| 465 | House (Imperial Age) |  |  | building-class (903) | Buildings | 4 |  | Buildings |
| 68 | Mill (Dark Age) | mill |  | building-class (903) | Buildings | 1 |  | Buildings |
| 129 | Mill (Feudal Age) |  |  | building-class (903) | Buildings | 2 |  | Buildings |
| 130 | Mill (Castle Age) |  |  | building-class (903) | Buildings | 3 |  | Buildings |
| 131 | Mill (Imperial Age) |  |  | building-class (903) | Buildings | 4 |  | Buildings |
| 1734 | Folwark (Dark Age) |  |  | building-class (903) | Buildings | 1 | Poles | Buildings |
| 1711 | Folwark (Feudal Age) |  |  | building-class (903) | Buildings | 2 | Poles | Buildings |
| 1720 | Folwark (Castle Age) |  |  | building-class (903) | Buildings | 3 | Poles | Buildings |
| 584 | Mining Camp (Dark Age) | mining-camp |  | building-class (903) | Buildings | 1 |  | Buildings |
| 585 | Mining Camp (Feudal Age) |  |  | building-class (903) | Buildings | 2 |  | Buildings |
| 586 | Mining Camp (Castle Age) |  |  | building-class (903) | Buildings | 3 |  | Buildings |
| 587 | Mining Camp (Imperial Age) |  |  | building-class (903) | Buildings | 4 |  | Buildings |
| 562 | Lumber Camp (Dark Age) | lumber-camp |  | building-class (903) | Buildings | 1 |  | Buildings |
| 563 | Lumber Camp (Feudal Age) |  |  | building-class (903) | Buildings | 2 |  | Buildings |
| 564 | Lumber Camp (Castle Age) |  |  | building-class (903) | Buildings | 3 |  | Buildings |
| 565 | Lumber Camp (Imperial Age) |  |  | building-class (903) | Buildings | 4 |  | Buildings |
| 1808 | Mule Cart | mule-cart |  | building-class (903) | Buildings | 1 |  | Buildings |
| 2556 | Settlement (Dark Age) |  |  | building-class (903) | Buildings | 1 |  | Buildings |
| 2558 | Settlement (Feudal Age) |  |  | building-class (903) | Buildings | 2 |  | Buildings |
| 2560 | Settlement (Castle Age) |  |  | building-class (903) | Buildings | 1 |  | Buildings |
| 45 | Dock (Dark Age) | dock |  | building-class (903) | Buildings | 1 |  | Buildings |
| 133 | Dock (Feudal Age) |  |  | building-class (903) | Buildings | 2 |  | Buildings |
| 47 | Dock (Castle Age) |  |  | building-class (903) | Buildings | 3 |  | Buildings |
| 51 | Dock (Imperial Age) |  |  | building-class (903) | Buildings | 4 |  | Buildings |
| 1189 | Harbor |  |  | building-class (903) | Buildings | 3 | Malay | Buildings |
| 199 | Fish Trap | fish-trap |  | farm-class (949) | Buildings | 2 |  | Buildings |
| 50 | Farm | farm |  | farm-class (949) | Buildings | 1 |  | Buildings |
| 1187 | Rice Farm |  |  | farm-class (949) | Buildings | 1 |  | Buildings |
| 1889 | Pasture |  |  | farm-class (949) | Buildings | 1 | Khitans | Buildings |
| 1893 | Pasture (Mangrove) |  |  | farm-class (949) | Buildings | 1 | Khitans | Buildings |
| 1897 | Pasture (Land) |  |  | farm-class (949) | Buildings | 1 | Khitans | Buildings |
| 103 | Blacksmith (Feudal Age) | blacksmith |  | building-class (903) | Buildings | 2 |  | Buildings |
| 18 | Blacksmith (Castle Age) |  |  | building-class (903) | Buildings | 3 |  | Buildings |
| 19 | Blacksmith (Imperial Age) |  |  | building-class (903) | Buildings | 4 |  | Buildings |
| 84 | Market (Feudal Age) | market |  | building-class (903) | Buildings | 2 |  | Buildings |
| 116 | Market (Castle Age) |  |  | building-class (903) | Buildings | 3 |  | Buildings |
| 137 | Market (Imperial Age) |  |  | building-class (903) | Buildings | 4 |  | Buildings |
| 104 | Monastery (Castle Age, Base) | monastery |  | building-class (903) | Buildings | 3 |  | Buildings |
| 30 | Monastery (Feudal Age) |  |  | building-class (903) | Buildings | 3 |  | Buildings |
| 31 | Monastery (Castle Age, Upgraded) |  |  | building-class (903) | Buildings | 3 |  | Buildings |
| 32 | Monastery (Imperial Age) |  |  | building-class (903) | Buildings | 4 |  | Buildings |
| 209 | University (Castle Age) | university |  | building-class (903) | Buildings | 3 |  | Buildings |
| 210 | University (Imperial Age) |  |  | building-class (903) | Buildings | 3 |  | Buildings |
| 276 | Wonder | wonder |  | building-class (903) | Buildings | 4 |  | Buildings |
| 1806 | Fortified Church |  |  | building-class (903) | Buildings | 3 |  | Buildings |
| 1754 | Caravanserai | caravanserai |  | building-class (903) | Buildings | 4 | Hindustanis | Buildings |
| WK: 734 / DE: 1021 | Feitoria | feitoria |  | building-class (903) | Buildings | 4 | Portuguese | Buildings |
| 12 | Barracks (Dark Age) | barracks |  | building-class (903) | Buildings | 1 |  | Buildings |
| 498 | Barracks (Feudal Age) |  |  | building-class (903) | Buildings | 2 |  | Buildings |
| 132 | Barracks (Castle Age) |  |  | building-class (903) | Buildings | 3 |  | Buildings |
| 20 | Barracks (Imperial Age) |  |  | building-class (903) | Buildings | 4 |  | Buildings |
| 87 | Archery Range (Feudal Age) | archery-range |  | building-class (903) | Buildings | 2 |  | Buildings |
| 10 | Archery Range (Castle Age) |  |  | building-class (903) | Buildings | 3 |  | Buildings |
| 14 | Archery Range (Imperial Age) |  |  | building-class (903) | Buildings | 4 |  | Buildings |
| 101 | Stable (Feudal Age) | stable |  | building-class (903) | Buildings | 2 |  | Buildings |
| 86 | Stable (Castle Age) |  |  | building-class (903) | Buildings | 3 |  | Buildings |
| 153 | Stable (Imperial Age) |  |  | building-class (903) | Buildings | 4 |  | Buildings |
| 49 | Siege Workshop | siege-workshop |  | building-class (903) | Buildings | 3 |  | Buildings |
| 598 | Outpost | outpost | outpost-line | building-class (903) | Buildings | 1 |  | Buildings |
| 72 | Palisade Wall | palisade-wall |  | wall-class (927) | Buildings | 1 |  | Buildings |
| 117 | Stone Wall | stone-wall | stone-wall-line | wall-class (927) | Buildings | 2 |  | Buildings |
| 155 | Fortified Wall | fortified-wall | stone-wall-line | wall-class (927) | Buildings | 3 |  | Buildings |
| 79 | Watch Tower | watch-tower | watch-tower-line | tower-class (952) | Buildings | 2 |  | Buildings |
| 234 | Guard Tower | guard-tower | watch-tower-line | tower-class (952) | Buildings | 3 |  | Buildings |
| 235 | Keep | keep | watch-tower-line | tower-class (952) | Buildings | 4 |  | Buildings |
| 236 | Bombard Tower | bombard-tower |  | tower-class (952) | Buildings | 4 |  | Buildings |
| 82 | Castle | castle |  | building-class (903) | Buildings | 3 |  | Buildings |
| 1251 | Krepost | krepost |  | building-class (903) | Buildings | 3 | Bulgarians | Buildings |
| 1665 | Donjon | donjon |  | tower-class (952) | Buildings | 2 | Sicilians | Buildings |
| 789 | Palisade Gate (Ascending Closed) |  |  | gate-class (939) | Buildings | 1 |  | Buildings |
| 790 | Palisade Gate (Ascending Open) |  |  | gate-class (939) | Buildings | 1 |  | Buildings |
| 791 | Palisade Gate (Ascending Endpieces) |  |  | gate-class (939) | Buildings | 1 |  | Buildings |
| 792 | Palisade Gate (Ascending Foundation) |  |  | gate-class (939) | Buildings | 1 |  | Buildings |
| 793 | Palisade Gate (Descending Closed) |  |  | gate-class (939) | Buildings | 1 |  | Buildings |
| 794 | Palisade Gate (Descending Open) |  |  | gate-class (939) | Buildings | 1 |  | Buildings |
| 795 | Palisade Gate (Descending Endpieces) |  |  | gate-class (939) | Buildings | 1 |  | Buildings |
| 796 | Palisade Gate (Descending Foundation) |  |  | gate-class (939) | Buildings | 1 |  | Buildings |
| 797 | Palisade Gate (Horizontal Closed) |  |  | gate-class (939) | Buildings | 1 |  | Buildings |
| 798 | Palisade Gate (Horizontal Open) |  |  | gate-class (939) | Buildings | 1 |  | Buildings |
| 799 | Palisade Gate (Horizontal Endpieces) |  |  | gate-class (939) | Buildings | 1 |  | Buildings |
| 800 | Palisade Gate (Horizontal Foundation) |  |  | gate-class (939) | Buildings | 1 |  | Buildings |
| 801 | Palisade Gate (Vertical Closed) |  |  | gate-class (939) | Buildings | 1 |  | Buildings |
| 802 | Palisade Gate (Vertical Open) |  |  | gate-class (939) | Buildings | 1 |  | Buildings |
| 803 | Palisade Gate (Vertical Endpieces) |  |  | gate-class (939) | Buildings | 1 |  | Buildings |
| 804 | Palisade Gate (Vertical Foundation) |  |  | gate-class (939) | Buildings | 1 |  | Buildings |
| 64 | Gate (Ascending Closed) | gate-ascending-closed |  | gate-class (939) | Buildings | 2 |  | Buildings |
| 78 | Gate (Ascending Open) | gate-ascending-open |  | gate-class (939) | Buildings | 2 |  | Buildings |
| 81 | Gate (Ascending Endpieces) |  |  | gate-class (939) | Buildings | 2 |  | Buildings |
| 487 | Gate (Ascending Foundation) | gate, / gate-ascending |  | gate-class (939) | Buildings | 2 |  | Buildings |
| 88 | Gate (Descending Closed) | gate-descending-closed |  | gate-class (939) | Buildings | 2 |  | Buildings |
| 91 | Gate (Descending Open) |  |  | gate-class (939) | Buildings | 2 |  | Buildings |
| 95 | Gate (Descending Endpieces) |  |  | gate-class (939) | Buildings | 2 |  | Buildings |
| 490 | Gate (Descending Foundation) | gate-descending |  | gate-class (939) | Buildings | 2 |  | Buildings |
| 659 | Gate (Horizontal Closed) | gate-horizontal-closed |  | gate-class (939) | Buildings | 2 |  | Buildings |
| 661 | Gate (Horizontal Open) | gate-horizontal-open |  | gate-class (939) | Buildings | 2 |  | Buildings |
| 663 | Gate (Horizontal Endpieces) | gate-horizontal-open |  | gate-class (939) | Buildings | 2 |  | Buildings |
| 665 | Gate (Horizontal Foundation) | gate-horizontal |  | gate-class (939) | Buildings | 2 |  | Buildings |
| 667 | Gate (Vertical Closed) | gate-vertical-closed |  | gate-class (939) | Buildings | 2 |  | Buildings |
| 669 | Gate (Vertical Open) | gate-vertical-open |  | gate-class (939) | Buildings | 2 |  | Buildings |
| 671 | Gate (Vertical Endpieces) | gate-vertical-open |  | gate-class (939) | Buildings | 2 |  | Buildings |
| 673 | Gate (Vertical Foundation) | gate-vertical |  | gate-class (939) | Buildings | 2 |  | Buildings |
| 63 | Fortified Gate (Ascending Closed) |  |  | gate-class (939) | Buildings | 3 |  | Buildings |
| 67 | Fortified Gate (Ascending Open) |  |  | gate-class (939) | Buildings | 3 |  | Buildings |
| 80 | Fortified Gate (Ascending Endpieces) |  |  | gate-class (939) | Buildings | 3 |  | Buildings |
| 488 | Fortified Gate (Ascending Foundation) |  |  | gate-class (939) | Buildings | 3 |  | Buildings |
| 85 | Fortified Gate (Descending Closed) |  |  | gate-class (939) | Buildings | 3 |  | Buildings |
| 90 | Fortified Gate (Descending Open) |  |  | gate-class (939) | Buildings | 3 |  | Buildings |
| 92 | Fortified Gate (Descending Endpieces) |  |  | gate-class (939) | Buildings | 3 |  | Buildings |
| 491 | Fortified Gate (Descending Foundation) |  |  | gate-class (939) | Buildings | 3 |  | Buildings |
| 660 | Fortified Gate (Horizontal Closed) |  |  | gate-class (939) | Buildings | 3 |  | Buildings |
| 662 | Fortified Gate (Horizontal Open) |  |  | gate-class (939) | Buildings | 3 |  | Buildings |
| 664 | Fortified Gate (Horizontal Endpieces) |  |  | gate-class (939) | Buildings | 3 |  | Buildings |
| 666 | Fortified Gate (Horizontal Foundation) |  |  | gate-class (939) | Buildings | 3 |  | Buildings |
| 668 | Fortified Gate (Vertical Closed) |  |  | gate-class (939) | Buildings | 3 |  | Buildings |
| 670 | Fortified Gate (Vertical Open) |  |  | gate-class (939) | Buildings | 3 |  | Buildings |
| 672 | Fortified Gate (Vertical Endpieces) |  |  | gate-class (939) | Buildings | 3 |  | Buildings |
| 674 | Fortified Gate (Vertical Foundation) |  |  | gate-class (939) | Buildings | 3 |  | Buildings |
| 624 | Pavilion A |  |  | building-class (903) | Buildings | 1 |  | Buildings |
| 625 | Pavilion C |  |  | building-class (903) | Buildings | 1 |  | Buildings |
| 626 | Pavilion B |  |  | building-class (903) | Buildings | 1 |  | Buildings |
| 712 | Yurt A |  |  | building-class (903) | Buildings | 1 |  | Buildings |
| 713 | Yurt B |  |  | building-class (903) | Buildings | 1 |  | Buildings |
| 714 | Yurt C |  |  | building-class (903) | Buildings | 1 |  | Buildings |
| 715 | Yurt D |  |  | building-class (903) | Buildings | 1 |  | Buildings |
| 716 | Yurt E |  |  | building-class (903) | Buildings | 1 |  | Buildings |
| 717 | Yurt F |  |  | building-class (903) | Buildings | 1 |  | Buildings |
| 718 | Yurt G |  |  | building-class (903) | Buildings | 1 |  | Buildings |
| 719 | Yurt H |  |  | building-class (903) | Buildings | 1 |  | Buildings |
| 684 | The Accursed Tower |  |  | tower-class (952) | Buildings | 1 |  | Buildings |
| 685 | The Tower of Flies |  |  | tower-class (952) | Buildings | 1 |  | Buildings |
| 826 | Monument |  |  | monument-class (901) | Buildings | 1 |  | Buildings |
| 59 | Forage Bush |  |  | foarge-class (907) | Gaia | 1 |  | Gaia |
| 1059 | Fruit Bush |  |  | foarge-class (907) | Gaia | 1 |  | Gaia |
| 1549 | Forage Bush (Gurjaras) |  |  | foarge-class (907) | Gaia | 1 | Gurjaras | Gaia |
| 2599 | Papaya Tree |  |  | foarge-class (907) | Gaia | 1 |  | Gaia |
| 2650 | Pineapple Bush |  |  | foarge-class (907) | Gaia | 1 |  | Gaia |
| 2590 | Capybara |  |  | livestock-class (958) | Gaia | 1 |  | Gaia |
| 2083 | Chicken A (Brown) |  |  | livestock-class (958) | Gaia | 1 |  | Gaia |
| 2085 | Chicken B (White) |  |  | livestock-class (958) | Gaia | 1 |  | Gaia |
| 2087 | Chicken C (Black) |  |  | livestock-class (958) | Gaia | 1 |  | Gaia |
| 705 | Cow (Black and White) |  |  | livestock-class (958) | Gaia | 1 |  | Gaia |
| 1596 | Cow (Black) |  |  | livestock-class (958) | Gaia | 1 |  | Gaia |
| 1598 | Cow (Brown & White) |  |  | livestock-class (958) | Gaia | 1 |  | Gaia |
| 1600 | Cow (Brown) |  |  | livestock-class (958) | Gaia | 1 |  | Gaia |
| 1060 | Goat |  |  | livestock-class (958) | Gaia | 1 |  | Gaia |
| 1243 | Goose |  |  | livestock-class (958) | Gaia | 1 |  | Gaia |
| 305 | Llama A (Brown) |  |  | livestock-class (958) | Gaia | 1 |  | Gaia |
| 1963 | Llama B (White) |  |  | livestock-class (958) | Gaia | 1 |  | Gaia |
| 1245 | Pig |  |  | livestock-class (958) | Gaia | 1 |  | Gaia |
| 594 | Sheep |  |  | livestock-class (958) | Gaia | 1 |  | Gaia |
| 833 | Turkey |  |  | livestock-class (958) | Gaia | 1 |  | Gaia |
| 1142 | Water Buffalo |  |  | livestock-class (958) | Gaia | 1 |  | Gaia |
| 1896 | Argali |  |  | prey-animal-class (909) | Gaia | 1 |  | Gaia |
| 1899 | Argali (Pasture) |  |  | farm-class (949) | Gaia | 1 |  | Gaia |
| 65 | Deer |  |  | prey-animal-class (909) | Gaia | 1 |  | Gaia |
| 1958 | Fox (Arctic) |  |  | fox-class (965) | Gaia | 1 |  | Gaia |
| 1955 | Fox (Red) |  |  | fox-class (965) | Gaia | 1 |  | Gaia |
| 1796 | Gazelle |  |  | prey-animal-class (909) | Gaia | 1 |  | Gaia |
| 2591 | Guanaco |  |  | prey-animal-class (909) | Gaia | 1 |  | Gaia |
| 1239 | Ibex |  |  | prey-animal-class (909) | Gaia | 1 |  | Gaia |
| 1900 | Ibex (Pasture) |  |  | farm-class (949) | Gaia | 1 |  | Gaia |
| 2095 | Monkey |  |  | prey-animal-class (909) | Gaia | 1 |  | Gaia |
| 2340 | Mouflon |  |  | prey-animal-class (909) | Gaia | 1 |  | Gaia |
| 1026 | Ostrich |  |  | prey-animal-class (909) | Gaia | 1 |  | Gaia |
| 2097 | Penguin |  |  | prey-animal-class (909) | Gaia | 1 |  | Gaia |
| 2597 | Rhea |  |  | prey-animal-class (909) | Gaia | 1 |  | Gaia |
| 2735 | Seal |  |  | prey-animal-class (909) | Gaia | 1 |  | Gaia |
| 1019 | Zebra |  |  | prey-animal-class (909) | Gaia | 1 |  | Gaia |
| 2098 | Hare A (Brown) |  |  | prey-animal-class (909) | Gaia | 1 |  | Gaia |
| 2099 | Hare B (Gray) |  |  | prey-animal-class (909) | Gaia | 1 |  | Gaia |
| 2100 | Hare C (Arctic) |  |  | prey-animal-class (909) | Gaia | 1 |  | Gaia |
| 2739 | Pheasant |  |  | prey-animal-class (909) | Gaia | 1 |  | Gaia |
| 2084 | Wild Chicken A (Brown) |  |  | prey-animal-class (909) | Gaia | 1 |  | Gaia |
| 2086 | Wild Chicken B (White) |  |  | prey-animal-class (909) | Gaia | 1 |  | Gaia |
| 2088 | Wild Chicken C (Black) |  |  | prey-animal-class (909) | Gaia | 1 |  | Gaia |
| WK: 412 / DE: 1301 | Elephant |  |  | predator-animal-class (910) | Gaia | 1 |  | Gaia |
| 2737 | Elk |  |  | predator-animal-class (910) | Gaia | 1 |  | Gaia |
| 822 | Javelina |  |  | predator-animal-class (910) | Gaia | 1 |  | Gaia |
| 1139 | Rhinoceros |  |  | predator-animal-class (910) | Gaia | 1 |  | Gaia |
| 2589 | Tapir |  |  | predator-animal-class (910) | Gaia | 1 |  | Gaia |
| 1924 | Walrus |  |  | predator-animal-class (910) | Gaia | 1 |  | Gaia |
| 48 | Wild Boar |  |  | predator-animal-class (910) | Gaia | 1 |  | Gaia |
| 2089 | Bear (Black) |  |  | predator-animal-class (910) | Gaia | 1 |  | Gaia |
| 486 | Bear (Brown) |  |  | predator-animal-class (910) | Gaia | 1 |  | Gaia |
| 2090 | Bear (Polar) |  |  | predator-animal-class (910) | Gaia | 1 |  | Gaia |
| 2595 | Black Panther |  |  | predator-animal-class (910) | Gaia | 1 |  | Gaia |
| 2594 | Caiman |  |  | predator-animal-class (910) | Gaia | 1 |  | Gaia |
| 1031 | Crocodile |  |  | predator-animal-class (910) | Gaia | 1 |  | Gaia |
| 812 | Jaguar |  |  | predator-animal-class (910) | Gaia | 1 |  | Gaia |
| 1135 | Komodo Dragon |  |  | predator-animal-class (910) | Gaia | 1 |  | Gaia |
| 1029 | Lion |  |  | predator-animal-class (910) | Gaia | 1 |  | Gaia |
| 2736 | Lynx |  |  | predator-animal-class (910) | Gaia | 1 |  | Gaia |
| 2592 | Snake |  |  | predator-animal-class (910) | Gaia | 1 |  | Gaia |
| 1241 | Snow Leopard |  |  | predator-animal-class (910) | Gaia | 1 |  | Gaia |
| 1137 | Tiger |  |  | predator-animal-class (910) | Gaia | 1 |  | Gaia |
| 2091 | Wolf (Arabian) |  |  | predator-animal-class (910) | Gaia | 1 |  | Gaia |
| 1965 | Wolf (Arctic) |  |  | predator-animal-class (910) | Gaia | 1 |  | Gaia |
| 89 | Wolf (Dire) |  |  | predator-animal-class (910) | Gaia | 1 |  | Gaia |
| 126 | Wolf (Grey) |  |  | predator-animal-class (910) | Gaia | 1 |  | Gaia |
| 202 | Wolf (Rabid) |  |  | predator-animal-class (910) | Gaia | 1 |  | Gaia |
| 1141 | Box Turtles |  |  | shore-fish-class (933) | Gaia | 1 |  | Gaia |
| 69 | Fish (Shore) |  |  | shore-fish-class (933) | Gaia | 1 |  | Gaia |
| 455 | Fish (Dorado) |  |  | ocean-fish-class (905) | Gaia | 1 |  | Gaia |
| 53 | Fish (Perch) |  |  | ocean-fish-class (905) | Gaia | 1 |  | Gaia |
| 456 | Fish (Salmon) |  |  | ocean-fish-class (905) | Gaia | 1 |  | Gaia |
| 458 | Fish (Snapper) |  |  | ocean-fish-class (905) | Gaia | 1 |  | Gaia |
| 457 | Fish (Tuna) |  |  | ocean-fish-class (905) | Gaia | 1 |  | Gaia |
| 450 | Great Fish (Marlin) |  |  | ocean-fish-class (905) | Gaia | 1 |  | Gaia |
| 451 | Great Fish (Marlin) |  |  | ocean-fish-class (905) | Gaia | 1 |  | Gaia |
| 2710 | Oysters |  |  | oyster-class (963) | Gaia | 1 |  | Gaia |
| 2625 | Whale |  |  | oyster-class (963) | Gaia | 1 |  | Gaia |
| 1247 | Wild Bactrian Camel |  |  | prey-animal-class (909) | Gaia | 1 |  | Gaia |
| 884 | Wild Camel |  |  | prey-animal-class (909) | Gaia | 1 |  | Gaia |
| 835 | Wild Horse A (Bay Dun) |  |  | prey-animal-class (909) | Gaia | 1 |  | Gaia |
| 2092 | Wild Horse B (Draft) |  |  | prey-animal-class (909) | Gaia | 1 |  | Gaia |
| 2093 | Wild Horse C (Dapple) |  |  | prey-animal-class (909) | Gaia | 1 |  | Gaia |
| 2094 | Wild Horse D (Andalusian) |  |  | prey-animal-class (909) | Gaia | 1 |  | Gaia |
| 1063 | Acacia Tree |  |  | tree-class (915) | Gaia | 1 |  | Gaia |
| 2028 | Asian Maple Tree (Autumn) |  |  | tree-class (915) | Gaia | 1 |  | Gaia |
| 2027 | Asian Maple Tree (Green) |  |  | tree-class (915) | Gaia | 1 |  | Gaia |
| 2016 | Asian Pine Tree |  |  | tree-class (915) | Gaia | 1 |  | Gaia |
| 348 | Bamboo Forest Tree |  |  | tree-class (915) | Gaia | 1 |  | Gaia |
| 1052 | Baobab Tree |  |  | tree-class (915) | Gaia | 1 |  | Gaia |
| 1717 | Birch Tree |  |  | tree-class (915) | Gaia | 1 |  | Gaia |
| 302 | Bush A |  |  | tree-class (915) | Gaia | 1 |  | Gaia |
| 1053 | Bush B |  |  | tree-class (915) | Gaia | 1 |  | Gaia |
| 1054 | Bush C |  |  | tree-class (915) | Gaia | 1 |  | Gaia |
| 2733 | Bush D |  |  | tree-class (915) | Gaia | 1 |  | Gaia |
| 1347 | Cypress Tree |  |  | tree-class (915) | Gaia | 1 |  | Gaia |
| 1051 | Dragon Tree |  |  | tree-class (915) | Gaia | 1 |  | Gaia |
| 411 | Forest Tree |  |  | tree-class (915) | Gaia | 1 |  | Gaia |
| 1348 | Italian Pine Tree |  |  | tree-class (915) | Gaia | 1 |  | Gaia |
| 414 | Jungle Tree |  |  | tree-class (915) | Gaia | 1 |  | Gaia |
| 1984 | Lush Bamboo Tree |  |  | tree-class (915) | Gaia | 1 |  | Gaia |
| 1144 | Mangrove Tree |  |  | tree-class (915) | Gaia | 1 |  | Gaia |
| 1248 | Oak Tree (Autumn) |  |  | tree-class (915) | Gaia | 1 |  | Gaia |
| 1249 | Oak Tree (Autumn Snow) |  |  | tree-class (915) | Gaia | 1 |  | Gaia |
| 349 | Oak Forest Tree |  |  | tree-class (915) | Gaia | 1 |  | Gaia |
| 1349 | Olive Tree |  |  | tree-class (915) | Gaia | 1 |  | Gaia |
| 351 | Palm Forest Tree |  |  | tree-class (915) | Gaia | 1 |  | Gaia |
| 2017 | Peach Blossom Tree |  |  | tree-class (915) | Gaia | 1 |  | Gaia |
| 350 | Pine Forest Tree |  |  | tree-class (915) | Gaia | 1 |  | Gaia |
| 1146 | Rainforest Tree |  |  | tree-class (915) | Gaia | 1 |  | Gaia |
| 1350 | Reeds |  |  | tree-class (915) | Gaia | 1 |  | Gaia |
| 413 | Snow Pine Tree |  |  | tree-class (915) | Gaia | 1 |  | Gaia |
| 2731 | Spruce Tree |  |  | tree-class (915) | Gaia | 1 |  | Gaia |
| 2732 | Spruce Snow Tree |  |  | tree-class (915) | Gaia | 1 |  | Gaia |
| 2025 | Willow Tree |  |  | tree-class (915) | Gaia | 1 |  | Gaia |
| 66 | Gold Mine |  |  | gold-mine-class (932) | Gaia | 1 |  | Gaia |
| 102 | Stone Mine |  |  | stone-mine-class (908) | Gaia | 1 |  | Gaia |
| 285 | Relic |  |  | relic-class (942) | Gaia | 1 |  | Gaia |
| 1071 | Abraha Elephant |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 844 | Admiral Yi Sun-shin |  |  | warship-class (922) | Heroes | 1 |  | Heroes |
| 169 | Aethelfirth |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 223 | Alaric the Goth |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 197 | Alexander Nevski |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 1725 | Algirdas |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 1763 | Amoghavarsha |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 177 | Archbishop |  |  | monastery-class (918) | Heroes | 1 |  | Heroes |
| 686 | Archer of the Eyes |  |  | archery-class (900) | Heroes | 1 |  | Heroes |
| 453 | Ataulf |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 777 | Attila the Hun |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 1070 | Babur |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 682 | Bad Neighbor |  |  | unpacked-trebuchet-class (954) | Heroes | 1 |  | Heroes |
| 730 | Bad Neighbor (Packed) |  |  | packed-trebuchet-class (951) | Heroes | 1 |  | Heroes |
| 1165 | Bayinnaung |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 167 | Belisarius |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 1687 | Bernard d'Armagnac |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 779 | Bleda the Hun |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 1681 | Bohemond |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 1183 | Bui Bi |  |  | monastery-class (918) | Heroes | 1 |  | Heroes |
| 1954 | Cao Cao |  |  | cavalry-class (912) | Castle | 4 | Wei | Heroes |
| WK: 927 / DE: 1295 | Chand Bardai |  |  | monastery-class (918) | Heroes | 1 |  | Heroes |
| 165 | Charlemagne |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 424 | Charles Martel |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 646 | Constable Richemont |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 1723 | Crusader Knight |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 307 | Cuauhtemoc |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 1268 | Cuman Chief |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 749 | Cusi Yupanqui |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 1685 | Dafydd ap Gruffydd |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 1106 | Dagnajan |  |  | cavalry-archer-class (936) | Heroes | 1 |  | Heroes |
| 1184 | Dinh Le |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 1730 | Dmitri of Moscow |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 638 | Duke D'Alençon |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 1669 | Edward Longshanks |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 198 | El Cid |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 824 | El Cid Campeador |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 733 | Emperor in a Barrel |  |  | king-class (959) | Heroes | 1 |  | Heroes |
| 1729 | Emperor Sigismund |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 1186 | Envoy |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 171 | Erik the Red |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 439 | Francesco Sforza |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 425 | Francisco de Orellana |  |  | cavalry-cannon-class (923) | Heroes | 1 |  | Heroes |
| 632 | Frankish Paladin |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 429 | Frederick Barbarossa |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 163 | Friar Tuck |  |  | monastery-class (918) | Heroes | 1 |  | Heroes |
| 1157 | Gajah Mada |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 175 | Gawain |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 1766 | General Araiyan |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 731 | Genghis Khan |  |  | cavalry-archer-class (936) | Heroes | 1 |  | Heroes |
| 1109 | Gidajan |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 1671 | Gilbert de Clare |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 1269 | Girgen Khan |  |  | cavalry-archer-class (936) | Heroes | 1 |  | Heroes |
| 683 | God's Own Sling |  |  | unpacked-trebuchet-class (954) | Heroes | 1 |  | Heroes |
| 729 | God's Own Sling (Packed) |  |  | packed-trebuchet-class (951) | Heroes | 1 |  | Heroes |
| 427 | Gonzalo Pizarro |  |  | cavalry-cannon-class (923) | Heroes | 1 |  | Heroes |
| 1072 | Guglielmo Embriaco |  |  | archery-class (900) | Heroes | 1 |  | Heroes |
| 648 | Guy Josselyne |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 426 | Harald Hardraade |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 1040 | Henry II |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 418 | Henry the Lion |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 847 | Henry V |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 428 | Hrolf the Ganger |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 1075 | Huanya Capac |  |  | archery-class (900) | Heroes | 1 |  | Heroes |
| 700 | Hunting Wolf |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 1771 | Ibrahim Lodi |  |  | cavalry-archer-class (936) | Heroes | 1 |  | Heroes |
| 842 | Imam |  |  | monastery-class (918) | Heroes | 1 |  | Heroes |
| 1819 | Ismail |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 1067 | Itzcoatl |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 1825 | Ivane |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 1265 | Ivaylo |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 1290 | Ivaylo |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 1692 | Jacqueline of Hainaut |  |  | king-class (959) | Heroes | 1 |  | Heroes |
| 1715 | Jadwiga |  |  | monastery-class (918) | Heroes | 1 |  | Heroes |
| 1713 | Jan Zizka |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| WK: 931 / DE: 1298 | Jarl |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 1158 | Jayanegara |  |  | king-class (959) | Heroes | 1 |  | Heroes |
| 1164 | Jayaviravarman |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 650 | Jean Bureau |  |  | siege-weapon-class (913) | Heroes | 1 |  | Heroes |
| 644 | Jean de Lorrain |  |  | siege-weapon-class (913) | Heroes | 1 |  | Heroes |
| 629 | Joan of Arc |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 430 | Joan the Maid |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 1673 | John the Fearless |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 1718 | Jogaila |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 1721 | Kestutis |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| WK: 930 / DE: 1297 | Khosrau |  |  | cavalry-archer-class (936) | Heroes | 1 |  | Heroes |
| 840 | King Alfonso |  |  | king-class (959) | Heroes | 1 |  | Heroes |
| 173 | King Arthur |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 230 | King Bela IV |  |  | king-class (959) | Heroes | 1 |  | Heroes |
| 838 | King Sancho |  |  | king-class (959) | Heroes | 1 |  | Heroes |
| 195 | Kitabatake |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 1267 | Kotyan Khan |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 702 | Kushluk |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 640 | La Hire |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 174 | Lancelot |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 1180 | Le Lai |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 1178 | Le Loi |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 1181 | Le Trien |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 106 | Leif Erikson |  |  | warship-class (922) | Heroes | 1 |  | Heroes |
| 1077 | Little John |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 1966 | Liu Bei |  |  | infantry-class (906) | Castle | 4 | Shu | Heroes |
| 1683 | Llywelyn ap Gruffydd |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 642 | Lord de Graville |  |  | archery-class (900) | Heroes | 1 |  | Heroes |
| 1182 | Luu Nhan Chu |  |  | archery-class (900) | Heroes | 1 |  | Heroes |
| 680 | Master of the Templar |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 1731 | Mikhail of Tver |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 1762 | Mihiro Bhoja |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 1076 | Miklos Toldi |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 196 | Minamoto |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 1828 | Mleh |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 176 | Mordred |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 1568 | Mounted Samurai |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 1034 | Musa ibn Nusayr |  |  | cavalry-archer-class (936) | Heroes | 1 |  | Heroes |
| 1068 | Mustafa Pasha |  |  | archery-cannon-class (944) | Heroes | 1 |  | Heroes |
| 845 | Nobunaga |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 707 | Ornlu the Wolf |  |  | predator-animal-class (910) | Heroes | 1 |  | Heroes |
| WK: 943 / DE: 1303 | Osman |  |  | cavalry-archer-class (936) | Heroes | 1 |  | Heroes |
| 1069 | Pacal II |  |  | archery-class (900) | Heroes | 1 |  | Heroes |
| 1074 | Pachacuti |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 1675 | Philip the Good |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 781 | Pope Leo I |  |  | monastery-class (918) | Heroes | 1 |  | Heroes |
| 1039 | Princess Yodit |  |  | king-class (959) | Heroes | 1 |  | Heroes |
| WK: 926 / DE: 1294 | Prithvi |  |  | archery-class (900) | Heroes | 1 |  | Heroes |
| 437 | Prithviraj |  |  | cavalry-archer-class (936) | Heroes | 1 |  | Heroes |
| 1769 | Qutlugh |  |  | cavalry-archer-class (936) | Heroes | 1 |  | Heroes |
| 1159 | Raden Wijaya |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 1764 | Rajendra Chola |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 678 | Reynald de Chatillon |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 1037 | Richard de Clare |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 160 | Richard the Lionheart |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 1677 | Robert Guiscard |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 200 | Robin Hood |  |  | archery-class (900) | Heroes | 1 |  | Heroes |
| 1679 | Roger Bosso |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 166 | Roland |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 706 | Saboteur |  |  | petard-class (935) | Heroes | 1 |  | Heroes |
| WK 929 / DE: 1296 | Saladin |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| WK: 925 / DE: 1293 | Sanyogita |  |  | king-class (959) | Heroes | 1 |  | Heroes |
| 852 | Scythian Scout |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 783 | Scythian Wild Woman |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 1820 | Selim the Grim |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 704 | Shah |  |  | king-class (959) | Heroes | 1 |  | Heroes |
| 1815 | Shah Ismail |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 1772 | Shaybani Khan |  |  | cavalry-archer-class (936) | Heroes | 1 |  | Heroes |
| 164 | Sheriff of Nottingham |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 170 | Siegfried |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 636 | Sieur Bertrand |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 634 | Sieur de Metz |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 652 | Sir John Fastolf |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 1299 | Sogdian Cataphract |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 1574 | Sosso Guard |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 1827 | Stephan |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 1073 | Su Dingfang |  |  | archery-class (900) | Heroes | 1 |  | Heroes |
| 698 | Subotai |  |  | cavalry-archer-class (936) | Heroes | 1 |  | Heroes |
| 1080 | Sumanguru |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 1160 | Sunda Royal Fighter |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 1035 | Sundjata |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 1978 | Sun Jian |  |  | cavalry-class (912) | Castle | 4 | Wu | Heroes |
| 1162 | Suryavarman I |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 1166 | Tabinshwehti |  |  | cavalry-archer-class (936) | Heroes | 1 |  | Heroes |
| 1822 | Tamar |  |  | monastery-class (918) | Heroes | 1 |  | Heroes |
| 172 | Tamerlane |  |  | cavalry-archer-class (936) | Heroes | 1 |  | Heroes |
| 1036 | Tariq ibn Ziyad |  |  | cavalry-archer-class (936) | Heroes | 1 |  | Heroes |
| 161 | The Black Prince |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 168 | Theodoric the Goth |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 1821 | Thoros |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 1262 | Tokhtamysh Khan |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 703 | Topa Yupanqui |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 1038 | Tristan |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 1266 | Tsar Konstantin |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 1163 | Udayadityavarman I |  |  | king-class (959) | Heroes | 1 |  | Heroes |
| 1727 | Ulrich von Jungingen |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 1276 | Urus Khan |  |  | cavalry-archer-class (936) | Heroes | 1 |  | Heroes |
| 203 | Vasco da Gama |  |  | warship-class (922) | Heroes | 1 |  | Heroes |
| 193 | Vlad Dracula |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 1281 | Vytautas the Great |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 1185 | Wang Tong |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 1690 | Warwolf Trebuchet |  |  | unpacked-trebuchet-class (954) | Heroes | 1 |  | Heroes |
| 1691 | Warwolf Trebuchet (Packed) |  |  | packed-trebuchet-class (951) | Heroes | 1 |  | Heroes |
| 849 | William the Conqueror |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 432 | William Wallace |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 1064 | Yekuno Amlak |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 1066 | Yodit |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 1768 | Young Babur |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 1732 | Young Jagwiga |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 1824 | Yury |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 1826 | Zakare |  |  | infantry-class (906) | Heroes | 1 |  | Heroes |
| 1078 | Zawisza the Black |  |  | cavalry-class (912) | Heroes | 1 |  | Heroes |
| 434 | King |  |  | king-class (959) | Other | 1 |  | Other |
| 2614 | Alpaca |  |  | controlled-animal-class (961) | Other | 1 |  | Other |
| 1237 | Bactrian Camel |  |  | controlled-animal-class (961) | Other | 1 |  | Other |
| 897 | Camel |  |  | controlled-animal-class (961) | Other | 1 |  | Other |
| 814 | Horse A |  |  | controlled-animal-class (961) | Other | 1 |  | Other |
| 1356 | Horse B |  |  | controlled-animal-class (961) | Other | 1 |  | Other |
| 1602 | Horse C |  |  | controlled-animal-class (961) | Other | 1 |  | Other |
| 1604 | Horse D |  |  | controlled-animal-class (961) | Other | 1 |  | Other |
| 1606 | Horse E |  |  | controlled-animal-class (961) | Other | 1 |  | Other |
| 1869 | Hunnic Horse |  |  | controlled-animal-class (961) | Other | 1 |  | Other |
| 274 | Flare | flare |  | miscellaneous-class (911) | Other | 1 |  | Other |
| 112 | Revealer |  |  | flag-class (930) | Other | 1 |  | Other |
| 837 | Map Revealer |  |  | flag-class (930) | Other | 1 |  | Other |
| WK: 934 / DE: 1300 | Alfred the Alpaca |  |  | cavalry-class (912) | Other | 1 |  | Other |
| 748 | Cobra Car |  |  | siege-weapon-class (913) | Other | 1 |  | Other |
| 860 | Furious the Monkey Boy |  |  | predator-animal-class (910) | Other | 1 |  | Other |
| 639 | Penguin |  |  | infantry-class (906) | Other | 1 |  | Other |
| 1577 | Photon Man |  |  | archery-cannon-class (944) | Other | 1 |  | Other |
| 1222 | Sharkatzor |  |  | siege-weapon-class (913) | Other | 1 |  | Other |
| 206 | VMDL |  |  | villager-class (904) | Other | 1 |  | Other |

### 3.2 Chronicles: Battle for Greece（8 个分类数组）

原始行 **438** 条（同一对象会出现在多个分类数组里），按 ID 去重后 **238** 个对象。`分类` 列出它出现过的所有分类。

| ID | 名称 | aiName | 线 | 类 | 建筑 | 时代 | 专属文明 | 分类 |
|---|---|---|---|---|---|---|---|---|
| 4 | Bowman | archer | archer-line | archery-class (900) | Archery Range | 2 |  | Range |
| 24 | Laminated Bowman | crossbowman | archer-line | archery-class (900) | Archery Range | 3 |  | Range |
| 492 | Recurve Bowman | arbalest | archer-line | archery-class (900) | Archery Range | 4 |  | Range |
| 7 | Skirmisher | skirmisher | skirmisher-line | archery-class (900) | Archery Range | 2 |  | Range |
| 6 | Elite Skirmisher | elite-skirmisher | skirmisher-line | archery-class (900) | Archery Range | 3 |  | Range |
| 39 | Cavalry Archer | cavalry-archer | cavalry-archer-line | cavalry-archer-class (936) | Archery Range | 3 |  | Range |
| 474 | Heavy Cavalry Archer | heavy-cavalry-archer | cavalry-archer-line | cavalry-archer-class (936) | Archery Range | 4 |  | Range |
| 5 | Gastraphetoros | hand-cannoneer |  | archery-cannon-class (944) | Archery Range | 4 | Athenians | Range |
| 74 | Levy | militiaman | militiaman-line | infantry-class (906) | Barracks | 1 |  | Barracks |
| 75 | Maceman | man-at-arms | militiaman-line | infantry-class (906) | Barracks | 2 |  | Barracks |
| 77 | Swordsman | long-swordsman | militiaman-line | infantry-class (906) | Barracks | 3 |  | Barracks |
| 567 | Paragon | champion | militiaman-line | infantry-class (906) | Barracks | 4 |  | Barracks |
| 93 | Spearman | spearman | spearman-line | infantry-class (906) | Barracks | 2 |  | Barracks |
| 358 | Guardsman | pikeman | spearman-line | infantry-class (906) | Barracks | 3 |  | Barracks |
| 359 | Elite Guardsman | halberdier | spearman-line | infantry-class (906) | Barracks | 4 |  | Barracks |
| 2110 | Hoplite |  | hoplite-line | infantry-class (906) | Barracks | 3 |  | Barracks |
| 2111 | Elite Hoplite |  | hoplite-line | infantry-class (906) | Barracks | 4 |  | Barracks |
| 2187 | Hoplite (with Xyphos) |  |  | infantry-class (906) | Barracks | 3 | Spartans | Barracks |
| 2188 | Elite Hoplite (with Xyphos) |  |  | infantry-class (906) | Barracks | 4 | Spartans | Barracks |
| 2384 | Phalangite |  | phalangite-line | infantry-class (906) | Barracks | 3 | Macedonians | Barracks |
| 2385 | Elite Phalangite |  | phalangite-line | infantry-class (906) | Barracks | 4 | Macedonians | Barracks |
| 125 | Priestess | monk |  | monastery-class (918) | Temple | 3 |  | Temple |
| 286 | Priestess with Relic |  |  | monk-with-relic-class (943) | Temple | 3 |  | Temple |
| 1258 | Battering Ram (Civic) | feudal-battering-ram | battering-ram-line | siege-weapon-class (913) | Siege Workshop | 2 |  | SiegeWorkshop |
| 35 | Battering Ram | battering-ram | battering-ram-line | siege-weapon-class (913) | Siege Workshop | 3 |  | SiegeWorkshop |
| 422 | Capped Ram | capped-ram | battering-ram-line | siege-weapon-class (913) | Siege Workshop | 4 |  | SiegeWorkshop |
| 548 | Siege Ram | siege-ram | battering-ram-line | siege-weapon-class (913) | Siege Workshop | 4 |  | SiegeWorkshop |
| 280 | Mangonel | mangonel | mangonel-line | siege-weapon-class (913) | Siege Workshop | 3 |  | SiegeWorkshop |
| 550 | Onager (non-WK) | onager | mangonel-line | siege-weapon-class (913) | Siege Workshop | 4 |  | SiegeWorkshop |
| 588 | Siege Onager | siege-onager | mangonel-line | siege-weapon-class (913) | Siege Workshop | 4 |  | SiegeWorkshop |
| 279 | Scorpion | scorpion | scorpion-line | scorpion-class (955) | Siege Workshop | 3 |  | SiegeWorkshop |
| 542 | Heavy Scorpion | heavy-scorpion | scorpion-line | scorpion-class (955) | Siege Workshop | 4 |  | SiegeWorkshop |
| 1105 | Siege Tower |  |  | siege-weapon-class (913) | Siege Workshop | 3 |  | SiegeWorkshop |
| 448 | Scout Cavalry | scout-cavalry | scout-cavalry-line | scout-cavalry-class (947) | Stable | 2 |  | Stable |
| 546 | Light Cavalry | light-cavalry | scout-cavalry-line | scout-cavalry-class (947) | Stable | 3 |  | Stable |
| 441 | Raider | hussar | scout-cavalry-line | scout-cavalry-class (947) | Stable | 4 |  | Stable |
| 38 | Lancer | knight | knight-line | cavalry-class (912) | Stable | 3 |  | Stable |
| 283 | Shock Cavalry | cavalier | knight-line | cavalry-class (912) | Stable | 4 |  | Stable |
| 569 | Imperial Cavalry | paladin | knight-line | cavalry-class (912) | Stable | 4 |  | Stable |
| 2150 | War Chariot |  | war-chariot-line | cavalry-class (912) | Stable | 3 | Achaemenids | Stable |
| 2151 | Elite War Chariot |  | war-chariot-line | cavalry-class (912) | Stable | 4 | Achaemenids | Stable |
| 2390 | Sannahya |  | sannahya-line | cavalry-class (912) | Stable | 3 | Puru | Stable |
| 2391 | Elite Sannahya |  | sannahya-line | cavalry-class (912) | Stable | 4 | Puru | Stable |
| 83 | Villager (Male) | villager |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 293 | Villager (Female) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 212 | Builder (Female) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 118 | Builder (Male) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 214 | Farmer (Female) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 259 | Farmer (Male) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 57 | Fisherman (Female) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 56 | Fisherman (Male) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 354 | Forager (Female) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 120 | Forager (Male) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 581 | Gold Miner (Female) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 579 | Gold Miner (Male) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 216 | Hunter (Female) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 122 | Hunter (Male) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 218 | Lumberjack (Female) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 123 | Lumberjack (Male) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 222 | Repairer (Female) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 156 | Repairer (Male) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 590 | Shepherd (Female) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 592 | Shepherd (Male) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 220 | Stone Miner (Female) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 124 | Stone Miner (Male) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 2334 | Oyster Gatherer (Female) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 2333 | Oyster Gatherer (Male) |  |  | villager-class (904) | Town Center | 1 |  | TownCenter |
| 2162 | Polemarch (Archaic Age) |  |  | infantry-class (906) |  | 1 | Spartans | TownCenter |
| 2164 | Polemarch (Civic Age) |  |  | infantry-class (906) |  | 2 | Spartans | TownCenter |
| 2165 | Polemarch (Classical Age) |  |  | infantry-class (906) |  | 3 | Spartans | TownCenter |
| 2166 | Polemarch (Imperial Age) |  |  | infantry-class (906) |  | 2 | Spartans | TownCenter |
| 2167 | Polemarch (Classical Age, with Ephorate) |  |  | infantry-class (906) |  | 3 | Spartans | TownCenter |
| 109 | Town Center (Archaic Age) | town-center |  | building-class (903) | Buildings | 1 |  | Buildings |
| 71 | Town Center (Civic Age) |  |  | building-class (903) | Buildings | 2 |  | Buildings |
| 141 | Town Center (Classical Age) |  |  | building-class (903) | Buildings | 3 |  | Buildings |
| 142 | Town Center (Imperial Age) |  |  | building-class (903) | Buildings | 4 |  | Buildings |
| 621 | Town Center (Foundation) | town-center-foundation |  | building-class (903) | Buildings | 1 |  | Buildings |
| 618 | Town Center (Annex 1, Archaic Age) |  |  | building-class (903) | Buildings | 1 |  | Buildings |
| 614 | Town Center (Annex 1, Civic Age) |  |  | building-class (903) | Buildings | 2 |  | Buildings |
| 481 | Town Center (Annex 1, Classical Age) |  |  | building-class (903) | Buildings | 3 |  | Buildings |
| 611 | Town Center (Annex 1, Imperial Age) |  |  | building-class (903) | Buildings | 4 |  | Buildings |
| 619 | Town Center (Annex 2, Archaic Age) |  |  | building-class (903) | Buildings | 1 |  | Buildings |
| 615 | Town Center (Annex 2, Civic Age) |  |  | building-class (903) | Buildings | 2 |  | Buildings |
| 482 | Town Center (Annex 2, Classical Age) |  |  | building-class (903) | Buildings | 3 |  | Buildings |
| 612 | Town Center (Annex 2, Classical Age) |  |  | building-class (903) | Buildings | 1 |  | Buildings |
| 620 | Town Center (Annex 3, Archaic Age) |  |  | building-class (903) | Buildings | 1 |  | Buildings |
| 616 | Town Center (Annex 3, Civic Age) |  |  | building-class (903) | Buildings | 2 |  | Buildings |
| 483 | Town Center (Annex 3, Classical Age) |  |  | building-class (903) | Buildings | 3 |  | Buildings |
| 613 | Town Center (Annex 3, Imperial Age) |  |  | building-class (903) | Buildings | 4 |  | Buildings |
| 2275 | Economic Town Center |  |  | building-class (903) | Buildings | 2 | Achaemenids | Buildings |
| 2276 | Defensive Town Center |  |  | building-class (903) | Buildings | 2 | Achaemenids | Buildings |
| 2277 | Military Town Center |  |  | building-class (903) | Buildings | 2 | Achaemenids | Buildings |
| 70 | House (Archaic Age) | house |  | building-class (903) | Buildings | 1 |  | Buildings |
| 463 | House (Civic Age) |  |  | building-class (903) | Buildings | 2 |  | Buildings |
| 464 | House (Classical Age) |  |  | building-class (903) | Buildings | 3 |  | Buildings |
| 465 | House (Imperial Age) |  |  | building-class (903) | Buildings | 4 |  | Buildings |
| 68 | Mill (Archaic Age) | mill |  | building-class (903) | Buildings | 1 |  | Buildings |
| 129 | Mill (Civic Age) |  |  | building-class (903) | Buildings | 2 |  | Buildings |
| 130 | Mill (Classical Age) |  |  | building-class (903) | Buildings | 3 |  | Buildings |
| 131 | Mill (Imperial Age) |  |  | building-class (903) | Buildings | 4 |  | Buildings |
| 584 | Mining Camp (Archaic Age) | mining-camp |  | building-class (903) | Buildings | 1 |  | Buildings |
| 585 | Mining Camp (Civic Age) |  |  | building-class (903) | Buildings | 2 |  | Buildings |
| 586 | Mining Camp (Classical Age) |  |  | building-class (903) | Buildings | 3 |  | Buildings |
| 587 | Mining Camp (Imperial Age) |  |  | building-class (903) | Buildings | 4 |  | Buildings |
| 562 | Lumber Camp (Archaic Age) | lumber-camp |  | building-class (903) | Buildings | 1 |  | Buildings |
| 563 | Lumber Camp (Civic Age) |  |  | building-class (903) | Buildings | 2 |  | Buildings |
| 564 | Lumber Camp (Classical Age) |  |  | building-class (903) | Buildings | 3 |  | Buildings |
| 565 | Lumber Camp (Imperial Age) |  |  | building-class (903) | Buildings | 4 |  | Buildings |
| 2172 | Port (Archaic Age) | paphos-port |  | building-class (903) | Buildings | 1 |  | Buildings |
| 2143 | Port (Civic Age) |  |  | building-class (903) | Buildings | 2 |  | Buildings |
| 2142 | Port (Classical Age) |  |  | building-class (903) | Buildings | 3 |  | Buildings |
| 2141 | Port (Imperial Age) |  |  | building-class (903) | Buildings | 4 |  | Buildings |
| 2119 | Shipyard (Civic Age) | paphos-shipyard |  | building-class (903) | Buildings | 2 |  | Buildings |
| 2118 | Shipyard (Classical Age) |  |  | building-class (903) | Buildings | 3 |  | Buildings |
| 2117 | Shipyard (Imperial Age) |  |  | building-class (903) | Buildings | 4 |  | Buildings |
| 199 | Fish Trap | fish-trap |  | farm-class (949) | Buildings | 2 |  | Buildings |
| 50 | Farm | farm |  | farm-class (949) | Buildings | 1 |  | Buildings |
| 103 | Blacksmith (Civic Age) | blacksmith |  | building-class (903) | Buildings | 2 |  | Buildings |
| 18 | Blacksmith (Classical Age) |  |  | building-class (903) | Buildings | 3 |  | Buildings |
| 19 | Blacksmith (Imperial Age) |  |  | building-class (903) | Buildings | 4 |  | Buildings |
| 84 | Market (Civic Age) | market |  | building-class (903) | Buildings | 2 |  | Buildings |
| 116 | Market (Classical Age) |  |  | building-class (903) | Buildings | 3 |  | Buildings |
| 137 | Market (Imperial Age) |  |  | building-class (903) | Buildings | 4 |  | Buildings |
| 104 | Temple (Archaic Age, Base) | monastery |  | building-class (903) | Buildings | 3 |  | Buildings |
| 30 | Temple (Civic Age) |  |  | building-class (903) | Buildings | 3 |  | Buildings |
| 31 | Temple (Classical Age, Upgraded) |  |  | building-class (903) | Buildings | 3 |  | Buildings |
| 32 | Temple (Imperial Age) |  |  | building-class (903) | Buildings | 4 |  | Buildings |
| 209 | Academy (Classical Age) | university |  | building-class (903) | Buildings | 3 |  | Buildings |
| 210 | Academy (Imperial Age) |  |  | building-class (903) | Buildings | 3 |  | Buildings |
| 276 | Wonder | wonder |  | building-class (903) | Buildings | 4 |  | Buildings |
| 12 | Barracks (Archaic Age) | barracks |  | building-class (903) | Buildings | 1 |  | Buildings |
| 498 | Barracks (Civic Age) |  |  | building-class (903) | Buildings | 2 |  | Buildings |
| 132 | Barracks (Classical Age) |  |  | building-class (903) | Buildings | 3 |  | Buildings |
| 20 | Barracks (Imperial Age) |  |  | building-class (903) | Buildings | 4 |  | Buildings |
| 87 | Archery Range (Civic Age) | archery-range |  | building-class (903) | Buildings | 2 |  | Buildings |
| 10 | Archery Range (Classical Age) |  |  | building-class (903) | Buildings | 3 |  | Buildings |
| 14 | Archery Range (Imperial Age) |  |  | building-class (903) | Buildings | 4 |  | Buildings |
| 101 | Stable (Civic Age) | stable |  | building-class (903) | Buildings | 2 |  | Buildings |
| 86 | Stable (Classical Age) |  |  | building-class (903) | Buildings | 3 |  | Buildings |
| 153 | Stable (Imperial Age) |  |  | building-class (903) | Buildings | 4 |  | Buildings |
| 49 | Siege Workshop | siege-workshop |  | building-class (903) | Buildings | 3 |  | Buildings |
| 598 | Outpost | outpost | outpost-line | building-class (903) | Buildings | 1 |  | Buildings |
| 72 | Palisade Wall | palisade-wall |  | wall-class (927) | Buildings | 1 |  | Buildings |
| 117 | Stone Wall | stone-wall | stone-wall-line | wall-class (927) | Buildings | 2 |  | Buildings |
| 155 | Fortified Wall | fortified-wall | stone-wall-line | wall-class (927) | Buildings | 3 |  | Buildings |
| 79 | Watch Tower | watch-tower | watch-tower-line | tower-class (952) | Buildings | 2 |  | Buildings |
| 234 | Guard Tower | guard-tower | watch-tower-line | tower-class (952) | Buildings | 3 |  | Buildings |
| 235 | Bastion | keep | watch-tower-line | tower-class (952) | Buildings | 4 |  | Buildings |
| 82 | Fort | castle |  | building-class (903) | Buildings | 3 |  | Buildings |
| 789 | Palisade Gate (Ascending Closed) |  |  | gate-class (939) | Buildings | 1 |  | Buildings |
| 790 | Palisade Gate (Ascending Open) |  |  | gate-class (939) | Buildings | 1 |  | Buildings |
| 791 | Palisade Gate (Ascending Endpieces) |  |  | gate-class (939) | Buildings | 1 |  | Buildings |
| 792 | Palisade Gate (Ascending Foundation) |  |  | gate-class (939) | Buildings | 1 |  | Buildings |
| 793 | Palisade Gate (Descending Closed) |  |  | gate-class (939) | Buildings | 1 |  | Buildings |
| 794 | Palisade Gate (Descending Open) |  |  | gate-class (939) | Buildings | 1 |  | Buildings |
| 795 | Palisade Gate (Descending Endpieces) |  |  | gate-class (939) | Buildings | 1 |  | Buildings |
| 796 | Palisade Gate (Descending Foundation) |  |  | gate-class (939) | Buildings | 1 |  | Buildings |
| 797 | Palisade Gate (Horizontal Closed) |  |  | gate-class (939) | Buildings | 1 |  | Buildings |
| 798 | Palisade Gate (Horizontal Open) |  |  | gate-class (939) | Buildings | 1 |  | Buildings |
| 799 | Palisade Gate (Horizontal Endpieces) |  |  | gate-class (939) | Buildings | 1 |  | Buildings |
| 800 | Palisade Gate (Horizontal Foundation) |  |  | gate-class (939) | Buildings | 1 |  | Buildings |
| 801 | Palisade Gate (Vertical Closed) |  |  | gate-class (939) | Buildings | 1 |  | Buildings |
| 802 | Palisade Gate (Vertical Open) |  |  | gate-class (939) | Buildings | 1 |  | Buildings |
| 803 | Palisade Gate (Vertical Endpieces) |  |  | gate-class (939) | Buildings | 1 |  | Buildings |
| 804 | Palisade Gate (Vertical Foundation) |  |  | gate-class (939) | Buildings | 1 |  | Buildings |
| 64 | Gate (Ascending Closed) | gate-ascending-closed |  | gate-class (939) | Buildings | 2 |  | Buildings |
| 78 | Gate (Ascending Open) | gate-ascending-open |  | gate-class (939) | Buildings | 2 |  | Buildings |
| 81 | Gate (Ascending Endpieces) |  |  | gate-class (939) | Buildings | 2 |  | Buildings |
| 487 | Gate (Ascending Foundation) | gate, / gate-ascending |  | gate-class (939) | Buildings | 2 |  | Buildings |
| 88 | Gate (Descending Closed) | gate-descending-closed |  | gate-class (939) | Buildings | 2 |  | Buildings |
| 91 | Gate (Descending Open) |  |  | gate-class (939) | Buildings | 2 |  | Buildings |
| 95 | Gate (Descending Endpieces) |  |  | gate-class (939) | Buildings | 2 |  | Buildings |
| 490 | Gate (Descending Foundation) | gate-descending |  | gate-class (939) | Buildings | 2 |  | Buildings |
| 659 | Gate (Horizontal Closed) | gate-horizontal-closed |  | gate-class (939) | Buildings | 2 |  | Buildings |
| 661 | Gate (Horizontal Open) | gate-horizontal-open |  | gate-class (939) | Buildings | 2 |  | Buildings |
| 663 | Gate (Horizontal Endpieces) | gate-horizontal-open |  | gate-class (939) | Buildings | 2 |  | Buildings |
| 665 | Gate (Horizontal Foundation) | gate-horizontal |  | gate-class (939) | Buildings | 2 |  | Buildings |
| 667 | Gate (Vertical Closed) | gate-vertical-closed |  | gate-class (939) | Buildings | 2 |  | Buildings |
| 669 | Gate (Vertical Open) | gate-vertical-open |  | gate-class (939) | Buildings | 2 |  | Buildings |
| 673 | Gate (Vertical Endpieces) | gate-vertical-open |  | gate-class (939) | Buildings | 2 |  | Buildings |
| 63 | Fortified Gate (Ascending Closed) |  |  | gate-class (939) | Buildings | 3 |  | Buildings |
| 67 | Fortified Gate (Ascending Open) |  |  | gate-class (939) | Buildings | 3 |  | Buildings |
| 80 | Fortified Gate (Ascending Endpieces) |  |  | gate-class (939) | Buildings | 3 |  | Buildings |
| 488 | Fortified Gate (Ascending Foundation) |  |  | gate-class (939) | Buildings | 3 |  | Buildings |
| 85 | Fortified Gate (Descending Closed) |  |  | gate-class (939) | Buildings | 3 |  | Buildings |
| 90 | Fortified Gate (Descending Open) |  |  | gate-class (939) | Buildings | 3 |  | Buildings |
| 92 | Fortified Gate (Descending Endpieces) |  |  | gate-class (939) | Buildings | 3 |  | Buildings |
| 491 | Fortified Gate (Descending Foundation) |  |  | gate-class (939) | Buildings | 3 |  | Buildings |
| 660 | Fortified Gate (Horizontal Closed) |  |  | gate-class (939) | Buildings | 3 |  | Buildings |
| 662 | Fortified Gate (Horizontal Open) |  |  | gate-class (939) | Buildings | 3 |  | Buildings |
| 664 | Fortified Gate (Horizontal Endpieces) |  |  | gate-class (939) | Buildings | 3 |  | Buildings |
| 666 | Fortified Gate (Horizontal Foundation) |  |  | gate-class (939) | Buildings | 3 |  | Buildings |
| 668 | Fortified Gate (Vertical Closed) |  |  | gate-class (939) | Buildings | 3 |  | Buildings |
| 670 | Fortified Gate (Vertical Open) |  |  | gate-class (939) | Buildings | 3 |  | Buildings |
| 672 | Fortified Gate (Vertical Endpieces) |  |  | gate-class (939) | Buildings | 3 |  | Buildings |
| 674 | Fortified Gate (Vertical Foundation) |  |  | gate-class (939) | Buildings | 3 |  | Buildings |
| 826 | Monument |  |  | monument-class (901) | Buildings | 1 |  | Buildings |
| 331 | Palintonon (Packed) | trebuchet |  | packed-trebuchet-class (951) | Fort | 4 |  |  |
| 42 | Palintonon (Unpacked) |  |  | unpacked-trebuchet-class (954) | Fort | 4 |  |  |
| 2101 | Immortal |  | immortal-line | infantry-class (906) | Fort | 3 | Achaemenids |  |
| 2102 | Elite Immortal |  | immortal-line | infantry-class (906) | Fort | 4 | Achaemenids |  |
| 2174 | Immortal (Ranged) |  |  | archery-class (900) | Fort | 3 | Achaemenids |  |
| 2175 | Elite Immortal (Ranged) |  |  | archery-class (900) | Fort | 4 | Achaemenids |  |
| 2104 | Strategos |  | strategos-line | infantry-class (906) | Fort | 3 | Athenians |  |
| 2105 | Elite Strategos |  | strategos-line | infantry-class (906) | Fort | 4 | Athenians |  |
| 2227 | Strategos (with Taxiarchs) |  | strategos-line | infantry-class (906) | Fort | 3 | Athenians |  |
| 2228 | Elite Strategos (with Taxiarchs) |  | strategos-line | infantry-class (906) | Fort | 4 | Athenians |  |
| 2382 | Companion Cavalry |  | companion-cavalry-line | cavalry-class (912) | Fort | 3 | Macedonians |  |
| 2383 | Elite Companion Cavalry |  | companion-cavalry-line | cavalry-class (912) | Fort | 4 | Macedonians |  |
| 2388 | Pattiyodha Longbowman |  | pattiyodha-longbowman-line | archery-class (900) | Fort | 3 | Puru |  |
| 2389 | Elite Pattiyodha Longbowman |  | pattiyodha-longbowman-line | archery-class (900) | Fort | 4 | Puru |  |
| 2107 | Hippeus |  | hippeus-line | infantry-class (906) | Fort | 3 | Spartans |  |
| 2108 | Elite Hippeus |  | hippeus-line | infantry-class (906) | Fort | 4 | Spartans |  |
| 2386 | Rhomphaia Warrior |  | rhomphaia-warrior-line | infantry-class (906) | Fort | 3 | Thracians |  |
| 2387 | Elite Rhomphaia Warrior |  | rhomphaia-warrior-line | infantry-class (906) | Fort | 4 | Thracians |  |
| 128 | Trade Cart (Empty) | trade-cart |  | trade-cart-class (919) | Market | 2 |  |  |
| 204 | Trade Cart (Full) | trade-cart |  | trade-cart-class (919) | Market | 2 |  |  |
| 2147 | Fishing Ship (Antiquity) |  |  | fishing-ship-class (921) | Port | 1 |  |  |
| 2171 | Oystering Ship |  |  | fishing-ship-class (921) | Port | 1 |  |  |
| 2630 | Whaling Ship |  |  | fishing-ship-class (921) | Port | 1 |  |  |
| 2149 | Merchant Ship |  |  | trade-cog-class (902) | Port | 2 |  |  |
| 2148 | Transport Ship (Antiquity) |  |  | transport-ship-class (920) | Port | 1 |  |  |
| 2123 | Lembos |  | lembos-line | warship-class (922) | Shipyard | 1 |  |  |
| 2124 | War Lembos |  | lembos-line | warship-class (922) | Shipyard | 2 |  |  |
| 2125 | Heavy Lembos |  | lembos-line | warship-class (922) | Shipyard | 3 |  |  |
| 2126 | Elite Lembos |  | lembos-line | warship-class (922) | Shipyard | 4 |  |  |
| 2127 | Monoreme |  | monoreme-line | warship-class (922) | Shipyard | 2 |  |  |
| 2128 | Bireme |  | monoreme-line | warship-class (922) | Shipyard | 3 |  |  |
| 2129 | Trireme |  | monoreme-line | warship-class (922) | Shipyard | 4 |  |  |
| 2130 | Galley (Antiquity) |  | ancient-galley-line | warship-class (922) | Shipyard | 2 |  |  |
| 2131 | War Galley (Antiquity) |  | ancient-galley-line | warship-class (922) | Shipyard | 3 |  |  |
| 2132 | Elite Galley |  | ancient-galley-line | warship-class (922) | Shipyard | 4 |  |  |
| 2133 | Incendiary Raft |  | incendiary-raft-line | warship-class (922) | Shipyard | 2 |  |  |
| 2134 | Incendiary Ship |  | incendiary-raft-line | warship-class (922) | Shipyard | 3 |  |  |
| 2135 | Heavy Incendiary Ship |  | incendiary-raft-line | warship-class (922) | Shipyard | 4 |  |  |
| 2138 | Catapult Ship |  | catapult-ship-line | warship-class (922) | Shipyard | 3 |  |  |
| 2139 | Onager Ship |  | catapult-ship-line | warship-class (922) | Shipyard | 4 |  |  |
| 2140 | Leviathan |  |  | warship-class (922) | Shipyard | 4 |  |  |

### 3.3 Return of Rome（12 个分类数组）

原始行 **370** 条（同一对象会出现在多个分类数组里），按 ID 去重后 **184** 个对象。`分类` 列出它出现过的所有分类。

| ID | 名称 | aiName | 线 | 类 | 建筑 | 时代 | 分类 |
|---|---|---|---|---|---|---|---|
| 93 | Hoplite | spearman | -290 | infantry-class (906) | Academy | 3 | Academy |
| 358 | Phalangite | pikeman | -290 | infantry-class (906) | Academy | 4 | Academy |
| 359 | Centurion | halberdier | -290 | infantry-class (906) | Academy | 4 | Academy |
| 4 | Bowman | archer | -299 | archery-class (900) | Archery Range | 2 | Range |
| 24 | Improved Bowman | crossbowman | -298 | archery-class (900) | Archery Range | 3 | Range |
| 492 | Composite Bowman | arbalest | -298 | archery-class (900) | Archery Range | 3 | Range |
| 5 | Chariot Archer | hand-cannoneer |  | cavalry-archer-class (936) | Archery Range | 3 | Range |
| 39 | Horse Archer | cavalry-archer | -293 | cavalry-archer-class (936) | Archery Range | 4 | Range |
| 474 | Heavy Horse Archer | heavy-cavalry-archer | -293 | cavalry-archer-class (936) | Archery Range | 4 | Range |
| 873 | Elephant Archer | elephant-archer |  | cavalry-archer-class (936) | Archery Range | 4 | Range |
| 281 | Clubman | throwing-axeman | -266 | infantry-class (906) | Barracks | 1 | Barracks |
| 531 | Axeman | elite-throwing-axeman | -266 | infantry-class (906) | Barracks | 2 | Barracks |
| 7 | Slinger | skirmisher |  | archery-class (900) | Barracks | 2 | Barracks |
| 74 | Short Swordsman | militiaman | -294 | infantry-class (906) | Barracks | 3 | Barracks |
| 75 | Broad Swordsman | man-at-arms | -294 | infantry-class (906) | Barracks | 3 | Barracks |
| 77 | Long Swordsman | long-swordsman | -294 | infantry-class (906) | Barracks | 4 | Barracks |
| 473 | Legionary | two-handed-swordsman | -294 | infantry-class (906) | Barracks | 4 | Barracks |
| 13 | Fishing Boat | fishing-ship | -287 | fishing-ship-class (921) | Dock | 1 | Dock |
| 15 | Fishing Ship |  | -287 | fishing-ship-class (921) | Dock | 3 | Dock |
| 545 | Light Transport | transport-ship | -286 | transport-ship-class (920) | Dock | 2 | Dock |
| 37 | Heavy Transport |  | -286 | transport-ship-class (920) | Dock | 4 | Dock |
| 17 | Trade Boat | trade-cog | -283 | trade-cog-class (902) | Dock | 3 | Dock |
| 11 | Merchant Ship |  | -283 | trade-cog-class (902) | Dock | 3 | Dock |
| 539 | Scout Ship | galley | -285 | warship-class (922) | Dock | 2 | Dock |
| 21 | War Galley | war-galley | -285 | warship-class (922) | Dock | 3 | Dock |
| 442 | Trireme | galleon | -285 | warship-class (922) | Dock | 4 | Dock |
| 1103 | Fire Galley | fire-galley |  | warship-class (922) | Dock | 4 | Dock |
| 420 | Catapult Trireme | cannon-galleon | -284 | warship-class (922) | Dock | 4 | Dock |
| 691 | Juggernaut | elite-cannon-galleon | -284 | warship-class (922) | Dock | 4 | Dock |
| 128 | Trade Cart (Empty) | trade-cart |  | trade-cart-class (919) | Market | 3 | Market |
| 204 | Trade Cart (Full) | trade-cart |  | trade-cart-class (919) | Market | 3 | Market |
| 280 | Stone Thrower | mangonel | -288 | siege-weapon-class (913) | Siege Workshop | 3 | SiegeWorkshop |
| 550 | Catapult | onager | -288 | siege-weapon-class (913) | Siege Workshop | 4 | SiegeWorkshop |
| 588 | Heavy Catapult | siege-onager | -288 | siege-weapon-class (913) | Siege Workshop | 4 | SiegeWorkshop |
| 279 | Ballista | scorpion | -289 | scorpion-class (955) | Siege Workshop | 4 | SiegeWorkshop |
| 542 | Helepolis | heavy-scorpion | -289 | scorpion-class (955) | Siege Workshop | 4 | SiegeWorkshop |
| 448 | Scout | scout-cavalry |  | scout-cavalry-class (947) | Stable | 2 | Stable |
| 38 | Cavalry | knight | -295 | cavalry-class (912) | Stable | 3 | Stable |
| 283 | Heavy Cavalry | cavalier | -295 | cavalry-class (912) | Stable | 4 | Stable |
| 569 | Cataphract | paladin | -295 | cavalry-class (912) | Stable | 4 | Stable |
| 329 | Camel Rider | camel |  | cavalry-class (912) | Stable | 3 | Stable |
| 1132 | War Elephant | battle-elephant | -292 | cavalry-class (912) | Stable | 4 | Stable |
| 1134 | Armored Elephant | elite-battle-elephant | -292 | cavalry-class (912) | Stable | 4 | Stable |
| 1370 | Chariot | steppe-lancer | -291 | cavalry-class (912) | Stable | 3 | Stable |
| 1372 | Scythe Chariot | elite-steppe-lancer | -291 | cavalry-class (912) | Stable | 4 | Stable |
| 125 | Priest | monk |  | monastery-class (918) | Temple | 3 | Temple |
| 83 | Villager (Male) | villager |  | villager-class (904) | Town Center | 1 | TownCenter |
| 293 | Villager (Female) |  |  | villager-class (904) | Town Center | 1 | TownCenter |
| 212 | Builder (Female) |  |  | villager-class (904) | Town Center | 1 | TownCenter |
| 118 | Builder (Male) |  |  | villager-class (904) | Town Center | 1 | TownCenter |
| 214 | Farmer (Female) |  |  | villager-class (904) | Town Center | 1 | TownCenter |
| 259 | Farmer (Male) |  |  | villager-class (904) | Town Center | 1 | TownCenter |
| 57 | Fisherman (Female) |  |  | villager-class (904) | Town Center | 1 | TownCenter |
| 56 | Fisherman (Male) |  |  | villager-class (904) | Town Center | 1 | TownCenter |
| 354 | Forager (Female) |  |  | villager-class (904) | Town Center | 1 | TownCenter |
| 120 | Forager (Male) |  |  | villager-class (904) | Town Center | 1 | TownCenter |
| 581 | Gold Miner (Female) |  |  | villager-class (904) | Town Center | 1 | TownCenter |
| 579 | Gold Miner (Male) |  |  | villager-class (904) | Town Center | 1 | TownCenter |
| 216 | Hunter (Female) |  |  | villager-class (904) | Town Center | 1 | TownCenter |
| 122 | Hunter (Male) |  |  | villager-class (904) | Town Center | 1 | TownCenter |
| 218 | Woodcutter (Female) |  |  | villager-class (904) | Town Center | 1 | TownCenter |
| 123 | Woodcutter (Male) |  |  | villager-class (904) | Town Center | 1 | TownCenter |
| 222 | Repairer (Female) |  |  | villager-class (904) | Town Center | 1 | TownCenter |
| 156 | Repairer (Male) |  |  | villager-class (904) | Town Center | 1 | TownCenter |
| 220 | Stone Miner (Female) |  |  | villager-class (904) | Town Center | 1 | TownCenter |
| 124 | Stone Miner (Male) |  |  | villager-class (904) | Town Center | 1 | TownCenter |
| 109 | Town Center (Stone Age) | town-center |  | building-class (903) | Buildings | 1 | Buildings |
| 71 | Town Center (Tool Age) |  |  | building-class (903) | Buildings | 2 | Buildings |
| 141 | Town Center (Bronze Age) |  |  | building-class (903) | Buildings | 3 | Buildings |
| 142 | Town Center (Iron Age) |  |  | building-class (903) | Buildings | 4 | Buildings |
| 621 | Town Center (Foundation) | town-center-foundation |  | building-class (903) | Buildings | 1 | Buildings |
| 70 | House (Stone Age) | house |  | building-class (903) | Buildings | 1 | Buildings |
| 463 | House (Tool Age) |  |  | building-class (903) | Buildings | 2 | Buildings |
| 464 | House (Bronze Age) |  |  | building-class (903) | Buildings | 3 | Buildings |
| 465 | House (Iron Age) |  |  | building-class (903) | Buildings | 4 | Buildings |
| 68 | Granary (Stone Age) | mill |  | building-class (903) | Buildings | 1 | Buildings |
| 129 | Granary (Tool Age) |  |  | building-class (903) | Buildings | 2 | Buildings |
| 130 | Granary (Bronze Age) |  |  | building-class (903) | Buildings | 3 | Buildings |
| 131 | Granary (Iron Age) |  |  | building-class (903) | Buildings | 4 | Buildings |
| 562 | Storage Pit (Stone Age) | lumber-camp |  | building-class (903) | Buildings | 1 | Buildings |
| 563 | Storage Pit (Tool Age) |  |  | building-class (903) | Buildings | 2 | Buildings |
| 564 | Storage Pit (Bronze Age) |  |  | building-class (903) | Buildings | 3 | Buildings |
| 565 | Storage Pit (Iron Age) |  |  | building-class (903) | Buildings | 4 | Buildings |
| 45 | Dock (Stone Age) | dock |  | building-class (903) | Buildings | 1 | Buildings |
| 133 | Dock (Tool Age) |  |  | building-class (903) | Buildings | 2 | Buildings |
| 47 | Dock (Bronze Age) |  |  | building-class (903) | Buildings | 3 | Buildings |
| 51 | Dock (Iron Age) |  |  | building-class (903) | Buildings | 4 | Buildings |
| 50 | Farm | farm |  | farm-class (949) | Buildings | 1 | Buildings |
| 84 | Market (Tool Age) | market |  | building-class (903) | Buildings | 2 | Buildings |
| 116 | Market (Bronze Age) |  |  | building-class (903) | Buildings | 3 | Buildings |
| 137 | Market (Iron Age) |  |  | building-class (903) | Buildings | 4 | Buildings |
| 104 | Temple (Stone Age) | monastery |  | building-class (903) | Buildings | 1 | Buildings |
| 30 | Temple (Tool Age) |  |  | building-class (903) | Buildings | 2 | Buildings |
| 31 | Temple (Bronze Age) |  |  | building-class (903) | Buildings | 3 | Buildings |
| 32 | Temple (Iron Age) |  |  | building-class (903) | Buildings | 4 | Buildings |
| 209 | Government Center (Bronze Age) | university |  | building-class (903) | Buildings | 3 | Buildings |
| 210 | Government Center (Iron Age) |  |  | building-class (903) | Buildings | 4 | Buildings |
| 276 | Wonder | wonder |  | building-class (903) | Buildings | 4 | Buildings |
| 12 | Barracks (Stone Age) | barracks |  | building-class (903) | Buildings | 1 | Buildings |
| 498 | Barracks (Tool Age) |  |  | building-class (903) | Buildings | 2 | Buildings |
| 132 | Barracks (Bronze Age) |  |  | building-class (903) | Buildings | 3 | Buildings |
| 20 | Barracks (Iron Age) |  |  | building-class (903) | Buildings | 4 | Buildings |
| 87 | Archery Range (Tool Age) | archery-range |  | building-class (903) | Buildings | 2 | Buildings |
| 10 | Archery Range (Bronze Age) |  |  | building-class (903) | Buildings | 3 | Buildings |
| 14 | Archery Range (Iron Age) |  |  | building-class (903) | Buildings | 4 | Buildings |
| 101 | Stable (Tool Age) | stable |  | building-class (903) | Buildings | 2 | Buildings |
| 86 | Stable (Bronze Age) |  |  | building-class (903) | Buildings | 3 | Buildings |
| 153 | Stable (Iron Age) |  |  | building-class (903) | Buildings | 4 | Buildings |
| 103 | Academy (Stone Age) | blacksmith |  | building-class (903) | Buildings | 3 | Buildings |
| 18 | Academy (Tool Age) |  |  | building-class (903) | Buildings | 3 | Buildings |
| 19 | Academy (Bronze Age) |  |  | building-class (903) | Buildings | 3 | Buildings |
| 105 | Academy (Iron Age) |  |  | building-class (903) | Buildings | 4 | Buildings |
| 49 | Siege Workshop | siege-workshop |  | building-class (903) | Buildings | 3 | Buildings |
| 72 | Small Wall | palisade-wall | -399 | wall-class (927) | Buildings | 2 | Buildings |
| 117 | Medium Wall | stone-wall | -399 | wall-class (927) | Buildings | 3 | Buildings |
| 155 | Fortified Wall | fortified-wall | -399 | wall-class (927) | Buildings | 4 | Buildings |
| 79 | Watch Tower | watch-tower | -398 | tower-class (952) | Buildings | 2 | Buildings |
| 234 | Sentry Tower | guard-tower | -398 | tower-class (952) | Buildings | 3 | Buildings |
| 235 | Guard Tower | keep | -398 | tower-class (952) | Buildings | 4 | Buildings |
| 236 | Ballista Tower | bombard-tower | -398 | tower-class (952) | Buildings | 4 | Buildings |
| 789 | Small Gate (Ascending Closed) |  |  | gate-class (939) | Buildings | 2 | Buildings |
| 790 | Small Gate (Ascending Open) |  |  | gate-class (939) | Buildings | 2 | Buildings |
| 791 | Small Gate (Ascending Endpieces) |  |  | gate-class (939) | Buildings | 2 | Buildings |
| 792 | Small Gate (Ascending Foundation) |  |  | gate-class (939) | Buildings | 2 | Buildings |
| 793 | Small Gate (Descending Closed) |  |  | gate-class (939) | Buildings | 2 | Buildings |
| 794 | Small Gate (Descending Open) |  |  | gate-class (939) | Buildings | 2 | Buildings |
| 795 | Small Gate (Descending Endpieces) |  |  | gate-class (939) | Buildings | 2 | Buildings |
| 796 | Small Gate (Descending Foundation) |  |  | gate-class (939) | Buildings | 2 | Buildings |
| 797 | Small Gate (Horizontal Closed) |  |  | gate-class (939) | Buildings | 2 | Buildings |
| 798 | Small Gate (Horizontal Open) |  |  | gate-class (939) | Buildings | 2 | Buildings |
| 799 | Small Gate (Horizontal Endpieces) |  |  | gate-class (939) | Buildings | 2 | Buildings |
| 800 | Small Gate (Horizontal Foundation) |  |  | gate-class (939) | Buildings | 2 | Buildings |
| 801 | Small Gate (Vertical Closed) |  |  | gate-class (939) | Buildings | 2 | Buildings |
| 802 | Small Gate (Vertical Open) |  |  | gate-class (939) | Buildings | 2 | Buildings |
| 803 | Small Gate (Vertical Endpieces) |  |  | gate-class (939) | Buildings | 2 | Buildings |
| 804 | Small Gate (Vertical Foundation) |  |  | gate-class (939) | Buildings | 2 | Buildings |
| 64 | Medium Gate (Ascending Closed) | gate-ascending-closed |  | gate-class (939) | Buildings | 3 | Buildings |
| 78 | Medium Gate (Ascending Open) | gate-ascending-open |  | gate-class (939) | Buildings | 3 | Buildings |
| 81 | Medium Gate (Ascending Endpieces) | gate-ascending-open |  | gate-class (939) | Buildings | 3 | Buildings |
| 487 | Medium Gate (Ascending Foundation) | gate, / gate-ascending |  | gate-class (939) | Buildings | 3 | Buildings |
| 88 | Medium Gate (Descending Closed) | gate-descending-closed |  | gate-class (939) | Buildings | 3 | Buildings |
| 91 | Medium Gate (Descending Open) |  |  | gate-class (939) | Buildings | 3 | Buildings |
| 95 | Medium Gate (Descending Endpieces) |  |  | gate-class (939) | Buildings | 3 | Buildings |
| 490 | Medium Gate (Descending Foundation) | gate-descending |  | gate-class (939) | Buildings | 3 | Buildings |
| 659 | Medium Gate (Horizontal Closed) | gate-horizontal-closed |  | gate-class (939) | Buildings | 3 | Buildings |
| 661 | Medium Gate (Horizontal Open) | gate-horizontal-open |  | gate-class (939) | Buildings | 3 | Buildings |
| 663 | Medium Gate (Horizontal Endpieces) | gate-horizontal-open |  | gate-class (939) | Buildings | 3 | Buildings |
| 665 | Medium Gate (Horizontal Foundation) | gate-horizontal |  | gate-class (939) | Buildings | 3 | Buildings |
| 667 | Medium Gate (Vertical Closed) | gate-vertical-closed |  | gate-class (939) | Buildings | 3 | Buildings |
| 669 | Medium Gate (Vertical Open) | gate-vertical-open |  | gate-class (939) | Buildings | 3 | Buildings |
| 673 | Medium Gate (Vertical Endpieces) | gate-vertical-open |  | gate-class (939) | Buildings | 3 | Buildings |
| 63 | Fortified Gate (Ascending Closed) |  |  | gate-class (939) | Buildings | 4 | Buildings |
| 67 | Fortified Gate (Ascending Open) |  |  | gate-class (939) | Buildings | 4 | Buildings |
| 80 | Fortified Gate (Ascending Endpieces) |  |  | gate-class (939) | Buildings | 4 | Buildings |
| 488 | Fortified Gate (Ascending Foundation) |  |  | gate-class (939) | Buildings | 4 | Buildings |
| 85 | Fortified Gate (Descending Closed) |  |  | gate-class (939) | Buildings | 4 | Buildings |
| 90 | Fortified Gate (Descending Open) |  |  | gate-class (939) | Buildings | 4 | Buildings |
| 92 | Fortified Gate (Descending Endpieces) |  |  | gate-class (939) | Buildings | 4 | Buildings |
| 491 | Fortified Gate (Descending Foundation) |  |  | gate-class (939) | Buildings | 4 | Buildings |
| 660 | Fortified Gate (Horizontal Closed) |  |  | gate-class (939) | Buildings | 4 | Buildings |
| 662 | Fortified Gate (Horizontal Open) |  |  | gate-class (939) | Buildings | 4 | Buildings |
| 664 | Fortified Gate (Horizontal Endpieces) |  |  | gate-class (939) | Buildings | 4 | Buildings |
| 666 | Fortified Gate (Horizontal Foundation) |  |  | gate-class (939) | Buildings | 4 | Buildings |
| 668 | Fortified Gate (Vertical Closed) |  |  | gate-class (939) | Buildings | 4 | Buildings |
| 670 | Fortified Gate (Vertical Open) |  |  | gate-class (939) | Buildings | 4 | Buildings |
| 672 | Fortified Gate (Vertical Endpieces) |  |  | gate-class (939) | Buildings | 4 | Buildings |
| 674 | Fortified Gate (Vertical Foundation) |  |  | gate-class (939) | Buildings | 3 | Buildings |
| 25 | Artifact |  |  | monument-class (901) | Other | 1 | Other |
| 52 | Ruins |  |  | monument-class (901) | Other | 1 | Other |
| 16 | Discovery |  |  | monument-class (901) | Other | 1 | Other |
| 274 | Flare | flare |  | miscellaneous-class (911) | Other | 1 | Other |
| 112 | Revealer |  |  | flag-class (930) | Other | 1 | Other |
| 837 | Map Revealer |  |  | flag-class (930) | Other | 1 | Other |
| 8 | Flying Dutchman |  |  | warship-class (922) | Other | 1 | Other |
| 115 | Medusa |  |  | infantry-class (906) | Other | 1 | Other |
| 106 | Black Rider |  |  | cavalry-archer-class (936) | Other | 1 | Other |
| 181 | Stealth Archer |  |  | archery-class (900) | Other | 1 | Other |
| 165 | Saint Francis |  |  | infantry-class (906) | Other | 1 | Other |
| 184 | Big Bertha |  |  | siege-weapon-class (913) | Other | 1 | Other |
| 1574 | Nuke Trooper |  |  | archery-cannon-class (944) | Other | 1 | Other |
| 1577 | Laser Trooper |  |  | archery-cannon-class (944) | Other | 1 | Other |
| 160 | Winsett's Z |  |  | infantry-class (906) | Other | 1 | Other |
| 161 | Winsett's other Z |  |  | infantry-class (906) | Other | 1 | Other |
| 164 | Zug 209 |  |  | infantry-class (906) | Other | 1 | Other |

---

## 4. 科技表 Technologies

字段：`id` / `name` / `aiName`（部分有）/ `building`（研究所）/ `age` / `civ`（专属文明）/ `notes`。RoR 那套字段不同：`cost`（如 `"300F, 100G"`）、`time`（秒）、`description`。

### 4.1 AoE2（主表）（原始 331 行 / 去重 326 个）

| ID | 名称 | aiName | 建筑 | 时代 | 专属文明 | 备注 |
|---|---|---|---|---|---|---|
| 100 | Crossbowman | ri-crossbow, ri-crossbowman (DE only) | Archery Range | 3 |  |  |
| 98 | Elite Skirmisher | ri-elite-skirmisher | Archery Range | 3 |  |  |
| 237 | Arbalest | ri-arbalest, ri-arbalester (DE only) | Archery Range | 4 |  |  |
| 218 | Heavy Cavalry Archer | ri-heavy-cavalry-archer | Archery Range | 4 |  |  |
| 85 | Hand Cannon | ri-hand-cannon | Archery Range | 4 |  |  |
| 655 | Imperial Skirmisher | ri-imperial-skirmisher | Archery Range | 4 | Vietnamese | Available for Vietnamese allies |
| 1451 | Heavy Mounted Crossbowman |  | Archery Range | 4 |  |  |
| 481 | Elite Elephant Archer | ri-elite-elephant-archer | Archery Range | 4 |  | DE only, same tech ID is used for unique unit upgrade for Indians civ in HD/WK |
| 1378 | Elite Bolas Rider |  | Archery Range | 4 | Mapuche |  |
| 599 | Elite Genitour | ri-elite-genitour | Archery Range | 4 | Berbers | Available for Berber allies |
| 437 | Thumb Ring | ri-thumb-ring | Archery Range | 3 |  |  |
| 436 | Parthian Tactics | ri-parthian-tactics | Archery Range | 4 |  |  |
| 1452 | Cranequins |  | Archery Range | 4 |  |  |
| 222 | Man-at-Arms | ri-man-at-arms | Barracks | 2 |  |  |
| 1402 | Champi Runner |  | Barracks | 2 |  |  |
| 207 | Long Swordsman | ri-long-swordsman | Barracks | 3 |  |  |
| 197 | Pikeman | ri-pikeman | Barracks | 3 |  |  |
| 384 | Eagle Warrior | ri-eagle-warrior | Barracks | 3 |  |  |
| 1351 | Champi Warrior |  | Barracks | 3 |  |  |
| 217 | Two-Handed Swordsman | ri-two-handed-swordsman | Barracks | 4 |  |  |
| 264 | Champion | ri-champion | Barracks | 4 |  |  |
| 885 | Legionary | ri-legionary | Barracks | 4 | Romans |  |
| 429 | Halberdier | ri-halberdier | Barracks | 4 |  |  |
| 434 | Elite Eagle Warrior | ri-elite-eagle-warrior | Barracks | 4 |  |  |
| 982 | Elite Fire Lancer |  | Barracks | 4 |  |  |
| 1352 | Elite Champi Warrior |  | Barracks | 4 |  |  |
| 1454 | Elite Varangian Guard |  | Barracks | 4 |  |  |
| 1391 | Elite Ibirapema Warrior |  | Barracks | 4 | Tupi |  |
| 1401 | Elite Temple Guard |  | Barracks | 4 | Muisca |  |
| 1387 | Elite War Dog |  | Barracks | 4 |  | Must be enabled by scenarios to be researched |
| 716 | Supplies | ri-supplies | Barracks | 2 |  |  |
| 875 | Gambesons | ri-gambesons | Barracks | 3 |  |  |
| 90 | Tracking | ri-tracking | Barracks | 2 |  | Auto-researched with barracks construction in Feudal Age in DE |
| 215 | Squires | ri-squires | Barracks | 3 |  |  |
| 602 | Arson | ri-arson | Barracks | 3 |  |  |
| 67 | Forging | ri-forging | Blacksmith | 2 |  |  |
| 199 | Fletching | ri-fletching | Blacksmith | 2 |  |  |
| 74 | Scale Mail Armor | ri-scale-mail | Blacksmith | 2 |  |  |
| 211 | Padded Archer Armor | ri-padded-archer-armor | Blacksmith | 2 |  |  |
| 81 | Scale Barding Armor | ri-scale-barding | Blacksmith | 2 |  |  |
| 68 | Iron Casting | ri-iron-casting | Blacksmith | 3 |  |  |
| 200 | Bodkin Arrow | ri-bodkin-arrow | Blacksmith | 3 |  |  |
| 76 | Chain Mail Armor | ri-chain-mail | Blacksmith | 3 |  |  |
| 212 | Leather Archer Armor | ri-leather-archer-armor | Blacksmith | 3 |  |  |
| 82 | Chain Barding Armor | ri-chain-barding | Blacksmith | 3 |  |  |
| 75 | Blast Furnace | ri-blast-furnace | Blacksmith | 4 |  |  |
| 201 | Bracer | ri-bracer | Blacksmith | 4 |  |  |
| 77 | Plate Mail Armor | ri-plate-mail | Blacksmith | 4 |  |  |
| 219 | Ring Archer Armor | ri-ring-archer-armor | Blacksmith | 4 |  |  |
| 80 | Plate Barding Armor | ri-plate-barding | Blacksmith | 4 |  |  |
| 315 | Conscription | ri-conscription | Castle | 4 |  |  |
| 379 | Hoardings | ri-hoardings | Castle | 4 |  |  |
| 321 | Sappers | ri-sappers | Castle | 4 |  |  |
| 408 | Spies/Treason |  | Castle | 4 |  | Use with <a href="/commands/commands-details.html#spy">spy</a> command to research Treason |
| 918 | Elite Composite Bowman | ri-elite-composite-bowman | Castle | 4 | Armenians | can use my-unique-unit-upgrade |
| 922 | Cilician Fleet | ri-cilician-fleet | Castle | 3 | Armenians | can use my-second-unique-research |
| 921 | Fereters | ri-fereters | Castle | 4 | Armenians | can use my-unique-research |
| 432 | Elite Jaguar Warrior | ri-elite-jaguar-man, ri-elite-jaguar-warrior (DE only) | Castle | 4 | Aztecs | can use my-unique-unit-upgrade |
| 460 | Atlatl | ri-atlatl | Castle | 3 | Aztecs | can use my-second-unique-research (DE only) |
| 24 | Garland Wars |  | Castle | 4 | Aztecs | can use my-unique-research |
| 828 | Elite Ratha | ri-elite-ratha | Castle | 4 | Bengalis | can use my-unique-unit-upgrade |
| 833 | Paiks | ri-paiks | Castle | 3 | Bengalis | can use my-second-unique-research |
| 834 | Mahayana | ri-mahayana | Castle | 4 | Bengalis | can use my-unique-research |
| 565 | Elite Camel Archer | ri-elite-camel-archer | Castle | 4 | Berbers | can use my-unique-unit-upgrade |
| 578 | Kasbah | ri-kasbah | Castle | 3 | Berbers | can use my-second-unique-research (DE only) |
| 579 | Maghrebi Camels | ri-maghrebi-camels | Castle | 4 | Berbers | can use my-unique-research |
| 781 | Elite Hussite Wagon | ri-elite-hussite-wagon | Castle | 4 | Bohemians | can use my-unique-unit-upgrade |
| 784 | Wagenburg Tactics | ri-wagenburg-tactics | Castle | 3 | Bohemians | can use my-second-unique-research |
| 785 | Hussite Reforms | ri-hussite-reforms | Castle | 4 | Bohemians | can use my-unique-research |
| 360 | Elite Longbowman | ri-elite-longbowman | Castle | 4 | Britons | can use my-unique-unit-upgrade |
| 3 | Yeomen |  | Castle | 3 | Britons | can use my-second-unique-research, my-unique-research in UP/WK |
| 461 | Warwolf | ri-warwolf | Castle | 4 | Britons | can use my-unique-research (DE only) |
| 678 | Elite Konnik | ri-elite-konnik | Castle | 4 | Bulgarians | can use my-unique-unit-upgrade |
| 685 | Stirrups | ri-stirrups | Castle | 3 | Bulgarians | can use my-second-unique-research |
| 686 | Bagains | ri-bagains | Castle | 4 | Bulgarians | can use my-unique-research |
| 751 | Elite Coustillier | ri-elite-coustillier | Castle | 4 | Burgundians | can use my-unique-unit-upgrade |
| 754 | Burgundian Vineyards | ri-burgundian-vineyards | Castle | 3 | Burgundians | can use my-second-unique-research |
| 755 | Flemish Revolution | ri-flemish-revolution | Castle | 4 | Burgundians | can use my-unique-research |
| 619 | Elite Arambai | ri-elite-arambai | Castle | 4 | Burmese | can use my-unique-unit-upgrade |
| 627 | Manipur Cavalry | ri-manipur-cavalry | Castle | 3 | Burmese | can use my-second-unique-research in DE, my-unique-research in WK |
| 626 | Howdah | ri-howdah | Castle | 4 | Burmese | can use my-unique-research in DE |
| 361 | Elite Cataphract | ri-elite-cataphract | Castle | 4 | Byzantines | can use my-unique-unit-upgrade |
| 464 | Greek Fire | ri-greek-fire | Castle | 3 | Byzantines | can use my-second-unique-research (DE only) |
| 61 | Logistica |  | Castle | 4 | Byzantines | can use my-unique-research |
| 370 | Elite Woad Raider | ri-elite-woad-raider | Castle | 4 | Celts | can use my-unique-unit-upgrade |
| 482 | Stronghold | ri-stronghold | Castle | 3 | Celts | can use my-second-unique-research (DE only) |
| 5 | Furor Celtica |  | Castle | 4 | Celts | can use my-unique-research |
| 362 | Elite Chu Ko Nu | ri-elite-chu-ko-nu | Castle | 4 | Chinese | can use my-unique-unit-upgrade |
| 462 | Great Wall | ri-great-wall | Castle | 3 | Chinese | can use my-second-unique-research (DE only) |
| 52 | Rocketry |  | Castle | 4 | Chinese | can use my-unique-research |
| 682 | Elite Kipchak | ri-elite-kipchak | Castle | 4 | Cumans | can use my-unique-unit-upgrade |
| 689 | Steppe Husbandry | ri-steppe-husbandry | Castle | 3 | Cumans | can use my-second-unique-research |
| 690 | Cuman Mercenaries | ri-cuman-mercenaries | Castle | 4 | Cumans | can use my-unique-research |
| 1482 | Elite Jomsviking |  | Castle | 4 | Danes | can use my-unique-unit-upgrade |
| 1484 | Hamask |  | Castle | 3 | Danes | can use my-second-unique-research |
| 1483 | Northmen's Fury |  | Castle | 4 | Danes | can use my-unique-research |
| 826 | Elite Urumi Swordsman | ri-elite-urumi-swordsman | Castle | 4 | Dravidians | can use my-unique-unit-upgrade |
| 831 | Medical Corps | ri-medical-corps | Castle | 3 | Dravidians | can use my-second-unique-research |
| 832 | Wootz Steel | ri-wootz-steel | Castle | 4 | Dravidians | can use my-unique-research |
| 569 | Elite Shotel Warrior | ri-elite-shotel | Castle | 4 | Ethiopians | can use my-unique-unit-upgrade |
| 574 | Royal Heirs | ri-royal-heirs | Castle | 3 | Ethiopians | can use my-second-unique-research (DE only) |
| 575 | Torsion Engines | ri-torsion, ri-torsion-engines | Castle | 4 | Ethiopians | can use my-unique-research |
| 363 | Elite Throwing Axeman | ri-elite-throwing-axeman | Castle | 4 | Franks | can use my-unique-unit-upgrade |
| 1496 | Ordonnance Companies |  | Castle | 3 | Franks | can use my-second-unique-research |
| 83 | Bearded Axe |  | Castle | 3 | Franks | my-unique-research in UP/WK |
| 493 | Chivalry | ri-chivalry | Castle | 4 | Franks | can use my-unique-research (DE only) |
| 920 | Elite Monaspa | ri-elite-monaspa | Castle | 4 | Georgians | can use my-unique-unit-upgrade |
| 923 | Svan Towers | ri-svan-towers | Castle | 3 | Georgians | can use my-second-unique-research |
| 924 | Aznauri Cavalry | ri-aznauri-cavalry | Castle | 4 | Georgians | can use my-unique-research |
| 365 | Elite Huskarl | ri-elite-huskarl | Castle | 4 | Goths | can use my-unique-unit-upgrade |
| 16 | Anarchy |  | Castle | 3 | Goths | can use my-second-unique-research, my-unique-research in UP/WK |
| 457 | Perfusion |  | Castle | 4 | Goths | can use my-unique-research (DE only) |
| 830 | Elite Chakram Thrower | ri-elite-chakram-thrower | Castle | 4 | Gurjaras | can use my-unique-unit-upgrade |
| 835 | Kshatriyas | ri-kshatriyas | Castle | 3 | Gurjaras | can use my-second-unique-research |
| 836 | Frontier Guards | ri-frontier-guards | Castle | 4 | Gurjaras | can use my-unique-research |
| 840 | Elite Ghulam | ri-elite-ghulam | Castle | 4 | Hindustanis | can use my-unique-unit-upgrade |
| 506 | Grand Trunk Road | ri-grand-trunk-road | Castle | 3 | Hindustanis | DE only, called Sultans in HD/WK for Indians civ, can use my-second-unique-research |
| 507 | Shatagni | ri-shatagni | Castle | 4 | Hindustanis | can use my-unique-research, same tech ID is used for Indians tech in HD/WK |
| 2 | Elite Tarkan | ri-elite-tarkan | Castle | 4 | Huns | can use my-unique-unit-upgrade |
| 483 | Marauders | ri-marauders | Castle | 3 | Huns | can use my-second-unique-research (DE only) |
| 21 | Atheism |  | Castle | 4 | Huns | can use my-unique-research |
| 509 | Elite Kamayuk | ri-elite-kamayuk | Castle | 4 | Incas | can use my-unique-unit-upgrade |
| 516 | Andean Sling | ri-andean-sling | Castle | 3 | Incas | can use my-second-unique-research (DE only) |
| 517 | Fabric Shields/Couriers | ri-fabric-shields | Castle | 4 | Incas | Renamed Fabric Shields in DE, can use my-unique-research |
| 468 | Elite Genoese Crossbowman | ri-elite-genoese-crossbowman | Castle | 4 | Italians | can use my-unique-unit-upgrade |
| 494 | Pavise | ri-pavise | Castle | 3 | Italians |  |
| 499 | Silk Road | ri-silk-road | Castle | 3 | Italians | can use my-second-unique-research (DE only), available in imperial age in HD/WK |
| 902 | Pirotechnia |  | Castle | 4 | Italians | can use my-unique-research |
| 366 | Elite Samurai | ri-elite-samurai | Castle | 4 | Japanese | can use my-unique-unit-upgrade |
| 484 | Yasama | ri-yasama | Castle | 3 | Japanese | can use my-second-unique-research (DE only) |
| 59 | Kataparuto |  | Castle | 4 | Japanese | can use my-unique-research |
| 991 | Elite Iron Pagoda |  | Castle | 4 | Jurchens | can use my-unique-unit-upgrade |
| 996 | Fortified Bastions |  | Castle | 3 | Jurchens | can use my-second-unique-research |
| 997 | Thunderclap Bombs |  | Castle | 4 | Jurchens | can use my-unique-research |
| 1002 | Elite Liao Dao |  | Castle | 4 | Khitans | can use my-unique-unit-upgrade |
| 1006 | Lamellar Armor |  | Castle | 3 | Khitans | can use my-second-unique-research |
| 1007 | Ordo Cavalry |  | Castle | 4 | Khitans | can use my-unique-research |
| 615 | Elite Ballista Elephant | ri-elite-ballista-elephant | Castle | 4 | Khmer | can use my-unique-unit-upgrade |
| 622 | Tusk Swords | ri-tusk-swords | Castle | 3 | Khmer | can use my-second-unique-research |
| 623 | Double Crossbow | ri-double-crossbow | Castle | 4 | Khmer | can use my-unique-research |
| 450 | Elite War Wagon | ri-elite-war-wagon | Castle | 4 | Koreans | can use my-unique-unit-upgrade |
| 486 | Eupseong/Panokseon | ri-eupseong | Castle | 3 | Koreans | can use my-second-unique-research (DE only) |
| 445 | Shinkichon |  | Castle | 4 | Koreans | can use my-unique-research |
| 684 | Elite Leitis | ri-elite-leitis | Castle | 4 | Lithuanians | can use my-unique-unit-upgrade |
| 691 | Hill Forts | ri-hill-forts | Castle | 3 | Lithuanians | can use my-second-unique-research |
| 692 | Tower Shields | ri-tower-shields | Castle | 4 | Lithuanians | can use my-unique-research |
| 472 | Elite Magyar Huszar | ri-elite-magyar-huszar | Castle | 4 | Magyars | can use my-unique-unit-upgrade |
| 514 | Corvinian Army/Mercenaries | ri-corvinian-army | Castle | 3 | Magyars | Renamed Corvinian Army in DE |
| 515 | Recurve Bow | ri-recurve-bow | Castle | 4 | Magyars | can use my-unique-research |
| 617 | Elite Karambit Warrior | ri-elite-karambit-warrior | Castle | 4 | Malay | can use my-unique-unit-upgrade |
| 624 | Thalassocracy | ri-thalassocracy | Castle | 3 | Malay | can use my-second-unique-research (DE only) |
| 625 | Forced Levy | ri-forced-levy | Castle | 4 | Malay | can use my-unique-research |
| 567 | Elite Gbeto | ri-elite-gbeto | Castle | 4 | Malians | can use my-unique-unit-upgrade |
| 576 | Tigui | ri-tigui | Castle | 3 | Malians | can use my-second-unique-research (DE only) |
| 577 | Farimba | ri-farimba | Castle | 4 | Malians | can use my-unique-research |
| 1376 | Elite Kona |  | Castle | 4 | Mapuche | can use my-unique-unit-upgrade |
| 1379 | Malon |  | Castle | 3 | Mapuche | can use my-second-unique-research (DE only) |
| 1380 | Butalmapu |  | Castle | 4 | Mapuche | can use my-unique-research |
| 27 | Elite Plumed Archer | ri-elite-plumed-archer | Castle | 4 | Mayans | can use my-unique-unit-upgrade |
| 485 | Obsidian Arrows |  | Castle | 3 | Mayans | removed in DE |
| 4 | Holcans/El Dorado |  | Castle | 4 | Mayans | can use my-unique-research |
| 371 | Elite Mangudai | ri-elite-mangudai | Castle | 4 | Mongols | can use my-unique-unit-upgrade |
| 487 | Nomads | ri-nomads | Castle | 3 | Mongols | can use my-second-unique-research (DE only) |
| 6 | Drill |  | Castle | 4 | Mongols | can use my-unique-research |
| 1364 | Elite Guecha Warrior |  | Castle | 4 | Muisca | can use my-unique-unit-upgrade |
| 1365 | Herbalism |  | Castle | 3 | Muisca | can use my-second-unique-research (DE only) |
| 1366 | Huaracas |  | Castle | 4 | Muisca | can use my-unique-research |
| 367 | Elite War Elephant | ri-elite-war-elephant | Castle | 4 | Persians | can use my-unique-unit-upgrade |
| 488 | Boiling Oil |  | Castle | 3 | Persians | removed in DE |
| 7 | Mahouts/Citadels |  | Castle | 4 | Persians | can use my-unique-research |
| 779 | Elite Obuch | ri-elite-obuch | Castle | 4 | Poles | can use my-unique-unit-upgrade |
| 782 | Szlachta Privileges | ri-szlachta-privileges | Castle | 3 | Poles | can use my-second-unique-research |
| 783 | Lechitic Legacy | ri-lechitic-legacy | Castle | 4 | Poles | can use my-unique-research |
| 563 | Elite Organ Gun | ri-elite-organ-gun | Castle | 4 | Portuguese | can use my-unique-unit-upgrade |
| 572 | Carrack | ri-carrack | Castle | 3 | Portuguese | Removed in DE |
| 1404 | Circumnavigation |  | Castle | 3 | Portuguese | can use my-second-unique-research |
| 573 | Arquebus | ri-arquebus | Castle | 4 | Portuguese | can use my-unique-research |
| 882 | Elite Centurion | ri-elite-centurion | Castle | 4 | Romans | can use my-unique-unit-upgrade |
| 883 | Ballistas | ri-ballistas | Castle | 3 | Romans | can use my-second-unique-research |
| 884 | Comitatenses | ri-comitatenses | Castle | 4 | Romans | can use my-unique-research |
| 368 | Elite Mameluke | ri-elite-mameluke | Castle | 4 | Saracens | can use my-unique-unit-upgrade |
| 28 | Bimaristan |  | Castle | 3 | Saracens | can use my-second-unique-research |
| 454 | Counterweights | ri-counterweights | Castle | 4 | Saracens | can use my-unique-research |
| 490 | Madrasah |  | Castle | 3 | Saracens | Removed in DE |
| 9 | Zealotry |  | Castle | 4 | Saracens | removed in DE, my-unique-research in UP/WK |
| 1462 | Elite Hearth Troop |  | Castle | 4 | Saxons | can use my-unique-unit-upgrade |
| 1491 | Clerical Recruitment |  | Castle | 3 | Saxons | can use my-second-unique-research |
| 1464 | Shield Wall |  | Castle | 4 | Saxons | can use my-unique-research |
| 1064 | Elite White Feather Guard |  | Castle | 4 | Shu | can use my-unique-unit-upgrade |
| 1069 | Bolt Magazine |  | Castle | 3 | Shu | can use my-second-unique-research |
| 1070 | Coiled Serpent Array |  | Castle | 4 | Shu | can use my-unique-research |
| 753 | Elite Serjeant | ri-elite-serjeant | Castle | 4 | Sicilians | can use my-unique-unit-upgrade |
| 756 | First Crusade | ri-first-crusade | Castle | 3 | Sicilians | can use my-second-unique-research |
| 757 | Hauberk | ri-hauberk | Castle | 4 | Sicilians | can use my-unique-research |
| 504 | Elite Boyar | ri-elite-boyar | Castle | 4 | Slavs | can use my-unique-unit-upgrade |
| 455 | Detinets | ri-detinets | Castle | 3 | Slavs | can use my-second-unique-research |
| 512 | Orthodoxy |  | Castle | 3 | Slavs | Removed in DE |
| 513 | Druzhina | ri-druzhina | Castle | 4 | Slavs | can use my-unique-research |
| 60 | Elite Conquistador | ri-elite-conquistador | Castle | 4 | Spanish | can use my-unique-unit-upgrade |
| 492 | Inquisition | ri-inquisition | Castle | 3 | Spanish | can use my-second-unique-research (DE only) |
| 440 | Supremacy |  | Castle | 4 | Spanish | can use my-unique-research |
| 680 | Elite Keshik | ri-elite-keshik | Castle | 4 | Tatars | can use my-unique-unit-upgrade |
| 687 | Silk Armor | ri-silk-armor | Castle | 3 | Tatars | can use my-second-unique-research |
| 688 | Timurid Siegecraft | ri-timurid-siegecraft | Castle | 4 | Tatars | can use my-unique-research |
| 364 | Elite Teutonic Knight | ri-elite-teutonic-knight | Castle | 4 | Teutons | can use my-unique-unit-upgrade |
| 489 | Ironclad | ri-ironclad | Castle | 3 | Teutons | can use my-second-unique-research (DE only) |
| 11 | Crenellations |  | Castle | 4 | Teutons | can use my-unique-research |
| 1389 | Elite Blackwood Archer |  | Castle | 4 | Tupi | can use my-unique-unit-upgrade |
| 1392 | Caciques |  | Castle | 3 | Tupi | can use my-second-unique-research (DE only) |
| 1393 | Curare |  | Castle | 4 | Tupi | can use my-unique-research |
| 369 | Elite Janissary | ri-elite-janissary | Castle | 4 | Turks | can use my-unique-unit-upgrade |
| 491 | Sipahi | ri-sipahi | Castle | 3 | Turks | can use my-second-unique-research (DE only) |
| 10 | Artillery |  | Castle | 4 | Turks | can use my-unique-research |
| 1472 | Elite Jarl |  | Castle | 4 | Varangians | can use my-unique-unit-upgrade |
| 1473 | Vendel Legacy |  | Castle | 3 | Varangians | can use my-second-unique-research |
| 1474 | Gothikon |  | Castle | 4 | Varangians | can use my-unique-research |
| 621 | Elite Rattan Archer | ri-elite-rattan-archer | Castle | 4 | Vietnamese | can use my-unique-unit-upgrade |
| 628 | Chatras | ri-chatras | Castle | 3 | Vietnamese | can use my-second-unique-research (DE only) |
| 629 | Paper Money | ri-paper-money | Castle | 4 | Vietnamese | can use my-unique-research |
| 398 | Elite Berserk | ri-elite-berserk | Castle | 4 | Vikings | can use my-unique-unit-upgrade |
| 463 | Chieftains | ri-chieftains | Castle | 3 | Vikings | can use my-second-unique-research (DE only) |
| 49 | Bogsveigar |  | Castle | 4 | Vikings | can use my-unique-research, previously called Berserkergang |
| 1036 | Elite Tiger Cavalry |  | Castle | 4 | Wei | can use my-unique-unit-upgrade |
| 1061 | Tuntian |  | Castle | 3 | Wei | can use my-second-unique-research |
| 1062 | Ming Guang Armor |  | Castle | 4 | Wei | can use my-unique-research |
| 1074 | Elite Fire Archer |  | Castle | 4 | Wu | can use my-unique-unit-upgrade |
| 1080 | Red Cliffs Tactics |  | Castle | 3 | Wu | can use my-second-unique-research |
| 1081 | Sitting Tiger |  | Castle | 4 | Wu | can use my-unique-research |
| 34 | Medium Warships | ri-war-galley | Dock | 3 |  | In DE, upgrades Galleys, Fire Galleys, and Hulks |
| 35 | Heavy Warships | ri-galleon | Dock | 4 |  | In DE, upgrades War Galleys, Fire Ships, and War Hulks |
| 246 | Fast Fire Ship | ri-fast-fire-ship | Dock | 4 |  |  |
| 1010 | Dragon Ship |  | Dock | 4 | Chinese | Now is upgraded with Heavy Warships |
| 905 | Demolition Ship |  | Dock | 3 |  |  |
| 244 | Heavy Demolition Ship | ri-heavy-demolition-ship | Dock | 4 |  |  |
| 37 | Cannon Galleon | ri-cannon-galleon | Dock | 4 |  | Free in DE |
| 376 | Elite Cannon Galleon | ri-deck-guns, ri-elite-cannon-galleon (DE only) | Dock | 4 |  |  |
| 597 | Elite Caravel | ri-elite-caravel | Dock | 4 | Portuguese |  |
| 372 | Elite Longboat | ri-elite-longboat | Dock | 4 | Vikings |  |
| 448 | Elite Turtle Ship | ri-elite-turtle-ship | Dock | 4 | Koreans |  |
| 906 | Fishing Lines |  | Dock | 2 |  |  |
| 65 | Gillnets | ri-gillnets | Dock | 3 |  |  |
| 1359 | 0% wood, 100% gold |  | Dock | 2 |  | Researched by trade cogs, changes wood/gold ratio that Trade Cogs drop off at the Dock |
| 1263 | 25% wood, 75% gold |  | Dock | 2 |  | No longer available |
| 1264 | 50% wood, 50% gold |  | Dock | 2 |  | Researched by trade cogs, changes wood/gold ratio that Trade Cogs drop off at the Dock |
| 1265 | 75% wood, 25% gold |  | Dock | 2 |  | No longer available |
| 1373 | 100% wood, 0% gold |  | Dock | 2 |  | Researched by trade cogs, changes wood/gold ratio that Trade Cogs drop off at the Dock |
| 202 | Double-Bit Axe | ri-double-bit-axe | Lumber Camp | 2 |  |  |
| 203 | Bow Saw | ri-bow-saw | Lumber Camp | 3 |  |  |
| 221 | Two-Man Saw | ri-two-man-saw | Lumber Camp | 4 |  |  |
| 19 | Cartography | ri-cartography | Market | 2 |  | Auto-researched with market construction in WK/DE |
| 23 | Coinage | ri-coinage | Market | 2 |  | Castle Age in WK/DE |
| 48 | Caravan | ri-caravan | Market | 3 |  |  |
| 17 | Banking | ri-banking | Market | 3 |  | Imperial Age in WK/DE |
| 15 | Guilds | ri-guilds | Market | 4 |  |  |
| 14 | Horse Collar | ri-horse-collar | Mill | 2 |  |  |
| 1014 | Domestication |  | Mill | 2 | Khitans |  |
| 13 | Heavy Plow | ri-heavy-plow | Mill | 3 |  |  |
| 1013 | Pastoralism |  | Mill | 3 | Khitans |  |
| 12 | Crop Rotation | ri-crop-rotation | Mill | 4 |  |  |
| 1012 | Transhumance |  | Mill | 4 | Khitans |  |
| 55 | Gold Mining | ri-gold-mining | Mining Camp | 2 |  |  |
| 278 | Stone Mining | ri-stone-mining | Mining Camp | 2 |  |  |
| 182 | Gold Shaft Mining | ri-gold-shaft-mining | Mining Camp | 3 |  |  |
| 279 | Stone Shaft Mining | ri-stone-shaft-mining | Mining Camp | 3 |  |  |
| 319 | Atonement | ri-atonement | Monastery | 3 |  |  |
| 252 | Fervor | ri-fervor | Monastery | 3 |  |  |
| 441 | Herbal Medicine |  | Monastery | 3 |  |  |
| 439 | Heresy | ri-heresy | Monastery | 3 |  |  |
| 316 | Redemption | ri-redemption | Monastery | 3 |  |  |
| 231 | Sanctity | ri-sanctity | Monastery | 3 |  |  |
| 46 | Devotion | ri-devotion | Monastery | 3 |  |  |
| 230 | Block Printing | ri-block-printing | Monastery | 4 |  |  |
| 45 | Faith | ri-faith | Monastery | 4 |  |  |
| 233 | Illumination | ri-illumination | Monastery | 4 |  |  |
| 438 | Theocracy | ri-theocracy | Monastery | 4 |  |  |
| 96 | Capped Ram | ri-capped-ram | Siege Workshop | 4 |  | Castle Age for Cuman civilization |
| 255 | Siege Ram | ri-siege-ram | Siege Workshop | 4 |  |  |
| 838 | Siege Elephant | ri-siege-elephant | Siege Workshop | 4 |  |  |
| 257 | Onager | ri-onager | Siege Workshop | 4 |  |  |
| 320 | Siege Onager | ri-siege-onager | Siege Workshop | 4 |  |  |
| 980 | Heavy Rocket Cart |  | Siege Workshop | 4 |  |  |
| 239 | Heavy Scorpion | ri-heavy-scorpion | Siege Workshop | 4 |  |  |
| 188 | Bombard Cannon | ri-bombard-cannon | Siege Workshop | 4 |  |  |
| 787 | Houfnice | ri-houfnice | Siege Workshop | 4 | Bohemians |  |
| 254 | Light Cavalry | ri-light-cavalry | Stable | 3 |  |  |
| 428 | Hussar | ri-hussar | Stable | 4 |  |  |
| 786 | Winged Hussar | ri-winged-hussar | Stable | 4 |  |  |
| 209 | Cavalier | ri-cavalier | Stable | 4 |  |  |
| 265 | Paladin | ri-paladin | Stable | 4 |  |  |
| 526 | Savar | ri-savar | Stable | 4 | Persians |  |
| 236 | Heavy Camel [Rider] | ri-heavy-camel, ri-heavy-camel-rider (DE only) | Stable | 4 |  | Renamed Heavy Camel Rider in DE |
| 521 | Imperial Camel [Rider] | ri-imperial-camel-rider | Stable | 4 | Hindustanis/Indians | Renamed Imperial Camel Rider in DE |
| 631 | Elite Battle Elephant | ri-elite-battle-elephant | Stable | 4 |  |  |
| 715 | Elite Steppe Lancer | ri-elite-steppe-lancer | Stable | 4 |  |  |
| 1033 | Elite Hei Guang Cavalry |  | Stable | 4 |  |  |
| 843 | Elite Shrivamsha Rider | ri-elite-shrivamsha-rider | Stable | 4 | Gurjaras |  |
| 435 | Bloodlines | ri-bloodlines | Stable | 2 |  |  |
| 39 | Husbandry | ri-husbandry | Stable | 3 |  |  |
| 22 | Loom | ri-loom | Town Center | 1 |  |  |
| 101 | Feudal Age | feudal-age | Town Center | 1 |  |  |
| 102 | Castle Age | castle-age | Town Center | 2 |  |  |
| 8 | Town Watch | ri-town-watch | Town Center | 2 |  |  |
| 213 | Wheelbarrow | ri-wheel-barrow | Town Center | 2 |  |  |
| 103 | Imperial Age | imperial-age | Town Center | 3 |  |  |
| 280 | Town Patrol | ri-town-patrol | Town Center | 3 |  |  |
| 249 | Hand Cart | ri-hand-cart | Town Center | 3 |  |  |
| 194 | Fortified Wall | ri-fortified-wall | University | 3 |  |  |
| 140 | Guard Tower | ri-guard-tower | University | 3 |  |  |
| 63 | Keep | ri-keep | University | 4 |  |  |
| 64 | Bombard Tower | ri-bombard-tower | University | 4 |  |  |
| 93 | Ballistics | ri-ballistics | University | 3 |  |  |
| 380 | Heated Shot | ri-heated-shot | University | 3 |  |  |
| 50 | Masonry | ri-masonry | University | 3 |  |  |
| 322 | Murder Holes | ri-murder-holes | University | 3 |  |  |
| 54 | Treadmill Crane | ri-stonecutting, ri-treadmill-crane (DE only) | University | 3 |  |  |
| 51 | Architecture | ri-architecture | University | 4 |  |  |
| 608 | Arrowslits | ri-arrowslits | University | 4 |  |  |
| 47 | Chemistry | ri-chemistry | University | 4 |  |  |
| 377 | Siege Engineers | ri-siege-engineers | University | 4 |  |  |
| 374 | Careening | ri-careening | University | 3 |  | Moved to the University in DE |
| 375 | Dry Dock | ri-dry-dock | University | 4 |  | Moved to the University in DE |
| 373 | Shipwright | ri-shipwright | University | 4 |  | Moved to the University in DE |
| 908 | Clinker Construction |  | University | 3 |  |  |
| 907 | Carvel Hull |  | University | 4 |  |  |
| 909 | Siphons |  | University | 3 |  |  |
| 910 | Incendiaries |  | University | 4 |  |  |

### 4.2 Chronicles（原始 163 行 / 去重 161 个）

| ID | 名称 | aiName | 建筑 | 时代 | 专属文明 | 备注 |
|---|---|---|---|---|---|---|
| 194 | Fortified Wall | ri-fortified-wall | Academy | 3 |  |  |
| 140 | Guard Tower | ri-guard-tower | Academy | 3 |  |  |
| 63 | Bastion | ri-keep | Academy | 4 |  |  |
| 93 | Target Practice | ri-ballistics | Academy | 3 |  |  |
| 380 | Lighthouse | ri-heated-shot | Academy | 3 |  |  |
| 50 | Masonry | ri-masonry | Academy | 3 |  |  |
| 322 | Murder Holes | ri-murder-holes | Academy | 3 |  |  |
| 54 | Treadmill Crane | ri-stonecutting | Academy | 3 |  |  |
| 51 | Architecture | ri-architecture | Academy | 4 |  |  |
| 608 | Arrowslits | ri-arrowslits | Academy | 4 |  |  |
| 47 | Flaming Arrows | ri-chemistry | Academy | 4 |  |  |
| 377 | Siege Engineers | ri-siege-engineers | Academy | 4 |  |  |
| 100 | Laminated Bowman | ri-crossbow, ri-crossbowman (DE only) | Archery Range | 3 |  |  |
| 98 | Elite Skirmisher | ri-elite-skirmisher | Archery Range | 3 |  |  |
| 237 | Recurve Bowman | ri-arbalest, ri-arbalester (DE only) | Archery Range | 4 |  |  |
| 218 | Heavy Cavalry Archer | ri-heavy-cavalry-archer | Archery Range | 4 |  |  |
| 437 | Thumb Ring | ri-thumb-ring | Archery Range | 3 |  |  |
| 436 | Parthian Tactics | ri-parthian-tactics | Archery Range | 4 |  |  |
| 1278 | Archery Range Balanced Doctrine |  | Archery Range | 2 | Macedonians |  |
| 1279 | Archery Range Conscript Doctrine |  | Archery Range | 2 | Macedonians |  |
| 1280 | Archery Range Mercenaries Doctrine |  | Archery Range | 2 | Macedonians |  |
| 222 | Maceman | ri-man-at-arms | Barracks | 2 |  |  |
| 207 | Swordsman | ri-long-swordsman | Barracks | 3 |  |  |
| 197 | Guardsman | ri-pikeman | Barracks | 3 |  |  |
| 1174 | Paragon |  | Barracks | 4 |  |  |
| 429 | Elite Guardsman | ri-halberdier | Barracks | 4 |  |  |
| 1137 | Elite Hoplite |  | Barracks | 4 |  |  |
| 1291 | Elite Phalangite |  | Barracks | 4 | Macedonians |  |
| 875 | Gambesons | ri-gambesons | Barracks | 3 |  |  |
| 215 | Baggage Carriers | ri-squires | Barracks | 3 |  |  |
| 602 | Arson | ri-arson | Barracks | 3 |  |  |
| 1173 | Battle Drills |  | Barracks | 4 |  | Equivalent of Two-handed Swordsman upgrade |
| 1275 | Barracks Balanced Doctrine |  | Barracks | 1 | Macedonians |  |
| 1276 | Barracks Conscript Doctrine |  | Barracks | 1 | Macedonians |  |
| 1277 | Barracks Mercenaries Doctrine |  | Barracks | 1 | Macedonians |  |
| 67 | Forging | ri-forging | Blacksmith | 2 |  |  |
| 199 | Fletching | ri-fletching | Blacksmith | 2 |  |  |
| 74 | Scale Mail Armor | ri-scale-mail | Blacksmith | 2 |  |  |
| 211 | Padded Archer Armor | ri-padded-archer-armor | Blacksmith | 2 |  |  |
| 81 | Scale Barding Armor | ri-scale-barding | Blacksmith | 2 |  |  |
| 68 | Iron Casting | ri-iron-casting | Blacksmith | 3 |  |  |
| 200 | Bodkin Arrow | ri-bodkin-arrow | Blacksmith | 3 |  |  |
| 76 | Chain Mail Armor | ri-chain-mail | Blacksmith | 3 |  |  |
| 212 | Leather Archer Armor | ri-leather-archer-armor | Blacksmith | 3 |  |  |
| 82 | Chain Barding Armor | ri-chain-barding | Blacksmith | 3 |  |  |
| 75 | Blast Furnace | ri-blast-furnace | Blacksmith | 4 |  |  |
| 201 | Bracer | ri-bracer | Blacksmith | 4 |  |  |
| 77 | Plate Mail Armor | ri-plate-mail | Blacksmith | 4 |  |  |
| 219 | Ring Archer Armor | ri-ring-archer-armor | Blacksmith | 4 |  |  |
| 80 | Plate Barding Armor | ri-plate-barding | Blacksmith | 4 |  |  |
| 315 | Conscription | ri-conscription | Fort | 4 |  |  |
| 379 | Hoardings | ri-hoardings | Fort | 4 |  |  |
| 321 | Sappers | ri-sappers | Fort | 4 |  |  |
| 408 | Spies/Treason |  | Fort | 4 |  | Use with <a href="/commands/commands-details.html#spy">spy</a> command to research Treason |
| 1115 | Elite Immortal |  | Fort | 4 | Achaemenids | can use my-unique-unit-upgrade |
| 1110 | Sparabaras |  | Fort | 3 | Achaemenids |  |
| 1111 | Reed Arrows |  | Fort | 3 | Achaemenids |  |
| 1112 | Scythed Chariots |  | Fort | 4 | Achaemenids |  |
| 1113 | Karda |  | Fort | 4 | Achaemenids |  |
| 1125 | Elite Strategos |  | Fort | 4 | Athenians | can use my-unique-unit-upgrade |
| 1120 | Taxiarchs |  | Fort | 3 | Athenians |  |
| 1121 | Iphicratean Tactics |  | Fort | 3 | Athenians |  |
| 1122 | Eisphora |  | Fort | 4 | Athenians |  |
| 1123 | Delian League |  | Fort | 4 | Athenians |  |
| 1289 | Elite Companion Cavalry |  | Fort | 4 | Macedonians | can use my-unique-unit-upgrade |
| 1284 | Veteran Chiliarchs |  | Fort | 3 | Macedonians |  |
| 1285 | Ends of the World |  | Fort | 3 | Macedonians |  |
| 1286 | Pezhetairoi |  | Fort | 4 | Macedonians |  |
| 1287 | Sarissophoroi |  | Fort | 4 | Macedonians |  |
| 1326 | Elite Pattiyodha Longbowman |  | Fort | 4 | Puru | can use my-unique-unit-upgrade |
| 1307 | Vadhavadha |  | Fort | 3 | Puru |  |
| 1308 | Leaf-Headed Shafts |  | Fort | 3 | Puru |  |
| 1309 | Vedic Teachings |  | Fort | 4 | Puru |  |
| 1310 | Skandhavaras |  | Fort | 4 | Puru |  |
| 1323 | Defensive Emplacement |  | Fort | 4 | Puru | Requires Skandhavaras |
| 1324 | Defensive Emplacement |  | Fort | 4 | Puru | Requires Skandhavaras |
| 1135 | Elite Hippeus |  | Fort | 4 | Spartans | can use my-unique-unit-upgrade |
| 1130 | Helot Levies |  | Fort | 3 | Spartans |  |
| 1131 | Krypteia |  | Fort | 3 | Spartans |  |
| 1132 | Xyphos |  | Fort | 4 | Spartans |  |
| 1133 | Peloponnesian League |  | Fort | 4 | Spartans |  |
| 1301 | Elite Rhomphaia Warrior |  | Fort | 4 | Thracians | can use my-unique-unit-upgrade |
| 1296 | Odomantian Raiders |  | Fort | 3 | Thracians |  |
| 1297 | Dii Plunderers |  | Fort | 3 | Thracians |  |
| 1298 | Bessian Metalworking |  | Fort | 4 | Thracians |  |
| 1299 | Peltasts |  | Fort | 4 | Thracians |  |
| 202 | Double-Bit Axe | ri-double-bit-axe | Lumber Camp | 2 |  |  |
| 203 | Bow Saw | ri-bow-saw | Lumber Camp | 3 |  |  |
| 221 | Two-Man Saw | ri-two-man-saw | Lumber Camp | 4 |  |  |
| 23 | Coinage | ri-coinage | Market | 3 |  |  |
| 48 | Caravan | ri-caravan | Market | 3 |  |  |
| 17 | Banking | ri-banking | Market | 4 |  |  |
| 15 | Guilds | ri-guilds | Market | 4 |  |  |
| 14 | Horse Collar | ri-horse-collar | Mill | 2 |  |  |
| 13 | Heavy Plow | ri-heavy-plow | Mill | 3 |  |  |
| 12 | Crop Rotation | ri-crop-rotation | Mill | 4 |  |  |
| 55 | Gold Mining | ri-gold-mining | Mining Camp | 2 |  |  |
| 278 | Stone Mining | ri-stone-mining | Mining Camp | 2 |  |  |
| 182 | Gold Shaft Mining | ri-gold-shaft-mining | Mining Camp | 3 |  |  |
| 279 | Stone Shaft Mining | ri-stone-shaft-mining | Mining Camp | 3 |  |  |
| 1270 | Fortified Outpost |  | Outpost | 1 | Macedonians |  |
| 1144 | War Lembos |  | Port | 2 |  |  |
| 1145 | Heavy Lembos |  | Port | 3 |  |  |
| 1146 | Elite Lembos |  | Port | 4 |  |  |
| 1255 | 0% wood, 100% gold |  | Port | 2 |  | Changes wood/gold ratio that Merchant Ships drop off at the Port |
| 1256 | 50% wood, 50% gold |  | Port | 2 |  | Changes wood/gold ratio that Merchant Ships drop off at the Port |
| 1257 | 75% wood, 25% gold |  | Port | 2 |  | Changes wood/gold ratio that Merchant Ships drop off at the Port |
| 1161 | Scoop Nets |  | Port | 3 |  | Gillnets equivalent, but new tech ID |
| 1162 | Drums |  | Port | 3 |  | Dry Dock equivalent, but new tech ID |
| 1167 | Shipwright |  | Port | 4 |  | New tech ID because the Port is a new building |
| 1151 | War Galley |  | Shipyard | 3 |  | New tech ID because the Shipyard is a new building |
| 1148 | Bireme |  | Shipyard | 3 |  |  |
| 1154 | Incendiary Ship |  | Shipyard | 3 |  |  |
| 1152 | Elite Galley |  | Shipyard | 4 |  |  |
| 1149 | Trireme |  | Shipyard | 4 |  |  |
| 1159 | Onager Ship |  | Shipyard | 4 |  |  |
| 1165 | Hypozomata |  | Shipyard | 3 |  | Careening Equivalent |
| 96 | Capped Ram | ri-capped-ram | Siege Workshop | 4 |  |  |
| 255 | Siege Ram | ri-siege-ram | Siege Workshop | 4 |  |  |
| 257 | Onager | ri-onager | Siege Workshop | 4 |  |  |
| 320 | Siege Onager | ri-siege-onager | Siege Workshop | 4 |  |  |
| 239 | Heavy Scorpion | ri-heavy-scorpion | Siege Workshop | 4 |  |  |
| 254 | Light Cavalry | ri-light-cavalry | Stable | 3 |  |  |
| 428 | Raider | ri-hussar | Stable | 4 |  |  |
| 209 | Shock Cavalry | ri-cavalier | Stable | 4 |  |  |
| 265 | Imperial Cavalry | ri-paladin | Stable | 4 |  |  |
| 236 | Elite War Chariot |  | Stable | 4 | Achaemenids |  |
| 1328 | Elite Sannahya |  | Stable | 4 | Puru |  |
| 435 | Bloodlines | ri-bloodlines | Stable | 2 |  |  |
| 39 | Husbandry | ri-husbandry | Stable | 3 |  |  |
| 1281 | Stable Balanced Doctrine |  | Stable | 2 | Macedonians |  |
| 1282 | Stable Conscript Doctrine |  | Stable | 2 | Macedonians |  |
| 1283 | Stable Mercenaries Doctrine |  | Stable | 2 | Macedonians |  |
| 319 | Syncretism | ri-atonement | Temple | 3 |  |  |
| 252 | Fervor | ri-fervor | Temple | 3 |  |  |
| 441 | Herbal Medicine |  | Temple | 3 |  |  |
| 439 | Hemlock | ri-heresy | Temple | 3 |  |  |
| 316 | Evocatio | ri-redemption | Temple | 3 |  |  |
| 231 | Apotropaic Magic | ri-sanctity | Temple | 3 |  |  |
| 230 | Haruspicy | ri-block-printing | Temple | 4 |  |  |
| 45 | Exorcism | ri-faith | Temple | 4 |  |  |
| 233 | Purification | ri-illumination | Temple | 4 |  |  |
| 438 | Mystery Cults | ri-theocracy | Temple | 4 |  |  |
| 22 | Loom | ri-loom | Town Center | 1 |  |  |
| 101 | Civic Age | feudal-age | Town Center | 1 |  |  |
| 102 | Classical Age | castle-age | Town Center | 2 |  |  |
| 8 | Town Watch | ri-town-watch | Town Center | 2 |  |  |
| 213 | Wheelbarrow | ri-wheel-barrow | Town Center | 2 |  |  |
| 103 | Imperial Age | imperial-age | Town Center | 3 |  |  |
| 280 | Town Patrol | ri-town-patrol | Town Center | 3 |  |  |
| 249 | Hand Cart | ri-hand-cart | Town Center | 3 |  |  |
| 1195 | Economic Satrapy |  | Town Center | 2 | Achaemenids |  |
| 1196 | Military Satrapy |  | Town Center | 2 | Achaemenids |  |
| 1197 | Defensive Satrapy |  | Town Center | 2 | Achaemenids |  |
| 1202 | Economic Policy |  | Town Center | 1 | Athenians |  |
| 1203 | Naval Policy |  | Town Center | 1 | Athenians |  |
| 1204 | Military Policy |  | Town Center | 1 | Athenians |  |
| 1223 | Ephorate |  | Town Center | 3 | Spartans |  |
| 1224 | Morai |  | Town Center | 3 | Spartans |  |
| 1225 | Skeuophoroi |  | Town Center | 3 | Spartans |  |
| 1226 | Hippagretai |  | Town Center | 4 | Spartans |  |

### 4.3 Return of Rome（原始 79 行 / 去重 79 个）

| ID | 名称 | 建筑 | 时代 | 造价 | 时间(s) | 类型 | 备注 |
|---|---|---|---|---|---|---|---|
| 73 | Phalangite | Academy | 4 | 300F, 100G | 90 | Upgrade | Called Phalanx before Return of Rome |
| 79 | Centurion | Academy | 4 | 1800F, 700G | 150 | Upgrade |  |
| 56 | Improved Bow | Archery Range | 3 | 140F, 80W | 45 | Enables Improved Bowman |  |
| 57 | Composite Bow | Archery Range | 3 | 180F, 100W | 100 | Upgrade |  |
| 38 | Heavy Horse Archer | Archery Range | 4 | 1750F, 800G | 150 | Upgrade |  |
| 63 | Battle Axe | Barracks | 2 | 100F | 40 | Upgrade |  |
| 65 | Broad Sword | Barracks | 3 | 140F, 50G | 90 | Upgrade |  |
| 66 | Long Sword | Barracks | 4 | 160F, 50G | 90 | Upgrade |  |
| 77 | Legionary | Barracks | 4 | 1400F, 600G | 150 | Upgrade | Called Legion before DE |
| 4 | Fishing Ship | Dock | 3 | 50F, 100W | 51 | Upgrade |  |
| 6 | Merchant Ship | Dock | 3 | 200F, 75W | 102 | Upgrade |  |
| 5 | War Galley | Dock | 3 | 150F, 75W | 128 | Upgrade | Required for Fire Galley |
| 8 | Heavy Transport | Dock | 4 | 150F, 125W | 180 | Upgrade |  |
| 7 | Trireme | Dock | 4 | 250F, 100W | 200 | Upgrade | Required for Catapult Trireme |
| 9 | Catapult Trireme | Dock | 4 | 300F, 100W | 100 | Upgrade | Requires Trireme |
| 25 | Juggernaut | Dock | 4 | 1300F, 700W | 200 | Upgrade |  |
| 34 | Nobility | Government Center | 3 | 175F, 120G | 70 | Horse units and Camel Riders +15% hit points |  |
| 19 | Writing | Government Center | 3 | 200F, 75G | 30 | Shared exploration with allies |  |
| 112 | Architecture | Government Center | 3 | 150F, 175W | 50 | Buildings -33% build time; +20% building hit points |  |
| 121 | Logistics | Government Center | 3 | 180F, 100G | 60 | Barracks units take 1/2 population |  |
| 128 | City Watch | Government Center | 3 | 200F | 45 | Buildings +3 LOS | Added in Return to Rome |
| 113 | Aristocracy | Government Center | 4 | 175F, 150G | 60 | Academy units move 25% faster |  |
| 106 | Ballistics | Government Center | 4 | 200F, 50G | 60 | Towers and ranged units have increased accuracy vs. moving targets | Required for Ballista Tower |
| 37 | Alchemy | Government Center | 4 | 250F, 200G | 100 | Ranged units and Fire Galleys +1 attack |  |
| 35 | Engineering | Government Center | 4 | 200F, 100W | 70 | +2 siege weapon/siege ship range |  |
| 129 | Conscription | Government Center | 4 | 450F, 250G | 60 | Land military units are trained 25% faster | Added in Return of Rome |
| 150 | Urbanization | Government Center | 4 | 350W, 150S | 45 | Houses provide double population space | Added in Return of Rome |
| 11 | Small Wall | Granary | 2 | 50F | 10 | Enables Small Wall |  |
| 16 | Watch Tower | Granary | 2 | 50F | 10 | Enables Watch Tower |  |
| 13 | Medium Wall | Granary | 3 | 180F, 100S | 60 | Upgrade |  |
| 12 | Sentry Tower | Granary | 3 | 120F, 50S | 30 | Upgrade |  |
| 14 | Fortified Wall | Granary | 4 | 300F, 175S | 75 | Upgrade |  |
| 15 | Guard Tower | Granary | 4 | 300F, 100S | 75 | Upgrade |  |
| 2 | Ballista Tower | Granary | 4 | 1800F, 750S | 150 | Upgrade | Requires Ballistics |
| 107 | Woodworking | Market | 2 | 120F, 75W | 60 | Woodcutters work 20% faster, carry +2 wood; +1 missile weapon range |  |
| 81 | Domestication | Market | 2 | 150F, 50W | 40 | Farms carry +75 food |  |
| 109 | Stone Mining | Market | 2 | 100F, 50S | 30 | Stone miners work 30% faster, carry +3 stone; Slingers +1 attack/range |  |
| 108 | Gold Mining | Market | 2 | 120F, 100W | 50 | Gold miners work 30% faster, carry +3 gold |  |
| 32 | Artisanship | Market | 3 | 170F, 150W | 80 | Woodcutters work 20% faster, carry +2 wood; +1 missile weapon range |  |
| 31 | Plow | Market | 3 | 250F, 75W | 75 | Farms carry +100 food |  |
| 28 | Wheel | Market | 3 | 175F 75W | 90 | Villagers move 50% faster | Required for chariots and trade carts |
| 110 | Craftsmanship | Market | 4 | 240F, 200W | 100 | Woodcutters work 20% faster, carry +2 wood; +1 missile weapon range |  |
| 80 | Irrigation | Market | 4 | 300F, 100W | 100 | Farms carry +125 food |  |
| 111 | Siegecraft | Market | 4 | 190F, 100S | 60 | Stone miners work 30% faster, carry +3 stone; slingers +1 attack/range; villagers +10 attack vs. buildings |  |
| 30 | Coinage | Market | 4 | 200F, 100G | 60 | Gold mines last 25% longer; Gold miners gather 33% faster, carry +3 gold; free tribute |  |
| 54 | Catapult | Siege Workshop | 4 | 300F, 250W | 100 | Upgrade |  |
| 36 | Heavy Catapult | Siege Workshop | 4 | 1800F, 900W | 150 | Upgrade |  |
| 27 | Helepolis | Siege Workshop | 4 | 1500F, 1000W | 150 | Upgrade |  |
| 71 | Heavy Cavalry | Stable | 4 | 350F, 125G | 100 | Upgrade |  |
| 78 | Cataphract | Stable | 4 | 1600F, 600G | 150 | Upgrade |  |
| 126 | Scythe Chariot | Stable | 4 | 1400W, 1000G | 200 | Upgrade |  |
| 125 | Armored Elephant | Stable | 4 | 1200F, 1000W | 150 | Upgrade |  |
| 46 | Toolworking | Storage Pit | 2 | 100F | 40 | +2 melee unit attack |  |
| 40 | Infantry Leather Armor | Storage Pit | 2 | 75F | 30 | +2 infantry melee armor |  |
| 41 | Archer Leather Armor | Storage Pit | 2 | 100F | 30 | +2 archer melee armor |  |
| 42 | Cavalry Leather Armor | Storage Pit | 2 | 125F | 30 | +2 cavalry melee armor |  |
| 51 | Metalworking | Storage Pit | 3 | 200F, 120G | 75 | +2 melee unit attack |  |
| 43 | Infantry Scale Armor | Storage Pit | 3 | 100F, 50G | 60 | +2 infantry melee armor |  |
| 44 | Archer Scale Armor | Storage Pit | 3 | 125F, 50G | 60 | +2 archer melee armor |  |
| 45 | Cavalry Scale Armor | Storage Pit | 3 | 150F, 50G | 45 | +2 cavalry melee armor |  |
| 47 | Bronze Shield | Storage Pit | 3 | 150F, 180G | 50 | +1 infantry armor vs. missile weapons |  |
| 52 | Metallurgy | Storage Pit | 4 | 300F, 180G | 100 | +3 melee unit attack |  |
| 48 | Infantry Chain Mail | Storage Pit | 4 | 125F, 100G | 75 | +2 infantry melee armor |  |
| 49 | Archer Chain Mail | Storage Pit | 4 | 150F, 100G | 75 | +2 archer melee armor |  |
| 50 | Cavalry Chain Mail | Storage Pit | 4 | 175F, 100G | 75 | +2 cavalry melee armor |  |
| 117 | Iron Shield | Storage Pit | 4 | 320F, 200G | 75 | +1 infantry armor vs. missile weapons |  |
| 122 | Tower Shield | Storage Pit | 4 | 400F, 250G | 100 | +1 infantry armor vs. missile weapons |  |
| 22 | Astrology | Temple | 3 | 150G | 50 | Conversion and healing 30% more effective |  |
| 24 | Polytheism | Temple | 3 | 120G | 50 | Priests move 40% faster |  |
| 21 | Mysticism | Temple | 3 | 120G | 50 | Double Priest hit points |  |
| 119 | Medicine | Temple | 4 | 150G | 50 | Increases Priest healing rate |  |
| 18 | Afterlife | Temple | 4 | 275G | 75 | Priests +3 conversion range |  |
| 114 | Monotheism | Temple | 4 | 350G | 75 | Priests can convert enemy Priests and buildings |  |
| 20 | Fanaticism | Temple | 4 | 150G | 60 | Priests restore faith 50% faster |  |
| 23 | Zealotry | Temple | 4 | 120G | 60 | Villagers move faster, are much stronger in combat, but carry less resources |  |
| 120 | Theocracy | Temple | 4 | 400G | 100 | Only one Priest in a group must rest after a conversion | Added in Return to Rome |
| 101 | Tool Age | Town Center | 1 | 500F | 120 | Advance to Tool Age |  |
| 102 | Bronze Age | Town Center | 2 | 800F | 140 | Advance to Bronze Age |  |
| 103 | Iron Age | Town Center | 3 | 1000F, 800G | 160 | Advance to Imperial Age |  |

---

## 5. SN 编号 0–511 的使用建议

来自 `strategic-numbers/sn-index-by-id` 页面原文（这是这一页最有价值的一句话，别的页面没写）：

> There are a total of 512 strategic numbers, numbered 0 to 511, that the game has made available, but currently there are only about 300 of them being used. The other 200 or so strategic numbers are not listed in the table below, and they can be used like extra goals. It's recommended to start with strategic number ID **510** (SN ID 511 currently has some bugs in DE) and work your way **descending** in ID until you reach the active strategic numbers, because DE can continue to add strategic numbers to the game and you don't want your custom strategic number to conflict with it.

落到实操：

1. 自定义 SN 从 **510 往下**取，别从 0 往上（DE 新版会往后加 SN，从低端占位必然撞车）。
2. **SN 511 在 DE 有 bug**，不要用。
3. 约 300 个已启用（见 03 卷的 `snArray` 313 条，含 13 条仅定义未启用）。
4. 用 SN 当 goal 的写法：`(set-strategic-number 510 1)` + `(strategic-number 510 == 1)`，注意 SN 是**有符号整数**、`min/max` 见 03 卷。

`sn-index-by-id` 页面的筛选维度（与 `sn-index` 同源，只是排序不同）：Search / Category（Attack, Buildings, Build Plan, Defense, Diplomacy, Economy, Exploring, Water, Other, None）/ Effective（All, Yes, No）/ Network（All, Network, Standard）/ Defined（All, Defined, Undefined）/ Active（All, Active, Conditional, Obsolete）/ Version（All, AoE1, AoC, UP, DE）。

---

## 6. AI 脚本赛事（events-index 全量）

| 状态 | 赛事 | 主办 | 时间 | 观赛/回放 |
|---|---|---|---|---|
| 即将开赛 | AIScripters Championship 2026 | Aleph | 2026 年 8–10 月 | Aleph 的 Twitch；对阵表 pending |
| 已完赛 | Prince of Nomad | Arandi | 2026 年 1–2 月 | 录播 pending |
| 已完赛 | Variety Cup | Bandit | 2025 年 11–12 月 | Bandit 的 Twitch + AIScripters YouTube |
| 已完赛 | FenCrazy Thing 9 | Aleph | 2025 年 10–11 月 | AIScripters YouTube |
| 已完赛 | 1v1 Bi-Map AI Tournament | Leif Ericson | 2025 年 8–9 月 | AIScripters Archive YouTube |

页面另有「Tournament History」链接，指向 2016 年以来的完整赛事史（外部 Google Sheet）。
社区说明原文大意：AI Scripters 社区定期在不同地图/设置下办「AI 对 AI」的比赛。

---

## 7. 外部资源索引（res-index 全量）

### 7.1 站内文章（全部已进 14 卷）

- A Collection of Helpful Info and Tips
- AI Command Performance Benchmarks
- Data Limits
- Defconsts, Goals, and Strategic Numbers
- How to Reference Players with AI Scripting Commands
- Intro to Commands
- Logical Operator Commands
- Star Wars Galactic Battlegrounds - AI Scripting Reference
- The Seventeen Strategic Number Settings You Must Change Immediately
- XS Scripting for AI Tournaments

### 7.2 DUC 教程

- Enmipho's Introduction to DUC
- Leif Ericson's Introduction to DUC（原站标注 incomplete）

### 7.3 外部站点与工具

| 资源 | 用途 |
|---|---|
| AI Ladder | AI 天梯，按月跑分 |
| AI Scripters Discord / Forums | 社区（`forums.aiscripters.com`） |
| AI Tournaments History Spreadsheet | 2016 年以来的赛事史 |
| AoE AI Database | 每个 AI 带 Elo 评分 |
| Arandi's / interlepus' YouTube 教程 | 视频教程 |
| HD AI Scripting Reference | HD 版 AI 参考 |
| Jan1302's AI Builder（archive.org） | 老式 AI 生成器 |
| MrElephant's Twitch | AI Scripting 与 AI Builder 入门直播 |
| Userpatch Website | UP 版本文档 |
| VS Code AI Scripting Language Extension | `.per` 语法高亮 |
| XS Scripting Reference | XS 参考（= UGC Guide 的 XS 章，见 05 卷） |

---

## 8. 已知 bug（84 条）

按报告日期倒序。每条给：标题 / 日期 / 涉及命令 / 涉及参数 / 涉及 SN / 说明 / 链接。

### 8.1 MapType constants incorrectly defined for AIs

- 日期：Nov 4, 2026
- 命令：`@map-type`
- 参数：`@MapType`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1567605015030530160">Link</a>

Minor bugs, but internal AI constants in the maps.json are defined in a confusing (and likely incorrect) way for the Moats and Teams Moats maps. The Moats map has no internal constant, and Team Moats is confusingly defined as moats. Also, there are also several constants in maps.json which contain a space, which the AI engine cannot handle, requiring AI scripters to manually defconst them. Currently Chaos Pit, Dorothea Quarry, Loch Ness, and Arabian Desert all contain spaces in their const_name definitions. A few dozen maps lack a const_name variable altogether, forcing AI scripters to defconst them.

### 8.2 up-assign-builders functionality has changed

- 日期：Oct 6, 2026
- 命令：`@up-assign-builders`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1556930564412538883">Link</a>

Elias: There is a new issue with assigning the first villagers to the first houses, on the newest patch. I think someone else reported it a while ago too. Both houses get only one builder each, even though there previously were two builders on one of the houses, with the same code. @fireball37's first two houses snippet is a reference implementation. My code is based on that. It uses (up-assign-builders c: house c: 2), not villager DUC, and this used to assign two villagers to the first house and assign the third villager to the second house. Update from interlepus: Yes, I have had issues with the first house too. had to review this completely, it was taking one vill from the 2 assigned to the first house to build de 2nd, while before the patch 2 went to house 1 and 1 went to house 2. So somehow I'm guessing the up assign builders command doesnt prevent villagers who have just been assigned to another building to be assigned as the builder to a new foundation.

### 8.3 actionid-research, orderid-research, and object-data-researching don't detect when a building is researching

- 日期：Oct 3, 2026
- 命令：`@up-get-object-data`, `@up-object-data`, `@up-filter-include`, `@up-filter-exclude`, `@up-remove-objects`
- 参数：`@ActionId`, `@OrderId`, `@ObjectData`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1556019050818183289">Link</a>

actionid-research and orderid-research don't seem to work at all, neither with up-filter-exclude nor with up-remove-objects. Nor does object-data-researching. When a blacksmith is researching scale mail armor, actionid-research and orderid-research are -1, and object-data-researching is 0. For now, object-data-progress-type might be the only way to check if a building is researching something.

### 8.4 AISCRIPTPROFILING launch parameter degrades performance

- 日期：Sep 29, 2026
- SN：`@sn-profiling-threshold`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1554467621284352111">Link</a>

Be advised that the AISCRIPTPROFILING launch option massively degrades AI performance (by about 4 times, at first glance).

### 8.5 object-data-ballistics doesn't work for town centers

- 日期：Sep 29, 2026
- 命令：`@up-get-object-data`, `@up-object-data`, `@up-remove-objects`
- 参数：`@ObjectData`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1554387200714739854">Link</a>

object-data-ballistics doesn't work for town-center. Just gives -2.

### 8.6 object-data-faith does not work anymore on DE

- 日期：Sep 28, 2026
- 命令：`@up-get-object-data`, `@up-object-data`, `@up-remove-objects`
- 参数：`@ObjectData`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1554122315489480725">Link</a>

object-data-faith does not work anymore on DE.

### 8.7 up-get-object-type-data doesn't work with object-data-attack-delay

- 日期：Sep 28, 2026
- 命令：`@up-get-object-type-data`
- 参数：`@ObjectData`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1554025124423008299">Link</a>

up-get-object-type-data doesn't work with attack-delay. Just gives -2. Might also be worth checking if any other DE object-datas are bugged with this command.

### 8.8 (up-jump-rule 10000) can cause crashes

- 日期：Sep 27, 2026
- 命令：`@up-jump-rule`, `@up-jump-dynamic`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1553877681425223721">Link</a>

Discovered another bug, which might be the cause of Bambi's crashes, since Bambi has several (up-jump-rule 10000) lines. An AI with just this code (defrule (true) => (up-jump-rule 10000)) causes the game to crash or fails to render the game about 10-20% of the time on any map. Sometimes it takes me 5-12 restarts of the same game to cause the crash/failed game start, but I can always reproduce it eventually.

### 8.9 4x4 building placement is bugged

- 日期：Sep 24, 2026
- 命令：`@build`, `@build-forward`, `@can-build`, `@can-build-with-escrow`, `@up-build`, `@up-can-build`, `@up-pending-placement`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1552712460912558124">Link</a>

4x4 building placement bug isnt fixed. Just had a game where half the players were completely unable to build a market for an hour. Then suddenly were after i manually placed one.

### 8.10 up-create-group doesn't work with group 20

- 日期：Sep 18, 2026
- 命令：`@up-create-group`, `@up-set-group`, `@up-modify-group-flag`
- 参数：`@GroupId`, `@ObjectData`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1550490014872240179">Link</a>

up-create-group doesn't work with group 20 despite the game including up to group 20 in DE. Group 19 still works, including with up-modify-group-flag, so you can see groups 1 to 19 in game. Note that up-create-group/up-modify-group-flag work perfectly with group 0 despite not being visible in game. Ungrouped units have a group-flag of -2. In userpatch, groups 0 to 9 all work perfectly.

### 8.11 Pasture counts work differently than expected for the different types of pastures

- 日期：Sep 9, 2026
- 命令：`@building-type-count`, `@building-type-count-total`, `@players-building-type-count`, `@cc-players-building-type-count`, `@up-object-type-count`, `@up-object-type-count-total`, `@up-get-fact`, `@up-get-player-fact`, `@up-get-fact-max`, `@up-get-fact-min`, `@up-get-fact-sum`, `@up-find-local`, `@up-find-status-local`, `@up-find-remote`, `@up-find-status-remote`
- 参数：`@BuildingId`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1547454463441379429">Link</a>

Count pasture-land/pasture-mangrove only count land/mangrove. Count pasture gives 0. This is different for farms where farm counts both land and mangrove, while farm-mangrove only counts mangrove. All pending pastures are included in pasture-land, and never pasture/pasture-mangrove. Again it's different for farms, where farm counts land and mangrove, and count pending farm-mangrove only counts mangrove.

### 8.12 Pasture animals are farm class

- 日期：Sep 9, 2026
- 命令：`@unit-type-count`, `@unit-type-count-total`, `@players-unit-type-count`, `@cc-players-unit-type-count`, `@up-object-type-count`, `@up-object-type-count-total`, `@up-get-fact`, `@up-get-player-fact`, `@up-get-fact-max`, `@up-get-fact-min`, `@up-get-fact-sum`, `@up-find-local`, `@up-find-status-local`, `@up-find-remote`, `@up-find-status-remote`
- 参数：`@ClassId`, `@FactId`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1547454382218678282">Link</a>

Pasture animals are farm-class, so counting farm-class or using duc on farm-class doesnt work properly. This should be changed.

### 8.13 villager-herder set is missing

- 日期：Sep 9, 2026
- 命令：`@unit-type-count`, `@unit-type-count-total`, `@players-unit-type-count`, `@cc-players-unit-type-count`, `@up-object-type-count`, `@up-object-type-count-total`, `@up-get-fact`, `@up-get-player-fact`, `@up-get-fact-max`, `@up-get-fact-min`, `@up-get-fact-sum`
- 参数：`@SetId`, `@UnitId`, `@FactId`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1547139274917285888">Link</a>

Missing set for villager-herder. They are still included in villager-food, however.

### 8.14 Units with secondary units for training at separate buildings have the wrong training location or don't have a duplicate unit altogether

- 日期：Sep 8, 2026
- 命令：`@can-train`, `@can-train-with-escrow`, `@train`, `@up-can-train`, `@up-train`, `@up-train-site-ready`, `@up-get-object-data`, `@up-object-data`, `@up-target-point`
- 参数：`@ObjectData`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1546839228271562823">Link</a>

I cant remember if i reported this before but the train-site for barracks-huskarl is castle instead of barracks. Same for the tarkan. Also, units with multiple train locations that have been introduced since the Last Chieftains DLC (e.g. settlement spearmen/skirms or monastery temple guards) do not have a separate training ID to train them from their secondary building, and only using action-train with up-target-point can currently train them from their secondary building.

### 8.15 The can-afford commands don't take into account resources spent on buildings during the current script pass

- 日期：Sep 5, 2026
- 命令：`@can-afford-building`, `@can-afford-complete-wall`, `@can-afford-research`, `@can-afford-unit`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1545860910671732838">Link1</a>, <a href="https://discord.com/channels/485565215161843714/485566694912163861/1546318732660576346">Link2</a>

The can-afford commands don't take into account resources spent on buildings during the current script pass. They do account for resources spent on units and techs though. The same bug happens in UserPatch.

### 8.16 up-can-research and up-research allow escrow to be used when using 0 as the EscrowGoalId

- 日期：Sep 5, 2026
- 命令：`@up-can-research`, `@up-research`
- 参数：`@EscrowGoalId`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1545802172766228570">Link</a>

Using 0 for the EscrowGoalId with up-can-research and up-research incorrectly allows escrowed resources to be used. With gold escrow set to 100 at the start, (up-can-research g-escrow c: ri-loom) correctly returns false if g-escrow is set to 1, i.e. without-escrow, but it returns true in all other cases at the start of the game, including if 0 is used instead of g-escrow. can-research/can-research-with-escrow/up-can-train/up-can-build all work as expected.

### 8.17 AI tick rates much higher in multiplayer games

- 日期：Aug 28, 2026
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1542830379369631774">Link</a>

MP tick rates for ai's have been bugged for a long time now. Currently averaging between 1000 ms (with one ai player and a human) and 2500 ms (with 7 ai players and a human) between ticks for empty ai files containing only a rare chat message about tick rate and the calculations thereoff. This is very far from the expected 666ms on 2.0 speed. The game also is choppy which is not the case without ai players. The choppiness is not affected by the number of ai players nor their code as it's the same with 1 empty ai as with 1 DE ai or even 7 Rehoboams. When I did the same tests a few months ago the issues were that the tick rates were actually to fast which doesn't seem the case anymore. A few years ago we didn't seem to have any of these issues. Apart from the choppiness obviously being less than ideal, it also would nerf the timing based ai's, including the DE ai alot to play with a tick rate of 2500ms. My pc has a benchmark score of 1300 and never lags in single player or online human games.

### 8.18 up-get-player-fact crashes when used with an invalid player

- 日期：Aug 27, 2026
- 命令：`@up-get-player-fact`
- 参数：`@FactId`, `@FactParameter`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1543588106337525820">Link</a>

Apparently if you use (up-get-player-fact military-population) on a player that isn't in the game, it'll crash. Had it happen several times already (works fine in 8-player games afaik since there is all players available). Update from Leif: This crash only occurs when the player used is between 3 and 8, and it is equal to the number of players in the game, +1. So, in a 2 player game, player 3 causes a crash. In a 4 player game, player 5 causes a crash. But, in a 4v4, player 9 doesn't cause a crash. Using focus-player or target-player for the player number doesn't crash, nor does any other command that uses Fact Ids.

### 8.19 Gather point bugs during ungarrison

- 日期：Aug 26, 2026
- 命令：`@up-gather-inside`, `@up-ungarrison`, `@up-target-objects`, `@up-target-point`
- 参数：`@DUCAction`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1542182968980807701">Original Post</a>, <a href="https://discord.com/channels/485565215161843714/925409493792202813/1542425839151349840">Update</a>

Just tested gather points on DE again. Here's the current status. For gather points it's not necessary to set it in the previous loop - instead you can just set it right before ungarrisoning a unit. The gather point still doesn't work for object targets - the units will always move to the point of the gather point but not target the object. This applies for all military and resource targets. Even if a human sets the gather point to a target, or does the ungarrison for an AI player it still wont work. Military units will always go to the point that you target. Villagers sometimes do that but sometimes will instantly reassign to their preferred resource and never go to the target. It seems to random. Either way, the villagers wont actually collect resources from the target you set. Also, the units always ungarrison at the bottom corner of the building, rather than the closest point to the gather point, like they would for humans. Update: I did some more testing with up-gather-inside. Actually it seems like all the weird behavior is caused by this command. If you avoid using this you can use gather points properly but the units will ungarrison instantly . The only way to avoid the instant ungarrison is by setting the gather point to itself. But this has the side effect of also garrisoning newly trained units. What we actually need is a way to turn off the auto ungarrison.

### 8.20 action-train and action-research escrow bugs

- 日期：Aug 18, 2026
- 命令：`@up-target-point`
- 参数：`@DUCAction`, `@EscrowGoalId`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1539131107956625508">Link</a>

action-train and action-research have issues bypassing escrow with up-target-point. For action-train, you have to use 1 rather than a GoalId to bypass escrow, e.g. (up-target-point 1 action-train c: knight-line). action-research cannot bypass escrow at all. For the first parameter, I tried 0, 1, a goal set to with-escrow, and a goal set to without-escrow, and nothing allowed action-research to bypass escrow.

### 8.21 Laggy villager assignment on water maps

- 日期：Aug 10, 2026
- 命令：`@up-idle-unit-count`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1536379020990611548">Link</a>

On Four Lakes (and perhaps on other water maps), the villager assignment system seems to be increasingly laggy as the game goes on. Past the 35 minute mark in an all-DE-AI 4v4, the DE AI's newly created villagers had around 5-10 seconds of idle time before given a task, and this idle time increased as the game progressed, sometimes to more than 25 seconds. The temporarily idling also happened for villagers that finished a task. This idle time did not exist when I ran a 4v4 all-DE-AI on Arabia. Proseon noticed this behavior happening with his AI also. However, it doesn't happen with my AI, which doesn't make fishing ships. I suspect having fishing ships might be the cause of this idle villager behavior.

### 8.22 Several unit sets or unit IDs aren't counted correctly for enemy players

- 日期：Aug 1, 2026
- 命令：`@players-unit-type-count`, `@up-get-player-fact`, `@up-get-focus-fact`, `@up-get-target-fact`, `@up-get-fact-sum`, `@up-get-fact-max`, `@up-get-fact-min`
- 参数：`@FactId`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1533265272222384359">Link</a>

Counting enemy units, e.g. up-get-target-fact unit-type-count or up-get-fact-sum any-enemy unit-type-count returns -1 or -2 values for the following unit-lines/sets: flemish-pikeman-set, foot-konnik-line, rocket-cart-line, monk-set, flemish-pikeman, flemish-pikeman-female, monk-with-relic, warrior-priest-with-relic, and missionary-with-relic. Self and allied units are counted correctly.

### 8.23 object-data-carry bugged for pastures

- 日期：Jun 24, 2026
- 命令：`@up-get-object-data`, `@up-object-data`, `@up-remove-objects`, `@up-clean-search`
- 参数：`@ObjectData`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1519513889874772110">Link</a>

object-data-carry for pastures is -2 unless a particular one of the three pasture animals on it has been killed, and then object-data-carry works properly.

### 8.24 The move position of groups of units in transport ships is bugged when the transport ship stops moving

- 日期：Jun 12, 2026
- 命令：`@up-get-object-data`, `@up-object-data`, `@up-remove-objects`
- 参数：`@ObjectData`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1514968574735941792">Link</a>

Here's a weird bug involving transport ships. If you decide to garrison a group into a transport ship their move pos will be constantly set to the transport ship location (as expected). If you unload the group somewhere their move pos will be set to the location they unboarded (as expected). If you move the group around as a group the move position will continue to update as expected. But the moment the group stops, the move postion gets reset to the position where they originally boarded the ship. I suspect this happens whenever they break formation. Probably it doesn't properly update the move position of the individual units in this scenario. Usually when a group stops, the move position gets reset to -1.

### 8.25 up-clean-search doesn't work with search-order-none

- 日期：Jun 3, 2026
- 命令：`@up-clean-search`
- 参数：`@SearchOrder`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1511620981716811827">Link</a>

up-clean-search for duplicate removal (value -1) does not work for search-order-none, it just does nothing in this case.

### 8.26 sn-fishing-boat-whaling-percentage > 0 causes most fishing boats to be sent to explore if whales haven't been found

- 日期：May 5, 2026
- SN：`@sn-fishing-boat-whaling-percentage`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1501218979534868600">Link</a>

I am having a weird issue where only about three fishing ships are fishing, and the rest are roaming around like the first one, possibly exploring. I suspected my fish trap code, but found that it does not spam commands at all. But now I found the culprit: I recently increased sn-fishing-boat-whaling-percentage from the default of 0 to 20 and sn-whaling-max-distance to 40, in order to catch any whales and possibly oysters(?) available. This leads to a vast majority of the fishing ships searching far and wide for whales, apparently. A test script is included on Discord. It's possible that fishing ships sent to explore for whales aren't included as fishing ships assigned to whales, meaning that the AI engine will keep on assigning new fishing ships to explore for whales in a fruitless attempt to reach the desired number of whaling ships set by sn-fishing-boat-whaling-percentage.

### 8.27 Bugs with sn-enable-research-queue

- 日期：Apr 25, 2026
- 命令：`@can-research`, `@can-research-with-escrow`, `@up-can-research`, `@up-research`
- SN：`@sn-enable-research-queue`, `@sn-enable-training-queue`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1497592259804397680">Link</a>

It looks like sn-enable-research-queue only works if you have sn-enable-training-queue set > 0 and have units queued. You cannot queue techs if a unit isn't training at that building.

### 8.28 object-data-attacker-count and object-data-under-attack doesn't work for building foundations

- 日期：Apr 13, 2026
- 命令：`@town-under-attack`, `@up-get-object-data`, `@up-object-data`, `@up-remove-objects`
- 参数：`@ObjectData`
- 链接：<a href="https://discord.com/channels/485565215161843714/485566694912163861/1493372417827934278">Link</a>

Apparently, object-data-attacker-count and object-data-under-attack NEVER return a positive value for foundations. I'm hitting it, illu just cant detect it. It also doesnt trigger (town-under-attack), only does if I hit something thats finished.

### 8.29 sn-dock-training-filter considers ally ships in the recently sighted targets check when it should only consider enemy ships

- 日期：Apr 1, 2026
- 命令：`@can-train`, `@can-train-with-escrow`, `@train`, `@up-can-train`, `@up-train`, `@up-train-site-ready`
- SN：`@sn-dock-training-filter`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1488849922110394522">Link</a>

With sn-dock-training-filter set to 2, the AI will train warships in a lake that only contains ally ships.

### 8.30 Issues with fire-lancer-line being > 0 with no fire lancers on the map

- 日期：Mar 19, 2026
- 命令：`@unit-type-count`, `@unit-type-count-total`, `@up-object-type-count`, `@up-object-type-count-total`, `@up-find-local`, `@up-find-status-local`, `@up-find-remote`, `@up-find-status-remote`
- 链接：<a href="https://discord.com/channels/485565215161843714/485566694912163861/1484227547251343503">Link</a>

There are situations where fire-lancer-line can be > 0 when counting enemy Khitan objects even though no fire lancers have been seen. Also happens when counting fire-lancer and elite-fire-lancer.

### 8.31 up-object-type-count-total double counts pending villagers

- 日期：Mar 3, 2026
- 命令：`@up-object-type-count-total`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1478563579639890004">Link</a>

up-object-type-count-total double counts pending villagers. With a 3 villager start and one villager pending at the start, (up-object-type-count-total c: villager == 5) is true, and with 2 villagers pending (up-object-type-count-total c: villager == 7) is true.

### 8.32 rocket-cart-line is defined incorrectly

- 日期：Feb 23, 2026
- 命令：`@players-unit-type-count`, `@unit-type-count`, `@unit-type-count-total`, `@up-object-type-count`, `@up-object-type-count-total`, `@up-find-local`, `@up-find-status-local`, `@up-find-remote`, `@up-find-status-remote`
- 参数：`@LineId`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1475357646243495946">Link1</a>, <a href="https://discordapp.com/channels/485565215161843714/925409493792202813/1385493391751516301">Link2</a>

In unitlines.json the rocket-cart-line is defined as 1904 and 1906, but rocket cart and heavy rocket cart are 1904 and 1907. This causes rocket-cart-line to not include heavy rocket carts. This also causes rocket cart projectiles to be counted with rocket-cart-line since the rocket cart projectile is 1906.

### 8.33 UP-ALLY-IN-GAME is defined in Nomad 1v1 games

- 日期：Feb 13, 2026
- 命令：`@#load-if-defined`, `@#load-if-not-defined`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1471976323772583946">Link</a>

#load-if-defined UP-ALLY-IN-GAME is true for Nomad 1v1 games because of treaty starts.

### 8.34 up-players-in-game doesn't work with enemy-treaty

- 日期：Feb 8, 2026
- 命令：`@up-players-in-game`, `@up-get-fact`
- 参数：`@FactId`, `@PlayerStance`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1470068387148464182">Link</a>

up-players-in-game says there are -1 enemy-treaty players in the game during treaty mode starts. Instead every enemy-treaty stance player is counted as an enemy.

### 8.35 Boar lurers can be retasked to explore by sn-cap-civilian-explorers

- 日期：Feb 8, 2026
- SN：`@sn-cap-civilian-explorers`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1469960619213197549">Link</a>

Boar lurers can be retasked to explore if sn-cap-civilian-explorers is > 0.

### 8.36 AI attacks know where enemy town locations are on nomad starts

- 日期：Feb 3, 2026
- 命令：`@up-get-point`, `@up-send-scout`
- 参数：`@PositionType`, `@ScoutMethod`
- 链接：<a href="https://discord.com/channels/485565215161843714/485591138556706817/1468219382290452622">Link</a>

AI attacks automatically seem to know where the enemy TC is on nomad starts, and when they send soldiers to attack they will always march toward that location, even if it's in the fog of war. A side effect is that position-enemy also knows enemy town locations that are in the fog of war. This might be linked to the bug where enemy TCs built during treaty mode being counted as coustillier, and the enemy TCs are added to the AIs explored objects list.

### 8.37 housing-headroom is uncapped by the pop cap, causing population-headroom to go negative

- 日期：Jan 6, 2026
- 命令：`@housing-headroom`, `@population-headroom`, `@up-get-fact`
- 参数：`@FactId`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1458065584083177677">Link</a>

housing-headroom is uncapped by the pop cap, and it will include headroom above the pop cap that it can't use. population-headroom is calculated by population-capacity - housing-capacity, so when housing capacity goes above the pop cap, population-headroom will go negative. There is some debate whether this should be changed or not. Follow the link to see the discussion.

### 8.38 building-type-count and building-type-count-total count cancelled building foundations

- 日期：Dec 30, 2025
- 命令：`@building-type-count`, `@building-type-count-total`, `@unit-type-count`, `@unit-type-count-total`, `@up-object-type-count`, `@up-object-type-count-total`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1455571914721591411">Link</a>

building-type-count and building-type-count-total count cancelled building foundations while the foundation is in its dying animation (status-down). Once the building's collapse animation ends, these commands no longer count the cancelled building. This is a legacy bug, and it also occurs in UP. The Discord link includes a test AI script to replicate it. Likewise, unit-type-count and unit-type-count-total count dying (status-down) units, when they should be excluded.

### 8.39 Italians my-unique-research and my-second-unique-research are incorrect

- 日期：Dec 10, 2025
- 命令：`@can-research`, `@can-research-with-escrow`, `@up-can-research`, `@up-research`
- 参数：`@TechId`
- 链接：<a href="https://discord.com/channels/485565215161843714/485566694912163861/1448453527297855630">Link</a>

Current Pavise is still my-second-unique-research and Silk Road is still my-unique-research. my-second-unique-research should be Silk Road, and my-unique-research should be Pirotechnia.

### 8.40 up-find-player and up-find-next-player don't work properly

- 日期：Feb 23, 2023
- 命令：`@up-find-player`, `@up-find-next-player`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1078215378855022643">Link1</a>, <a href="https://discord.com/channels/485565215161843714/925409493792202813/1444764691036504269">Link2</a>

up-find-player and up-find-next-player are a mess. This has been reported on various occasions. I am doing some (slightly unstructured) testing now. My preliminary findings: find-closest works, but returns -1 after the farthest player, and does not cycle back to the first. find-ordered does not work at all, just returns -1. find-attacker works, but I think it only returns the most recent attacker (potentially Gaia) or else -1? find-random may not be very useful, since it will (according to the docs) only hold out the most recently found player. Also, I suspect that player 0, i.e. Gaia, occasionally comes up with find-closest. My tests have been run with the recommended pattern of first finding a player with up-find-player and then using up-find-next-player with the same settings and the same I/O goal. There are many more possible tests to run. Also, find-closest finds or estimates the positions of unexplored enemies, but also seems to respond to explored buildings.

### 8.41 object-data-carry doesn't work for trade carts

- 日期：Nov 24, 2025
- 命令：`@up-get-object-data`, `@up-object-data`, `@up-remove-objects`, `@up-clean-search`
- 参数：`@ObjectData`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1442546497706135685">Link</a>

Trade carts report an object-data-carry of 0 at all times. object-data-carry works properly in UP.

### 8.42 Units can go idle when targeting buildings at their max range, sometimes causing bugs with interrupting their attack animation.

- 日期：Nov 5, 2025
- 命令：`@up-get-object-data`, `@up-object-data`, `@up-target-objects`, `@up-target-point`
- 参数：`@ObjectData`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1435748618991829073">Link</a>

Units can go idle when targeting buildings at their max range, sometimes causing bugs with interrupting their attack animation.

### 8.43 Trebuchets continually unpack and repack or go idle

- 日期：Nov 5, 2025
- 命令：`@attack-now`
- SN：`@sn-number-attack-groups`, `@sn-maximum-town-size`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1435743498451292221">Link</a>

Trebuchets permanently unpack and repack. Most of the time all trebs worked perfectly fine, then all of them on a single castle at once go idle for the rest of the game.

### 8.44 Mangonels go idle when units are inside their minimum range

- 日期：Oct 28, 2025
- 命令：`@up-get-object-data`, `@up-object-data`, `@up-target-objects`, `@up-target-point`
- 参数：`@ObjectData`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1432923135639814204">Link</a>

Mangonels just sperg out and freeze in a command spam whenever anything is within their minimum range.

### 8.45 fe-break-point does not allow the AI script that triggered the break point to continue playing.

- 日期：Aug 24, 2025
- 命令：`@fe-break-point`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1409094206647177239">Link</a>

"Continue" from a break point does not continue the script that triggered the break point, only the game. Other scripts seem to be unaffected.

### 8.46 up-guard-unit can crash the game

- 日期：Aug 8, 2025
- 命令：`@up-guard-unit`
- 参数：`@LineId`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1403468905481240626">Link</a>

up-guard-unit basically crashes DE at the moment. Highly recommend not using this command. Most of the crashes seem to come with rules that execute the command every pass. Rules with disable-self or a long timer seem to crash the game less. Update: it looks like unit lines might be the source of crashes with up-guard-unit.

### 8.47 object-data-to-precise measures from left corner of target point

- 日期：Jul 3, 2025
- 命令：`@up-object-data`, `@up-get-object-data`, `@up-remove-objects`, `@up-clean-search`
- 参数：`@ObjectData`
- 链接：<a href="https://discordapp.com/channels/485565215161843714/485566694912163861/1390355449290817729">Link</a>

So, my test seems to confirm that object-data-to-precise measures from the left corner of the precise target point. It does measure from the precise location of the target object though. UP correctly calculates from the precise point exactly, not its left corner. Until this bug is fixed, use up-get-object-data to store the target object's object-data-precise-x and object-data-precise-y, and then use up-get-point-distance to calculate the precise distance from the target point.

### 8.48 AIs can train more than one hero

- 日期：May 19, 2025
- 命令：`@can-train`, `@can-train-with-escrow`, `@train`, `@up-can-train`, `@up-train`
- 链接：<a href="https://discordapp.com/channels/485565215161843714/925409493792202813/1374171802473070622">Link</a>

AIs can train more than one hero for the Three Kingdoms DLC civs. Currently AI scripters must check unit counts to ensure the AI doesn't have a hero before training.

### 8.49 The EscrowGoalId parameter for up-can-build-line doesn't work properly

- 日期：Feb 28, 2025
- 命令：`@up-can-build-line`
- 参数：`@EscrowGoalId`
- 链接：<a href="https://discordapp.com/channels/485565215161843714/925409493792202813/1345041379260108820">Link</a>

up-build-line does not respect escrow, which is OK to me. But up-can-build-line does not work as documented either. In my limited testing, setting the EscrowGoalID parameter to 0 allows freely using escrowed resources, setting it to a goal that has with-escrow (0) denies the escrowed resources, setting it to a goal that has without-escrow (1) allows using the resources, setting it to a goal that has any other value denies the escrowed resources. Essentially, it currently only accepts the literal values of 0 (with-escrow) or 1 (without-escrow) instead of a Goal Id.

### 8.50 position-enemy counts walls when calculating the target player's closest building

- 日期：Feb 7, 2025
- 命令：`@up-get-point`, `@up-player-distance`, `@up-send-scout`
- 参数：`@PositionType`, `@ScoutMethod`
- 链接：<a href="https://discordapp.com/channels/485565215161843714/925409493792202813/1337413622246408286">Link</a>

position-enemy counts walls when calculating the target player's closest building, but walls should be excluded.

### 8.51 up-delete-objects command left gates at 1 HP

- 日期：Nov 9, 2024
- 命令：`@up-delete-objects`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1304770789559763018">Link</a>

weird bug here, red deleted all its walls but the gates remained at 1 hp.

### 8.52 live-boar dropsite distance bugged

- 日期：Nov 6, 2024
- 命令：`@dropsite-min-distance`, `@up-get-fact`
- 参数：`@FactId`, `@Resource`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1303903748988469321">Link</a>

(dropsite-min-distance live-boar ... ...) is still super inconsistent. Either this or boars (not sure about deer) seem to be bugged. The same boar is spotted at different locations/times. Pictures show first rule trigger. Looks like I might need to use precise distance instead of dropsite-min-distance here. I remember having issues with finding boars and deer with remote search like a year ago, from that time I use ID loops to find boars and deer

### 8.53 Sometimes AIs will stop building farms for no reason

- 日期：Nov 1, 2024
- 命令：`@build`, `@can-build`, `@can-build-with-escrow`, `@up-build`, `@up-can-build`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1301908835492958260">Link</a>

For some reason the farms will not continue to be built. Only after all farms are deleted, will farms start to be built again. In addition to what ER says, I think it starts to happen with farms being placed farther out.

### 8.54 Wolves not always found properly with up-find-remote

- 日期：Sep 8, 2024
- 命令：`@up-find-remote`, `@up-find-status-remote`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1282264202852962386">Link</a>

Doing a up-find-remote or up-find-status-remote search for predator-class with gaia as the focus player doesn't find wolves.

### 8.55 up-can-search crash

- 日期：Sep 1, 2024
- 命令：`@up-can-search`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1279797387136733257">Link</a>

up-can-search causes a crash, regardless of map type and regardless of using (up-can-search search-local) or (up-can-search search-remote)

### 8.56 object-data-player doesn't update for human-controlled units after an AI monk converts them

- 日期：May 23, 2024
- 命令：`@up-get-object-data`, `@up-object-data`, `@up-find-local`, `@up-find-remote`, `@up-find-status-local`, `@up-find-status-remote`, `@up-remove-objects`
- 参数：`@ObjectData`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1243318310398070864">Link</a>

I've been wondering why Bright Spark's military have been clumping in the home base during team games vs humans but I've never been able to recreate it with AI games. Turns out, if you are a human player and your unit gets converted - DUC remote searches still think the unit belongs to the human player. Play the same scenario with an AI and the DUC search picks up the unit switching side. In Bright Spark's example, every case the units were clumped up it was because it had converted an enemy human's unit and my DUC was getting the army to all action-default to that unit, even though it wasn't an enemy anymore.

### 8.57 sn-allow-gathering-sea-fish-with-villagers doesn't work when set to 1

- 日期：Mar 18, 2024
- SN：`@sn-allow-gathering-sea-fish-with-villagers`
- 链接：<a href="https://discord.com/channels/485565215161843714/485566694912163861/1219212583211503637">Link1</a>, <a href="https://discord.com/channels/485565215161843714/485566694912163861/1504516943305244752">Link2</a>, <a href="https://discord.com/channels/485565215161843714/925409493792202813/1504872622880591902">Link3</a>

Setting sn-allow-gathering-sea-fish-with-villagers to 1 doesn't allow villagers to gather sea fish. On Alpine Lakes, sea fish were 18 tiles away, and even though sn-maximum-food-drop-distance was 32 villagers go to chop wood instead after all other food sources are exhausted. If shore fish are added to the map, villagers start gathering the shore fish.

### 8.58 up-create-group doesn't work with goals as parameters

- 日期：Mar 2, 2024
- 命令：`@up-create-group`
- 链接：<a href="https://discord.com/channels/485565215161843714/485566694912163861/1213516805600186419">Link</a>

I can't get up-create-group to work with goals for index and count, it only seems to work if I pass 0 to both parameters.

### 8.59 Relative filepaths to xs files in an include command don't work for AI mods

- 日期：Feb 26, 2024
- 命令：`@include`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1211546829523656744">Link</a>

In the Mod, the xs files must be placed in the xs folder before it can be loaded in the Mod. You can't use statements like (include "..\ai\MyAIFolder\filename.xs") to load .xs files from a folder in a different location.

### 8.60 Load commands can prevent include commands to fail

- 日期：Feb 15, 2024
- 命令：`@include`, `@load`, `@load-random`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1207690744492720138">Link</a>

In my testing, if there are any "include" commands to load a .xs file that appear before any "load" commands to load a .per file, then these .xs files are not loaded. Any .xs files that you want to include must appear after all .per "load" commands.

### 8.61 Some Userpatch constants not properly defined

- 日期：Jan 26, 2024
- 参数：`@ActionId`, `@ExploredState`, `@ObjectList`, `@ObjectStatus`, `@SearchOrder`, `@ObjectData`, `@OrderId`
- 链接：<a href="https://discord.com/channels/485565215161843714/485566694912163861/1200456724323250206">Link</a>

Did some quick testing with removing the UserPatchConst.per file from my AI. Looks like the ExploredState, ObjectList, ObjectStatus, SearchOrder, and ObjectData constants aren't defined properly in DE. Also, actionid-relic and orderid-relic are missing but the rest of the actions and orders are defined.

### 8.62 Dividing negative numbers by positive numbers gives incorrect result

- 日期：Jan 2, 2024
- 命令：`@up-modify-escrow`, `@up-modify-goal`, `@up-modify-sn`
- 链接：[Reported by TheMaximalBeing privately]

It turns out that dividing negative numbers by positive numbers doesn't work. It tends to give one larger than expected.

### 8.63 up-get-player-fact unit counting bugs

- 日期：Jan 2, 2024
- 命令：`@players-unit-type-count`, `@up-get-player-fact`
- 参数：`@FactId`, `@LineId`, `@UnitId`
- 链接：[Reported by TheMaximalBeing privately]

Several bugs: (1) all ally unit counts are currently bugged since they count the entire unit line, rather than just the unit given to the command. (2) all enemy unit counts are currently bugged as they, including all the different upgrades, just count the base unit and not the specific given upgrade. The unit lines still work for enemies. (3) elite-huskarl-barracks/elite-stable-tarkan cannot be counted for ally & enemy players. Both give 0 and there is no unit-line as an alternative. (4) elite-gbeto cannot be counted for ally & enemy players. Only the non-elite gbeto is counted. (5) dismounted-konniks/elite-dismounted-konniks are not counted for enemy players and give -1. dismounted-konnik-line gives -2, presumably because it is counting both of these. (5) flemish-militia-male and flemish-militia-female are not counted for enemy players and give -1. Instead, for enemy players, they get included in flemish-militia-trained. I assume this is intended behavior. But something for people to be aware of.

### 8.64 wall-invisible-percentage and wall-completed-percentage only go up to 50%

- 日期：Nov 19, 2023
- 命令：`@wall-completed-percentage`, `@wall-invisible-percentage`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1175990960728059926">Link</a>

It appears wall-invisible-percentage/wall-completed-percentage are bugged in DE. For some reason when building walls at perimeter 2, wall-completed-percentage only went up to 50% when the full outer wall was complete.

### 8.65 (can-build town-center) doesn't check if the AI has enough stone

- 日期：Sep 9, 2023
- 命令：`@can-build`, `@can-build-with-escrow`, `@up-can-build`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1150040321963601930">Link</a>

Seems like can-build town-center returns true even if there is not enough stone for a town-center, while UP does check for stone. Only can-build town-center-foundation currently checks if there is enough stone.

### 8.66 can-build returns false on Nomad before the TC is built

- 日期：Jun 22, 2023
- 命令：`@can-build`, `@can-build-with-escrow`, `@up-can-build`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1121464519437328445">Link</a>

Another major DE bug: on land nomad, can-build returns false for all buildings except town-center until the tc is built. Immortal needs to check if other buildings can be built. Immortal uses other buildings as pathing checks. Also Immortal likes to place houses before the tc is built

### 8.67 The four resource modifier SNs don't allow negative values like UP

- 日期：Jun 5, 2023
- SN：`@sn-food-modifier-percentage`, `@sn-gold-modifier-percentage`, `@sn-stone-modifier-percentage`, `@sn-wood-modifier-percentage`
- 链接：<a href="https://discord.com/channels/485565215161843714/485566694912163861/1115250747865579520">Link</a>

The four resource modifier SNs (sn-food-modifier-percentage, etc) don't allow negative values like UP, just positive values. See Discord link for screenshot. The SNs need to be updated so that their hardcoded minimum is -100, not 0.

### 8.68 up-set-placement-data can't be used with target-player or focus-player

- 日期：Apr 30, 2023
- 命令：`@up-build`, `@up-set-placement-data`
- SN：`@sn-focus-player-number`, `@sn-target-player-number`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1102379431781224592">Link</a>

From what i see in up-set-placement-data for UP 1.5, it accepts target-player and focus-player. In DE it does not, it only accepts constants 101 - 111. Confirmed, code is present in UP 1.5 allowing target-player and focus-player to be used for up-set-placement-data while there is no such code present in DE (latest build 82587)

### 8.69 SN 511 isn't usable

- 日期：Apr 25, 2023
- 命令：`@strategic-number`, `@set-strategic-number`, `@up-compare-sn`, `@up-modify-sn`
- 链接：<a href="https://discord.com/channels/485565215161843714/485566694912163861/1100559877522329621">Link</a>

Only SNs 0-510 are usable in DE. 0-511 are usable in UP.

### 8.70 sn-boar-lure-destination doesn't send villagers to the correct location

- 日期：Mar 25, 2023
- SN：`@sn-boar-lure-destination`
- 链接：<a href="https://discord.com/channels/485565215161843714/485566694912163861/1089316493243723796">Link</a>

Ok, I finished my tests with sn-boar-lure-destination. "Broken" is when villager stops attacking/moving after initial shots. Many values end up leading to the middle of TC. Some places aren't possible to be reached. See the Discord link for screenshots.

### 8.71 up-get-player-fact building-count bug

- 日期：Mar 2, 2023
- 命令：`@up-get-player-fact`
- 参数：`@FactId`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1080832859457196062">Link</a>

up-get-player-fact for building-count does not work for enemy players on DE. It just returns -1. This command does however work when used as a normal fact: (players-building-count etc.). Update: up-get-player-fact for building-count only returns 0 now.

### 8.72 Path distance calculation issues

- 日期：Nov 22, 2022
- 命令：`@up-get-path-distance`, `@up-path-distance`
- 链接：<a href="https://discord.com/channels/485565215161843714/485566694912163861/1044618526050230392">Link1</a>, <a href="https://discord.com/channels/485565215161843714/485566694912163861/1449416353801961562">Link2</a>

There are cases where the path distance calculation is wrong (path distances on arena f.e. not always showing that objects inside the enemy's walled town were inaccessible). See discussion at Discord link. Update: it looks like path distances correctly know that closed diagonal gates cannot be pathed through, but there are still issues with horizontal and vertical gates being considered pathable even when they're closed.

### 8.73 idle-farm-count yields negative values for Rice Farms

- 日期：Oct 31, 2022
- 命令：`@idle-farm-count`, `@up-get-fact`
- 参数：`@FactId`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1036563141347246101">Link 1</a>, <a href="https://discord.com/channels/485565215161843714/925409493792202813/1109703443519635596">Link 2</a>

Report 1: I found a bug with work (idle-farm-count == xx). On the map water nomad - (idle-farm-count == xx) - not work. Only on the map water nomad - idle-farm-count starts to take negative values if one farm is occupied, then idle-farm will be == -1. If 2 farms is occupied - idle-farm will be == -2. Because of this, my AI builds an infinite number of farms on this map. Report 2: And bug with idle-farms-count on the water nomad map... More precisely, on any map where there is water and farms can be built on it. Leif Edit: I believe this bug is caused by idle-farm-count not counting rice farms. idle-farm-count will equal the number of rice farmers * -1.

### 8.74 Resetting Offense Priorities can cause a crash

- 日期：Oct 11, 2022
- 命令：`@up-set-offense-priority`, `@up-reset-target-priorities`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1029456095325990944">Link</a>

A reliable way to crash your DE-game is to reset offense-priorities like this each rule-pass: (up-reset-target-priorities priority-offense 1). If you up-set-offense-priority for a building (not for a class) and up-reset-target-priorities priority-offense 1 after that, then the game crashes. If you up-reset-target-priorities priority-offense 1 before up-set-offense-priority, than the game doesn't crash. If you up-set-offense-priority for a class and up-reset-target-priorities priority-offense 1 after that, than the game doesn't crash. This crash occurred in an AI using attack-now and later in the game TSA. If I use an empty ai-file with the code above it crashes my game. Leif edit: Confirmed that if you use up-set-offense-priority to set the priority of any building or unit ID at any time, then using (up-reset-target-priorities priority-offense 1) will cause a crash. The only ways to prevent a crash with up-set-offense-priority are to either only modify class priorities with up-set-offense-priority or never use up-reset-target-priorities.

### 8.75 position-flank is always very close to the enemy's starting location

- 日期：Oct 2, 2022
- 命令：`@up-get-point`, `@up-send-scout`
- 参数：`@PositionType`, `@ScoutMethod`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1026117370168750150">Link</a>

Position flank works differently on DE. It allways gives the correct y-coordinate and then it gives an x coordinate 0-12 numbers higher than the correct one. This basicly means position-flank will always give the position of the enemy flank tc within 6 tiles on DE if you just subtract 6 from the x coordinate. This allows the AI to easily find the enemy even without scouting. On UP it seems to just use the mirrored flank position to predict where the enemy should be.

### 8.76 position-mirror gives position-opposite effect instead of position-mirror

- 日期：Oct 2, 2022
- 命令：`@up-get-point`, `@up-send-scout`
- 参数：`@PositionType`, `@ScoutMethod`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1026117370168750150">Link1</a>, <a href="https://discord.com/channels/485565215161843714/925409493792202813/1405774563379511297">Link2</a>

Position-mirror does not work on DE. Instead it just gives the same value as position-opposite. scout-mirror with up-send-scout is also affected.

### 8.77 Villager Gathering/Exploring/Building SNs bugged in DE

- 日期：Sep 18, 2022
- SN：`@sn-cap-civilian-gatherers`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1021167578472783884">Link</a>

There seems to be an issue with the villager exploring or gathering SNs in DE. It's possible for villagers to be sent to gather resources even when sn-cap-civilian-gatherers is set to 0. The code in the Discord link tells 2 villagers to explore and 1 villager to build houses. But when the villager finishes building the two houses it goes and gathers sheep despite the fact that gatherers are capped at 0. In UP, the builder correctly starts exploring after finishing the houses. See Discord link for test script.

### 8.78 dropsite-min-distance deer-hunting returning 255 instead of -1

- 日期：Sep 4, 2022
- 命令：`@dropsite-min-distance`
- 参数：`@Resource`
- 链接：<a href="https://discord.com/channels/485565215161843714/485566694912163861/1016047774673928192">Link</a>

dropsite-min-distance deer-hunting starts out 255 in first loop and then goes to -1 and stays at -1 until deer have been found. Same with other hunting drop distances. In UP, these hunting drop distances are 255 when they haven't been found.

### 8.79 load-random with '+' load feature doesnt work

- 日期：Aug 6, 2022
- 命令：`@load-random`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/1005481892298104832">Link</a>

The UP load-random command doesn't seem to work on DE. Maybe the "+" loading feature isn't recognized or load-random doesn't work with a defconst yet. Meleon has this code. The #load-if works fine, but I confirmed that the Meleon\core.per is not loaded for whatever reason. See Discord link for test script.

### 8.80 Switching point of view with Ctrl-Shift-F1-8 doesn't update typing to other players perspective

- 日期：Jun 26, 2022
- 命令：`@chat-local`, `@chat-local-to-self`, `@chat-local-using-id`, `@chat-local-using-range`, `@up-chat-data-to-self`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/990673033452736532">Link 1</a>, <a href="https://discord.com/channels/485565215161843714/925409493792202813/1018158049640329306">Link 2</a>

Report 1: In UP, if you switch perspective to p2 with Ctrl+Shift+F2, up-chat-data-to-self correctly only shows messages sent by the p2 AI script. However, in DE any up-chat-data-to-self messages sent by the p1 AI are always displayed, even if you switch perspective to p2 with Ctrl+Shift+F2. chat-local-to-self works properly though. Only the non-local messages seem to be bugged to always show player 1's perspective. Report 2: Switching point of view with Ctrl-Shift-F1-8 doesnt update typing to other players perspective. It stays at Player 1. I can't type as another AI player to Player 1 for example.

### 8.81 Villagers hunting far unexplored boar

- 日期：Mar 30, 2022
- SN：`@sn-maximum-hunt-drop-distance`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/958750646096515213">Link</a>

Here is that time again where my villagers start hunting a boar well beyond their revealed line of sight and in black fog of war, at the enemy's base. See Discord link for recorded games.

### 8.82 up-build not as reliable in DE? - negative sn-placement-fail-delta causing incorrect placement and build delay

- 日期：Jan 22, 2022
- 命令：`@up-build`
- SN：`@sn-placement-fail-delta`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/934512291456618527">Link 1</a>, <a href="https://discord.com/channels/485565215161843714/925409493792202813/1014628241354526791">Link 2</a>

Report 1: place-control works differently on DE than UP, sometimes buildings desired built in front of the town are placed in the back. Report 2: I have the suspicion, that up-build is also bugged in regard of negative sn-placement-fail-delta. 1st screenshot is a test-arabia-scenario with UP where all is as expected. 2nd screenshot is the same scenario with DE, where it build the blacksmith next to LC, but not the market, which I eventually build myself. After reaching castle age it build the castle somewhat to the front (as intended) and the other buildings near TC (as intended), but the barracks, which has also a negative sn-placement-fail-delta, got build 10 sec after reaching castle way out to the front, despite it should be build to the back in my understanding! See Discord links for screenshots. Leif update: the issue seems to be with sn-placement-fail-delta. Positive values seem to have no effect, while negative values seem to prevent placement altogether.

### 8.83 sn-ignore-tower-elevation settings are reversed from UP

- 日期：Jan 22, 2022
- SN：`@sn-ignore-tower-elevation`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/934458658736189451">Link</a>

(set-strategic-number sn-ignore-tower-elevation 0) It seems AI still not prefer high-elevation. Leif update: The SN settings are reversed. Setting the SN to 1 prefers elevation, not 0.

### 8.84 up-get-group-size and up-group-size ignore garrisoned units

- 日期：Jan 14, 2022
- 命令：`@up-get-group-size`, `@up-group-size`
- 链接：<a href="https://discord.com/channels/485565215161843714/925409493792202813/931625553700745318">Link</a>

up-get-group-size and up-group-size exclude garrisoned and dead units when calculating the group size in DE, while UP includes them. If this difference is intended, then this isn't a bug.

---

CSV：`_objects.csv`（809 行）
CSV：`_objects_chr.csv`（238 行）
CSV：`_objects_ror.csv`（184 行）
CSV：`_techs.csv`（326 行）
CSV：`_techs_chr.csv`（161 行）
CSV：`_techs_ror.csv`（79 行）
CSV：`_loadifs.csv`（430 行）

---

## 附录：复跑

```bash
python -X utf8 _probe/_tmp/gen_vol04.py
```

数据源重建：

```bash
# 1. 拉 commands.js
curl -o _probe/_tmp/commands.js https://airef.github.io/js/commands.js
# 2. node vm 执行并导出（dump_airef3.js）
D:/Software/nodejs/node.exe _probe/_tmp/dump_airef3.js
```
