import os, io, json, sys
sys.path.insert(0, r"D:\Software\DeepSeek Harness\工作区2\_probe\datparse")
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\json_layer"
BASE = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat"
DAT = os.path.join(BASE, "empires2_x2_p1.dat")
import parse_dat as P
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

civs = json.loads(open(os.path.join(BASE, "civilizations.json"), "rb").read().decode("utf-8-sig"))["civilization_list"]
data, how = P.load_dat(DAT)
p = P.Parser(data)
st = p.parse()
w("loaded %s" % how)
w("datcivs=%d jsons=%d" % (len(st["civs"]), len(civs)))

# build dat unit id set and tech id set (units all civs, techs list)
dat_unit_ids = set()
for c in p.civs if hasattr(p, "civs") else []:
    pass
# fall back: use first_units captured? use stage8 blob via read_civ
w("parser attrs: %s" % [a for a in dir(p) if not a.startswith("_")])

# techs
tech_ids = set()
tl = getattr(p, "techs", None)
w("p.techs type=%s" % type(tl))
if isinstance(tl, list):
    for t in tl:
        pass

w("")
w("=== civilizations.json: do its id fields land in .dat id spaces? ===")
w("NOTE: civilizations.json has NO tech_tree_id / team_bonus_id / icon_set / resources fields:")
w("  json keys = %s" % list(civs[0].keys()))
w("  .dat civ keys = player_type,name,tech_tree_id,team_bonus_id,resources,icon_set")
w("  overlap = %s" % sorted(set(civs[0].keys()) & {"player_type","name","tech_tree_id","team_bonus_id","resources","icon_set"}))

# unit id set from semantics file
sem = json.loads(open(r"D:\Software\DeepSeek Harness\工作区2\_probe\semantic\unit_names.json", encoding="utf-8").read())
uids = set(int(k) for k in (sem.get("units") or sem).keys() if str(k).isdigit()) if isinstance(sem, dict) else set()
w("")
w("semantic unit_ids available = %d" % len(uids))
tech_sem = json.loads(open(r"D:\Software\DeepSeek Harness\工作区2\_probe\semantic\tech_names.json", encoding="utf-8").read())
tids = set(int(k) for k in (tech_sem.get("techs") or tech_sem).keys() if str(k).isdigit()) if isinstance(tech_sem, dict) else set()
w("semantic tech_ids available = %d" % len(tids))
if not tids:
    w("  tech_names.json top-level keys sample = %s" % list(tech_sem)[:5] if isinstance(tech_sem, dict) else "n/a")

for f, space, name in (("unique_unit_id", uids, "unit"), ("elite_unique_unit_id", uids, "unit"),
                       ("unique_unit_upgrade_id", uids, "unit")):
    vals = [(c["internal_name"], c[f]) for c in civs if isinstance(c.get(f), int) and c[f] >= 0]
    hit = [(n, v) for n, v in vals if v in space]
    w("  %-24s n=%3d in_%s_id_space=%3d (%.0f%%)  e.g. %s" % (
        f, len(vals), name, len(hit), 100.0 * len(hit) / max(1, len(vals)), vals[:3]))
for f in ("unique_tech_id_1", "unique_tech_id_2", "unique_unit_line"):
    vals = [(c["internal_name"], c[f]) for c in civs if isinstance(c.get(f), int)]
    hit = [(n, v) for n, v in vals if v in tids]
    w("  %-24s n=%3d in_tech_id_space=%3d (%.0f%%)  e.g. %s" % (
        f, len(vals), len(hit), 100.0 * len(hit) / max(1, len(vals)), vals[:3]))

# unique_unit_line is negative -> unitlines.json namespace
ul = json.loads(open(os.path.join(BASE, "unitlines.json"), "rb").read().decode("utf-8-sig"))
lines = {e["LineID"]: e["Name"] for e in ul["UnitLines"]}
lane = [(c["internal_name"], c["unique_unit_line"]) for c in civs if isinstance(c.get("unique_unit_line"), int)]
hitl = [(n, v, lines[v]) for n, v in lane if v in lines]
w("")
w("  unique_unit_line -> unitlines.json LineID: n=%d resolved=%d (%.0f%%)" % (len(lane), len(hitl), 100.0*len(hitl)/max(1,len(lane))))
w("  samples: %s" % hitl[:8])
open(os.path.join(OUT, "s54_civjoin.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())
