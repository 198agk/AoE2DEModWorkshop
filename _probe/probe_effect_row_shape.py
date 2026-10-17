"""What does an effect_rows() row actually look like?  Printing one is cheaper
than guessing field names -- the last run read `b`/`a`/`type` and got 0 of
everything, so at least one of those names must be wrong."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.api as A  # noqa: E402
import aoe2mod.dat.locate as L  # noqa: E402
import aoe2mod.intent.compiler as C  # noqa: E402

tk = A.open_toolkit()
tk._ensure()
data, civs, _cs, gv, tail, _how = tk._parsed
techs = L.locate_techs(data, tail, gv)
effects, _ = L.locate_effects(data)

# tech[85] is the documented Hand Cannoneer enable.  Print whatever shape exists.
for ti in (85, 16, 263):
    rows = C.effect_rows(effects, techs[ti], fanout=None, ix=None)
    print("tech[%d]  rows=%d" % (ti, len(rows)))
    for r in rows[:4]:
        print("   keys=%s" % sorted(r.keys()))
        print("   %s" % r)
    print()

# And the raw tech record keys, so we know what `civ` is really called.
print("tech record keys: %s" % sorted(techs[85].keys()))
print("tech[85] civ=%r effect_id=%r" % (techs[85].get("civ"),
                                        techs[85].get("effect_id")))
