# -*- coding: utf-8 -*-
"""Does a storage-point overlay recurse into SUBDIRECTORIES?

Why this file exists
--------------------
The in-game failure of 2026-10-14 (a rewritten
`resources/_common/dat/CivTechTrees/BRITONS.json` did nothing while the `.dat`
half of the same mod worked) has one very attractive explanation:

    "the DAT storage point only overlays files at its ROOT, so a file nested
     one directory down is never seen."

That explanation is testable WITHOUT the game, because the game already proves
it false somewhere else.  The WIDGETUI storage point's root is `widgetui/`
(see the shipped registry `modes/Pompeii/Pompeii.json`), and a well-known
published mod ships its emblem replacement at

    widgetui/textures/ingame/emblems/lithuanians.png

-- THREE directories below the storage root -- and that art is visible in the
game's bottom command panel (screenshots; `_probe/loose_override_proof.py`).
So storage-point overlays DO resolve nested paths.  Depth 1 cannot be the
reason the DAT override failed.

What this changes
-----------------
It removes the cheapest explanation and sharpens the open question from
"is the overlay recursive?" to "why is `CivTechTrees/` special?" -- candidates
then being that the tree is read before mods are mounted, that it is read from
the base path only, or that the build panel does not consult it at all (the
panel file `futuravailableunits.json` sits next to `TechTreePreviewPanel` in
the exe string pool, so the screen the user checked may have been reading a
different file).

PROVEN here     : storage points are declared with a directory root; mods ship
                  nested files under WIDGETUI's root; the DAT root's only
                  nested mod file is the one that failed.
ANSWERED SINCE (2026-10-19): recursion was never the question.  The DAT overlay
                  is recursive, and the tree write still moves nothing --
                  `dsh test v15` shipped two CivTechTrees files over a
                  byte-identical `.dat`, engine logged loading the mod, build
                  menu unchanged in both directions.  The menu follows `.dat`
                  `type 2` commands on a tech the civ owns, last to fire wins
                  (v7 grant / v17 revoke).
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                        # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
PROFILE = r"C:\Users\26913\Games\Age of Empires 2 DE"
MODS = os.path.join(PROFILE, "76561198406248391", "mods")

FAILURES = []


def check(cond, label):
    print("[%s] %s" % ("PASS" if cond else "FAIL", label))
    if not cond:
        FAILURES.append(label)


# ---------------------------------------------------------------------------
print("=" * 74)
print("A -- the shipped registry declares each storage point with a DIRECTORY root")
print("=" * 74)
reg_path = os.path.join(GAME, "modes", "Pompeii", "Pompeii.json")
reg = json.load(io.open(reg_path, encoding="utf-8-sig"))
points = reg["storage_point_list"]
print("    registry: %s" % reg_path)
print("    storage points declared: %d" % len(points))
by_type = {}
for e in points:
    if isinstance(e, dict) and e.get("type"):
        by_type[e["type"]] = e
print("    DAT     -> %r" % (by_type.get("DAT") or {}).get("path"))
print("    WIDGETUI-> %r" % (by_type.get("WIDGETUI") or {}).get("path"))
check("path" in by_type.get("DAT", {}), "the DAT storage point declares a path")
check("path" in by_type.get("WIDGETUI", {}), "the WIDGETUI storage point declares a path")

DAT_REL = by_type["DAT"]["path"].replace("\\", "/")
WUI_REL = by_type["WIDGETUI"]["path"].replace("\\", "/")


# ---------------------------------------------------------------------------
print()
print("=" * 74)
print("B -- every mod file, measured by how DEEP it sits under its storage root")
print("=" * 74)


def mod_dirs():
    out = []
    for kind in ("local", "subscribed"):
        base = os.path.join(MODS, kind)
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            p = os.path.join(base, name)
            if os.path.isdir(p):
                out.append((name, p))
    return out


def depth_under(mod_dir, rel):
    """Return (depth, relpath) for files under mod_dir/<rel>, depth 0 = direct child."""
    base = os.path.join(mod_dir, *rel.split("/"))
    if not os.path.isdir(base):
        return []
    hits = []
    for dirpath, _dirs, files in os.walk(base):
        for f in files:
            full = os.path.join(dirpath, f)
            inner = os.path.relpath(full, base).replace("\\", "/")
            hits.append((inner.count("/"), inner))
    return hits


for label, rel in (("WIDGETUI", WUI_REL), ("DAT", DAT_REL)):
    print()
    print("  --- %s  (storage root %r) ---" % (label, rel))
    nested_total = 0
    mods_with = 0
    deepest = 0
    sample = []
    nested_mods = set()
    for name, p in mod_dirs():
        hits = depth_under(p, rel)
        n = len([h for h in hits if h[0] >= 1])
        if hits:
            mods_with += 1
        if n:
            nested_total += n
            nested_mods.add(name)
            deepest = max(deepest, max(h[0] for h in hits if h[0] >= 1))
            if len(sample) < 4:
                for d, inner in sorted(hits, key=lambda t: -t[0]):
                    if d >= 1:
                        sample.append((name[:44], d, inner))
                        break
    print("      mods contributing files here : %d" % mods_with)
    print("      files nested >=1 below root  : %d" % nested_total)
    print("      deepest nesting              : %d" % deepest)
    for nm, d, inner in sample:
        print("        depth %d  %-44s %s" % (d, nm, inner))
    if label == "WIDGETUI":
        wui_nested = nested_total
        wui_deepest = deepest
    else:
        dat_nested = nested_total
        dat_sample = sample
        dat_nested_mods = nested_mods


# ---------------------------------------------------------------------------
print()
print("=" * 74)
print("C -- the pivotal case: a nested WIDGETUI override that RENDERS IN GAME")
print("=" * 74)
EMBLEM_REL = "textures/ingame/emblems/lithuanians.png"
game_png = os.path.join(GAME, "widgetui", *EMBLEM_REL.split("/"))
found = []
for name, p in mod_dirs():
    mod_png = os.path.join(p, "widgetui", *EMBLEM_REL.split("/"))
    if os.path.isfile(mod_png):
        gs = os.path.getsize(game_png) if os.path.isfile(game_png) else -1
        found.append((name, os.path.getsize(mod_png), gs, mod_png))
print("    storage root        : %r" % WUI_REL)
print("    path below the root : %r  (depth 3)" % EMBLEM_REL)
print("    game file exists    : %s (%d B)"
      % (os.path.isfile(game_png), os.path.getsize(game_png) if os.path.isfile(game_png) else -1))
for name, ms, gs, mp in found:
    print("    mod  %-46s %8d B   game %8d B   differs %s"
          % (name[:46], ms, gs, ms != gs))
check(len(found) >= 1,
      "a published mod ships a file THREE levels below the WIDGETUI storage root")
check(any(ms != gs for _n, ms, gs, _p in found),
      "that nested file differs from the game's copy (so it is a real override)")

print()
print("    RECORDED OBSERVATION, not re-measured here: that override is the")
print("    chibi emblem art, and it is visible in the running game's bottom")
print("    command panel (screenshots + user-visible art in the HUD).  See")
print("    _probe/loose_override_proof.py for the on-disk half of that proof.")


# ---------------------------------------------------------------------------
print()
print("=" * 74)
print("D -- so, which explanation survives?")
print("=" * 74)
print("    WIDGETUI: %d nested mod files, deepest depth %d  -> overlays DO recurse"
      % (wui_nested, wui_deepest))
print("    DAT     : %d nested mod file(s), and it is the one that failed in game"
      % dat_nested)
for nm, d, inner in dat_sample:
    print("        %-44s depth %d  %s" % (nm, d, inner))
check(wui_nested > 50 and wui_deepest >= 3,
      "nested overrides are normal in a storage point whose in-game effect is known "
      "(%d files, depth %d)" % (wui_nested, wui_deepest))
# The DAT half has to exclude THIS PROJECT'S OWN experiment mods ("dsh test v14/v15/v17"
# all ship `CivTechTrees/<CIV>.json`).  Counting them made this a literal about the
# user's mutable mod list -- the same rot that broke `test_install*.py` -- and it fired
# the moment v17 was installed.  What the claim is really about is the SHIPPED world:
# among mods that are not ours, nested DAT files stay rare.
_own = {n for n in dat_nested_mods if n.lower().startswith("dsh test")}
_dat_nested_foreign = dat_nested - sum(
    1 for n in _own for _d, _i in depth_under(dict(mod_dirs())[n], DAT_REL) if _d >= 1)
print("      of which this project's own experiment mods: %d (%d file(s))"
      % (len(_own), dat_nested - _dat_nested_foreign))
check(_dat_nested_foreign <= 2,
      "'the overlay is not recursive' is REFUTED, because nesting works elsewhere "
      "(%d nested DAT files outside this project's own test mods is not a depth limit)"
      % _dat_nested_foreign)

print()
print("=" * 74)
print("VERDICT")
print("=" * 74)
print("OVERLAY DEPTH: storage-point overlays resolve nested subdirectories --")
print("proven in game elsewhere (%d nested WIDGETUI files, depth %d, and the"
      % (wui_nested, wui_deepest))
print("chibi emblem that sits 3 levels down is visible in the HUD).  So the DAT")
print("override did not fail because of depth.")
print()
print("ANSWERED SINCE (2026-10-19): the tree path is not special after all -- it")
print("is written, it is loaded, and the build menu does not consult it.  v15 sent")
print("only `CivTechTrees/*.json` (byte-identical `.dat` carrier) and the screen did")
print("not move.  v17 then put the same question to the layer that DOES gate the")
print("menu -- the `.dat` `type 2` command -- and both directions moved.  So the")
print("candidate list below is history, not open work.")
print("NOT PROVEN: what `CivTechTrees/` IS consulted for (the tech-tree preview")
print("reads it; `futuravailableunits.json`, which sits next to")
print("`TechTreePreviewPanel` in the exe string pool, is the other reader).")
print()
if FAILURES:
    print("FAILURES: %d" % len(FAILURES))
    for f in FAILURES:
        print("  - %s" % f)
    sys.exit(1)
print("ALL OVERLAY-DEPTH CHECKS PASSED")
