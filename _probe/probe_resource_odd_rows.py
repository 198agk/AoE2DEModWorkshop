"""The odd rows inside the Resource Modifier family, before wiring them.

`probe_refusal_reasons.py` showed the family is mostly regular (B=0 set / B=1
change, C=-1) but not entirely:

  * type 1 (Set/+-) has 8 commands with B == -1
  * type 6 (Multiply) has 3 with B == 1 and 1 with B == 4, though its own
    schema says B is unused
  * 18 commands across the family have C != -1, which scales the amount by
    ANOTHER resource's current value

A rule that silently treats those as ordinary would produce a preview that
promises a number the engine will then multiply by something the tool never
read.  Dump them so the design can refuse exactly the ambiguous ones and say
why, instead of guessing in either direction.
"""
import os
import sys

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
    labels = C.load_resource_labels()

    print("=== rows whose B is not 0/1, or whose C is not -1 ===")
    n = 0
    for ti, t in enumerate(techs):
        for row in C.effect_rows(effects, t, ix=None):
            if row["type"] not in RESOURCE_TYPES:
                continue
            _ty, a, b, c, d = row["raw"]
            if b in (0, 1) and c == -1:
                continue
            n += 1
            print("  tech[%d] %-34s type %-3d A=%-4d(%-14s) B=%-3s C=%-4s D=%s"
                  % (ti, (t.get("name") or "")[:34], row["type"], a,
                     labels.get(a, "UNNAMED"), b, c, d))
    print("  total odd rows: %d" % n)
    print("")

    # Sanity: the grant rows this whole round is about must all be regular.
    print("=== the civilization start-resource grants ===")
    WANT = {223: "Persians", 224: "Aztecs", 225: "Huns", 226: "Chinese",
            227: "Mayans", 228: "Sicilians", 1394: "Tupi"}
    RES = {91: "food", 92: "wood", 93: "stone", 94: "gold"}
    for ti in sorted(WANT):
        for row in C.effect_rows(effects, techs[ti], ix=None):
            _ty, a, b, c, d = row["raw"]
            if a not in RES:
                continue
            print("  tech[%d] %-10s cmd %d: type %d B=%s C=%s D=%s  -> %s"
                  % (ti, WANT[ti], row["index"], row["type"], b, c, d,
                     RES[a]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
