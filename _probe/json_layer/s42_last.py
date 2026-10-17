import os, io, json, re, sys, collections
sys.path.insert(0, r"D:\Software\DeepSeek Harness\工作区2\_probe\datparse")
import parse_dat as P

OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\json_layer"
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
BASE = os.path.join(GAME, "resources", "_common", "dat")
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

exe = open(os.path.join(GAME, "AoE2DE_s.exe"), "rb").read()

def jload(fp):
    return json.loads(open(fp, "rb").read().decode("utf-8-sig"))

def keyset(o, acc=None):
    if acc is None: acc = set()
    if isinstance(o, dict):
        for k, v in o.items():
            acc.add(k); keyset(v, acc)
    elif isinstance(o, list):
        for v in o: keyset(v, acc)
    return acc

# ---------- A. civTechTrees.json (mono): is its schema shared? ----------
w("=" * 78)
w("A. civTechTrees.json mono container: strings and offsets")
w("=" * 78)
for s in (b'"civs"', b'civs"', b'civ_id', b'civ_techs_buildings', b'civ_techs_units',
          b'civTechTrees.json', b'CivTechTrees/%s.json', b'CivTechTrees'):
    offs = [m.start() for m in re.finditer(re.escape(s), exe)]
    w("  %-28s count=%d  offsets=%s" % (s.decode(), len(offs), offs[:6]))
# show the byte window around 53352056
lo, hi = 53351900, 53352300
w("  window @53351900-53352300:")
w("  " + repr(exe[lo:hi]))

# ---------- B. futuravailableunits RequiredAge vs CivTechTrees Age ID ----
w("")
w("=" * 78)
w("B. futuravailableunits.RequiredAge  vs  CivTechTrees.<civ>.Age ID")
w("=" * 78)
fau = jload(os.path.join(BASE, "futuravailableunits.json"))
civs = jload(os.path.join(BASE, "civilizations.json"))["civilization_list"]
# map civilizations.json internal_name -> tech_tree_name (== CivTechTrees file stem)
name2tt = {c["internal_name"]: c["tech_tree_name"] for c in civs}
w("  sample mapping: %s" % list(name2tt.items())[:5])
tot = match = diff = notfound = 0
examples = []
for civkey, blob in fau.items():
    tt = name2tt.get(civkey)
    if not tt: continue
    fp = os.path.join(BASE, "CivTechTrees", tt + ".json")
    if not os.path.exists(fp): continue
    ctt = jload(fp)
    age = {}
    for nd in ctt["civ_techs_units"]:
        age[nd["Node ID"]] = nd.get("Age ID")
    for nd in ctt["civ_techs_buildings"]:
        age[nd["Node ID"]] = nd.get("Age ID")
    def walk(node):
        global tot, match, diff, notfound
        if isinstance(node, dict):
            if "ID" in node and "RequiredAge" in node:
                tot += 1
                a = age.get(node["ID"])
                if a is None: notfound += 1
                elif a == node["RequiredAge"]: match += 1
                else:
                    diff += 1
                    if len(examples) < 12:
                        examples.append((civkey, node.get("Name"), node["ID"],
                                         node["RequiredAge"], a))
            for v in node.values(): walk(v)
        elif isinstance(node, list):
            for v in node: walk(v)
    walk(blob)
w("  compared entries=%d  match=%d  diff=%d  id-not-in-ctt=%d" % (tot, match, diff, notfound))
w("  diff examples (civ,name,id,RequiredAge,CivTechTrees.Age ID):")
for e in examples: w("     %s" % (e,))
w("  -> if match dominates, futuravailableunits.RequiredAge is the SAME quantity as")
w("     CivTechTrees Age ID (both per-civ), NOT the .dat global tech-tree age.")

# ---------- C. paphosfutureavailableunits vs futuravailableunits --------
w("")
w("=" * 78)
w("C. paphosfutureavailableunits.json vs futuravailableunits.json")
w("=" * 78)
pf = jload(os.path.join(BASE, "paphosfutureavailableunits.json"))
w("  paphos top keys type=%s n=%s" % (type(pf).__name__, len(pf)))
w("  paphos top keys(sample)=%s" % (list(pf)[:8] if isinstance(pf, dict) else "<list>"))
ka = keyset(fau); kb = keyset(pf)
w("  fau keys=%d paphos keys=%d" % (len(ka), len(kb)))
w("  in paphos not fau: %s" % sorted(kb - ka))
w("  in fau not paphos: %s" % sorted(ka - kb))
miss = [k for k in sorted(kb) if k.encode() not in exe]
w("  paphos keys NOT literal in exe: %s" % miss)

# ---------- D. campaign JSON shapes ------------------------------------
w("")
w("=" * 78)
w("D. campaign / other dat-dir JSON shapes")
w("=" * 78)
for f in ("paphos_campaign.json", "peru_campaign.json", "providence_campaign.json"):
    fp = os.path.join(BASE, f)
    if not os.path.exists(fp): w("  %s MISSING" % f); continue
    j = jload(fp)
    w("  %s  %d B" % (f, os.path.getsize(fp)))
    w("     top type=%s" % type(j).__name__)
    if isinstance(j, dict):
        w("     top keys=%s" % list(j)[:10])
        for k in list(j)[:2]:
            v = j[k]
            w("       %s -> %s" % (k, type(v).__name__))
            if isinstance(v, list) and v and isinstance(v[0], dict):
                w("         item keys=%s" % list(v[0]))
                w("         first=%s" % json.dumps(v[0], ensure_ascii=False)[:300])
    elif isinstance(j, list) and j and isinstance(j[0], dict):
        w("     item keys=%s" % list(j[0]))
        w("     first=%s" % json.dumps(j[0], ensure_ascii=False)[:300])
    w("     keys not in exe: %s" % [k for k in sorted(keyset(j)) if k.encode() not in exe])
w("  history.json in dat dir? %s" % os.path.exists(os.path.join(BASE, "history.json")))
w("  history.json elsewhere in game tree:")
for root, d, files in os.walk(GAME):
    if "history.json" in files:
        w("     %s" % os.path.join(root, "history.json"))

# ---------- E. sounds.json vs .dat sounds ------------------------------
w("")
w("=" * 78)
w("E. sounds.json vs .dat sound entries")
w("=" * 78)
data, how = P.load_dat(os.path.join(BASE, "empires2_x2_p1.dat"))
p = P.Parser(data); st = p.parse()
snd = jload(os.path.join(BASE, "sounds.json"))["sound_list"]
w("  sounds.json entries=%d ; sample=%s" % (len(snd), json.dumps(snd[:3], ensure_ascii=False)))
raw = st.get("sounds_raw") or st.get("sound_names")
w("  .dat stats sound_count=%s" % st.get("sound_count"))
w("  parser-exposed sound key names: %s" % sorted(st.keys()))
# look for the actual sound records
for k, v in st.items():
    if isinstance(v, list) and v and isinstance(v[0], dict):
        w("  st[%s] list len=%d first=%s" % (k, len(v), json.dumps(v[0], ensure_ascii=False)[:200]))
w("  'sound_list' literal in exe: %s" % (b"sound_list" in exe))
w("  'Play_<s>' literal in exe: " + str(b"Play_%s" in exe))

# ---------- F. buttons.json: is command-button data in the .dat? -------
w("")
w("=" * 78)
w("F. buttons.json vs .dat CommandSlots / genieutils Unit.h")
w("=" * 78)
bt = jload(os.path.join(BASE, "buttons.json"))["command_button_list"]
w("  buttons.json entries=%d ; sample=%s" % (len(bt), json.dumps(bt[:3], ensure_ascii=False)))
uh = r"D:\Software\DeepSeek Harness\工作区2\_probe\source\genieutils\include\genie\dat\Unit.h"
w("  Unit.h exists: %s" % os.path.exists(uh))
if os.path.exists(uh):
    txt = open(uh, encoding="utf-8", errors="replace").read()
    for needle in ("CommandSlot", "ButtonID", "command", "Command"):
        n = len(re.findall(needle, txt))
        w("    Unit.h[%s] = %d" % (needle, n))
    m = re.search(r"class CommandSlot[\s\S]{0,700}", txt)
    w("  --- CommandSlot class ---")
    w("  " + (m.group(0) if m else "<not found>"))
open(os.path.join(OUT, "s42_last.py.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())
