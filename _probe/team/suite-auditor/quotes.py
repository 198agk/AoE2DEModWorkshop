# -*- coding: utf-8 -*-
"""Print the exact verbatim lines behind each static finding, with file:line."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))

# (file, line, how many lines of context around)
SPOTS = [
    ("_probe/test_panel_edit.py", 73),
    ("_probe/probe_bundle_dat_half.py", 132),
    ("_probe/probe_bundle_dat_half.py", 140),
    ("_probe/probe_install_safety.py", 156),
    ("_probe/probe_install_safety.py", 157),
    ("_probe/probe_install_safety.py", 159),
    ("_probe/test_dat_json_override.py", 91),
    ("_probe/test_dat_json_override.py", 165),
    ("_probe/test_mod_load_timing.py", 140),
    ("_probe/test_time_gate_and_tooltip.py", 138),
    ("_probe/test_time_gate_and_tooltip.py", 146),
    ("_probe/test_smoke6_result.py", 113),
    ("_probe/test_smoke6_result.py", 211),
    ("_probe/test_zero_mod_experiment.py", 268),
    ("_probe/test_protocol_subjects.py", 257),
    ("aoe2mod/tests/test_buildpanel.py", 96),
    ("aoe2mod/tests/test_buildpanel.py", 98),
    ("aoe2mod/game/buildpanel.py", 447),
    ("aoe2mod/game/buildpanel.py", 481),
    ("aoe2mod/game/buildpanel.py", 484),
    ("aoe2mod/tests/test_buildpanel.py", 74),
    ("aoe2mod/tests/test_buildpanel.py", 107),
    ("_probe/test_panel_wire.py", 95),
    ("_probe/test_smoke5_design.py", 58),
    ("_probe/test_smoke5_design.py", 60),
    ("_probe/test_smoke5_design.py", 61),
    ("aoe2mod/tests/test_product_v7_recipe.py", 73),
    ("aoe2mod/tests/test_product_v7_recipe.py", 75),
    ("_probe/test_panel_tree_agreement.py", None),
    ("_probe/test_enabling_research.py", 71),
    ("_probe/test_revoke_is_not_enough.py", 118),
    ("aoe2mod/tests/test_api.py", 590),
    ("aoe2mod/tests/test_api.py", 604),
]

cache = {}
for rel, ln in SPOTS:
    p = os.path.join(ROOT, rel)
    if not os.path.isfile(p):
        print("MISSING %s" % rel)
        continue
    if p not in cache:
        with open(p, encoding="utf-8", errors="replace") as fh:
            cache[p] = fh.read().splitlines()
    lines = cache[p]
    if ln is None:
        # print every line containing 'len(mt) == 3'
        for i, s in enumerate(lines, 1):
            if "len(mt) == 3" in s:
                print("%s:%d: %s" % (rel, i, s.strip()))
        continue
    if ln > len(lines):
        print("OUT OF RANGE %s:%d (file has %d lines)" % (rel, ln, len(lines)))
        continue
    print("%s:%d: %s" % (rel, ln, lines[ln - 1].strip()))
