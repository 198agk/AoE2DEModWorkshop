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

# A word-boundary match, so an identifier like IDS_FAILED_TO_OPEN_FILE does not
# count as a failure report.
_FAIL_RE = re.compile(r"\bFAIL(?:ED|URE)?\b")

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
    r"_probe\test_mod_load_timing.py",
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
    r"_probe\probe_build_panel_gate.py",
    r"_probe\test_dat_layer_override.py",
    r"_probe\test_enabling_research.py",
    r"_probe\test_civ_unit_gate.py",
    r"_probe\test_overlay_depth.py",
    r"_probe\test_tree_form.py",
    r"_probe\test_dat_json_override.py",
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
    # The registry itself.  Ten probes rotted unrun before anyone noticed, and
    # the reason nobody noticed is that "is every test reachable?" was a question
    # only a human could answer.  This asks it mechanically, including the four
    # files that are named test_* but are measurements -- declared, with reasons,
    # and checked for staleness.
    r"_probe\probe_suite_registry.py",
]

# Suites that are not Python.  The screen's script is JavaScript and no Python
# test can execute it: `test_ui_server.py` calls the same App the page calls and
# stayed green through two shipped page defects -- a refusal counted as buildable,
# and then a ReferenceError on every render.  Run it where it actually runs.
NODE_SUITES = [
    r"_probe\ui_page_harness.js",
]

fails = []
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
    print("%-46s exit=%d  %s" % (os.path.basename(rel), p.returncode,
                                 verdict[:96]))
    if bad:
        for ln in tail[-25:]:
            print("        %s" % ln)

print()
print("SUITES: %s" % ("ALL PASSED" if not fails else "FAILED -> %s" % fails))
sys.exit(1 if fails else 0)
