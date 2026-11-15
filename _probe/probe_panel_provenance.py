# -*- coding: utf-8 -*-
"""Is futuravailableunits.json a BUILD-TIME artifact or a runtime cache?

Why this matters
----------------
The 2026-10-14 in-game test edited CivTechTrees/BRITONS.json and the Barracks
menu did not change.  If the menu is fed by `futuravailableunits.json`, and that
file is a build-time artifact the game never regenerates, then the tree edit
SHOULD have changed nothing -- the observation would be fully explained without
any overlay bug, and the decisive experiment becomes the Smoke2 panel edit
(which has never actually run clean, because the game disabled that mod).

How to tell build-time from runtime without running the game
-----------------------------------------------------------
A runtime cache would be rewritten at the user's first launch, so it would
differ between two installs of the same build -- that is the test that survives.

mtime ordering does NOT: 2026-11-12 23:22:44, Steam's validation re-delivered
futuravailableunits.json with byte-identical content (sha 1abbcd6c4c5a1fd5) and
a fresh mtime, so the panel became "newer than the executable" (itself restamped
at 23:19:46) without a byte of data moving.  Assertions below compare CONTENT
against the archived vanilla copy; mtimes are printed as observations only.

Documented facts to check against:
  * `CivTechTrees/*.json`     mtime 2026-09-24  (shipped content)
  * the .dat                  mtime 2026-09-23
  * `futuravailableunits.json` -- unknown, that is what we measure
  * `modes/Pompeii/.../civTechTrees.json` mtime 2025-05-06 (older than its own
     per-civ siblings, which already suggests "generated once, then the
     per-civ form became canonical").

Also compares the panel file against what the tree says, per civ: if the panel
were regenerated from the tree at runtime they would agree everywhere.  It
disagrees on ~19 of ~3,683 comparable pairs (the exact count depends on how many
civs both files cover -- the earlier "18" was over the 56 civs the panel file
covers; this probe walks every tree that has a panel key).  Either way it is not
a live projection.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os
import sys
import datetime

sys.path.insert(0, _HERE_PATH(".."))

import aoe2mod.api as A                       # noqa: E402
from aoe2mod.game import buildpanel as BP     # noqa: E402
from aoe2mod.game import civtechtrees as CT   # noqa: E402

GAME = A.open_toolkit().game_root

def stamp(path):
    if not os.path.isfile(path):
        return "MISSING"
    st = os.stat(path)
    return "%s  (%d B)" % (
        datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        st.st_size)

print("game root : %s" % GAME)
print()
print("--- shipped content mtimes ---------------------------------------")

interesting = [
    ("the .dat", os.path.join(GAME, "resources", "_common", "dat",
                              "empires2_x2_p1.dat")),
    ("the exe", os.path.join(GAME, "AoE2DE_s.exe")),
]

# the panel file(s)
for p in BP.panel_paths(GAME):
    if p:
        interesting.append((os.path.basename(p), p))

# a few per-civ tree files, earliest and latest
tdir = CT.trees_dir(GAME)
tfiles = sorted(os.path.join(tdir, f) for f in os.listdir(tdir)
                if f.lower().endswith(".json"))
print("per-civ tree files: %d" % len(tfiles))
by_mtime = sorted(tfiles, key=lambda p: os.stat(p).st_mtime)
interesting.append(("tree EARLIEST (%s)" % os.path.basename(by_mtime[0]),
                    by_mtime[0]))
interesting.append(("tree LATEST   (%s)" % os.path.basename(by_mtime[-1]),
                    by_mtime[-1]))

# other dat-layer JSONs, for a baseline of "when is this folder written"
ddir = os.path.join(GAME, "resources", "_common", "dat")
for name in ("civilizations.json", "linkedTechs.json", "maps.json",
             "hotkeys.json", "sounds.json", "objreplacement.json"):
    interesting.append((name, os.path.join(ddir, name)))

# the Pompeii aggregate, for contrast
interesting.append((
    "Pompeii civTechTrees.json",
    os.path.join(GAME, "modes", "Pompeii", "resources", "_common", "dat",
                 "civTechTrees.json")))

for label, path in interesting:
    print("    %-34s %s" % (label, stamp(path)))

print()
print("--- the panel file's own mtime spread across the tree -------------")
pm = None
for p in BP.panel_paths(GAME):
    if p:
        pm = os.stat(p).st_mtime
        break
if pm is None:
    print("    no panel file on disk")
else:
    newer = [os.path.basename(p) for p in tfiles if os.stat(p).st_mtime > pm]
    same_day = [os.path.basename(p) for p in tfiles
                if abs(os.stat(p).st_mtime - pm) < 86400]
    print("    panel mtime                : %s"
          % datetime.datetime.fromtimestamp(pm).strftime("%Y-%m-%d %H:%M:%S"))
    print("    tree files NEWER than it   : %d" % len(newer))
    print("    tree files within a day    : %d" % len(same_day))

print()
print("--- has the game RUN since the panel was written? -----------------")
# The decisive form of the argument is not "older than the exe" -- it is that
# the game has been launched since, and the panel still carries its unpack
# mtime.  A runtime cache would have been rewritten at the first launch.
LOGS = r"C:\Users\26913\Games\Age of Empires 2 DE\logs"
log_dirs = []
if os.path.isdir(LOGS):
    log_dirs = sorted(d for d in os.listdir(LOGS)
                      if os.path.isdir(os.path.join(LOGS, d)))
log_mtimes = [(d, os.stat(os.path.join(LOGS, d)).st_mtime) for d in log_dirs]
after = [(d, m) for d, m in log_mtimes if m > pm]
print("    log sessions on disk       : %d" % len(log_dirs))
print("    sessions AFTER the panel   : %d" % len(after))
for d, m in after[-4:]:
    print("        %s  %s" % (d, datetime.datetime.fromtimestamp(m)
                             .strftime("%Y-%m-%d %H:%M:%S")))
print("    panel mtime still          : %s"
      % datetime.datetime.fromtimestamp(pm).strftime("%Y-%m-%d %H:%M:%S"))
print("    -> %s" % ("the game ran and did NOT rewrite the panel"
                     if after else
                     "no launch recorded after the panel; argument unavailable"))

print()
print("--- does the panel agree with the tree? --------------------------")
tk = A.open_toolkit()
tk._ensure()
trees = tk._trees()
panels = BP.load_all(GAME)

agree = disagree = 0
samples = []
for civ, tree in sorted(trees.items()):
    pk = BP.civ_key_for(panels, civ)
    if pk is None:
        continue
    wrapper = panels[pk]
    whole = wrapper["obj"] if isinstance(wrapper, dict) and "obj" in wrapper \
        else wrapper
    sub = whole.get(pk, whole) if isinstance(whole, dict) else whole
    if not isinstance(sub, dict) or "Buildings" not in sub:
        continue
    listed = {}
    for b in sub["Buildings"]:
        listed.setdefault(b.get("ID"), set()).update(
            u.get("ID") for u in (b.get("Units") or []))
    for row in CT.unit_rows(tree):
        node = row.get("Node ID")
        st = row.get("Node Status")
        bld = row.get("Building ID")
        if bld not in listed:
            continue
        present = node in listed[bld]
        can = st != "NotAvailable"
        if present == can:
            agree += 1
        else:
            disagree += 1
            if len(samples) < 8:
                samples.append((civ, bld, node, st, present))

print("    agree %d / disagree %d" % (agree, disagree))
for civ, bld, node, st, present in samples:
    print("        %-12s bldg %-4s unit %-5s tree=%-18s panel lists it=%s"
          % (civ, bld, node, st, present))

print()
print("=" * 78)
# The verdict is DERIVED, not asserted.  Writing it before the numbers is the
# documented failure mode of this project: the prose outlives the table.
if pm is None:
    print("INCONCLUSIVE: no panel file on disk.")
else:
    exe_m = os.stat(os.path.join(GAME, "AoE2DE_s.exe")).st_mtime
    panel_is_old = pm < exe_m
    panel_in_shipped_window = len(same_day) > 0.5 * len(tfiles)
    print("    panel older than the exe          : %s" % panel_is_old)
    print("    panel written with the tree files : %s (%d of %d within a day)"
          % (panel_in_shipped_window, len(same_day), len(tfiles)))
    print("    tree files newer than the panel   : %d" % len(newer))
    print("    panel vs tree disagreements       : %d of %d"
          % (disagree, agree + disagree))
    print()
    if panel_is_old and panel_in_shipped_window:
        print("READING: the panel is a SHIPPED ARTIFACT, not a runtime cache.")
        print("  -> editing the tree could not have changed the menu, so the")
        print("     2026-10-14 test was not a fair test of the tree edit.")
        print("  -> the decisive experiment is the panel edit (Smoke2), which")
        print("     still has never run clean.")
    else:
        print("READING: the mtimes do NOT show a shipped artifact; the panel")
        print("may be rewritten at runtime.  Do not conclude either way from")
        print("this alone -- say so.")
    if disagree:
        print("    AND: %d disagreements means the panel is not a live"
              % disagree)
        print("    projection of the tree in either direction.")
print("=" * 78)
print("ANSWERED SINCE (2026-10-19): the build menu consults NEITHER panel file.")
print("Excluded in both directions by plain-game runs (Sicilians")
print("panel-silent-but-offered / Poles panel-listed-but-not-offered).  The menu")
print("follows `.dat` `type 2` commands on a tech the civ owns, last to fire wins")
print("(`dsh test v7` grant / `dsh test v17` revoke).  mtimes still bound WHEN this")
print("file was written -- it ships with the package, not as a runtime cache.")

# ---- assertions: turn measurements into a pin -------------------------------
#
# mtime ORDER is not an invariant and this pin must not assert it.  Steam's
# validation rewrites the mtime of any file whose bytes it re-delivers: on
# 2026-11-12 23:22:44 it re-downloaded futuravailableunits.json (byte-identical
# to what was already there, sha 1abbcd6c4c5a1fd5) and the panel instantly became
# NEWER than AoE2DE_s.exe, which had itself been rewritten at 23:19:46.  Both
# failed assertions below fired on that reshuffle while the data had not moved a
# byte -- "panel older than the exe" and "tree files within a day of the panel"
# are observations of one particular download, not properties of the build.
#
# The claim the pin is actually making is "this is shipped content, not a runtime
# cache".  The test for that is CONTENT: a runtime cache would differ from the
# vanilla archive, and from a second install of the same build.  mtimes stay in
# the printout above as measured facts.
import hashlib as _hashlib


def _sha_of(path):
    h = _hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


ARCHIVE = _HERE_PATH("..", "_cache", "vanilla_dat", "futuravailableunits.json")
PANEL = next((p for p in BP.panel_paths(GAME) if p), None)
assert pm is not None and PANEL, "the panel file must exist"
if os.path.isfile(ARCHIVE):
    live_sha, arch_sha = _sha_of(PANEL), _sha_of(ARCHIVE)
    assert live_sha == arch_sha, (
        "the panel in the game folder is not the shipped one (live %s vs "
        "archived vanilla %s) -- a probe or a mod rewrote it, and every number "
        "in this file then describes a fixture" % (live_sha[:16], arch_sha[:16]))
    print("    panel content == archived vanilla : True (%s)" % live_sha[:16])
else:
    print("    panel content == archived vanilla : unchecked "
          "(no archive at _cache/vanilla_dat)")
# A runtime cache would be rewritten at first launch, i.e. strictly later than
# the patch that shipped it.  Allow the Steam-re-validation case: the bytes are
# unchanged (proven above when the archive exists), only the stamp moved.
assert len(same_day) == len(tfiles) or (
    os.path.isfile(ARCHIVE) and _sha_of(PANEL) == _sha_of(ARCHIVE)), (
    "the tree files and the panel must either unpack together or be provably "
    "the same bytes as the shipped copy -- otherwise one of them is regenerated "
    "at runtime (%d of %d within a day)" % (len(same_day), len(tfiles)))
assert disagree > 0, (
    "the panel must NOT be a live projection of the tree; if it agreed "
    "everywhere this probe would be measuring a derivation, not a second file")
print()
print("PANEL PROVENANCE PIN: PASSED")
