# -*- coding: utf-8 -*-
r"""The IDEAL injective experiment: two DIFFERENT-looking buttons, one screen.

The four injective civilizations found by `probe_injective_civ.py` are injective
only if the two subjects are visually distinguishable:

  * GEORGIANS: kind-P unit 320 and kind-T unit 588 are BOTH "Siege Onager" at
    building 49 -- whichever layer drives, the player sees one "Siege Onager"
    button.  Not injective in practice.
  * SPARTANS: kind-P unit 2147 and kind-T unit 13 are BOTH "Fishing Ship" at
    building 2172.  Same problem.

The naming collision is not an accident: the disagreement IS a variant-id
substitution, and the variants usually share a display name.

So search every civilization and every building for a (kind-P, kind-T) pair that
(a) sits in the SAME building, so one screen answers it;
(b) has DIFFERENT display names, so the player can tell them apart;
(c) has the kind-T row at `ResearchedCompleted`, so its absence cannot be
    explained by an un-researched prerequisite;
(d) needs the lowest age, so no long game.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402
from aoe2mod.semantic.index import index as sem_index       # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
idx = sem_index()
trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)

ZH = {}
kd = os.path.join(GAME, "resources", "zh", "strings", "key-value")
for fn in sorted(os.listdir(kd)):
    if fn.endswith(".txt"):
        with open(os.path.join(kd, fn), "rb") as fh:
            for line in fh.read().decode("utf-8-sig", "replace").splitlines():
                k, _, v = line.strip().partition("\t")
                if k.strip().isdigit() and v.startswith('"') and v.endswith('"'):
                    ZH.setdefault(int(k.strip()), v[1:-1])


def uname(uid):
    u = idx.get("unit", uid)
    return (u and (u.zh or u.en)) or ("unit %s" % uid)


def bname(bid):
    for t in trees.values():
        for r in CT.rows_of(t):
            if r.get("Use Type") == "Building" and r.get("Node ID") == bid:
                sid = r.get("Name String ID")
                if sid and sid in ZH:
                    return ZH[sid]
    return "bldg %s" % bid


civs = {}
seen = set()
for _pk, rec in sorted(panels.items()):
    for disp in sorted(k for k in rec["obj"] if isinstance(k, str)):
        if (rec["path"], disp) in seen:
            continue
        seen.add((rec["path"], disp))
        stem = CT.civ_file_stem(disp)
        if stem in trees:
            civs[stem] = (disp, rec["obj"])

hits = []
for stem, (disp, obj) in sorted(civs.items()):
    tree = trees[stem]
    owned = {r.get("Node ID") for r in CT.rows_of(tree)
             if r.get("Use Type") == "Building"}
    rows = {r.get("Node ID"): r for r in CT.unit_rows(tree)
            if r.get("Node ID") is not None}
    # panel, per building
    panel_by_b = {}
    for b_id in BP.buildings(obj, disp) or []:
        us = BP.entries(obj, disp, b_id, BP.UNITS_KEY) or []
        if us:
            panel_by_b[b_id] = us
    panel_ids_all = {e.get("ID") for us in panel_by_b.values() for e in us}
    for b_id, us in panel_by_b.items():
        if b_id not in owned:
            continue
        # kind P: panel lists, tree cannot supply at this building
        kind_p = []
        for e in us:
            uid = e.get("ID")
            row = rows.get(uid)
            if row is None or row.get("Node Status") == "NotAvailable":
                kind_p.append((uid, e.get("Name"), e.get("RequiredAge")))
        if not kind_p:
            continue
        # kind T: tree grants (RC), panel silent EVERYWHERE, same building
        kind_t = []
        for uid, r in rows.items():
            if r.get("Building ID") != b_id:
                continue
            if r.get("Node Status") != "ResearchedCompleted":
                continue
            if uid in panel_ids_all:
                continue
            kind_t.append((uid, r.get("Name"), r.get("Age ID")))
        if not kind_t:
            continue
        for pu, pn, pa in kind_p:
            for tu, tn, ta in kind_t:
                if (pn or "").lower() == (tn or "").lower():
                    continue          # visually ambiguous -- skip
                hits.append((max(pa or 9, ta or 9), stem, b_id, pu, pn, pa,
                             tu, tn, ta))

hits.sort()
print("candidates with DIFFERENT names, kind-T at ResearchedCompleted,")
print("same building, kind-P and kind-T both present:")
print()
print("  %-13s %-26s %-6s %-24s %-5s | %-24s %-5s"
      % ("civ", "building", "P id", "P name (panel-only)", "age",
         "T name (tree-only)", "age"))
for mx, stem, b, pu, pn, pa, tu, tn, ta in hits:
    print("  %-13s %-26s %-6s %-24s %-5s | %-24s %-5s"
          % (stem, bname(b), pu, pn, pa, tn, ta))
print()
print("total: %d" % len(hits))
if hits:
    mx, stem, b, pu, pn, pa, tu, tn, ta = hits[0]
    print()
    print("*** BEST: %s, building %s (%s), max age %s ***"
          % (stem, b, bname(b), mx))
    print("    P (panel lists, tree cannot): %s %s  age %s" % (pu, pn, pa))
    print("    T (tree grants, panel silent): %s %s  age %s" % (tu, tn, ta))
    print()
    print("    panel drives -> %s present, %s ABSENT" % (pn, tn))
    print("    tree drives  -> %s ABSENT, %s present" % (pn, tn))
    print("    union        -> both present")
    print("    neither      -> both absent")
