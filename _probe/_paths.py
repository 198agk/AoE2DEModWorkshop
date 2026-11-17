# -*- coding: utf-8 -*-
"""Where the build products live, in ONE place.

WHY THIS EXISTS
---------------
Every build product used to be written OUTSIDE the checkout -- one folder for the
cargo tree, one for the shipping bundle -- and twenty-odd probes each wrote that
absolute path out by hand.  Two things went wrong with that:

  * The workspace was not self-contained.  `git clean`, a fresh clone, or a move
    of the folder left the products behind, and a probe that could not find them
    reported red for a reason that had nothing to do with the code.
  * The Integrity Label on those folders was not the workspace's.  On this machine
    a folder outside the checkout carried no label and every copied
    `python.exe` in it worked, while the ones under the checkout inherited Low
    and died with 0xC0000135 the moment they started (2026-11-01, six hours lost).
    Keeping the products inside the workspace means they inherit the same label
    as everything else the project writes, so the launcher is tested where it
    will actually be run.

So: everything is under the checkout now, and a probe asks this module instead of
repeating a path.

  _out/AoE2ModWorkshop/   the shipping bundle (`_probe/make_bundle.py`)
  _cache/AGE2/desktop/    the ASCII cargo tree     (`_probe/build_shell_ascii.py`)

Both are gitignored.  Both can be moved with an environment variable, which is
what lets two test runs exist at the same time without fighting over one folder:

  AOE2MOD_BUNDLE   the bundle root
  AOE2MOD_BUILD    the ASCII cargo tree's `desktop` directory
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

BUNDLE = os.environ.get("AOE2MOD_BUNDLE") or os.path.join(
    REPO, "_out", "AoE2ModWorkshop")
BUILD = os.environ.get("AOE2MOD_BUILD") or os.path.join(
    REPO, "_cache", "AGE2", "desktop")
EXE = os.path.join(BUILD, "src-tauri", "target", "release",
                   "aoe2-mod-workshop.exe")
BUNDLED_EXE = os.path.join(BUNDLE, "aoe2-mod-workshop.exe")
RUN_UI = os.path.join(REPO, "tools", "run_ui.py")
