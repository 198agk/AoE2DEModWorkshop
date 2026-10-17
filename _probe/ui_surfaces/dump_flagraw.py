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

def hexdump(lo, hi, label):
    w("\n########## %s [0x%x-0x%x] ##########\n" % (label, lo, hi))
    seg = data[lo:hi]
    for i in range(0, len(seg), 16):
        chunk = seg[i:i + 16]
        hexs = " ".join("%02x" % b for b in chunk)
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        w("  0x%08x  %-47s  %s\n" % (lo + i, hexs, asc))

# flag table region raw
hexdump(0x3258ef0, 0x3259140, "flag table raw (EXIT / RUN_REGRESSION_TESTS)")
# the +DummyVoiceChat region raw
hexdump(0x31f9450, 0x31f94c0, "+DummyVoiceChat region raw")
# tool manager table
hexdump(0x334e7a0, 0x334e900, "tool manager table raw")

# probe for + prefixed flags
w("\n### '+FLAG' style probes (whole exe) ###\n")
found = {}
for m in re.finditer(rb"\+[A-Za-z][A-Za-z0-9_]{2,40}", data):
    s = m.group().decode("ascii")
    found.setdefault(s, []).append(m.start())
w("distinct '+Flag' strings: %d\n" % len(found))
for s in sorted(found):
    w("  %-44s x%d  @0x%x\n" % (s, len(found[s]), found[s][0]))

txt = out.getvalue()
io.open(_HERE_PATH("_probe", "ui_surfaces", "exe_flagraw.txt"), "w", encoding="utf-8").write(txt)
print(txt[:9000])
