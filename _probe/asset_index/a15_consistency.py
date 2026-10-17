#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a15_consistency.py -- prove the stem-substitution rule from the EXPLICIT fields.

If the engine resolves animations by substituting the animation token in the
standing graphic's stem, then wherever the dat DOES reference a non-idle animation
explicitly, its stem must equal the standing graphic's stem.  That is a
self-consistency test that needs no assumptions.

Output: stem_consistency.json, unit_sprite_sets.json
"""
import json, os, collections

HERE = os.path.dirname(os.path.abspath(__file__))
GFXDIR = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs\graphics"
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


disk_canon = set()
for f in os.listdir(GFXDIR):
    if f.lower().endswith(".sld"):
        n = f.lower()[:-4]
        if n.endswith("_x1"):
            n = n[:-3]
        disk_canon.add(n)

slot2g = {g["slot"]: g for g in G}
dat_by_canon = {}
for g in G:
    f = (g["file"] or "").strip().lower()
    if f:
        s, a = canon(f)
        dat_by_canon["%s_%s" % (s, a) if a else s] = g

# ---------------------------------------------------------------- field -> anim
FIELD_ANIM = {
    "standing_1": "idlea", "standing_2": "idleb", "dying": "deatha",
    "undead": "decaya", "attack_graphic": "attacka", "attack_graphic2": "attackb",
    "idle_attack_graphic": "idlec",
}
ALL_FIELDS = ["standing_1", "standing_2", "dying", "undead", "attack_graphic",
              "attack_graphic2", "garrison_graphic", "spawning_graphic",
              "upgrade_graphic", "hero_glow_graphic", "idle_attack_graphic",
              "special_graphic", "construction_graphic", "snow_graphic",
              "destruction_graphic", "destruction_rubble_graphic",
              "researching_graphic", "research_completed_graphic"]


def refs(u):
    out = {}
    for f in ALL_FIELDS:
        v = u.get(f)
        if isinstance(v, int) and v in slot2g:
            nm = (slot2g[v]["file"] or "").strip().lower()
            if nm:
                out[f] = nm
    return out


# ------------------------------------------------------- the consistency test
print("=== CONSISTENCY: does the explicit field's FileName carry the anim token? ===")
cons = collections.Counter()
mismatch_ex = []
byid = {}
for ci, civ in enumerate(C):
    for u in civ["units"]:
        byid.setdefault(u["id"], {})[ci] = u

for uid, per in byid.items():
    u = per[sorted(per)[0]]
    r = refs(u)
    base_stem = None
    st = r.get("standing_1")
    if st:
        s, a = canon(st)
        if a:
            base_stem = s
    if base_stem is None:
        continue
    for f, want in FIELD_ANIM.items():
        nm = r.get(f)
        if not nm:
            continue
        s, a = canon(nm)
        if f == "standing_1":
            continue
        cons["checked"] += 1
        if a == want:
            cons["token matches expected anim"] += 1
        else:
            cons["token DIFFERS from expected anim"] += 1
            if len(mismatch_ex) < 10:
                mismatch_ex.append((uid, u["name"], f, want, nm, a))
        if s == base_stem:
            cons["stem == standing_1 stem"] += 1
        else:
            cons["stem != standing_1 stem"] += 1
            if len(mismatch_ex) < 16:
                mismatch_ex.append((uid, u["name"], f, base_stem, s, "STEM-DIFF"))
for k, v in cons.items():
    print("   %-34s %d" % (k, v))
for m in mismatch_ex[:12]:
    print("      %s" % (m,))

# ------------------------------------------------ build stem-substituted sets
print("\n=== BUILD: stem-substituted sprite set per unit ===")
WANT = ["idlea", "idleb", "walka", "attacka", "attackb", "deatha", "decaya"]
sets = {}
cov = collections.Counter()
for uid, per in byid.items():
    u = per[sorted(per)[0]]
    r = refs(u)
    st = r.get("standing_1")
    s, a = canon(st) if st else (None, None)
    entry = {"unit_id": uid, "name": u["name"], "type": u["type"], "class": u["class"],
             "stem": s, "anims": {}}
    if s:
        for w in WANT:
            nm = "%s_%s" % (s, w)
            g = dat_by_canon.get(nm)
            entry["anims"][w] = {
                "sld": (nm + ".sld"),
                "x1": (nm + "_x1.sld") in disk_canon and True or ((nm + "_x1") in disk_canon),
                "slot": g["slot"] if g else None,
                "frame_count": g["frame_count"] if g else None,
                "angle_count": g["angle_count"] if g else None,
                "on_disk": (nm in disk_canon),
            }
            if entry["anims"][w]["on_disk"]:
                cov[w] += 1
    sets[uid] = entry

print("units with a resolvable stem: %d / %d"
      % (sum(1 for e in sets.values() if e["stem"]), len(sets)))
for w in WANT:
    print("   %-8s resolvable on disk: %5d" % (w, cov[w]))
any_sprite = sum(1 for e in sets.values() if any(v["on_disk"] for v in e["anims"].values()))
print("units with AT LEAST ONE sprite on disk: %d" % any_sprite)

json.dump(sets, open(os.path.join(HERE, "unit_sprite_sets.json"), "w", encoding="utf-8"),
          ensure_ascii=False)
print("\nwrote unit_sprite_sets.json")
