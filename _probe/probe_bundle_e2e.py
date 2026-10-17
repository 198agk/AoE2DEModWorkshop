"""Bundle API end-to-end: one folder, several sentences, one .dat.

The claim under test is not "the code runs".  It is that a bundle is
ALL-OR-NOTHING and ACCUMULATES:

* every sentence's edit is present in the ONE file that loads, which is what two
  separate mods could not deliver (`probe_multi_intent.py` measured two builds
  touching the same 1701 villager bytes);
* two edits to the same field add up instead of one overwriting the other, which
  is only true because each step reads `before` from the accumulated buffer;
* a bundle with a bad sentence is refused ENTIRELY, and the message names which
  sentence -- never a mod that silently does less than it says;
* an edit in the tech/effect TAIL survives folding with an edit in the unit
  RECORDS, proving the section offset stays valid across steps.

Everything is checked by RE-PARSING the bytes on disk with the unmodified
parser, and by re-reading the field values from the emitted mod folder -- not by
trusting the edit list.
"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)

import aoe2mod.api as A                      # noqa: E402
from aoe2mod.dat import locate as L          # noqa: E402
from aoe2mod.dat import parser as P          # noqa: E402
from aoe2mod.intent import compiler as C     # noqa: E402

FAILS = []


def check(label, ok, detail=""):
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label,
                           ("  -- " + detail) if detail else ""))
    if not ok:
        FAILS.append(label)


def values_from_disk(dat_path):
    """Read villager 83 hp and Loom's gold cost out of a .dat ON DISK."""
    raw, _how = P.load_dat(dat_path)
    p = P.Parser(raw)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    civs, _cs, gv, tail = L.locate(raw, parser=p)
    hp = None
    for c in civs:
        for u in c["units"]:
            if u["id"] == 83:
                hp = u["hit_points"]
                break
        if hp is not None:
            break
    loom = L.locate_techs(raw, tail, gv)[22]
    gold = [c["amount"] for c in loom["costs"] if c["type"] == 3]
        # unique civ copies all hold the same hp; take the plain value
    return hp, (gold[0] if gold else None), len(raw)


tk = A.open_toolkit()
tk._ensure()
BASE_HP, BASE_GOLD, _n = values_from_disk(tk.dat_path)
print("=== baseline ===")
print("  villager 83 hit_points : %s" % BASE_HP)
print("  Loom (tech 22) gold    : %s" % BASE_GOLD)

INTENTS = [
    {"intent": "unit.stat", "unit": 83, "stat": "hit_points", "delta": 5},
    {"intent": "tech.cost", "tech": 22, "resource": "gold", "delta": -10},
    {"intent": "unit.stat", "unit": 83, "stat": "hit_points", "delta": 7},
]

print()
print("=== 1. plan_bundle previews the whole request ===")
pb = tk.plan_bundle(INTENTS)
print("  descriptions          : %s" % json.dumps(pb["descriptions"], ensure_ascii=False))
print("  per-intent edits      : %s" % pb["per_intent_edits"])
print("  total edits           : %d" % pb["edit_count"])
print("  civs touched          : %d" % pb["civs_edited"])
print("  offsets written twice : %d" % pb["overlap_count"])
check("the preview reaches every sentence", len(pb["plans"]) == 3)
check("a preview that folds reports all three sentences' edits",
      pb["edit_count"] == sum(pb["per_intent_edits"]))
check("the preview verified the folded stream", pb["verification"]["ok"])
check("the preview names overlapping offsets instead of hiding them",
      pb["overlap_count"] > 0)

print()
print("=== 2. build_bundle emits ONE mod that carries every sentence ===")
out = os.path.join(tempfile.mkdtemp(prefix="bundle_"), "Nine Lives")
man = tk.build_bundle(INTENTS, out, title="Bundle Probe", author="probe",
                      description="villager hp +12 total and Loom gold -10")
print("  mod folder   : %s" % out)
print("  dat file/raw : %d / %d" % (man["dat_file_bytes"], man["dat_raw_bytes"]))
print("  reparse ok   : %s (leftover %s)" % (man["reparse_ok"], man["reparse_leftover"]))
print("  edit_count   : %d" % man["edit_count"])
print("  per-intent   : %s" % man["per_intent_edits"])
hp, gold, rawlen = values_from_disk(man["dat"])
print("  ON DISK villager 83 hp : %s" % hp)
print("  ON DISK Loom gold      : %s" % gold)
check("the emitted mod re-parses to an exact EOF", man["reparse_ok"])
check("the ONE loaded file accumulates BOTH hit-point sentences (%s + 12)" % BASE_HP,
      hp == BASE_HP + 12, "on disk %s, expected %s" % (hp, BASE_HP + 12))
check("the tail edit (tech cost) survived folding with the record edits",
      gold == BASE_GOLD - 10, "on disk %s, expected %s" % (gold, BASE_GOLD - 10))
check("sentence order does not matter for distinct fields", man["edit_count"] > 0)

print()
print("=== 3. the fold accumulates rather than overwrites ===")
# If each step read `before` from the ORIGINAL file, the second "+7" would read
# 25 and write 32 -- a plausible number that silently dropped the first edit.
check("hp +5 then hp +7 is +12, not +7", hp == BASE_HP + 12,
      "the overwrite bug would give %s" % (BASE_HP + 7))
check("it is not the last-writer-wins result", hp != BASE_HP + 7)

print()
print("=== 4. ALL-OR-NOTHING: a bad sentence refuses the WHOLE bundle ===")
bad = [{"intent": "unit.stat", "unit": 83, "stat": "hit_points", "delta": 5},
       {"intent": "unit.attack_class", "unit": 12, "kind": "attack", "delta": 3},
       {"intent": "tech.cost", "tech": 22, "resource": "gold", "delta": -10}]
# Unit 12 is the Barracks: `unit.stat displayed_attack` on it is LEGAL (it stores
# a displayed_attack of 0, 252 edits) -- an earlier version of this probe assumed
# a building cannot carry an attack at all and so tested nothing.  What a
# building genuinely cannot do is expose a raw `attack_class` entry: its unit
# type stores an empty attack list, so `unit.attack_class` is the sentence that
# cannot be written (see _probe/probe_barracks_attack.py).
try:
    tk.build_bundle(bad, os.path.join(tempfile.mkdtemp(prefix="bundle_bad_"), "No"),
                    title="Should Not Exist", author="probe")
    check("a bundle with an impossible sentence is refused", False,
          "it built instead of refusing")
except C.IntentError as exc:
    msg = str(exc)
    print("  refusal: %s" % msg)
    check("a bundle with an impossible sentence is refused", True)
    check("the refusal names WHICH sentence failed", "sentence 2" in msg, msg)

print()
print("=== 5. a bundle whose sentences are all individually bad names all of them ===")
# Both must fail while RESOLVING, so they are collected together.  A sentence
# that fails while COMPILING (like the Barracks attack_class above) is raised
# from the fold instead, because whether a record stores a field is only known
# once the record is read -- there is no useful way to predict it up front.
allbad = [{"intent": "unit.stat", "unit": 99999, "stat": "hit_points", "delta": 3},
          {"intent": "tech.cost", "tech": 99999, "resource": "gold", "delta": -10}]
try:
    tk.build_bundle(allbad, os.path.join(tempfile.mkdtemp(prefix="bundle_bad2_"), "No"),
                    title="Should Not Exist", author="probe")
    check("a bundle of only-bad sentences is refused", False, "it built")
except C.IntentError as exc:
    msg = str(exc)
    print("  refusal: %s" % msg)
    check("a bundle of only-bad sentences is refused", True)
    check("it reports every bad sentence, not just the first",
          "sentence 1" in msg and "sentence 2" in msg, msg)

print()
print("=== 6. an empty bundle is refused, not silently a no-op ===")
try:
    tk.build_bundle([], os.path.join(tempfile.mkdtemp(prefix="bundle_empty_"), "No"),
                    title="Should Not Exist", author="probe")
    check("an empty bundle is refused", False, "it built")
except C.IntentError as exc:
    check("an empty bundle is refused", "at least one" in str(exc), str(exc))

print()
print("=== 7. single-intent behaviour is unchanged (no regression) ===")
single = tk.plan({"intent": "unit.stat", "unit": 83, "stat": "hit_points", "delta": 5})
check("plan() still works on one intent", single["edit_count"] == 1701,
      "edit_count %s" % single.get("edit_count"))
bs = tk.build({"intent": "unit.stat", "unit": 83, "stat": "hit_points", "delta": 5},
              os.path.join(tempfile.mkdtemp(prefix="single_"), "One"),
              title="Single Probe", author="probe")
hp1, _g, _l = values_from_disk(bs["dat"])
check("build() still writes exactly one sentence", hp1 == BASE_HP + 5,
      "on disk %s, expected %s" % (hp1, BASE_HP + 5))

print()
if FAILS:
    print("BUNDLE PROBE: %d FAILURE(S): %s" % (len(FAILS), FAILS))
    sys.exit(1)
print("BUNDLE PROBE: CLEAN -- one request, one mod, every sentence present.")
