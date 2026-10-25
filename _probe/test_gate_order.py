# -*- coding: utf-8 -*-
"""No assertion may sit after the LAST failure gate.

Every nail in this folder ends with a block like::

    if FAILS:
        print("... FAILED -> %s" % FAILS)
        return 1

Anything that appends to FAILS after the last such block cannot change the exit
code -- the run reports green no matter what it saw.  That is worse than a
missing assertion, because the file LOOKS like it checks the thing.

This was not hypothetical: on 2026-10-25 I inserted a whole section after that
gate in `test_replace_sentence.py` and it printed two `FAIL` lines while the
suite exited 0.  So the check is structural and it walks every nail.

The first version of this scanner compared against the FIRST gate and reported a
false positive on `test_availability_intent_e2e.py`, which has a staged gate
("stopping: the plan failed") and a final one -- assertions between them are
alive, because the final gate still reads FAILS.  The test is therefore "is there
any gate after this assertion", not "is the first gate before it".
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    dead = []
    gated = 0
    scanned = 0
    for name in sorted(os.listdir(HERE)):
        if not (name.startswith("test_") and name.endswith(".py")):
            continue
        if name == os.path.basename(__file__):
            continue
        path = os.path.join(HERE, name)
        text = io.open(path, encoding="utf-8", errors="replace").read()
        gates = [m.end() for m in re.finditer(r"if FAILS:", text)]
        scanned += 1
        if not gates:
            continue
        gated += 1
        last = gates[-1]
        for m in re.finditer(r"\n\s+(?:check\(|FAILS\.append\()", text):
            if m.start() > last:
                dead.append("%s: records a failure at char %d, "
                            "but the last gate is at %d"
                            % (name, m.start(), last))
                break

    print("test_*.py files scanned: %d (%d have a failure gate)"
          % (scanned, gated))
    print("recorded after the last gate: %d" % len(dead))
    for line in dead[:10]:
        print("  %s" % line)
    if dead:
        print("GATE ORDER: %d DEAD ASSERTION(S) -- nothing reads the result"
              % len(dead))
        return 1
    print("GATE ORDER: NO ASSERTION SITS BEHIND THE LAST FAILURE GATE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
