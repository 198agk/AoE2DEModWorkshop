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
    w("\n########## %s [0x%x-0x%x] ##########\n" % (label, lo, hi))
    seg = data[lo:hi]
    for m in re.finditer(rb"[\x20-\x7e]{%d,}" % minlen, seg):
        w("  0x%08x  %s\n" % (lo + m.start(), m.group().decode("ascii")))

# The tool manager flag table
dump(0x334d600, 0x334ea00, "TOOL MANAGER flag table")

# The other regression table near 0x32590e0
dump(0x3258c00, 0x3259500, "regression table near 0x32590e0")

# NO_WINDOW and window constants
dump(0x350a280, 0x350a500, "window mode constants")

txt = out.getvalue()
io.open(_HERE_PATH("_probe", "ui_surfaces", "exe_flags2.txt"), "w", encoding="utf-8").write(txt)
print(txt)
