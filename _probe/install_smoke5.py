# -*- coding: utf-8 -*-
r"""Place smoke5 into the profile's ``mods\local`` folder.

Per the user's instruction (2026-10-15): a mod is installed by PUTTING THE
FOLDER IN PLACE; the game notices it by itself and the user sets the enabled
flag in the mod manager.  So this script:

  * refuses to run while the game is up (the game rewrites mod-status.json on
    exit and may switch mods off, and a copy into a directory the game is
    scanning is not something to do blind);
  * copies the built tree into ``<account>\\mods\\local\\<title>``;
  * verifies every byte landed by re-reading it and comparing sha256;
  * does NOT touch mod-status.json, Enable, priority, or anything else.

Usage:
    $env:PYTHONPATH='D:\Software\DeepSeek Harness\工作区2'
    & $py _probe\install_smoke5.py
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aoe2mod.game import locations as G                    # noqa: E402

PROBE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(PROBE, "out_smoke5")
TITLE = "aoe2mod Smoke5 TreeVsPanel"
PROFILE = r"C:\Users\26913\Games\Age of Empires 2 DE"


def running():
    r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq AoE2DE_s.exe"],
                       capture_output=True, text=True)
    return "AoE2DE_s.exe" in r.stdout


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if running():
        print("!! the game is RUNNING.  Quit it first -- nothing has been changed.")
        return 1
    if not os.path.isdir(SRC):
        print("!! %s does not exist -- run build_smoke5.py first" % SRC)
        return 1

    acc = G.pick_account(PROFILE)
    dest = os.path.join(acc, "mods", "local", TITLE)
    print("account : %s" % acc)
    print("source  : %s" % SRC)
    print("dest    : %s" % dest)

    if os.path.isdir(dest):
        shutil.rmtree(dest)
    shutil.copytree(SRC, dest)

    print()
    print("verifying what landed (sha256 of source vs copy):")
    ok = True
    for root, _dirs, files in os.walk(SRC):
        for f in sorted(files):
            s = os.path.join(root, f)
            rel = os.path.relpath(s, SRC)
            d = os.path.join(dest, rel)
            if not os.path.isfile(d):
                print("  MISSING  %s" % rel)
                ok = False
                continue
            a, b = sha(s), sha(d)
            same = a == b
            ok = ok and same
            print("  %-56s %9d B  %s" % (rel, os.path.getsize(d),
                                         "identical" if same else "DIFFERENT"))
    print()
    print("ALL BYTES IDENTICAL: %s" % ok)

    print()
    print("other local mods still present (this script did not touch them):")
    local = os.path.join(acc, "mods", "local")
    for d in sorted(os.listdir(local)) if os.path.isdir(local) else []:
        print("   %s%s" % (d, "   <<< the new one" if d == TITLE else ""))

    print()
    print("NEXT (the user's part):")
    print("  1. start the game and open the mod manager")
    print("  2. make sure '%s' is ENABLED and, to keep the test" % TITLE)
    print("     single-variable, that no other dat-layer mod is")
    print("  3. one Britons game, Dark Age; look at the BARRACKS:")
    print("       Champi Scout button present -> the TREE file drives the menu")
    print("       Militia button missing      -> the PANEL file drives the menu")
    print("     control: Villager HP must read 1000, or the mod did not load")
    print()
    print("mod-status.json was NOT modified by this script.")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
