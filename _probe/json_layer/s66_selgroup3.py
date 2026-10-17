import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, io, re
OUT = _HERE_PATH("_probe", "json_layer")
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
exe = open(os.path.join(GAME, "AoE2DE_s.exe"), "rb").read()
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")
def win(c, b, a, lbl):
    lo, hi = max(0, c - b), min(len(exe), c + a)
    w("--- %s @%d ---" % (lbl, c))
    for m in re.finditer(rb"[\x20-\x7e]{4,}", exe[lo:hi]):
        w("  %8d  %s" % (lo + m.start(), m.group(0).decode("latin-1")))

w("=== every string containing 'group' right before a '.json' or 'def' ===")
for m in re.finditer(rb"[\x20-\x7e]{4,}", exe):
    s = m.group(0).decode("latin-1")
    if ("group" in s.lower() and ("json" in s.lower() or "def" in s.lower())):
        w("  %8d  %s" % (m.start(), s))
w("")
w("=== every string ending in '_def' or '_def.json' or containing 'def.json' ===")
for m in re.finditer(rb"[\x20-\x7e]{3,}", exe):
    s = m.group(0).decode("latin-1")
    if s.endswith("_def") or "def.json" in s:
        w("  %8d  %s" % (m.start(), s))
w("")
w("=== strings that look like a filename prefix ending with '_' (potential <prefix>+file assembly) ===")
cands = set()
for m in re.finditer(rb"\b[a-z][a-z0-9_]{2,24}_\x00", exe):
    cands.add(m.group(0)[:-1].decode("latin-1"))
for c in sorted(cands):
    if any(k in c for k in ("paphos", "chronicles", "pompeii", "peru", "paris", "portland", "providence", "base", "mod")):
        w("  %s" % c)
w("")
w("=== ALL strings mentioning 'Selection' with context (dedup) ===")
seen = set()
for m in re.finditer(rb"[\x20-\x7e]*[Ss]election[\x20-\x7e]*", exe):
    s = m.group(0).decode("latin-1")
    if s not in seen and len(s) < 70:
        seen.add(s)
for s in sorted(seen):
    w("  %s" % s)
open(os.path.join(OUT, "s66_selgroup3.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue()[:9000])
