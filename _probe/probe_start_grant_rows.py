"""Enumerate the `Resource Modifier (Set/+/-)` grants that touch starting resources.

Corrected encoding: for command type 1 (`Resource Modifier (Set/+/-)`,
effect_command_types.json) the params are
    A:resource id   B:0=set/1=change   C:times-resource or -1   D:value
so the resource id is in slot **1**, not slot 2.  The previous probe only looked
at slot 2, which is why it reported a single hit for a mechanism that governs
every civilization's opening bank.

Output: for each of resource 91..94, every command that sets or changes it,
with the owning tech's display name and its parameters.  If a "give the Britons
more starting food" feature is to exist, these rows are what it would edit --
and they are already reachable with the EXISTING `tech.effect` intent, because
that intent addresses a command by (tech, position) in the list.
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import aoe2mod.api as A                                          # noqa: E402
from aoe2mod.dat import parser as P                               # noqa: E402
from aoe2mod.semantic.index import index as semantic_index        # noqa: E402

START = {91: "Starting Food", 92: "Starting Wood",
         93: "Starting Stone", 94: "Starting Gold"}
MODES = {0: "SET", 1: "CHANGE"}


def main():
    tk = A.open_toolkit()
    tk._ensure()
    p = P.Parser(tk._raw)
    p.parse()
    effects = p.stats["effects"]
    techs = p.stats["techs"]
    ix = semantic_index()

    owner = {}
    for ti, t in enumerate(techs):
        eid = t.get("effect_id")
        if eid is not None and eid >= 0:
            owner.setdefault(eid, []).append(ti)

    for want in sorted(START):
        print("=" * 78)
        print("resource %d = %s" % (want, START[want]))
        print("=" * 78)
        found = 0
        for ei, eff in enumerate(effects):
            for ci, cmd in enumerate(eff.get("commands") or ()):
                if len(cmd) < 5:
                    continue
                ctype, a, b, c, d = cmd[0], cmd[1], cmd[2], cmd[3], cmd[4]
                if ctype != 1 or a != want:
                    continue
                found += 1
                for ti in owner.get(ei, []):
                    ent = ix.get("tech", ti)
                    label = ent.display if ent else str(ti)
                    print("  tech[%-4d] %-30s effect %-5d cmd %-2d  %s %g"
                          "   (A=%d B=%d C=%d D=%g)"
                          % (ti, label, ei, ci, MODES.get(b, "?%d" % b), d,
                             a, b, c, d))
        if not found:
            print("  (no Resource Modifier command targets this resource)")
        print("")
    return 0


if __name__ == "__main__":
    sys.exit(main())
