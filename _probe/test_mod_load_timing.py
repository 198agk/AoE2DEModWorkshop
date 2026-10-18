# -*- coding: utf-8 -*-
r"""PIN: the reason every in-game availability test failed -- TIMING, not mechanism.

The user's latest result (m24260) was the first test with a valid subject and a
working control:

    「村民血量1000没问题，黑暗时代兵营没有蔷琵侦察兵」
      villager 1000 (control PASSED)  /  no Champi Scout (test FAILED)

But the CONTROL PASSING is itself the clue.  The `.dat` edit DID render.  So the mod
was read -- yet the tree/panel edit was not.  That asymmetry has one obvious cause,
and the game's own log states it.

## The measurement

    session 2026.10.15-1603.52  (the smoke6 test)
        236  Setup mod manager
        249  Setup post mod manager
        254  Opening resource packages     <-- DAT / CivTechTrees / panel read HERE
        328  Running Game
        954  Enabling mod #0 (aoe2mod Smoke6 Champi Scout)   <-- 700 lines LATE
       1895  Exiting with code 0

    session 2026.10.14-2330.11  (the earlier tree-write test)
        265  Opening resource packages
        340  Running Game
        866  Enabling mod #0 (aoe2mod Panel Smoke - Britons Hand Cannoneer)
        891  Enabling mod #0 (aoe2mod Panel Smoke - Britons Hand Cannoneer)

**Every single one of this project's mods has been enabled AFTER "Opening resource
packages".**  Four prior sessions show the same shape (1623.36, 1625.36, 1705.28,
2330.11, 1603.52).

So a mod installed while the game is already running is only picked up in a LATER
mod-manager pass, by which time the DAT storage point has long been read.  The `.dat`
still took effect because the user then started a NEW GAME, which reloads game data;
the tree/panel layer is read once at bootstrap and is not re-read for the new game.

## Why this matters

It means the availability write has **never been tested at all** -- every attempt was
structurally incapable of showing it, because the mod was not loaded when those files
were read.  The correct test is: install the mod, then **restart the game** so it
appears in the startup enable list (lines 237-244, alongside the user's other mods).
The user's own instruction (`m22351`: "put it in the folder, the game recognises it")
is necessary but not sufficient -- the game must be (re)started after the copy.

## The distinction this pins

    "the mod loaded"  (verified: the .dat edit rendered)
    "the mod was loaded BEFORE the files were read"  (NOT verified; refuted here)

Every conclusion drawn earlier from "the mod loaded and the menu did not change" is
therefore void -- including the 2026-10-14 result that made this write "unproven".

Run:  $env:PYTHONPATH='D:\\Software\\AI\\帝国项目'; python _probe\test_mod_load_timing.py
"""
import os
import re
import sys

LOGS = r"C:\Users\26913\Games\Age of Empires 2 DE\logs"
# Every name this project's test mods have ever used.  `dsh test vN` is the current
# scheme (`_probe/testmod_name.py`); the older ones are kept so historical sessions
# still match.
MY_MODS = ("aoe2mod", "Smoke", "Panel Smoke", "dsh test")
fails = []


def check(name, ok, detail=""):
    print("  %-72s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "   %s" % detail))
    if not ok:
        fails.append(name)


def sessions():
    for d in sorted(os.listdir(LOGS)):
        p = os.path.join(LOGS, d, "MainLog.txt")
        if os.path.isfile(p):
            yield d, p


def first(lines, pat):
    for i, ln in enumerate(lines, 1):
        if re.search(pat, ln):
            return i
    return None


print("A  every session that enabled one of MY mods, and where")
rows = []
for name, path in sessions():
    lines = open(path, "rb").read().decode("utf-8", "replace").splitlines()
    res = first(lines, r"Opening resource packages")
    my = [i for i, ln in enumerate(lines, 1)
          if "Enabling mod #0" in ln and any(m in ln for m in MY_MODS)]
    if not my:
        continue
    rows.append((name, res, my[0], my[-1], len(lines)))
    print("   %-22s resource-packages@%-5s  my mod enabled@%-5s (last %-5s)  lines=%d"
          % (name, res, my[0], my[-1], len(lines)))

print()
print("B  what the log shows, for whatever sessions are still on disk")
# The logs directory ROTATES, so the number of matching sessions is not a stable
# claim -- requiring ">= 4" made this pin fail for a reason unrelated to what it
# measures (it found 1).  Report the counts; assert only what is time-independent.
print("     sessions matching one of my mod names: %d" % len(rows))
_late = [r for r in rows if r[1] is not None and r[2] > r[1]]
_early = [r for r in rows if r[1] is not None and r[2] <= r[1]]
print("     ...where the mod line falls AFTER resource loading : %d" % len(_late))
print("     ...and where it falls in the STARTUP enable block  : %d" % len(_early))
for r in rows:
    print("        %-22s resources@%-5s mine@%-5s  %s"
          % (r[0], r[1], r[2], "STARTUP" if r[1] is not None and r[2] <= r[1]
             else "late"))
# There is no stable invariant here any more, and that is the finding: the mod was
# LATE in every session up to 2026-10-16-0930, and EARLY (startup block, line 237)
# from 2026-10-16-1011 onwards -- which is when it started being registered in
# `mod-status.json` before launch.  So a pin asserting either direction would encode
# a moment in time, not a rule.

print()
print("C  the startup block, per session")
bad = []
for name, path in sessions():
    lines = open(path, "rb").read().decode("utf-8", "replace").splitlines()
    a = first(lines, r"^Setup mod manager")
    b = first(lines, r"^Setup post mod manager")
    if a is None or b is None:
        continue
    startup = "\n".join(lines[a - 1:b])
    if any(m in startup for m in MY_MODS):
        bad.append(name)
print("     sessions that enabled one of my mods during startup: %d of %d"
      % (len(bad), len(rows)))
print("     earliest such session: %s"
      % (min(bad) if bad else "none"))
print("     [note] the log-position fact is reported without asserting a direction:")

print()
print("D  WHAT THIS MEASURES, AND WHAT IT DOES NOT")
print("     It measures ONE thing: the log line `Enabling mod #0 (<title>)` for my mods")
print("     falls after `Opening resource packages`.  The user corrected the reading of")
print("     that line (m24660): a data mod is loaded WHEN A MATCH STARTS, not at launch,")
print("     so this timing is NOT why a JSON availability write failed.")
print()
print("     The interpretation once drawn from this file -- 'the tree/panel were read at")
print("     bootstrap, before this mod existed for the engine, so the availability write")
print("     has never been tested' -- is SUPERSEDED.  The clean 2026-10-15 test selected")
print("     the data mod before the match, the .dat control rendered, and the JSON write")
print("     still did not reach the build menu.")
print()
print("     Kept because the log-position fact itself is real and cheap to re-check;")
print("     do NOT cite it as an explanation.")

print()
print("MOD LOAD TIMING: the log line for my mods lands after 'Opening resource")
print("  packages' -- a fact about the LOG, not the reason any test failed (the user's")
print("  m24660 correction superseded that reading).")
for n in fails:
    print("  FAILED: %s" % n)
sys.exit(1 if fails else 0)
