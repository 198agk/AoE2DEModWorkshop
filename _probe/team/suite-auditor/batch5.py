# -*- coding: utf-8 -*-
"""Batch 5: mutations aimed at the intents the coverage map says are thin.

  tech.cost         -- the cost-slot SELECTOR (not just the label)
  tech.research_time-- the per-research-location fan-out
  unit.attack_class -- the kind selector (attack vs armour)
  tech.effect       -- the actual float32 write into the effects array

Usage: python batch5.py [label ...]
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
    ("m22_tech_effect_write_noop",
     "aoe2mod/tests/test_api.py",
     "aoe2mod/intent/compiler.py",
     '    buf[off:off + 4] = struct.pack("<f", row["stored"])',
     "    buf[off:off + 4] = data[off:off + 4]",
     "tech.effect: the edit is reported but the bytes are left as they "
     "were -- does the only registered suite that invokes tech.effect "
     "re-read the .dat, or does it trust the report?"),

    ("m23_cost_slot_type_ignored",
     "aoe2mod/tests/test_compiler.py",
     "aoe2mod/intent/compiler.py",
     '        if c.get("type") != want:',
     "        if False:",
     "tech.cost: _pick_cost_slot stops filtering by resource type, so the "
     "first slot of ANY type is chosen -- the classic 'wrong number, "
     "right-looking report' bug."),

    ("m24_research_location_single",
     "aoe2mod/tests/test_compiler.py",
     "aoe2mod/intent/compiler.py",
     '    locs = tech.get("research_locations") or ()',
     '    locs = (tech.get("research_locations") or ())[:1]',
     "tech.research_time: only the FIRST research-location copy is "
     "written; the record becomes self-contradictory.  edit_count for "
     "tech 12 should drop 2 -> 1."),

    ("m25_attack_class_kind_ignored",
     "aoe2mod/tests/test_compiler.py",
     "aoe2mod/intent/compiler.py",
     '        which = resolved.raw.get("kind", "attack")',
     '        which = "attack"',
     "unit.attack_class: the kind selector is ignored, so asking for "
     "melee armour edits the attack class instead."),
]


def run_one(label, suite, target, old, new, why):
    root = mutate.fresh(os.path.join(OUT, "run_" + label))
    try:
        mutate.patch(root, target, old, new)
        code, out = mutate.run(root, suite)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    log = os.path.join(OUT, label + ".log")
    with open(log, "w", encoding="utf-8", newline="") as fh:
        fh.write("SUITE: %s\nMUTATION: %s\nOLD: %r\nNEW: %r\nWHY: %s\n\n%s"
                 % (suite, target, old, new, why, out))
    lines = [x.rstrip() for x in out.strip().splitlines() if x.strip()]
    fails = [ln for ln in lines if "FAIL" in ln or "PROBLEM" in ln
             or "Traceback" in ln]
    rec = {"label": label, "suite": suite, "mutation": target,
           "exit": code, "fail_lines": len(fails),
           "tail": lines[-3:], "why": why}
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
    with open(os.path.join(OUT, "batch5.json"), "w", encoding="utf-8") as fh:
        json.dump(recs, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
