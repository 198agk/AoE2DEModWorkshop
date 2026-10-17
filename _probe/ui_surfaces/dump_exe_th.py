import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import re, io

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
data = open(EXE, "rb").read()
out = io.StringIO()
w = out.write

def dump(lo, hi, label, minlen=3):
    w("\n########## %s  [0x%x - 0x%x] ##########\n" % (label, lo, hi))
    seg = data[lo:hi]
    for m in re.finditer(rb"[\x20-\x7e]{%d,}" % minlen, seg):
        s = m.group().decode("ascii")
        if len(s) >= minlen:
            w("  0x%08x  %s\n" % (lo + m.start(), s[:170]))

# test harness command table
dump(0x31f8800, 0x31f9500, "testharness storage/command names")
dump(0x3222400, 0x3222700, "testharness UI events")
dump(0x3258800, 0x3258600 + 0x400, "TEST_HARNESS_COMM + neighbours")
dump(0x3258f00, 0x3259300, "regression command table start")
dump(0x334d300, 0x334e900, "Regression tool strings")

txt = out.getvalue()
io.open(_HERE_PATH("_probe", "ui_surfaces", "exe_th_dump.txt"), "w", encoding="utf-8").write(txt)
print(txt)
