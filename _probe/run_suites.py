# -*- coding: utf-8 -*-
"""Run the fast product suites and print a one-line verdict for each."""
import os
import re
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
    r"_probe\test_reskin.py",
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

print()
print("SUITES: %s" % ("ALL PASSED" if not fails else "FAILED -> %s" % fails))
sys.exit(1 if fails else 0)
