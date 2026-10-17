# -*- coding: utf-8 -*-
r"""Print the structure of the two files, for a plain-language answer."""
import json
import os

G = r"D:\Games\Steam\steamapps\common\AoE2DE"
DAT = os.path.join(G, "resources", "_common", "dat")

t = json.loads(open(os.path.join(DAT, "CivTechTrees", "POLES.json"), "rb")
               .read().decode("utf-8-sig"))
print("树 POLES.json")
print("  顶层键:", list(t))
print("  civ_id =", t.get("civ_id"))
print("  civ_techs_units 条数      =", len(t.get("civ_techs_units") or []))
print("  civ_techs_buildings 条数  =", len(t.get("civ_techs_buildings") or []))
print("  一条 unit 行长这样:")
u = (t.get("civ_techs_units") or [])[0]
for k, v in u.items():
    print("      %-24s %r" % (k, v))

p = json.loads(open(os.path.join(DAT, "futuravailableunits.json"), "rb")
               .read().decode("utf-8-sig"))
print()
print("面板 futuravailableunits.json")
print("  顶层文明数:", len(p))
print("  前 8 个文明键:", list(p)[:8])
poles = p.get("Poles", {})
print("  Poles 的键:", list(poles))
blks = poles.get("Buildings") or []
print("  Poles 建筑块数:", len(blks))
print("  前 8 个块的 ID:", [b.get("ID") for b in blks[:8]])
b = next((x for x in blks if x.get("ID") == 45), None)
if b:
    print("  码头(45)块:")
    print("     Units:", [(e.get("ID"), e.get("Name"), e.get("RequiredAge"))
                          for e in (b.get("Units") or [])][:6], "...")
    print("     Techs:", [(e.get("ID"), e.get("Name"))
                          for e in (b.get("Techs") or [])])
