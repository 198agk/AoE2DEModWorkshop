import os, sys, io, json, hashlib
sys.path.insert(0, r"D:\Software\DeepSeek Harness\工作区2\_probe\datparse")
import parse_dat as P

OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\json_layer"
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

src = open(r"D:\Software\DeepSeek Harness\工作区2\_probe\datparse\parse_dat.py", encoding="utf-8").read()
for fn in ("read_tech", "read_effect", "read_effect_command", "read_unit_line", "read_research_location",
           "read_tech_tree_age", "read_building_connection", "read_unit_connection", "read_research_connection"):
    i = src.find("def %s(" % fn)
    j = src.find("\ndef ", i + 5)
    w("=" * 70)
    w(src[i:j])

w("=" * 70)
w("MOD .dat COMPARISON")
bases = {
    "base": r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat",
    "mod297820": r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\subscribed\297820_10 倍资源文明联盟3倍科技\resources\_common\dat\empires2_x2_p1.dat",
    "mod423821": r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\subscribed\423821_四月-juntuanzhangtianfumozu军团长天赋模组\resources\_common\dat\empires2_x2_p1.dat",
    "mod550749": r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\subscribed\550749_{2026}10倍资源文明联盟2倍科技 北欧dlc可用 v48\resources\_common\dat\empires2_x2_p1.dat",
}
summ = {}
for tag, path in bases.items():
    if not os.path.exists(path):
        w("  %-10s MISSING" % tag); continue
    raw = open(path, "rb").read()
    try:
        data, how = P.load_dat(path)
    except Exception as e:
        w("  %-10s load_dat FAILED %r" % (tag, e)); continue
    p = P.Parser(data)
    try:
        st = p.parse()
        ok = True
    except Exception as e:
        w("  %-10s parse FAILED %r" % (tag, e)); continue
    w("  %-10s file=%d inflated=%d civs=%d techs=%d uhdr=%d tt=%s" % (
        tag, len(raw), len(data), st.get("civ_count"), st.get("tech_count"),
        st.get("unit_header_count"), json.dumps(st.get("tech_tree"))))
    civnames = [c["name"] for c in st["civs"]]
    w("      civs: %s" % civnames)
    summ[tag] = {
        "raw": len(raw), "inflated": len(data), "civ_count": st.get("civ_count"),
        "tech_count": st.get("tech_count"), "uhdr": st.get("unit_header_count"),
        "tt": st.get("tech_tree"), "civs": civnames,
        "tbi": {c["name"]: c["team_bonus_id"] for c in st["civs"]},
        "tti": {c["name"]: c["tech_tree_id"] for c in st["civs"]},
        "nonzero": {c["name"]: c["unit_pointers_nonzero"] for c in st["civs"]},
        "nunits": {c["name"]: len(c["units"]) for c in st["civs"]},
    }

if "base" in summ and "mod297820" in summ:
    b, m = summ["base"], summ["mod297820"]
    w("\n  base vs mod297820 civ-name sets: only_in_base=%s only_in_mod=%s" % (
        [c for c in b["civs"] if c not in m["civs"]], [c for c in m["civs"] if c not in b["civs"]]))
    diff = [(c, b["tbi"].get(c), m["tbi"].get(c)) for c in b["civs"] if c in m["tbi"] and b["tbi"][c] != m["tbi"][c]]
    w("  team_bonus_id differences: %d  %s" % (len(diff), diff[:12]))
    diff2 = [(c, b["tti"].get(c), m["tti"].get(c)) for c in b["civs"] if c in m["tti"] and b["tti"][c] != m["tti"][c]]
    w("  tech_tree_id differences : %d  %s" % (len(diff2), diff2[:12]))
    nz = [(c, b["nonzero"].get(c), m["nonzero"].get(c)) for c in b["civs"] if c in m["nonzero"] and b["nonzero"][c] != m["nonzero"][c]]
    w("  unit_pointers_nonzero differences: %d  %s" % (len(nz), nz[:12]))

open(os.path.join(OUT, "s23_moddat.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue()[-4200:])
