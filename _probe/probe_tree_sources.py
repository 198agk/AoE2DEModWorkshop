# -*- coding: utf-8 -*-
"""Where could the engine be reading the tech tree from?

Motivation
----------
A rewritten `resources/_common/dat/CivTechTrees/BRITONS.json` shipped INSIDE a
mod that demonstrably took effect (its `.dat` half gave villagers 1000 HP) had
NO in-game effect (2026-10-14).  Two cheap explanations are already refuted:

  * depth -- `_probe/test_overlay_depth.py`: 550 mod files sit nested under the
             WIDGETUI storage root, deepest 4 levels, and the one 3 levels down
             is visible in the HUD.
  * form  -- `_probe/test_tree_form.py`: the engine names exactly one template,
             `CivTechTrees/%s.json`, and the aggregate `civTechTrees.json` is a
             mode-only form.

So the remaining candidates are (a) the tree is read from somewhere else on
disk, or (b) it is read before mods are mounted.  This probe hunts for (a) --
a second copy, a DLC/mode variant, or a precompiled pack.  It does not read
fields and cannot answer (b).
"""
import os
import re

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
PROFILE = r"C:\Users\26913\Games\Age of Empires 2 DE"
EXE = os.path.join(GAME, "AoE2DE_s.exe")

FILE_KEYS = ("civtech", "futureavailableunits")


def interesting_file(name):
    fl = name.lower()
    if any(k in fl for k in FILE_KEYS):
        return True
    if "techtree" in fl and fl.endswith(".json"):
        return True
    return False


def interesting_dir(name):
    low = name.lower()
    if low in ("modes", "dlc", "dat"):
        return True
    return "civtech" in low or "techtree" in low


def scan(root, label):
    files, dirs = [], []
    for dp, dn, fn in os.walk(root):
        b = os.path.basename(dp)
        if b and interesting_dir(b):
            dirs.append(dp)
        for f in fn:
            if interesting_file(f):
                files.append(os.path.join(dp, f))
    print("=" * 76)
    print("%s : %s" % (label, root))
    print("=" * 76)
    print("  matching files: %d" % len(files))
    groups = {}
    for p in files:
        groups.setdefault(os.path.dirname(p), []).append(os.path.basename(p))
    for d in sorted(groups):
        names = sorted(groups[d])
        print("    %s  (%d)" % (d, len(names)))
        for n in names[:8]:
            print("        %s" % n)
        if len(names) > 8:
            print("        ... +%d more" % (len(names) - 8))
    print("  modes/dlc/dat/civtech dirs: %d" % len(dirs))
    for d in sorted(dirs)[:40]:
        print("    %s" % d)
    if len(dirs) > 40:
        print("    ... +%d more" % (len(dirs) - 40))
    print()
    return files, dirs


scan(GAME, "GAME TREE")
scan(PROFILE, "USER PROFILE")


def window(needle, before=2048, after=2048, limit=90):
    with open(EXE, "rb") as fh:
        exe = fh.read()
    offs, start = [], 0
    while True:
        i = exe.find(needle, start)
        if i < 0:
            break
        offs.append(i)
        start = i + 1
    print("=" * 76)
    print("EXE literal %r : %d occurrence(s)  (file %d B)" %
          (needle.decode("ascii", "replace"), len(offs), len(exe)))
    print("=" * 76)
    for off in offs:
        lo = max(0, off - before)
        hi = min(len(exe), off + after)
        print("  --- occurrence @0x%x, window 0x%x..0x%x ---" % (off, lo, hi))
        n = 0
        for m in re.finditer(rb"[\x20-\x7e]{4,}", exe[lo:hi]):
            print("    %08x  %s" % (lo + m.start(), m.group().decode("ascii")))
            n += 1
            if n >= limit:
                print("    ... (window truncated)")
                break
    print()
    return offs


window(b"CivTechTrees/%s.json")
window(b"civTechTrees.json")
window(b"futuravailableunits.json")

print("=" * 76)
print("PACKED-FILE CHECK: resources/_common/dat/InterfaceData.pbin")
print("=" * 76)
pbin = os.path.join(GAME, "resources", "_common", "dat", "InterfaceData.pbin")
if os.path.exists(pbin):
    with open(pbin, "rb") as fh:
        blob = fh.read()
    print("  size : %d B" % len(blob))
    print("  head : %s" % blob[:32].hex(" "))
    print("  zip? %s" % blob.startswith(b"PK\x03\x04"))
    for probe in (b"CivTechTrees", b"civ_techs_units", b"LinkedTechs",
                  b"futuravailableunits", b"Longbowman", b"Hand Cannoneer",
                  b"ResearchedCompleted"):
        print("  contains %-22r : %s" %
              (probe.decode(), blob.find(probe) >= 0))
else:
    print("  MISSING")

print()
print("=" * 76)
print("EVERY `dat` DIRECTORY (so a DLC/mode variant cannot hide)")
print("=" * 76)
for dp, dn, fn in os.walk(GAME):
    if os.path.basename(dp).lower() != "dat":
        continue
    print("  %s  (%d files)" % (dp, len(fn)))
    for f in sorted(fn)[:60]:
        try:
            sz = os.path.getsize(os.path.join(dp, f))
        except OSError:
            sz = -1
        print("      %-44s %d" % (f, sz))
print()
print("TREE SOURCES: see the inventory above.")
