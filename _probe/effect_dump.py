"""Dump raw EffectCommands for named techs and check the C == -1 question.

Two things this resolves:
  1. The earlier histogram showed attr -1 as 5,075 of ~6,400 modifier commands.
     Is C genuinely -1 in the data, or is the tuple order wrong?
  2. The sample decode matched no tech name -- so what IS tech["name"]?

Read-only. BASE only.
"""
import os, sys, io, json, contextlib, collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "datparse"))
import parse_dat as P

SCHEMA = os.path.join(HERE, "schema")
TYPES = json.load(open(os.path.join(SCHEMA, "effect_command_types.json"), encoding="utf-8"))["types"]
ATTRS = json.load(open(os.path.join(SCHEMA, "effect_attributes.json"), encoding="utf-8"))["attributes"]

BASE = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat"


def load(path):
    data, _ = P.load_dat(path)
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    return p.stats


s = load(BASE)
effs = s["effects"]
techs = s["techs"]

# --- what does tech["name"] actually look like? ---------------------------
print("=== tech['name'] samples (civ, name, effect_id) ===")
seen = set()
for t in techs:
    if t["civ"] == 1 and t.get("name") not in seen:
        seen.add(t.get("name"))
    if len(seen) > 14:
        break
for nm in list(seen)[:14]:
    print("   %r" % nm)

print("\n=== techs whose name contains Loom/Feudal/Imperial ===")
for t in techs:
    nm = t.get("name") or ""
    if any(k in nm for k in ("Loom", "Feudal", "Imperial", "Wheel")):
        print("   civ=%-3s name=%-28r effect_id=%-5s type=%-3s icon=%s"
              % (t["civ"], nm, t.get("effect_id"), t.get("type"), t.get("icon_id")))

# --- the C == -1 question --------------------------------------------------
print("\n=== C value histogram for the three modifier types ===")
for tt in (0, 4, 5):
    cs = collections.Counter()
    for e in effs:
        for c in e["commands"]:
            if c[0] == tt:
                cs[c[2]] += 1
    print("  type %d: distinct C=%d  top: %s" % (tt, len(cs), sorted(cs.items(), key=lambda kv: -kv[1])[:10]))

# --- raw bytes for a concrete effect --------------------------------------
print("\n=== raw tuples for the first effect that has commands ===")
for i, e in enumerate(effs):
    if e["commands"]:
        print("  effect[%d] name=%r ncmd=%d" % (i, e["name"][:40], len(e["commands"])))
        for c in e["commands"][:10]:
            print("     type=%-4d A=%-7d B=%-6d C=%-6d D=%s" % c)
        break

# --- a known vanilla tech with an attribute effect ------------------------
print("\n=== resolve one civ-1 tech to its effect, dump every command ===")
cands = [t for t in techs if t["civ"] == 1 and t.get("effect_id", -1) >= 0]
print("  civ-1 techs with an effect: %d" % len(cands))
for t in cands[:3]:
    ei = t["effect_id"]
    print("\n  tech name=%r civ=%s effect_id=%s" % (t.get("name"), t["civ"], ei))
    e = effs[ei]
    print("    effect[%d] raw name=%r ncmd=%d" % (ei, e["name"][:40], len(e["commands"])))
    for c in e["commands"][:12]:
        info = TYPES.get(str(c[0]), {})
        print("      %-38s type=%-4d A=%-7d B=%-6d C=%-6d D=%s"
              % (info.get("label", "Type %d" % c[0])[:38], c[0], c[1], c[2], c[3], c[4]))

# --- how many commands have a type NOT in the schema table? ---------------
schema_types = set(int(k) for k in TYPES)
unknown = collections.Counter()
for e in effs:
    for c in e["commands"]:
        if c[0] not in schema_types:
            unknown[c[0]] += 1
print("\n=== command types absent from effect_command_types.json ===")
print("  distinct unknown types: %d | total commands: %d" % (len(unknown), sum(unknown.values())))
print("  %s" % sorted(unknown.items(), key=lambda kv: -kv[1])[:10])
