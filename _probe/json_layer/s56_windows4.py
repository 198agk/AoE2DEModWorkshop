import os, io, re
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\json_layer"
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
exe = open(os.path.join(GAME, "AoE2DE_s.exe"), "rb").read()
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")
def window(center, before, after, label):
    lo, hi = max(0, center - before), min(len(exe), center + after)
    w("--- %s @%d [%d..%d] ---" % (label, center, lo, hi))
    for m in re.finditer(rb"[\x20-\x7e]{4,}", exe[lo:hi]):
        w("  %8d  %s" % (lo + m.start(), m.group(0).decode("latin-1")))

window(53359544, 700, 700, "unitcategories.json")
w("")
window(53017296, 400, 1700, "eras.json/civilizations.json")
w("")
window(53053040, 500, 900, "linkedTechs.json")
w("")
window(53262528, 250, 1250, "maps.json")
open(os.path.join(OUT, "s56_windows4.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())
