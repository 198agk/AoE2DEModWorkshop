"""How much of the effect space does `tech.effect` currently refuse, and how
much of that refusal is the Resource Modifier family?

`probe_start_res_e2e.py` found that every civilization's starting-resource bonus
is a `Resource Modifier (Set/+/-)` command (type 1), and that `tech.effect`
REFUSES all of them: `_EFFECT_OPERATION` (compiler.py:145) lists only the 21
attribute-modifier command types (0/4/5 and their 10/20/30/40/200/203 scoped
variants), so a type-1 command falls through to
"command type 1 does not carry an attribute; its parameters have their own
meaning" -- the wording as it read BEFORE the sentence was fixed to name the
command ("资源修改器 (Set/+/-) does not carry an attribute..."); `probe_refusal_
reasons.py` matches on the unchanged tail, so the classification still holds.

That refusal was CORRECT as written -- a resource modifier really does not carry
an attribute -- but it meant a whole family the UI can list was unwritable.  Before
proposing a fix, measure the size of the family: how many commands, how many
techs, and what the non-editable remainder consists of.  A gap worth 3 commands
is a footnote; a gap worth a thousand is a feature.

STATUS: the measurement came back 236 type-1 + 117 type-6 commands, 142 techs
with nothing else editable, so the family was implemented (`_RESOURCE_SCOPE` /
`_RESOURCE_CHANGE` / `_RESOURCE_MULTIPLY` in `aoe2mod/intent/compiler.py`, and the
`resource` flag on an `effect_rows` row).  Re-running this file now reports the
POST-fix numbers: editable rises from 6,260 to 6,599 and the type-1/type-6
"refused" buckets split into editable / refused-irregular.  The historical
figures quoted above are what the design was sized against.
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


def main():
    tk = A.open_toolkit()
    tk._ensure()
    raw = tk._raw
    tail, gv = tk._parsed[4], tk._parsed[3]
    # Use the LOCATOR's records, not the raw parser stats: effect_rows() wants
    # the dict-shaped command records the locator emits (the parser's own
    # `stats["effects"]` holds tuples).  This is the same pair of calls
    # sweep_tech_effect.py makes.
    techs = L.locate_techs(raw, tail, gv)
    effects, effects_start = L.locate_effects(raw)
    tables = C.load_effect_tables()
    types = tables["types"].get("types") or {}
    labels = C.load_resource_labels()

    total = Counter()
    editable = Counter()
    non_editable_by_type = Counter()
    resource_rows = []
    techs_with_resource_cmd = set()

    for ti, t in enumerate(techs):
        for row in C.effect_rows(effects, t, ix=None):
            ty = row["type"]
            total[ty] += 1
            if row["editable"]:
                editable[ty] += 1
            else:
                non_editable_by_type[ty] += 1
    grand_total = sum(total.values())
    grand_editable = sum(editable.values())
    print("effect commands across all %d techs : %d" % (len(techs), grand_total))
    print("  currently editable                 : %d (%.1f%%)"
          % (grand_editable, 100.0 * grand_editable / grand_total))
    print("  currently refused                  : %d (%.1f%%)"
          % (grand_total - grand_editable,
             100.0 * (grand_total - grand_editable) / grand_total))
    print("")

    print("refused commands, grouped by command type:")
    for ty, n in non_editable_by_type.most_common():
        lab = (types.get(str(ty)) or {}).get("label") or ("Type %d" % ty)
        params = (types.get(str(ty)) or {}).get("params")
        print("  type %-4d %-34s %5d   params=%s" % (ty, lab, n, params))
    print("")

    # The Resource Modifier family specifically.
    for ty in (1, 6):
        n = total.get(ty, 0)
        print("type %d (%s): %d commands total" % (
            ty, (types.get(str(ty)) or {}).get("label"), n))
        # what resources do they target, and are those resources nameable?
        targets = Counter()
        unnamed = 0
        for ti, t in enumerate(techs):
            for row in C.effect_rows(effects, t, ix=None):
                if row["type"] != ty:
                    continue
                a = row["raw"][1]
                targets[a] += 1
                if a not in labels:
                    unnamed += 1
        named = sum(v for k, v in targets.items() if k in labels)
        print("   distinct target resource ids: %d, commands %d"
              % (len(targets), sum(targets.values())))
        print("   target ids the game names   : %d commands (%.1f%%)"
              % (named, 100.0 * named / max(1, sum(targets.values()))))
        print("   target ids with NO name     : %d commands" % unnamed)
        print("   top targets: %s"
              % [(k, labels.get(k, "type %d" % k), v)
                 for k, v in targets.most_common(12)])
        print("")

    # Which techs would gain an editable command?  That is the number of new
    # things the UI could offer.
    gained = []
    for ti, t in enumerate(techs):
        rows = C.effect_rows(effects, t, ix=None)
        if any(r["type"] in (1, 6) for r in rows) and not any(r["editable"] for r in rows):
            gained.append(ti)
    print("techs with NO editable command today that a resource-modifier fix "
          "would make editable: %d" % len(gained))
    print("  first 20: %s" % gained[:20])
    return 0


if __name__ == "__main__":
    sys.exit(main())
