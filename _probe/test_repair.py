"""`aoe2mod/repair.py` says the truth about a mod's `.dat`, on any machine.

The one-off probe (`tmp_repair_check.py`) measured five REAL community mods, and
that was worth doing -- it is how the verdicts were calibrated.  But it cannot be
a suite: it hard-codes which mods this player happens to have installed, so it
would report a failure on a machine that has different ones, for a reason that
has nothing to do with the code.

This file builds its own cases instead, from files that exist wherever the game
is installed:

  A. shipped vs shipped                      -> identical
  B. a path that is not there                -> no_dat, as data not an exception
  C. a .dat the PRODUCT built (83 HP -> 1000) -> auto, with the edit named
  D. the same bytes with the version string  -> impossible, and it says why
     rewritten from `VER 8.9` to `VER 7.8`

D is the interesting one.  A real `VER 7.8` file differs in layout, not just in
its header, so faking the header is a weaker test than the real thing -- what it
proves is the RULE that a generation mismatch outranks everything else, which is
the rule that keeps a cross-generation mod from being described as "5 easy
edits".  The real-file measurement stays in `tmp_repair_check.py` and in the
handoff notes.
"""
import io
import os
import shutil
import sys
import tempfile
import zlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aoe2mod.api as A
import aoe2mod.dat.parser as P
import aoe2mod.repair as R

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
SHIPPED = os.path.join(GAME, R.DAT_REL)

FAILS = []


def check(ok, label, detail=""):
    print(("  ok   " if ok else "  FAIL ") + label + ((" :: " + str(detail)) if detail else ""))
    if not ok:
        FAILS.append(label)
    return ok


def _w(path, blob):
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)
    with open(path, "wb") as fh:
        fh.write(blob)


def _rewrite_version(src, dst, old=b"VER 8.9", new=b"VER 7.8"):
    """Copy a .dat with its version STRING changed, offsets untouched.

    Same byte count in and out, so every offset after the header stays valid --
    which is what makes this a test of the RULE rather than of the layout.
    """
    raw, how = P.load_dat(src)
    assert len(old) == len(new), "the fake only works when the two strings match in length"
    assert raw[:len(old)] == old, "expected the shipped head to start with %r" % old
    body = new + raw[len(old):]
    co = zlib.compressobj(6, zlib.DEFLATED, -15)
    blob = co.compress(body) + co.flush()
    with io.open(dst, "wb") as fh:
        fh.write(blob)
    return len(body), len(blob)


def main():
    tmp = tempfile.mkdtemp(prefix="repair_suite_")
    try:
        print("=== A. the shipped file, compared with itself")
        got = R.check(SHIPPED, GAME)
        check(got.get("verdict") == "identical", "a file identical to the base says so",
              got.get("verdict"))
        check(got.get("ok") is True, "and it is not an error")
        check(not got.get("reasons"), "and it has nothing to warn about",
              got.get("reasons"))

        print()
        print("=== B. no .dat at all is data, not an exception")
        got = R.check(os.path.join(tmp, "nope.dat"), GAME)
        check(got.get("verdict") == "no_dat" and got.get("ok") is False,
              "a missing file is reported", got.get("verdict"))
        check(any("松散文件" in r for r in (got.get("reasons") or [])),
              "and the reason says a loose-file mod does not go stale",
              got.get("reasons"))

        print()
        print("=== C. a .dat the product itself built, so one edit exists")
        out = os.path.join(tmp, "built")
        man = A.open_toolkit(GAME).build(
            {"intent": "unit.stat", "unit": 83, "stat": "hit_points", "value": 1000},
            out, title="repair suite probe", author="dsh", overwrite=True)
        built_dat = os.path.join(man["mod_dir"], R.DAT_REL)
        got = R.check(built_dat, GAME)
        c = got.get("counts") or {}
        check(got.get("verdict") == R.AUTO, "one edited value reads as auto",
              got.get("verdict"))
        check(c.get("unit_changes", 0) >= 1, "and the change is counted", c)
        check(c.get("units_added") == 0 and c.get("techs_added") == 0,
              "and nothing is claimed about added records", c)
        rows = got.get("changes") or []
        check(any(r.get("field") == "hit_points" and r.get("to") == 1000 for r in rows),
              "and the edit is named with the number it was set to",
              [r for r in rows if r.get("field") == "hit_points"][:1])
        check(all(r.get("label") and not r["label"].startswith("hit_") for r in rows),
              "and every row carries a Chinese label, not the locator's key",
              sorted({r.get("label") for r in rows})[:4])
        check(R.describe(got).startswith("可以自动修"), "and the one-line summary agrees",
              R.describe(got))

        print()
        print("=== D. a generation mismatch outranks every other finding")
        fake = os.path.join(tmp, "fake_old.dat")
        raw_len, blob_len = _rewrite_version(SHIPPED, fake)
        got = R.check(fake, GAME)
        check(got.get("verdict") == R.IMPOSSIBLE,
              "a VER 7.8 file is impossible, not a list of edits", got.get("verdict"))
        check(got.get("same_generation") is False, "and the generations differ",
              (got.get("mod_version"), got.get("base_version")))
        check(got.get("mod_version") == "VER 7.8", "and the mod's own version is read",
              got.get("mod_version"))
        check(any("换代" in r for r in (got.get("reasons") or [])),
              "and the reason names the format generation, not an offset",
              got.get("reasons"))
        check(R.describe(got).startswith("不能自动修"), "and the summary refuses too",
              R.describe(got))

        print()
        print("=== E. whatever is installed here, every row gets a verdict")
        from aoe2mod.game import locations as GL
        prof = GL.find_profile_root()
        rows = R.scan_installed(prof, GAME, limit=5)
        print("    mods with their own .dat: %d" % len(rows))
        # Deliberately no count assertion: a different machine has a different
        # number of mods, and a suite that demands one is a suite that lies.
        check(all(r.get("name") for r in rows), "every row names its mod")
        check(all(r.get("verdict") in ("identical", R.AUTO, R.MANUAL, R.IMPOSSIBLE, "no_dat")
                  for r in rows), "every verdict is one of the five",
              sorted({r.get("verdict") for r in rows}))
        # This assertion started life as `all(... or True)`, which is true for
        # every possible value -- a check that cannot fail is not a check.  The
        # real invariant: the SCANNER reports facts, and the one-line summary is
        # added by whoever shows it (Toolkit.repair_check does), so a caller that
        # wants raw data is not handed pre-chewed prose.
        check(all("summary" not in r for r in rows),
              "the scanner returns facts, not the screen's one-liner",
              [r.get("summary") for r in rows if "summary" in r][:2])

        print()
        print("=== F. a repair carries what the author shipped beside the .dat")
        # Measured 2026-10-23: 14 of the 16 installed mods that ship a .dat also
        # ship other files (WAIFor Arcade: 688 DRS, 357 MB).  install_mod does
        # rmtree + copytree, so a rebuilt folder holding only info.json + .dat
        # would delete the art.  This section builds its own source folder so it
        # does not depend on what this machine happens to have installed.
        src = os.path.join(tmp, "author_mod")
        os.makedirs(os.path.join(src, "resources", "zh", "strings", "key-value"))
        os.makedirs(os.path.join(src, "resources", "_common", "dat"))
        os.makedirs(os.path.join(src, "resources", "_common", "drs", "graphics"))
        _w(os.path.join(src, "info.json"), b'{"Title":"author mod"}')
        _w(os.path.join(src, "thumbnail.png"), b"\x89PNG-shim")
        _w(os.path.join(src, R.DAT_REL), b"OLD-DAT-BYTES")
        _w(os.path.join(src, "resources", "zh", "strings", "key-value",
                        "key-value-modded-strings-utf8.txt"), b'1 "\x61\x62\x63"')
        _w(os.path.join(src, "resources", "_common", "drs", "graphics",
                        "unit.sld"), b"SLDDATA")
        dst = os.path.join(tmp, "rebuilt_mod")
        os.makedirs(dst)
        _w(os.path.join(dst, "info.json"), b'{"Title":"rebuilt"}')
        got = R.carry_over(src, dst)
        copied = got["copied"]
        check(any(p.endswith("key-value-modded-strings-utf8.txt") for p in copied),
              "the author's text table came over", copied)
        check(any(p.endswith(".sld") for p in copied),
              "and so did the art", copied)
        check(not any(p.lower().endswith("empires2_x2_p1.dat") for p in copied),
              "the old .dat did not come over", copied)
        check("info.json" not in copied and not any(p.startswith("thumbnail") for p in copied),
              "the new folder keeps its own manifest and thumbnail", copied)
        check(sorted(p for p in got["skipped"] if p.lower().endswith(".dat"))
              == [R.DAT_REL.replace(os.sep, "/")],
              "and both decisions are reported, not silent", got["skipped"])
        with open(os.path.join(dst, "info.json"), "rb") as fh:
            check(fh.read() == b'{"Title":"rebuilt"}',
                  "the old info.json did not overwrite the new one")
        # Read the copied file through a guard, not with a bare open().  A bare
        # open() raises FileNotFoundError when the copy never happened, and a
        # raised exception is a CRASH: the suite exits non-zero with no FAIL line,
        # which reads like a broken harness rather than like a broken product.
        # The first version of this section did exactly that, and the reverse
        # validation could not tell "the check failed" from "the test died".
        art = os.path.join(dst, "resources", "_common", "drs", "graphics", "unit.sld")
        if os.path.isfile(art):
            with open(art, "rb") as fh:
                check(fh.read() == b"SLDDATA", "and the copied file is byte for byte")
        else:
            check(False, "and the copied file is byte for byte",
                  "the file is not there at all: " + art)

        print()
        if FAILS:
            print("REPAIR: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
            return 1
        print("REPAIR: IDENTICAL, MISSING, AUTO AND CROSS-GENERATION ARE ALL NAMED")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
