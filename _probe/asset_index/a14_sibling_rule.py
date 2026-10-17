#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a14_sibling_rule.py -- establish the animation-set rule empirically.

Finding to explain (a13): the dat CONTAINS walka graphics (492 with a FileName) but
NO unit field ever references one.  Meanwhile attacka/deatha/decaya/idleb ARE
referenced.  So walking must be resolved some other way.

Two candidates:
  R-conv : given a referenced graphic file, the engine substitutes the animation
           token to build sibling file names and looks those up in the graphic table.
  R-adj  : the graphic table stores a stem's animations in a fixed contiguous order,
           so a sibling's slot is base + offset.

Tests:
  T1  order/contiguity of slots per stem
  T2  does a dat graphic exist for every (referenced stem, expected anim)?
  T3  for stems where walka is in the dat, is it ALWAYS immediately related by slot?
  T4  how many units gain a walk sprite under R-conv, and at what slot?
"""
import json, os, collections, re, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
G = json.load(open(os.path.join(HERE, "graphics_raw.json"), encoding="utf-8"))
C = json.load(open(os.path.join(HERE, "units_raw.json"), encoding="utf-8"))

ANIMS = set("""idlea idleb idlec walka walkb walkc attacka attackb attackc
deatha deathb decaya constr rubble destruction flag garrison""".split())


def canon(name):
    n = (name or "").strip().lower()
    if n.endswith(".sld"):
        n = n[:-4]
    if n.endswith("_x1") or n.endswith("_x2"):
        n = n[:-3]
    i = n.rfind("_")
    if i > 0 and n[i + 1:] in ANIMS:
        return n[:i], n[i + 1:]
    return n, None


slot2g = {g["slot"]: g for g in G}
GSE = [g for g in G if (g["file"] or "").strip()]
print("graphics with a FileName: %d" % len(GSE))

# ---- stem -> {anim: (slot, file)} -------------------------------------------
stem_anims = collections.defaultdict(dict)
for g in GSE:
    s, a = canon(g["file"])
    if a:
        stem_anims[s][a] = (g["slot"], g["file"])

DE = re.compile(r"^[bunaspBUNASP]_")
de_stems = [s for s in stem_anims if DE.match(s)]
print("DE-style stems with an anim-tagged graphic: %d" % len(de_stems))

# ------------------------------------------------------------------ T1 order
ORDER = ["idlea", "idleb", "idlec", "walka", "walkb", "walkc", "attacka", "attackb",
         "attackc", "deatha", "deathb", "decaya"]
print("\n--- T1: slot ordering within a stem ---")
contig = noncontig = 0
order_ok = order_bad = 0
span_gaps = []
for s in de_stems:
    d = stem_anims[s]
    if len(d) < 2:
        continue
    items = sorted(d.items(), key=lambda kv: kv[1][0])
    slots = [v[0] for _, v in items]
    if slots == list(range(slots[0], slots[0] + len(slots))):
        contig += 1
    else:
        noncontig += 1
        if len(span_gaps) < 8:
            span_gaps.append((s, [(k, v[0]) for k, v in items]))
    seq = [k for k, _ in items]
    ref = [a for a in ORDER if a in d]
    if seq == ref:
        order_ok += 1
    else:
        order_bad += 1
print("stems with >=2 anims: %d ; slots contiguous: %d ; NOT contiguous: %d"
      % (contig + noncontig, contig, noncontig))
print("order == canonical idle->walk->attack->death->decay: %d ; other: %d"
      % (order_ok, order_bad))
for s, it in span_gaps[:6]:
    print("   %-44s %s" % (s, it))

# ------------------------------------------------------- T2 expected siblings
print("\n--- T2: which anims exist per referenced stem ---")
SPRITE_ANIMS = ["idlea", "idleb", "walka", "walkb", "attacka", "attackb", "attackc",
                "deatha", "decaya"]
cnt = collections.Counter()
for s in de_stems:
    for a in SPRITE_ANIMS:
        if a in stem_anims[s]:
            cnt[a] += 1
print("of %d DE stems, how many have each anim (in the dat):" % len(de_stems))
for a in SPRITE_ANIMS:
    print("   %-8s %5d  (%.1f%%)" % (a, cnt[a], 100.0 * cnt[a] / len(de_stems)))

# ------------------------------------------------- T3 walk reachable by convention
print("\n--- T3: units whose standing_1 references an idleA graphic ---")
FIELDS = ["standing_1", "standing_2", "dying", "undead", "attack_graphic",
          "attack_graphic2", "garrison_graphic", "spawning_graphic", "upgrade_graphic",
          "hero_glow_graphic", "idle_attack_graphic", "special_graphic",
          "construction_graphic", "snow_graphic", "destruction_graphic",
          "destruction_rubble_graphic", "researching_graphic",
          "research_completed_graphic"]

# distinct unit ids and their referenced stems per civ
byid = {}
for ci, civ in enumerate(C):
    for u in civ["units"]:
        byid.setdefault(u["id"], {})[ci] = u
print("distinct unit ids: %d" % len(byid))

def refs(u):
    out = {}
    for f in FIELDS:
        v = u.get(f)
        if isinstance(v, int) and v in slot2g:
            out[f] = (slot2g[v]["file"] or "").strip().lower()
    return out

walk_via_conv = collections.Counter()
walk_stem_missing = []
unit_has_walk = 0
for uid, per in byid.items():
    u = per[sorted(per)[0]]
    r = refs(u)
    st = r.get("standing_1", "")
    s, a = canon(st)
    if a == "idlea":
        if "walka" in stem_anims.get(s, {}):
            unit_has_walk += 1
        else:
            walk_stem_missing.append((uid, u["name"], s))
print("units whose standing_1 is an idleA graphic: %d"
      % sum(1 for uid, per in byid.items()
            if canon(refs(per[sorted(per)[0]]).get("standing_1", ""))[1] == "idlea"))
print("   of those, sibling walka exists in the dat: %d" % unit_has_walk)
print("   of those, no walka sibling: %d" % len(walk_stem_missing))
print("   examples without walka: %s" % [(x[0], x[1], x[2]) for x in walk_stem_missing[:12]])

# distribution of how many anims a unit's stem provides
dist = collections.Counter()
for uid, per in byid.items():
    u = per[sorted(per)[0]]
    s, a = canon(refs(u).get("standing_1", ""))
    avail = [x for x in SPRITE_ANIMS if x in stem_anims.get(s, {})]
    dist[len(avail)] += 1
print("\nanim-count-per-unit-stem histogram: %s" % dict(sorted(dist.items())))
