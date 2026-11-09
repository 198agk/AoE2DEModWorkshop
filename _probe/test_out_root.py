# -*- coding: utf-8 -*-
"""`_out_root()` must differ for the repo and for the shipped package.

Why this nail exists: measured 2026-11-02, `_out/AoE2ModWorkshop` had grown from
50.9 MB to **1.7 GB**.  `app/_mods_out/` held 77 test mods at 93 MB each, written
by suites that ran the exe without `AOE2MOD_BUILD_OUT`.  The cause is that for
the shipped copy, "three levels up from server.py" is `<bundle>/app` -- part of
what gets zipped and handed to a player.  The exe still starts, so nothing looked
wrong for days.
"""
import io
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))

# `_probe/run_suites.py` sets AOE2MOD_BUILD_OUT to keep concurrent runs apart, and
# that override outranks the path logic this file is about.  Clearing it here is
# what makes the three path checks measure the code rather than the runner; the
# override gets its own section at the end, where it is set on purpose.
os.environ.pop("AOE2MOD_BUILD_OUT", None)

src = io.open(os.path.join(REPO, "aoe2mod", "ui", "server.py"),
              encoding="utf-8").read()
fn = src[src.find("def _out_root"):src.find("def _safe_dir")]

fails = []


def check(ok, what, detail=""):
    print("%-5s %s%s" % ("ok" if ok else "FAIL", what,
                         "" if not detail else " :: " + str(detail)))
    if not ok:
        fails.append(what)


def out_root_for(fake_file):
    ns = {"__file__": fake_file, "os": os, "__name__": "probe"}
    exec(compile(fn, "<server>", "exec"), ns)
    return ns["_out_root"]()


# --- a source checkout stays in the repo ---------------------------------
got = out_root_for(os.path.join(REPO, "aoe2mod", "ui", "server.py"))
check(got == os.path.join(REPO, "_mods_out"),
      "a source checkout emits into the repo's own _mods_out", got)

# --- the shipped package emits BESIDE itself -----------------------------
tmp = tempfile.mkdtemp(prefix="outroot_")
try:
    bundle = os.path.join(tmp, "AoE2ModWorkshop")
    app = os.path.join(bundle, "app")
    os.makedirs(os.path.join(app, "aoe2mod", "ui"))
    os.makedirs(os.path.join(bundle, "runtime"))
    fake = os.path.join(app, "aoe2mod", "ui", "server.py")
    with open(fake, "w", encoding="utf-8") as fh:
        fh.write("# fixture\n")

    got2 = out_root_for(fake)
    check(got2 == os.path.join(bundle, "_mods_out"),
          "with runtime/ beside app/, output goes beside the bundle", got2)
    check(os.sep + "app" + os.sep not in got2 + os.sep
          and not got2.startswith(app + os.sep),
          "and never inside app/, which is what gets shipped", got2)

    # --- a copy of app/ WITHOUT runtime/ is a dev tree, not a package ----
    shutil.rmtree(os.path.join(bundle, "runtime"))
    got3 = out_root_for(fake)
    check(got3 == os.path.join(app, "_mods_out"),
          "without runtime/ beside it, it is not a package: old behaviour", got3)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# --- the env override still wins -----------------------------------------
tmp2 = tempfile.mkdtemp(prefix="outroot2_")
os.environ["AOE2MOD_BUILD_OUT"] = tmp2
try:
    got4 = out_root_for(os.path.join(REPO, "aoe2mod", "ui", "server.py"))
    check(got4 == os.path.abspath(tmp2),
          "AOE2MOD_BUILD_OUT still overrides everything", got4)
finally:
    os.environ.pop("AOE2MOD_BUILD_OUT", None)
    shutil.rmtree(tmp2, ignore_errors=True)

print("OUT ROOT: ALL PASSED" if not fails
      else "OUT ROOT: %d CHECK(S) FAILED -> %s" % (len(fails), fails))
sys.exit(1 if fails else 0)
