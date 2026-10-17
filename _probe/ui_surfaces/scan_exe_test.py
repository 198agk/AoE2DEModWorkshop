import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import re, io, sys

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
data = open(EXE, "rb").read()
out = io.StringIO()
w = out.write

ASCII_RUN = re.compile(rb"[\x20-\x7e]{4,}")
runs = [(m.start(), m.group().decode("ascii")) for m in ASCII_RUN.finditer(data)]
w("total ascii runs >=4: %d\n" % len(runs))

def find(pat, label, limit=40):
    rx = re.compile(pat, re.I)
    hits = [(o, s) for (o, s) in runs if rx.search(s)]
    w("\n=== %s : %d hits ===\n" % (label, len(hits)))
    for o, s in hits[:limit]:
        w("  0x%x  %s\n" % (o, s[:150]))
    return hits

find(r"testharness|test_harness", "testharness")
find(r"regression", "regression")
find(r"^--", "cli flags starting --")
find(r"-[a-z]*auto[a-z]*", "auto*")
find(r"headless|no_?window|norender|batch", "headless/batch")
find(r"replay.*(play|run|speed)|playspeed", "replay automation")
find(r"check.?sum|checksum", "checksum")
find(r"determinis|deterministic|lockstep|sim_?sync", "determinism")

w("\n=== distinct strings containing 'test' (len<=40) ===\n")
seen = set()
for o, s in runs:
    if re.search(r"test", s, re.I) and len(s) <= 40:
        if s not in seen:
            seen.add(s)
w("count: %d\n" % len(seen))
for s in sorted(seen)[:120]:
    w("  %s\n" % s)

txt = out.getvalue()
io.open(_HERE_PATH("_probe", "ui_surfaces", "exe_testharness.txt"), "w", encoding="utf-8").write(txt)
print(txt[:6000])
