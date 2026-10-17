#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a13_anim_probe.py -- how are walkA/attackA/deathA graphics reached?

Hypothesis W: the dat references only SOME animations per unit; the game's full
animation set is discovered by NAME CONVENTION over the *.sld files sharing a stem.
Hypothesis R: every animation the game plays is an explicit dat graphic reference.

Canonical form used everywhere: lowercase, drop '.sld', drop trailing '_x1'/'_x2'.
`canon(name) -> (stem, anim_token_or_None)`.
"""
import json, os, collections, re

HERE = os.path.dirname(os.path.abspath(__file__))
GFXDIR = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs\graphics"
G = json.load(open(os.path.join(HERE, "graphics_raw.json"), encoding="utf-8"))
C = json.load(open(os.path.join(HERE, "units_raw.json"), encoding="utf-8"))

ANIMS = set("""idlea idleb idlec walka walkb walkc attacka attackb attackc
deatha deathb decaya constr rubble destruction flag garrison researching
researchingglow researchcompleteglow damage upgrade spawning heroglow levelup
unitspawn buildingupgrade""".split())


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


disk_stem = set()          # stems only
disk_canon = set()         # canonical strings, e.g. 'u_all_archer_walka'
for f in os.listdir(GFXDIR):
    if not f.lower().endswith(".sld"):
        continue
    n = f.lower()[:-4]
    if n.endswith("_x1"):
        n = n[:-3]
    disk_canon.add(n)
    s, a = canon(f)
    disk_stem.add(s)
print("drs\\graphics .sld files: %d   distinct canonical names: %d"
      % (len(os.listdir(GFXDIR)), len(disk_canon)))

slot2g = {g["slot"]: g for g in G}

samples = [g["file"] for g in G if g["file"] and len(g["file"]) > 12][:10]
print("\nsample dat graphic FileName -> canon:")
for s in samples:
    st, an = canon(s)
    print("   %-46s -> stem=%-44s anim=%s" % (s, st, an))

grafx_anims = collections.Counter()
datanim_by_file = {}
dat_canon = set()
for g in G:
    f = (g["file"] or "").strip()
    if not f:
        continue
    s, a = canon(f)
    datanim_by_file[f.lower()] = a or "<other>"
    grafx_anims[a or "<other>"] += 1
    dat_canon.add("%s_%s" % (s, a) if a else s)
print("\n--- dat graphics by animation token in FileName (17359 with a file) ---")
for a, n in grafx_anims.most_common(40):
    print("   %-20s %d" % (a, n))

# ---------------------------------------- what unit FIELDS reference which anim
FIELDS = ["standing_1", "standing_2", "dying", "undead", "attack_graphic",
          "attack_graphic2", "garrison_graphic", "spawning_graphic", "upgrade_graphic",
          "hero_glow_graphic", "idle_attack_graphic", "special_graphic",
          "construction_graphic", "snow_graphic", "destruction_graphic",
          "destruction_rubble_graphic", "researching_graphic",
          "research_completed_graphic"]
field_anim = collections.defaultdict(collections.Counter)
refset = collections.defaultdict(set)
for c in C:
    for u in c["units"]:
        for f in FIELDS:
            v = u.get(f)
            if isinstance(v, int) and v in slot2g:
                nm = (slot2g[v]["file"] or "").strip().lower()
                if nm:
                    field_anim[f][datanim_by_file.get(nm, "<other>")] += 1
                    refset[f].add(nm)
        for dg in u.get("damage_graphics") or []:
            v = dg[0]
            if isinstance(v, int) and v in slot2g:
                nm = (slot2g[v]["file"] or "").strip().lower()
                if nm:
                    field_anim["damage_graphics"][datanim_by_file.get(nm, "<other>")] += 1
                    refset["damage_graphics"].add(nm)

print("\n--- unit FIELD -> animation token of the graphic it points at ---")
for f in FIELDS + ["damage_graphics"]:
    if f in field_anim:
        tot = sum(field_anim[f].values())
        top = ", ".join("%s=%d" % (a, n) for a, n in field_anim[f].most_common(6))
        print("   %-28s n=%-7d %s" % (f, tot, top))

everything = set()
for s in refset.values():
    everything |= s
everything_canon = set()
for nm in everything:
    s, a = canon(nm)
    everything_canon.add("%s_%s" % (s, a) if a else s)
print("\ndistinct .sld stems referenced by any unit field: %d" % len(everything))

# ------------------------------------------------------- the critical question
print("\n--- are walk/attack/death/decay anims referenced by ANY unit field? ---")
for kind in ["walk", "attack", "death", "decay", "idle"]:
    d = set(x for x in disk_canon if re.search(r"_%s[abc]$" % kind, x))
    r = d & everything_canon
    print("   _%-8s on disk: %-6d referenced: %-6d (%.1f%%)"
          % (kind, len(d), len(r), 100.0 * len(r) / max(1, len(d))))
    ex = sorted(d - r)[:4]
    if ex:
        print("        unreferenced examples: %s" % ex)

# for idleA-referenced stems, does sibling walkA exist on disk / in the dat?
idle_stems = set()
for nm in everything:
    s, a = canon(nm)
    if a == "idlea":
        idle_stems.add(s)
print("\nidleA-stem population referenced by units: %d" % len(idle_stems))
sib = collections.Counter()
sib_ex = []
for s in sorted(idle_stems):
    row = {}
    for a in ["walka", "attacka", "deatha", "decaya", "walkb", "idleb"]:
        nm = "%s_%s" % (s, a)
        row[a] = ((nm in disk_canon), (nm in dat_canon), (nm in everything_canon))
    for k in row:
        sib["%s on disk" % k] += row[k][0]
        sib["%s in dat" % k] += row[k][1]
        sib["%s referenced" % k] += row[k][2]
    if len(sib_ex) < 6 and row["walka"][0]:
        sib_ex.append((s, row))
for a in ["walka", "attacka", "deatha", "decaya", "walkb", "idleb"]:
    print("   %-8s on_disk=%-5d in_dat=%-5d referenced_by_unit=%-5d"
          % (a, sib["%s on disk" % a], sib["%s in dat" % a], sib["%s referenced" % a]))
print("\nexamples (idleA stem -> sibling d/i/r = on_disk/in_dat/referenced):")
for s, row in sib_ex:
    print("   %-44s walkA=%s/%s/%s attackA=%s/%s/%s deathA=%s/%s/%s"
          % (s, row["walka"][0], row["walka"][1], row["walka"][2],
             row["attacka"][0], row["attacka"][1], row["attacka"][2],
             row["deatha"][0], row["deatha"][1], row["deatha"][2]))
