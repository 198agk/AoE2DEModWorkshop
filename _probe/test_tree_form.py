# -*- coding: utf-8 -*-
"""Which tree file does the engine actually parse -- the per-civ template or the aggregate?

Why this file exists
--------------------
The in-game failure of 2026-10-14 (a rewritten
`resources/_common/dat/CivTechTrees/BRITONS.json` did nothing, while the `.dat`
half of the same single mod worked) has two live explanations left after
`_probe/test_civ_unit_gate.py` killed the "the .dat cannot express per-civ
availability" line of attack and `_probe/test_overlay_depth.py` killed "storage
overlays do not recurse into subdirectories" (the chibi mod's emblems sit THREE
levels under `widgetui/` and are visible in the HUD).

The remaining candidates were:

    (a) the engine reads the tree from the BASE path only, so no mod can
        override it;
    (b) the engine reads a DIFFERENT file for the screen the user checked --
        namely the aggregate `civTechTrees.json`, or the build panel cache
        `futuravailableunits.json`.

This probe settles the FORM question from shipped bytes, with no game run.

What was measured (2026-10-14)
------------------------------
1. `AoE2DE_s.exe` contains exactly ONE string that looks like a tree path
   template: `CivTechTrees/%s.json`, once, at `0x3261a18`.
2. That literal sits at the END of its own generated schema cluster.  Walking
   the NUL-separated string runs BACKWARDS from the template gives, in
   alphabetical order, the 17 row-field names that are their own runs:
   `Age ID` / `Building ID` / `Building in new column` /
   `Building upgraded from ID` / `Draw Node Type` / `Help String ID` /
   `Link ID` / `Link Node Type` / `Name String ID` / `Node ID` /
   `Node Status` / `Node Type` / `Picture Index` / `Prerequisite IDs` /
   `Prerequisite Types` / `Trigger Tech ID` / `Use Type`,
   then the file's three top-level keys in order
   `civ_id` -> `civ_techs_buildings` -> `civ_techs_units`,
   and then the template itself as the final run of the cluster.
   (17 of the 18 JSON row keys, not 18: `Name` is a common literal and the
   linker pooled it elsewhere -- it exists twice in the image as a bare run.
   This is why the expected count has to come from the pool, not from the
   JSON key list; see the assertion's comment.)
   AFTER the template come the enum value clusters, `Draw Node Type` first
   (`UnitTech` / `Age` / `Unit` / `UnitUpgrade` / `Research` / `BuildingTech`
   / `BuildingNonTech` / `UniqueResearch` / `UniqueBuilding` / `UniqueTech` /
   `RegionalUnit` / `RegionalBuilding` / `RegionalTech` / `BuildingExtra` /
   `Tech`) and then `Node Status` (`Available` / `NotAvailable` /
   `ResearchedCompleted` / `ResearchRequired`) -- the order the schema declares
   them.  A path template whose own field table ends immediately before it is
   what "this is the file I read" looks like.
3. The aggregate literal `civTechTrees.json` also appears exactly ONCE, at
   `0x32e1678` -- far from the tree schema, alone in its own string run, with no
   path separator and no neighbouring filename, so it is not a path template.
4. The BASE game ships only `resources/_common/dat/CivTechTrees/` (62 per-civ
   files) and NO aggregate anywhere under the base tree.
5. The ONLY aggregate on the whole install lives in the MODE:
   `modes/Pompeii/resources/_common/dat/civTechTrees.json`
   (1,671,526 B, mtime 2025-05-06 -- older than its sibling per-civ files at
   2026-09-24), covering the 17 Rome civs.  The DAT storage point is also the
   ONLY one of the 28 declared storage points carrying
   `use_modes_path_for_mods: True`.

Reading
-------
The aggregate is the MODE form of the tree, not the base form: a content mode
swaps the entire civilization set (Pompeii's 17 Rome civs), and a
`CivTechTrees/<CIV>.json` template cannot enumerate a civ set that belongs to
the mode.  The base game, which has a fixed civ list, uses the per-civ
template.  So `unit.availability` writes to the right file in the right form --
and the 2026-10-14 failure is NOT a "wrong file name / wrong form" bug.

6. The two forms carry the SAME 18 row keys and describe the same rows.  Over
   the 17 Pompeii civs, keys are identical as unions, and for every row present
   in both, the shared-key VALUES are equal (0 differences).  What differs is
   only serialization style: the aggregate spells out default-valued keys
   (`"Link ID": -1`, `"Prerequisite IDs": [0,0,0,0,0]`) that the per-civ files
   omit (2125 rows where the aggregate row is a strict key superset, 0 the
   other way).  That is a writer's choice, not a schema difference -- which is
   why reading either form fine but dumping the WRONG key names (see
   `aoe2mod/game/civtechtrees.py`) silently produces a file the engine cannot
   parse.

PROVEN here     : the engine names one tree template, `CivTechTrees/%s.json`,
                  and it is the per-civ form whose own generated field schema
                  ends immediately before it; the aggregate is a mode-only
                  artifact; the two forms are semantically identical.
NOT PROVEN here : nothing -- this question has since been measured.  Form and
                  file name were already cleared; the two survivors it listed
                  are both now dead.  SCHEDULING is out (`dsh test v17` was
                  installed with the game closed and selected before the match
                  started, and it took effect).  SCREEN is out too, and in the
                  direction this file guessed: `futuravailableunits.json` is
                  excluded in BOTH directions by plain-game runs (Sicilians
                  panel-silent-but-offered, Poles panel-listed-but-not-offered).
                  The real reason a tree overlay moves nothing is that the build
                  menu does not read the tree at all (`dsh test v15`); it reads
                  `.dat` `type 2` Enable/Disable Unit commands, last-to-fire
                  wins (`dsh test v7` / `v17`).  The tree IS read -- by the
                  tech-tree PREVIEW screen.
"""
import io
import _gamepaths as GP
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

GAME = GP.GAME
EXE = os.path.join(GAME, "AoE2DE_s.exe")
DAT_DIR = os.path.join(GAME, "resources", "_common", "dat")
TREE_DIR = os.path.join(DAT_DIR, "CivTechTrees")
P0 = os.path.join(GAME, "modes", "Pompeii")
P0_DAT = os.path.join(P0, "resources", "_common", "dat")

ROW_KEYS = ("Age ID", "Building ID", "Building in new column",
            "Building upgraded from ID", "Draw Node Type", "Help String ID",
            "Link ID", "Link Node Type", "Name", "Name String ID", "Node ID",
            "Node Status", "Node Type", "Picture Index", "Prerequisite IDs",
            "Prerequisite Types", "Trigger Tech ID", "Use Type")

FAILURES = []


def check(cond, label):
    print("[%s] %s" % ("PASS" if cond else "FAIL", label))
    if not cond:
        FAILURES.append(label)


def rowkeys(obj):
    s = set()
    for k in ("civ_techs_units", "civ_techs_buildings"):
        for r in obj.get(k, []):
            s.update(r)
    return s


def rk(r):
    return (r.get("Node ID"), r.get("Use Type"))


def ascii_span(buf, idx):
    """The contiguous printable-ASCII run containing buf[idx].

    A raw 160-byte window around a match catches binary neighbours and then
    "does this contain a path separator" answers about garbage, not about the
    string.  The engine's string pool is NUL-separated, so the run is the right
    unit of evidence.
    """
    def printable(b):
        return 0x20 <= b < 0x7F
    if not printable(buf[idx]):
        return b""
    lo = idx
    while lo > 0 and printable(buf[lo - 1]):
        lo -= 1
    hi = idx
    while hi < len(buf) and printable(buf[hi]):
        hi += 1
    return buf[lo:hi]


def runs_before(buf, idx, window):
    """NUL-separated printable runs in [idx-window, idx), in FORWARD order.

    The engine's string pool is NUL-separated, so the RUN -- not a fixed byte
    window -- is the unit that carries meaning.  A window straddles runs and
    makes "does this contain X" answer about neighbours; the ordered run list is
    what a serializer's field schema actually looks like in a binary.
    """
    def printable(b):
        return 0x20 <= b < 0x7F
    lo = max(0, idx - window)
    out = []
    i = lo
    while i < idx:
        if printable(buf[i]):
            s = i
            while i < idx and printable(buf[i]):
                i += 1
            out.append(buf[s:i])
        else:
            i += 1
    return out


with io.open(EXE, "rb") as fh:
    exe = fh.read()

# ---------------------------------------------------------------------------
print("=" * 74)
print("A -- the engine names exactly one tree path template, and it is per-civ")
print("=" * 74)
tpl = b"CivTechTrees/%s.json"
n_tpl = exe.count(tpl)
n_agg = exe.count(b"civTechTrees.json")
print("    'CivTechTrees/%%s.json' occurrences : %d  @0x%x" % (n_tpl, exe.find(tpl)))
print("    'civTechTrees.json'    occurrences : %d  @0x%x" % (n_agg, exe.find(b"civTechTrees.json")))
check(n_tpl == 1, "the per-civ path template occurs exactly once")
check(n_agg == 1, "the aggregate literal occurs exactly once")

# the schema neighbourhood of the template
j = exe.find(tpl)
own_run = ascii_span(exe, j)
print("    the template's own string run : %r" % own_run)
check(own_run == tpl, "the template occupies a run by itself -- it is a literal, not a fragment")

# the run immediately before it
before = runs_before(exe, j, 700)
print("    runs before it : %d over %d bytes" % (len(before), 700))
print("    the three the engine orders first : %r" % (before[-3:],))
check(before[-1] == b"civ_techs_units",
      "civ_techs_units is the run NUL-adjacent to the template")
check(before[-2] == b"civ_techs_buildings" and before[-3] == b"civ_id",
      "civ_techs_buildings and civ_id precede it -- the file's top-level key order")

# all row fields appear as their OWN runs in that cluster -- 17 of the 18, and
# the missing one is the point: a common literal like "Name" is pooled once
# elsewhere in the image, so counting runs is the right test only if the
# expected count is derived from the pool, not from the JSON key list.
rows_in = [k for k in ROW_KEYS if k.encode("ascii") in before]
missing = [k for k in ROW_KEYS if k not in rows_in]
print("    row-field names as their own runs : %d of %d" % (len(rows_in), len(ROW_KEYS)))
print("    the one that is pooled elsewhere  : %r" % missing)
check(len(rows_in) == 17 and missing == ["Name"],
      "17 row fields are their own runs and only 'Name' is pooled elsewhere")
check(exe.count(b"\x00Name\x00") >= 1,
      "'Name' does exist as a run somewhere in the image -- it is deduplicated, not absent")
# and they are ordered alphabetically, the way a generated field table is
idx = {k: before.index(k.encode("ascii")) for k in ROW_KEYS if k.encode("ascii") in before}
ordered = sorted(idx, key=lambda k: idx[k])
print("    their order : %s" % ordered[:6])
check(ordered == sorted(ordered),
      "the row fields sit in alphabetical order -- a generated schema, not prose")

# the enums follow the template as their own run clusters, in schema order
after = runs_before(exe, j + 1500, 1500)
print("    runs after it : %d" % len(after))
check(len(after) >= 8, "enum run clusters follow the template")
for v in ("UnitTech", "UnitUpgrade", "BuildingTech", "UniqueResearch"):
    check(v.encode("ascii") in after,
          "the Draw Node Type value %s is one of the runs after the template" % v)
for v in ("Available", "NotAvailable", "ResearchedCompleted", "ResearchRequired"):
    check(v.encode("ascii") in after,
          "the Node Status value %s is one of the runs after the template" % v)
check(after.index(b"UnitTech") < after.index(b"Available"),
      "the Draw Node Type enum precedes the Node Status enum, as the schema orders them")

# the aggregate's neighbourhood is unrelated, and has no path separator
k = exe.find(b"civTechTrees.json")
agg_run = ascii_span(exe, k)
print("    aggregate string run : %r" % agg_run)
print("    aggregate neighbours : %r" % ascii_span(exe, k - 1))
print("    aggregate follower   : %r" % ascii_span(exe, k + len(b"civTechTrees.json")))
check(b"\\" not in agg_run and b"/" not in agg_run,
      "the aggregate literal carries no path separator in its own string run")
# and it is NOT adjacent to the tree schema / path template the way the per-civ one is
check(tpl not in agg_run and b"CivTechTrees" not in agg_run,
      "the aggregate literal is not part of the per-civ path template's string run")

# ---------------------------------------------------------------------------
print()
print("=" * 74)
print("B -- the base game ships the per-civ form and NO aggregate")
print("=" * 74)
base_files = sorted(f for f in os.listdir(TREE_DIR) if f.endswith(".json"))
print("    base CivTechTrees/ files : %d" % len(base_files))
aggregates = []
for dp, _dn, fn in os.walk(GAME):
    for f in fn:
        if f.lower() == "civtechtrees.json":
            aggregates.append(os.path.join(dp, f))
print("    every civTechTrees.json on the install :")
for a in aggregates:
    print("        %s" % a)
check(len(base_files) >= 60, "the base tree is a directory of per-civ files")
check(all(os.path.join(GAME, "modes") in a for a in aggregates),
      "every aggregate lives under modes/ -- the base game ships none")

# ---------------------------------------------------------------------------
print()
print("=" * 74)
print("C -- the DAT storage point is the only one that is mode-aware")
print("=" * 74)
reg = json.load(io.open(os.path.join(P0, "Pompeii.json"), encoding="utf-8-sig"))
pts = [e for e in reg["storage_point_list"] if isinstance(e, dict)]
flagged = [e for e in pts if e.get("use_modes_path_for_mods")]
print("    storage points declared              : %d" % len(pts))
print("    carrying use_modes_path_for_mods     : %d" % len(flagged))
for e in flagged:
    print("        %r" % (e,))
check(len(flagged) == 1, "exactly one storage point is declared mode-aware")
check(flagged[0].get("type") == "DAT", "and it is DAT")
check(flagged[0].get("path", "").replace("\\", "/") == "resources/_common/dat",
      "with the path that holds both the tree directory and the aggregate")

# ---------------------------------------------------------------------------
print()
print("=" * 74)
print("D -- the two forms describe the SAME rows (so form is not the bug)")
print("=" * 74)
agg = json.load(io.open(os.path.join(P0_DAT, "civTechTrees.json"),
                        encoding="utf-8-sig"))["civs"]
by = {c["civ_id"]: c for c in agg}
pdir = os.path.join(P0_DAT, "CivTechTrees")
per_file = sorted(f[:-5] for f in os.listdir(pdir) if f.endswith(".json"))
print("    aggregate entries : %d -> %s" % (len(by), sorted(by)))
print("    per-civ files     : %d" % len(per_file))
check(set(by) == set(per_file), "the aggregate covers exactly the per-civ files")

pairs = 0
agg_super = per_super = 0
valdiff = 0
wk_agg = set()
wk_per = set()
for cid in sorted(by):
    p = json.load(io.open(os.path.join(pdir, cid + ".json"), encoding="utf-8-sig"))
    c = by[cid]
    wk_per |= rowkeys(p)
    for key in ("civ_techs_units", "civ_techs_buildings"):
        A = {rk(r): r for r in c[key]}
        B = {rk(r): r for r in p[key]}
        wk_agg |= {kk for r in c[key] for kk in r}
        for kk in set(A) & set(B):
            pairs += 1
            ka, kb = set(A[kk]), set(B[kk])
            if kb < ka:
                agg_super += 1
            elif ka < kb:
                per_super += 1
            if any(A[kk][x] != B[kk][x] for x in ka & kb):
                valdiff += 1
print("    rows present in both forms           : %d" % pairs)
print("    aggregate row has MORE keys          : %d" % agg_super)
print("    per-civ row has MORE keys            : %d" % per_super)
print("    shared-key VALUE differences         : %d" % valdiff)
print("    key union, aggregate : %d" % len(wk_agg))
print("    key union, per-civ   : %d" % len(wk_per))
check(pairs > 2000, "the two forms share thousands of rows")
check(valdiff == 0, "no shared key ever disagrees in value -- the forms are semantically identical")
check(agg_super > 0 and per_super == 0,
      "the aggregate merely spells out default-valued keys the per-civ files omit")
check(wk_agg == wk_per and wk_agg == set(ROW_KEYS),
      "both forms use exactly the 18 documented row keys")

# the base form uses the same row keys as the mode's per-civ form
bmain = json.load(io.open(os.path.join(TREE_DIR, "BRITONS.json"), encoding="utf-8-sig"))
check(rowkeys(bmain) == wk_per,
      "the base per-civ form uses the same 18 row keys as the mode's per-civ form")

print()
if FAILURES:
    print("FAILURES: %d" % len(FAILURES))
    for f in FAILURES:
        print("  - %s" % f)
    sys.exit(1)
print("TREE FORM: the engine parses the per-civ template `CivTechTrees/%s.json`;")
print("the aggregate `civTechTrees.json` is a MODE-only artifact; the two forms")
print("carry identical semantics, so `unit.availability` writes the right file in")
print("the right form and the 2026-10-14 failure is not a naming or shape bug.")
print("ANSWERED SINCE (2026-10-19): `dsh test v15` shipped exactly these files in")
print("exactly this form, over a byte-identical `.dat`, with the engine log")
print("confirming the mod loaded -- and the build menu moved in NEITHER direction.")
print("So the form and the file name were never the problem, and the tree is not")
print("what the build menu reads (the tech-tree PREVIEW does read it).  What gates")
print("the menu is a `.dat` `type 2` command on a tech the civ owns, last one to")
print("fire wins (v7 grant / v17 revoke).  See _交接说明.md sections 2, 2b-2d.")
