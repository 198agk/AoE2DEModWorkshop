import os, io, re, json
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\json_layer"
SRC = r"D:\Software\DeepSeek Harness\工作区2\_probe\source"
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

w("=== search ALL shipped tool source for the 7 unitcategories.json names ===")
names = ["Infantry", "Cavalry", "Archers", "CavalryArchers", "Monks", "Warboats", "SiegeWeapons",
         "CavalryArcher", "SiegeWeapon", "Warship", "Archer", "Monk"]
hits = {n: [] for n in names}
for root, dirs, files in os.walk(SRC):
    for fn in files:
        if os.path.splitext(fn)[1].lower() not in (".h", ".hpp", ".cpp", ".cc", ".c", ".py", ".txt", ".ini", ".json"):
            continue
        fp = os.path.join(root, fn)
        try:
            t = open(fp, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        for n in names:
            if n in t:
                hits[n].append(os.path.relpath(fp, SRC))
for n in names:
    w("  %-16s files=%d %s" % (n, len(hits[n]), hits[n][:4]))

w("")
w("=== AGE3NamesV0007.ini : look for unit-class names ===")
ini = r"D:\Games\Steam\steamapps\common\AoE2DE\Tools_Builds\AGE3NamesV0007.ini"
t = open(ini, "rb").read().decode("utf-8", "ignore")
lines = t.splitlines()
w("  total lines=%d" % len(lines))
for n in names:
    c = [l for l in lines if n.lower() in l.lower()]
    w("  %-16s lines=%d  %s" % (n, len(c), c[:3]))
# where do section headers look like?
w("  section headers sample = %s" % [l for l in lines if l.startswith("[")][:20])
w("  lines containing 'Unit Class' or 'class' = %s" % [l for l in lines if "class" in l.lower()][:12])
open(os.path.join(OUT, "s58_unitclass.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())
