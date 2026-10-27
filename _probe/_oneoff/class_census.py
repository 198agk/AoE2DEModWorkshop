"""Census of attack/armour classes actually present, with the reader's labels."""
import os, sys, json, io, collections
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import aoe2mod.dat.parser as P
import aoe2mod.dat.locate as L

GAME = r"d:\games\steam\steamapps\common\AoE2DE"
DAT = os.path.join(GAME, "resources/_common/dat/empires2_x2_p1.dat")
raw, _ = P.load_dat(DAT)
p = P.Parser(raw); p.parse()
civs, _, gv, _ = L.locate(raw, p)

names = json.load(io.open("_golden/class_names.json", encoding="utf-8"))
cn = names.get("names") or names
def nm(c):
    v = cn.get(str(c)) or cn.get(c)
    return (v[0] if isinstance(v, list) and v else v) or "?"

atk = collections.Counter(); arm = collections.Counter()
for c in civs:
    for u in c["units"]:
        t50 = u.get("type50") or {}
        for a in (t50.get("attacks") or []):
            atk[a["class"]] += 1
        for a in (t50.get("armors") or []):
            arm[a["class"]] += 1
print("attack classes present:", len(atk))
for c, n in atk.most_common(30):
    print("  %-4d %-22s %d" % (c, nm(c), n))
print("armour classes present:", len(arm))
for c, n in arm.most_common(30):
    print("  %-4d %-22s %d" % (c, nm(c), n))
