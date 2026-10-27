# -*- coding: utf-8 -*-
"""Build the shell in an ASCII path, with the source synced from the repo first.

Two constraints collide:

  * The repo lives at `D:\\Software\\AI\\帝国项目`, and mingw's `windres` cannot
    open `...\\帝国项目\\desktop\\src-tauri\\icons\\icon.ico` -- "Invalid argument",
    not "file not found". So the shell cannot be compiled in place.
  * Building somewhere else previously meant keeping a SECOND source tree, which
    silently drifted: the shipped exe was compiled from copies that stopped at
    four routes while the repo had nineteen.

So the ASCII build tree is not a copy that lives there; it is a copy that is
REPLACED from the repo on every build. `--stale` proves the sync happened by
comparing file counts before and after.
"""
import filecmp
import os
import shutil
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESKTOP = os.path.join(REPO, "desktop")
BUILD = r"D:\Software\AI\AGE2\desktop"
MINGW = r"C:\Users\26913\AppData\Local\Temp\mingw\mingw64\bin"
CARGO = r"C:\Users\26913\.cargo\bin"

# Source dirs that must be identical between repo and build tree.
SYNC = ["aoe2mod-dat", "aoe2mod-serve", "src-tauri"]


def sync_one(name):
    src = os.path.join(DESKTOP, name)
    dst = os.path.join(BUILD, name)
    if not os.path.isdir(src):
        print("REFUSING: missing source", src)
        return False
    # Keep the build tree's target/ and gen/ (cargo caches, generated schemas);
    # replace only tracked source.
    keep = {}
    for k in ("target", "gen"):
        p = os.path.join(dst, k)
        if os.path.isdir(p):
            keep[k] = p
    tmp = dst + ".old"
    if os.path.isdir(tmp):
        shutil.rmtree(tmp, ignore_errors=True)
    if os.path.isdir(dst):
        os.rename(dst, tmp)
    shutil.copytree(
        src, dst,
        ignore=shutil.ignore_patterns("target", "gen", "__pycache__", "*.pyc"))
    for k, p in keep.items():
        tp = os.path.join(dst, k)
        if os.path.isdir(tp):
            shutil.rmtree(tp, ignore_errors=True)
        if os.path.isdir(p):
            os.rename(p, tp)
    shutil.rmtree(tmp, ignore_errors=True)
    return True


def count_rs(root):
    n = 0
    for base, dirs, files in os.walk(root):
        if "target" in dirs:
            dirs.remove("target")
        n += sum(1 for f in files if f.endswith(".rs"))
    return n


def main():
    print("repo:", REPO)
    print("build:", BUILD)
    for name in SYNC:
        if not sync_one(name):
            return 1
        a = count_rs(os.path.join(DESKTOP, name))
        b = count_rs(os.path.join(BUILD, name))
        flag = "ok" if a == b else "MISMATCH"
        print("  %-14s repo %2d .rs  build %2d .rs  %s" % (name, a, b, flag))
        if a != b:
            print("REFUSING: the build tree is not the repo's source")
            return 1

    env = dict(os.environ)
    env["PATH"] = MINGW + os.pathsep + CARGO + os.pathsep + env.get("PATH", "")
    env.pop("CARGO_TARGET_DIR", None)
    print("building…")
    cargo_exe = os.path.join(CARGO, "cargo.exe")
    r = subprocess.run([cargo_exe, "build", "--release"],
                       cwd=os.path.join(BUILD, "src-tauri"), env=env)
    if r.returncode != 0:
        print("BUILD FAILED")
        return 1
    exe = os.path.join(BUILD, "src-tauri", "target", "release",
                       "aoe2-mod-workshop.exe")
    print("built:", exe, os.path.getsize(exe), "bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
