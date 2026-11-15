# -*- coding: utf-8 -*-
"""Run the fast product suites and print a one-line verdict for each."""
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PY = sys.executable

# A FAILURE REPORT, not the word.  The first version was
# `\bFAIL(?:ED|URE)?\b`, and on 2026-10-25 it called two green suites red:
# `test_nail_hygiene.py` prints `ok   a FAIL at any column is recognised` (it is
# checking the detector) and `test_gate_order.py` prints `37 have a failure
# gate`.  Both exited 0 with their own PASS line and were still counted as
# failures -- the runner's own worst shape, a red that is not about the code.
#
# The shapes the tree actually prints (see `_probe/test_nail_hygiene.py:73-75`
# for the first three):
#       `  FAIL a :: b`   `FAIL a :: b`   `a :: FAIL`
#       `FAILURES: 1 -> [...]`              (_probe/test_tech_effect.py)
#       `NAIL HYGIENE: 2 CHECK(S) FAILED -> [...]`
# An identifier like IDS_FAILED_TO_OPEN_FILE is not a report, and neither is a
# sentence that mentions the word.
_FAIL_RE = re.compile(
    # A passing check can SAY anything -- including quoting a failure shape it just
    # proved the rule catches (`_probe/test_fail_shapes.py` does exactly that, and
    # on 2026-10-26 three of its `ok` lines were read as failures by a 143-suite
    # run).  So the `ok` exclusion is applied once, to the whole pattern, instead
    # of being re-stated on the arms that happened to need it first.
    #
    # The anchor is a zero-width lookahead so the arms below may match anywhere in
    # the line: `a :: FAIL` and `[FAIL] name :: detail` are reports whose marker is
    # not at column 0.
    r"(?m)^(?!\s*ok\b)(?=[^\n]*(?:"
    # `FAILED: both halves stay in step`, and the bare `FAILED:` that
    # `print("FAILED:", name)` hands to the regex as a literal -- the colon ends
    # the string, so there is no whitespace after it to match.  `FAILED:WORD`
    # (no space) is still an identifier and stays quiet.  2026-11-09.
    r"^\s*FAILED:(?:\s|$)"
    r"|^\s*FAILED\s+\S"                     # `FAILED %d check(s)` / `FAILED 3 CHECKS:`
    r"|\bFAILURES:\s*(?:\d|%[sdr])"          # `FAILURES: 1 -> [...]` / `FAILURES: %s`
    r"|^\s*FAIL(?:\s|:)(?!\s*[A-Z][A-Z0-9 _()/.-]{2,}:)"  # report, not a verdict
    r"|\bFAIL\s+[^\s]+\s*::"               # `FAIL name :: detail`
    r"|\bFAIL(?:ED|URE|URES)?\s*$"           # report ends the line
    r"|\bCHECK\(S\)\s+FAILED\b"            # `N CHECK(S) FAILED -> [...]`
    # `MOD ROUTES: FAILURES ABOVE` -- the sign-off five suites print when they
    # failed (`test_mod_routes`, `test_rebuild`, `test_pages_shipped`,
    # `test_e2e_shipped`, `ship_and_verify`).  It carries an ALL-CAPS label with
    # no digits, so the "a sign-off is a label" convention read it as quiet while
    # it was in fact the only line saying the run went red.  `... ABOVE` is never
    # a pass; catch it by its second word, not by the label rule.  2026-11-01.
    r"|\bFAIL(?:ED|URE|URES|S)?\s+(?:ABOVE|BELOW)\b"
    r"|\[\s*FAIL(?:ED|URE|URES)?\s*\]"      # `[FAIL] name :: detail`
    r"))"
)

SUITES = [
    r"aoe2mod\tests\test_compiler.py",
    r"aoe2mod\tests\test_emit_mod.py",
    r"aoe2mod\tests\test_api.py",
    r"aoe2mod\tests\test_civtechtrees.py",
    r"aoe2mod\tests\test_civtechtrees_writer.py",
    r"_probe\test_revoke_chain_closed.py",
    r"aoe2mod\tests\test_buildpanel.py",
    r"_probe\test_panel_edit.py",
    r"_probe\test_panel_wire.py",
    r"_probe\test_smoke_subject.py",
    r"_probe\test_smoke5_design.py",
    r"_probe\test_zero_mod_experiment.py",
    r"_probe\test_panel_is_not_build_menu.py",
    r"_probe\test_panel_vs_dat_train.py",
    r"_probe\test_screen_vocabulary.py",
    r"_probe\test_button_groups.py",
    r"_probe\test_decisive_subjects.py",
    r"_probe\test_trigtech_space.py",
    r"_probe\test_protocol_subjects.py",
    r"_probe\test_panel_tree_agreement.py",
    r"_probe\test_panel_shape.py",
    r"_probe\test_time_gate_and_tooltip.py",
    r"_probe\test_dat_carrier.py",
    r"_probe\test_mod_name_resolution.py",
    r"_probe\test_subject_instantiable.py",
    # test_mod_load_timing.py -- retired 2026-10-25 (Recycle Bin).  It recorded
    # that every in-game availability test up to 2026-10-19 failed for TIMING
    # reasons; v17 answered it, so the file is a closed question's minutes.
    r"_probe\test_smoke6_result.py",
    r"_probe\test_test_validity.py",
    r"_probe\test_dat_grant_route.py",
    r"_probe\test_dat_edit_routes.py",
    r"_probe\test_smoke8_control_b.py",
    r"_probe\test_enabling_vs_effect.py",
    r"_probe\test_v2_semantic_diff.py",
    r"_probe\test_v4_reproduces_incas.py",
    r"_probe\probe_button_slot_collision.py",
    r"_probe\probe_slot_grouping.py",
    r"_probe\probe_free_slot_rule.py",
    r"_probe\test_info_json_shape.py",
    r"_probe\test_button_slots.py",
    r"_probe\test_datgrant.py",
    r"_probe\test_dat_half_count.py",
    r"_probe\probe_enabling_scope.py",
    r"_probe\probe_bundle_dat_half.py",
    r"_probe\test_bundle_dat_half_e2e.py",
    r"_probe\test_revoke_is_not_enough.py",
    r"aoe2mod\tests\test_product_v7_recipe.py",
    r"_probe\testmod_name.py",
    r"_probe\test_title_byte_limit.py",
    r"aoe2mod\tests\test_availability_e2e.py",
    r"aoe2mod\tests\test_availability_intent.py",
    r"_probe\test_tech_availability_e2e.py",
    # The plan's promise about the `.dat` half is checked against BYTES here.
    # It stayed wrong for a whole round -- `mod_contains_dat: false` in the
    # schema while every availability build shipped a 11.9 MB `.dat` -- because
    # nothing in the fast set ever opened the emitted file.
    r"_probe\test_availability_dat_half.py",
    # Black-box grant through the PUBLIC API (`tk.plan` / `tk.build`), i.e. the
    # path a user takes, including the `datgrant` recipe -- the product test
    # `aoe2mod/tests/test_availability_e2e.py` exercises the tree/emitter
    # functions directly and so would keep passing if the API wiring broke.
    r"_probe\test_availability_intent_e2e.py",
    r"_probe\test_donor_rule.py",
    r"_probe\test_mechanism_gate.py",
    r"_probe\test_type3_scope.py",
    r"_probe\test_tech_side_families.py",
    r"_probe\test_schema_vocabulary.py",
    # Sits next to the vocabulary audit on purpose: both answer "is the schema
    # telling the truth?", one about the shipped tables and one about the
    # plugin folders layered on top.  A plugin that silently failed to merge
    # would look exactly like a plugin that did nothing wrong.
    r"_probe\test_schema_plugins.py",
    r"_probe\probe_build_panel_gate.py",
    r"_probe\test_dat_layer_override.py",
    r"_probe\test_enabling_research.py",
    r"_probe\test_civ_unit_gate.py",
    r"_probe\test_overlay_depth.py",
    r"_probe\test_tree_form.py",
    # test_dat_json_override.py -- retired 2026-10-25 (Recycle Bin).  It asked
    # whether any mod ever demonstrated a .dat-layer JSON override; v45
    # (2026-10-22) answered it with two canaries in one match.
    r"_probe\test_linkedtechs_semantics.py",
    r"_probe\test_json_is_engine_data.py",
    r"_probe\probe_panel_provenance.py",
    r"_probe\probe_panel_coverage.py",
    r"_probe\probe_panel_era.py",
    r"_probe\probe_install_safety.py",
    r"_probe\probe_shipped_disagreement.py",
    r"_probe\test_families.py",
    r"_probe\test_declared_resources.py",
    r"_probe\test_unit_sprite_chain.py",
    r"_probe\test_sprite_chain.py",
    r"_probe\test_sld_encode.py",
    r"_probe\test_reskin.py",
    r"_probe\test_repaint.py",
    r"_probe\test_retarget.py",
    # The ten below sat in `_probe/` registered with NOBODY -- not in this list,
    # not in run_long.py -- so nothing ever ran them.  Four of them had rotted
    # silently (a renamed API key, a cosmetic field the parser started surfacing,
    # two literals counting the user's own mod list, and a `delta: 0` contract
    # the product deliberately changed).  A test no runner calls is not a test.
    r"_probe\test_age_variants.py",
    r"_probe\test_dat_availability_layers.py",
    r"_probe\test_effect_walk.py",
    r"_probe\test_tech_intent.py",
    r"_probe\test_tech_cost.py",
    r"_probe\test_tech_effect.py",
    r"_probe\test_install.py",
    r"_probe\test_install_e2e.py",
    # The UI shell.  These two are product assertions in the strictest sense:
    # the sentence parser is the only thing standing between a Chinese sentence
    # and a wrong edit, and the server test is the only thing that exercises the
    # HTTP layer at all (route names, JSON body shape, status codes).
    r"_probe\test_ui_nl.py",
    r"_probe\test_ui_server.py",
    # Two invariants that were TRUE-BY-ACCIDENT until something measured them.
    # The plan/build pair: every intent has two independent implementations, and
    # a preview that promises what the build refuses sends the player one click
    # too far (measured on `tech.research_time delta 0`).  The prose pair: the
    # screen prints the product's own sentences, so wording produced in English
    # is wording a Chinese player cannot read (measured at 8 of 12 strings).
    r"_probe\test_plan_build_agreement.py",
    r"_probe\test_prose_language.py",
    # The material layer (D direction).  `test_icons.py` pins the two icon tables
    # to different pictures -- the wrong table shows a player the picture of
    # something else, and nothing else in the suite would notice.  The prose pair
    # pins what text this build actually ships: technologies have descriptions,
    # units have NONE, and an honest gap is the first thing to get "filled in"
    # with an invention later.
    r"_probe\test_icons.py",
    r"_probe\test_prose_supply.py",
    # The menu layer.  The player asked whether reversing the game could turn it
    # into an editor; the hard part of the answer is a measurement, not an
    # opinion: the exe is native with no CLR header and no managed-runtime
    # strings, so nothing can make it run our code -- while resources/_common/
    # wpfg/ IS a mod-visible root whose 3.3 MB of markup lives on disk.  Suite
    # C pins the third leg: the widget classes are a closed, compiled-in
    # inventory.  Without this, "we could add any screen you want" sounds cheap
    # and is wrong, and "the menus are untouchable" is wrong in the other
    # direction.
    r"_probe\test_ui_layer_wiring.py",
    # A second icon source that LOOKS like a drop-in replacement.  95 PNGs under
    # wpfg/resources/uniticons at 256 px, named NNN_50730, in a root the suite
    # above proves mod-overridable.  Wiring it per icon id would be a guess: it
    # covers 95 of the 1,000 Units icon ids, and the one place the install says
    # what they are for names two of them after a civilization (`armenians_...`
    # -> 041, `georgians_...` -> 035), which is exactly the kind of near-miss
    # that ships a wrong picture.  This pins the naming rule and the coverage
    # gap so nobody "improves" the grid into using it without measuring.
    r"_probe\test_uniticons_hires.py",
    # The update guard.  Every mod this tool builds ships a whole 12 MB .dat, so
    # a game patch is silently overwritten by the installed copy -- and nothing
    # says so.  The guard's five statuses each have to be reachable, and two of
    # them (a re-compressed but identical .dat, an unknown mod) exist ONLY to
    # keep it from crying wolf: a false alarm costs the user a pointless rebuild,
    # and after the second one they stop reading it.
    r"_probe\test_update_guard.py",
    # Why the game refuses to open after the .dat is copied into the install
    # directory.  The player hit that dialog and asked; the answer is a compiled
    # set of file checksums, and it has a product consequence that is easy to get
    # backwards: the .dat in the install directory IS checked, the availability
    # panel JSON is NOT -- so a loose panel file is legitimate where a replaced
    # .dat is not, which is what every working experiment here already relies on.
    # It also names the reason three earlier searches failed: the dialog's line
    # is IDS_WARN_USER_FILE_CRC_BREAK, a NAMED key, and every loader in this repo
    # reads only the numeric half of that table.
    r"_probe\test_file_crc_table.py",
    # The other half of the install story.  The user chose (2026-10-20) to warn
    # and still install while the game is open, because the engine rewrites
    # mod-status.json at exit and can undo the entry while leaving the files.
    # The load-bearing assertion is the third answer: an unreadable process table
    # must NOT read as "it is closed", or the guard becomes a false all-clear.
    # The suite also spends a real install on a throwaway account, because the
    # answer has to reach the manifest the screen reads, not just live in a
    # function nobody calls.
    r"_probe\test_install_running.py",
    # A toggle must not INVENT the mod it is asked to toggle.  Found by accident
    # (2026-10-20) when a probe POSTed /api/mod with a name that cannot exist and
    # set_mod_enabled answered ok after inserting a phantom entry at Priority 1
    # of the player's real list.  resolve_mod_name returns "bare" for a name that
    # matches nothing, and its docstring promised a caller error that this caller
    # did not have.  The check that matters is the one the fix must NOT break: a
    # folder dropped into mods/local by hand is registered by the game itself, so
    # it is absent from mod-status.json and must still toggle.
    r"_probe\test_mod_toggle_unknown.py",
    # The one hole neither the page harness nor the server suite can see.  The
    # harness stubs `fetch`, so it proves the page SENDS a body; the server suite
    # calls the App methods, so it proves the method works.  A renamed key -- the
    # page posting `mod_dir`, the route reading `folder` -- is green in both and a
    # KeyError on the first click.  `/api/install`, `/api/mod` and `/api/uninstall`
    # cannot be exercised over HTTP without writing the player's real mod list,
    # which is exactly why the contract has to be read out of the sources instead.
    r"_probe\test_page_route_contract.py",
    # The read half of tech.effect, and the fifth time an internal key leaked into
    # a sentence: three of a row's four labels used to fall back to English built
    # by string formatting ("Class 251", "Resource 66", "unit 2154") across 4,308
    # visible rows.  The fallbacks are now the shipped class word plus the record
    # number, because 102 units -- all engine projectiles -- have no name string at
    # all, and the user chose that over translating "Projectile" (2026-10-20).
    # The check that cannot be written as a count is distinguishability: the same
    # unnamed unit must always read the same, and two different ones never must.
    r"_probe\test_effect_labels.py",
    # The read half of "change what a technology does": a technology stores only
    # a pointer, so every number a tech actually moves lives in another part of
    # the file as a command list.  8,005 reachable commands; before this the page
    # could not show one of them.  Asserts the offset printed IS the number
    # written (decoded through the same code the write uses) and that a write
    # records a POSITION, not a byte offset, so a rebuild survives a re-read.
    r"_probe\test_effect_list.py",
    # 图形 (20,883 records) and 音效 (930) -- the two biggest tables in AGE3 that
    # this build could not open at all, which is the concrete meaning of
    # 「依旧无法替代age3」.  The load-bearing checks are that the picker counts the
    # rows it pages (3,520 graphics and 491 sounds have no name and are not
    # listed), that a graphic record's `SpeedMultiplier` is reached through
    # `/api/table-field-set` and NOT through `/api/field-set` (unit 100 and
    # graphic 100 are different records), and that the four tab chips exist.
    r"_probe\test_table_tabs.py",
    # A table edit has to survive a rebuild, which is the promise a data editor
    # actually makes.  Pins that the intent stores (table, position) and never a
    # byte offset, that the replayed stream re-walks with leftover 0, and that a
    # batch across BOTH tables lands in one mod.
    r"_probe\test_table_rebuild.py",
    # 效果 (1,500 records / 10,500 commands) -- a technology only carries an
    # effect ID, so 486 records (2,795 numbers) belong to no technology and no
    # screen here could open them.  The load-bearing checks are that the walk
    # lands exactly on the table's end (a one-byte drift per record silently
    # points a write at the neighbouring record), that the five slots of a
    # command sit at type@0/a@1/b@3/c@5/d@7 (a first version derived them from
    # `d - 11` and put all three i16 on one byte, so three columns showed one
    # number), and that a packed value keeps its class byte while its number
    # changes 1 -> 7.
    r"_probe\test_effect_table.py",
    # 2026-11-03 地形 200 / 地形通行表 54 / 玩家颜色 16 -- 14,616 numbers
    # that `Parser.parse()` had already read and no screen could reach.
    # Each one is pinned to walk to its own end (a one-byte drift points a
    # write at the neighbouring record), to label itself in Chinese with the
    # terrain kind named (「地形 7 的伤害倍率」, not 「Mult.7」), and to refuse
    # the terrain shape pointer with a reason.  Measured 2026-11-03: the
    # restriction walk was 2 bytes off because `_colour_count_at()` returns
    # the count field's own offset.
    r"_probe\test_new_tables.py",
    # 2026-11-03 「我要改指定的dat或者ai/xs，你这完全没有给我选择」: 18 `.dat`
    # candidates and 62 script files on this machine, and picking one has to
    # really change what the editor reads -- not just repaint a dropdown.
    r"_probe\test_sources.py",
    # 2026-11-03 /api/mod-move called `self._body()`, a method that never
    # existed, so every move killed the handler before a response was
    # written and the screen said 「移不动：Failed to fetch」.  This pin parses
    # the handler and refuses any self.<name>() it does not define.
    r"_probe\test_handler_methods.py",
    # 「谁能造X」 -- the one question the data answers without a number, and the
    # one the reader used to refuse ("可用性得指定一个文明"), which is the opposite
    # of an answer.  Its load-bearing assertion is that a BUILDING is answered at
    # all: a Castle is `Building` id 82 and no `Unit` row has that id, so asking
    # the unit space alone produced the false sentence "not in any tech tree"
    # for something 62 of 62 civs have.  Also pins that the cannot side is
    # blocked+absent, never 62 minus the can side.
    r"_probe\test_who_can.py",
    # An ANSWER is not an ERROR.  `renderClauses` colours a card from
    # `buildable()`, which is false for anything carrying no intent -- correct
    # for a refusal, wrong for an answer.  「谁能造长弓兵」 therefore shipped as a
    # red card that read like the tool had failed.  Every other check reads the
    # JSON from /api/parse and cannot see a CSS class, so this one drives the
    # real page headless.
    r"_probe\test_answer_cards.py",
    # Opening a unit in the field editor builds the field index on first use:
    # measured 14.52 s for 136,861 records (2026-11-02), 0.003 s cached.  For
    # fourteen seconds the pane said one static sentence -- indistinguishable
    # from a hang, and the same complaint the startup bar already answers.  This
    # nail holds the whole chain: the scanner reports BYTES WALKED (not a timer),
    # /api/job answers in milliseconds while the scan holds the GIL, a cached
    # open draws no bar at all, and the scan must not get slower for reporting.
    r"_probe\test_job_progress.py",
    # Saving a file-switch is a wait of 9-22 s: `App.set_dat` decompresses,
    # parses, locates and re-indexes, and the page used to sit still with the
    # old data on screen and every control live.  Player 2026-11-08: 「点了之后
    # 我也不知道是不是在加载…这段时间我切别的页面又做什么的」.  The veil is
    # measured in a real browser on BOTH paths: the slow one must open, lock the
    # page and show a percentage the server produced; the warm one (0.31 s) must
    # not flash at all.
    r"_probe\test_datveil.py",
    # 保存 twice must UPDATE the folder it wrote last, not make a second one:
    # the folder is named from the mod Title, and an empty name box used to have
    # the SERVER derive a Title from the batch's first edit, so a mod grew one
    # folder per save.  Player 2026-11-09: 「总不能我每改动一次，就另存为一份吧」.
    r"_probe\test_save_reuse.py",
    r"_probe\test_archives.py",
    # 官方 .dat 存档架：幂等、不再对得上名字的 blob、损坏的索引、只能留最新的 prune。
    # Six complaints from one screenshot session (2026-11-02), each a real
    # defect a player hit in a real window:
    #   「有些图标不正常」    -> 400 separate /api/icon requests took 3.6 s to paint
    #   「这个改成中文」      -> the civ picker printed `British` in a Chinese tool
    #   「我改的是哪个 dat」  -> the screen never said which file on disk it edits
    #   「0/-1 是代表什么」   -> nothing explained the game's two sentinel numbers
    #   「试算这些是什么意思」 -> 试算 / 写入 are not words a player says
    #   「关闭没保存的弹窗」  -> closing the window silently dropped the batch
    # Each check names the measurement, so a future edit that undoes one of them
    # fails with the reason rather than with "the page changed".
    r"_probe\test_ui_fixes.py",
    # Where emitted mod folders go.  Measured 2026-11-02: the shipped package had
    # grown from 50.9 MB to 1.7 GB because `_out_root()` resolved to
    # `<bundle>/app` for the shipped copy -- so every suite that ran the exe
    # without AOE2MOD_BUILD_OUT wrote a 93 MB mod folder INSIDE the package.
    # Nothing broke, which is why it went unnoticed for days.
    r"_probe\test_out_root.py",
    # 「你这个大小不对啊，还有版本是哪的版本，你不能读取游戏的版本号吗，后面那一串
    # 我也不知道哪的」 (2026-11-03).  Three complaints, one line on the rail: it printed
    # 89.0 MB for a file Explorer sizes at 11.4 MB (89.0 MB is the size AFTER the
    # game's compression is undone), and it printed 「数据版本 54」, which is the .dat's
    # internal FileVersion ordinal -- the field layout the parser needs, never the
    # release the player runs.  The number the game itself shows on its main menu is
    # a banner baked into AoE2DE_s.exe.  This pin reads that exe with its own regex,
    # so a regression in aoe2mod/game/version.py cannot mark its own homework.
    r"_probe\test_version_display.py",
    # 「为什么没全部显示，比如我要添加几千甚至几万的表格怎么办」 -- the list was a
    # hard 400 with no way to reach row 401, and the counter said "400 / 1651"
    # as if that were the whole game.  Now it pages, appends, and re-batches the
    # pictures for the new page.  The load-generation check in this file also
    # pins the race measured while building it: two loads started at boot, and
    # the slower one wiped the faster one's rows.
    r"_probe\test_list_paging.py",
    # 「就不能像正常的软件那样，任何改动都能直接全页保存」 -- the gesture was
    # type, 先看看, 记下这个改动, and a value typed without the second click was
    # silently NOT in the batch: the header still said 已改 0 项 and closing the
    # window lost it without a word.  Enter now queues the edit; 先看看 stays for
    # seeing the bytes first but is no longer a step you must take.
    r"_probe\test_enter_commit.py",
    # The exe prefers a Python engine when one sits beside it, so every
    # `*_shipped` suite talks to the BUNDLE's copy of `aoe2mod/`.  A stale copy
    # there is the most expensive red in this project: the repo is green, the
    # exe answers with last week's reader, and a hundred suites report bugs that
    # were fixed days ago (it happened with `ui/nl.py`, found by accident).
    r"_probe\test_bundle_package_sync.py",
    # A refusal that names a REAL mechanism must survive typo repair.  「所有步兵
    # 砍树速度加10%」 was repaired 树速度 -> 速度 and came back as a WALK SPEED edit
    # of 217 infantry -- the repair overwrote a truthful answer.  The guard is a
    # list of terminal refusal sentences; this pins that the list is read, that a
    # real slip is still repaired, and that the sentence above stays refused.
    r"_probe\test_typo_guard.py",
    # 「造价是多少」 is a QUESTION whose answer the tool already holds.  It used to
    # name the four slots and ask which one -- a menu, not an answer.  The
    # example must also name a resource the record really charges (「城堡食物
    # 造价减10%」 points at an empty slot).
    r"_probe\test_cost_answer.py",
    # A class refusal ENDS with a sentence to copy, so that sentence is a
    # promise: it must parse, and it must be about the field the player named.
    # Both broke on 2026-11-02 -- 「射程比弓箭手更远」 was answered 「所有弓箭手移动
    # 速度加10%」 because a comparison word was tested before any field word.
    r"_probe\test_class_hint.py",
    # A card that offers a sentence is a promise that the sentence works.  The
    # reader moves under the text (one added vocabulary word re-routes a whole
    # sentence), so every one of the 15 examples is re-read through the live
    # reader and must land on its OWN intent -- the exact failure that once
    # listed 「把村民血量设成40」 on a plugin intent's card while the reader
    # resolved it to `unit.stat`.
    r"_probe\test_intent_examples.py",
    # The preview has to say what the number BECOMES (25 → 45), because checking
    # a sentence against the game otherwise means opening the field editor and
    # reading the integer yourself -- the chore this tool exists to remove.  The
    # load-bearing assertion is the one against the AVERAGE: a class edit spans
    # 217 units with different starting values (45 distinct pairs), and one
    # representative number would be a confident answer to a question nobody
    # asked.
    r"_probe\test_preview_values.py",
    # 「村民血量是多少」 -- AGE3 has no answer path at all; to learn a villager's hit
    # points you find the record in a tree of 620 columns and read the integer
    # yourself.  The question is read as 「…加1」, so `preview_values.before` IS the
    # number on disk and cannot disagree with a later write.  Pinned here: a
    # question resolves to NO intent (so the page cannot offer a build button for
    # it), and a field with several values reports how many instead of one.
    r"_probe\test_question_answers.py",
    # "Storing the intents" is the mod panel's whole promise: after a patch the
    # player should not have to remember what they wrote weeks ago.  The field
    # editor bypasses the intent compiler (no sentence resolves to "set this
    # named field of record N"), so a build recorded from it carries intents the
    # compiler REJECTS -- measured 2026-10-30, all nine historical field builds
    # were unrebuildable with "unknown intent".  Pinned here: the record stores
    # (record, field, value) and re-locates it in the CURRENT file, never a byte
    # offset, because after a patch an offset writes into a neighbouring field
    # while reporting success.
    r"_probe\test_rebuild_fields.py",
    # The shipped bundle has NO Pillow (`_build/aoe2mod.spec:88` excludes PIL), so
    # a picture swap that works in the repository and dies in the exe is exactly
    # the defect class this project keeps paying for.  This suite blocks PIL with
    # a meta_path hook before importing the reader, then reads hand-built PNG,
    # BMP and DDS fixtures whose four rows are four DIFFERENT colours -- the
    # first version of the reader ignored the row offset and read row 0 for every
    # scanline, which a symmetric test image cannot see.
    r"_probe\test_picture_formats.py",
    # 2026-10-28: Steam replaced the `.dat` and both engines kept writing through
    # offset tables measured from the OLD file -- every sampled `hit_points`
    # offset was 4397 bytes off for civilisation 1, and `/api/stat` answered
    # ok:true throughout.  Pinned here: a stamp that disagrees stops the parse
    # with BOTH byte counts in the sentence, a declared-but-absent stamp does not
    # become a shrug, and the SHIPPED folder carries `app/_golden/dat_stamp.json`
    # (without it a player's copy runs with no guard at all while the repo's copy
    # is protected -- the split-brain that has already cost this project twice).
    r"_probe\test_dat_stamp_guard.py",
    # The shell used to embed a SECOND engine -- a subset (5 of 14 sentence
    # families, 8 routes missing, a page 80 KB older) -- so a double-clicked
    # release was dumber than a checkout, and every suite here still passed
    # because they all started the Python engine.  Pinned: engine_root() prefers
    # Python, and the child dies when its parent is force-killed (TerminateProcess
    # delivers no WM_CLOSE, so the shell's own handler never runs -- a dozen
    # killed shells once left a dozen 1 GB interpreters holding ports).
    r"_probe\test_shell_engine.py",
    # The user's own words, once: 「ui有问题，显示不全，非要拖动滚动条」.  Measured
    # the same hour: the page stood 921px in an 821px window because one line
    # guessed how much chrome sat above the editor (220px, actually 272px).  The
    # gate fails on ANY `calc(100dvh - Npx)` that is not the frame's own 32px
    # padding, and then measures a real Chromium at both real widths, because a
    # text gate cannot see a page that scrolls.
    # 2026-11-03, verbatim: 「选择指定的数据文件没起作用，列表也没法全部显示，
    # 即便点了显示，随便点一个就会恢复，而且随便点一个，选中的总是在中间」.
    # Four defects behind one paragraph, all invisible to the 191 suites that
    # already ran green because every one of them read JSON from the routes and
    # none of them drove the list in a browser: the name table was a process-wide
    # singleton so a mod `.dat` still listed the install's 1651 units; picking a
    # row called `loadEditor()` with no argument and threw away the 1,251 rows
    # the player had revealed; `edRecentre` centred the pick so any scroll was
    # undone (measured 4200 -> 1718 on one click); and a request read `self.tk`
    # twice, so a swap in between decoded a 125 MB mod's offsets out of the
    # game's 93 MB stream -- the EOFError on the player's screen.
    r"_probe\test_editor_list.py",
    r"_probe\test_undo_redo.py",
    r"_probe\test_task_table.py",
    # The last record family, and the only one whose records do not say where
    # they begin: a civ's first byte is the byte after the previous civ's last
    # unit, so this table takes its starts from the unit index instead of paying
    # 9 s to re-walk 136,861 unit records.  A shortcut that is never measured is
    # a silent corruption across 63 records, so the suite walks the block the
    # honest way and requires every derived start to land on the same byte, then
    # checks the 601-slot ordering against the file's own numbers (65 live /
    # 24 varying / 536 always zero) rather than trusting the label table.
    r"_probe\test_civ_table.py",
    # The three stretches of the file that are not record families at all, and
    # therefore the three the editor could never reach: the 25 scalars after the
    # 200 terrain records (map width in pixels, tile size, the fog flags), the
    # seven counters between the last technology and the tech tree, and the 550
    # tech-tree connections.  Nothing pointed at them, so nothing refused a
    # wrong offset; this pin gives each one an address, a Chinese name, the
    # read-only fields that would desync the walk, and a write path that lands
    # and reads back.  It walks the four connection layouts separately because
    # an age record read as a unit record runs off the end of the block.
    r"_probe\test_file_tables.py",
    # The 「找字段」 placeholder is the only copy on the editor screen that
    # makes a promise, and it was a ternary chain that grew by copy: every
    # table that forgot a branch inherited 图形's 「图形文件编号 / 帧数 /
    # 播放速度」.  Measured 2026-11-04 -- 文明 offered all three (a civ
    # record has none of them), 地形 offered 「名称 / 水面」 and 颜色 offered
    # 「描边」, none of which exist in those records.  This pin reads the
    # copy out of the page and requires every example to hit a real label,
    # so a placeholder that finds nothing fails here instead of on the
    # player's screen.
    r"_probe\test_field_search_hint.py",
    # The same lie, one box over.  `#lang-xs-text` has offered
    # 「例如：把 goal 0 设成 1」 since it was built and that sentence produced
    # NOTHING: `ainl.ACTIONS` had no verb for writing a goal, so the reader
    # answered 没有读出动作 and the box returned an empty `code`.  No pin saw
    # it, because every existing one tested `ainl.EXAMPLES` -- the chips the
    # page paints -- and not the placeholder.  This pin compiles both, and
    # requires the goal bridge to WRITE (xsSetGoal / set-goal) as well as
    # read (xsGetGoal): a bridge with one direction is a box that can look
    # and not touch.
    r"_probe\test_rule_box_examples.py",
    # A civilisation typed into the 「整份 AI 脚本」 form went into
    # (civ-selected X) with no check: 「不列颠」 shipped Chinese inside the
    # file, "british" was not the token the engine's name table holds, and
    # `problems` stayed empty for both.  This pins the bridge from every
    # spelling a player can type to the token the parser reads, and that an
    # unnameable one is REPORTED instead of silently dropped.
    r"_probe\test_ai_plan_civ.py",
    # The same boundary, applied to the rest of the form.  `civ` was the
    # first field found reaching the file unexamined; `name` reached it as
    # script (a newline ended the comment the name sits in), and the two
    # counts plus `age` were repaired silently.  This pin is why a clamp
    # has to come back to the player as a sentence.
    r"_probe\test_ai_plan_fields.py",
    # Every write before 2026-11-05 was an equal-width byte swap inside a
    # record that already existed, which is what let the undo stack be a list
    # of (offset, before, after) and let `_after_write` patch three caches in
    # place.  Adding or removing a record moves every offset after it, and all
    # three assumptions failed on the way in: the flag array has to grow at
    # `ptr_off + 4*m` and not at the end of the record run (padding there made
    # the parser read the first record's bytes as 27,251 pointers and die in
    # `read_bird`); undo has to replay the steps BACKWARDS or it shrinks the
    # array before it cuts the record; and the index that says where each
    # record starts has to be thrown away, with any scan already running made
    # to lose.  This pin holds all three, plus the two refusals that keep a
    # structural edit from being silent: a record other things point at is not
    # deleted without being told twice, and `"*"` (a field-write scope) is not
    # an address.
    r"_probe\test_record_crud.py",
    # 一千条 = 一次 splice = 一步撤销, and the keys a selection needs.  The
    # batch planner writes a flag window that must never read record bytes
    # as pointers, and Ctrl+V has to be ONE undo step even when it took
    # several donors.
    r"_probe\test_editor_bulk.py",
    # One record added to one civilisation used to cost 44 s: `_restructure`
    # re-parsed 93 MB (10.45 s) and `_unit_index` re-scanned every record
    # (10.43 s), for 0.04 s of actual byte work.  A splice is a (at, cut, add)
    # plan, so the model can be MOVED instead of rebuilt -- the pin proves the
    # moved model is indistinguishable from a fresh parse (136,928 offsets, 0
    # differences), that a chain that cannot prove itself falls back to the slow
    # path, and that an undo lands back on the original bytes.
    r"_probe\test_relocate.py",
    # 「我要新增完全空白的」 -- reported 2026-11-06. Every add used to clone a
    # donor, because a unit record's tail is type-dependent and rebuilding it
    # from zeros is one guess per field. `newunit.blank_image` makes the guess
    # once and then walks its own bytes back with the reader that will read them
    # out of the file: a record one byte off does not look wrong, it makes every
    # record after it in that civilisation garbage. The pin proves the walk
    # closes at every game version, that the bytes at the new span ARE the blank
    # record, and that the model, the statistics, the browser and the field form
    # all see it.
    r"_probe\test_blank_unit.py",
    # 「为什么不能修改名字」 -- reported 2026-11-06.  Every name field was
    # read-only and the refusal for `Name` told the player to use 「重命名」, a
    # function that existed nowhere in the repo.  A name is TWO things: a
    # `debug_string` inside the record (marker + length + text, three
    # consecutive addresses) and an i32 pointing at a row in a `key-value`
    # string table -- and that id is SHARED (5079 is 57 records' name), so a
    # rename has to mint a new one and carry the row to the mod.  The pin
    # proves both halves move on all 63 civ copies, that the screens see the
    # new name before the save, that undo restores the bytes AND the model, and
    # that a rename which changes nothing writes nothing.
    r"_probe\test_rename.py",
    # 2026-11-06, two nails from the user's own 125 MB mod:
    # `test_stage_stop` because the tech tab said `_Stop: 没有说明` whenever two
    # scans overlapped (a per-call exception class plus `orig` read outside the
    # lock), and `test_name_text` because 4,473 unit names and 230 tech names in
    # that mod are UTF-8 stored in a byte string and the list showed them as
    # `è´¸æ\x98\x93`.  Both are about a rule that is right where it lives and
    # wrong where it was used, so both pins assert the SHAPE as well as the
    # behaviour -- a fix that only made the symptom go away would pass a
    # behaviour-only test while the next scan overlap brings it back.
    r"_probe\test_stage_stop.py",
    r"_probe\test_name_text.py",
    # 「单位绑定效果」其实是反过来的：.dat 里没有从单位到科技的指针，
    # 只有科技的效果命令里写着单位编号。这条钉子走一遍全表（1,510 条
    # 科技、8,005 条命令、0.1 s），核对屏幕上的数字就是文件里的数字，
    # 并且核对接它的路由在 do_GET 里——第一版插进了 do_POST，页面用
    # GET 拉，404。
    r"_probe\test_unit_effects.py",
    # The mod screen has two views over one set of rows.  The card is a class on
    # the container, not a second kind of row: the harness counts rows by
    # `className === "mod"`, so a row that said "mod card" would make a whole
    # block of assertions pass by measuring nothing.
    r"_probe\test_mods_view.py",
    # 「换图标」不是一个数字：记录里的 IconID 只是四样东西之一，另外三样
    # 在贴图文件、材质表和图标表里。四样有一半对不上，命令卡上就是空框
    # （2026-10-24 实机十一次）。这条钉子核对：两张图占两个槽、同一条记录
    # 换第二张图是同槽替换而不是报失败、一次保存会产出两个模组文件夹并且
    # 两个名字都要报出来、以及写盘时缺的正是「界面」那半个。
    r"_probe\test_icon_set.py",
    # The left-hand grid listed 363 rows the right-hand pane refused to open:
    # 529 of the 2,693 unit ids have no copy in civilization index 1 (British,
    # the reference every number in the pane is quoted from) and 「野猪」 48 is
    # one of them -- clicking it produced one red line saying the record does
    # not exist, in a civilization the player never picked.  The nail walks all
    # of them: every row the grid offers must open, the pane must quote British
    # where British has the record and say WHICH civilization it quoted where it
    # does not, and a specific civ named by the player is never overridden.
    r"_probe\test_reference_civ.py",
    # 命令面板不只是能看：拖动进会话、把单位加进卡、从卡上拿掉、改训练时间。
    # 钉子同时钉住「plan_move 只读」与「splice 拿的是活缓冲」——第一版把
    # apply_steps 交给了一份拷贝，模型照样搬迁，下一次解析死在 read_bird。
    r"_probe\test_card_edit.py",
    # '按时代' -- the era of a box comes from futuravailableunits.json's
    # RequiredAge (the file the game reads), one vote per unit because the two
    # files disagree, and two numbers per box because a box is a chain.
    r"_probe\test_card_ages.py",
    # 「搞个关于页面」 (2026-11-07): the seventh view, three addresses that are
    # printed and copied rather than linked (a real anchor would replace the
    # workshop window, which has no address bar and no back button), and a
    # version line that quotes this run's `/api/meta` instead of the markup.
    r"_probe\test_about_page.py",
    # 2026-11-08: 玩家说「右边那么大一片空白，要不你放个这张图片上去」。
    # 关于页每张卡里的正文段落只有 509px（`--measure` 62ch），卡片 1056px，
    # 右边那半张一直空着。这条钉子钉那张图：资源真在树里、路由按 image/jpeg
    # 送出、标记与样式按既有的步进写、两张窗口宽度下都不压到正文。
    r"_probe\test_notice_figure.py",
    # 玩家说「面板是只有1-15，但是游戏支持能写到30…那我想搞个这种伪翻页」
    # (2026-11-08).  三个数从此分开: 一屏 15 格、两页、引擎认到第 30 格。
    # 钉子钉住三者互不相等、page_of/page_span 的分界、写入上下限、以及
    # 页面把一屏画成一屏而不是把 30 格摊平。
    r"_probe\test_card_pages.py",
    r"_probe\test_card_pickwin.py",
    r"_probe\test_pseudo_pages.py",
    # 「这个页面依旧是不能实时更新的」(2026-11-11): 面板过去每放一个图标就
    # `loadCard` 一次 -- 两条请求、其中一条要走完 89 MB 的 civ 块。现在写动词
    # 把新的页列表自己带回来，页面按答案重画；`/api/live` 是一个长轮询，任何
    # 写（撤回/重做也算）都会把停在那里的屏幕叫醒，所以别处改了这边也跟着变。
    # 钉子钉住四件容易假的事：落后的版本号立刻作答而不是被挂住、停着的请求
    # 被唤醒时拿到的是这一整步之后的计数、三个页动词与窗口里的点击都不再
    # `loadCard`、以及轮询之间留了一段安静窗口（否则 networkidle 永不达成，
    # 渲染门禁会 30 s 超时）。
    r"_probe\test_live_panel.py",
    # 一个格子挂一串可重复研究的科技 = 伪翻页：读、写、撤销、快扫、页面入口。
    # The start-up 防伪声明 window is measured in a live page: whether boot
    # really opens it, whether its six sentences are a copy of the 关于
    # section rather than a second list, and whether "not now" and "not
    # this week" are two different decisions.  None of that is visible
    # from the source text.
    r"_probe\test_notice_modal.py",
    # A list of 18 mods with two arrows is one place per press, and every press
    # rewrites `mod-status.json` -- the file whose array order IS the load order.
    # A drag states where in one write, so the arithmetic has to be right: the
    # row is lifted OUT before it is put back (a drop one place down is otherwise
    # a no-op), Position is 1-based while the array index is 0-based, a drop past
    # the end means last, and a drop where the row already is writes nothing.
    r"_probe\test_mod_order.py",
    # 「应该给我选择数据模组的功能」-- 列文件的路由从 2026-11-03 就在，但唯一的
    # 调用者是编辑器页签栏那个下拉框，于是「这二十份里我在改哪一份」这个问题的
    # 答案住在另一个界面上。钉子钉住三件容易假的事：正在改的与游戏读的不是同
    # 一个问题（五个数据模组抢，优先级最高的赢）、一行是标签但切过去必须发路
    # 径、以及 supported 是「我们读得懂」而不是「54 这个数」。
    r"_probe\test_dat_picker.py",

    # 「format 43」不是坏文件，是 VER 7.8 的布局序号；一份模组比本体旧多少，
    # 只有 FileVersion 头能回答（记录计数会被刻意裁剪的模组误报），而那个数
    # 的方向写在函数名里（steps_behind），调用方没有机会把符号读反。
    r"_probe\test_dat_version.py",
    # One inline <script> holds ~6,000 lines, so a single bad string literal is
    # not a broken feature: the browser refuses the whole program and the page
    # looks like a server that never answered.  Measured 2026-11-05 -- a raw
    # newline inside `window.confirm(e.message + ...)` gave `pageerror ::
    # Invalid or unexpected token`, an empty #edlist, and a probe that sat on
    # `wait_for_function` for 180 s before blaming the wait.  Twelve suites load
    # that page and not one of them says "the file does not parse", which is the
    # same shape as the networkidle pin: a timeout sends the reader to the
    # timeout.  This one costs a second and names the file.
    r"_probe\test_page_syntax.py",
    r"_probe\test_filmstrip.py",
    r"_probe\test_editor_fit.py",
    # BRAND.md rule 5 had been broken twice: the Tauri shell page drew its own
    # gold pentagon and the Python loading page drew a blue one.  Pinned: one
    # inline PNG per page, pixel-identical across all three, and equal to a fresh
    # LANCZOS downscale of `brand/app-icon.png` -- plus that the build tree
    # syncs the page tauri-codegen INLINES, or a release ships a page that is not
    # in the repository.
    r"_probe\test_splash_brand.py",
    # Where the products live, asserted rather than assumed.  The bundle and the
    # cargo tree were written outside the checkout until 2026-11-01; the owner
    # asked twice to keep them in the workspace, and the reason is not tidiness
    # -- a copied `runtime\python.exe` outside the checkout died with
    # 0xC0000135 because the folder's Integrity Label differed, which cost six
    # hours to find.  This pin fails the moment a probe spells an absolute
    # product path again.
    r"_probe\test_products_in_workspace.py",
    # The other half of the Chinese-text work, and the reason two rounds of it
    # were partly wasted: refusals found by calling the facade with a hand-written
    # intent are not necessarily refusals a player can reach.  What a player can
    # reach is exactly what `nl.read()` can produce.  Six English refusals in the
    # compiler are API-only -- a sentence cannot spell an unknown intent, an
    # unknown stat key, or a civilization that is not in the game -- and this
    # holds that line with the sentences that WOULD trigger each shape, plus a
    # third check that the facade still refuses all six (otherwise the first two
    # would stay green by describing something that no longer exists).
    r"_probe\test_screen_reach.py",
    # A unit the game does not have.  This is the one intent that APPENDS a record
    # instead of patching a byte, so nothing the byte patcher's suites prove
    # applies to it: an append moves every byte after it, and the reader walks the
    # civ's slot array in order.  The suite therefore checks the three things a
    # green reparse would not catch on its own -- that the emitted .dat re-parses
    # with every byte consumed, that the new id is IN the civ's record run, and
    # that the name line landed in the file the game's own 605-byte instructions
    # name as the way a mod adds a string.
    r"_probe\test_new_unit.py",
    # The command-card box.  The manifest can say "moved to box 5" while the byte
    # in the shipped record still says 1 -- nothing downstream re-reads it -- so
    # this pin asserts on the emitted file, not on the return value.  It also
    # covers the two refusals a player can reach by typing a number: a box the
    # card cannot hold, and a donor whose train entry points at no building at
    # all (British has 683 such units, so that donor is reachable by name).
    r"_probe\test_new_unit_box.py",
    # The first feature this project built on a dat-folder JSON file rather than on
    # .dat bytes.  Its expensive failure is not "the group was not added" but "the
    # file was rewritten and the player's own groups were replaced", so the pin
    # re-reads the emitted file from disk and compares every pre-existing group key
    # for key -- and checks the line endings survived, because a file that flips to
    # LF shows up as a whole-file diff in any mod a player unpacks.
    r"_probe\test_linked_group.py",
    # The other half of the same feature, and the reason it exists: a `.dat`
    # effect's command list is variable-length, and the writer used to advance its
    # raw cursor by the NEW count without correcting for the old one.  Measured
    # 2026-10-22: appending two commands emitted 22 bytes and produced a
    # 96,331,764-byte stream (+3,061,612) whose re-parse died inside read_bird.
    # A pin here matters because the failure is not local -- it corrupts every
    # field after the edited record, so no other test would name the cause.
    r"_probe\test_effect_append.py",
    # A technology the game does not have, from a sentence.  The module-level
    # clone is pinned in `test_new_tech.py`; what is pinned HERE is the path a
    # player walks -- the reader used to refuse every such sentence with a
    # complaint about a missing UNIT, and the preview used to promise files the
    # build did not write.
    r"_probe\test_new_tech.py",
    r"_probe\test_tech_create.py",
    # Reading a community mod back.  This is the newest capability and the one
    # with the longest failure mode: a mod that ships a whole .dat keeps handing
    # the engine a snapshot from the day it was built, and nothing says so.  Four
    # verdicts, each reachable and named: identical / no_dat / auto (one edit) /
    # impossible (a different generation of the format).  The last one used to
    # report "读不开" because the version was read AFTER the parse -- the file's
    # layout is exactly what cannot be walked, so the order is load-bearing.
    r"_probe\test_repair.py",
    # Turning that diff back into edits.  The interesting fact is not that a
    # read-back works but that it is EXACT: `dsh test v46` changed five
    # town-centre records, one intent reproduces all five, and the rebuilt
    # stream is byte-identical to the author's own file.  A fold that is skipped
    # cannot even run (sentence 2 is a no-op), and a family split across two
    # values has no single-intent answer -- the second is the one worth a
    # conflict report rather than a quiet choice.
    r"_probe\test_replay.py",
    # The step after replay: rebuild the mod and put it back.  Two failures look
    # like success here -- a rebuilt .dat carrying the wrong numbers (the mod
    # still loads) and a reinstall that deletes the author's other files
    # (install_mod does rmtree + copytree, and 14 of the 16 mods measured on this
    # machine ship more than info.json + .dat).  Both are asserted, and the
    # strong claim is byte identity: same intents, same base data, same stream.
    r"_probe\test_repair_apply.py",
    # The AI entry, and the one thing it must never do.  A model is asked for
    # sentences and answers with sentences; those go into the box and the
    # ordinary reader judges them.  If a model's answer ever came back as an
    # intent, plan or bytes, it would re-enter below all three gates -- the
    # reader's refusal, plan()'s refusal, and the plan/build agreement nail -- so
    # the core assertion here is that nothing but text crosses back.  The rest
    # covers the two states of the button (no configuration means no box at all)
    # and the HTTP shape, against a local server so no key and no network exist.
    r"_probe\test_ai_entry.py",
    # The one shape that makes an icon appear: two folders.  A mod folder that
    # carries both the .dat and widgetui is read as a data mod only, so the icon
    # tables never load (measured 2026-10-24: five runs empty, one split run
    # drawing).  This nail asserts on the PROFILE rather than the build output,
    # so it fails on either half of the rule breaking: the emitter no longer
    # splitting the layer, and install no longer following it in.
    r"_probe\test_split_delivery.py",
    # What a newcomer reads.  Six defects shared one shape: the bytes were right
    # and the SENTENCE was wrong (a raw "wood" in a Chinese preview, a reader's
    # assumption dropped on the floor, no way to tell which of twenty mods the
    # next match loads, "已生成并安装" printed without reading verification.ok,
    # an instruction pointing at a screen that has no data-mod dropdown, and two
    # English refusals on the way in).  None of them could turn any other nail
    # red, which is exactly why they shipped.
    r"_probe\test_newcomer_wall.py",
    # The registry itself.  Ten probes rotted unrun before anyone noticed, and
    # the reason nobody noticed is that "is every test reachable?" was a question
    # only a human could answer.  This asks it mechanically, including the four
    # files that are named test_* but are measurements -- declared, with reasons,
    # and checked for staleness.
    r"_probe\probe_suite_registry.py",
    # The pair a split build becomes on screen.  `list_mods` returns two rows and the
    # page drew them as unrelated entries: two switches for one decision, and
    # switching one alone is the state measured to draw no icon while looking fine.
    # Pure naming rule over rows, so it needs no game data -- the cases that matter
    # are the ones a screen cannot show (an orphan half, a title that really ends in
    # the word).
    r"_probe\test_pair_rows.py",
    # One sentence, a whole class of units.  骑兵 is a category (188 visible
    # units, no record of its own) and used to be refused -- correctly, because
    # the substring fallback landed on 科技「骑兵钢甲」.  With a scope word it is
    # a deliberate edit of 13,671 records in half a minute, so both halves are
    # pinned: the scoped reading WORKS, and the unscoped one is still refused.
    # The byte assertions are the point -- the build re-reads the emitted .dat
    # and requires every member to have moved by exactly the amount while no
    # record outside the class moved at all (1,764 moved, 0 wrong, measured).
    r"_probe\test_class_edit.py",
    # The window mode of the one entry point.  This is the only suite that starts
    # `tools/run_ui.py` as a real process and looks for a real top-level window,
    # because every cheaper version of this test passes while the launcher is
    # broken: an in-process call to `_run_window` says nothing about the
    # `__main__` wiring, and importing pywebview says nothing about whether the
    # machine can render (measured 2026-10-25: import failed until the package was
    # installed into `_vendor`, then a real window opened -- the same sentence was
    # true, then false, which is why it is measured instead of repeated).
    r"_probe\test_window_mode.py",
    # The arithmetic of a mirrored field.  `dat_bindings.json` describes the
    # mirror in prose ("moves both by the same DELTA and never copies the
    # value"); this suite is that sentence with numbers attached.  It exists
    # because the first version of it was VACUOUS and stayed green while the
    # mirror was broken to copy the value -- it checked cavalry, and British
    # cavalry has 0 records whose two fields diverge, so it was asserting a
    # property of records nothing had written.  The gap check now edits archers
    # (3 divergent members) and first asserts those records were written at all.
    r"_probe\test_class_mirror.py",
    # The reader's vocabulary is derived from `dat_bindings.json` since
    # 2026-10-25.  Two failures are possible and they point opposite ways: a
    # learned word can re-route a sentence that used to be right (a WRONG ANSWER,
    # not a refusal), and `sentence_reachable()` can advertise an intent no
    # sentence produces (a claim nobody can cash).  This file measures both, and
    # its first version only measured the first -- the reachability half was
    # "does this intent name a bound field?", which is true for a plugin intent
    # that merely repeats shipped options and can never be reached because
    # `intent_for_stat()` hands each word to exactly one intent.
    r"_probe\test_nl_schema_words.py",
    # The ones above ask the schema on a cold start.  This one adds a plugin while
    # the process runs and asks again WITHOUT clearing anything -- which is what a
    # player actually does.  It exists because `load_schema()` already keys its cache
    # on the schema directories while the vocabulary built from it was keyed on the
    # literal "table": the plugin showed up in `meta.intents`, the page offered it,
    # and every sentence for it was still refused until a restart (measured
    # 2026-10-25).  Clearing the cache inside the test would be the test instructing
    # the code; the player cannot clear a cache.
    r"_probe\test_nl_live_vocab.py",
    # This one nails the CHEAP facts behind an expensive open question: the loader's
    # field list in the EXE, what `chance` means, and the family edges the product
    # reads.  Those facts rot silently -- a report number drifts, a Steam update
    # rewrites the shipped file, or `declared_edges()` stops returning the villager
    # pair (the worst case: the two halves are no longer one family, so every villager
    # edit silently halves).  It deliberately does NOT nail "does the game honour a
    # mod's copy", which is still open, so the boundary is printed at the end.
    r"_probe\test_objreplace_facts.py",
    # Two independent halves: every editable plan must name the file it rewrites
    # (the four byte-patcher intents said nothing until 2026-10-25), and the page
    # must print that field -- a plan key nobody renders is half a fix.  Both
    # halves fail separately, which is why the sweep alone would have missed it.
    r"_probe\test_plan_writes.py",
    # 2026-10-25: a nail asserted `got["intent"] == intent_for_stat(...)`, and the
    # reader computes that id with the same call -- pinning the function moved BOTH
    # sides, so it stayed green while every plugin intent became unreachable.  This
    # suite is a source-level guard against that shape coming back.
    r"_probe\test_nail_hygiene.py",
    # The ledgers' counts must equal the tree's.  Two properties make this worth
    # running: an undated claim that disagrees reds it, and the dated-record rule
    # still matching something -- without the second it would demand that six
    # dated rows be rewritten to today's number.
    r"_probe\test_doc_drift.py",
    # "插件化" has two halves and only one of them was measured.  A plugin can teach
    # the reader a FIELD (that is `test_nl_schema_words.py`); it cannot add a sentence
    # SHAPE, because `nl.py` decides meaning in thirteen hand-written branches.  This
    # one builds two plugins -- one with a `stat` field, one without -- and asserts the
    # screen advertises only the first, plus that a sentence shaped like the second is
    # refused instead of quietly becoming something else.  The failure it guards is a
    # green tick on a promise nobody can keep.
    r"_probe\test_sentence_shapes.py",
    # The picker that answers "what does this change touch".  It is a suite for the
    # same reason the registry check is one: its failure mode is a SMALL number, not
    # an error.  Measured while building it -- matching the changed path answered
    # "4 of 125" for `aoe2mod/api.py` where 84 suites reach it, and a 3-character
    # floor on the module stem silently dropped `nl.` and two suites with it.
    r"_probe\test_suite_picker.py",
    # The fourteenth intent: a row in `objreplacement.json` that the engine reads
    # when it GENERATES the map, so it changes what stands on the ground at 0:00
    # rather than what a barracks can produce.  Measured 2026-10-25 on a real
    # match (report §十一).  Two shapes here are the ones that go wrong quietly:
    # a row added beside the shipped ones (must not disturb the villager sex
    # swap) and a row that REPLACES one (must be refused unless asked for).
    r"_probe\test_replace_on_map.py",
    # The sentence layer for the same intent.  The file above asks whether the
    # ROW is written; this one asks whether a player can ASK for it -- and the
    # two fail independently: the branch landed with every phrasing refused as
    # "this sentence has no number", and the file-writing nail was green.
    r"_probe\test_replace_sentence.py",
    # Structural rather than behavioural: it walks every nail in this folder and
    # fails if any of them records a failure after its last `if FAILS:` block.
    # Written because I did exactly that on 2026-10-25 -- the section printed two
    # FAIL lines and the suite still exited 0 -- and no other nail can see it.
    r"_probe\test_gate_order.py",
    # The runner's own two contracts, because both broke on 2026-10-25 and
    # nothing else could see it: a word-match on FAIL called two GREEN suites
    # red (`ok   a FAIL at any column is recognised`), and importing this file
    # ran all 131 suites because the loop sat at module level.
    r"_probe\test_runner_contract.py",
    # The other half of that contract, and the reason the first half is safe to
    # loosen: the rule now ignores a SENTENCE about FAIL, so something has to
    # check that every shape the suites actually print is still recognised.
    # Reading their string literals found `_probe/test_effect_append.py`'s
    # `[FAIL] name :: detail` -- a real report the loosening had let through.
    r"_probe\test_fail_shapes.py",
    # And the coverage claim next door.  `_probe/test_full_sweep.py` reports
    # DECLARED BUT UNSWEPT for any intent it cannot build a case for; the
    # exemption table answers that, and this nail checks the answers are
    # checkable (file exists AND carries the token the table names).  It also
    # covers a hole a 20-minute sweep leaves: nothing else ran that guard's
    # rules without paying for the whole run.
    r"_probe\test_sweep_exemptions.py",
    # The form panel composes sentences the player never typed.  A template
    # that drifts from the reader still "works" on screen -- the click fills
    # the box and the sentence underneath is one the tool cannot read -- so
    # the only place that drift can be seen is a round trip.
    r"_probe\test_compose_roundtrip.py",
    # The route the page actually reads must hand out the same forms the
    # round trip measured; a filter or a re-sort in between would offer a
    # form the reader refuses, and nothing would say so until a click.
    r"_probe\test_forms_route.py",
    # The screen's wording lives in one table now, and three separate things can
    # rot it without raising anything: a tag naming a key the table lacks (the
    # inline Chinese stays, so it looks fine), a tag moved onto a container
    # (`textContent` then deletes the `<code>` samples the sentence talks about),
    # and a status word that starts printing `status.frobnicated` instead of the
    # machine value.  Each was measured by breaking one place and watching this
    # file print a named failure.
    r"_probe\test_locale.py",
    # Named recipes: the sentences a player types every week, saved under a name.
    # Saving a name and reading it back always works; the failure this file is
    # written against is a stored sentence that the READER no longer accepts,
    # sitting in the list looking exactly like a working one.  Its own first run
    # crashed on a corrupt file instead of reporting it, and the reverse check
    # could not see the indented `  FAIL` lines it prints -- both fixed here.
    r"_probe\test_recipes.py",
    # The front page's intent TABLE.  Section E of test_doc_drift asks whether the
    # README names every intent, and it stayed green while the table was a row
    # short -- because that intent was mentioned lower down.  A mention is what a
    # search finds; a row is what a stranger reads.
    r"_probe\test_readme_table.py",
    # project.json is generated from the live schema; this rows the two ways it
    # can lie -- a file nobody regenerated, and a generator that is wrong the
    # same way every time (which `--check` cannot see, because the file does
    # equal what the generator produces).
    r"_probe\test_project_json.py",
    # The handoff page's info table broke twice in three days and only a human
    # noticed: a history row split across two physical lines (which ends the
    # table for every row after it), and an edit that prepended the newest story
    # while keeping the old one, so the cell read twice.  Walks the table from
    # its header instead of naming line numbers -- those move whenever a section
    # is added above, and a gate that demands the wrong range cries wolf.
    r"_probe\test_handoff_table.py",
    # The player-facing page and the schema are two artifacts describing the same
    # features, and on 2026-10-26 they disagreed: `unit.create`'s honesty note
    # still said the bundle path had never been loaded while a sibling field in
    # the same object cited the run that loaded it (v85).  This checks membership
    # AND dates -- a page that says a feature was seen but moves its date is the
    # half a membership-only check would miss.
    r"_probe\test_release_notes.py",
    # Every URL the page fetches must exist, every panel must be loaded by
    # something, and every route must reach a producer.  The neighbouring
    # `test_page_route_contract.py` compares the KEYS inside bodies; a panel whose
    # URL was never implemented stays silently empty and its rejection is swallowed
    # by the same catch that handles "no recipes yet".
    r"_probe\test_url_coverage.py",
    # The design checker is the gate the workspace contract names; this nail is
    # what stops the gate from quietly relaxing.  It writes its own scratch tree,
    # so it must not be pointed at the live page.
    r"_probe\test_design_acceptance.py",
    # The command card: one byte per box.  Registered because every way it can
    # fail looks like success -- a wrong offset reads garbage and re-parses to
    # the old box, and an overwrite instead of a swap drops a unit silently.
    r"_probe\test_card.py",
    # Can the player READ why it failed?  Both failure shapes are silent when
    # broken: the shell's error page was a blank window for want of a Cargo
    # feature, and the engine's failure was a splash that spun forever.  This
    # suite reads painted pixels, so it also catches the case where the reason
    # is on screen but a 74-character path is clipped by the box it sits in.
    r"_probe\probe_startup_failure.py",
    # Is the native build's .dat the same BYTES as the reference's?  Every
    # cheaper check stayed green while `城堡攻击加5` shipped half the writes it
    # should have, because AoE2 stores several numbers twice and only one of the
    # two was moving.  A count of one's own writes cannot see that; a byte
    # comparison of two independent builds can.
    r"_probe\test_stat_mirrors.py",
    # Can every sentence the parser accepts also be built?  `check_routes.py`
    # compares route names and `report_typable.py` compares parse output, so
    # neither asks this -- and three intents accepted a sentence and then refused
    # it at build time.
    r"_probe\test_parse_build_agreement.py",
    # Does a sentence that names a civilisation still edit all 63 of them?  It
    # did, and nothing observable said so: `/api/parse` returned 200, the intent
    # looked right, the edit count was plausible.  The only witness is asking
    # whether the bytes match what the sentence asked for, which this does by
    # building the same edit in Python and comparing hashes.
    r"_probe\test_civ_scope.py",
    # Does `/api/rebuild` put the rebuilt bytes back where the mod lives?  It
    # answered ok with a fresh edit count while the installed file kept the old
    # bytes, because the replay neither installed nor reused the record's title.
    r"_probe\test_rebuild_installs.py",
    # Does the reader put the target on the same BYTE as the reference?  Two
    # implementations agreeing on the intent is not agreement: `tech.effect`
    # subtracted one from the ordinal on both sides, so the report looked right
    # while the writer edited the second command instead of the first.  Only a
    # comparison of the resolved offset catches that.
    r"_probe\test_reader_matches_reference.py",
    # Does `unit.sprite` rewrite the unit the sentence named?  It walked one
    # frozen pair table (villager -> sheep), so every sprite sentence edited the
    # villager's 244 records no matter which unit was asked about -- and the
    # preview described the sentence rather than the edit.
    r"_probe\test_sprite_target.py",
    # Does the count the preview promises equal the count the build reports?
    # Three of the seven builders emitted no `edit_count` from their dry path, so
    # `织布机研究时间改成5` previewed 0 for an edit that writes one.  A zero that
    # means "this shape does not report" reads exactly like a zero that means
    # "nothing will happen".
    r"_probe\test_preview_counts.py",
    # ---- five suites that existed on disk but were named by NO runner --------
    # `probe_suite_registry.py` reported ten such files on 2026-11-01.  A suite
    # nothing runs is not a gate; it is a file that looks like one, and it can
    # rot for months while `SUITES: ALL PASSED` keeps printing.  The five that
    # finish in seconds live here; the five that spawn the shipped shell or walk
    # 93 MB twice live in run_long.py.
    r"_probe\test_civ_trees.py",
    r"_probe\test_mod_routes.py",
    r"_probe\test_dds_parity.py",
    # DDS parity compares the Rust decoder against the Python one, and until
    # 2026-11-05 they agreed with each other because they shared one bug: both
    # read BC3 alpha with the DXT3 rule (sixteen 4-bit values) instead of two
    # endpoints plus sixteen 3-bit indices. Seventeen of the editor's 400 icon
    # rows then had no opaque pixel at all and read as ghosts -- reported by the
    # owner that morning. Agreement between two implementations is not evidence
    # when both were written from the same wrong sentence, so this suite checks
    # the alpha plane against a third decoder built from the format description.
    r"_probe\test_dds_alpha.py",
    r"_probe\test_dat_baseline.py",
    # plan/build agreement on all eleven intent shapes.  The same sentence going
    # through two paths that disagree about the count is the bug class this tree
    # keeps finding, and this was never in a runner.
    r"_probe\test_plan_roundtrip.py",
    # The operation log: every write route leaves one line, and a log folder the
    # player cannot write to cannot fail the write itself.  Found by
    # probe_suite_registry.py on 2026-11-09 as the last suite on disk that no
    # runner named -- which meant "the log has one line per operation" was a
    # claim with nothing behind it, on the one file a support question is
    # answered from.  Three seconds, so it belongs in the fast list.
    r"_probe\test_oplog.py",
    # 「这个生成的东西应该放local去」, 2026-11-10: the script screen's save button
    # had three paths (write a rule, save a file, save an OLD file) and none of
    # them put the result under mods/local, so a generated rule could only land
    # on the game's own 53 `.per` files.  Three suites, one per question: the
    # library (aifiles), the route (over the socket), and the BUTTON (the page's
    # own handler, with the chooser refreshing beside it).
    r"_probe\test_local_overwrite.py",
    r"_probe\test_local_save_shipped.py",
    r"_probe\test_local_save_click.py",
    # Every row `upgrade_check` returns carries the same twelve counters.  The
    # refused path used to hand-build ten of them, so a mod the engine could not
    # move printed "undefined 条" for the two counters that only exist on a
    # whole-record copy -- and refused rows are the ones a player re-reads.  Five
    # seconds, and it reads the source to make sure the copies do not come back.
    r"_probe\test_upgrade_counts.py",
    # The effect table is the one place where a record count says nothing about
    # whether the port worked: an effect has no id, so a technology points at one
    # by POSITION, and a copied technology onto a newer file points at whatever
    # now sits in that slot.  Measured on 408773 (VER 8.8 -> 8.9): 1,731 live
    # pointers, 247 naming a different effect, 5 naming nothing -- which is the
    # player's report, "the mod updated and there is only a shell left".  The
    # join decision is a pure function over record bytes, so its properties get
    # checked here without a single .dat; the report contract is pinned beside it
    # because a fix the panel does not print is a fix the player cannot verify.
    # Under a second.
    r"_probe\test_effect_link.py",
    # A technology has no id: it is addressed by POSITION.  So when 8.9 fills the
    # placeholder slots at 18/78/79/121 with [SCEN] Move Huskarl and three [FTT]
    # techs, "carry the author edit to position 78" stops meaning "carry the
    # author edit" and starts meaning "delete an official technology" -- measured
    # on 314918, whose installed file was missing three official techs and had a
    # name field reading `Fabric ArmorHuskarl`.  The fix moves the author record
    # to the tail and repoints every RequiredTechs that named the old slot.  Three
    # name lists and one integer map, so the properties are checked here against
    # the installed game data, no mod build.  ~2 s.
    r"_probe\test_tech_slot_reuse.py",
    # Rebuilding a mod always lands in `mods/local/<name>`, and the copy it was
    # rebuilt FROM usually sits in `mods/subscribed/` -- Steam owns that folder,
    # so writing into it gets checked and reverted.  Both entries carry the same
    # `.dat`, so "which mods need adapting" listed a mod twice and "adapt all"
    # rebuilt it again on every press.  This pins the three answers: one row per
    # mod, the new copy takes the old one's slot (`priority` is 1-based,
    # `position` is 0-based), and the old entry is disabled rather than deleted.
    # 0.2 s, all in a temp profile -- it belongs in the fast list.
    r"_probe\test_upgrade_handover.py",
    # Carrying a record between DAT generations reads the source BY FIELD NAME,
    # so a fact that two generations store under different names is not carried,
    # it is defaulted -- silently, because a missing name is a legitimate answer
    # and only a pack failure is an error.  Measured on the 209785 mod (VER 8.4
    # rebuilt onto 8.9): every unit's Creatable.TrainLocationsCount went out as 0
    # and every tech's ResearchLocationCount did too, so AGE showed an empty
    # training list and the author's own technologies had no research building.
    # This suite pins both directions of the two fold pairs, plus the two things
    # a fold must not do (invent a count, silently drop extra slots), plus a
    # same-generation byte-for-byte round trip on every archived generation that
    # parses.  The module has claimed this file existed since it was written.
    # ~35 s, four parses of a 93 MB build.
    r"_probe\test_portgen.py",
]

# Suites that are not Python.  The screen's script is JavaScript and no Python
# test can execute it: `test_ui_server.py` calls the same App the page calls and
# stayed green through two shipped page defects -- a refusal counted as buildable,
# and then a ReferenceError on every render.  Run it where it actually runs.
NODE_SUITES = [
    r"_probe\ui_page_harness.js",
]

fails = []
TOTAL = len(SUITES) + len(NODE_SUITES)
DONE = [0]


def _tick():
    """Print the position in the WHOLE run, not in whichever list we are in.

    A bare `exit=0` line tells nobody whether the next suite takes two seconds or
    three minutes, and this run has both kinds.  The counter is the only thing on
    this output a human can use to decide whether to wait.
    """
    DONE[0] += 1
    sys.stdout.write("[%d/%d] " % (DONE[0], TOTAL))
    sys.stdout.flush()


DEV_PORT = 7811
DEV_URL = "http://127.0.0.1:%d/" % DEV_PORT


def _ask(path, want=None, timeout=10):
    """GET one route off the dev server; None when it does not answer.

    Kept as a plain function rather than a session object because the only
    question this file asks is "is the page up yet".

    Ten seconds, not three: this runner does not own 7811 -- a developer's own
    engine, or another suite driving a .dat switch, can hold the one thread that
    is parsing for tens of seconds.  Measured 2026-11-12: /api/meta answered
    after **48 s** while a datveil run was mid-switch, and a 3 s window read
    that as "nothing is there" (see _dev_server, which then started a second
    server on the same port).
    """
    import urllib.request
    try:
        with urllib.request.urlopen(DEV_URL + path, timeout=timeout) as r:
            body = r.read()
    except Exception:                                    # noqa: BLE001
        return None
    if want is not None and want not in body:
        return None
    return body


def _port_open(host="127.0.0.1", port=None, timeout=2.0):
    """True when a TCP connect to the port succeeds.

    Separate from _ask on purpose: "a socket accepted me" and "an HTTP answer
    came back inside N seconds" are different questions, and confusing them is
    how a busy server gets reported as an absent one.  The connect is refused
    in milliseconds when nothing listens, so this costs nothing on a quiet box.
    """
    import socket
    try:
        with socket.create_connection((host, port or DEV_PORT), timeout=timeout):
            return True
    except OSError:
        return False


def _stop(proc):
    """Put the dev server down without letting it outlive the run."""
    if proc is None or proc.poll() is not None:
        return
    try:
        proc.terminate()
        proc.wait(timeout=20)
    except Exception:                                    # noqa: BLE001
        try:
            proc.kill()
        except Exception:                                # noqa: BLE001
            pass


def _dev_server():
    """Make sure something answers on 7811 before the suites read it.

    Seventeen suites in the fast list -- test_datveil, test_live_panel,
    test_card_pages, test_notice_modal, test_ui_fixes, test_version_display,
    test_list_paging, test_enter_commit, test_task_table, test_civ_table,
    test_file_tables, test_unit_effects, test_notice_figure, test_card_pickwin,
    test_pseudo_pages, test_editor_fit, test_filmstrip -- default their BASE to
    http://127.0.0.1:7811 and never spawn a server themselves.  Run by hand
    after starting the dev server they are green; run by this runner on a quiet
    machine all seventeen went red on 2026-11-12 with ERR_CONNECTION_REFUSED.
    A missing server reported as a broken page is the same lie as a stale
    server reporting a fixed bug: both blame the code for the harness.

    So: reuse a server that is already there (a developer's own 7811), else
    start one, and wait for /api/progress to say ready -- the page answers
    /api/meta seconds after binding, but the tables are only filled once the
    warm thread has read the game data (measured 36.9 s on 2026-11-12, and a
    suite that measures a half-warm page is measuring the wrong thing).
    Returns the process, or None when the port was already served.
    """
    import atexit
    import time

    # "Is anything there" is a TCP question, not an HTTP one.  The HTTP answer
    # can take 48 s when the server is busy parsing a .dat (measured
    # 2026-11-12), and treating that silence as absence started a SECOND server
    # on the same port -- which Windows allows to bind, so two engines then
    # answered at random and every suite that read the wrong one went red.
    if _port_open():
        print("dev server: 7811 is already listening, using it as it is")
        return None

    proc = subprocess.Popen(
        [PY, "-X", "utf8", "-u", os.path.join(ROOT, "tools", "run_ui.py"),
         "--serve-only", "--port", str(DEV_PORT)],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    atexit.register(_stop, proc)

    deadline = time.time() + 240
    while time.time() < deadline:
        if proc.poll() is not None:
            print("dev server: run_ui.py exited with %s before it listened; "
                  "the seventeen suites will report their own failure"
                  % proc.returncode)
            return proc
        if _port_open(timeout=0.5):
            break
        time.sleep(0.5)
    else:
        print("dev server: nothing listens on %s after 240 s" % DEV_URL)
        return proc

    # Measured from a plain start stamp, not from "deadline minus 300": the
    # first version printed the difference between two clock reads taken on
    # the same line, so it always said 0.0 s and told us nothing about how
    # long the warm thread really took (2026-11-12).
    warm_t0 = time.time()
    while time.time() - warm_t0 < 300:
        body = _ask("api/progress")
        if body is not None and re.search(rb'"ready"\s*:\s*true', body):
            break
        if proc.poll() is not None:
            break
        time.sleep(1.0)
    print("dev server: %s is up (pid %d, warm after %.1f s)"
          % (DEV_URL, proc.pid, time.time() - warm_t0))
    return proc


#: The three files a probe or a mod installer writes into the game folder, and
#: the archived originals they must equal.  Measured 2026-11-13: a helper script
#: (`_probe/_tmp/inst5.py`) installed a crc-forged `.dat` into the live game at
#: 04:18 during a full run; 36 suites then failed with `StampError` -- correctly,
#: because the stamp really was measuring a different file -- and the run looked
#: like a code regression for ten minutes.  A guard that names the file, the two
#: sha256 prefixes and the minute it changed turns that into one line.
#: The install the probes read.  A string with forward slashes: `os.path.join`
#: with a bare "D:" jumps through the drive's current directory.
LIVE_DAT_DIR = "D:/Games/Steam/steamapps/common/AoE2DE/resources/_common/dat"
VANILLA_DIR = os.path.join(ROOT, "_cache", "vanilla_dat")
DATA_FILES = ("empires2_x2_p1.dat", "futuravailableunits.json",
              "paphosfutureavailableunits.json")


def _sha256_head(path):
    """First 16 hex chars of a file's sha256, or None when it is not there."""
    import hashlib
    try:
        with open(path, "rb") as fh:
            h = hashlib.sha256()
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()[:16]
    except OSError:
        return None


def _data_state():
    """`{name: (size, sha16_or_None)}` for the live game data files."""
    out = {}
    for name in DATA_FILES:
        path = os.path.join(LIVE_DAT_DIR, name)
        try:
            size = os.path.getsize(path)
        except OSError:
            size = None
        out[name] = (size, _sha256_head(path))
    return out


def _report_data(before=None):
    """Print how the live game data compares to `_cache/vanilla_dat`.

    Returns the current state so the caller can compare it again later.  This
    never refuses to run: a `.dat` from another generation is a legal thing to
    have (the tool exists to merge mods), it is just not a state in which a red
    suite means anything.
    """
    state = _data_state()
    odd = []
    for name in DATA_FILES:
        size, sha = state[name]
        want = _sha256_head(os.path.join(VANILLA_DIR, name))
        if size is None:
            odd.append("%s is MISSING from the game folder" % name)
        elif want is not None and sha != want:
            odd.append("%s is %s bytes / %s, the archived vanilla is %s"
                       % (name, size, sha, want))
    if before is not None:
        for name in DATA_FILES:
            was = before.get(name) or (None, None)
            now = state.get(name) or (None, None)
            # Already reported above when it is simply not there; report only a
            # real transition, so a missing file does not print twice.
            if was != now and now != (None, None):
                odd.append("%s CHANGED DURING THE RUN: %s -> %s"
                           % (name, was, now))
            elif was != now:
                odd.append("%s DISAPPEARED DURING THE RUN: was %s"
                           % (name, was))
    if odd:
        print("=" * 78)
        print("GAME DATA IS NOT THE ARCHIVED VANILLA -- read every red below in")
        print("that light.  A stamp error is the guard doing its job, not a")
        print("regression.  Restore with `python -X utf8 "
              "_probe/restore_vanilla_dat.py`.")
        for line in odd:
            print("  * " + line)
        print("=" * 78)
    else:
        print("game data: the three live files match _cache/vanilla_dat")
    return state


def main():
    """Run every suite and return the exit status.

    Kept behind the guard below so this file can be imported: a probe
    that only wants `_FAIL_RE` or `SUITES` must not start a 131-suite
    run.  Learned on 2026-10-25 by doing exactly that.
    """
    # One env var, one meaning, for every child.  `AOE2MOD_BUILD_OUT` is read
    # by `aoe2mod/ui/server.py`, and several suites start the SHIPPED exe with
    # `cwd=<bundle>`.  A relative value therefore names a different folder in the
    # exe than in the runner, and the build reports a path nobody can find:
    # `test_sprite_target.py` and `test_civ_scope.py` both failed on 2026-11-02
    # with `no .dat in the built folder` while passing when run by hand.  Fix it
    # once here, resolved against the repo, instead of in every suite.
    _bo = os.environ.get("AOE2MOD_BUILD_OUT")
    if _bo and not os.path.isabs(_bo):
        os.environ["AOE2MOD_BUILD_OUT"] = os.path.join(ROOT, _bo)

    # Seventeen suites read an ambient 7811 and none of them starts one; see
    # _dev_server.  Started once for the whole run, not per suite: the warm
    # thread takes ~37 s and paying that seventeen times would double the run.
    dev = _dev_server()

    # The three live game-data files, before the first suite reads them.  Printed
    # again at the end so a file that changed mid-run is named.
    data0 = _report_data()

    for rel in SUITES:
        path = os.path.join(ROOT, rel)
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        # Say which suite is running BEFORE waiting for it.  A run of 230 items
        # prints nothing until an item finishes, and the first one alone takes
        # six to eight minutes (aoe2mod/tests/test_compiler.py); two long runs
        # were killed on 2026-11-12 for looking stuck while they were working.
        print("%-46s running" % os.path.basename(rel))
        p = subprocess.run([PY, path], cwd=ROOT, env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out = p.stdout.decode("utf-8", "replace")
        tail = [ln for ln in out.strip().splitlines() if ln.strip()]
        verdict = tail[-1] if tail else "(no output)"
        # The exit code is the real signal.  The text scan is only a backstop for a
        # suite that prints a failure yet forgets to exit nonzero -- and it must not
        # fire on an identifier that merely CONTAINS "FAIL", e.g. the label
        # "IDS_FAILED_TO_OPEN_FILE" in probe_install_safety.py (the `_` before it
        # means no word boundary).  A crude `"FAIL" in out` flagged that suite as
        # broken while it was passing every check.
        bad = p.returncode != 0 or _FAIL_RE.search(out) is not None
        if bad:
            fails.append(rel)
        _tick()
        print("%-46s exit=%d  %s" % (os.path.basename(rel), p.returncode,
                                     verdict[:96]))
        if bad:
            for ln in tail[-25:]:
                print("        %s" % ln)

    # Node is a hard requirement rather than an optional extra: the page is part of
    # the product, and a suite that cannot run its subject must not report green.
    NODE = shutil.which("node")
    for rel in NODE_SUITES:
        path = os.path.join(ROOT, rel)
        if not NODE:
            fails.append(rel)
            print("%-46s SKIPPED  node was not found on PATH" % os.path.basename(rel))
            continue
        print("%-46s running" % os.path.basename(rel))
        p = subprocess.run([NODE, path], cwd=ROOT,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out = p.stdout.decode("utf-8", "replace")
        tail = [ln for ln in out.strip().splitlines() if ln.strip()]
        verdict = tail[-1] if tail else "(no output)"
        bad = p.returncode != 0 or _FAIL_RE.search(out) is not None
        if bad:
            fails.append(rel)
        _tick()
        print("%-46s exit=%d  %s" % (os.path.basename(rel), p.returncode,
                                     verdict[:96]))
        if bad:
            for ln in tail[-25:]:
                print("        %s" % ln)

    _stop(dev)

    print()
    # Say it again at the end: a file swapped mid-run explains reds that the
    # header could not have predicted.
    _report_data(data0)
    print()
    print("SUITES: %s" % ("ALL PASSED" if not fails else "FAILED -> %s" % fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
