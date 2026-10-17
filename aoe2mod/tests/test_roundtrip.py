# -*- coding: utf-8 -*-
"""Prove the vendored engine is still byte-exact.

This is the load-bearing test: if the package's parser+writer no longer
round-trip the real game data byte-for-byte, nothing built on top of it can be
trusted.  It runs against every dataset the research phase used.
"""
import contextlib
import hashlib
import io
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.dat import parser as P
from aoe2mod.dat import writer as W

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
MODS = (r"C:\Users\26913\Games\Age of Empires 2 DE"
        r"\76561198406248391\mods\subscribed")


def mod_dat(workshop_id):
    """Resolve a subscribed mod's .dat by its Workshop id PREFIX.

    The folder is `<WorkshopID>_<Title>` and the Title carries a version the
    author bumps between releases ('... v48' became '... v50'), so pinning the
    full name makes the suite fail on someone else's rename.  The id never
    changes; match on that.
    """
    if not os.path.isdir(MODS):
        return os.path.join(MODS, workshop_id + "_<missing>",
                            "resources", "_common", "dat", "empires2_x2_p1.dat")
    hits = [d for d in os.listdir(MODS)
            if d.startswith(workshop_id + "_") and os.path.isdir(os.path.join(MODS, d))]
    if not hits:
        return os.path.join(MODS, workshop_id + "_<not-installed>",
                            "resources", "_common", "dat", "empires2_x2_p1.dat")
    return os.path.join(MODS, sorted(hits)[0],
                        "resources", "_common", "dat", "empires2_x2_p1.dat")


TARGETS = [
    ("BASE", os.path.join(GAME, "resources", "_common", "dat",
                          "empires2_x2_p1.dat")),
    ("MODE_Pompeii", os.path.join(GAME, "modes", "Pompeii", "resources",
                                  "_common", "dat", "empires2_x2_p1.dat")),
    ("MOD_297820", mod_dat("297820")),
    ("MOD_423821", mod_dat("423821")),
    ("MOD_550749", mod_dat("550749")),
]

COUNTERS = ["civs", "unit_objects", "techs", "effects", "graphics",
            "sounds", "unit_headers", "terrains"]


def one(name, path):
    if not os.path.exists(path):
        print("  %-13s MISSING %s" % (name, path))
        return False
    raw, how = P.load_dat(path)
    p = P.Parser(raw)
    with contextlib.redirect_stdout(io.StringIO()):
        st = p.parse()
    leftover = len(raw) - p.r.pos

    out, rep = W.serialize_dat(st, raw=raw, strict=True)
    delta = len(out) - len(raw)

    # reparse the writer's output with the UNMODIFIED parser
    (out2, _) = (out, None)
    p2 = P.Parser(out)
    with contextlib.redirect_stdout(io.StringIO()):
        st2 = p2.parse()
    left2 = len(out) - p2.r.pos

    # second serialize must be identical (idempotence)
    out3, _ = W.serialize_dat(st2, raw=out, strict=True)

    same = (out == raw)
    ok = (leftover == 0 and delta == 0 and rep["model_vs_original_mismatches"] == 0
          and left2 == 0 and out3 == out and same)
    fv = st["file_version"]
    if isinstance(fv, (bytes, bytearray)):
        fv = fv.decode("latin-1")
    fv = str(fv).strip("\x00").strip()
    print("  %-13s %-8s left %d  raw %-10d delta %+d  mis %-3d  L1 %-5s L2 %-5s  %s"
          % (name, fv, leftover, len(raw), delta,
             rep["model_vs_original_mismatches"], left2 == 0, out3 == out,
             "ok" if ok else "FAIL"))
    print("                sha256 %s" % hashlib.sha256(out).hexdigest()[:32])
    return ok


def main():
    print("=" * 78)
    print("VENDORED ENGINE ROUND-TRIP  (aoe2mod.dat.parser + aoe2mod.dat.writer)")
    print("=" * 78)
    t0 = time.time()
    results = [(n, one(n, p)) for n, p in TARGETS]
    print("-" * 78)
    good = sum(1 for _, v in results if v)
    print("BYTE-EXACT ROUND-TRIP: %d / %d   (%.1f s)"
          % (good, len(results), time.time() - t0))
    for n, v in results:
        if not v:
            print("   FAILED: %s" % n)
    return 0 if good == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
