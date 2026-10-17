# -*- coding: utf-8 -*-
"""Which fields can the locator already reach that the schema never exposes?

Round 6 fixed the READ side (describe) drifting from the write side; Round 7
fixed the cost list drifting from the compiler's own chooser.  Both were cases
of one list quietly disagreeing with another.

There is a third list nobody has audited: the marks the locator itself writes
with ``r.at(name)``.  A mark is an offset the locator *already knows*.  If a
mark is not in ``unit_fields``/``tech_fields``, then a field the tool can
physically address is invisible to every intent -- and no test catches it,
because nothing ever asks for a field that has no name.

Read-only: parses the real BASE dat, invents nothing.
"""
import json
import os
import sys
import collections
import contextlib
import io

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

from aoe2mod.dat import parser as P      # noqa: E402
from aoe2mod.dat import locate as L      # noqa: E402
from aoe2mod.intent import compiler as C  # noqa: E402

BASE = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat"

# `r.at("x")` is a positional placeholder the locator uses inside attack /
# armour entry loops; it names no field, so it is not a candidate.
PLACEHOLDER = {"x"}


def main():
    intents, B = C.load_schema()
    data, how = P.load_dat(BASE)
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    civs, _, gv, tail = L.locate(data, parser=p)

    print("=== the locator's own marks, by unit type ===")
    all_marks, marks_by_type = set(), {}
    sample = {}
    n_units = 0
    for cv in civs:
        for u in cv["units"]:
            n_units += 1
            o = {k: v for k, v in (u.get("_offs") or {}).items()
                 if k not in PLACEHOLDER}
            all_marks |= set(o)
            marks_by_type.setdefault(u["type"], set()).update(o)
            for k in o:
                sample.setdefault(k, (cv["name"], u["id"], u.get("name", "?")))

    print("units scanned        : %d  across %d civs" % (n_units, len(civs)))
    print("distinct marks       : %d" % len(all_marks))
    for t in sorted(marks_by_type):
        if t in (10, 70, 80):          # the three that matter for modding
            print("  type %-3d (%d marks): %s"
                  % (t, len(marks_by_type[t]), ", ".join(sorted(marks_by_type[t]))))

    print()
    print("=== type50 sub-fields (only combatants carry these) ===")
    t50 = collections.OrderedDict()
    for cv in civs[:8]:                # a sample is enough to learn the shape
        for u in cv["units"]:
            tt = u.get("type50")
            if tt:
                for k, v in tt.items():
                    t50.setdefault(k, []).append(type(v).__name__)
    for k in t50:
        kinds = sorted(set(t50[k]))
        print("  %-26s %s" % (k, "/".join(kinds)))

    print()
    print("=== tech marks ===")
    techs = L.locate_techs(data, tail, gv)
    tech_marks, tech_sample = set(), {}
    for t in techs:
        o = {k: v for k, v in (t.get("_offs") or {}).items()
             if k not in PLACEHOLDER}
        tech_marks |= set(o)
        for k in o:
            tech_sample.setdefault(k, t.get("name"))
    print("techs scanned        : %d" % len(techs))
    print("distinct marks       : %d -> %s"
          % (len(tech_marks), ", ".join(sorted(tech_marks))))

    print()
    print("=== MARKED BUT NOT BOUND: the reachable-but-invisible fields ===")
    uf = B.get("unit_fields", {})
    tf = B.get("tech_fields", {})
    miss_u = sorted(all_marks - set(uf))
    miss_t = sorted(tech_marks - set(tf))
    print("unit_fields bound    : %d -> %s" % (len(uf), ", ".join(sorted(uf))))
    print("UNBOUND unit marks   : %d" % len(miss_u))
    for m in miss_u:
        civ, uid, nm = sample.get(m, ("?", "?", "?"))
        print("    %-24s e.g. %s id=%s %r" % (m, civ, uid, nm))
    print("UNBOUND tech marks   : %d" % len(miss_t))
    for m in miss_t:
        print("    %-24s e.g. %s" % (m, tech_sample.get(m)))
    print("unit_fields entries with NO mark (unreachable by construction): %s"
          % ", ".join(sorted(set(uf) - all_marks)) or "(none)")

    # The reverse question: is every binding's `source` actually produced?
    print()
    print("=== binding sources present in the data? ===")
    srcs = set()
    for k, v in list(uf.items()) + list(tf.items()):
        if isinstance(v, dict) and v.get("source"):
            srcs.add(v["source"])
        for sub in ("mirror",):
            if isinstance(v, dict) and isinstance(v.get(sub), dict):
                srcs.add(v[sub].get("source"))
    for s in sorted(x for x in srcs if x):
        where = ("mark" if s in all_marks or s in tech_marks
                 else ("type50" if s in t50 else "?"))
        print("  %-18s -> %s" % (s, where))


if __name__ == "__main__":
    main()
