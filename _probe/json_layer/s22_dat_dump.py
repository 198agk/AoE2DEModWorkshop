import os, sys, io, json
sys.path.insert(0, r"D:\Software\DeepSeek Harness\工作区2\_probe\datparse")
import parse_dat as P

DAT = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat"
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\json_layer"
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

data, how = P.load_dat(DAT)
p = P.Parser(data)
st = p.parse()

w("=== DAT stats (stage results)")
for k in sorted(st):
    v = st[k]
    if isinstance(v, list):
        w("  %-38s list[%d]" % (k, len(v)))
    elif isinstance(v, dict):
        w("  %-38s dict %s" % (k, json.dumps(v, ensure_ascii=False)[:150]))
    else:
        w("  %-38s %s" % (k, v))
w("\nparser notes:")
for n in p.notes:
    w("  - %s" % n)

tt = st["tech_tree"]
w("\n=== DAT tech_tree = %s" % json.dumps(tt, ensure_ascii=False))

w("\n=== DAT civs")
civs = st["civs"]
for i, c in enumerate(civs):
    w("  %2d  pt=%-3s name=%-16s tti=%-6s tbi=%-6s nres=%-3d units=%-5d nonzero=%d" % (
        i, c["player_type"], c["name"], c["tech_tree_id"], c["team_bonus_id"],
        len(c["resources"]), c["unit_pointers_total"], c["unit_pointers_nonzero"]))

from collections import Counter
w("\n=== distinct tech_tree_id: %s" % dict(Counter(c["tech_tree_id"] for c in civs)))
w("=== distinct team_bonus_id: %s" % dict(Counter(c["team_bonus_id"] for c in civs)))

w("\n=== DAT unit_lines (stage 6) = %r   <-- None means .dat has NO unitlines array" % (st.get("unit_lines"),))
w("=== DAT techs=%d unit_headers=%d sounds=%d graphics=%d effects=%d" % (
    len(st["techs"]), len(st["unit_headers"]), len(st["sounds"]), len(st["graphics"]), len(st["effects"])))

w("\n=== sample techs (first 5) name/civ/effect_id")
for t in st["techs"][:5]:
    w("   %s" % json.dumps({k: t.get(k) for k in ("name", "civ", "effect_id", "type", "icon_id")}, ensure_ascii=False))
w("\n=== civ[1] resources (first 20): %s" % (list(st["civs"][1]["resources"][:20]),))
w("=== civ[0] name=%r pt=%s" % (st["civs"][0]["name"], st["civs"][0]["player_type"]))

# Do civ names in .dat match the civ names in civilizations.json?
civjson = json.loads(open(r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\civilizations.json", "rb").read().decode("utf-8-sig"))
jn = [c.get("internal_name") for c in civjson["civilization_list"]]
dn = [c["name"] for c in civs]
w("\n=== .dat civ names  (%d): %s" % (len(dn), dn))
w("=== json civ names (%d): %s" % (len(jn), jn))

open(os.path.join(OUT, "s22_dat_dump.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue()[:9000])
