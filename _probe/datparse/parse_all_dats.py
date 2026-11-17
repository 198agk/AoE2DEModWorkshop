# -*- coding: utf-8 -*-
"""parse_all_dats.py -- run the UNMODIFIED proven parser over every real .dat
on disk (base game, Pompeii mode, and all three mod datasets in the profile).

Purpose: the goal statement is "verify full-parse feasibility".  Parsing only
the base game file does not test that -- the mod files are produced by
third-party tools and are the actual input our tool must consume.  This script
tests each one and reports exact-EOF / leftover independently, with no
file-specific special casing.

Writes nothing except stdout.
"""
import os
import os as _os, sys as _sys
_p = _os.path.dirname(_os.path.abspath(__file__))
while _p and not _os.path.isfile(_os.path.join(_p, "_gamepaths.py")):
    _p = _os.path.dirname(_p)
if _p and _p not in _sys.path:
    _sys.path.insert(0, _p)
import _gamepaths as GP
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import parse_dat  # noqa: E402

GAME = GP.GAME
PROF = GP.PROFILE

TARGETS = []


def add(tag, path):
    if os.path.isfile(path):
        TARGETS.append((tag, path))


# --- base game ------------------------------------------------------------
add("BASE", os.path.join(GAME, r"resources\_common\dat\empires2_x2_p1.dat"))
# --- first-party mode (Return of Rome / AoE1 data -- different version!) ---
add("MODE_Pompeii", os.path.join(GAME, r"modes\Pompeii\resources\_common\dat\empires2_x2_p1.dat"))
# --- third-party mod datasets in the user profile -------------------------
SUB = GP.SUBSCRIBED
if os.path.isdir(SUB):
    for d in sorted(os.listdir(SUB)):
        cand = os.path.join(SUB, d, r"resources\_common\dat\empires2_x2_p1.dat")
        add("MOD_" + d[:40], cand)


def main():
    print("=" * 78)
    print("FULL-PARSE FEASIBILITY: unmodified parse_dat.Parser over every real .dat")
    print("=" * 78)
    print("targets found: %d" % len(TARGETS))
    print("")

    rows = []
    for tag, path in TARGETS:
        print("-" * 78)
        print("%s" % tag)
        print("  path : %s" % path)
        print("  disk : %d bytes" % os.path.getsize(path))
        t0 = time.time()
        try:
            data, how = parse_dat.load_dat(path)
        except Exception as e:                                   # noqa: BLE001
            print("  LOAD FAILED: %s: %s" % (type(e).__name__, e))
            rows.append((tag, "LOAD-FAIL", os.path.getsize(path), None, None, None))
            continue
        td = time.time() - t0
        print("  container : %s" % how)
        print("  raw size  : %d bytes  (%.2f s)" % (len(data), td))
        print("  first 8   : %r" % data[:8])

        p = parse_dat.Parser(data)
        t1 = time.time()
        try:
            st = p.parse()
        except Exception as e:                                   # noqa: BLE001
            off = p.r.pos
            print("  !!! PARSE FAILED at offset %d (0x%X): %s: %s"
                  % (off, off, type(e).__name__, e))
            ctx = data[max(0, off - 12):off + 12]
            print("      bytes: %s" % " ".join("%02x" % b for b in ctx))
            rows.append((tag, "PARSE-FAIL", len(data), off, None, st if 'st' in dir() else None))
            continue
        tp = time.time() - t1
        final = p.r.pos
        total = len(data)
        leftover = total - final
        ok = (final == total)
        print("  ---")
        print("  file_version : %r" % st.get("file_version"))
        print("  civs=%d techs=%d effects=%d unit_headers=%d graphics=%d"
              % (st["civ_count"], st["tech_count"], st["effect_count"],
                 st["unit_header_count"], st["graphic_count"]))
        print("  final offset : %d" % final)
        print("  data size    : %d" % total)
        print("  EXACT EOF    : %s   leftover=%d" % ("YES" if ok else "NO", leftover))
        print("  parse time   : %.2f s" % tp)
        n_units = sum(len(c.get("units", [])) for c in st["civs"])
        print("  unit objects : %d" % n_units)
        rows.append((tag, "OK" if ok else "MISMATCH", total, final, leftover, st))

    print("")
    print("=" * 78)
    print("SUMMARY")
    print("=" * 78)
    print("%-42s %-10s %12s %12s %10s" % ("target", "status", "size", "final", "leftover"))
    for tag, status, total, final, leftover, _st in rows:
        print("%-42s %-10s %12s %12s %10s"
              % (tag[:42], status,
                 total if total is not None else "-",
                 final if final is not None else "-",
                 leftover if leftover is not None else "-"))

    okn = sum(1 for r in rows if r[1] == "OK")
    print("")
    print("EXACT-EOF PARSE: %d / %d" % (okn, len(rows)))


if __name__ == "__main__":
    main()
