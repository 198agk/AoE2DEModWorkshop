# -*- coding: utf-8 -*-
"""Run a batch of mutations: each one patches a COPY of aoe2mod, then runs one suite.

Usage:  python batch.py [label ...]        (no args = every mutation)
Read-only w.r.t. the real aoe2mod/: all edits land in mutations/run_<label>/.
"""
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mutate  # noqa: E402

OUT = os.path.join(HERE, "mutations")

# (label, suite, target_file, old, new, why)
MUTATIONS = [
    ("m01_verify_surgical_always_ok",
     "aoe2mod/tests/test_buildpanel.py",
     "aoe2mod/game/buildpanel.py",
     '    ok = info["outside_is_untouched"]',
     "    ok = True",
     "verify_surgical's verdict forced True: is any caller's `ok is True` "
     "assertion able to fail?"),

    ("m02_remove_counts_twice",
     "aoe2mod/tests/test_buildpanel.py",
     "aoe2mod/game/buildpanel.py",
     "        removed += 1",
     "        removed += 7",
     "remove_entry over-reports what it removed"),

    ("m03_grant_appends_twice",
     "aoe2mod/tests/test_availability_e2e.py",
     "aoe2mod/game/civtechtrees.py",
     '    tree.setdefault(UNITS_KEY, []).append(row)\n    return row, warnings',
     '    tree.setdefault(UNITS_KEY, []).append(row)\n'
     '    tree.setdefault(UNITS_KEY, []).append(row)\n    return row, warnings',
     "a grant that adds TWO rows instead of one"),

    ("m04_button_byte_noop",
     "_probe/test_dat_half_count.py",
     "aoe2mod/intent/datgrant.py",
     "    patched[boff] = slot",
     "    patched[boff] = bbefore",
     "the training-button byte write becomes a no-op, so the recipe reports "
     "an edit it did not make"),

    ("m05_grid_never_reported",
     "_probe/test_reskin.py",
     "aoe2mod/game/sprites.py",
     "        if a and b and a != b:",
     "        if False:",
     "grid_mismatches stops reporting any frame-grid change"),

    ("m06_can_build_always_true",
     "_probe/test_mechanism_gate.py",
     "aoe2mod/game/civtechtrees.py",
     '    return st is not None and st != "NotAvailable"',
     "    return True",
     "can_build says every civ can build every node"),

    ("m07_verify_files_always_ok",
     "_probe/test_reskin.py",
     "aoe2mod/intent/reskin.py",
     '    rep["ok"] = not (rep["absent_targets"] or rep["not_the_donor"])',
     '    rep["ok"] = True',
     "reskin.verify_files certifies a payload without checking it"),

    ("m08_tree_serialize_reflows",
     "aoe2mod/tests/test_availability_e2e.py",
     "aoe2mod/game/civtechtrees.py",
     '    return text.encode("utf-8")',
     '    return (text + "\\n").encode("utf-8")',
     "the tree serialiser appends a byte the caller did not ask for"),

    ("m09_carrier_flag_always_true",
     "aoe2mod/tests/test_availability_e2e.py",
     "aoe2mod/mod/emitter.py",
     '        "dat_is_carrier": dat_carrier,',
     '        "dat_is_carrier": True,',
     "every emitted mod claims its .dat is an unmodified carrier"),

    ("m10_dat_identical_flag",
     "aoe2mod/tests/test_availability_intent.py",
     "aoe2mod/mod/emitter.py",
     '    manifest["changes_dat"] = False if dat_carrier else (dat_bytes is not None)',
     '    manifest["changes_dat"] = False',
     "the manifest always denies changing the .dat"),
]


def run_one(label, suite, target, old, new, why):
    root = mutate.fresh(os.path.join(OUT, "run_" + label))
    try:
        if target != "-":
            mutate.patch(root, target, old, new)
        code, out = mutate.run(root, suite)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    log = os.path.join(OUT, label + ".log")
    with open(log, "w", encoding="utf-8", newline="") as fh:
        fh.write("SUITE: %s\nMUTATION: %s\nOLD: %r\nNEW: %r\nWHY: %s\n\n%s"
                 % (suite, target, old, new, why, out))
    lines = [x.rstrip() for x in out.strip().splitlines() if x.strip()]
    fails = [ln for ln in lines if "FAIL" in ln]
    rec = {"label": label, "suite": suite, "mutation": target,
           "exit": code, "fail_lines": len(fails),
           "tail": lines[-2:], "why": why}
    print(json.dumps(rec, ensure_ascii=False))
    sys.stdout.flush()
    return rec


def main():
    want = set(sys.argv[1:])
    os.makedirs(OUT, exist_ok=True)
    recs = []
    for m in MUTATIONS:
        if want and m[0] not in want:
            continue
        recs.append(run_one(*m))
    with open(os.path.join(OUT, "batch.json"), "w", encoding="utf-8") as fh:
        json.dump(recs, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
