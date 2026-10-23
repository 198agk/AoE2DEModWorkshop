# -*- coding: utf-8 -*-
"""`repair_apply` rebuilds a mod from today's data and puts it back.

Two failures look like success and this file exists for both:

  1. the rebuilt `.dat` can carry the wrong numbers -- the mod still loads, so
     nothing complains;
  2. the reinstall can delete the author's other files -- `install_mod` does
     rmtree + copytree, and 14 of the 16 mods measured on this machine ship
     more than info.json + .dat (WAIFor Arcade: 688 DRS, 357 MB).

The mod under test is the PRODUCT's own output, because that is the one case
where the expected `.dat` is known exactly: replay should reproduce it byte for
byte.  Everything runs in a throwaway profile -- a test that reads or writes the
player's real mod list is a test that reports whatever that player happens to
have installed.
"""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aoe2mod.api as A
import aoe2mod.repair as R

FAILS = []


def check(ok, label, detail=""):
    print(("  ok   " if ok else "  FAIL ") + label
          + ((" :: " + str(detail)) if detail else ""))
    if not ok:
        FAILS.append(label)
    return ok


def _refused(fn):
    try:
        fn()
    except Exception as exc:
        return str(exc)
    return None


def main():
    tk = A.open_toolkit()
    tmp = tempfile.mkdtemp(prefix="repair_apply_")
    try:
        print("=== A. a mod the product built, repaired")
        out = os.path.join(tmp, "author_out")
        man = tk.build({"intent": "unit.stat", "unit": 83, "stat": "hit_points",
                        "value": 40}, out, title="dsh repair probe",
                       author="dsh", description="author's own mod", overwrite=True)
        author_dat = open(os.path.join(man["mod_dir"], R.DAT_REL), "rb").read()

        # A file the author shipped beside the .dat.  Its survival is the whole
        # point of carry_over, so the fixture must really contain one.
        extra_rel = os.path.join("resources", "zh", "strings", "key-value",
                                "key-value-modded-strings-utf8.txt")
        extra = os.path.join(man["mod_dir"], extra_rel)
        os.makedirs(os.path.dirname(extra), exist_ok=True)
        with open(extra, "wb") as fh:
            fh.write('9001 "作者自己的文本"'.encode("utf-8"))

        prof = os.path.join(tmp, "profile")
        account = "12345678901234567"
        os.makedirs(os.path.join(prof, account, "profile"))
        os.makedirs(os.path.join(prof, account, "mods", "local"))
        tk.install(man["mod_dir"], name="dsh repair probe",
                   title="dsh repair probe", profile_root=prof, overwrite=True)
        placed = os.path.join(prof, account, "mods", "local", "dsh repair probe")
        check(os.path.isfile(os.path.join(placed, extra_rel)),
              "the fixture really ships a file beside the .dat")

        got = tk.repair_apply("dsh repair probe", out_dir=os.path.join(tmp, "rebuilt"),
                              author="dsh", profile_root=prof)
        check(got.get("verdict") == R.AUTO, "the verdict is auto", got.get("verdict"))
        check(got.get("replayed") == 1, "one intent replays the edit",
              got.get("replayed"))
        check(bool(got.get("installed")), "the builder reports the mod installed")

        new_dat = open(os.path.join(placed, R.DAT_REL), "rb").read()
        # Byte identity is the strong claim: the same intents on the same base
        # data must reproduce the same stream, not merely the same value.
        check(new_dat == author_dat, "the reinstalled .dat is byte-identical to the author's",
              "%d vs %d" % (len(new_dat), len(author_dat)))
        check(os.path.isfile(os.path.join(placed, extra_rel)),
              "the author's other file survived the reinstall")
        with open(os.path.join(placed, extra_rel), "rb") as fh:
            check(fh.read() == '9001 "作者自己的文本"'.encode("utf-8"),
                  "and its bytes are unchanged")
        copied = (got.get("carried") or {}).get("copied") or []
        check(any(p.endswith("key-value-modded-strings-utf8.txt") for p in copied),
              "the carried list names it", copied)
        check(not any(p.lower().endswith("empires2_x2_p1.dat") for p in copied),
              "and the old .dat was not carried over", copied)

        print()
        print("=== B. an identical mod is not dressed up as a repair")
        # An "identical" mod cannot be produced by the product: every intent it
        # accepts CHANGES something (setting a field to the value it already has
        # is refused as a no-op).  Identical mods exist in the wild anyway --
        # they are carrier mods, a copy of the shipped .dat inside a folder.  So
        # the fixture is built by hand, which is also what such a mod really is.
        noop_dir = os.path.join(tmp, "noop_mod")
        os.makedirs(os.path.join(noop_dir, os.path.dirname(R.DAT_REL)))
        with open(os.path.join(noop_dir, "info.json"), "w", encoding="utf-8") as fh:
            fh.write('{"Title":"dsh repair noop","Author":"dsh",'
                     '"Description":"","CacheStatus":0}')
        base = open(os.path.join(tk.game_root, R.DAT_REL), "rb").read()
        with open(os.path.join(noop_dir, R.DAT_REL), "wb") as fh:
            fh.write(base)
        tk.install(noop_dir, name="dsh repair noop", title="dsh repair noop",
                   profile_root=prof, overwrite=True)
        # Guarded on purpose: an identical mod has ZERO intents, so if the early
        # return is ever removed the rebuild raises "这个组合里一句都没有".  A
        # raised exception is a crash -- exit 1 with no FAIL line -- and a crash
        # reads like a broken harness rather than like a broken product, so the
        # reverse validation could not tell the two apart.  Turn it into a FAIL.
        try:
            got2 = tk.repair_apply("dsh repair noop", profile_root=prof)
        except Exception as exc:
            got2 = None
            check(False, "an identical mod is repaired without raising",
                  "%s: %s" % (type(exc).__name__, exc))
        if got2 is None:
            raise SystemExit(1)
        check(got2.get("verdict") == R.IDENTICAL,
              "a mod whose .dat equals the shipped one reads as identical",
              got2.get("verdict"))
        check(got2.get("replayed") == 0 and got2.get("installed") is None,
              "and nothing is rebuilt or reinstalled",
              (got2.get("replayed"), got2.get("installed")))
        check(got2.get("carried") is None,
              "and no file is copied onto itself", got2.get("carried"))

        print()
        print("=== C. the refusals name what is missing")
        msg = _refused(lambda: tk.repair_apply("__no_such_mod__", profile_root=prof))
        check(msg is not None, "a name that is not installed is refused")
        check(bool(msg) and any("\u4e00" <= ch <= "\u9fff" for ch in (msg or "")),
              "and it is refused in Chinese", msg)

        print()
        if FAILS:
            print("REPAIR APPLY: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
            return 1
        print("REPAIR APPLY: A MOD IS REBUILT FROM THE SHIPPED DATA, ITS OTHER FILES "
              "SURVIVE, AND THE RESULT IS INSTALLED")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
