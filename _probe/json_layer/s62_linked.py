import os, io, json
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\json_layer"
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
BASE = os.path.join(GAME, "resources", "_common", "dat")
POM = os.path.join(GAME, "modes", "Pompeii", "resources", "_common", "dat")
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

bj = json.load(open(os.path.join(BASE, "linkedTechs.json"), encoding="utf-8-sig"))
pj = json.load(open(os.path.join(POM, "linkedTechs.json"), encoding="utf-8-sig"))
w("=== linkedTechs NameId overlap: base 20 vs pompeii 1 ===")
bn = {e["NameId"]: e for e in bj["LinkedTechs"]}
pn = {e["NameId"]: e for e in pj["LinkedTechs"]}
w("  base NameIds    = %s" % sorted(bn))
w("  pompeii NameIds = %s" % sorted(pn))
for k in sorted(pn):
    w("  NameId %s" % k)
    w("    base    : %s" % json.dumps(bn.get(k), ensure_ascii=False))
    w("    pompeii : %s" % json.dumps(pn[k], ensure_ascii=False))

w("")
w("=== selection_group_def.json: base vs pompeii parse failure ===")
tb = open(os.path.join(BASE, "selection_group_def.json"), "rb").read().decode("utf-8-sig")
tp = open(os.path.join(POM, "selection_group_def.json"), "rb").read().decode("utf-8-sig")
try:
    json.loads(tb); w("  base: parses OK")
except Exception as e:
    w("  base: PARSE FAIL %s" % e)
try:
    json.loads(tp); w("  pompeii: parses OK")
except Exception as e:
    w("  pompeii: PARSE FAIL %s" % e)
lines = tp.splitlines()
w("  pompeii lines around 375-390:")
for i in range(370, min(392, len(lines))):
    w("    %4d| %s" % (i + 1, lines[i]))
w("")
w("  base lines around the same construct (search 'radial_data'):")
for i, l in enumerate(tb.splitlines()):
    if "radial_data" in l:
        w("    %4d| %s" % (i + 1, l))
        for j in range(i, min(i + 8, len(tb.splitlines()))):
            w("    %4d| %s" % (j + 1, tb.splitlines()[j]))
        break
open(os.path.join(OUT, "s62_linked.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())
