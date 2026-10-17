import os, io, re
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\json_layer"
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
exe = open(os.path.join(GAME, "AoE2DE_s.exe"), "rb").read()
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")
def win(c, b, a, lbl):
    lo, hi = max(0, c - b), min(len(exe), c + a)
    w("--- %s @%d [%d..%d] ---" % (lbl, c, lo, hi))
    for m in re.finditer(rb"[\x20-\x7e]{4,}", exe[lo:hi]):
        w("  %8d  %s" % (lo + m.start(), m.group(0).decode("latin-1")))

win(53278385, 900, 900, "chronicles_ prefix / mod file exists")
w("")
for m in re.finditer(b"rgid", exe):
    win(m.start(), 250, 250, "rgid @%d" % m.start())
w("")
win(53259600, 1500, 400, "hotkeys.json full parse site")
open(os.path.join(OUT, "s65_chronicles.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())
