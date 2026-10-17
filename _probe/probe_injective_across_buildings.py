# -*- coding: utf-8 -*-
r"""Injective across BUILDINGS: one game, two different buttons, two screens.

The same-building search found 0 because the disagreement is a *variant-id
substitution* and the variants share a display name (Siege Onager 320 vs 588,
Fishing Ship 2147 vs 13).  A player cannot tell those apart.

But one game visits many buildings.  So the requirement relaxes to:

  * a kind-P subject in building A (panel lists it, tree cannot supply it)
  * a kind-T subject in building B (tree grants it, panel is silent)
  * DIFFERENT display names
  * both at the lowest age, both in buildings the civ owns

Then one game answers it: click A, click B.
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

out = []
for stem, (disp, obj) in sorted(civs.items()):
    tree = trees[stem]
    owned = {r.get("Node ID") for r in CT.rows_of(tree)
             if r.get("Use Type") == "Building"}
    rows = {r.get("Node ID"): r for r in CT.unit_rows(tree)
            if r.get("Node ID") is not None}
    panel_ids, panel_rows = set(), {}
    for b_id in BP.buildings(obj, disp) or []:
        for e in (BP.entries(obj, disp, b_id, BP.UNITS_KEY) or []):
            panel_ids.add(e.get("ID"))
            panel_rows[e.get("ID")] = (b_id, e.get("RequiredAge"), e.get("Name"))

    kind_p = [(uid, b, age, nm) for uid, (b, age, nm) in panel_rows.items()
              if b in owned
              and (uid not in rows or rows[uid].get("Node Status")
                   == "NotAvailable")]
    kind_t = [(uid, r.get("Building ID"), r.get("Age ID"), r.get("Name"))
              for uid, r in rows.items()
              if r.get("Node Status") == "ResearchedCompleted"
              and r.get("Building ID") in owned
              and uid not in panel_ids]

    for pu, pb, pa, pn in kind_p:
        for tu, tb, ta, tn in kind_t:
            if (pn or "").lower() == (tn or "").lower():
                continue
            out.append((max(pa or 9, ta or 9), stem, pb, pu, pn, pa,
                        tb, tu, tn, ta))

out.sort()
print("injective across buildings, distinct names, both ResearchedCompleted-able:")
print()
print("  %-12s %-22s %-22s" % ("civ", "P: panel-only", "T: tree-only"))
print("  %-12s %-22s %-22s" % ("", "(building, age)", "(building, age)"))
for mx, stem, pb, pu, pn, pa, tb, tu, tn, ta in out[:40]:
    print("  %-12s %-22s %-22s" % (stem,
                                   "%s a%s (%s)" % (pn, pa, bname(pb)),
                                   "%s a%s (%s)" % (tn, ta, bname(tb))))
print()
print("total: %d   (max age column spans %s)"
      % (len(out), sorted({o[0] for o in out})))
if out:
    mx, stem, pb, pu, pn, pa, tb, tu, tn, ta = out[0]
    print()
    print("*** LOWEST-AGE CANDIDATE: %s ***" % stem)
    print("    P: %s (unit %s) age %s in %s" % (pn, pu, pa, bname(pb)))
    print("    T: %s (unit %s) age %s in %s" % (tn, tu, ta, bname(tb)))
    print()
    print("    panel drives -> %s present, %s ABSENT" % (pn, tn))
    print("    tree drives  -> %s ABSENT, %s present" % (pn, tn))
    print("    union        -> BOTH present")
    print("    neither      -> BOTH absent")
