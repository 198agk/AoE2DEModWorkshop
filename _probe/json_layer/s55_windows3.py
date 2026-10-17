import os, io, re
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\json_layer"
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
exe = open(os.path.join(GAME, "AoE2DE_s.exe"), "rb").read()
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

def window(center, before=1500, after=1500):
    lo, hi = max(0, center - before), min(len(exe), center + after)
    w("--- window @%d  [%d..%d] ---" % (center, lo, hi))
    for m in re.finditer(rb"[\x20-\x7e]{4,}", exe[lo:hi]):
        w("  %8d  %s" % (lo + m.start(), m.group(0).decode("latin-1")))

w("=" * 90); w("A. '*.json' @52536472 - a directory-scan / glob loader?"); w("=" * 90)
window(52536472)

w(""); w("=" * 90); w("B. bare '.json' @52429848"); w("=" * 90)
window(52429848, 900, 900)

w(""); w("=" * 90); w("C. civTechTrees.json @53352056"); w("=" * 90)
window(53352056, 1200, 1200)

w(""); w("=" * 90); w("D. linkedUnits.json @52798912 - wide window (is there a parse site?)"); w("=" * 90)
window(52798912, 2200, 2200)
open(os.path.join(OUT, "s55_windows3.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())
