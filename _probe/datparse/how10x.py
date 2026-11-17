import os as _os, sys as _sys
_p = _os.path.dirname(_os.path.abspath(__file__))
while _p and not _os.path.isfile(_os.path.join(_p, "_gamepaths.py")):
    _p = _os.path.dirname(_p)
if _p and _p not in _sys.path:
    _sys.path.insert(0, _p)
import _gamepaths as GP
"""How do real data mods implement themselves?

Focus: the effect-command layer. This is where '10x resources' / '2x tech' live.
"""
import os, sys, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parse_dat as P

GAME = GP.DAT
MODS = GP.SUBSCRIBED

def find(prefix):
    for n in os.listdir(MODS):
        if n.startswith(prefix):
            return os.path.join(MODS, n)
    raise SystemExit("no mod with prefix " + prefix)

M10  = find("550749")
MJUN = find("423821")
print("M10 =", M10)

def load(path):
    data, _ = P.load_dat(path)
    p = P.Parser(data)
    import io, contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    return p

def eff(d):
    return d.stats["effects"]

def hist(d):
    c = collections.Counter()
    for e in eff(d):
        for cmd in e["commands"]:
            c[cmd[0]] += 1
    return c

print("loading base..."); b = load(GAME)
print("loading 10x ..."); m = load(os.path.join(M10, "resources", "_common", "dat", "empires2_x2_p1.dat"))

hb, hm = hist(b), hist(m)
print("\n=== effect command TYPE counts (type: base -> mod) ===")
for t in sorted(set(hb) | set(hm)):
    print("  type %-4s base=%-7s mod=%-7s" % (t, hb.get(t,0), hm.get(t,0)))

# The interesting part: which effects are NEW in the mod, and what do they do?
bnames = [e["name"] for e in eff(b)]
mnames = [e["name"] for e in eff(m)]
print("\n=== base effect names (first 40, non-empty) ===")
seen = [n for n in bnames if n][:40]
for n in seen:
    print("   ", n)

# Effects referenced by the mod's NEW techs
btech = b.stats["techs"]
mtech = m.stats["techs"]
print("\n=== tech count base=%d mod=%d ===" % (len(btech), len(mtech)))
newtech = [t for t in mtech[len(btech):]]
print("new techs:", len(newtech), "with effect_id>=0:",
      sum(1 for t in newtech if t["effect_id"] is not None and t["effect_id"] >= 0))
byname = collections.Counter(t["name"] for t in newtech)
print("new-tech names:", byname.most_common(20))

# effects actually referenced by mod's new techs
refd = [t["effect_id"] for t in newtech if t["effect_id"] is not None and 0 <= t["effect_id"] < len(eff(m))]
print("distinct effects referenced by new techs:", len(set(refd)))
for ei in list(dict.fromkeys(refd))[:25]:
    e = eff(m)[ei]
    print("   effect[%d] name=%-28s commands=%s" % (ei, repr(e["name"])[:28], e["commands"]))

# Search all mod effects for resource-ish types
print("\n=== mod effects using resource-modifier types (1,6,31,36,41,46,11,16) ===")
RES = {1,6,11,16,21,26,31,36,41,46}
hits = collections.Counter()
for i, e in enumerate(eff(m)):
    for cmd in e["commands"]:
        if cmd[0] in RES:
            hits[cmd] += 1
print("  total resource commands:", sum(hits.values()))
for cmd, n in hits.most_common(30):
    print("   type=%-3s A=%-6s B=%-7s C=%-6s D=%-8s  x%d" % (cmd[0], cmd[1], cmd[2], cmd[3], cmd[4], n))
