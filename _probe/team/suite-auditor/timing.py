# -*- coding: utf-8 -*-
"""Time each candidate suite once against the pristine scratch copy."""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "scratch")
PY = sys.executable

CANDIDATES = [
    "aoe2mod/tests/test_buildpanel.py",
    "aoe2mod/tests/test_availability_intent.py",
    "aoe2mod/tests/test_civtechtrees.py",
    "aoe2mod/tests/test_emit_mod.py",
    "aoe2mod/tests/test_availability_e2e.py",
    "_probe/test_mechanism_gate.py",
    "_probe/test_dat_half_count.py",
    "_probe/test_reskin.py",
    "_probe/test_unit_sprite_chain.py",
    "_probe/test_panel_tree_agreement.py",
    "_probe/test_families.py",
    "_probe/test_donor_rule.py",
    "_probe/test_dat_layer_override.py",
    "_probe/test_tree_form.py",
    "_probe/test_linkedtechs_semantics.py",
    "_probe/test_declared_resources.py",
    "aoe2mod/tests/test_compiler.py",
]

env = dict(os.environ)
env["PYTHONIOENCODING"] = "utf-8"
env["PYTHONUTF8"] = "1"
env.pop("PYTHONPATH", None)

for rel in CANDIDATES:
    p = os.path.join(ROOT, rel.replace("/", os.sep))
    if not os.path.isfile(p):
        print("%-46s MISSING" % rel)
        continue
    t0 = time.time()
    r = subprocess.run([PY, "-X", "utf8", rel], cwd=ROOT, env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    dt = time.time() - t0
    out = r.stdout.decode("utf-8", "replace").strip().splitlines()
    tail = out[-1][:90] if out else ""
    print("%-46s %6.1fs exit=%d  %s" % (rel, dt, r.returncode, tail))
    sys.stdout.flush()
