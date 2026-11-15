# -*- coding: utf-8 -*-
"""A stale offset table must stop the tool, not corrupt a file and say ok:true.

WHY THIS EXISTS
---------------
2026-10-28: Steam replaced `empires2_x2_p1.dat` (93,268,152 -> 93,272,287 bytes).
Both engines kept writing through offset tables measured from the OLD file --
every sampled `hit_points` offset was 4397 bytes off for civilisation 1 -- and
`/api/stat` answered `ok:true` for all of it.  A player would have shipped a mod
that changed a neighbouring field and called it a hit-point edit.

The guard is `aoe2mod/dat/datstamp.py`, called from `aoe2mod/api.py` BEFORE the
5-second parse so the loading screen can say why.  Three behaviours matter and
this suite pins all three:

  1. a stamp that exists and DISAGREES raises, and the sentence names both byte
     counts (a refusal that says "mismatch" without the numbers is unactionable);
  2. a stamp that was DECLARED but cannot be found is an error too -- falling
     back to "no stamp, carry on" would be the silent version of the same bug;
  3. no stamp anywhere is silent, because a development checkout legitimately
     has none and every repo suite runs from one.

The fourth assertion is about the SHIPPED folder, not the repo: `make_bundle.py`
must carry `app/_golden/dat_stamp.json`, or a player's copy runs with no guard at
all while the repository's copy is protected.  That is the split-brain this
project has already paid for twice.

Run:  python -X utf8 _probe/test_dat_stamp_guard.py
"""
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from aoe2mod.dat import datstamp as DS                       # noqa: E402

FAILS = []


def check(label, ok, detail=""):
    # The detail is a whole refusal sentence (200+ characters), so it is printed
    # only when the check FAILS: on a pass the label already says what held, and
    # a wall of duplicated prose hides the one line that did not.
    print("  %s %s%s" % ("ok  " if ok else "FAIL", label,
                         (" :: " + detail) if (detail and not ok) else ""))
    if not ok:
        FAILS.append(label)
    return ok


def DS_raw_sha(path):
    """sha256 of a table file, in 1 MiB chunks (stat_offsets.json is 19.6 MB)."""
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(1 << 20)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def eq(label, got, want):
    return check("%s :: %r" % (label, want) if got != want else label,
                 got == want, "" if got == want else "got %r" % (got,))


def write_stamp(path, raw_bytes, sha):
    doc = {"dat": {"raw_bytes": raw_bytes, "raw_sha256": sha}, "tables": {}}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh)


def main():
    tmp = tempfile.mkdtemp(prefix="aoe2mod-stamp-")
    good = os.path.join(tmp, "good.json")
    bad = os.path.join(tmp, "bad.json")
    RAW = b"\x00" * 4096
    HONEST = DS.raw_sha256(RAW)
    write_stamp(good, len(RAW), HONEST)
    # A stamp from the file Steam replaced: same shape, wrong sha.
    write_stamp(bad, 93268152, "82eb7d148f8c6ee53f4dfa93210c3ce7dfb63194b65692ae51"
                               "bfc780d62980fe")
    saved = os.environ.get(DS.STAMP_ENV)

    try:
        print("\n=== 1. a stamp that matches lets the parse through ===")
        os.environ[DS.STAMP_ENV] = good
        eq("no complaint", DS.mismatch(RAW, dat_display="test.dat"), None)
        eq("and check() returns True", DS.check(RAW), True)

        print("\n=== 2. a stamp that disagrees REFUSES, with both byte counts ===")
        os.environ[DS.STAMP_ENV] = bad
        why = DS.mismatch(RAW, dat_display="test.dat")
        check("it refuses", bool(why), str(why))
        why = why or ""
        check("the sentence names the size the tables were measured from",
              "93268152" in why, why)
        check("and the size of the data in hand", str(len(RAW)) in why, why)
        check("it names the sha of the tables' file", "82eb7d148f8c" in why, why)
        check("and the sha of the data in hand", HONEST[:12] in why, why)
        check("it says what breaks (writing at the wrong place)",
              u"\u6539\u5230\u522b\u7684\u4f4d\u7f6e" in why, why)
        check("and that the tool would have claimed success",
              "ok:true" in why, why)
        check("it ends with the command that fixes it",
              "make_dat_stamp.py" in why, why)
        try:
            DS.check(RAW)
            check("check() raises on a mismatch", False)
        except DS.StampError as exc:
            # `check` does not take a display name, so its sentence says
            # 「游戏数据」 where `mismatch(..., dat_display="test.dat")` said the
            # path.  The numbers are the part that must survive both.
            check("check() raises with the same diagnosis",
                  "93268152" in str(exc) and HONEST[:12] in str(exc), str(exc))

        print("\n=== 3. a DECLARED stamp that is missing does not become a shrug ===")
        gone = os.path.join(tmp, "not-there.json")
        os.environ[DS.STAMP_ENV] = gone
        # Two different situations, and the module distinguishes them:
        #   * a development checkout declares a path that has moved, and the
        #     repo's own `_golden/` is then still the right table -- falling
        #     through to it is correct, so this must NOT raise;
        #   * nothing exists anywhere and one was declared -- that is a folder
        #     that will write through tables nobody vouched for, and it raises.
        check("a moved declaration falls back to another real stamp",
              isinstance(DS.mismatch(RAW), str),
              "or None if the fallback table happens to match, both fine")
        try:
            DS.mismatch(RAW, stamp="")
            check("declared but nowhere at all raises", False)
        except DS.StampError as exc:
            check("it names the variable",
                  DS.STAMP_ENV in str(exc), str(exc))
            check("and it says why an absent table is dangerous",
                  "ok:true" in str(exc), str(exc))

        print("\n=== 4. no stamp anywhere is SILENT (a dev checkout has none) ===")
        os.environ.pop(DS.STAMP_ENV, None)
        # `stamp=""` is the module's own spelling for "there is no stamp
        # anywhere" (see `mismatch`'s docstring): nothing was declared, so there
        # is nothing to disagree with and the parse goes ahead.
        eq("no stamp means no complaint", DS.mismatch(RAW, stamp=""), None)
        check("and stamp_path() only reports a file that exists",
              DS.stamp_path() is None or os.path.isfile(DS.stamp_path()),
              str(DS.stamp_path()))

        print("\n=== 5. a stamp that will not parse is a refusal, not a pass ===")
        broken = os.path.join(tmp, "broken.json")
        with open(broken, "w", encoding="utf-8") as fh:
            fh.write("{not json at all")
        os.environ[DS.STAMP_ENV] = broken
        try:
            DS.mismatch(RAW)
            check("a broken stamp raises", False)
        except DS.StampError as exc:
            check("the sentence names the file and the parse failure",
                  "broken.json" in str(exc), str(exc))
        blank = os.path.join(tmp, "blank.json")
        with open(blank, "w", encoding="utf-8") as fh:
            fh.write("{}")
        os.environ[DS.STAMP_ENV] = blank
        try:
            DS.mismatch(RAW)
            check("a stamp with no sha raises", False)
        except DS.StampError as exc:
            check("and names the missing key",
                  "raw_sha256" in str(exc), str(exc))

        print("\n=== 6. the guard is wired into the load path, before the parse ===")
        import io
        api_src = io.open(os.path.join(ROOT, "aoe2mod", "api.py"),
                          encoding="utf-8").read()
        check("api.py calls datstamp.check", "datstamp as DS" in api_src
              and "DS.check(" in api_src)
        check("and the call is guarded, not swallowed",
              "except DS.StampError" in api_src and "raise" in api_src)
        # ORDER: the stamp must be checked before the cache is consulted, or a
        # cache built from the same wrong bytes papers over the mismatch.
        pos_stamp = api_src.find("DS.check(")
        pos_cache = api_src.find("parsecache as PC")
        check("the stamp is checked before the parse cache is used",
              -1 < pos_stamp < pos_cache, "%s vs %s" % (pos_stamp, pos_cache))

        print("\n=== 7. the SHIPPED folder carries the stamp ===")
        from _probe.make_bundle import DEFAULT_OUT, SCAFFOLDING
        app_golden = os.path.join(DEFAULT_OUT, "app", "_golden", "dat_stamp.json")
        if os.path.isdir(DEFAULT_OUT):
            check("the bundle has app/_golden/dat_stamp.json",
                  os.path.isfile(app_golden), app_golden)
            if os.path.isfile(app_golden):
                shipped = json.loads(io.open(app_golden, encoding="utf-8").read())
                here = json.loads(io.open(os.path.join(
                    ROOT, "_golden", "dat_stamp.json"), encoding="utf-8").read())
                eq("and it is the same stamp the repo measures against",
                   shipped.get("dat"), here.get("dat"))
                # THE TABLES THE STAMP VOUCHES FOR MUST MATCH IT.  A bundle can
                # carry a correct stamp and a 19.6 MB table measured from some
                # other `.dat` -- that is what happened (2026-11-12: repo
                # `21632d17…`, bundle `59e9ba56…`, and every shipped write landed
                # 27-36 bytes off with ok:true).  The stamp passing while the
                # table beside it contradicts it is the worst possible state, so
                # the shipped copy is hashed here, not assumed to be the repo's.
                want = shipped.get("tables") or {}
                golden_dir = os.path.join(DEFAULT_OUT, "app", "_golden")
                stale, absent = [], []
                for name, sha in sorted(want.items()):
                    if name in SCAFFOLDING:
                        continue
                    got_path = os.path.join(golden_dir, name)
                    if not os.path.isfile(got_path):
                        absent.append(name)
                        continue
                    got = DS_raw_sha(got_path)
                    if got != sha:
                        stale.append("%s: bundle %s… vs stamp %s…"
                                     % (name, got[:12], sha[:12]))
                check("every shipped table hashes to what the stamp says",
                      not stale, "; ".join(stale))
                # A table the stamp names but the folder does not hold means the
                # folder predates `copy_golden` copying tables at all.  It is not
                # a hash mismatch, so it does not fail here, but it is worth
                # saying out loud: the bundle is older than this rule.
                if absent:
                    print("  --   named by the stamp, not in this bundle yet"
                          " (rebuild it): %s" % ", ".join(absent))
        else:
            print("  --   no bundle at %s, skipping the shipped check" % DEFAULT_OUT)
            check("make_bundle.py copies the stamp", "copy_golden" in
                  io.open(os.path.join(HERE, "make_bundle.py"),
                          encoding="utf-8").read())
    finally:
        if saved is None:
            os.environ.pop(DS.STAMP_ENV, None)
        else:
            os.environ[DS.STAMP_ENV] = saved
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILS:
        print("DAT STAMP GUARD: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    print("DAT STAMP GUARD: A STALE TABLE STOPS THE TOOL WITH BOTH BYTE COUNTS, "
          "AND THE SHIPPED FOLDER CARRIES THE STAMP")
    return 0


if __name__ == "__main__":
    sys.exit(main())
