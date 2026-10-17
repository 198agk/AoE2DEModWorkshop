#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a16_coverage.py -- definitive coverage taxonomy for entity -> sprite.

Two resolution paths, tested separately:
  DIRECT : the graphic's FileName verbatim + '.sld' exists in drs\\graphics
  SUBST  : FileName ends in an animation token -> replace that token with each
           sibling animation token and test each resulting name on disk

For every distinct unit id we report which path worked, what the failure class is
when neither did, and the honest denominator.  Also enumerates the failure reasons
for unmapped graphics.
"""
import json, os, collections

HERE = os.path.dirname(os.path.abspath(__file__))
GFXDIR = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs\graphics"
POM = r"D:\Games\Steam\steamapps\common\AoE2DE\modes\Pompeii\resources\_common\drs\graphics"
TRE = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs\small-trees"
G = json.load(open(os.path.join(HERE, "graphics_raw.json"), encoding="utf-8"))
C = json.load(open(os.path.join(HERE, "units_raw.json"), encoding="utf-8"))

ANIMS = set("""idlea idleb idlec walka walkb walkc attacka attackb attackc
deatha deathb decaya constr rubble destruction flag garrison""".split())
SPRITE_ANIMS = ["idlea", "idleb", "walka", "attacka", "attackb", "deatha", "decaya"]


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


def stems(d):
    out = set()
    if not os.path.isdir(d):
        return out
    for f in os.listdir(d):
        if f.lower().endswith(".sld"):
            n = f.lower()[:-4]
            if n.endswith("_x1") or n.endswith("_x2"):
                n = n[:-3]
            out.add(n)
    return out


main = stems(GFXDIR)
pom = stems(POM)
tre = stems(TRE)
print("on-disk canonical stems: drs\\graphics=%d  Pompeii=%d  small-trees=%d"
      % (len(main), len(pom), len(tre)))

slot2g = {g["slot"]: g for g in G}
dat_by_canon = {}
for g in G:
    f = (g["file"] or "").strip().lower()
    if f:
        s, a = canon(f)
        dat_by_canon["%s_%s" % (s, a) if a else s] = g

ALL_FIELDS = ["standing_1", "standing_2", "dying", "undead", "attack_graphic",
              "attack_graphic2", "garrison_graphic", "spawning_graphic",
              "upgrade_graphic", "hero_glow_graphic", "idle_attack_graphic",
              "special_graphic", "construction_graphic", "snow_graphic",
              "destruction_graphic", "destruction_rubble_graphic",
              "researching_graphic", "research_completed_graphic"]


def resolve(u):
    """-> (direct_files, subst_files, diag)"""
    direct, subst, diag = {}, {}, {}
    for f in ALL_FIELDS:
        v = u.get(f)
        if not isinstance(v, int):
            continue
        if v < 0:
            diag[f] = "sentinel(-1)"
            continue
        g = slot2g.get(v)
        if g is None:
            diag[f] = "slot-not-decoded"
            continue
        nm = (g["file"] or "").strip().lower()
        if not nm:
            diag[f] = "graphic-has-no-FileName"
            continue
        s, a = canon(nm)
        if nm in main or s in main:
            direct[f] = nm
        elif a and ("%s_%s" % (s, a)) in main:
            direct[f] = nm
        if a:
            got = {}
            for w in SPRITE_ANIMS:
                cand = "%s_%s" % (s, w)
                if cand in main:
                    got[w] = cand
            if got:
                subst[f] = got
        elif s in main or nm in main:
            subst[f] = {"direct": nm}
        dg = []
        if not direct.get(f) and not subst.get(f):
            if nm in ("none",):
                diag[f] = "FileName=='None' (unset)"
            elif not a:
                diag[f] = "no-anim-token-and-not-on-disk"
            elif not any("%s_%s" % (s, w) in main for w in SPRITE_ANIMS):
                diag[f] = "stem-not-on-disk"
            else:
                diag[f] = "other"
    return direct, subst, diag


byid = {}
for ci, civ in enumerate(C):
    for u in civ["units"]:
        byid.setdefault(u["id"], {})[ci] = u

cov = collections.Counter()
fail_reason = collections.Counter()
rows = []
for uid, per in sorted(byid.items()):
    civ0 = sorted(per)[0]
    u = per[civ0]
    direct, subst, diag = resolve(u)
    n_file = sum(1 for k, v in direct.items() if v)
    n_sub = sum(1 for k, v in subst.items() if v)
    ok = bool(direct) or bool(subst)
    cov["unit ids total"] += 1
    if ok:
        cov["mapped to >=1 sprite"] += 1
        if direct:
            cov["with a DIRECT (verbatim FileName) hit"] += 1
        if any(isinstance(v, dict) and "idlea" in v for v in subst.values()):
            cov["with a substituted idleA"] += 1
    else:
        cov["UNMAPPED"] += 1
        reasons = set(diag.values())
        if not diag:
            fail_reason["no graphic fields set at all (all -1)"] += 1
        elif reasons == {"sentinel(-1)"}:
            fail_reason["all graphic fields are the -1 sentinel"] += 1
        elif "graphic-has-no-FileName" in reasons:
            fail_reason["graphic exists but FileName is empty"] += 1
        elif "FileName=='None' (unset)" in reasons:
            fail_reason["FileName is the literal 'None'"] += 1
        elif "stem-not-on-disk" in reasons:
            fail_reason["stem not present in drs\\graphics"] += 1
        else:
            fail_reason["other: " + ",".join(sorted(reasons))] += 1
    rows.append((uid, u["name"], u["type"], u["class"], n_file, n_sub, sorted(set(diag.values()))))

print("\n=== UNIT -> SPRITE COVERAGE (by distinct unit id, primary civ) ===")
for k in ["unit ids total", "mapped to >=1 sprite", "UNMAPPED",
          "with a DIRECT (verbatim FileName) hit", "with a substituted idleA"]:
    print("   %-42s %d" % (k, cov[k]))
print("\n=== failure taxonomy for the UNMAPPED ===")
for k, v in fail_reason.most_common():
    print("   %-46s %d" % (k, v))

# by unit type
print("\n=== coverage by unit Type ===")
byt = collections.defaultdict(lambda: [0, 0])
for uid, nm, t, cl, nf, ns, dg in rows:
    byt[t][0] += 1
    if nf or ns:
        byt[t][1] += 1
TN = {10: "EyeCandy", 20: "Flag", 25: "DeadFish?", 30: "Moving", 60: "Projectile",
      70: "Combatant/Creatable", 80: "Building"}
for t in sorted(byt):
    tot, ok = byt[t]
    print("   type %-4d %-22s %5d / %5d  (%.1f%%)"
          % (t, TN.get(t, "?"), ok, tot, 100.0 * ok / tot))

# the unmapped, listed
un = [r for r in rows if not (r[4] or r[5])]
print("\n=== first 25 UNMAPPED units ===")
for r in un[:25]:
    print("   id %-5d %-26s type=%-4d class=%-4d why=%s" % (r[0], r[1][:26], r[2], r[3], r[6]))
print("... total unmapped: %d" % len(un))
json.dump([{"unit_id": r[0], "name": r[1], "type": r[2], "class": r[3],
            "n_direct": r[4], "n_subst": r[5], "reasons": r[6]} for r in un],
          open(os.path.join(HERE, "unmapped_units.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\nwrote unmapped_units.json")
