# -*- coding: utf-8 -*-
"""When does the game actually READ each data layer?

Motivation: in the 2026-10-14 session the shipped `.dat` half visibly took
effect (Villager HP 1000) while the JSON halves did not -- and in EVERY one of
my sessions the mod was only enabled *mid-session*, never in the startup
enable list.  If a layer is read before mods mount, then a mod that gets
enabled later can never affect it, and "the write did nothing" would be a
statement about LOAD ORDER, not about the write.

So: find, for each session, the line numbers of the load-order landmarks and of
the mod-enable lines, and see what the mid-session enables actually precede.
"""
import os
import re

LOGS = r"C:\Users\26913\Games\Age of Empires 2 DE\logs"

# Landmarks, in the order the engine prints them.
MARKERS = [
    ("mod manager setup",      r"Setup mod manager"),
    ("Enabling mod",           r"Enabling mod #"),
    ("post-mod-manager",       r"post mod manager|PostModManager"),
    ("modded languages",       r"install modded languages|modded languages"),
    ("open resource packages", r"Opening resource packages|open resource packages"),
    ("palettes/shapes",        r"Setting up palettes|palettes"),
    ("sound system",           r"Setting up sound system|sound system"),
    ("screen resolution",      r"screen resolution"),
    ("player profile",         r"Loading player profile"),
    ("hotkeys",                r"Setting up hotkeys"),
]

# What each dat-layer file would be consulted for, if it is consulted at all.
INTEREST = ["futuravailableunits", "CivTechTrees", "empires2_x2_p1", "mod-status",
            "morematerials", "materials.json", "linkedTechs", "civilizations.json"]


def sessions():
    out = []
    for name in sorted(os.listdir(LOGS)):
        d = os.path.join(LOGS, name)
        ml = os.path.join(d, "MainLog.txt")
        if os.path.isdir(d) and os.path.isfile(ml):
            out.append((name, ml))
    return out


print("=" * 78)
print("1  load-order landmarks vs. mod-enable lines, per session")
print("=" * 78)

for name, ml in sessions():
    lines = open(ml, encoding="utf-8", errors="replace").read().splitlines()
    hits = {}
    for label, pat in MARKERS:
        rx = re.compile(pat)
        first = None
        for i, ln in enumerate(lines):
            if rx.search(ln):
                first = i + 1
                break
        hits[label] = first
    enables = []
    for i, ln in enumerate(lines):
        if "Enabling mod #" in ln:
            enables.append((i + 1, ln.strip()))
    print()
    print("--- %s  (%d lines)" % (name, len(lines)))
    for label, _ in MARKERS:
        v = hits[label]
        print("    %-22s %s" % (label, ("line %d" % v) if v else "-- absent --"))
    if enables:
        post = hits["post-mod-manager"]
        for ln_no, txt in enables:
            where = "STARTUP" if (post and ln_no < post) else "MID-SESSION"
            print("    %-22s line %-5d %s   [%s]"
                  % ("mod enabled", ln_no, txt[:58], where))
    else:
        print("    no mod was enabled in this session")

print()
print("=" * 78)
print("2  is any dat-layer FILENAME ever mentioned in a log?")
print("=" * 78)
tot = {k: 0 for k in INTEREST}
for name, ml in sessions():
    txt = open(ml, encoding="utf-8", errors="replace").read()
    for k in INTEREST:
        tot[k] += txt.count(k)
for k in INTEREST:
    print("    %-24s %d occurrence(s) across all sessions" % (k, tot[k]))
print()
print("NOTE: a count of 0 means the engine never NAMES the file in the log --")
print("      it does not mean the file is unused.  Logs record events, not reads.")
