"""How much signal is there in the tech -> effect -> command chain?

Before proposing any intent that edits an effect, measure:
  1. how many techs actually reference an effect
  2. how many effects are referenced by more than one tech (the fan-in trap:
     editing a shared effect changes every tech that points at it)
  3. which command types / attributes are actually used, and with what values
  4. whether effects are per-civ or global

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
print("effects: %d | techs: %d" % (len(effs), len(techs)))

# --- 1. techs that reference an effect -------------------------------------
ref = [t for t in techs if t.get("effect_id") is not None and t["effect_id"] >= 0]
print("\n=== techs referencing an effect ===")
print("  with effect_id >= 0 : %d / %d (%.1f%%)" % (len(ref), len(techs), 100.0 * len(ref) / len(techs)))
ids = [t["effect_id"] for t in ref]
print("  distinct effect ids : %d" % len(set(ids)))
print("  max effect id       : %d" % max(ids))
print("  effects never referenced: %d" % (len(effs) - len(set(ids))))

# --- 2. fan-in -------------------------------------------------------------
fan = collections.Counter(ids)
multi = {k: v for k, v in fan.items() if v > 1}
print("\n=== fan-in: effects referenced by more than one tech ===")
print("  effects with fan-in > 1 : %d" % len(multi))
print("  top fan-in              : %s" % sorted(fan.items(), key=lambda kv: -kv[1])[:8])
print("  fan-in histogram        : %s" % sorted(collections.Counter(fan.values()).items()))

# a tech record is per-civ; count DISTINCT (civ, effect) to see sharing across civs
civ_eff = collections.Counter((t["civ"], t["effect_id"]) for t in ref)
print("  distinct (civ, effect) pairs: %d" % len(civ_eff))

# --- 3. command types and attributes --------------------------------------
print("\n=== command type histogram (all effects) ===")
tcount = collections.Counter()
for e in effs:
    for c in e["commands"]:
        tcount[c[0]] += 1
for t, n in sorted(tcount.items(), key=lambda kv: -kv[1]):
    lbl = TYPES.get(str(t), {}).get("label", "Type %d" % t)
    print("  type %-4d %-42s %6d" % (t, lbl, n))

print("\n=== only the commands reachable from a referenced effect ===")
reach = collections.Counter()
attr_of = collections.Counter()
for t in ref:
    e = effs[t["effect_id"]] if t["effect_id"] < len(effs) else None
    if not e:
        continue
    for c in e["commands"]:
        reach[c[0]] += 1
        if tcount and c[0] in (0, 4, 5, 10, 14, 15):
            attr_of[c[2]] += 1
print("  %s" % sorted(reach.items(), key=lambda kv: -kv[1])[:14])
print("\n  attribute histogram for set/plus/minus modifiers:")
for a, n in sorted(attr_of.items(), key=lambda kv: -kv[1])[:18]:
    print("    attr %-5s %-38s %6d" % (a, ATTRS.get(str(a), "?"), n))

# --- 4. are effects global or per-civ? ------------------------------------
print("\n=== are effects global or per civ? ===")
print("  effects count: %d | civs: %d" % (len(effs), s["civ_count"]))
print("  command totals per effect: min %d max %d" % (
    min(len(e["commands"]) for e in effs), max(len(e["commands"]) for e in effs)))
empt = sum(1 for e in effs if not e["commands"])
print("  effects with ZERO commands: %d" % empt)

# --- 5. sample: what does a well-known tech actually do? ------------------
print("\n=== sample decode: Loom(22), Feudal Age(102), Imperial Age(103) ===")


def describe(c):
    t, A, B, C, D = c
    info = TYPES.get(str(t))
    label = info["label"] if info else "Type %d" % t
    if "Attribute" in label or "attribute" in label:
        return "%-40s unit=%-6s class=%-5s attr=%-28s D=%s" % (
            label, A, B, ATTRS.get(str(C), "Attr %s" % C), D)
    return "%-40s A=%-7s B=%-6s C=%-6s D=%s" % (label, A, B, C, D)


for t in techs:
    if t.get("name") in ("Loom", "Feudal Age", "Imperial Age") and t["civ"] == 1:
        ei = t.get("effect_id", -1)
        print("\n  tech %r civ=%s effect_id=%s (offset start %s)" % (t["name"], t["civ"], ei, t.get("_eff_off")))
        if 0 <= ei < len(effs):
            print("    effect[%d] name=%r ncmd=%d" % (ei, effs[ei]["name"][:30], len(effs[ei]["commands"])))
            for c in effs[ei]["commands"][:8]:
                print("      ", describe(c))
