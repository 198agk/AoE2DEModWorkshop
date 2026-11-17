import os as _os, sys as _sys
_p = _os.path.dirname(_os.path.abspath(__file__))
while _p and not _os.path.isfile(_os.path.join(_p, "_gamepaths.py")):
    _p = _os.path.dirname(_p)
if _p and _p not in _sys.path:
    _sys.path.insert(0, _p)
import _gamepaths as GP
"""Identify the exact effect commands that implement '10x resources' / '2x tech'."""
import os, sys, collections, io, contextlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parse_dat as P

GAME = GP.DAT
MODS = GP.SUBSCRIBED
M10 = [os.path.join(MODS, n) for n in os.listdir(MODS) if n.startswith("550749")][0]
M10 = os.path.join(M10, "resources", "_common", "dat", "empires2_x2_p1.dat")

def load(path):
    data, _ = P.load_dat(path)
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    return p

b = load(GAME)
m = load(M10)
eb, em = b.stats["effects"], m.stats["effects"]

# ---- 1. Are the ORIGINAL 1500 effects identical? --------------------------
same = 0
diff = []
for i in range(min(len(eb), len(em))):
    if eb[i]["commands"] == em[i]["commands"] and eb[i]["name"] == em[i]["name"]:
        same += 1
    else:
        diff.append(i)
print("=== base effects vs mod[0:1500] ===")
print("  identical: %d / 1500" % same)
print("  differing indexes: %d  (first 30: %s)" % (len(diff), diff[:30]))
for i in diff[:12]:
    print("    [%d] base name=%r cmd=%s" % (i, eb[i]["name"][:22], eb[i]["commands"][:3]))
    print("         mod  name=%r cmd=%s" % (em[i]["name"][:22], em[i]["commands"][:3]))

# ---- 2. New effects (index >= 1500) that multiply resources heavily --------
print("\n=== NEW effect commands with type 6 (Resource Multiply), D>=2 or D<=0.5 ===")
n = 0
for i in range(1500, len(em)):
    for cmd in em[i]["commands"]:
        if cmd[0] == 6 and (cmd[4] >= 2.0 or 0 < cmd[4] <= 0.5):
            print("   eff[%d] %-22s A(res)=%-6s B=%-4s C=%-6s D=%s"
                  % (i, repr(em[i]["name"])[:22], cmd[1], cmd[2], cmd[3], cmd[4]))
            n += 1
            if n > 25: break
    if n > 25: break
print("   (shown %d)" % n)

print("\n=== NEW effect commands with type 101 (Tech Cost Modifier) / 103 (Tech Time) ===")
for t in (101, 103):
    c = collections.Counter()
    for i in range(1500, len(em)):
        for cmd in em[i]["commands"]:
            if cmd[0] == t:
                c[(cmd[1], cmd[2], cmd[4])] += 1
    print("  type %d: %d distinct (A,B,D) triples; top 15:" % (t, len(c)))
    for k, v in c.most_common(15):
        print("      A=%-6s B=%-5s D=%-8s  x%d" % (k[0], k[1], k[2], v))

print("\n=== NEW effect commands with type 8 (Modify Tech) ===")
c = collections.Counter()
for i in range(1500, len(em)):
    for cmd in em[i]["commands"]:
        if cmd[0] == 8:
            c[(cmd[1], cmd[2], cmd[3], cmd[4])] += 1
print("  %d distinct; top 15:" % len(c))
for k, v in c.most_common(15):
    print("      A=%-6s B=%-6s C=%-6s D=%-8s x%d" % (k[0], k[1], k[2], k[3], v))

print("\n=== type 255 (unnamed) — base vs mod, with A/B/C/D ===")
for label, e, lo in (("base", eb, 0), ("mod", em, 1500)):
    c = collections.Counter()
    hi = len(e) if label == "mod" else len(e)
    for i in range(lo, hi):
        for cmd in e[i]["commands"]:
            if cmd[0] == 255:
                c[cmd[1:]] += 1
    print("  %s: %d distinct payloads; top 10:" % (label, len(c)))
    for k, v in c.most_common(10):
        print("      A=%-6s B=%-6s C=%-6s D=%-8s x%d" % (k[0], k[1], k[2], k[3], v))
