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

# All TKN_* tokens
w("### all TKN_* tokens ###\n")
tk = sorted(set(m.group().decode("ascii") for m in re.finditer(rb"TKN_[A-Z0-9_]{2,40}", data)))
w("count: %d\n" % len(tk))
for t in tk:
    w("  %s\n" % t)

# All distinct 'Error: Parsing script' style messages + neighbours
w("\n### script-parser error/help strings (0x32df000-0x32e0000) ###\n")
lo, hi = 0x32dea00, 0x32e0200
seg = data[lo:hi]
for m in re.finditer(rb"[\x20-\x7e]{8,220}", seg):
    s = m.group().decode("ascii")
    w("  0x%08x  %s\n" % (lo + m.start(), s))

# Any other "script" surface: strings with .fst / script file extension
w("\n### script file extensions / TKN context anywhere ###\n")
for pat in [rb"\.fst\b", rb"\.txt\b.{0,40}script", rb"script.{0,30}\.txt", rb"autotest", rb"civ_?crash"]:
    for m in re.finditer(pat, data, re.I):
        o = m.start()
        ctx = data[max(0, o - 60):o + 80]
        s = "".join(chr(b) if 32 <= b < 127 else "." for b in ctx)
        w("  [%s] 0x%x  %s\n" % (pat.decode(), o, s))

txt = out.getvalue()
io.open(_HERE_PATH("_probe", "ui_surfaces", "exe_tkn.txt"), "w", encoding="utf-8").write(txt)
print("TKN_ tokens:", len(tk))
print(", ".join(tk))
