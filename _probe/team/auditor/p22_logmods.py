# -*- coding: utf-8 -*-
"""Audit probe 22: what the game log actually records about enabled mods, and
whether Smoke5 has EVER been enabled."""
import os, glob, re, json

PROFILE = r"C:\Users\26913\Games\Age of Empires 2 DE"
LOGS = os.path.join(PROFILE, "logs")


def head(t):
    print(); print("=" * 78); print(t); print("=" * 78)


sessions = [d for d in glob.glob(os.path.join(LOGS, "*")) if os.path.isdir(d)]
sessions.sort(key=lambda d: os.path.getmtime(d), reverse=True)
print("sessions: %d, newest 12 by mtime:" % len(sessions))
for s in sessions[:12]:
    print("   %-46s %s" % (os.path.basename(s),
          __import__("time").strftime("%Y-%m-%d %H:%M", __import__("time").localtime(os.path.getmtime(s)))))

head("22a: 'Enabling mod' lines -- newest sessions first")
seen = 0
for s in sessions:
    ml = os.path.join(s, "MainLog.txt")
    if not os.path.isfile(ml):
        continue
    lines = open(ml, encoding="utf-8", errors="replace").read().splitlines()
    en = [l for l in lines if "Enabling mod" in l]
    if not en:
        continue
    seen += 1
    print()
    print("   -- %s  (%d 'Enabling mod' lines)" % (os.path.basename(s), len(en)))
    for l in en:
        print("      %s" % l.strip()[:180])
    if seen >= 4:
        break

head("22b: every distinct mod path the logs ever enabled")
pat = re.compile(r"Enabling mod[^\n]*")
allmods = {}
for s in sessions:
    ml = os.path.join(s, "MainLog.txt")
    if not os.path.isfile(ml):
        continue
    for l in open(ml, encoding="utf-8", errors="replace"):
        if "Enabling mod" in l:
            allmods.setdefault(l.strip()[:200], 0)
            allmods[l.strip()[:200]] += 1
print("   %d distinct lines" % len(allmods))
for k, v in sorted(allmods.items(), key=lambda kv: -kv[1])[:40]:
    print("   x%-4d %s" % (v, k))

head("22c: newest session, mod-manager life-cycle markers in order")
if sessions:
    ml = os.path.join(sessions[0], "MainLog.txt")
    print("   file:", ml, os.path.isfile(ml))
    if os.path.isfile(ml):
        keys = ("Setup mod manager", "Enabling mod", "Terminating Mod Manager",
                "Loading player profile", "Opening resource packages", "Running Game")
        for i, l in enumerate(open(ml, encoding="utf-8", errors="replace")):
            for k in keys:
                if k in l:
                    print("   [%6d] %s" % (i + 1, l.strip()[:170]))
                    break
