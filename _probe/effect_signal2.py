"""Corrected attribute histogram + fan-in trap + writer/mark support.

The previous probe indexed c[2] as if it were C. The tuple is
    (Type, A, B, C, D)   ->  A=c[1], B=c[2], C=c[3], D=c[4]
so it counted the CLASS (B) and reported it as the ATTRIBUTE.

This probe answers the questions that decide whether an effect-edit intent is
safe to build:
  1. the real attribute histogram (c[3]) for modifier commands
  2. what A/B mean for each command (unit target vs class target)
  3. the fan-in trap: how many techs would an edit to one effect touch
  4. does the parser mark effect/command offsets (can we write at all)?
  5. does the writer support effects, and is there a size/geometry change?

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

MODIFIERS = {0: "Set", 4: "Add", 5: "Multiply"}


def dump_effect(i):
    e = effs[i]
    print("  effect[%d] name=%r ncmd=%d" % (i, e["name"][:44], len(e["commands"])))
    print("    keys on effect: %s" % sorted(e.keys()))
    for c in e["commands"][:8]:
        print("      type=%-4d A=%-7d B=%-6d C=%-6d D=%s" % c)


print("=== does anything mark effect offsets? ===")
print("  effect dict keys : %s" % sorted(effs[1].keys()))
print("  (no '_off' key means the locator discards the offset)")

# --- 1. corrected attribute histogram, split by target kind ---------------
print("\n=== CORRECTED attribute histogram (C = c[3]) for modifier commands ===")
byattr = collections.Counter()
bytarget = collections.Counter()
for e in effs:
    for c in e["commands"]:
        if c[0] in MODIFIERS:
            byattr[c[3]] += 1
            bytarget["unit" if c[2] == -1 else "class"] += 1
print("  target kind: %s" % sorted(bytarget.items()))
for a, n in sorted(byattr.items(), key=lambda kv: -kv[1])[:22]:
    print("    attr %-5s %-44s %6d" % (a, ATTRS.get(str(a), "?"), n))

# --- 2. a real class-target command, verified against AGE's Tester --------
print("\n=== commands whose C is 8 or 9 (AGE packs class into D) ===")
n89 = 0
for e in effs:
    for c in e["commands"]:
        if c[0] in MODIFIERS and c[3] in (8, 9):
            if n89 < 6:
                D = c[4]
                print("    type=%d A=%d B=%d C=%d D=%s -> age would read "
                      "class=%d value=%d" % (c[0], c[1], c[2], c[3], D,
                                             int(D) >> 8, int(D) & 0xFF))
            n89 += 1
print("  total C in (8,9): %d" % n89)

# --- 3. fan-in trap --------------------------------------------------------
print("\n=== fan-in trap ===")
fan = collections.Counter(t["effect_id"] for t in techs
                          if t.get("effect_id", -1) >= 0)
worst = sorted(fan.items(), key=lambda kv: -kv[1])[:6]
for ei, n in worst:
    names = [t.get("name") for t in techs if t.get("effect_id") == ei][:6]
    print("  effect[%d] referenced by %d techs: %s" % (ei, n, names))
print("  effects with fan-in > 1: %d of %d referenced" % (
    sum(1 for v in fan.values() if v > 1), len(fan)))

# --- 4. are unreferenced effects editable-but-invisible? -------------------
print("\n=== unreferenced effects that still have commands ===")
unref = [i for i in range(len(effs)) if fan.get(i, 0) == 0]
nonempty = [i for i in unref if effs[i]["commands"]]
print("  unreferenced: %d | of those non-empty: %d" % (len(unref), len(nonempty)))
print("  first few non-empty unreferenced: %s" % nonempty[:10])

# --- 5. writer support -----------------------------------------------------
print("\n=== writer support for effects ===")
import inspect
sys.path.insert(0, os.path.join(HERE, "serializer"))
try:
    import write_dat as W
    src = inspect.getsource(W.write_effect)
    print("  write_effect exists:\n%s" % "\n".join("    " + l for l in src.splitlines()))
    src2 = inspect.getsource(W.write_effect_command)
    print("  write_effect_command exists:\n%s" % "\n".join("    " + l for l in src2.splitlines()))
except Exception as ex:
    print("  could not introspect writer: %r" % (ex,))
