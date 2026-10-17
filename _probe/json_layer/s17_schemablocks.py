import re, io, os
EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
buf = open(EXE, "rb").read()
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\json_layer"
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")
def dump(lo, hi, label, maxs=90, minlen=4):
    seg = buf[lo:hi]
    w("\n=== %s [%d..%d]" % (label, lo, hi))
    for m in re.finditer(rb"[\x20-\x7e]{%d,}" % minlen, seg):
        w("  @%-9d %s" % (lo + m.start(), m.group().decode("ascii")))

dump(52548800, 52552500, "futuravailableunits SCHEMA BLOCK @52549936", 130, 4)
dump(53370000, 53370800, "paphosfutureavailableunits SCHEMA BLOCK @53370528", 40, 4)
open(os.path.join(OUT, "s17_schemablocks.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())
