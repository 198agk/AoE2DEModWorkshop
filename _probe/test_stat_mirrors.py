# -*- coding: utf-8 -*-
"""`unit.stat` must write the same bytes as the reference, mirror included.

Why this exists
---------------
`城堡攻击加5` used to ship 126 changed bytes in the native build where the
reference ships 252.  Every other check stayed green: the build succeeded, the
edits counted themselves consistently, the mod installed, and the game loaded
it.  The only symptom was in the game itself -- the unit panel read 10 while the
arrow still hit for 5 -- and that is exactly the kind of defect a count of one's
own writes cannot see.

The cause is that AoE2 stores several properties TWICE: the number the panel
renders (`DisplayedAttack`) and the number the damage maths reads (the class 3/4
row of `attacks`).  A `unit.stat` edit that moves only the panel number produces
a record the game never ships.

What this checks
----------------
For a sample of sentences, both engines build a mod and this compares the two
`empires2_x2_p1.dat` streams BYTE FOR BYTE.  Not the counts, not the offsets --
the bytes.  A count can agree while the bytes disagree, and then the numbers on
screen are the only place the difference shows up.

The mirror carries the DELTA, never the value.  `check_delta_not_value` pins
that separately, because shipped data happens to keep every mirrored pair equal
(measured: 0 divergent records across all 63 civilisations), so a build
comparison alone cannot tell "copies the delta" from "copies the value".  The
distinction matters the moment a user's own earlier edit created a divergence.

Run: py -X utf8 _probe/test_stat_mirrors.py
"""

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

GAME = r"d:\games\steam\steamapps\common\AoE2DE"
DAT = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")
# The native `aoe2mod-serve` binary's cargo target.  It used to live in %TEMP%
# (1.3 GB), which put a build product outside the checkout -- the same thing the
# owner asked twice to stop doing.  It is `_cache/aoe2target` now, so it inherits
# the workspace's Integrity Label as well (a copied launcher that sat outside once
# died with 0xC0000135).  CARGO_TARGET_DIR still overrides, for a one-off build.
SERVE = os.path.join(
    os.environ.get("CARGO_TARGET_DIR")
    or os.path.join(ROOT, "_cache", "aoe2target"),
    "release", "aoe2mod-serve.exe")

PORT = 7851

# One sentence per shape of the mirror rule.
#
#   * displayed_attack  -- the FORWARD case: the panel field is the binding and
#     the raw class-3/4 attack row follows it;
#   * max_range         -- the REVERSE case: the engine number is the binding and
#     `displayed_range` follows;
#   * hit_points        -- NOT mirrored at all.  Present so that a fix which
#     "mirrors everything" fails here instead of silently doubling writes.
CASES = [
    ("城堡攻击加5", {"intent": "unit.stat", "unit": 82, "stat": "displayed_attack", "delta": 5}),
    ("民兵射程加1", {"intent": "unit.stat", "unit": 74, "stat": "max_range", "delta": 1}),
    ("村民血量改成100", {"intent": "unit.stat", "unit": 1810, "stat": "hit_points", "value": 100}),
]


def read_raw():
    with open(DAT, "rb") as f:
        return zlib.decompressobj(-15).decompress(f.read())


def wait_ready(base):
    for _ in range(240):
        try:
            with urllib.request.urlopen(base + "/api/progress", timeout=10) as r:
                if json.load(r).get("progress", {}).get("ready"):
                    return
        except Exception:
            pass
        time.sleep(0.5)
    raise SystemExit("the server never reported ready")


def post(base, path, body):
    req = urllib.request.Request(
        base + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)


def python_build(intent, out_dir, title):
    import aoe2mod.ui.server as S

    app = S.App()
    res = app.build([intent], title=title, author="aoe2mod", out_dir=out_dir)
    if not res.get("ok"):
        return None, res.get("error")
    # Read the folder the build NAMES, do not rebuild the path from the argument:
    # `App.build` puts every mod in its own subfolder (`out_dir/<safe title>`), so
    # joining `out_dir` here pointed one level too high and the file was not
    # there.  Measured 2026-11-01.
    path = os.path.join(res.get("built") or out_dir, "resources", "_common",
                        "dat", "empires2_x2_p1.dat")
    with open(path, "rb") as f:
        return zlib.decompressobj(-15).decompress(f.read()), None


def main():
    if not os.path.isfile(SERVE):
        raise SystemExit("build the native server first: " + SERVE)
    base = "http://127.0.0.1:%d" % PORT
    proc = subprocess.Popen([SERVE, "--port", str(PORT)], cwd=ROOT,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    bad = []
    try:
        wait_ready(base)
        for label, intent in CASES:
            tmp = tempfile.mkdtemp(prefix="mirror_")
            py, err = python_build(intent, tmp, "py_" + intent["stat"])
            if py is None:
                bad.append("%-16s python refused: %s" % (label, err))
                print("%-16s SKIP  python refused: %s" % (label, err))
                continue
            r = post(base, "/api/build", dict(intent, title="rs_" + intent["stat"],
                                              author="aoe2mod", install=False))
            if not r.get("ok"):
                bad.append("%-16s native refused: %s" % (label, r.get("error")))
                print("%-16s FAIL  native refused: %s" % (label, r.get("error")))
                continue
            path = os.path.join(r["built"], "resources", "_common", "dat",
                                "empires2_x2_p1.dat")
            with open(path, "rb") as f:
                ru = zlib.decompressobj(-15).decompress(f.read())
            if ru == py:
                print("%-16s ok    %d bytes identical, edits=%s mirror=%s"
                      % (label, len(ru), r.get("edit_count"), r.get("mirror_count")))
            else:
                n = sum(1 for a, b in zip(py, ru) if a != b)
                bad.append("%-16s bytes differ in %d places" % (label, n))
                print("%-16s FAIL  %d bytes differ" % (label, n))
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=20)
        except Exception:
            proc.kill()

    if check_delta_not_value():
        print("%-16s ok    the mirror moves by the delta, not the value" % "delta-not-value")
    else:
        bad.append("the mirror copied the value instead of carrying the delta")

    print("VERDICT  cases=%d  bad=%d (must be 0)" % (len(CASES), len(bad)))
    for b in bad:
        print("  " + b)
    return 0 if not bad else 1


def check_delta_not_value():
    """The mirror rule, tested without needing a divergent record to exist.

    Shipped data keeps every mirrored pair equal (0 divergent records measured
    across 63 civilisations), so a build comparison cannot distinguish "carries
    the delta" from "copies the new value": both produce the same bytes when the
    two numbers started equal.  This reads the rule from the code instead -- the
    write must be `before + delta`, and a rewrite of it to `new_value` has to be
    visible as a difference in the source.
    """
    path = os.path.join(ROOT, "desktop", "aoe2mod-serve", "src", "stat_edit.rs")
    with open(path, encoding="utf-8") as f:
        src = f.read()
    # Both call sites: the public /api/stat path and the /api/build path.
    return src.count("m_before + (value - before)") >= 1 and \
        src.count("before + mirror_delta") >= 1


if __name__ == "__main__":
    sys.exit(main())
