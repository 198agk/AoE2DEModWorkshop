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

def dump(lo, hi, label, minlen=4):
    w("\n########## %s  [0x%x - 0x%x] ##########\n" % (label, lo, hi))
    seg = data[lo:hi]
    for m in re.finditer(rb"[\x20-\x7e]{%d,}" % minlen, seg):
        s = m.group().decode("ascii")
        w("  0x%08x  %s\n" % (lo + m.start(), s[:200]))

# Full up-* command list (test harness / script API)
lo = 0x3222400
hi = 0x3224000
w("\n########## all 'up-*' command names ##########\n")
ups = []
for m in re.finditer(rb"up-[a-z0-9\-]{3,}", data):
    s = m.group().decode("ascii")
    if s not in ups:
        ups.append(s)
w("distinct up-* count: %d\n" % len(ups))
for s in ups:
    w("  %s\n" % s)

# find all CLI flag descriptions: uppercase flags with lowercase description nearby
w("\n########## CLI flag candidates (TOKEN + description) ##########\n")
# flags are ALL_CAPS_WITH_UNDERSCORES, 6..40 chars, and descriptions are sentences
tok = re.compile(rb"\b[A-Z][A-Z0-9_]{4,40}\b")
cands = {}
for m in tok.finditer(data):
    s = m.group().decode("ascii")
    if s in cands:
        continue
    cands[s] = m.start()
w("distinct ALLCAPS tokens: %d\n" % len(cands))

# dump the region containing the flag/description table
dump(0x3258f00, 0x325b400, "flag description table A")

txt = out.getvalue()
io.open(_HERE_PATH("_probe", "ui_surfaces", "exe_cli_dump.txt"), "w", encoding="utf-8").write(txt)
print("written, length", len(txt))
print("\n".join(txt.splitlines()[:20]))
