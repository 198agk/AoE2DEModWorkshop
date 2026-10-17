"""Is `unit 12 (Barracks) displayed_attack` really impossible?

`probe_bundle_e2e.py` case 4 assumed it was: an earlier round established that a
building has no attack, and `plan()` refuses `unit.attack_class` on a Barracks
with "兵营 has no 基础攻击 field to change (its unit type does not store one)".

But a bundle containing that sentence BUILT instead of refusing, which means one
of two things, and they are very different:

(A) Barracks really does carry an attack entry, and my test picked a legal
    sentence while believing it was illegal.  Then the test is wrong and the
    product is fine -- but `describe()` must AGREE that the field is editable.
(B) `plan()` refuses it while `compile_edits` writes it.  Then the two paths
    disagree about the same field in the DANGEROUS direction (preview says no,
    write says yes), which is the mirror image of the defect this codebase has
    already fixed three times.

Never assume which.  Ask both paths the same question and compare.
"""
import contextlib
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)

import aoe2mod.api as A                      # noqa: E402
from aoe2mod.intent import compiler as C     # noqa: E402

tk = A.open_toolkit()
tk._ensure()

INTENT = {"intent": "unit.stat", "unit": 12, "stat": "displayed_attack", "delta": 3}
ATTACK_INTENT = {"intent": "unit.attack_class", "unit": 12, "kind": "attack",
                 "delta": 3}

print("=== what describe() says about Barracks (unit 12) ===")
d = tk.describe(12)
print("  name        : %s" % d["name"])
print("  stats keys  : %s" % sorted(d["stats"].keys()))
print("  has displayed_attack : %s" % ("displayed_attack" in d["stats"]))
for key in ("displayed_attack", "displayed_melee_armour", "hit_points"):
    print("  %-22s: %r" % (key, d["stats"].get(key)))

print()
print("=== what plan() says ===")
for label, it in (("unit.stat displayed_attack", INTENT),
                  ("unit.attack_class attack", ATTACK_INTENT)):
    try:
        p = tk.plan(dict(it))
        print("  %-28s PLANNED  edit_count=%s description=%r"
              % (label, p.get("edit_count"), p.get("description")))
    except C.IntentError as exc:
        print("  %-28s REFUSED  %s" % (label, exc))

print()
print("=== what compile_edits actually does ===")
schema, bindings = C.load_schema()
data, civs, _cs, gv, tail, _how = tk._parsed
for label, it in (("unit.stat displayed_attack", INTENT),
                  ("unit.attack_class attack", ATTACK_INTENT)):
    try:
        r = C.resolve(dict(it), schema, bindings=bindings)
        patched, edits = C.compile_edits(data, civs, r, bindings, schema,
                                         tail=tail, gv=gv, stats=tk._stats,
                                         game_root=tk.game_root)
        print("  %-28s WROTE    %d edit(s)" % (label, len(edits)))
        for e in edits[:3]:
            print("      %s: %s -> %s" % (e.where, e.before, e.after))
    except C.IntentError as exc:
        print("  %-28s REFUSED  %s" % (label, exc))

print()
print("=== does the Barracks record really carry an attack entry? ===")
from aoe2mod.dat import locate as L          # noqa: E402
for ci, cname, u in L.find_units(civs, 12)[:1]:
    row = dict(u)
    print("  civ %d %s  type=%s class=%s hp=%s"
          % (ci, cname, row.get("type"), row.get("class"), row.get("hit_points")))
    for k in ("attacks", "armours", "displayed_attack", "displayed_melee_armour"):
        print("  %-22s: %r" % (k, row.get(k)))
