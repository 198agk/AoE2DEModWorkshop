# -*- coding: utf-8 -*-
"""Why does the game write `Enabled: false` for MY mod but `true` for others?

The log proves the game runs its mod manager at least twice: once at boot
(`Setup mod manager` ~232, `Enabling mod #` 233-246, `post mod manager` ~259)
and again at the main menu after the intro video (`Closing video` ~880, then
`Enabling mod #` ~900-990).  Every one of my mods was only picked up on the
SECOND pass -- because they were installed while the game was already running.

This compares the status entries field by field, to see whether the game has a
way to tell a mod it has seen before from one it has not.
"""
import json
import os

STATUS = (r"C:\Users\26913\Games\Age of Empires 2 DE"
          r"\76561198406248391\mods\mod-status.json")
BAK = STATUS + ".bak"

s = json.loads(open(STATUS, encoding="utf-8", errors="replace").read(),
               strict=False)
print("=" * 78)
print("mod-status.json  (%d bytes, %d mods)" % (os.path.getsize(STATUS),
                                                len(s.get("Mods", []))))
print("=" * 78)
allkeys = set()
for m in s["Mods"]:
    allkeys |= set(m)
print("union of keys across entries: %s" % sorted(allkeys))
print()
for m in s["Mods"]:
    print("  prio %-3s enabled=%-5s %s" % (m.get("Priority"),
                                           m.get("Enabled"),
                                           str(m.get("Title") or m.get("Path"))[:52]))
    missing = sorted(allkeys - set(m))
    if missing:
        print("        MISSING KEYS vs union: %s" % missing)

print()
print("=" * 78)
print("side by side: my mod vs a user mod the game keeps enabled")
print("=" * 78)
mine = [m for m in s["Mods"] if "aoe2mod" in str(m.get("Path", "")).lower()]
theirs = [m for m in s["Mods"] if m.get("Enabled") is True]
if mine and theirs:
    a, b = mine[0], theirs[0]
    keys = sorted(set(a) | set(b))
    print("  %-18s | %-34s | %s" % ("key", "MINE (" + str(a.get("Enabled")) + ")",
                                    "THEIRS (" + str(b.get("Enabled")) + ")"))
    print("  " + "-" * 74)
    for k in keys:
        va, vb = a.get(k, "<absent>"), b.get(k, "<absent>")
        va = str(va)[:32]
        vb = str(vb)[:32]
        flag = "  <== differs" if a.get(k) != b.get(k) else ""
        print("  %-18s | %-34s | %s%s" % (k, va, vb, flag))

if os.path.isfile(BAK):
    print()
    print("=" * 78)
    print("the .bak (written by ME, before the game rewrote it)")
    print("=" * 78)
    b = json.loads(open(BAK, encoding="utf-8", errors="replace").read(),
                   strict=False)
    print("  %d bytes, %d mods" % (os.path.getsize(BAK), len(b.get("Mods", []))))
    for m in b.get("Mods", []):
        print("    prio %-3s enabled=%-5s %s" % (m.get("Priority"),
                                                 m.get("Enabled"),
                                                 str(m.get("Title"))[:50]))
    print("  my mod present in the .bak: %s"
          % any("aoe2mod" in str(m.get("Path", "")).lower()
                for m in b.get("Mods", [])))
