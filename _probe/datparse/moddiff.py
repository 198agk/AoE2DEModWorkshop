import _gamepaths as GP
# -*- coding: utf-8 -*-
"""
What do REAL data mods actually change?

Parses the base dat plus the two installed data mods and compares them at the
level a modder thinks in: civs, unit counts, stats, techs, effects, graphics.
Prints only compact aggregates so the output stays readable.
"""
import os, sys, zlib, hashlib, collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import parse_dat as P

GAME = GP.DAT
MODS = {
    "BASE": GAME,
    "MOD_423821_juntuan": os.path.join(GP.SUBSCRIBED, "423821_四月-juntuanzhangtianfumozu军团长天赋模组", "resources", "_common", "dat", "empires2_x2_p1.dat"),
    "MOD_550749_10x": os.path.join(GP.SUBSCRIBED, "550749_{2026}10倍资源文明联盟2倍科技 北欧dlc可用 v34test", "resources", "_common", "dat", "empires2_x2_p1.dat"),
}


def parse(path):
    data, how = P.load_dat(path)
    p = P.Parser(data)
    s = p.parse()
    return s, p, data


results = {}
for label, path in MODS.items():
    s, p, data = parse(path)
    results[label] = (s, p, data)
    print("=" * 72)
    print("%s  (%d bytes compressed -> %d decompressed)"
          % (label, os.path.getsize(path), len(data)))
    print("  civs=%s graphics=%s(nz %s) sounds=%s effects=%s unitheaders=%s techs=%s terrains=%s"
          % (s["civ_count"], s["graphic_count"], s["graphic_pointers_nonzero"],
             s["sound_count"], s["effect_count"], s["unit_header_count"],
             s["tech_count"], len(s["terrain_block"]["terrains"])))
    print("  techtree ages/bld/unit/res = %s/%s/%s/%s"
          % (s["tech_tree"]["ages"], s["tech_tree"]["buildings"],
             s["tech_tree"]["units"], s["tech_tree"]["research"]))
    tt = s["terrain_block"]
    print("  terrain block: TerrainsUsed2=%s BordersUsed=%s MaxTerrain=%s"
          % (tt.get("terrains_used2"), tt.get("borders_used"), tt.get("max_terrain")))

base_s = results["BASE"][0]
base_civ_names = [c["name"] for c in base_s["civs"]]
print()
print("=" * 72)
print("BASE civ names (%d):" % len(base_civ_names))
for i, n in enumerate(base_civ_names):
    print("   [%2d] %s" % (i, n), end="\n" if (i % 3 == 2) else "")
print()

# ---- per-civ unit stat fingerprint: are civ stat blocks independent? ----
def unit_fp(civ):
    h = hashlib.sha256()
    for u in civ["units"]:
        h.update(b"%d|%d|%d|%d;" % (u["id"], u["type"], u["hit_points"], u["class"]))
    return h.hexdigest()[:16]


for label in MODS:
    s = results[label][0]
    fps = collections.Counter(unit_fp(c) for c in s["civs"])
    print("%-20s distinct per-civ unit-stat fingerprints: %d  (most common covers %d civs)"
          % (label, len(fps), fps.most_common(1)[0][1]))

# ---- where do the mods differ? ----
print()
print("=" * 72)
print("Villager (id 83) hit points per civ -- first 12 civs")
for label in MODS:
    s = results[label][0]
    vals = []
    for c in s["civs"][:12]:
        hp = None
        for u in c["units"]:
            if u["id"] == 83:
                hp = u["hit_points"]
                break
        vals.append(hp)
    print("   %-20s %s" % (label, vals))

print()
print("Archer (id 4) hit points per civ -- first 12 civs")
for label in MODS:
    s = results[label][0]
    vals = []
    for c in s["civs"][:12]:
        hp = None
        for u in c["units"]:
            if u["id"] == 4:
                hp = u["hit_points"]
                break
        vals.append(hp)
    print("   %-20s %s" % (label, vals))

# ---- civ resource blocks (starting resources etc.) ----
print()
print("=" * 72)
print("civ Resources array (starting food/wood/stone/gold are indexes 91-94):")
for label in MODS:
    s = results[label][0]
    for want in ("Gaia", "Aztecs"):
        for c in s["civs"]:
            if c["name"].upper() == want.upper():
                r = c["resources"]
                print("   %-20s %-8s len=%d  91..94=%s"
                      % (label, c["name"], len(r), r[91:95] if len(r) > 94 else "n/a"))
                break

# ---- tech / effect counts and name samples ----
print()
print("=" * 72)
print("Tech count and effect usage")
for label in MODS:
    s = results[label][0]
    eff = collections.Counter(t["effect_id"] for t in s["techs"])
    used = sum(1 for k in eff if k >= 0)
    print("   %-20s techs=%d distinct effect_ids=%d (>=0: %d) max_effect_id=%d"
          % (label, len(s["techs"]), len(eff), used, max(eff)))

# how many units exist in total and how many distinct ids
print()
print("=" * 72)
for label in MODS:
    s = results[label][0]
    ids = set()
    total = 0
    for c in s["civs"]:
        for u in c["units"]:
            ids.add(u["id"])
            total += 1
    print("   %-20s unit objects=%d distinct ids=%d" % (label, total, len(ids)))

# ---- graphics: what changed? ----
print()
print("=" * 72)
print("Graphics fingerprint per file (name|filename|slp|framecount hashed)")
for label in MODS:
    s = results[label][0]
    h = hashlib.sha256()
    for g in s["graphics"]:
        h.update(("%s|%s|%s|%s;" % (g.get("name"), g.get("file"),
                                    g.get("slp"), g.get("frame_count"))).encode())
    print("   %-20s graphics=%d fp=%s" % (label, len(s["graphics"]), h.hexdigest()[:24]))
