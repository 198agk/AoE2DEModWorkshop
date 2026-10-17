"""Does the wired panel half actually land in the emitted mod?

The build must produce BOTH `CivTechTrees/BRITONS.json` and the panel file, and
the panel's own verification must be honest about what it proved.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from aoe2mod.game import buildpanel as BP  # noqa: E402
import aoe2mod.api as A  # noqa: E402

OUT = os.path.join(HERE, "out_panelwire")
tk = A.open_toolkit()

# Hand Cannoneer (5) -> Britons: the tree calls it NotAvailable and the panel's
# Archery Range does not list it, so BOTH halves have real work to do.
man = tk.build({"intent": "unit.availability", "unit": "Hand Cannoneer",
                "civ": "British", "action": "grant"},
               OUT, title="panel wire test", author="aoe2mod", overwrite=True)

print("mod dir:", OUT)
found = []
for root, _dirs, names in os.walk(OUT):
    for n in names:
        p = os.path.join(root, n)
        found.append(os.path.relpath(p, OUT).replace(os.sep, "/"))
print("files emitted:")
for f in sorted(found):
    print("   %s  (%d B)" % (f, os.path.getsize(os.path.join(OUT, f))))

tree_rel = "resources/_common/dat/CivTechTrees/BRITONS.json"
panel_rel = "resources/_common/dat/futuravailableunits.json"
print()
print("tree file present : %s" % (tree_rel in found))
print("panel file present: %s" % (panel_rel in found))

if panel_rel in found:
    text, obj = BP.load_panel(os.path.join(OUT, panel_rel))
    ok = BP.has_entry(obj, "Britons", 87, 5, BP.UNITS_KEY)
    print("panel lists Hand Cannoneer at the Archery Range: %s" % ok)
    shipped_text, shipped = BP.load_panel(
        os.path.join(tk.game_root, BP.PANEL_REL))
    n0 = len(BP.entries(shipped, "Britons", 87, BP.UNITS_KEY))
    n1 = len(BP.entries(obj, "Britons", 87, BP.UNITS_KEY))
    print("Archery Range entries: %d -> %d" % (n0, n1))
    oks, info = BP.verify_surgical(shipped_text, text)
    print("surgical: %s  %s" % (oks, info))

print()
print("manifest keys: %s" % sorted(man.keys()))
for k in ("panel", "edit_count", "mod_contains_dat", "civ", "space"):
    if k in man:
        print("   %s = %r" % (k, man[k]))
print()
print("panel verdict: ok=%r mode=%r" % (man["panel"].get("ok"),
                                        man["panel"].get("mode")))
print("proven:")
for p in man["verification"]["proven"]:
    print("   + %s" % p)
print("not proven:")
for p in man["verification"]["not_proven"]:
    print("   - %s" % p)
