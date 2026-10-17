# -*- coding: utf-8 -*-
"""Run the byte-exact round-trip check across every .dat in the survey set.

The verifier proves one file at a time; a version-aware writer could still be
wrong for the DE datasets whose record set differs (more civs, appended units).
This drives the same parse -> serialize -> compare -> reserialize pipeline for
all of them and prints a single table, so "round-trips everywhere" is a measured
claim rather than an extrapolation from two samples.
"""
import hashlib
import io
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROBE = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(PROBE, "datparse"))

import parse_dat
import write_dat

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
USERMODS = (r"C:\Users\26913\Games\Age of Empires 2 DE"
            r"\76561198406248391\mods\subscribed")

TARGETS = [
    ("BASE", os.path.join(GAME, r"resources\_common\dat\empires2_x2_p1.dat")),
    ("MODE_Pompeii", os.path.join(
        GAME, r"modes\Pompeii\resources\_common\dat\empires2_x2_p1.dat")),
    ("MOD_297820", os.path.join(
        USERMODS, "297820_10 倍资源文明联盟3倍科技",
        r"resources\_common\dat\empires2_x2_p1.dat")),
    ("MOD_423821", os.path.join(
        USERMODS, "423821_四月-juntuanzhangtianfumozu军团长天赋模组",
        r"resources\_common\dat\empires2_x2_p1.dat")),
    ("MOD_550749", os.path.join(
        USERMODS, "550749_{2026}10倍资源文明联盟2倍科技 北欧dlc可用 v48",
        r"resources\_common\dat\empires2_x2_p1.dat")),
]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def one(name, path):
    row = {"name": name, "path": path}
    if not os.path.isfile(path):
        row["status"] = "MISSING"
        return row
    raw, how = parse_dat.load_dat(path)
    row["raw"] = len(raw)
    p = parse_dat.Parser(bytearray(raw))
    st1 = p.parse()
    fv = st1.get("file_version") or ""
    if isinstance(fv, (bytes, bytearray)):
        fv = fv.decode("latin-1")
    row["ver"] = fv.strip()
    row["leftover"] = len(raw) - p.r.pos

    t0 = time.time()
    out1, rep1 = write_dat.serialize_dat(st1, raw=raw, strict=True)
    row["out1"] = len(out1)
    row["delta"] = len(out1) - len(raw)
    row["mis1"] = rep1["model_vs_original_mismatches"]
    row["same1"] = (out1 == raw)

    # loop 2: idempotence
    p2 = parse_dat.Parser(bytearray(out1))
    st2 = p2.parse()
    out2, rep2 = write_dat.serialize_dat(st2, raw=out1, strict=True)
    row["same2"] = (out2 == out1)
    row["mis2"] = rep2["model_vs_original_mismatches"]
    row["secs"] = time.time() - t0
    row["ok"] = (row["leftover"] == 0 and row["same1"] and row["same2"]
                 and row["mis1"] == 0 and row["mis2"] == 0)
    return row


def main():
    rows = []
    for name, path in TARGETS:
        print("=== %s ===" % name, flush=True)
        try:
            r = one(name, path)
        except Exception as e:
            r = {"name": name, "status": "ERROR", "err": "%s: %s"
                 % (type(e).__name__, e)}
        rows.append(r)
        print("   status=%s" % ("OK" if r.get("ok") else r.get("status", "FAIL")),
              flush=True)
        if r.get("err"):
            print("   %s" % r["err"], flush=True)
            import traceback
            traceback.print_exc()

    print()
    print("=" * 100)
    print("BYTE-EXACT ROUND-TRIP ACROSS ALL DATASETS")
    print("=" * 100)
    print("%-14s %-9s %6s %12s %12s %8s %6s %5s %5s %5s"
          % ("target", "ver", "left", "raw", "out1", "delta", "mis1", "L1", "L2", "ok"))
    for r in rows:
        if r.get("err"):
            print("%-14s  ERROR: %s" % (r["name"], r["err"]))
            continue
        print("%-14s %-9s %6d %12d %12d %+8d %6d %5s %5s %5s"
              % (r["name"], r.get("ver", "?"), r.get("leftover", -1),
                 r.get("raw", 0), r.get("out1", 0), r.get("delta", 0),
                 r.get("mis1", -1), r.get("same1"), r.get("same2"),
                 "YES" if r.get("ok") else "NO"))
    n_ok = sum(1 for r in rows if r.get("ok"))
    print()
    print("ROUND-TRIP BYTE-EXACT: %d / %d" % (n_ok, len(rows)))
    return 0 if n_ok == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
