# -*- coding: utf-8 -*-
r"""Does the shipped data really switch a BUILDING off for one civilization?

`probe_revoke_mechanism.py` found 9 shipped `type 2 ... b = 0` disable
commands, and exactly one of them is reached by a CIVILIZATION-OWNED tech
rather than a global one:

    tech 932 / 940  'Mule Cart (make avail)'  civ = 45 / 44  ->  effect 944
    effect 944      enable 1808, disable 562, disable 584

562 is the Lumber Camp and 584 its second age variant.  If that reading is
right, the shipped data says "Armenians and Georgians cannot build a Lumber
Camp; they get a Mule Cart instead" -- i.e. the `.dat` *does* carry a
per-civilization disable, and `unit.availability.revoke` can be built on the
same shape instead of on a guess.

This file checks the four links of that chain:
  A. who owns tech 932 / 940, and is it free (no research cost, no location)?
  B. what does effect 944 actually command?
  C. what do the Armenians' and Georgians' TECH TREES say about 562 / 584?
  D. what do the other civilizations' trees say (the contrast group)?

Read-only.
"""
import contextlib
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import aoe2mod.dat.parser as P                             # noqa: E402
import aoe2mod.dat.locate as L                            # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402
from aoe2mod.game import locations as G                    # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
# The tree has THREE id spaces and `Node ID` is shared between them, so a
# building must be asked for in its own space.  `civtechtrees` exposes only
# UNIT_USE_TYPES and TECH_USE_TYPES, so name the third one here instead of
# letting a building query silently answer "no row".
BUILDING_USE_TYPES = ("Building",)
fails = []


def check(name, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + name + ("  :: " + str(detail) if detail else ""))
    if not ok:
        fails.append(name)


raw, how = P.load_dat(G.dat_path(GAME))
pr = P.Parser(raw)
with contextlib.redirect_stdout(io.StringIO()):
    pr.parse()
st = pr.stats
techs = st.get("techs") or []
effects = st.get("effects") or []
civs, _cs, _gv, _tail = L.locate(raw, parser=pr)

print("=== A. the owners of the disabling effect")
for ti in (932, 940):
    t = techs[ti]
    locs = t.get("research_locations") or []
    print("  tech %-5d %-28r civ=%r locations=%r"
          % (ti, t.get("name"), t.get("civ"), locs))
    check("tech %d is owned by one civilization" % ti,
          isinstance(t.get("civ"), int) and t.get("civ") >= 0, t.get("civ"))
    # A tech with no page in the UI has location -1 and zero cost.  That is the
    # shape the civilization bonuses use, and the shape `datgrant.pick_tech`
    # deliberately prefers ("a technology the civilization owns and that fires
    # at 0:00").  Demanding an EMPTY list here was my error, not the data's.
    check("tech %d is invisible in the UI (location -1, free)" % ti,
          all(l[0] < 0 for l in locs) and
          all((l[1], l[2]) == (0, 0) for l in locs), "locations=%r" % (locs,))

owners = sorted({techs[ti].get("civ") for ti in (932, 940)})
print("  civ indexes that own them: %r" % (owners,))
for ci in owners:
    if 0 <= ci < len(civs):
        print("    civ %d = %r" % (ci, civs[ci].get("name")))

print("=== B. what effect 944 commands")
eff = effects[944]
print("  effect 944 %r" % (eff.get("name"),))
for c in eff.get("commands") or []:
    print("    type=%r a=%r b=%r c=%r d=%r" % (c[0], c[1], c[2], c[3], c[4]))
check("effect 944 enables unit 1808 (the Mule Cart)",
      any(c[0] == 2 and c[1] == 1808 and c[2] == 1 for c in eff["commands"]))
check("effect 944 disables 562 and 584 (Lumber Camp and its age variant)",
      {(c[0], c[1], c[2]) for c in eff["commands"]} >= {(2, 562, 0), (2, 584, 0)})

print("=== C. the two civilizations' own trees")
trees = CT.load_trees(GAME)
for ci in owners:
    name = civs[ci].get("name") or ""
    stem = CT.civ_file_stem(name)
    tree = trees.get(stem)
    check("a tree file exists for %r" % name, tree is not None, stem)
    if not tree:
        continue
    for bid in (562, 584, 1808):
        status = CT.node_status(tree, bid, BUILDING_USE_TYPES)
        row = CT.row_for(tree, bid, BUILDING_USE_TYPES)
        print("    %-12s node %-5d %-20r %r"
              % (stem, bid, status, (row or {}).get("Name")))

print("=== D. contrast: what everyone else says about 562")
granted = []
for stem, tree in sorted(trees.items()):
    if CT.node_status(tree, 562, BUILDING_USE_TYPES) == "ResearchedCompleted":
        granted.append(stem)
print("  civilizations whose tree grants Lumber Camp 562: %d" % len(granted))
print("  %r" % (granted[:8],))
mule = owners
for ci in mule:
    stem = CT.civ_file_stem(civs[ci].get("name") or "")
    check("%s does NOT grant Lumber Camp 562" % stem, stem not in granted, stem)
check("at least 40 other civilizations DO grant it", len(granted) >= 40, len(granted))

print()
print("MULE CART PRECEDENT: %s" % ("ALL CHECKS PASSED" if not fails else "FAILED"))
if fails:
    for f in fails:
        print("  - " + f)
sys.exit(1 if fails else 0)
