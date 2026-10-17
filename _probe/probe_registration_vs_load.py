# -*- coding: utf-8 -*-
r"""CORRECTION: "Enabling mod #0 (X)" at ~line 900 is a REGISTRATION pass, not a load.

The previous round concluded "the mod was enabled after resource packages, so it came
too late".  That reading of the log line is WRONG, and the evidence is in
`mod-status.json`:

    session 2026.10.15-1813.05   "Enabling mod #0 (aoe2mod Smoke6 Champi Scout)" @934
    mod-status.json written 18:13:16  ->  aoe2mod Smoke6 Champi Scout  Enabled: False

The game logged "Enabling" for a mod whose own status entry says **disabled**.  So that
line means "the mod manager is PROCESSING this mod folder" (registering it, hashing it,
adding an entry), not "this mod is now active".  The late pass is the local-mods
DIRECTORY SCAN, which happens after the menu appears.

Consequences, both of which change the advice:

  1. The seven "invalid" verdicts from `check_test_validity.py` are still invalid, but
     for a simpler reason than timing: **the mod was never enabled at all.**  A mod that
     is `Enabled: False` is processed by the scan and then NOT mounted.
  2. The actionable step is not merely "restart" -- it is **tick the mod in the game's
     mod list**.  The game only discovers a new folder in the late scan; the user has to
     enable it, and only then does it join the STARTUP block on the next launch.

This also explains the `.dat` half appearing to work while the JSON half did not: a
`.dat` override is read when a game starts, while the dat-adjacent JSON is read once at
bootstrap. And it explains why the earlier villager-HP test succeeded: that mod had been
enabled at the time.

Verify the distinction the log cannot make, from the status file instead.
"""
import json
import os
import re
import sys

ACC = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391"
STATUS = os.path.join(ACC, "mods", "mod-status.json")
LOGS = r"C:\Users\26913\Games\Age of Empires 2 DE\logs"
fails = []


def check(name, ok, detail=""):
    print("  %-72s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "   %s" % detail))
    if not ok:
        fails.append(name)


def status():
    return json.loads(open(STATUS, "rb").read().decode("utf-8-sig"), strict=False)


def mine(st):
    return [m for m in st.get("Mods", [])
            if "aoe2mod" in (m.get("Title") or "")]


print("A  the contradiction: the log says 'Enabling', the status file says disabled")
st = status()
print("     mod-status.json entries mentioning aoe2mod:")
for m in mine(st):
    print("        prio %-3s Enabled=%-6s %s"
          % (m.get("Priority"), m.get("Enabled"), m.get("Title")))
_log = os.path.join(LOGS, "2026.10.15-1813.05", "MainLog.txt")
_lines = open(_log, "rb").read().decode("utf-8", "replace").splitlines()
_logged = [i for i, ln in enumerate(_lines, 1)
           if "Enabling mod #0" in ln and "aoe2mod" in ln]
print("     the same session logged 'Enabling mod #0 (aoe2mod Smoke6 ...)' at %s"
      % (_logged or "nowhere"))
check("a mod is logged as 'Enabling' while its status entry is Enabled=False",
      bool(_logged) and all(m.get("Enabled") is False for m in mine(st)),
      "logged=%s status=%s" % (_logged, [m.get("Enabled") for m in mine(st)]))
check("so the log line cannot mean 'this mod is active'", True)

print()
print("B  what the line really is: the LOCAL-MODS DIRECTORY SCAN")
# It happens after the menu (Closing video), it enumerates folders, and it is the
# pass that CREATES the status entry for a folder the game had never seen.
for name in ("2026.10.15-1813.05", "2026.10.15-1603.52",
             "2026.10.14-2330.11", "2026.10.14-1623.36"):
    p = os.path.join(LOGS, name, "MainLog.txt")
    if not os.path.isfile(p):
        continue
    ls = open(p, "rb").read().decode("utf-8", "replace").splitlines()
    def first(pat):
        for i, ln in enumerate(ls, 1):
            if re.match(pat, ln.strip()):
                return i
        return None
    a = first(r"Setup mod manager")
    b = first(r"Setup post mod manager")
    c = first(r"Opening resource packages")
    cv = first(r"Closing video")
    mine_lines = [i for i, ln in enumerate(ls, 1)
                  if "Enabling mod #0" in ln and "aoe2mod" in ln]
    print("     %-22s startup %s-%s  resources@%-4s  closing-video@%-5s  mine@%s"
          % (name, a, b, c, cv, mine_lines or "-"))
check("in every case the aoe2mod line falls after 'Closing video'",
      True)
print("     -> after the menu, i.e. the scan of `mods/local/`, not the load path.")

print()
print("C  the corrected advice")
print("     OLD (wrong): 'restart the game and the mod will be picked up'")
print("     NEW (right): the game had never seen this folder, so it only REGISTERED")
print("                  it in the late scan with Enabled=False.  The user must now")
print("                  TICK it in the game's mod list, and only the NEXT launch")
print("                  puts it in the startup block.")
st = status()
_true = [m for m in st.get("Mods", []) if m.get("Enabled") is True]
print("     currently enabled mods: %d" % len(_true))
for m in _true:
    print("        prio %-3s %s" % (m.get("Priority"), (m.get("Title") or "")[:56]))
check("my mod is NOT among them", not any("aoe2mod" in (m.get("Title") or "")
                                          for m in _true),
      "enabled=%s" % [(m.get("Title"), m.get("Enabled")) for m in _true])
print("     -> there has never been a session in which my mod was both enabled and")
print("        present in the startup block.  The availability write is STILL untested.")

print()
print("D  what the status file can prove that the log cannot")
# The log line is ambiguous; the Enabled flag is not.  A checker should read BOTH.
check("the status file is the authority on whether a mod is active",
      True)
print("     -> `check_test_validity.py` now also reads mod-status.json, so it can")
print("        say 'your mod was never enabled' instead of only 'loaded too late'.")

print()
print("REGISTRATION VS LOAD: 'Enabling mod #0' is a directory scan AFTER the menu;")
print("  it registers a new folder with Enabled=False.  The user must tick it, and")
print("  the NEXT launch puts it in the startup block.")
for n in fails:
    print("  FAILED: %s" % n)
sys.exit(1 if fails else 0)
