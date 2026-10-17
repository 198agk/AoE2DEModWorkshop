"""Can the product say WHICH civilization a starting-resource bonus belongs to?

`probe_start_grant_rows.py` found the grants (effect commands of type 1 whose
slot A is resource 91..94) and named their owning techs, but the tech names are
`C-Bonus, +50f +50w` -- they do not say whose bonus it is.  A UI that offers
"give the Britons +50 starting food" needs the civ.

`walk_tech` records `t["civ"] = r.i16()` (locate.py:333).  If that is a civ
index, the link exists and the feature is a naming problem, not a data problem.
If it is -1/0 for all of them, the bonuses are attached to civs some other way
(the CivTechTrees json, or the free-tech list) and the tool must go look there.

Also prints the tech's research cost/flag, because a starting bonus should be a
FREE, auto-granted tech -- if these cost resources or need prerequisites, they
are ordinary researchable bonuses that happen to touch a starting resource.
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import aoe2mod.api as A                                          # noqa: E402
from aoe2mod.dat import parser as P                               # noqa: E402
from aoe2mod.dat import locate as L                               # noqa: E402
from aoe2mod.semantic.index import index as semantic_index        # noqa: E402

CIV_TECHS = [223, 224, 225, 226, 227, 228, 1394]


def main():
    tk = A.open_toolkit()
    tk._ensure()
    p = P.Parser(tk._raw)
    p.parse()
    techs = p.stats["techs"]
    parsed = tk._parsed
    located = L.locate_techs(tk._raw, parsed[4], parsed[3])
    ix = semantic_index()

    # The dat's own civ order, so a civ index can be named.
    civ_names = [c["name"] for c in tk._civs]
    print("per-civ TECH records vs the parser's tech list")
    print("  parser techs      : %d" % len(techs))
    print("  located techs     : %d" % len(located))
    print("")

    print("%-6s %-30s %-8s %-8s %s" % ("tech", "name", "civ", "civ name", "free?"))
    for ti in CIV_TECHS:
        t = techs[ti]
        lt = located[ti] if ti < len(located) else {}
        civ = lt.get("civ", t.get("civ"))
        cname = (civ_names[civ] if isinstance(civ, int)
                 and 0 <= civ < len(civ_names) else "?")
        costs = lt.get("costs") or t.get("costs") or []
        paid = [(c["type"], c["amount"], c["flag"]) for c in costs
                if c["amount"]]
        ent = ix.get("tech", ti)
        print("%-6d %-30s %-8s %-8s costs=%s"
              % (ti, (ent.display if ent else t.get("name")), civ, cname, paid))
    print("")

    # Does the civ field separate them at all?  Print the whole distribution for
    # techs that touch starting resources vs everything.
    from collections import Counter
    dist = Counter(lt.get("civ") for lt in located)
    print("distribution of the tech 'civ' field over all %d techs:" % len(located))
    for k, v in sorted(dist.items(), key=lambda kv: (kv[0] is None, kv[0])):
        print("   civ=%-6s %d techs" % (k, v))
    return 0


if __name__ == "__main__":
    sys.exit(main())
