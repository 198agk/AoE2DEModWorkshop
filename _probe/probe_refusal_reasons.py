"""Why is each refused effect command refused?  Two different causes, and they
must not be conflated.

`probe_effect_type_gap.py` found 1,745 refused commands out of 8,005.  The bulk
is the Resource Modifier family (type 1/6 and their scoped variants), which
`_EFFECT_OPERATION` does not list at all.  But 160 of the refusals are type
0/4/5 -- attribute modifiers that ARE in the table -- so they must be refused
for the other reason: `attribute_label` is empty, i.e. the attribute id has no
name in `effect_attributes.json`.

Those two causes call for opposite responses.  The first is a missing FEATURE
(the family is well-understood, just unwired).  The second is missing DATA (the
table is honest about being incomplete for DE) and must stay a refusal, because
naming an unknown attribute would be inventing one.

Also measures the three design questions for wiring resource modifiers at all:
  1. What is `C` (times-resource)?  A command with C != -1 scales its amount by
     another resource, so a plain delta is not the whole story.
  2. What is `B`?  0=set, 1=change.  A "set" has no meaningful delta; the
     `tech.effect` intent already carries both `delta` and `value`, so the split
     must be by B, not by guessing.
  3. Does D hold a plain float32 for these types (same byte offset as the
     attribute modifiers)?
"""
import os
import sys
from collections import Counter

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import aoe2mod.api as A                                          # noqa: E402
import aoe2mod.intent.compiler as C                               # noqa: E402
from aoe2mod.dat import locate as L                               # noqa: E402

RESOURCE_TYPES = (1, 6, 11, 16, 21, 26, 31, 36, 41, 46)


def main():
    tk = A.open_toolkit()
    tk._ensure()
    raw = tk._raw
    tail, gv = tk._parsed[4], tk._parsed[3]
    techs = L.locate_techs(raw, tail, gv)
    effects, _ = L.locate_effects(raw)

    by_reason = Counter()
    unnamed_attrs = Counter()
    refused_types = Counter()
    for t in techs:
        for row in C.effect_rows(effects, t, ix=None):
            if row["editable"]:
                continue
            reason = row["reason"] or ""
            if "does not carry an attribute" in reason:
                by_reason["type not in the operation table"] += 1
                refused_types[row["type"]] += 1
            elif "has no name in the effect attribute table" in reason:
                by_reason["attribute id has no name"] += 1
                unnamed_attrs[row["attribute"]] += 1
            else:
                by_reason["other: %s" % reason] += 1

    print("=== refusals by reason ===")
    for r, n in by_reason.most_common():
        print("  %-38s %5d" % (r, n))
    print("")
    # This check read `set(refused_types) <= set(_EFFECT_OPERATION_TYPES)` until
    # the 160 unnamed-attribute refusals were unlocked -- i.e. it asserted the
    # exact condition the fix removes, so it can only print a stale False now.
    # The post-fix invariant is the opposite one: NO attribute-modifier command
    # (type 0 or its 4/5/10/14/... scoped variants) may be refused any more, for
    # ANY reason.  Keep the type list so the assertion still means something.
    _attr_refused = sorted(set(refused_types) & set(_EFFECT_OPERATION_TYPES))
    print("attribute-modifier types (0/4/5 and the 21 scoped ids) still "
          "refused: %s" % (_attr_refused or "none",))
    print("  refused types present: %s" % sorted(refused_types))
    print("  unnamed attribute ids : %s"
          % [(k, v) for k, v in unnamed_attrs.most_common(12)])
    print("")

    # ---- design questions about the resource-modifier family --------------
    b_hist = Counter()
    c_hist = Counter()
    d_is_integral = 0
    d_total = 0
    a_is_named = Counter()
    labels = C.load_resource_labels()
    for t in techs:
        for row in C.effect_rows(effects, t, ix=None):
            if row["type"] not in RESOURCE_TYPES:
                continue
            _ty, a, b, cc, d = row["raw"]
            b_hist[(row["type"], b)] += 1
            c_hist[cc] += 1
            d_total += 1
            if d is not None and float(d) == int(d):
                d_is_integral += 1
            a_is_named[(a in labels)] += 1

    print("=== design questions ===")
    print("(B) set/change field, per type:")
    for (ty, b), n in sorted(b_hist.items()):
        print("    type %-3d B=%-4s %4d" % (ty, b, n))
    print("(C) times-resource: %s" % (c_hist.most_common(8),))
    print("    commands with C == -1 : %d" % (c_hist.get(-1, 0),))
    print("    commands with C != -1 : %d" % (sum(v for k, v in c_hist.items()
                                                 if k != -1),))
    print("(D) integral values     : %d / %d" % (d_is_integral, d_total))
    print("(A) target id named by the game's table: %s"
          % {("named" if k else "NOT named"): v for k, v in a_is_named.items()})
    return 0


_EFFECT_OPERATION_TYPES = (0, 4, 5, 10, 14, 15, 20, 24, 25, 30, 34, 35, 40, 44,
                           45, 200, 201, 202, 203, 204, 205)


if __name__ == "__main__":
    sys.exit(main())
