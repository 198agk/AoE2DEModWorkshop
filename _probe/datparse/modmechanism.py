import _gamepaths as GP
# -*- coding: utf-8 -*-
"""How do real data mods implement their headline feature?

Specifically: MOD_550749 claims "10x resources, 2x tech". Find the mechanism.
Also: what exactly differs inside Civs (the biggest diff area)?
"""
import os, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import parse_dat as P

GAME = GP.DAT
MOD10 = os.path.join(GP.SUBSCRIBED, "550749_{2026}10倍资源文明联盟2倍科技 北欧dlc可用 v34test", "resources", "_common", "dat", "empires2_x2_p1.dat")
MODJT = os.path.join(GP.SUBSCRIBED, "423821_四月-juntuanzhangtianfumozu军团长天赋模组", "resources", "_common", "dat", "empires2_x2_p1.dat")


def parse(path):
    data, _ = P.load_dat(path)
    p = P.Parser(data)
    return p.parse()


base = parse(GAME)
m10 = parse(MOD10)
mjt = parse(MODJT)

# ---- 1. Effects: what commands do mods add? ----
def effect_cmd_histo(s):
    h = collections.Counter()
    for e in s["effects"]:
        for c in e.get("commands", []):
            h[c[0]] += 1          # tuple (type, A, B, C, D)
    return h

print("=" * 74)
print("EFFECT COMMAND TYPE HISTOGRAM")
for label, s in (("BASE", base), ("juntuan", mjt), ("10x", m10)):
    h = effect_cmd_histo(s)
    print("  %-10s effects=%d  commands=%d" % (label, s["effect_count"], sum(h.values())))

# ---- 2. Civ resources: which indexes changed between base and 10x ----
print()
print("=" * 74)
print("CIV RESOURCES: indexes differing between BASE and MOD_10x")
for ci, (cb, cm) in enumerate(zip(base["civs"], m10["civs"])):
    if cb["name"] != cm["name"]:
        print("  civ %d NAME differs: %r vs %r" % (ci, cb["name"], cm["name"]))
    rb, rm = cb["resources"], cm["resources"]
    if len(rb) != len(rm):
        print("  civ %d (%s) resource length %d -> %d" % (ci, cb["name"], len(rb), len(rm)))
        continue
    diffs = [(i, rb[i], rm[i]) for i in range(len(rb)) if rb[i] != rm[i]]
    if diffs:
        print("  civ %d (%s): %d differing resource indexes" % (ci, cb["name"], len(diffs)))
        for i, a, b in diffs[:20]:
            print("      [%3d] %s -> %s" % (i, a, b))
        if len(diffs) > 20:
            print("      ... and %d more" % (len(diffs) - 20))

# ---- 3. What differs inside Civs, categorised ----
print()
print("=" * 74)
print("CIVS DIFF BREAKDOWN (BASE vs MOD_10x, civ by civ)")
tot_units_added = tot_units_changed = 0
for ci, (cb, cm) in enumerate(zip(base["civs"], m10["civs"])):
    ub = {u["id"]: u for u in cb["units"]}
    um = {u["id"]: u for u in cm["units"]}
    added = sorted(set(um) - set(ub))
    removed = sorted(set(ub) - set(um))
    changed = []
    for k in sorted(set(ub) & set(um)):
        a, b = ub[k], um[k]
        if (a["hit_points"], a["type"], a["class"]) != (b["hit_points"], b["type"], b["class"]):
            changed.append((k, a["hit_points"], b["hit_points"], a["type"], b["type"]))
    tot_units_added += len(added)
    tot_units_changed += len(changed)
    if ci < 8 or added or removed or changed:
        print("  [%2d] %-12s base=%d mod=%d  added=%d removed=%d stat-changed=%d"
              % (ci, cb["name"], len(ub), len(um), len(added), len(removed), len(changed)))
        if added:
            print("        added ids: %s" % added[:12])
        if changed:
            print("        changed (id, hp_base->hp_mod, type_base->type_mod): %s" % changed[:8])
print()
print("  TOTALS across civs: units added=%d, stat-changed=%d" % (tot_units_added, tot_units_changed))

# ---- 4. do added units have names? ----
print()
print("=" * 74)
print("SAMPLE OF UNITS THAT EXIST ONLY IN THE MOD (civ 1)")
cb, cm = base["civs"][1], m10["civs"][1]
ub = {u["id"]: u for u in cb["units"]}
um = {u["id"]: u for u in cm["units"]}
added = sorted(set(um) - set(ub))
print("  civ %s added %d units" % (cb["name"], len(added)))
for k in added[:15]:
    u = um[k]
    print("      id=%-6d name=%-24s type=%-3d hp=%-4d class=%s"
          % (k, u["name"], u["type"], u["hit_points"], u["class"]))

# ---- 5. Techs added ----
print()
print("=" * 74)
print("TECHS ADDED BY MOD (last 15 by index)")
nb, nm = len(base["techs"]), len(m10["techs"])
print("  base techs=%d mod techs=%d (+%d)" % (nb, nm, nm - nb))
for t in m10["techs"][nb:nb + 15]:
    print("      civ=%-3d effect_id=%-5d type=%-3d icon=%-5d name=%r"
          % (t["civ"], t["effect_id"], t["type"], t["icon_id"], t["name"]))
