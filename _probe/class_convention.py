"""Which convention does effect B actually use -- the label prefix, or the list position?

AGE's class_names list starts with "No Class/Invalid Class" then "0 - Archer".
Two readings are possible:

  PREFIX  stored B == the number written in the label, so B=0 is Archer and the
          first list entry is unreachable.
  INDEX   stored B == the selection index into the list, so B=0 is "No Class"
          and B=1 is Archer.

The dat settles it without any table: find techs whose own name says what class
they touch.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [ROOT, HERE, os.path.join(HERE, "datparse")]

from aoe2mod import api as A                      # noqa: E402
from aoe2mod.dat import locate as L               # noqa: E402

tk = A.open_toolkit()
tk._ensure()
effs, _ = L.locate_effects(tk._raw)
techs = L.locate_techs(tk._raw, tk._parsed[4], tk._parsed[3])

# class value -> tech names
by_class = {}
for t in techs:
    eid = t.get("effect_id")
    if eid is None or eid < 0 or eid >= len(effs):
        continue
    nm = t.get("name") or ""
    for c in effs[eid]["commands"]:
        if c["type"] not in (0, 4, 5):
            continue
        if c["c"] in (8, 9):
            b = (int(c["d"]) & 0xFFFF) >> 8          # packed: class is the high byte
        else:
            b = c["b"]
        if b is None or b == -1:
            continue
        by_class.setdefault(b, set()).add(nm)

print("=== techs whose NAME names a unit type, and the class they touch ===")
CUES = [("archer", ("archer",)), ("cavalry", ("cavalry", "knight", "scout")),
        ("infantry", ("infantry", "militia", "spearman", "champion")),
        ("monk", ("monk",)), ("building", ("building", "tower", "wall", "tc", "house")),
        ("siege", ("siege", "mangonel", "ram")), ("ship", ("ship", "boat", "galley", "dromon")),
        ("camel", ("camel",)), ("elephant", ("elephant",)),
        ("gunpowder", ("gunpowder", "hand cannon", "bombard")),
        ("villager", ("villager", "shepherd", "farmer", "lumberjack", "miner", "fisher")),
        ("trade", ("trade",)), ("skirmisher", ("skirmisher",)), ("eagle", ("eagle",)),
        ("steppe", ("steppe",)), ("armored", ("armored", "armoured")),
        ("light cav", ("light cav",)), ("battle ele", ("battle ele",)),
        ("elephant archer", ("elephant archer",)), ("mameluke", ("mameluke",)),
        ("cav archer", ("cav archer", "cavalry archer", "horse archer")),
        ("foot archer", ("foot archer",)), ("pikeman", ("pikeman",)),
        ("huskarl", ("huskarl",)), ("samurai", ("samurai",)), ("cataphract", ("cataphract",)),
        ("warship", ("warship",)), ("fishing", ("fishing",)),
        ("trade cog", ("trade cog",))]

for label, keys in CUES:
    hits = {}
    for b, names in by_class.items():
        for nm in names:
            low = nm.lower()
            if any(k in low for k in keys):
                hits.setdefault(b, []).append(nm)
    if not hits:
        continue
    top = sorted(hits.items(), key=lambda kv: -len(kv[1]))[:5]
    print("  %-16s classes: %s" % (label, "; ".join(
        "B=%d x%d (%s)" % (b, len(n), n[0][:28]) for b, n in top)))

print()
print("=== how many distinct class values are used at all ===")
print("  distinct B values:", sorted(by_class))
print()
print("=== control: does B=0 mean Archer? ===")
print("  B=0 named by:", sorted(by_class.get(0, ()))[:10])
print("  B=1 named by:", sorted(by_class.get(1, ()))[:10])
print("  B=4 named by:", sorted(by_class.get(4, ()))[:10])
