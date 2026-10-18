import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
lines = [
"DOCS AUDIT - D:\\Software\\AI\\帝国项目 - 2026-10-18 (HEAD 2678d05)",
"VERDICT: STALE   research numbers reproduce; narrative layers were never updated after 2026-10-17.",
"DEAD REFS: 6 cited _probe/*.py absent (_rng3/_rng5/cost_fallback_impact/tech_describe_audit{,2}/probe_donor_bias), all in 数据模组能力目录v1.md.",
"DEAD REFS: _shots/ absent (sprites SKILL:279); HUD_COMPARISON.png + HUD_COMPOSITE.png absent (ui-textures SKILL:87); out_suites_bundle2.txt absent (项目状态:214).",
"OLD ROOT: aoe2mod/dat/parser.py:7 still carries D:\\Software\\DeepSeek Harness\\工作区2 - the only shipped .py hit; .dsh/skills/** is clean.",
"C1 SPRITES: sprites SKILL:335 'No in-game verification exists' vs :116/:121/:179 v10/v11/v13 proofs; :338 'Zero of 9 mods ship any .sld' vs mod 551412 = 466 .sld.",
"C2 GRAPHICS CATALOGUE: :6/:22/:386 'never started the game, never wrote a mod' vs :240/:241/:273 citing v10/v11/v12/v13.",
"C3 PER-CIV AVAILABILITY: dat SKILL:46 '.dat CANNOT express it' vs :467 'CAN express it'; 项目状态:126 says proven in game.",
"C4 PANEL (worst): 项目状态:143 / dat SKILL:298-306 '10 buildings appear NOWHERE, 62/62' - refuted by _probe/test_panel_shape.py (PASSES): 0 of 10 nowhere, 67/68 have block 118, 434 block-only pairs.",
"C5 COUNTS: intents 8 (doc) vs 10; strategies 3 (doc) vs 4; api.py:1978-97 docstring itself says 3 but returns dat,js,sld,paint.",
"C6 TREE WRITE: 数据模组:2988 quotes api.py 'NO in-game test has yet shown EITHER file' - string does not exist in aoe2mod/ (0 grep hits).",
"C7 v12: 项目状态:147 says v12 实机通过, :152 says 'v12 已装待验' five lines later.",
"C8 SIZE: 项目状态:4 says 422 KB, :163 says 313,909 B, measured 451,749 B / 4,143 lines.",
"C9 ui-textures:42 '30 types' vs :82 '31' - measured 31.",
"MATCH: .dat 93,268,152 B / EOF 0; 63 civs; techs 1510; effects 1500; graphics 21,001 slots / 20,883 non-empty; sounds 769; unit headers 1701.",
"MATCH: 15,486 .sld; 15,559 total (38 smp + 35 slp); 15,484 valid / 4,850,222 frames; x1 7,743 = x2 7,743, 0 orphans; 2 zero-byte stubs.",
"MATCH: tree 287 unit / 238 tech nodes; 3,686 rows; panel-vs-dat 4,239 / 20 / 64; 4 distinct train maps (56/3/3/1).",
"MATCH: 133 widgetui JSONs / 116 with widgets / 6,504 widgets / Surround 1.09%; textures 7,840 = 5,977/1,655/206; wpfg 3,039 = 233/2,708.",
"MATCH: icons.json 14 segments / 2,138 non-null; materials overlap 199; 3 .box fonts (combined.box 341,236 B); palettes 67 pal + 5 palx.",
"MISMATCH: 8,656 files / 321 multi-label -> measured 8,657 / 322 (off by one).",
"MISMATCH: mods 9 (doc) vs 11 measured; Title!=folder 8/8 vs 10/11 differing; mods writing DAT root 5-of-5 vs 6-of-6.",
"MISMATCH: run_suites 63 or 64 (doc) vs 73; aoe2mod .py 28 vs 38; _probe .py 582 vs 828 top-level / 1,214 recursive.",
"MISMATCH: old-path blast radius 390 files/455 lines vs 353-354 files/403-410 lines; commits 2 or 3 vs 4; sync_engine asserts 4 vs 8.",
"MISMATCH: dat SKILL:38 tech_fields 2 vs 3 (omits effect); dat SKILL:448 '5 of 5' now 6.",
"UNCHECKED: run_long / sync_engine / in-game; icons.json 86.1% resolution rules; sld grid-join 7,602/7,618. Report: _probe/team/docs-auditor/REPORT.md",
]
for l in lines: print(l)
sys.stderr.write("LINES=%d\n" % len(lines))
