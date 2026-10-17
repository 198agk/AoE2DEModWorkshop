"""How does a civilization actually GET its starting resources?

`probe_civ_resources.py` proved the civ `resources` array is a real, named,
correctly-indexed surface -- but indices 91..94 (`Starting Food/Wood/Stone/Gold`)
are **0.0 in all 63 civs**.  So if a player asks "give the Britons 500 extra
starting food", editing the array is not the answer.  Where is it?

The two candidate mechanisms in this data format:
  1. a tech effect command with `Resource Modifier (Set/+/-)` targeting resource
     91..94, granted to the civ by its free/first tech, or
  2. something outside the .dat entirely (map defaults).

This walks every effect command in the shipped data, keeps the ones whose
attribute is 91..94, and prints the owning tech plus whether it is a starting
grant.  The answer decides whether the product can already do the feature with
the EXISTING `tech.effect` intent (in which case nothing new is needed) or
whether it needs a new binding.
"""
import os
import sys
from collections import Counter

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import aoe2mod.api as A                                   # noqa: E402
import aoe2mod.intent.compiler as C                        # noqa: E402
from aoe2mod.dat import parser as P                        # noqa: E402
from aoe2mod.semantic.index import index as semantic_index   # noqa: E402

START = {91: "Starting Food", 92: "Starting Wood",
         93: "Starting Stone", 94: "Starting Gold"}


def main():
    tk = A.open_toolkit()
    tk._ensure()
    p = P.Parser(tk._raw)
    p.parse()
    effects = p.stats["effects"]
    techs = p.stats["techs"]
    ix = semantic_index()

    # Which tech points at which effect, so a hit can name its owner.
    owner = {}
    for ti, t in enumerate(techs):
        eid = t.get("effect_id")
        if eid is not None and eid >= 0:
            owner.setdefault(eid, []).append(ti)

    hits = Counter()
    rows = []
    for ei, eff in enumerate(effects):
        for ci, cmd in enumerate(eff.get("commands") or ()):
            # cmd = [type, a, b, c, d] (attribute is cmd[2] for the modifier types)
            if len(cmd) < 4:
                continue
            ctype, a, b = cmd[0], cmd[1], cmd[2]
            attr = cmd[2]
            # Attribute Modifier (Set/+/-) = 0/4, Multiply = 5, Resource
            # Modifier = 1.  Only the resource-targeting families can grant
            # starting resources, but scan for the resource id in any slot so a
            # missed encoding shows up instead of hiding.
            if attr not in START and cmd[2] != attr:
                pass
            if attr in START or (ctype == 1 and cmd[2] in START):
                for ti in owner.get(ei, []):
                    name = ix.get("tech", ti).display if ix.get("tech", ti) else ti
                    rows.append((ti, name, ei, ci, ctype, START[attr], list(cmd)))
                    hits[attr] += 1

    print("effect commands anywhere that mention a starting-resource id:")
    if not rows:
        print("  (none -- starting resources are NOT set by any effect command)")
    for r in rows[:40]:
        print("  tech[%d] %-28s effect %d cmd %d type %d -> %s  %s"
              % (r[0], r[1], r[2], r[3], r[4], r[5], r[6]))
    print("")
    print("hits per starting resource: %s" % dict(hits))
    print("")

    # And the other direction: which effects target ANY of the 91..94 slots at
    # all, regardless of command type (in case the modifier is encoded with the
    # resource in a different position).
    loose = Counter()
    for ei, eff in enumerate(effects):
        for cmd in eff.get("commands") or ():
            for slot in range(len(cmd)):
                v = cmd[slot]
                if isinstance(v, int) and v in START:
                    loose[(slot, v)] += 1
    print("any-slot mentions of 91..94 (slot index, resource id) -> count:")
    for k, v in sorted(loose.items()):
        print("  slot %d resource %d (%s): %d" % (k[0], k[1], START[k[1]], v))
    print("")

    # Cross-check with the civ array: is index 84 (Starting Villagers) the only
    # starting-* slot that is actually populated?
    civs = p.stats["civs"]
    populated = sorted({i for c in civs for i, v in enumerate(c["resources"])
                        if v and (80 <= i <= 95)})
    print("non-zero civ-array indices in the 80..95 'starting' neighbourhood: %s"
          % [(i, civs[0]["resources"][i]) for i in populated])
    return 0


if __name__ == "__main__":
    sys.exit(main())
