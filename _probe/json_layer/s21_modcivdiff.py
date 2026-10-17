import os, io, json
BASE = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat"
M297 = None
M550 = None
root = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\subscribed"
for d in os.listdir(root):
    if d.startswith("297820"):
        M297 = os.path.join(root, d, "resources", "_common", "dat")
    if d.startswith("550749"):
        M550 = os.path.join(root, d, "resources", "_common", "dat")
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\json_layer"
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

def load(p):
    return json.loads(open(p, "rb").read().decode("utf-8-sig"))

b = load(os.path.join(BASE, "civilizations.json"))
w("BASE civilizations.json keys=%s  n_civs=%d" % (list(b.keys()), len(b["civilization_list"])))
w("BASE civ[1] (Britons-ish): %s" % json.dumps(b["civilization_list"][1], ensure_ascii=False))
w("BASE all field names used: %s" % sorted({k for c in b["civilization_list"] for k in c}))

m = load(os.path.join(M297, "civilizations.json"))
w("\n\nMOD 297820 civilizations.json keys=%s  n_civs=%d  size=%d" % (
    list(m.keys()), len(m["civilization_list"]), os.path.getsize(os.path.join(M297, "civilizations.json"))))
w("MOD civ[1]: %s" % json.dumps(m["civilization_list"][1], ensure_ascii=False))
w("MOD all field names used: %s" % sorted({k for c in m["civilization_list"] for k in c}))

bk = {c.get("internal_name"): c for c in b["civilization_list"]}
mk = {c.get("internal_name"): c for c in m["civilization_list"]}
w("\nnames only in BASE: %s" % sorted(set(bk) - set(mk)))
w("names only in MOD : %s" % sorted(set(mk) - set(bk)))

w("\n\n=== PER-CIV FIELD DIFF (base vs mod)")
ndiff = 0
for name in sorted(set(bk) & set(mk)):
    cb, cm = bk[name], mk[name]
    for k in sorted(set(cb) | set(cm)):
        vb, vm = cb.get(k, "<ABSENT>"), cm.get(k, "<ABSENT>")
        if vb != vm:
            w("  %-14s %-28s base=%s  mod=%s" % (name, k, json.dumps(vb, ensure_ascii=False)[:110], json.dumps(vm, ensure_ascii=False)[:110]))
            ndiff += 1
w("total differing fields: %d" % ndiff)

w("\n\n=== ORDER check: same order?")
w("base order [:8] = %s" % [c.get('internal_name') for c in b['civilization_list'][:8]])
w("mod  order [:8] = %s" % [c.get('internal_name') for c in m['civilization_list'][:8]])
w("identical order: %s" % ([c.get('internal_name') for c in b['civilization_list']] == [c.get('internal_name') for c in m['civilization_list']]))

# 550749 linkedTechs
w("\n\n=== linkedTechs.json base vs mod 550749")
lb = load(os.path.join(BASE, "linkedTechs.json"))
lm = load(os.path.join(M550, "linkedTechs.json"))
w("base n=%d  mod n=%d" % (len(lb["LinkedTechs"]), len(lm["LinkedTechs"])))
bid = {e["NameId"]: e for e in lb["LinkedTechs"]}
mid = {e["NameId"]: e for e in lm["LinkedTechs"]}
w("only in base NameIds: %s" % sorted(set(bid) - set(mid)))
w("only in mod  NameIds: %s" % sorted(set(mid) - set(bid)))
for nid in sorted(set(bid) & set(mid)):
    if bid[nid] != mid[nid]:
        w("  CHANGED %s: base=%s  mod=%s" % (nid, json.dumps(bid[nid], ensure_ascii=False), json.dumps(mid[nid], ensure_ascii=False)))
w("\nfull MOD linkedTechs:")
for e in lm["LinkedTechs"]:
    w("   %s" % json.dumps(e, ensure_ascii=False))

open(os.path.join(OUT, "s21_modcivdiff.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue()[:9000])
