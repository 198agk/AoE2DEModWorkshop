# -*- coding: utf-8 -*-
r"""After an in-game run: did the game enable the v10 mod, and how?

Reads every log directory under the profile, finds `Enabling mod #0 (...)` lines,
and reports whether `dsh test v10` was among them -- and in which phase (startup
vs mid-session).  This is the same evidence format that caught the 100-byte Title
truncation and the "enabled mid-session" surprise.

Usage:  python _probe/check_v10_load.py
"""
import os
import re
import sys

PROFILE = r"C:\Users\26913\Games\Age of Empires 2 DE"
LOGS = os.path.join(PROFILE, "logs")
WANT = "dsh test v10"

ENABLE = re.compile(r"Enabling mod #\d+ \((.*)\)")
STARTUP_END = re.compile(r"Setup post mod manager|Opening resource packages")


def read_text(path):
    try:
        with open(path, "rb") as f:
            return f.read().decode("utf-8", "replace")
    except OSError:
        return ""


def main():
    if not os.path.isdir(LOGS):
        print("no logs directory: %s" % LOGS)
        return 2
    dirs = sorted((d for d in os.listdir(LOGS)
                   if os.path.isdir(os.path.join(LOGS, d))))
    print("log sessions: %d" % len(dirs))
    print()

    hits = []
    for d in dirs:
        base = os.path.join(LOGS, d)
        for fn in ("MainLog.txt", "Main.txt"):
            p = os.path.join(base, fn)
            if not os.path.exists(p):
                continue
            txt = read_text(p)
            if not txt:
                continue
            mods = []
            startup_end = None
            for i, line in enumerate(txt.splitlines(), 1):
                m = ENABLE.search(line)
                if m:
                    mods.append((i, m.group(1)))
                if startup_end is None and STARTUP_END.search(line):
                    startup_end = i
            if not mods:
                continue
            mine = [(i, t) for i, t in mods if WANT in t]
            if not mine:
                continue
            phase = []
            for i, t in mine:
                if startup_end is None:
                    phase.append((i, t, "startup? (no marker)"))
                elif i < startup_end:
                    phase.append((i, t, "STARTUP (before line %d)" % startup_end))
                else:
                    phase.append((i, t, "MID-SESSION (after line %d)" % startup_end))
            hits.append((d, fn, phase, len(mods)))
            print("%s / %s   (%d Enabling lines)" % (d, fn, len(mods)))
            for i, t, ph in phase:
                print("   line %-5d %s" % (i, ph))
                print("             %r" % t)
            print()

    if not hits:
        print("RESULT: `%s` was NEVER enabled in any logged session." % WANT)
        print("        Either the mod was not ticked in the mod manager, or the")
        print("        game rejected it before logging (check the Title length).")
        return 1

    print("RESULT: `%s` appears in %d session(s)." % (WANT, len(hits)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
