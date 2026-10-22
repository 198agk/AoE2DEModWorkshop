# -*- coding: utf-8 -*-
r"""PIN: the ZERO-MOD experiment -- the shipped files already contradict.

Two in-game tests were spent on mod-based experiments that could not answer the
question.  The design audit (`_probe/team/auditor/REPORT.md`) then found the
replacement ambiguous too: a sibling mod ships the same three engine paths with
different content, the control `.dat` is byte-identical between them, and one of
the two subjects was masked by the tree anyway.

So: use what the game already ships.  The tree and the panel DISAGREE on a small
number of (civ, unit) pairs, and every one of them is observable with NO MOD
INSTALLED, which removes the "did it load / did it win the layer" confounds
entirely.

  kind P -- the panel lists the unit, the tree says `NotAvailable`.
            A visible button proves the menu reads the PANEL: the tree cannot
            supply it.
  kind T -- the tree grants the unit, the panel does not list it.
            A MISSING button proves the menu reads the PANEL (the tree would
            have supplied it); a visible one points at the TREE.

The counts and the JURCHENS Barracks case are asserted, so a game update that
changes the disagreement makes this suite fail rather than quietly retire the
only clean experiment the project has.

Run:  $env:PYTHONPATH='D:\\Software\\AI\\帝国项目'; python _probe\test_zero_mod_experiment.py
"""
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
fails = []


def check(name, ok, detail=""):
    print("  %-62s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "   %s" % detail))
    if not ok:
        fails.append(name)


trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)

# Every unit id any civ's tree models -- the comparable universe.
NODES = sorted({r.get("Node ID") for t in trees.values()
                for r in CT.unit_rows(t) if r.get("Node ID") is not None})
INFO = {}
for t in trees.values():
    for r in CT.unit_rows(t):
        nid = r.get("Node ID")
        if nid is not None:
            INFO.setdefault(nid, (r.get("Building ID"), r.get("Age ID"),
                                  r.get("Name")))

P, T = defaultdict(list), defaultdict(list)
# `load_all()` is keyed by civ, but EACH value's `obj` is the whole multi-civ
# file -- iterating both levels visits a civilization once per civ record and
# multiplies every count by ~57.  Dedupe on (file, display name).
seen = set()
for _pk, rec in sorted(panels.items()):
    obj = rec["obj"]
    for disp in sorted(k for k in obj if isinstance(k, str)):
        if (rec["path"], disp) in seen:
            continue
        seen.add((rec["path"], disp))
        stem = CT.civ_file_stem(disp)
        tree = trees.get(stem)
        if tree is None:
            continue
        blds = {r.get("Node ID") for r in CT.rows_of(tree)
                if r.get("Use Type") == "Building"}
        for nid in NODES:
            st = CT.node_status(tree, nid, CT.UNIT_USE_TYPES)
            bb, ee = BP.find_entry(obj, disp, nid, BP.UNITS_KEY)
            bl, age, nm = INFO.get(nid, (None, None, None))
            if st == "NotAvailable" and ee is not None:
                P[stem].append((nid, ee.get("RequiredAge"), bb))
            elif st == "ResearchedCompleted" and ee is None and bb is None:
                if bl in blds:
                    T[stem].append((nid, age, bl))

np_, nt = sum(len(v) for v in P.values()), sum(len(v) for v in T.values())
print("A  the shipped disagreement exists, and is small enough to name")
check("kind P (panel lists, tree says NotAvailable) == 11 pairs", np_ == 11,
      "got %d: %s" % (np_, {k: v for k, v in sorted(P.items()) if v}))
check("kind T (tree grants, panel silent) == 3 pairs", nt == 3,
      "got %d: %s" % (nt, {k: v for k, v in sorted(T.items()) if v}))
check("the civ keys are disjoint where it matters (no civ has both kinds)",
      not (set(P) & set(T)) or not any(P[c] and T[c] for c in set(P) & set(T)),
      "a civ with both kinds would be the ideal single-game test")

print()
print("B  the MUISCA Barracks case (the corrected GAME 1 observation)")
# The Jurchens case below is kept because it is still a real kind-P pair -- but it
# is UNUSABLE as a subject (section H), so the recommended case is Muisca 359.
_mu = trees["MUISCA"]
check("Muisca's tree says unit 359 (Halberdier) NotAvailable",
      CT.node_status(_mu, 359, CT.UNIT_USE_TYPES) == "NotAvailable")
_mk = BP.panel_path_for(GAME, "Muisca")[1]
_mobj = panels[_mk]["obj"]
_b359, _e359 = BP.find_entry(_mobj, _mk, 359, BP.UNITS_KEY)
check("Muisca's PANEL lists 359 (Halberdier) at building 12",
      _e359 is not None and _b359 == 12, "bldg=%r entry=%r" % (_b359, _e359))
_mtechs = {e.get("ID") for blk in BP.buildings(_mobj, "Muisca")
           for e in (blk.get(BP.TECHS_KEY) or [])}
check("Muisca's PANEL also lists 359's upgrade tech 429 -- a COMPLETE path",
      429 in _mtechs, "panel Techs = %s" % sorted(_mtechs))

print()
print("B2 the JURCHENS case is still a kind-P pair, but unusable as a subject")
j = trees["JURCHENS"]
check("Jurchens' tree says unit 77 (Long Swordsman) NotAvailable",
      CT.node_status(j, 77, CT.UNIT_USE_TYPES) == "NotAvailable")
check("Jurchens' tree says unit 473 (Two-Handed Swordsman) NotAvailable",
      CT.node_status(j, 473, CT.UNIT_USE_TYPES) == "NotAvailable")
check("Jurchens' tree says unit 567 (Champion) NotAvailable",
      CT.node_status(j, 567, CT.UNIT_USE_TYPES) == "NotAvailable")
_pk = BP.panel_path_for(GAME, "Jurchens")[1]
_obj = panels[_pk]["obj"]
for nid, nm in ((77, "Long Swordsman"), (473, "Two-Handed"), (567, "Champion")):
    _b, _e = BP.find_entry(_obj, _pk, nid, BP.UNITS_KEY)
    check("Jurchens' PANEL lists %d (%s) at building 12" % (nid, nm),
          _e is not None and _b == 12, "bldg=%r entry=%r" % (_b, _e))
_jtechs = {e.get("ID") for blk in BP.buildings(_obj, "Jurchens")
           for e in (blk.get(BP.TECHS_KEY) or [])}
check("but Jurchens' panel does NOT offer 77's upgrade tech 207, so the path is "
      "incomplete and the subject is unusable", 207 not in _jtechs,
      "panel Techs = %s" % sorted(_jtechs))

print()
print("C  the case is NOT an age artifact (the mistake the last test made)")
# Hand Cannoneer (5) carries RequiredAge 4 for every civ that has it, so a
# Dark-Age game could never show it however the menu is fed.  Assert the contrast
# subject's gate explicitly, so the reason the OLD test was uninformative is
# pinned alongside the reason this one is not.
_tk = BP.panel_path_for(GAME, "Turks")[1]
_a5 = BP.find_entry(panels[_tk]["obj"], _tk, 5, BP.UNITS_KEY)[1]
check("the CONTRAST subject (Hand Cannoneer 5) really is Age 4 (so the old test "
      "was gated)", _a5 is not None and _a5.get("RequiredAge") == 4,
      "Turks entry: %r" % (_a5,))

print()
print("D  the age profile of the subjects")
_77, _473, _567 = (INFO[77][1], INFO[473][1], INFO[567][1])
check("node 77's tree Age ID is 3 (Castle) -- no Imperial requirement",
      _77 == 3, "Age ID=%r" % _77)
print("      the CORRECTED GAME 1 subject is Muisca 359 (Halberdier), Imperial Age")
print("      Barracks -> can the spear line reach 长戟兵?")
print("        yes -> the menu reads the PANEL (its upgrade tech 429 is offered)")
print("        no  -> the menu does NOT read the panel's complete path")
print("      (JURCHENS 77 is a Castle-Age pair but its panel path is incomplete)")

print()
print("E  no enabled mod can contaminate it")
import json                                                # noqa: E402
ACC = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391"
MODS = os.path.join(ACC, "mods")
try:
    st = json.loads(open(os.path.join(MODS, "mod-status.json"), "rb")
                    .read().decode("utf-8-sig"), strict=False)
    dirty = []
    ours = []
    for m in st.get("Mods", []):
        if not m.get("Enabled"):
            continue
        d = os.path.join(MODS, (m.get("Path") or "").replace("//", os.sep))
        if not os.path.isdir(d):
            continue
        for root, _dd, files in os.walk(d):
            for f in files:
                rel = os.path.relpath(os.path.join(root, f), d).lower()
                if ("civtechtrees" in rel or "futuravailableunits" in rel
                        or rel.endswith("empires2_x2_p1.dat")):
                    (ours if os.path.basename(d).startswith("dsh ")
                     else dirty).append((os.path.basename(d), rel))
    # This machine's own experiment mods are EXPECTED to be enabled and to ship
    # a `.dat` -- that is what they are for.  What this pin has to catch is a
    # THIRD-PARTY mod quietly shipping game data the shipped files disagree
    # with, because then a reading cannot be attributed to the shipped data.
    # Measured 2026-10-22: the first version of this pin counted `dsh test v49`
    # (this tool's own mod, enabled on purpose) and reported a clean machine as
    # contaminated -- the same defect as pinning the player's mod list as a
    # literal.
    check("no THIRD-PARTY enabled mod ships a tree / panel / dat file",
          not dirty, "contaminated by %s" % dirty[:3])
    if ours:
        print("     (this tool's own enabled mods, expected: %s)"
              % sorted({n for n, _r in ours}))
except (OSError, ValueError) as e:
    check("the profile's mod-status.json is readable", False, str(e))

print()
print("F  can ONE civilization be injective?  (the audit's finding #4)")
# The audit's point: a single kind-P observation is 2-to-1 ("the panel drives" vs
# "the two layers are unioned").  A single civilization would be injective if it
# had BOTH kinds on screen -- so search for one, with two filters that a first
# attempt lacked:
#   * `buildpanel.buildings()` returns building BLOCKS (dicts), not ids; iterating
#     it and passing each element as `building_id` makes every panel lookup return
#     [] and the search reports "no injective civ" for the wrong reason.
#   * an internal object with no display name (unit 320 is `ARROW8`) is not
#     observable; admitting it makes GEORGIANS look injective when it is not.
from aoe2mod.semantic.index import index as sem_index       # noqa: E402
_idx = sem_index()


def _name_of(uid):
    u = _idx.get("unit", uid)
    return ((u.zh or u.en) if u else None) or None


civs = {}
_seen = set()
for _pk, rec in sorted(panels.items()):
    for disp in sorted(k for k in rec["obj"] if isinstance(k, str)):
        if (rec["path"], disp) in _seen:
            continue
        _seen.add((rec["path"], disp))
        stem = CT.civ_file_stem(disp)
        if stem in trees:
            civs[stem] = (disp, rec["obj"])

kindP, kindT = {}, {}
for stem, (disp, obj) in sorted(civs.items()):
    tree = trees[stem]
    owned = {r.get("Node ID") for r in CT.rows_of(tree)
             if r.get("Use Type") == "Building"}
    trows = {r.get("Node ID"): r for r in CT.unit_rows(tree)
             if r.get("Node ID") is not None}
    panel = {}
    for blk in BP.buildings(obj, disp):        # <- iterating BLOCKS, not ids
        for e in (blk.get(BP.UNITS_KEY) or []):
            panel.setdefault(e.get("ID"), []).append((blk.get("ID"),
                                                      e.get("RequiredAge"),
                                                      e.get("Name")))
    P = []
    for uid, places in panel.items():
        if _name_of(uid) is None:              # invisible internals are not subjects
            continue
        for bid, age, nm in places:
            if bid not in owned:
                continue
            st = trows[uid].get("Node Status") if uid in trows else None
            if uid not in trows or st == "NotAvailable":
                P.append((uid, nm))
    T = []
    for uid, r in trows.items():
        if (r.get("Node Status") == "ResearchedCompleted"
                and r.get("Building ID") in owned
                and uid not in panel and _name_of(uid) is not None):
            T.append((uid, r.get("Name")))
    if P:
        kindP[stem] = P
    if T:
        kindT[stem] = T

_both = sorted(set(kindP) & set(kindT))
print("      kind-P civs: %d   kind-T civs: %d   both: %d"
      % (len(kindP), len(kindT), len(_both)))
for s in _both:
    _pn = {(n or "").lower() for _u, n in kindP[s]}
    _tn = {(n or "").lower() for _u, n in kindT[s]}
    print("        %-11s P=%s T=%s disjoint-names=%s"
          % (s, sorted(_pn), sorted(_tn), not (_pn & _tn)))
check("NO single civilization is injective (only SPARTANS has both, and its two "
      "subjects are BOTH 'Fishing Ship')",
      len(_both) == 1 and _both[0] == "SPARTANS"
      and not ({(n or "").lower() for _u, n in kindP["SPARTANS"]}
               - {(n or "").lower() for _u, n in kindT["SPARTANS"]}),
      "civs with both: %s" % _both)
print("     [note] the injective answer is therefore a TWO-GAME protocol (no "
      "single game is decisive)")
print("        GAME 1  MUISCA  Imperial Age  Barracks(12)  look for 长戟兵(359)")
print("           tree=NotAvailable; panel lists 359 AND its upgrade tech 429")
print("           -> present => PANEL or UNION")
print("        GAME 2  SICILIANS Imperial Age SiegeWorkshop(49) look for 重型投石车(588)")
print("           tree=ResearchedCompleted, panel SILENT both channels -> TREE or UNION")
print("        1有2无 -> PANEL | 1无2有 -> TREE | 都有 -> UNION | 都无 -> neither")
print("        (see section H: the earlier JURCHENS 77 subject was UNUSABLE)")
print()
print("G  the panel has TWO availability channels -- kind-T must be silent in BOTH")
# `futuravailableunits.json` lists, per building, a `Units` array AND a `Techs`
# array.  A unit that arrives via an upgrade research appears in the *Techs*
# array (research it, then the unit is trainable).  Unit 588 (Siege Onager) has
# `Trigger Tech ID = 320`, and:
#     GEORGIANS  panel Techs at building 49 CONTAINS 320
#     SICILIANS  panel Techs at building 49 does NOT
# So for GEORGIANS the panel is NOT silent about Siege Onager -- it says so in the
# Techs channel.  Treating it as a kind-T disagreement would have made "no Siege
# Onager button" read as evidence about the panel when it was evidence about a
# gate.  This is the third gate class to bite this project (age, then research).
_old, _new = [], []
for _stem, (_disp, _obj) in sorted(civs.items()):
    _tree = trees[_stem]
    _owned = {r.get("Node ID") for r in CT.rows_of(_tree)
              if r.get("Use Type") == "Building"}
    _units_all, _techs_all = set(), set()
    for _blk in BP.buildings(_obj, _disp):
        for _e in (_blk.get(BP.UNITS_KEY) or []):
            _units_all.add(_e.get("ID"))
        for _e in (_blk.get(BP.TECHS_KEY) or []):
            _techs_all.add(_e.get("ID"))
    for _r in CT.unit_rows(_tree):
        _uid = _r.get("Node ID")
        if (_uid is None or _name_of(_uid) is None
                or _r.get("Node Status") != "ResearchedCompleted"
                or _r.get("Building ID") not in _owned or _uid in _units_all):
            continue
        _ttl = _r.get("Trigger Tech ID")
        _old.append((_stem, _uid))
        if _ttl and _ttl in _techs_all:
            continue
        _new.append((_stem, _uid))

check("the two-channel rule removes exactly GEORGIANS 588",
      set(_old) - set(_new) == {("GEORGIANS", 588)},
      "old=%s new=%s" % (sorted(_old), sorted(_new)))
check("kind-T is then exactly SPARTANS 13 and SICILIANS 588",
      set(_new) == {("SPARTANS", 13), ("SICILIANS", 588)}, "got %s" % sorted(_new))

_sic = trees["SICILIANS"]
check("Sicilians' tree grants 588 and its panel is silent in BOTH channels, so "
      "GAME 2 is clean",
      CT.node_status(_sic, 588, CT.UNIT_USE_TYPES) == "ResearchedCompleted"
      and BP.find_entry(panels[BP.panel_path_for(GAME, "Sicilians")[1]]["obj"],
                        "Sicilians", 588, BP.UNITS_KEY)[1] is None)
_geo = panels[BP.panel_path_for(GAME, "Georgians")[1]]["obj"]
check("Georgians' panel DOES carry the upgrade tech in the Techs channel (this "
      "is why it is NOT a kind-T subject)",
      320 in {e.get("ID") for blk in BP.buildings(_geo, "Georgians")
              if blk.get("ID") == 49 for e in (blk.get(BP.TECHS_KEY) or [])})

print()
print("H  the same check on the kind-P side -- and the LABEL was backwards")
# Round 43 used this check to disqualify subjects and called the survivors "clean".
# `probe_upgrade_gate.py` / `probe_decisive_subjects.py` showed the scoring was
# INVERTED: a kind-P subject whose upgrade tech is ABSENT from the panel's `Techs`
# array is one the panel says you can build while NOT offering the research that
# produces it.  If the engine needs that research, the unit is unreachable WHICHEVER
# file the menu reads -- so "absent" proves nothing.  That is the USELESS case, not
# the clean one.  Only 4 of the 11 subjects supply a COMPLETE path.
_P_CASES = [("JURCHENS", "Jurchens", 77), ("JURCHENS", "Jurchens", 473),
            ("JURCHENS", "Jurchens", 567), ("MUISCA", "Muisca", 359),
            ("HUNS", "Huns", 532), ("WU", "Wu", 474),
            ("BULGARIANS", "Bulgarians", 569), ("ARMENIANS", "Armenians", 569),
            ("POLES", "Poles", 691), ("MAPUCHE", "Mapuche", 528),
            ("SHU", "Shu", 532)]
_complete, _incomplete = [], []
for _stem, _disp, _uid in _P_CASES:
    _tree = trees[_stem]
    _o = panels[BP.panel_path_for(GAME, _disp)[1]]["obj"]
    _row = CT.row_for(_tree, _uid, CT.UNIT_USE_TYPES)
    _ttl = _row.get("Trigger Tech ID") if _row else None
    _tids = {e.get("ID") for blk in BP.buildings(_o, _disp)
             for e in (blk.get(BP.TECHS_KEY) or [])}
    (_complete if (_ttl and _ttl in _tids) else _incomplete).append(
        (_stem, _uid, _ttl))
print("      COMPLETE path -- the panel lists the unit AND its upgrade tech (%d):"
      % len(_complete))
for _s, _u, _t in _complete:
    print("         %-12s unit %-6s tech %s" % (_s, _u, _t))
print("      INCOMPLETE -- the panel lists the unit but NOT its upgrade tech (%d):"
      % len(_incomplete))
for _s, _u, _t in _incomplete:
    print("         %-12s unit %-6s tech %s   <- unusable as a subject"
          % (_s, _u, _t))
check("the previously-recommended JURCHENS 77 is INCOMPLETE (so the earlier card "
      "recommended an unusable subject)",
      ("JURCHENS", 77, 207) in _incomplete,
      "complete=%s incomplete=%s" % (_complete, _incomplete))
check("exactly 4 kind-P subjects supply a COMPLETE path",
      sorted((s, u) for s, u, _t in _complete)
      == [("MAPUCHE", 528), ("MUISCA", 359), ("POLES", 691), ("WU", 474)],
      "complete=%s" % sorted((s, u) for s, u, _t in _complete))
_check_muisca = [t for s, u, t in _complete if s == "MUISCA" and u == 359]
check("the corrected GAME 1 subject (MUISCA 359) is among the complete ones",
      _check_muisca == [429], "got %s" % _check_muisca)

print()
print("ZERO-MOD EXPERIMENT: %s" % ("PINNED"
                                   if not fails else "BROKEN -> %s" % fails))
print("  the shipped files disagree; a game with NO mod installed settles it,")
print("  and no layer/loading confound exists because nothing is layered.")
for name in fails:
    print("  FAILED: %s" % name)
sys.exit(1 if fails else 0)
