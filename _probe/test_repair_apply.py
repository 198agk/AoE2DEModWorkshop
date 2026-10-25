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
import io
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aoe2mod.api as A
import aoe2mod.repair as R
from aoe2mod.game import locations as G
from aoe2mod.mod import emitter as E2
from aoe2mod.game import ddstex as DD

HERE_DIR = os.path.dirname(os.path.abspath(__file__))

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
        print("=== D. a repair does not rebuild the shape that draws nothing")
        # An author's folder can hold a `widgetui` layer next to its `.dat`.  Copying it
        # verbatim would put the tables back into the data half, the one arrangement
        # measured not to draw (2026-10-24: five blank boxes inside one folder, one
        # drawn checkerboard after splitting).  So build that shape, repair it, and read
        # where the tables ended up on disk.
        # The UI half is BUILT here rather than borrowed from an earlier round's
        # output directory: a fixture that lives in `_probe/out_*` disappears the
        # moment someone cleans the workspace, and the failure then reads like a
        # product bug.  One unit.create with an icon goes through the same emitter
        # the player's own build uses, so the layer is genuine.
        _fixture_icon = os.path.join(tmp, "fixture_icon.png")
        _iw = _ih = 64
        _pix = bytearray()
        for _y in range(_ih):
            for _x in range(_iw):
                _odd = ((_x // 8) + (_y // 8)) % 2
                _pix += bytearray((255, 0, 255, 255) if _odd
                                  else (0, 255, 255, 255))
        with io.open(_fixture_icon, "wb") as _fh:
            _fh.write(DD.encode_png(_iw, _ih, bytes(_pix)))
        _fixture = os.path.join(tmp, "fixture_ui_half")
        _man = tk.build({"intent": "unit.create", "donor": 83, "civ": "British",
                         "name": "repair fixture", "icon": _fixture_icon},
                        _fixture, title="dsh repair fixture", author="dsh",
                        description="", overwrite=True)
        ui_src = _man.get("ui_mod_dir")
        if not ui_src or not os.path.isdir(ui_src):
            check(False, "the product can produce a UI half to merge", ui_src)
        else:
            shaped = os.path.join(tmp, "both_layers")
            tk.build({"intent": "unit.stat", "unit": 109, "stat": "hit_points",
                      "value": 4000}, shaped, title="dsh repair both layers",
                     author="dsh", description="", overwrite=True)
            for src_root in (ui_src, shaped + E2.UI_FOLDER_SUFFIX):
                if not os.path.isdir(src_root):
                    continue
                for base, _dirs, files in os.walk(src_root):
                    rel = os.path.relpath(base, src_root)
                    for name in files:
                        if name == "info.json" or name.startswith("thumbnail"):
                            continue
                        dst_dir = shaped if rel == "." else os.path.join(shaped, rel)
                        if not os.path.isdir(dst_dir):
                            os.makedirs(dst_dir)
                        shutil.copyfile(os.path.join(base, name),
                                        os.path.join(dst_dir, name))
                if src_root != ui_src:
                    shutil.rmtree(src_root, ignore_errors=True)
            check(_widget_count(shaped) > 0,
                  "the fixture really carries both layers in one folder",
                  _widget_count(shaped))
            tk.install(shaped, name="dsh repair both layers",
                       title="dsh repair both layers", profile_root=prof,
                       overwrite=True)
            got3 = None
            try:
                got3 = tk.repair_apply("dsh repair both layers", profile_root=prof)
            except Exception as exc:                   # noqa: BLE001
                check(False, "a mod with both layers is repaired without raising",
                      "%s: %s" % (type(exc).__name__, exc))
            if got3 is not None:
                man3 = got3.get("manifest") or {}
                check(_widget_count(man3.get("mod_dir")) == 0,
                      "the rebuilt data half carries no widgetui",
                      _widget_count(man3.get("mod_dir")))
                check(_widget_count(man3.get("ui_mod_dir")) > 0,
                      "and the tables went to a second mod instead",
                      (man3.get("ui_mod_dir"),
                       _widget_count(man3.get("ui_mod_dir"))))
                rows3 = [r for r in G.list_mods(prof)
                         if str(r.get("title") or "").startswith("dsh repair both layers")]
                counts = sorted(_widget_count(r.get("path")) for r in rows3)
                check(len(counts) == 2 and counts[0] == 0,
                      "both halves are installed, one with the tables and one without",
                      counts)

        print()
        if FAILS:
            print("REPAIR APPLY: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
            return 1
        print("REPAIR APPLY: A MOD IS REBUILT FROM THE SHIPPED DATA, ITS OTHER FILES "
              "SURVIVE, AND THE RESULT IS INSTALLED")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _widget_count(path):
    """How many `widgetui/` files a folder holds (-1 when it is not there)."""
    if not path or not os.path.isdir(path):
        return -1
    n = 0
    for base, _dirs, files in os.walk(path):
        for name in files:
            rel = os.path.relpath(os.path.join(base, name), path)
            if rel.replace(os.sep, "/").startswith("widgetui/"):
                n += 1
    return n


if __name__ == "__main__":
    sys.exit(main())
