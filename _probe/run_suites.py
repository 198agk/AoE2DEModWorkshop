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
    r"^\s*FAILED:\s"                       # `FAILED: both halves stay in step`
    r"|^\s*FAILED\s+\S"                     # `FAILED %d check(s)` / `FAILED 3 CHECKS:`
    r"|\bFAILURES:\s*(?:\d|%[sdr])"          # `FAILURES: 1 -> [...]` / `FAILURES: %s`
    r"|^\s*FAIL(?:\s|:)(?!\s*[A-Z][A-Z0-9 _()/.-]{2,}:)"  # report, not a verdict
    r"|\bFAIL\s+[^\s]+\s*::"               # `FAIL name :: detail`
    r"|\bFAIL(?:ED|URE|URES)?\s*$"           # report ends the line
    r"|\bCHECK\(S\)\s+FAILED\b"            # `N CHECK(S) FAILED -> [...]`
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


def main():
    """Run every suite and return the exit status.

    Kept behind the guard below so this file can be imported: a probe
    that only wants `_FAIL_RE` or `SUITES` must not start a 131-suite
    run.  Learned on 2026-10-25 by doing exactly that.
    """
    for rel in SUITES:
        path = os.path.join(ROOT, rel)
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
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

    print()
    print("SUITES: %s" % ("ALL PASSED" if not fails else "FAILED -> %s" % fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
