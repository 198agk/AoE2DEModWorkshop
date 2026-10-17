import os, io, json, sys
sys.path.insert(0, r"D:\Software\DeepSeek Harness\工作区2\_probe\datparse")
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\json_layer"
BASE = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat"
import parse_dat as P
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

data, how = P.load_dat(os.path.join(BASE, "empires2_x2_p1.dat"))
p = P.Parser(data); st = p.parse()

w("=== .dat Unit: does it carry a CLASS field and a TRAIN building? (raw record) ===")
c = st["civs"][1]  # British
recs = c["units"] if isinstance(c, dict) and "units" in c else None
w("  civ keys = %s" % list(c.keys())[:15])
if recs:
    u = recs[1]
    w("  unit record keys (%d) = %s" % (len(u), sorted(u.keys())))
    for k in ("id", "name", "class", "type", "icon_id", "enabled", "disabled", "train_locations", "unit_class"):
        if k in u:
            w("    %-18s = %r" % (k, u[k]))
w("")
w("=== genieutils UnitClass enum vs unitcategories.json names ===")
src = r"D:\Software\DeepSeek Harness\工作区2\_probe\source\genieutils\include\genie\dat\Unit.h"
if os.path.exists(src):
    t = open(src, encoding="utf-8", errors="ignore").read()
    import re
    m = re.search(r"enum class UnitClass\s*\{(.*?)\};", t, re.S)
    if m:
        members = [x.strip() for x in m.group(1).split(",") if x.strip()]
        w("  UnitClass n=%d" % len(members))
        for c2 in ["Infantry", "Cavalry", "Archer", "CavalryArcher", "Monk", "Warship", "SiegeWeapon",
                   "Archers", "CavalryArchers", "Monks", "Warboats", "SiegeWeapons"]:
            w("    %-18s exact-member=%s  substring=%s" % (c2, c2 in members,
              [x for x in members if c2.lower() in x.lower()][:3]))
else:
    w("  Unit.h not found at %s" % src)
open(os.path.join(OUT, "s58_unitclass.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())
