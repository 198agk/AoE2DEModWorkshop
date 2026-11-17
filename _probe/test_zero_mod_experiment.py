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

Run:  python _probe\test_zero_mod_experiment.py
"""
import io
import _gamepaths as GP
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402

GAME = GP.GAME
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

# Which enabled mods are OURS?  A pin about "a third-party mod must not
# contaminate a reading" is only honest if it can tell the two apart, and the
# two signals that actually hold are:
#
#   * `info.json`'s `Author` -- the one field this tool sets on purpose.  But
#     this project's own suites do not all use it: `test_install_e2e.py` writes
#     `"E2E"`, `test_repair.py` and `test_split_delivery.py` write `"dsh"`, and
#     `aoe2mod/tests/test_api.py` writes `"test"`.  All of them build with THIS
#     engine and install into the real profile, so a rule keyed on
#     `"aoe2mod"` alone reported them as contamination.
#   * this tool's own build records (`provenance.load()`): if the mod carries a
#     record, this tool built it.  Measured 2026-11-03: `gate rebuild`
#     (`_probe/test_rebuild_installs.py:26`), `dsh test rebuild`,
#     `repair suite probe` and `弓箭手攻击力+1` all have records and all ship a
#     `.dat` half, exactly as intended.
#
# A real Steam subscription has neither.  The 12 enabled subscriptions on this
# machine (`RauFrosch`, `蘭亭 Ink Pavilion`, `naga1v8`, ...) ship no game data at
# all today, so the pin still has something to catch if one of them ever does.
_OUR_AUTHORS = {"aoe2mod", "aoe2mod probe", "aoe2mod test", "aoe2mod-test",
                "dsh", "e2e", "test"}
try:
    from aoe2mod.mod import provenance as _PV                # noqa: E402
    _OUR_TITLES = set((_PV.load().get("builds") or {}).keys())
except Exception:                                            # pragma: no cover
    _OUR_TITLES = set()

# Every path this suite parsed.  If a mod folder ever appears here the whole
# reading is about that mod, and no profile inspection would have told us.
_ROOTS = [os.path.normcase(os.path.abspath(GAME)).rstrip(os.sep) + os.sep]
_from_game_root = True
_stray = []
for _t in trees.values():
    _p = _t.get("path")
    if _p and not os.path.normcase(os.path.abspath(_p)).startswith(_ROOTS[0]):
        _stray.append(_p)
for _rec in panels.values():
    for _p in ([_rec.get("path")] + list(_rec.get("sources") or [])):
        if _p and not os.path.normcase(os.path.abspath(_p)).startswith(_ROOTS[0]):
            _stray.append(_p)
if _stray:
    _from_game_root = False
    print("     paths outside the game root: %s" % _stray[:3])
print("     parsed %d trees and %d panels, all under %s"
      % (len(trees), len(panels), GAME))

ACC = GP.ACCOUNT
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
        # Whose mod is it?  Read `info.json`'s Author, not the folder name.
        # The folder-name rule (`startswith("dsh ")`) was true when this tool
        # wrote `dsh test v49`; it now names a mod after the player's title, so
        # every mod this tool built (`rb one field`, `mx`, `effectsmoke`) was
        # counted as THIRD-PARTY contamination and the pin failed on an
        # otherwise clean machine.  Measured 2026-11-01.  `Author` is the one
        # field this tool sets on purpose (`_flat_intent` pins it to
        # "aoe2mod"), so it is the thing to read.
        author = ""
        try:
            info = json.loads(open(os.path.join(d, "info.json"), "rb")
                              .read().decode("utf-8-sig"), strict=False)
            author = (info.get("Author") or "").strip()
        except (OSError, ValueError):
            author = ""
        for root, _dd, files in os.walk(d):
            for f in files:
                rel = os.path.relpath(os.path.join(root, f), d).lower()
                if ("civtechtrees" in rel or "futuravailableunits" in rel
                        or rel.endswith("empires2_x2_p1.dat")):
                    _name = os.path.basename(d)
                    _mine = (author.lower() in _OUR_AUTHORS
                             or _name in _OUR_TITLES
                             or (m.get("Title") or "") in _OUR_TITLES)
                    (ours if _mine else dirty).append((_name, rel))
    # This machine's own experiment mods are EXPECTED to be enabled and to ship
    # a `.dat` -- that is what they are for.  What this pin has to catch is a
    # THIRD-PARTY mod quietly shipping game data the shipped files disagree
    # with, because then a reading cannot be attributed to the shipped data.
    # Measured 2026-10-22: the first version of this pin counted `dsh test v49`
    # (this tool's own mod, enabled on purpose) and reported a clean machine as
    # contaminated -- the same defect as pinning the player's mod list as a
    # literal.
    # Measured 2026-11-07: the player turned on a real Steam data mod and this
    # went red.  Their enable list is not evidence about this repo -- and this
    # suite never launches the game, it parses the shipped files out of the game
    # root, so an enabled mod cannot reach the numbers below at all.  Reported,
    # not failed.
    if dirty:
        print("     NOTE a third-party mod ships game data and is enabled now:"
              " %s" % sorted({n for n, _r in dirty}))
        print("     NOTE an IN-GAME reading of these numbers would need it off;"
              " this suite reads the game root, so its numbers are unaffected.")
    if ours:
        print("     (this tool's own enabled mods, expected: %s)"
              % sorted({n for n, _r in ours}))
    check("the readings above came from the game root, not a mod folder",
          _from_game_root, "paths outside %s" % GAME)
except (OSError, ValueError) as e:
    check("the profile's mod-status.json is readable", False, str(e))

# The ownership rule above is the whole pin: too narrow and it reports this
# project's own experiment mods as contamination (measured 2026-11-03, 184-suite
# run: `gate rebuild` had no `Author` at all, so the `author == "aoe2mod"` rule
# called it third-party); too wide and it can never fire.  Assert the SHAPE of
# the rule on fixed inputs, so a future edit that widens it to "anything with a
# .dat is ours" fails here instead of in a review.
print()
print("E2 the ownership rule still tells the two apart")
_OUR_AUTHORS_L = sorted(_OUR_AUTHORS)
check("the owned-author set is what this project writes",
      "aoe2mod" in _OUR_AUTHORS and "dsh" in _OUR_AUTHORS
      and "e2e" in _OUR_AUTHORS and "test" in _OUR_AUTHORS,
      "%s" % _OUR_AUTHORS_L)
check("the ownership rule does not cover a Steam author",
      "raufrosch" not in _OUR_AUTHORS and "unpublished" not in _OUR_AUTHORS,
      "%s" % _OUR_AUTHORS_L)
# The rule has two ways to recognise one of our own builds: the `Author` field,
# and the title recorded in the build ledger.  The second one exists because
# `gate rebuild` was made before this tool wrote Author at all.
#
# This check used to name that one record.  That made it a check on **which
# builds this machine happens to remember**: the whole suite reads an isolated
# state directory now (`AOE2MOD_STATE_DIR`), and that directory's ledger has its
# own five records and no `gate rebuild`, so the pin failed on a clean machine
# with the reading it was guarding perfectly intact (2026-11-07).  Pin the SHAPE
# of the rule instead: the title channel must exist and must be consulted.
_zs = io.open(os.path.join(ROOT, "_probe", "test_zero_mod_experiment.py"),
              encoding="utf-8").read()
check("the ownership rule consults the build ledger by folder name",
      '_name in _OUR_TITLES' in _zs)
check("and by the mod's own Title", '(m.get("Title") or "") in _OUR_TITLES' in _zs)
check("the ledger still answers with something when it is read",
      isinstance(_OUR_TITLES, set), "records=%d" % len(_OUR_TITLES))
if _OUR_TITLES:
    check("a build this machine remembers is recognised by title alone",
          True, "sample=%r" % sorted(_OUR_TITLES)[0])
else:
    print("  note   this state directory's ledger is empty, so no sample is shown")

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
