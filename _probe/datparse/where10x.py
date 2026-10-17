"""Find where the 10x actually lives: resource commands on food/wood/gold/stone."""
import os, sys, collections, io, contextlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parse_dat as P

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat"
MODS = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\subscribed"
D10 = [os.path.join(MODS, n) for n in os.listdir(MODS) if n.startswith("550749")][0]
M10 = os.path.join(D10, "resources", "_common", "dat", "empires2_x2_p1.dat")

def load(path):
    data, _ = P.load_dat(path)
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    return p

b = load(GAME); m = load(M10)
eb, em = b.stats["effects"], m.stats["effects"]
bt, mt = b.stats["techs"], m.stats["techs"]

print("base effects=%d techs=%d | mod effects=%d techs=%d"
      % (len(eb), len(bt), len(em), len(mt)))

CORE = {0: "Food", 1: "Wood", 2: "Stone", 3: "Gold", 4: "Pop"}
print("\n=== type 1 (Resource Set/Change) touching CORE resources (0-4) ===")
for label, e in (("BASE", eb), ("MOD", em)):
    rows = []
    for i in range(len(e)):
        for c in e[i]["commands"]:
            if c[0] == 1 and c[1] in CORE:
                rows.append((c[1], c[2], c[4], i, e[i]["name"][:34]))
    print("  %s: %d commands" % (label, len(rows)))
    for r in sorted(set(rows))[:25]:
        print("     %-8s B=%-4s D=%-12s eff[%d] %s" % (CORE[r[0]], r[1], r[2], r[3], r[4]))

# ---- Which effects do the mod's NEW techs point at, and do any auto-apply? ----
new_techs = mt[len(bt):]
print("\n=== mod new techs that are NOT empty placeholders (effect_id>=0): %d ===" %
      sum(1 for t in new_techs if t["effect_id"] is not None and t["effect_id"] >= 0))
real = [t for t in new_techs if t["effect_id"] is not None and t["effect_id"] >= 0]
civs = collections.Counter(t["civ"] for t in real)
print("  by civ field:", civs.most_common(12))
types = collections.Counter(t["type"] for t in real)
print("  by type field:", types.most_common(12))

# effects that produce crazy core resources
print("\n=== any effect with D >= 1000 on a core resource (potential '10x') ===")
for label, e in (("BASE", eb), ("MOD", em)):
    hits = []
    for i in range(len(e)):
        for c in e[i]["commands"]:
            if c[0] in (1, 6) and c[1] in CORE and abs(c[4]) >= 1000:
                hits.append((i, e[i]["name"][:30], c))
    print("  %s: %d" % (label, len(hits)))
    for h in hits[:15]:
        print("      eff[%d] %-32s cmd=%s" % (h[0], h[1], h[2]))

# ---- The 'New Tech' techs: what are their ResearchLocations? ----
print("\n=== sample of real new mod techs ===")
for t in real[:20]:
    print("  civ=%-4s eff=%-6s type=%-3s icon=%-6s name=%-24s loc=%s"
          % (t["civ"], t["effect_id"], t["type"], t["icon_id"], repr(t["name"])[:24],
             t["research_locations"][:3]))
