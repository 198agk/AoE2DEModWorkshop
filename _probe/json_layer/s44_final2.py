import os, io, json, re, sys
sys.path.insert(0, r"D:\Software\DeepSeek Harness\工作区2\_probe\datparse")
import parse_dat as P

OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\json_layer"
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
BASE = os.path.join(GAME, "resources", "_common", "dat")
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")
exe = open(os.path.join(GAME, "AoE2DE_s.exe"), "rb").read()

def jload(f):
    return json.loads(open(os.path.join(BASE, f), "rb").read().decode("utf-8-sig"))

# --- K. sounds.json values in exe ---
w("=" * 78)
w("K. sounds.json: are its VALUES engine strings?")
w("=" * 78)
sj = jload("sounds.json")["sound_list"]
for e in sj[:8]:
    w("  key=%-22s name=%-28s key_in_exe=%-5s name_in_exe=%s" % (
        e["key"], e["name"], e["key"].encode() in exe, e["name"].encode() in exe))
w("  distinct keys=%d in exe=%d ; distinct names=%d in exe=%d" % (
    len({e['key'] for e in sj}), len([e for e in sj if e['key'].encode() in exe]),
    len({e['name'] for e in sj}), len([e for e in sj if e['name'].encode() in exe])))
# Where is Play_%s and sound_list relative to each other?
for pat in (b"sound_list", b"Play_%s"):
    w("  %-12s offsets=%s" % (pat.decode(), [m.start() for m in re.finditer(re.escape(pat), exe)]))
lo = 52553100
w("  window @52553100..52553600:")
for m in re.finditer(rb"[ -~]{4,}", exe[lo:lo+400]):
    w("     %8d %s" % (lo + m.start(), m.group(0).decode("latin-1")))

# --- L. buttons.json values in exe / strings ---
w("")
w("=" * 78)
w("L. buttons.json: are its values engine strings?")
w("=" * 78)
bj = jload("buttons.json")["command_button_list"]
w("  n=%d" % len(bj))
for e in bj[:6]:
    w("  name=%-28r in_exe=%-5s" % (e.get("name"), str(e.get("name", "")).encode() in exe))
en = open(os.path.join(GAME, "resources", "en", "strings", "key-value",
                       "key-value-strings-utf8.txt"), "rb").read()
for e in bj[:6]:
    w("  name=%-28r in_en_strings=%s" % (e.get("name"), str(e.get("name", "")).encode() in en))
w("  help_string_id values in en string table: %s" % [
    (e.get("name"), e.get("help_string_id")) for e in bj[:5]])
# are the help_string_ids actual ids in the table?
ids = set()
for line in en.decode("utf-8", "replace").splitlines():
    m = re.match(r"^(\d+)\s", line)
    if m: ids.add(int(m.group(1)))
w("  en table id count=%d ; of buttons' help_string_id present: %s" % (
    len(ids), [(e.get("help_string_id"), e.get("help_string_id") in ids) for e in bj[:5]]))

# --- M. linkedUnits / sharedbuildings vs .dat upgrade chains ---
w("")
w("=" * 78)
w("M. linkedUnits.json / sharedbuildings.json vs .dat UnitConnection groups")
w("=" * 78)
data, how = P.load_dat(os.path.join(BASE, "empires2_x2_p1.dat"))
p = P.Parser(data); st = p.parse()
# rebuild unit connection groups
r = P.Reader(data)
# re-seek to stage 10 (from the parser's own recorded offsets)
import importlib
p2 = P.Parser(data)
p2.parse()
s10 = [s for s in p2.stage_offsets if s[0].startswith("stage 10")]
w("  stage offsets tail: %s" % p2.stage_offsets[-3:])
# simpler: use the already-decoded tech tree if cached
tt = st.get("tech_tree")
w("  tech_tree summary: %s" % tt)
# Instead use civ unit data: build id->name, and unit upgrade chains from
# the JSON's own claim (linkedUnits pairs) and check the .dat for a
# "TrainLocation/upgrade" relation: .dat unit records have 'upgrade' info?
civ = st["civs"][1]
u0 = civ["units"][0]
w("  unit record keys: %s" % sorted(u0.keys()))
lu = jload("linkedUnits.json")["Data"]
sb = jload("sharedbuildings.json")["Data"]
names = {}
for c in st["civs"]:
    for u in c["units"]:
        names.setdefault(u["id"], u["name"])
w("  linkedUnits entries: %s" % [(x["Name"], x["Units"]) for x in lu[:4]])
w("  sharedbuildings entries: %s" % json.dumps(sb[:2], ensure_ascii=False))
w("  resolution of linkedUnits pairs in .dat civ 1:")
for x in lu:
    ok = [(i, names.get(i, "<absent>")) for i in x["Units"]]
    if x["Name"] in ("Lü Bu", "Villagers", "Kongming Lantern"):
        w("     %-20s %s" % (x["Name"], ok))
w("  resolution of sharedbuildings first entry:")
for x in sb[:2]:
    w("     %-20s raw=%s" % (x["Name"], json.dumps(x, ensure_ascii=False)))
    for pair in x.get("Units", []):
        w("        pair=%s -> .dat names %s" % (
            json.dumps(pair, ensure_ascii=False),
            {k: names.get(pair[k], "<absent>") for k in pair}))
open(os.path.join(OUT, "s44_final2.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())
