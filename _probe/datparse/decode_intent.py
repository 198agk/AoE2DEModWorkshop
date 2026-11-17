import os as _os, sys as _sys
_p = _os.path.dirname(_os.path.abspath(__file__))
while _p and not _os.path.isfile(_os.path.join(_p, "_gamepaths.py")):
    _p = _os.path.dirname(_p)
if _p and _p not in _sys.path:
    _sys.path.insert(0, _p)
import _gamepaths as GP
"""Human-readable decode of the 10x mod's signature effects.
This is the prototype of 'intent -> data': turn raw EffectCommands into a sentence
a player would understand, using the verified schema tables.
"""
import os, sys, io, json, contextlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import parse_dat as P

SCHEMA = os.path.join(os.path.dirname(HERE), "schema")
TYPES = json.load(open(os.path.join(SCHEMA, "effect_command_types.json"), encoding="utf-8"))["types"]
ATTRS = json.load(open(os.path.join(SCHEMA, "effect_attributes.json"), encoding="utf-8"))["attributes"]
ARMOR = json.load(open(os.path.join(SCHEMA, "armor_classes.json"), encoding="utf-8"))

MODS = GP.SUBSCRIBED
D10 = [os.path.join(MODS, n) for n in os.listdir(MODS) if n.startswith("550749")][0]
BASE = GP.DAT
M10 = os.path.join(D10, "resources", "_common", "dat", "empires2_x2_p1.dat")


def load(path):
    data, _ = P.load_dat(path)
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    return p.stats


def attr_name(c):
    return ATTRS.get(str(c), "Attr %s" % c)


def cls_name(b):
    if isinstance(ARMOR, dict):
        for k in ("class_names", "classes", "armor_classes"):
            if k in ARMOR and isinstance(ARMOR[k], dict):
                return ARMOR[k].get(str(b), "Class %s" % b)
    return "Class %s" % b


def describe(cmd):
    t, A, B, C, D = cmd
    info = TYPES.get(str(t))
    label = info["label"] if info else "Type %d" % t
    who = "all units" if A == -1 else ("unit %s" % A)
    if B is not None and B != -1:
        who = cls_name(B)
    low = label.lower()
    if "attribute" in low:
        return "%s: %s = %s  [%s]" % (label, attr_name(C), D, who)
    if "resource" in low:
        return "%s: resource %s = %s  [%s]" % (label, C if C != -1 else A, D, who)
    return "%s: A=%s B=%s C=%s D=%s" % (label, A, B, C, D)


print("=" * 78)
print("MOD: 10x resources  (decoded)")
print("=" * 78)
s = load(M10)
em = s["effects"]
for idx in (4987, 5535, 4999, 5534):
    if idx >= len(em):
        continue
    raw = em[idx]["name"]
    try:
        nm = raw.encode("latin-1").decode("gb18030")
    except Exception:
        nm = raw
    print("\neffect[%d]  %s" % (idx, nm))
    for c in em[idx]["commands"]:
        print("    ", describe(c))

print("\n" + "=" * 78)
print("BASE for comparison")
print("=" * 78)
b = load(BASE)
print("BASE effects=%d techs=%d" % (len(b["effects"]), len(b["techs"])))
be = b["effects"]
# find the vanilla analogous effect
for idx in (0, 1, 100):
    if idx < len(be):
        print("\nBASE effect[%d] %r" % (idx, be[idx]["name"][:50]))
        for c in be[idx]["commands"][:6]:
            print("    ", describe(c))
