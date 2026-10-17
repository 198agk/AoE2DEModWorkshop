import os, io, json, re, hashlib
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\json_layer"
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
BASE = os.path.join(GAME, "resources", "_common", "dat")
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

w("=" * 90)
w("N. ALL copies of each in-scope JSON anywhere under the GAME tree (overlay/precedence map)")
w("=" * 90)
NAMES = ["AIConsts.json","adapterblacklist.json","airesourcetypes.json","buttons.json",
         "civilizations.json","civTechTrees.json","dropsites.json","eras.json",
         "futuravailableunits.json","hotkeys.json","linkedTechs.json","linkedUnits.json","maps.json",
         "objreplacement.json","selection_group_def.json","sharedbuildings.json","sounds.json",
         "unitcategories.json","unitlines.json","morematerials.json","materials.json"]
found = {n: [] for n in NAMES}
for root, dirs, files in os.walk(GAME):
    for fn in files:
        if fn in found:
            fp = os.path.join(root, fn)
            found[fn].append((os.path.relpath(fp, GAME), os.path.getsize(fp)))
for n in NAMES:
    w("  %-26s copies=%d" % (n, len(found[n])))
    for p, s in found[n]:
        w("        %-72s %9d B" % (p, s))

w("")
w("=" * 90)
w("O. string-table overlay ('-modded-') files: does the pattern exist?")
w("=" * 90)
res = os.path.join(GAME, "resources")
for d in sorted(os.listdir(res)):
    kv = os.path.join(res, d, "strings", "key-value")
    if os.path.isdir(kv):
        fs = sorted(os.listdir(kv))
        w("  %-10s %s" % (d, fs))
w("  content of en\\...\\key-value-modded-strings-utf8.txt (first 200 B):")
p = os.path.join(res, "en", "strings", "key-value", "key-value-modded-strings-utf8.txt")
if os.path.exists(p):
    w("     %r  (%d B)" % (open(p, "rb").read()[:200], os.path.getsize(p)))
p2 = os.path.join(res, "_common", "non-localized-key-value-strings-utf8.txt")
w("  %s exists=%s" % (p2, os.path.exists(p2)))

w("")
w("=" * 90)
w("P. user-mod tree: every dat-dir JSON shipped by any mod")
w("=" * 90)
USER = r"C:\Users\26913\Games\Age of Empires 2 DE"
for root, dirs, files in os.walk(USER):
    if "_common" in root and "dat" in root.split(os.sep)[-1:]:
        for fn in files:
            fp = os.path.join(root, fn)
            w("  %-110s %9d B" % (os.path.relpath(fp, USER), os.path.getsize(fp)))

w("")
w("=" * 90)
w("Q. Does widgetui\\futuravailableunits.json == dat\\futuravailableunits.json ?")
w("=" * 90)
a = os.path.join(BASE, "futuravailableunits.json")
b = os.path.join(GAME, "widgetui", "futuravailableunits.json")
for p in (a, b):
    if os.path.exists(p):
        h = hashlib.md5(open(p, "rb").read()).hexdigest()
        w("  %-70s %9d B  md5=%s" % (os.path.relpath(p, GAME), os.path.getsize(p), h))
    else:
        w("  %s MISSING" % p)
if os.path.exists(a) and os.path.exists(b):
    ja = json.loads(open(a, "rb").read().decode("utf-8-sig"))
    jb = json.loads(open(b, "rb").read().decode("utf-8-sig"))
    w("  identical content: %s" % (ja == jb))
    w("  keys A=%d B=%d ; A-only=%s B-only=%s" % (
        len(ja), len(jb), sorted(set(ja) - set(jb))[:8], sorted(set(jb) - set(ja))[:8]))
# and the dat-dir widgetui
w("")
w("=" * 90)
w("R. 'widgetui' json copies in the dat dir:")
w("=" * 90)
for root, dirs, files in os.walk(os.path.join(GAME, "widgetui")):
    for fn in files:
        if fn.endswith(".json"):
            fp = os.path.join(root, fn)
            w("  %-70s %9d B" % (os.path.relpath(fp, GAME), os.path.getsize(fp)))
open(os.path.join(OUT, "s47_overlay.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())
