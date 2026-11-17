import os as _os, sys as _sys
_p = _os.path.dirname(_os.path.abspath(__file__))
while _p and not _os.path.isfile(_os.path.join(_p, "_gamepaths.py")):
    _p = _os.path.dirname(_p)
if _p and _p not in _sys.path:
    _sys.path.insert(0, _p)
import _gamepaths as GP
"""Commands-only diff of the first 1500 effects: which commands did the mod actually change?"""
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

b = load(GAME); m = load(M10)
eb, em = b.stats["effects"], m.stats["effects"]

cmd_diff = [i for i in range(1500) if eb[i]["commands"] != em[i]["commands"]]
print("=== first-1500 effects where COMMANDS changed: %d / 1500 ===" % len(cmd_diff))

# categorise the change
print("\n=== sample of command changes (original effect semantics) ===")
for i in cmd_diff[:40]:
    bc, mc = eb[i]["commands"], em[i]["commands"]
    print("  eff[%d] %-30s" % (i, repr(eb[i]["name"])[:30]))
    print("      base: %s" % (bc[:4],))
    print("      mod : %s" % (mc[:4],))

# Aggregate: what command types appear in the changed effects, and how?
print("\n=== command types present in changed effects (base vs mod) ===")
cb, cm = collections.Counter(), collections.Counter()
for i in cmd_diff:
    for c in eb[i]["commands"]: cb[c[0]] += 1
    for c in em[i]["commands"]: cm[c[0]] += 1
for t in sorted(set(cb) | set(cm)):
    print("   type %-4s base=%-6s mod=%-6s" % (t, cb.get(t,0), cm.get(t,0)))

# Look for the resource-multiply story: type 6 anywhere
print("\n=== ALL type-6 (Resource Multiply) commands in each file, grouped by A (resource id) ===")
for label, e in (("BASE", eb), ("MOD", em)):
    g = collections.defaultdict(list)
    for i in range(len(e)):
        for c in e[i]["commands"]:
            if c[0] == 6:
                g[c[1]].append((i, c[4]))
    print("  %s: %d resource ids touched" % (label, len(g)))
    for a in sorted(g):
        vals = sorted(set(v for _, v in g[a]))
        print("      resource %-5s x%-4d multipliers=%s" % (a, len(g[a]), vals[:8]))

print("\n=== type 1 (Resource Set/Change) grouped by (A,B) ===")
for label, e in (("BASE", eb), ("MOD", em)):
    g = collections.defaultdict(list)
    for i in range(len(e)):
        for c in e[i]["commands"]:
            if c[0] == 1:
                g[(c[1], c[2])].append(c[4])
    print("  %s: %d (A,B) pairs" % (label, len(g)))
