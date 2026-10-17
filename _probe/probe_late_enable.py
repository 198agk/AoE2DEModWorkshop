# -*- coding: utf-8 -*-
"""What TRIGGERS the mid-session mod enable, and does the .dat still work?

In every one of my sessions the mod is enabled at line ~866-976, long after
`post mod manager` (~line 251).  Yet the .dat half DID take effect in game
(Villager HP 1000).  So the .dat must be read later still -- at match start --
which would explain why a mid-session enable can reach it but not the UI layers.

This prints the event lines bracketing each late enable, so the trigger is
identified from the log rather than guessed.
"""
import os
import re

LOGS = r"C:\Users\26913\Games\Age of Empires 2 DE\logs"
SESSION = "2026.10.14-2339.53"      # the session where .dat took effect

# Lines that name a phase we care about.
PAT = re.compile(
    r"(Enabling mod #|Setup mod manager|post mod manager|Opening resource|"
    r"resource packages|Loading player profile|Setting up hotkeys|"
    r"Starting game|game start|skirmish|Skirmish|Match|match|"
    r"Loading scenario|scenario|Create game|setup game|Game::setup|"
    r"map|Map|Play|start game|Launch|launch|profile|Profile)", re.I)

lines = open(os.path.join(LOGS, SESSION, "MainLog.txt"),
             encoding="utf-8", errors="replace").read().splitlines()

print("=" * 78)
print("session %s -- %d lines" % (SESSION, len(lines)))
print("=" * 78)

print()
print("--- the late enable region, verbatim (lines 855..945) ---")
for i in range(854, min(945, len(lines))):
    ln = lines[i]
    mark = "  <<<" if ("Enabling mod #" in ln) else ""
    print("  %4d  %s%s" % (i + 1, ln[:150], mark))

print()
print("--- every event line AFTER the enable, until the log ends ---")
late = [i for i, ln in enumerate(lines) if "Enabling mod #" in ln]
if late:
    start = late[0]
    for i in range(start, len(lines)):
        ln = lines[i].strip()
        if not ln:
            continue
        # print the interesting ones plus a tail sample
        if re.search(r"(game|Game|match|Match|scenario|map|Map|exit|Exit"
                     r"|terminat|Terminat|player|Player|error|Error"
                     r"|fail|Fail|resource|Resource|profile|Profile)", ln):
            print("  %4d  %s" % (i + 1, ln[:150]))

print()
print("=" * 78)
print("VERDICT INPUTS")
print("=" * 78)
for i, ln in enumerate(lines):
    if "Enabling mod #" in ln:
        print("  first mod enable at line %d" % (i + 1))
        break
for i, ln in enumerate(lines):
    if re.search(r"Exiting with code", ln):
        print("  game exits at line %d: %s" % (i + 1, ln.strip()[:80]))
        break
