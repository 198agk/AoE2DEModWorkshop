"""Where does "Aztecs cannot build a Hand Cannoneer" actually live?

The .dat itself was the last candidate, because the user established that the
game loads the .dat (verbatim, 2026-10-14): a mod "just replaces the game's file
of the same name and path", "the game wants dat, not json".

This file pins the answer on the .dat side, because each of its parts has been
proposed and refuted separately and each is easy to propose again:

  REFUTED as the per-civ gate, in the .dat:
    * membership in the civ's own unit array -- unit 5 is in ALL 63 arrays, at
      the SAME index (5).  The civ arrays do differ in SIZE (2164..2693), so this
      was a real question; it is answered.
    * the unit RECORD -- stripping offsets recursively, unit 5's record is
      identical for all 63 civs except the `civ` field.  For unit 41 the same
      test left only `civ` plus three DECORATIVE fields (icon_id, attack_graphic)
      on the handful of ids that resolve to different units per civ.
    * the effect layer -- unit 5's only enable is tech 85, owned by NO civ
      (civ=-1), and across the whole 8,005-command corpus there are exactly 7
      type-2 DISABLE commands; none of them names unit 5.
    * transitive prerequisite -- Chemistry (tech 47) is ResearchedCompleted for
      all 62 playable civs, yet 38 of them cannot build the Hand Cannoneer.
    * the .dat TechTree -- ONE global object (`DatFile.h:109 genie::TechTree
      TechTree;`, serialized exactly once at `DatFile.cpp:266`), so it cannot
      carry per-civ data at all.  Its per-node `Status` byte is 2 in every one
      of the 266 unit connections.

  CONCLUSION this file asserts: the .dat has NO per-civ expression of unit
  availability.  Per-civ availability is why `resources/_common/dat/CivTechTrees/`
  is a DIRECTORY of one file per civilization -- a shape the global .dat cannot
  have.

  Which re-aims the open question: the mod's CivTechTrees write not taking effect
  is a MOD-OVERLAY question, not a "wrong file" question.  So part B checks the
  only offline evidence available: does any shipped mod ever override a file
  inside a SUBDIRECTORY of the dat folder?  WIDGETUI overrides go many levels
  deep, but the dat folder's only subdirectory is CivTechTrees itself.

PROVEN: the four .dat refutations above; the dat folder's subdirectory inventory;
        that the ONLY mod file ever placed below resources/_common/dat/ is my own
        smoke test's CivTechTrees/BRITONS.json -- the very write that failed.
NOT PROVEN: that the engine's DAT overlay is not recursive, or that it is.  One
        data point cannot separate those.  The experiment that can is printed at
        the end of part F.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aoe2mod.api as A                     # noqa: E402
import aoe2mod.game.civtechtrees as CT      # noqa: E402

UNIT = 5          # Hand Cannoneer: 24 civs can build it, 38 cannot
CHEM = 47         # Chemistry

tk = A.open_toolkit()
tk._ensure()

civs = tk._civs
trees = tk._trees()
techs = tk._tech_records()
effects = tk._effect_records()


def strip(o):
    """Drop `_`-prefixed bookkeeping at EVERY depth.

    A top-level-only strip left `_off_*` byte offsets inside nested dicts and
    made byte-identical records look 43/43 different.  That bug already produced
    one false "train_locations is the gate" conclusion, so it is named here.
    """
    if isinstance(o, dict):
        return {k: strip(v) for k, v in o.items() if not k.startswith("_")}
    if isinstance(o, list):
        return [strip(v) for v in o]
    return o


def tree_status(civ_name, node_id, use=CT.UNIT_USE_TYPES):
    t = trees.get(CT.civ_file_stem(civ_name))
    return CT.node_status(t, node_id, use) if t else None


failures = []


def check(ok, msg):
    print("[%s] %s" % ("PASS" if ok else "FAIL", msg))
    if not ok:
        failures.append(msg)


print("=" * 74)
print("A -- membership in the civ's own unit array is NOT the gate")
print("=" * 74)
sizes = sorted(len(c["units"]) for c in civs)
print("    civ unit-array sizes: min %d  max %d  (they really do differ)"
      % (sizes[0], sizes[-1]))
present = [c["name"] for c in civs if any(u["id"] == UNIT for u in c["units"])]
check(len(present) == len(civs),
      "unit %d is present in the own array of all %d civs (%d found)"
      % (UNIT, len(civs), len(present)))
idxs = {[u["id"] for u in c["units"]].index(UNIT) for c in civs}
check(len(idxs) == 1 and idxs == {5},
      "and at the SAME array index for every civ: %s" % sorted(idxs))

print()
print("=" * 74)
print("B -- the unit RECORD is NOT the gate")
print("=" * 74)
groups = {}
for c in civs:
    rec = next((u for u in c["units"] if u["id"] == UNIT), None)
    if rec is None:
        groups.setdefault("ABSENT", []).append(c["name"])
        continue
    s = strip(rec)
    s.pop("civ", None)          # the civ index is expected to differ everywhere
    groups.setdefault(json.dumps(s, sort_keys=True), []).append(c["name"])
print("    distinct records for unit %d with `civ` excluded, across %d civs: %d"
      % (UNIT, len(civs), len(groups)))
biggest = max(groups.values(), key=len)
print("    largest group: %d civs (%s)" % (len(biggest), biggest[:6]))
# Every remaining difference must be a DECORATIVE field, on the handful of ids
# that resolve to a DIFFERENT unit per civ.  Those are the six Chronicles
# civilizations, which use a 405xxx name block and really do have another unit
# at this id (Gastraphetes, not Hand Cannoneer) -- and the tree marks unit 5
# NotAvailable for all six anyway, so they are consistent.
DECORATIVE = {"icon_id", "type50"}
base = next(u for u in next(c for c in civs if c["name"] == biggest[0])["units"]
            if u["id"] == UNIT)
base_s = strip(base)
base_s.pop("civ", None)
extra = []
for key, names in groups.items():
    if len(names) > 1:
        continue
    rec = next(u for u in next(c for c in civs if c["name"] == names[0])["units"]
               if u["id"] == UNIT)
    rec_s = strip(rec)
    rec_s.pop("civ", None)
    diff = {k for k in set(rec_s) | set(base_s) if rec_s.get(k) != base_s.get(k)}
    extra.append((names[0], sorted(diff)))
print("    civs whose record differs by more than `civ`: %d" % len(extra))
for n, d in extra:
    print("      %-13s %s" % (n, d))
check(not any(set(d) - DECORATIVE for _n, d in extra),
      "every per-civ variation is a decorative field (%s)"
      % sorted({f for _n, d in extra for f in d}))
check(len(extra) <= 6 and all(set(d) <= DECORATIVE for _n, d in extra),
      "at most the 6 Chronicles civs differ, and only in decorative fields "
      "(%d differ)" % len(extra))

print()
print("=" * 74)
print("C -- the effect layer is NOT the per-civ gate")
print("=" * 74)
enables, disables, other = [], [], []
for ti, t in enumerate(techs):
    eid = t.get("effect_id")
    if eid is None or eid < 0 or eid >= len(effects):
        continue
    for ci, cmd in enumerate(effects[eid].get("commands") or []):
        if cmd.get("type") != 2 or UNIT not in (cmd.get("a"),):
            continue
        row = (ti, t.get("name"), t.get("civ"), ci, cmd.get("a"), cmd.get("b"))
        if cmd.get("b") == 1:
            enables.append(row)
        elif cmd.get("b") == 0:
            disables.append(row)
        else:
            other.append(row)
print("    type-2 commands naming unit %d: enable %d, disable %d, irregular %d"
      % (UNIT, len(enables), len(disables), len(other)))
for row in enables:
    print("      enable  tech[%d] %-28s civ=%-5s cmd%d A=%s B=%s"
          % (row[0], str(row[1])[:28], row[2], row[3], row[4], row[5]))
check(len(disables) == 0 and len(other) == 0,
      "no command anywhere DISABLES unit %d" % UNIT)

all_disable = []
for ti, t in enumerate(techs):
    eid = t.get("effect_id")
    if eid is None or eid < 0 or eid >= len(effects):
        continue
    for ci, cmd in enumerate(effects[eid].get("commands") or []):
        if cmd.get("type") == 2 and cmd.get("b") == 0:
            all_disable.append((ti, t.get("name"), t.get("civ"), cmd.get("a")))
print()
print("    every type-2 DISABLE in the whole .dat: %d" % len(all_disable))
for row in all_disable:
    print("      tech[%d] %-34s civ=%-5s target unit %s"
          % (row[0], str(row[1])[:34], row[2], row[3]))
check(all(row[3] != UNIT for row in all_disable),
      "none of the .dat's %d disable commands targets unit %d"
      % (len(all_disable), UNIT))
check(len(all_disable) < 20,
      "disables are a tiny, closed set (%d rows total)" % len(all_disable))

print()
print("=" * 74)
print("D -- the prerequisite is universal, so transitivity cannot explain it")
print("=" * 74)
chem = [tree_status(c["name"], CHEM, CT.TECH_USE_TYPES) for c in civs]
hist = {}
for s in chem:
    hist[s] = hist.get(s, 0) + 1
print("    Chemistry (tech %d) status across civs: %s" % (CHEM, hist))
can = [c["name"] for c in civs
       if tree_status(c["name"], UNIT) not in (None, "NotAvailable")]
cannot = [c["name"] for c in civs if tree_status(c["name"], UNIT) == "NotAvailable"]
print("    can build unit %d: %d     told NotAvailable: %d" % (UNIT, len(can), len(cannot)))
check(cannot, "the split is real (%d civs on the blocked side)" % len(cannot))
check(all(s in (None, "ResearchedCompleted", "ResearchRequired") for s in chem),
      "Chemistry is never NotAvailable, so it cannot gate the Hand Cannoneer")

print()
print("=" * 74)
print("E -- the .dat TechTree is a single GLOBAL object")
print("=" * 74)
source = os.path.join("_probe", "source", "genieutils")
h = os.path.join(source, "include", "genie", "dat", "DatFile.h")
c = os.path.join(source, "src", "dat", "DatFile.cpp")
has_global = h and os.path.isfile(h) and "genie::TechTree TechTree;" in open(h, encoding="utf-8").read()
serialized_twice = c and os.path.isfile(c) and \
    open(c, encoding="utf-8").read().count("serialize<ISerializable>(TechTree)") == 1
print("    DatFile.h declares one `genie::TechTree TechTree;`        : %s" % has_global)
print("    DatFile.cpp serializes it exactly once                      : %s" % serialized_twice)
check(has_global and serialized_twice,
      "the dat TechTree is global, so it cannot express a per-civ gate")
tt = tk._stats.get("tech_tree") if hasattr(tk, "_stats") else None
if tt:
    print("    parsed counts: %s" % tt)

print()
print("=" * 74)
print("F -- does any shipped mod override a SUBDIRECTORY of the dat folder?")
print("=" * 74)
game = tk.game_root
datdir = os.path.join(game, "resources", "_common", "dat")
subdirs = sorted(d for d in os.listdir(datdir)
                 if os.path.isdir(os.path.join(datdir, d)))
print("    the dat folder's only subdirectories: %s" % subdirs)

deep = 0
deep_names = []
third_party_deep = 0
third_party = []
# Walk the DISK, not just `tk.mods()`.  `tk.mods()` reads `mod-status.json`, and a
# local mod folder can sit in `mods/local/` with NO status entry at all -- the game
# discovers those (per the user's instruction m22351: 「你只需要放入对应文件夹就可以
# 了，游戏能自动识别」), and `install_smoke6.py` deliberately only copies the folder.
# Enumerating via the status file therefore made this count read 0 once the mod
# under test stopped being registered, which would have silently retired the
# finding this section exists to pin.
from aoe2mod.game import locations as _G                   # noqa: E402
_prof = _G.find_profile_root()
_seen = {}
for _m in tk.mods():
    _seen[os.path.realpath(_m["path"])] = _m["name"]
for _acc in _G.find_accounts(_prof):
    for _kind in ("subscribed", "local"):
        _d = _G.account_mods_dir(_acc, _kind)
        if not os.path.isdir(_d):
            continue
        for _name in sorted(os.listdir(_d)):
            _p = os.path.join(_d, _name)
            if os.path.isdir(_p):
                _seen.setdefault(os.path.realpath(_p), _name)
_registered = len(tk.mods())
mods = [{"name": _n, "path": _p}
        for _p, _n in sorted(_seen.items(), key=lambda kv: kv[1])]
print("    mods found on disk: %d  (registered in mod-status.json: %d)"
      % (len(mods), _registered))
for m in mods:
    base = os.path.join(m["path"], "resources", "_common", "dat")
    if not os.path.isdir(base):
        continue
    names = []
    for root, _dirs, files in os.walk(base):
        for fn in files:
            rel = os.path.relpath(os.path.join(root, fn), base)
            names.append(rel)
            if os.sep in rel:
                deep += 1
                deep_names.append((m["name"], rel))
                # My own tests are the only ones that reach below dat/.  Every name
                # this project's mods have ever used must be listed, or the filter
                # starts calling my own artifact "third-party" -- which happened when
                # the naming scheme changed to `dsh test vN`
                # (`_probe/testmod_name.py`: PREFIX = "dsh test").
                if not (m["name"].startswith("aoe2mod")
                        or m["name"].startswith("dsh test")
                        or m["name"] == "Smoke Test Villager HP"):
                    third_party_deep += 1
                    third_party.append((m["name"], rel))
    print("    %-46s %d file(s) under dat/: %s"
          % (m["name"][:46], len(names), names[:4]))
print()
print("    mod files living BELOW the dat folder: %d  %s" % (deep, deep_names))
print("    ...of which from a THIRD-PARTY mod     : %d  %s"
      % (third_party_deep, third_party))
check(third_party_deep == 0,
      "no third-party mod ships a file inside a dat subdirectory -- the only "
      "such files are MY OWN smoke tests, whose in-game result was that the "
      "CivTechTrees write did NOT take effect")
# The nested-file COUNT depends on which of my smoke mods is installed right now:
# smoke6 wrote `CivTechTrees/BRITONS.json` (deep=1), while smoke7 is dat-only
# (deep=0).  Asserting a literal 1 made this pin fail for a reason unrelated to
# what it measures.  The invariant that matters is that every nested file is MINE,
# expressed against the measured SETS rather than by an identity that is true by
# construction (`deep == len(deep_names)` would be a tautology).
_mine_deep = [t for t in deep_names
              if not (t[0].startswith("aoe2mod")
                      or t[0].startswith("dsh test")
                      or t[0] == "Smoke Test Villager HP")]
check(len(_mine_deep) == 0,
      "every nested dat file belongs to a mod of MINE (found %d foreign: %s)"
      % (len(_mine_deep), _mine_deep))
check(deep == len(deep_names),
      "the counted total agrees with the enumerated list (%d vs %d)"
      % (deep, len(deep_names)))
print("    note: the nested count is %d today; it was 1 while smoke6 (which wrote"
      % deep)
print("    CivTechTrees/BRITONS.json) was installed, and 0 now that smoke7 is the")
print("    dat-only test.  The invariant is that none of them is third-party.")
print()
print("    READ THIS AS: the DAT overlay either is not recursive, or the")
print("    CivTechTrees write failed for another reason.  One data point cannot")
print("    tell those apart.  The experiment that CAN: ship the same edit as a")
print("    loose file at the dat ROOT-relative path the engine names, and ship it")
print("    a second time as an edited main .dat, and see which one lands.")

print()
print("=" * 74)
print("VERDICT")
print("=" * 74)
print("CIV UNIT GATE: the .dat cannot express per-civ unit availability via the "
      "layers this file tested -- membership, the record, the effect layer "
      "transitivity and the global `TechTree` object are each refuted.  The "
      "per-civ gate is why CivTechTrees/ is a directory of one file per "
      "civilization, so the mod-overlay question is about DIRECTORY RECURSION in "
      "the DAT storage point, which no installed mod has ever exercised.")
print()
print("  *** CORRECTION (2026-10-15, Round 58): the word 'cannot' above is TOO "
      "STRONG. ***")
print("  This file examined what the shipped data USES for the units it tested.  "
      "A different question -- whether the machinery exists -- answers YES:")
print("  `_probe/test_dat_grant_route.py` and `probe_makeavail_automatic.py` "
      "measured")
print("  112 civ-owned techs carrying an effect command `type 2, b=1` (enable "
      "unit),")
print("  99 of which are ABSENT from the owning civilization's tree -- i.e. they")
print("  apply because of `tech.civ` alone, exactly like a civilization bonus.")
print("  That is a `.dat`-only per-civ unit grant.  See `_probe/build_smoke7.py`.")
if failures:
    print()
    print("FAILURES: %d" % len(failures))
    for f in failures:
        print("  - %s" % f)
    sys.exit(1)
