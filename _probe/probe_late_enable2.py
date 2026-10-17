# -*- coding: utf-8 -*-
"""The late-enable region, with rlink noise removed.

The log is dominated by `[rlink - error] curl_easy_setop failed` spam (one line
plus a blank line per timestamp), which hides the actual sequence.  Filter it
and print what is really around the late enable.
"""
import os
import re

LOGS = r"C:\Users\26913\Games\Age of Empires 2 DE\logs"
SESSIONS = ["2026.10.14-2339.53", "2026.10.14-2330.11", "2026.10.14-1705.28"]

NOISE = re.compile(r"rlink - error|^\s*$")


def clean(path):
    out = []
    for i, ln in enumerate(open(path, encoding="utf-8",
                                errors="replace").read().splitlines()):
        if NOISE.search(ln):
            continue
        out.append((i + 1, ln.rstrip()))
    return out


for sess in SESSIONS:
    p = os.path.join(LOGS, sess, "MainLog.txt")
    if not os.path.isfile(p):
        continue
    rows = clean(p)
    print()
    print("=" * 78)
    print("%s   (%d real lines after removing rlink noise)" % (sess, len(rows)))
    print("=" * 78)
    # find the late enable
    idx = None
    for n, (orig, ln) in enumerate(rows):
        if "Enabling mod #" in ln and "aoe2mod" in ln:
            idx = n
            break
    if idx is None:
        print("   no aoe2mod enable line found")
        continue
    print("--- 12 real lines BEFORE and 20 AFTER the first aoe2mod enable ---")
    for n in range(max(0, idx - 12), min(len(rows), idx + 21)):
        orig, ln = rows[n]
        mark = "  <<<" if "aoe2mod" in ln else ""
        print("  raw%-5d %s%s" % (orig, ln[:120], mark))
