# -*- coding: utf-8 -*-
"""Build the shell in an ASCII path, with the source synced from the repo first.

Two constraints collide:

  * The repo lives at `D:\\Software\\AI\\Aoe2`, and mingw's `windres` cannot
    open `...\\Aoe2\\desktop\\src-tauri\\icons\\icon.ico` -- "Invalid argument",
    not "file not found". So the shell cannot be compiled in place.
  * Building somewhere else previously meant keeping a SECOND source tree, which
    silently drifted: the shipped exe was compiled from copies that stopped at
    four routes while the repo had nineteen.

So the ASCII build tree is not a copy that lives there; it is a copy that is
REPLACED from the repo on every build. Every synced tree is then checked by a
content fingerprint (file count + sha256 over name|size), because counting `.rs`
files said "ok" for two `ui/index.html` that differed by a whole day.
"""
import filecmp
import hashlib
import os
import shutil
import subprocess
import sys
import _paths as P

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESKTOP = os.path.join(REPO, "desktop")
BUILD = P.BUILD
MINGW = r"C:\Users\26913\AppData\Local\Temp\mingw\mingw64\bin"
CARGO = r"C:\Users\26913\.cargo\bin"

# Source dirs that must be identical between repo and build tree.
#
# `ui` is in this list because the shell INLINES desktop/ui/index.html at compile
# time (tauri-codegen). Leaving it out meant the build tree kept a 2026-10-26 copy
# of the splash page while the repo had today's: the exe shipped a page nobody
# could find in the repo, and `count_rs` below reported "ok" because neither side
# holds a single .rs file.
SYNC = ["aoe2mod-dat", "aoe2mod-serve", "src-tauri", "ui"]


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


def fingerprint(root):
    """(file count, sha256 over the sorted name|size list) for a source tree.

    Counting `.rs` files was the old check, and it is blind to every non-Rust
    file -- which is exactly what went wrong: `ui/` holds no `.rs` at all, so
    "repo 0 .rs, build 0 .rs, ok" printed while the two `index.html` differed by
    44 KB and a whole day. The shell inlines that page, so the difference shipped.
    """
    h = hashlib.sha256()
    n = 0
    for base, dirs, files in os.walk(root):
        for skip in ("target", "gen", "__pycache__", ".git"):
            if skip in dirs:
                dirs.remove(skip)
        for f in sorted(files):
            if f.endswith((".pyc", ".pyo")):
                continue
            p = os.path.join(base, f)
            try:
                size = os.path.getsize(p)
            except OSError:
                continue
            rel = os.path.relpath(p, root).replace(os.sep, "/")
            h.update(("%s|%d\n" % (rel, size)).encode("utf-8"))
            n += 1
    return n, h.hexdigest()


def diff_files(a, b):
    """Names (relative) present in one tree but not the other, or of other size."""
    seen = {}
    for root in (a, b):
        cur = {}
        for base, dirs, files in os.walk(root):
            for skip in ("target", "gen", "__pycache__", ".git"):
                if skip in dirs:
                    dirs.remove(skip)
            for f in files:
                if f.endswith((".pyc", ".pyo")):
                    continue
                p = os.path.join(base, f)
                try:
                    cur[os.path.relpath(p, root).replace(os.sep, "/")] = os.path.getsize(p)
                except OSError:
                    pass
        seen[root] = cur
    out = []
    for name in sorted(set(seen.get(a, {})) | set(seen.get(b, {}))):
        if seen.get(a, {}).get(name) != seen.get(b, {}).get(name):
            out.append(name)
    return out


def main():
    print("repo:", REPO)
    print("build:", BUILD)
    for name in SYNC:
        if not sync_one(name):
            return 1
        src = os.path.join(DESKTOP, name)
        dst = os.path.join(BUILD, name)
        na, ha = fingerprint(src)
        nb, hb = fingerprint(dst)
        flag = "ok" if ha == hb else "MISMATCH"
        print("  %-14s repo %4d files  build %4d files  %s"
              % (name, na, nb, flag))
        if ha != hb:
            for d in diff_files(src, dst)[:12]:
                print("      differs:", d)
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
