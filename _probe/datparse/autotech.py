import _gamepaths as GP
"""Resolve the mod's own tech/effect wiring: which tech auto-applies the resource effects."""
import os, sys, io, contextlib, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parse_dat as P

MODS = GP.SUBSCRIBED
D10 = [os.path.join(MODS, n) for n in os.listdir(MODS) if n.startswith("550749")][0]
M10 = os.path.join(D10, "resources", "_common", "dat", "empires2_x2_p1.dat")

data, _ = P.load_dat(M10)
p = P.Parser(data)
with contextlib.redirect_stdout(io.StringIO()):
    p.parse()
em, mt = p.stats["effects"], p.stats["techs"]

# Who references effect 4987 (opening resources) and 5535 (+2000 each)?
targets = {4987: "kāijú zīyuán shèzhì (opening resource setup)", 5535: "gè xiàng zīyuán +2000",
           4993: "unlock tech pt dark", 5000: "Aztecs"}
print("=== techs referencing key effects ===")
for ei, label in targets.items():
    refs = [(i, t) for i, t in enumerate(mt) if t.get("effect_id") == ei]
    print("  effect[%d] %-46s referenced by %d techs" % (ei, label, len(refs)))
    for i, t in refs[:6]:
        print("      tech[%d] civ=%-4s type=%-3s icon=%-6s name=%-24s loc=%s"
              % (i, t["civ"], t["type"], t["icon_id"], repr(t["name"])[:24], t["research_locations"][:2]))

# A tech with no research locations + civ -1 + type 0 = auto-applied
print("\n=== candidate AUTO-APPLY techs (civ=-1, no research locations, effect>=0) ===")
auto = [(i, t) for i, t in enumerate(mt)
        if t["civ"] == -1 and not t["research_locations"] and t["effect_id"] is not None and t["effect_id"] >= 0]
print("  count: %d" % len(auto))
for i, t in auto[:15]:
    print("      tech[%d] eff=%-6s type=%-3s name=%r" % (i, t["effect_id"], t["type"], t["name"][:30]))

# Full dump of the opening-resource effect
print("\n=== effect[4987] full command list (AGGREGATED BY TYPE) ===")
e = em[4987]
cnt = collections.Counter(c[0] for c in e["commands"])
print("  name=%r  commands=%d  types=%s" % (e["name"], len(e["commands"]), dict(cnt)))
print("  first 12 commands:", e["commands"][:12])

# Types used across the whole mod, with AGE-derived labels
LABEL = {0:"Attribute Modifier (Set)",1:"Resource Modifier (Set/+/-)",2:"Enable/Disable Unit",
         3:"Upgrade Unit",4:"Attribute Modifier (+/-)",5:"Attribute Modifier (Multiply)",
         6:"Resource Modifier (Multiply)",7:"Spawn Unit",8:"Modify Tech",10:"Team Attr (Set)",
         101:"Tech Cost Modifier",102:"Disable Tech",103:"Tech Time Modifier",
         200:"Own Master Attr (Set)",201:"Own Master Attr (+/-)",202:"Own Master Attr (Multiply)",
         203:"Selected Unit Attr (Set)",204:"Selected Unit Attr (+/-)",205:"Selected Unit Attr (Multiply)",
         255:"UNNAMED / sentinel"}
print("\n=== all effect-command types used in the mod (%d distinct) ===" % len(cnt))
for t, n in sorted(cnt.items()):
    print("   %-4s %-36s x%d" % (t, LABEL.get(t, "?"), n))

# What does 255 look like exactly
print("\n=== every distinct type-255 command payload in the mod ===")
c = collections.Counter()
for i in range(len(em)):
    for cmd in em[i]["commands"]:
        if cmd[0] == 255:
            c[cmd[1:]] += 1
for k, v in c.most_common():
    print("   A=%-6s B=%-6s C=%-6s D=%-8s x%d" % (k[0], k[1], k[2], k[3], v))
