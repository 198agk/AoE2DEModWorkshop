"""Design data for a `tech.effect` intent.

Three questions decide whether editing "what a tech does" can be safe:
  1. does the vendored locator expose the effect walker?
  2. how shared is an effect really?  (effect[0] had fan-in 88, but all those
     techs were named 'New Research' -- if it is an empty placeholder, sharing
     it is harmless; if it has commands, an edit silently hits 88 techs)
  3. can a tech be addressed unambiguously by id, and what does its effect look
     like?

Read-only. BASE only.
"""
import os, sys, io, json, contextlib, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from aoe2mod.dat import locate as L
from aoe2mod.dat import parser as P
from aoe2mod.dat import families as F

BASE = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat"


def load(path):
    data, _ = P.load_dat(path)
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    return data, p


data, p = load(BASE)
civs, civs_start, gv, tail = L.locate(data, parser=p)
techs = L.locate_techs(data, tail, gv)
effs, eff_start = L.locate_effects(data, parser=p)

print("=== 1. vendored locator exposes the walker ===")
print("  techs: %d | effects: %d | section start: %d" % (len(techs), len(effs), eff_start))
print("  first effect has marks: %s"
      % sorted(k for k in effs[1]["commands"][0].keys() if k.startswith("_off")))

print("\n=== 2. what is effect[0], the fan-in 88 one? ===")
e0 = effs[0]
print("  effect[0] name=%r ncmd=%d" % (e0["name"], len(e0["commands"])))
ref0 = [t for t in techs if t.get("effect_id") == 0]
print("  referenced by %d techs; distinct names: %s"
      % (len(ref0), sorted({t["name"] for t in ref0})[:6]))
print("  civs referencing it: %s" % sorted({t["civ"] for t in ref0})[:12])

print("\n=== 3. fan-in restricted to effects that actually have commands ===")
fan = collections.defaultdict(list)
for i, t in enumerate(techs):
    if t.get("effect_id", -1) >= 0:
        fan[t["effect_id"]].append((i, t))
shared = {k: v for k, v in fan.items() if len(v) > 1}
print("  distinct effects referenced: %d" % len(fan))
print("  effects referenced by >1 tech: %d" % len(shared))

# The trap only bites when the effect is NOT an empty placeholder.
dangerous = {}
for k, v in shared.items():
    if effs[k]["commands"]:
        dangerous[k] = v
print("  of those, effects that HAVE commands: %d" % len(dangerous))
for k, v in sorted(dangerous.items(), key=lambda kv: -len(kv[1]))[:8]:
    names = [t["name"] for _, t in v][:4]
    print("    effect[%d] ncmd=%d shared by %d techs: %s"
          % (k, len(effs[k]["commands"]), len(v), names))

print("\n=== 4. the top offenders: same effect, DIFFERENT tech names, same civ ===")
for k, v in sorted(dangerous.items(), key=lambda kv: -len(kv[1]))[:4]:
    groups = collections.defaultdict(set)
    for _, t in v:
        groups[t["civ"]].add(t["name"])
    multi = {c: n for c, n in groups.items() if len(n) > 1}
    print("  effect[%d]: %d techs, %d civs, %d civs with >1 distinct name"
          % (k, len(v), len(groups), len(multi)))
    for c, n in list(multi.items())[:2]:
        print("      civ %s -> %s" % (c, sorted(n)[:4]))

print("\n=== 5. addressing a tech by id ===")
for tid in (22, 103, 102, 200):
    t = techs[tid]
    ei = t.get("effect_id", -1)
    print("  tech[%d] civ=%s name=%r effect_id=%s ncmd=%s"
          % (tid, t["civ"], t["name"], ei,
             len(effs[ei]["commands"]) if ei >= 0 else "-"))
    if ei >= 0:
        for ci, c in enumerate(effs[ei]["commands"][:4]):
            print("        cmd%d type=%d a=%d b=%d c=%d d=%s"
                  % (ci, c["type"], c["a"], c["b"], c["c"], c["d"]))

print("\n=== 6. techs with NO effect ===")
none = [i for i, t in enumerate(techs) if t.get("effect_id", -1) < 0]
print("  %d of %d techs have effect_id < 0 (nothing to edit)" % (len(none), len(techs)))
print("  out-of-range effect_id: %s"
      % [i for i, t in enumerate(techs)
         if t.get("effect_id", -1) >= len(effs)][:5])
