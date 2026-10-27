"""Print the (offset,width,kind,label) Python targets for the bindings Rust lacks.

`plan` deliberately carries no offsets, so the only way to know which bytes a
build must land on is to call the same resolver the writer uses.
"""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import aoe2mod.dat.parser as P
import aoe2mod.intent.compiler as C
import aoe2mod.dat.locate as L
import aoe2mod.dat.families as F

GAME = r"d:\games\steam\steamapps\common\AoE2DE"
DAT = os.path.join(GAME, "resources/_common/dat/empires2_x2_p1.dat")

raw, _how = P.load_dat(DAT)
p = P.Parser(raw)
p.parse()
F.warm(p.stats, GAME)
intents, bindings = C.load_schema()

civs, civs_start, gv, tail = L.locate(raw, p)
print("civs", len(civs), "start", civs_start, "gv", gv)
civ = civs[1]
units = {u["id"]: u for u in civ["units"]}
print("civ", civ.get("name"), "units", len(units))
u74 = units[74]
print("unit74 keys", sorted(u74))
print("costs", u74.get("costs"))
print("type50 keys", sorted(u74.get("type50") or {}))

def show(title, unit_id, binding):
    u = units[unit_id]
    prim = list(C._primary_targets_for_unit(u, binding))
    print("%-24s unit=%-5d prim=%s" % (title, unit_id, prim))
    if prim:
        mir = list(C._mirrors_of_offset(bindings, u, prim[0][0]))
        print("%-24s %s" % ("", "mirror=%s" % (mir,)))

cost_b = dict(bindings["cost_entry"])
cost_b["resource_types_inverted"] = 4
cost_b["label"] = "成本 population"
show("cost population", 74, cost_b)
atk = bindings["attack_classes"]["attack"]
show("attack class", 4, atk)
show("attack class 82", 82, atk)
arm = bindings["attack_classes"]["armour"]
show("armour class", 74, arm)
disp = bindings["unit_fields"]["displayed_attack"]
show("displayed_attack 82", 82, disp)
show("displayed_attack 83", 83, disp)
show("displayed_attack 74", 74, disp)
