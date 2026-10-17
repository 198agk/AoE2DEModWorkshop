"""Effect 1350 ('Champi Scout (Make avail)') — is it civ-restricted?
locate_effects(data, parser=None) -> (effects, start), records keyed 'index'/'name'/'commands'.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os
import sys

sys.path.insert(0, _HERE_PATH("..", "..", ".."))
from aoe2mod.dat import parser as P          # noqa: E402
from aoe2mod.dat import locate as L          # noqa: E402

ROOT = r"D:\Games\Steam\steamapps\common\AoE2DE"
DAT = os.path.join(ROOT, "resources", "_common", "dat")

blob, how = P.load_dat(os.path.join(DAT, "empires2_x2_p1.dat"))
p = P.Parser(blob)
p.parse()

effs, eff_start = L.locate_effects(blob, parser=p)
print("effects n=%d start=%s" % (len(effs), eff_start))

for i in (1350, 1351, 1352, 1353, 1402):
    e = effs[i]
    print("    effect %-5d name=%-32r n_cmd=%d" % (i, e["name"], len(e["commands"])))
    for c in e["commands"]:
        print("        type=%-4d a=%-8d b=%-8d c=%-8d d=%s" % (c["type"], c["a"], c["b"], c["c"], c["d"]))

print("\n--- every effect whose name mentions 'Champi' ---")
for i, e in enumerate(effs):
    if "Champi" in e["name"]:
        print("    %-5d %-34r cmds=%s" % (i, e["name"],
              [(c["type"], c["a"], c["b"], c["c"], c["d"]) for c in e["commands"]]))

print("\n--- a KNOWN civ-locked 'make avail' for comparison (Tarkan / Plumed) ---")
for i, e in enumerate(effs):
    if "ake avail" in e["name"] and ("Tarkan" in e["name"] or "Plumed" in e["name"]):
        print("    %-5d %-34r cmds=%s" % (i, e["name"],
              [(c["type"], c["a"], c["b"], c["c"], c["d"]) for c in e["commands"]]))
print("DONE")
