# -*- coding: utf-8 -*-
"""Batch 3: writer mismatch accounting, int-delta arithmetic, sprite index,
buildpanel duplicate guard, and the mirror-slot contract.

Usage: python batch3.py [label ...]
"""
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mutate  # noqa: E402

OUT = os.path.join(HERE, "mutations")

MUTATIONS = [
    ("m16_writer_mismatch_silenced",
     "_probe/test_dat_edit_routes.py",
     "aoe2mod/dat/writer.py",
     "                self.mismatches += 1",
     "                self.mismatches += 0",
     "the writer stops counting model-vs-raw disagreements, so its "
     "self-report always claims the model reproduced the file"),

    ("m17_int_delta_broken_emit",
     "aoe2mod/tests/test_emit_mod.py",
     "aoe2mod/intent/compiler.py",
     '    new = (before + amount) if op == "delta" else amount',
     "    new = amount",
     "integer `delta` is treated as an absolute value (Archer attack 4 -> 2 "
     "instead of 4 -> 6)"),

    ("m18_sprite_byid_broken",
     "_probe/test_unit_sprite_chain.py",
     "aoe2mod/game/sprites.py",
     '                self._by_id.setdefault(g["id"], g)',
     '                self._by_id.setdefault(-1, g)',
     "record() no longer answers by graphic id, so every id lookup collapses "
     "onto one record"),

    ("m19_duplicate_insert_allowed",
     "aoe2mod/tests/test_buildpanel.py",
     "aoe2mod/game/buildpanel.py",
     "    if _entry_spans(text, arr_lo, arr_hi, node_id):",
     "    if False:",
     "insert_entry stops refusing a duplicate, so the same node can be listed "
     "twice in one building's array"),

    ("m20_mirror_slot_dropped",
     "aoe2mod/tests/test_compiler.py",
     "aoe2mod/intent/compiler.py",
     '        yield off, width, kind, "%s (mirror)" % label, 0, fb',
     "        continue",
     "the reverse-mirror walker emits nothing, so an edit to a raw attack slot "
     "leaves the displayed panel number stale"),
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
    with open(os.path.join(OUT, "batch3.json"), "w", encoding="utf-8") as fh:
        json.dump(recs, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
