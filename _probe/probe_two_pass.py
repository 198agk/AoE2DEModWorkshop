# -*- coding: utf-8 -*-
"""Is the mod manager run TWICE -- once at boot, once at match start?

If it is, then a mod written into mod-status.json while the game is already at
the menu gets enabled on the SECOND pass -- and by then the UI layers may
already have been read, while the .dat is read right there.  That would explain
why the .dat half took effect in game while the JSON halves never did.
"""
import os
import re

LOGS = r"C:\Users\26913\Games\Age of Empires 2 DE\logs"
NOISE = re.compile(r"rlink - error|Obstruction type|^\s*$")
SPAM = re.compile(r"Obstruction type")

# Every line that says a layer is being set up / read.
KEYS = [
    ("Setup mod manager",        r"Setup mod manager"),
    ("post mod manager",         r"post mod manager"),
    ("Enabling mod",             r"Enabling mod #"),
    ("Closing video",            r"Closing video"),
    ("Opening resource packages", r"Opening resource packages"),
    ("Game::setup",              r"Game::setup|setup\(\) before|setup\(\) after"),
    ("player profile",           r"Loading player profile"),
    ("hotkeys",                  r"Setting up hotkeys"),
    ("Running Game",             r"Running Game"),
    ("first Obstruction warn",   r"Obstruction type \[4\]"),
    ("Terminating Mod Manager",  r"Terminating Mod Manager"),
    ("Exiting",                  r"Exiting with code"),
]

for name in sorted(os.listdir(LOGS)):
    d = os.path.join(LOGS, name)
    p = os.path.join(d, "MainLog.txt")
    if not (os.path.isdir(d) and os.path.isfile(p)):
        continue
    raw = open(p, encoding="utf-8", errors="replace").read().splitlines()
    print()
    print("=" * 74)
    print(name)
    print("=" * 74)
    for label, pat in KEYS:
        rx = re.compile(pat)
        hits = [i + 1 for i, ln in enumerate(raw) if rx.search(ln)]
        if hits:
            shown = hits if len(hits) <= 8 else hits[:4] + ["..."] + hits[-2:]
            print("   %-26s %s" % (label, shown))
        else:
            print("   %-26s --" % label)
