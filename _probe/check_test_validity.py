# -*- coding: utf-8 -*-
r"""Was the last game session a VALID test of a mod?  Answer it from the log.

Every one of this project's seven in-game tests was structurally incapable of
showing an availability write, because the mod was enabled AFTER
"Opening resource packages" (`_probe/test_mod_load_timing.py`).  Nothing in the
game UI tells the user that, and the symptom is indistinguishable from "the mod is
wrong": the `.dat` half renders and the JSON half silently does nothing.

This tool closes that loop.  Run it after a session and it says, in one line,
whether the mod under test was loaded EARLY ENOUGH for its JSON layers to be read.

    python _probe\check_test_validity.py                 # newest session
    python _probe\check_test_validity.py --mod smoke6    # filter by substring

Exit code is 0 when the test was valid, 1 when it was not, so a caller can gate on
it.  "No session found" is exit 2 -- distinct from "invalid", because a missing log
is not evidence about the mod.
"""
import argparse
import os
import re
import sys

LOGS = r"C:\Users\26913\Games\Age of Empires 2 DE\logs"
STATUS = (r"C:\Users\26913\Games\Age of Empires 2 DE"
          r"\76561198406248391\mods\mod-status.json")

# Phase markers, in bootstrap order.  A mod enabled before "Setup post mod manager"
# is in the startup block; one enabled after "Opening resource packages" came too
# late for the dat storage point.
PHASES = ("Initializing Mod Manager", "Setup mod manager", "Setup post mod manager",
          "Opening resource packages", "Running Game", "Closing video",
          "Terminating Mod Manager")


def enabled_in_status(needle):
    """Is any mod whose Title contains `needle` actually ENABLED?

    The log cannot answer this and is actively misleading: it prints
    "Enabling mod #0 (X)" during the LATE local-mods directory scan for a mod whose
    own status entry says ``Enabled: false``.  Measured: session 2026.10.15-1813.05
    logged that line for `aoe2mod Smoke6 Champi Scout` while `mod-status.json`
    (written 18:13:16, the same session) had it disabled.  So the status file is the
    authority, and without reading it a checker will blame TIMING when the real
    answer is "the mod was never on".
    """
    try:
        import json
        st = json.loads(open(STATUS, "rb").read().decode("utf-8-sig"),
                        strict=False)
    except Exception:
        return None
    for m in st.get("Mods", []):
        if needle.lower() in (m.get("Title") or "").lower() and m.get("Enabled"):
            return m
    return False


def sessions(newest_first=True):
    if not os.path.isdir(LOGS):
        return []
    out = []
    for d in os.listdir(LOGS):
        p = os.path.join(LOGS, d, "MainLog.txt")
        if os.path.isfile(p):
            out.append((d, p, os.path.getmtime(p)))
    out.sort(key=lambda t: t[2], reverse=newest_first)
    return out


def analyse(path, needle):
    lines = open(path, "rb").read().decode("utf-8", "replace").splitlines()
    phase = {}
    for i, ln in enumerate(lines, 1):
        s = ln.strip()
        for p in PHASES:
            if s == p and p not in phase:
                phase[p] = i
    enabled = [(i, ln.strip()) for i, ln in enumerate(lines, 1)
               if "Enabling mod #0" in ln and needle.lower() in ln.lower()]
    startup_block = None
    if "Setup mod manager" in phase and "Setup post mod manager" in phase:
        startup_block = (phase["Setup mod manager"], phase["Setup post mod manager"])
    return {"lines": len(lines), "phase": phase, "enabled": enabled,
            "startup_block": startup_block, "needle": needle}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mod", default="aoe2mod",
                    help="substring of the mod title to look for")
    ap.add_argument("--session", default=None,
                    help="a specific log directory name")
    ap.add_argument("--all", action="store_true",
                    help="check every session that mentions the mod")
    args = ap.parse_args()

    if args.session:
        p = os.path.join(LOGS, args.session, "MainLog.txt")
        if not os.path.isfile(p):
            print("no such session: %s" % args.session)
            return 2
        cands = [(args.session, p, 0)]
    else:
        cands = [t for t in sessions()
                 if args.all or "Enabling mod #0" in
                 open(t[1], "rb").read().decode("utf-8", "replace")]

    if not cands:
        print("no game session log found under %s" % LOGS)
        return 2

    verdicts = []
    for name, path, _m in (cands if args.all else cands[:1]):
        r = analyse(path, args.mod)
        print("=" * 76)
        print("session %s   (%d lines)" % (name, r["lines"]))
        print("-" * 76)
        for p in PHASES:
            if p in r["phase"]:
                print("   line %-6d %s" % (r["phase"][p], p))
        print()
        if not r["enabled"]:
            print("   the mod %r never appears in this session" % args.mod)
            verdicts.append((name, None))
            continue
        first = r["enabled"][0][0]
        print("   mod %r appears at line %s" % (args.mod,
                                                 ", ".join(str(i) for i, _ in r["enabled"])))
        _on = enabled_in_status(args.mod)
        if _on is False:
            print("   VERDICT: INVALID -- NO mod matching %r is ENABLED." % args.mod)
            print("            `mod-status.json` says Enabled=false for every such mod.")
            print("            The log's 'Enabling mod #0 (...)' line is the late")
            print("            local-mods DIRECTORY SCAN (it runs after the menu),")
            print("            which REGISTERS a new folder but does not turn it on.")
            print("            -> tick the mod in the game's mod list; only the NEXT")
            print("               launch puts it in the startup enable block.")
            verdicts.append((name, False))
            continue
        if _on:
            print("   mod-status.json: ENABLED (prio %s)" % _on.get("Priority"))
        blk = r["startup_block"]
        res = r["phase"].get("Opening resource packages")
        if blk and blk[0] < first < blk[1]:
            print("   VERDICT: VALID -- it is inside the STARTUP enable block "
                  "(lines %d-%d)" % blk)
            print("            the engine read resources AFTER this, so the JSON "
                  "layers of this mod were")
            print("            in place when they were consulted.")
            verdicts.append((name, True))
        elif res is not None and first > res:
            print("   VERDICT: INVALID -- it appears at line %d, but resource "
                  "packages opened at line %d." % (first, res))
            print("            The `.dat` half may still render (a new game reloads "
                  "game data), while the")
            print("            dat-adjacent JSON half is read at startup and was "
                  "NOT in place.")
            print("            -> quit the game completely and relaunch, so the mod "
                  "appears in the")
            print("               startup enable block, then test again.")
            verdicts.append((name, False))
        else:
            print("   VERDICT: UNCLEAR -- the mod appears at line %d and no "
                  "resource-packages marker was found." % first)
            verdicts.append((name, None))

    if args.all:
        print()
        print("=" * 76)
        ok = sum(1 for _n, v in verdicts if v is True)
        bad = sum(1 for _n, v in verdicts if v is False)
        unk = sum(1 for _n, v in verdicts if v is None)
        print("SUMMARY: %d valid, %d invalid, %d unclear, over %d session(s)"
              % (ok, bad, unk, len(verdicts)))

    _last = verdicts[-1][1] if verdicts else None
    print()
    print("TEST VALIDITY: %s" % {True: "VALID", False: "INVALID",
                                  None: "UNCLEAR"}[_last])
    return 0 if _last is True else (1 if _last is False else 2)


if __name__ == "__main__":
    sys.exit(main())
