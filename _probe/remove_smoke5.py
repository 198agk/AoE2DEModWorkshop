# -*- coding: utf-8 -*-
r"""Remove the smoke5 mod: its experiment cannot answer the question.

The design audit (task-1) found it broken three independent ways:

  1. The sibling mod `aoe2mod Bundle VillagerHP plus Britons HandCannon` ships
     the SAME three engine paths (`.dat`, `futuravailableunits.json`,
     `CivTechTrees\BRITONS.json`) with DIFFERENT content, and its `.dat` is
     byte-identical to smoke5's (both sha256[:16] 330665c06b53f033).  So "Villager
     HP 1000" cannot attribute which mod loaded, and with both enabled no
     outcome can be attributed to smoke5.

  2. Subject B (Militia 74) is masked by the design's own precondition: the
     Britons TREE already grants it (`ResearchedCompleted`), so removing the
     PANEL entry cannot be observed -- the tree supplies the button anyway.

  3. Both mods ship the same three paths, so per-file layering can produce the
     design's headline outcome with smoke5's edits entirely absent.

The shipped files already disagree in one direction with NO mod involved
(Jurchens: panel lists Long Swordsman/Two-Handed/Champion at the Barracks while
the tree says NotAvailable), which is strictly cheaper to observe.

This script deletes the smoke5 mod folder and touches nothing else -- no
mod-status.json edit, no other mod.
"""
import os
import _gamepaths as GP
import shutil
import subprocess
import sys

TITLE = "aoe2mod Smoke5 TreeVsPanel"
ACC = GP.ACCOUNT
DEST = os.path.join(ACC, "mods", "local", TITLE)


def running():
    r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq AoE2DE_s.exe"],
                       capture_output=True, text=True)
    return "AoE2DE_s.exe" in r.stdout


def main():
    if running():
        print("!! the game is RUNNING.  Quit it first -- nothing has been changed.")
        return 1
    if not os.path.isdir(DEST):
        print("already absent: %s" % DEST)
        return 0
    # Verify the resolved path really is the intended mod before deleting.
    real = os.path.realpath(DEST)
    want = os.path.realpath(os.path.join(ACC, "mods", "local", TITLE))
    if real != want or "mods" not in real or TITLE not in real:
        print("REFUSING: resolved %r is not the intended mod folder" % real)
        return 2
    shutil.rmtree(real)
    print("removed: %s" % real)
    print()
    print("remaining local mods:")
    local = os.path.join(ACC, "mods", "local")
    for d in sorted(os.listdir(local)):
        print("   %s" % d)
    return 0


if __name__ == "__main__":
    sys.exit(main())
