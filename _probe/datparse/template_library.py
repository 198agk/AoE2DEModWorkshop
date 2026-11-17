import os as _os, sys as _sys
_p = _os.path.dirname(_os.path.abspath(__file__))
while _p and not _os.path.isfile(_os.path.join(_p, "_gamepaths.py")):
    _p = _os.path.dirname(_p)
if _p and _p not in _sys.path:
    _sys.path.insert(0, _p)
import _gamepaths as GP
"""Template library: for every EffectCommand type used in the VANILLA dat, find a real
example (tech name + commands decoded to plain language). These are verified, in-game
precedents for each kind of gameplay change -> the backbone of 'intent -> data'.
"""
import os, sys, io, json, contextlib, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import parse_dat as P

SCHEMA = os.path.join(os.path.dirname(HERE), "schema")
TYPES = json.load(open(os.path.join(SCHEMA, "effect_command_types.json"), encoding="utf-8"))["types"]
ATTRS = json.load(open(os.path.join(SCHEMA, "effect_attributes.json"), encoding="utf-8"))["attributes"]
BASE = GP.DAT

data, _ = P.load_dat(BASE)
p = P.Parser(data)
with contextlib.redirect_stdout(io.StringIO()):
    p.parse()
s = p.stats
techs, effects = s["techs"], s["effects"]

# semantic names: unit id -> english name, from the semantic layer if present
SEM = os.path.join(os.path.dirname(HERE), "semantic", "unit_names.json")
unit_en = {}
if os.path.exists(SEM):
    j = json.load(open(SEM, encoding="utf-8"))
    src = j.get("units", j)
    if isinstance(src, dict):
        for k, v in src.items():
            if isinstance(v, dict):
                unit_en[int(k)] = v.get("en") or v.get("name") or ""
            elif isinstance(v, str):
                unit_en[int(k)] = v
    elif isinstance(src, list):
        for i, v in enumerate(src):
            if isinstance(v, dict):
                unit_en[i] = v.get("en") or ""
print("unit names loaded: %d" % len(unit_en))

# which tech references each effect
eff2tech = {}
for ti, t in enumerate(techs):
    e = t.get("effect_id", -1)
    if e is not None and e >= 0:
        eff2tech.setdefault(e, []).append(ti)


def attr_name(c):
    return ATTRS.get(str(c), "Attr %s" % c)


def who(A, B):
    if B is not None and B != -1:
        return "class %s" % B
    if A == -1:
        return "all units"
    return "%s (unit %s)" % (unit_en.get(A, ""), A) if A in unit_en else "unit %s" % A


def describe(cmd):
    t, A, B, C, D = cmd
    info = TYPES.get(str(t))
    label = info["label"] if info else "Type %d" % t
    low = label.lower()
    if "attribute" in low and "own master" not in low:
        return "%s | %s -> %s = %s" % (label, who(A, B), attr_name(C), D)
    if "resource" in low and "own master" not in low:
        return "%s | resource %s (A) = %s" % (label, A if A != -1 else C, D)
    if "enable" in low:
        return "%s | %s" % ("Enable" if B not in (0, None) else "Disable",
                            who(A, -1))
    if "spawn" in low:
        return "%s | %s x%s at %s" % (label, who(A, -1), C, B)
    if "upgrade" in low:
        return "%s | %s -> %s" % (label, who(A, -1), who(B, -1))
    if "tech" in low and "modify" in low:
        return "%s | tech %s field B=%s = %s" % (label, A, B, D)
    return "%s | A=%s B=%s C=%s D=%s" % (label, A, B, C, D)


# find one good example per type: prefer an effect whose tech has a real (non-empty) name
by_type = collections.defaultdict(list)
for ei, e in enumerate(effects):
    for c in (e.get("commands") or []):
        by_type[c[0]].append((ei, c))

def effname(e):
    raw = e.get("name") or ""
    try:
        return raw.encode("latin-1").decode("gb18030")
    except Exception:
        return raw

out = []
print("\n%-28s %5s %5s  %s" % ("TYPE", "cmds", "exs", "EXAMPLE"))
print("-" * 118)
for t in sorted(by_type, key=lambda k: -len(by_type[k])):
    info = TYPES.get(str(t), {})
    label = info.get("label", "?")
    # choose the example whose effect has a named tech
    best = None
    for ei, c in by_type[t]:
        ts = eff2tech.get(ei) or []
        named = [x for x in ts if (techs[x].get("name") or "").strip()]
        if named:
            best = (ei, c, named[0]); break
    if best is None:
        ei, c = by_type[t][0]; tn = None
    else:
        ei, c, tn = best
    tname = (techs[tn].get("name") if tn is not None else None) or "(no tech name)"
    line = describe(c)
    print("%-28s %5d %5d  %s" % ("%s" % label, len(by_type[t]), 0, line))
    print("%34s example effect[%d] %r  via tech[%s] %r"
          % ("", ei, effname(effects[ei])[:34], tn, tname[:30]))
    out.append(dict(type=t, label=label, cmds=len(by_type[t]), example_cmd=list(c),
                    effect_index=ei, effect_name=effname(effects[ei]),
                    tech_index=tn, tech_name=tname, description=line))

with open(os.path.join(HERE, "template_library.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("\nwrote template_library.json with %d types" % len(out))
print("total distinct command types used in vanilla: %d ; total commands: %d"
      % (len(by_type), sum(len(v) for v in by_type.values())))
