"""Assemble the installed layout: one folder, double-click, no external Python.

What it produces
----------------
    _out\\AoE2ModWorkshop\\  (the path lives in `_probe/_paths.py`)
        aoe2-mod-workshop.exe     ~5.5 MB   the Tauri shell
        runtime\\                  ~35 MB    stripped CPython 3.12.14
        app\\tools\\run_ui.py
        app\\aoe2mod\\             ~3 MB     engine (source only, no test output)
        README.txt                            how to start, what it needs

Why a stripped runtime and not the dsh one
------------------------------------------
Measured 2026-10-27: the dsh runtime is 347.4 MB / 7,463 files, and 294.4 MB of
that is `Lib\\site-packages` (numpy, opencv, onnxruntime, lxml, capstone...).
The engine imports only the standard library, so a copy with `site-packages`,
`tkinter`, `idlelib`, `test`, `ensurepip`, `venv`, `lib2to3`, `pydoc_data`,
`asyncio`, `unittest` removed weighs **34.5 MB / 583 files** and was verified to
import `aoe2mod.api` and answer `toolkit.version`.

Why the engine is copied without `tests/out`
--------------------------------------------
`aoe2mod\\` in the checkout is 49.4 MB, but 45.7 MB of that is four copies of
`empires2_x2_p1.dat` left behind by `aoe2mod/tests/`.  The shipping copy keeps
`aoe2mod/tests/*.py` (so the tool can run its own checks) and drops every
`out/` directory and every `__pycache__`.

Guard style: every copy is checked by size after it lands, and the whole thing
refuses to write into a non-empty target unless `--force` is given.
"""
import argparse
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import _paths as P

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DEFAULT_OUT = P.BUNDLE
EXE = P.EXE
RUNTIME_SRC = sys.prefix

# WebView2Loader.dll must sit beside the exe, and the failure mode when it is
# missing is the worst one this project has met: Windows shows a modal
# "系统错误 / 由于找不到 WebView2Loader.dll", the process stays alive doing
# nothing, and `%TEMP%\aoe2-mod-workshop.log` is created with ZERO bytes -- so
# every log-based probe reads `alive=True log=False` and concludes the app is
# fine.  Measured 2026-10-27.  The DLL lives next to the release exe, because
# the cargo build copies it there from the webview2 crate.
LOADER_DLL = "WebView2Loader.dll"

SKIP_DIRS = {
    "site-packages", "tkinter", "idlelib", "test", "ensurepip", "venv",
    "lib2to3", "pydoc_data", "turtledemo", "unittest", "asyncio",
    "multiprocessing", "concurrent", "distutils", "sqlite3", "curses", "dbm",
    "include", "libs", "tcl", "Scripts", "tests",
}
TOP_FILES = (
    "python.exe", "pythonw.exe", "python3.dll", "python312.dll",
    "vcruntime140.dll", "vcruntime140_1.dll",
)

README = """帝国时代 2 决定版 · 模组工坊
===============================

怎么启动
--------
双击 aoe2-mod-workshop.exe。没有控制台窗口，也不用装 Python。

它需要什么
----------
1. 本机的《帝国时代 2 决定版》（Steam 版）。第一次启动会自动找游戏目录；
   找不到时可以用环境变量指定：

       set AOE2MOD_ROOT=<本文件夹>\\app
       set AOE2MOD_GAME_ROOT=<这里填 AoE2DE 的安装目录>

2. 生成的模组会装进游戏自己的 profile 目录，然后在游戏的「创建游戏」界面
   的「数据模组：」下拉框里选它。

数据模组只在「数据模组」下拉框里选，不需要在模组界面里「启用」开关。

文件夹里都是什么
----------------
  aoe2-mod-workshop.exe   外壳（Tauri + WebView2）
  runtime\\                自带的 Python 3.12，只需要标准库
  app\\                    引擎与界面（aoe2mod\\ + tools\\）
  dat_archive\\           官方数据档案库（313 MB，见下）
  %TEMP%\\aoe2-mod-workshop.log   启动日志，出问题先看它

dat_archive\（官方数据档案库）
--------------------------------
游戏每更新一次，所有改过数值的数据模组就全部对不上号：文件里记的是
「第几条第几个字段」，补丁一动，那些位置就挪了。要把它搬过去，必须先
知道作者当初是照着哪一份官方数据改的 —— 也就是更新之前的那一份。

所以工具每次打开都会看一眼游戏本体，把当天的 empires2_x2_p1.dat 存一份
进来，按格式代（VER 8.9 / VER 8.8 / …）归档。这里现在有 53 份，跨 11 代，
最早到 2019 年 10 月发售前那次公测。

它不会自己变大：同一份文件只存一次（按 sha256 认），所以游戏没更新就不会多。
新装的人拿到这一包，第一次遇上补丁就能直接一键适配；自己从头攒的话，要等
第二次补丁才有「改之前」的那一份可对照。不要删它 —— 删了不会丢档（游戏本体
还在），但会丢掉历史，下次补丁就只能拒绝适配、让你手动指定基准。

这个目录只在工具自己的盘上，不进游戏，也不影响模组数量。

卸载
----
整个文件夹删掉即可。回收站里的模组请自己去清空。
"""


def _rmtree(path):
    """Delete `path` even when the checkout has read-only files in it.

    Measured 2026-11-11: `aoe2mod/ui/static/art/preview-girl.jpg` is checked in
    with mode 0555, `copy2` preserves that on Windows as FILE_ATTRIBUTE_READONLY,
    and `shutil.rmtree(..., ignore_errors=True)` then leaves the whole
    `app/aoe2mod/ui/static/art/` chain behind WITHOUT RAISING.  The next
    `copytree` died on `FileExistsError: app\\aoe2mod` -- a `--force` rebuild
    that reported success at every step it took and shipped nothing.
    So: clear the read-only bit and retry, then prove the directory is gone.
    """
    def onexc(func, target, exc):
        try:
            os.chmod(target, 0o777)
        except OSError:
            pass
        try:
            func(target)
        except OSError:
            pass

    if not os.path.isdir(path):
        return
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=onexc)
    else:
        shutil.rmtree(path, onerror=lambda f, t, e: onexc(f, t, e[1]))
    if os.path.isdir(path):
        raise SystemExit("FAILED: %s survived rmtree -- a file inside is locked "
                         "(close the app, or delete it by hand)" % path)


def size_of(path):
    total = 0
    count = 0
    for base, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(base, name))
                count += 1
            except OSError:
                pass
    return total, count


def copy_runtime(dst):
    """The runtime without any bytecode: 97 `.pyc` shipped from the source
    interpreter's own `Lib/<pkg>/__pycache__` (measured 2026-11-09) and 20 such
    folders came along through `copytree`.  They are stdlib caches, not ours,
    and a package whose only `.pyc` files are other people's is a package whose
    contents cannot be explained from what is inside it."""
    os.makedirs(dst, exist_ok=True)
    for name in TOP_FILES:
        src = os.path.join(RUNTIME_SRC, name)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(dst, name))
    no_pyc = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo")
    dlls = os.path.join(RUNTIME_SRC, "DLLs")
    if os.path.isdir(dlls):
        shutil.copytree(dlls, os.path.join(dst, "DLLs"), ignore=no_pyc)
    lib_src = os.path.join(RUNTIME_SRC, "Lib")
    lib_dst = os.path.join(dst, "Lib")
    os.makedirs(lib_dst, exist_ok=True)
    # The interpreter writes bytecode for the handful of modules it imports
    # before `site` runs: `encodings.aliases`, `encodings.utf_8`,
    # `encodings.__init__` and this file itself.  `tools/run_ui.py` cannot stop
    # those -- by the time it runs they are already written.  A `sitecustomize`
    # drops the count from 32 to 4 on the very first launch of the packaged exe
    # (measured 2026-11-11); the flag has to be set inside the interpreter's own
    # start-up for the rest to follow.
    with io.open(os.path.join(lib_dst, "sitecustomize.py"), "w",
                 encoding="utf-8", newline="\n") as fh:
        fh.write("# Written by make_bundle.py.  Stops the shipped interpreter from\n"
                 "# caching bytecode inside a folder that make_bundle.py has just\n"
                 "# certified as free of it.\n"
                 "import sys\n"
                 "sys.dont_write_bytecode = True\n")
    for entry in os.listdir(lib_src):
        if entry in SKIP_DIRS or entry == "__pycache__":
            continue
        src = os.path.join(lib_src, entry)
        out = os.path.join(lib_dst, entry)
        if os.path.isdir(src):
            shutil.copytree(src, out, ignore=no_pyc)
        else:
            shutil.copy2(src, out)
    # Bake those four caches here instead of letting the first player write them.
    # Same interpreter, same sources, same mtimes, so the files stay valid and a
    # later launch does not rewrite them: the folder a user receives is the
    # folder it stays.  `-c pass` is enough -- the writes happen before any code
    # of ours runs.
    py = os.path.join(dst, "python.exe")
    if os.path.isfile(py):
        subprocess.run([py, "-c", "pass"], cwd=dst, timeout=120,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return size_of(dst)


def copy_app(dst):
    """app/ = tools/ + aoe2mod/ with test output and caches removed."""
    os.makedirs(dst, exist_ok=True)
    shutil.copytree(
        os.path.join(REPO, "tools"), os.path.join(dst, "tools"),
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    pkg_src = os.path.join(REPO, "aoe2mod")
    pkg_dst = os.path.join(dst, "aoe2mod")

    def ignore(dirname, names):
        drop = []
        for name in names:
            if name == "__pycache__":
                drop.append(name)
            elif name == "out" and os.path.basename(dirname) == "tests":
                drop.append(name)
            elif name.endswith((".pyc", ".pyo")):
                drop.append(name)
        return drop

    shutil.copytree(pkg_src, pkg_dst, ignore=ignore)
    return size_of(dst)


#: Folders that are build OUTPUT, never source.  `_out_root()` in
#: `aoe2mod/ui/server.py` falls back to `<repo>/_mods_out`, and a shipped exe
#: resolves that relative to `cwd=<bundle>pp` -- so any suite that ran the
#: shipped exe without `AOE2MOD_BUILD_OUT` wrote 93 MB `.dat` folders straight
#: into the package.  Measured 2026-11-02: the 50.9 MB bundle had grown to
#: 1.7 GB, 1.2 GB of it `app/_mods_out` from 77 test runs.
_OUTPUT_DIRS = ("_mods_out", "_out", "_cache", "_build")


def stray_output(root):
    """`(relative path, bytes)` for every build-output folder under `root`."""
    found = []
    for base, dirs, _files in os.walk(root):
        for d in list(dirs):
            if d in _OUTPUT_DIRS:
                full = os.path.join(base, d)
                found.append((os.path.relpath(full, root).replace(os.sep, "/"),
                              size_of(full)[0]))
                dirs.remove(d)
    return found


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(1 << 20)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


#: Tables the stamp names that are NOT runtime data.  `unit_slots`, `unit_spans`,
#: `sprite_pairs` and `dat_baseline` are the artefacts of how the offsets were
#: measured -- 20 MB of scaffolding the shipped engine never opens (the Python
#: engine parses the `.dat` itself).  They stay out of the package on purpose;
#: `_probe/make_bundle_native.py:121` excludes three of the four by name
#: (`sprite_pairs` was never copied there in the first place).
SCAFFOLDING = frozenset(("dat_baseline.json", "unit_slots.json",
                         "unit_spans.json", "sprite_pairs.json"))

#: Tables both engines open that the stamp does not name, because the probes that
#: measure them predate it.  Small (208 KB together) and read at run time by
#: `desktop/aoe2mod-serve/src/{ai,civtree,unitfield}.rs`, so they travel even
#: though there is no hash to check them against.
NOT_IN_STAMP = ("ai_grammar.json", "civ_trees.json", "stat_mirrors.json")


def copy_golden(dst):
    """app/_golden/ = the stamp, plus every table the stamp vouches for.

    The stamp itself is not negotiable: `aoe2mod/dat/datstamp.py:74` looks for
    `<app>/_golden/dat_stamp.json` and `aoe2mod/api.py:253` refuses to parse data
    the tables were not measured from.  Without it a shipped folder has no guard
    at all, and the failure the guard exists for went like this -- 2026-10-28,
    Steam replaced the `.dat`, every sampled `hit_points` offset was 4397 bytes
    off for civilisation 1, and `/api/stat` answered ok:true.

    The tables are what went wrong later.  This function used to copy the stamp
    ALONE and leave whatever `stat_offsets.json` an earlier
    `_probe/ship_and_verify.py` had dropped beside it, so the shipped folder
    carried a 19.6 MB table measured from a different `.dat` than the stamp in
    the same folder vouched for (measured 2026-11-12: repo `21632d17…`, bundle
    `59e9ba56…`, 1,268,964 offsets displaced by 27-36 bytes).  A package whose
    stamp contradicts the table beside it is worse than one with no table: the
    guard passes and every stat write lands in the neighbouring field, with
    ok:true -- the exact bug the stamp was added to stop.

    So the tables travel WITH their stamp and are checked against it here: each
    stamp-named table in the repo is hashed, and a disagreement aborts the build
    instead of shipping the contradiction.  Scaffolding (see SCAFFOLDING) is not
    runtime data and is skipped.
    """
    out = os.path.join(dst, "_golden")
    os.makedirs(out, exist_ok=True)
    src = os.path.join(REPO, "_golden", "dat_stamp.json")
    if not os.path.isfile(src):
        return 0
    shutil.copy2(src, os.path.join(out, "dat_stamp.json"))
    stamp = json.loads(io.open(src, encoding="utf-8").read())
    want = stamp.get("tables") or {}
    disagree, shipped = [], 0
    for name in sorted(want):
        if name in SCAFFOLDING:
            continue
        table = os.path.join(REPO, "_golden", name)
        if not os.path.isfile(table):
            continue
        got = _sha256(table)
        if got != want[name]:
            disagree.append("%s: repo %s… vs stamp %s…"
                            % (name, got[:12], want[name][:12]))
            continue
        shutil.copy2(table, os.path.join(out, name))
        shipped += 1
    for name in NOT_IN_STAMP:
        src_table = os.path.join(REPO, "_golden", name)
        if os.path.isfile(src_table):
            shutil.copy2(src_table, os.path.join(out, name))
    if disagree:
        raise SystemExit(
            "FAILED: the stamp vouches for tables that do not match it.\n"
            "        Re-run the make_* probes, then _probe/make_dat_stamp.py:\n  "
            + "\n  ".join(disagree))
    names = [n for n in sorted(want) if n not in SCAFFOLDING
             and os.path.isfile(os.path.join(REPO, "_golden", n))]
    print("tables   %d hashed against the stamp: %s"
          % (shipped, ", ".join(names)))
    return os.path.getsize(os.path.join(out, "dat_stamp.json"))


#: The shelf of official .dat builds.  313 MB of blobs, and without them the
#: package cannot upgrade anything on a fresh machine: _load_pair() needs the
#: build a mod was made from, _warm can only save TODAY'S build, and the engine
#: refuses rather than guessing.  Shipping it is what makes "one click" true on
#: the first patch after install, so it travels with the package by default.
ARCHIVE_DIR = "dat_archive"
#: Small files the shelf is read by a human with.  The blobs are the product;
#: these are the index and the receipts.
#:
#: index.json is not a receipt -- it is the only place the BUILD dates live.
#: dat_archive.json answers "which .dat do I hold" and its first_seen is this
#: tool's own copy time, so shipping only that leaves the panel unable to say
#: when a generation went live (every row printed 2026-11-10, the day of the
#: bulk import, and the player rightly called it wrong).  Without it the panel
#: falls back to "存下于 <copy date>" instead of inventing a release date.
ARCHIVE_KEEP = ("dat_archive.json", "index.json", "README.md", "MANIFEST.csv",
                "SHA256SUMS.txt")


def copy_archive(dst):
    """<tool>/dat_archive/ = every archived build, so a fresh install can adapt."""
    src = os.path.join(REPO, ARCHIVE_DIR)
    if not os.path.isdir(src):
        print("archive  ABSENT at %s -- the package ships without a shelf, so"
              % src)
        print("         one-click adaptation refuses until the tool has seen"
              " two builds of the same generation (i.e. after one patch).")
        return 0, 0
    os.makedirs(dst, exist_ok=True)
    n = 0
    for name in sorted(os.listdir(src)):
        full = os.path.join(src, name)
        if not os.path.isfile(full):
            continue
        if name.endswith(".dat") or name in ARCHIVE_KEEP:
            shutil.copy2(full, os.path.join(dst, name))
            n += 1
    # Prove the count against the index rather than trusting the loop: a shelf
    # that ships 52 of 53 blobs still answers count: 53 and fails one mod.
    idx = os.path.join(src, ARCHIVE_DIR + ".json")
    try:
        with io.open(idx, "r", encoding="utf-8-sig") as fh:
            want = len((json.load(fh) or {}).get("entries") or {})
    except (IOError, OSError, ValueError):
        want = 0
    got = len([x for x in os.listdir(dst) if x.endswith(".dat")])
    if want and got != want:
        print("FAILED: the shelf has %d blobs, %d landed in %s" % (want, got, dst))
        return -1, got
    return size_of(dst)[0], got


def main(argv=None):
    ap = argparse.ArgumentParser(description="assemble the installed layout")
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--no-archive", action="store_true",
                    help="skip dat_archive/ (smaller package, but one-click "
                         "adaptation cannot carry a mod across its first patch)")
    ap.add_argument("--force", action="store_true",
                    help="delete the target first if it already has files")
    args = ap.parse_args(argv)

    out = os.path.abspath(args.out)
    if not os.path.isfile(EXE):
        print("REFUSING: the shell is not built at %s" % EXE)
        return 1
    # Refuse before writing anything: a bundle without this DLL is a folder
    # that shows a system-error dialog and logs nothing at all.
    dll_src = os.path.join(os.path.dirname(EXE), LOADER_DLL)
    if not os.path.isfile(dll_src):
        print("REFUSING: %s is not next to the release exe (%s)."
              % (LOADER_DLL, os.path.dirname(EXE)))
        print("          Without it the exe dies in the loader with a modal")
        print("          dialog and writes no log line at all.")
        return 1
    if not os.path.isdir(RUNTIME_SRC):
        print("REFUSING: no runtime at %s" % RUNTIME_SRC)
        return 1
    if os.path.isdir(out) and os.listdir(out):
        if not args.force:
            print("REFUSING: %s is not empty (pass --force to replace it)" % out)
            return 1
        _rmtree(out)
    os.makedirs(out, exist_ok=True)

    shutil.copy2(EXE, os.path.join(out, "aoe2-mod-workshop.exe"))
    # Beside the exe, not inside app\ or runtime\: the Windows loader searches
    # the directory of the image before anywhere else.
    shutil.copy2(dll_src, os.path.join(out, LOADER_DLL))
    rt_mb, rt_n = copy_runtime(os.path.join(out, "runtime"))
    app_mb, app_n = copy_app(os.path.join(out, "app"))
    stamp_bytes = copy_golden(os.path.join(out, "app"))
    arch_bytes, arch_n = ((0, 0) if args.no_archive
                          else copy_archive(os.path.join(out, ARCHIVE_DIR)))
    if arch_n < 0:
        return 1
    # Refuse to ship build output.  A package that carries its own `_mods_out`
    # ships 93 MB per test run, and the player's first build then lands beside
    # files that look like the tool's own state.
    strays = stray_output(os.path.join(out, "app"))
    if strays:
        total = sum(n for _p, n in strays)
        print("REFUSING: build output inside the package (%.1f MB)" % (total / (1024.0 ** 2)))
        for rel, n in strays[:8]:
            print("      %-40s %7.1f MB" % (rel, n / (1024.0 ** 2)))
        return 1
    with io.open(os.path.join(out, "README.txt"), "w",
                 encoding="utf-8", newline="\r\n") as fh:
        fh.write(README)

    exe_mb = os.path.getsize(os.path.join(out, "aoe2-mod-workshop.exe")) / (1024.0 ** 2)
    total_mb, total_n = size_of(out)
    print("runtime  %7.1f MB  %5d files" % (rt_mb / (1024.0 ** 2), rt_n))
    print("app      %7.1f MB  %5d files" % (app_mb / (1024.0 ** 2), app_n))
    print("shell    %7.1f MB" % exe_mb)
    print("TOTAL    %7.1f MB  %5d files  -> %s" % (total_mb / (1024.0 ** 2), total_n, out))

    # The DLL is the one file whose absence produces no log line, so check it
    # landed rather than trusting the copy above.
    for name in ("aoe2-mod-workshop.exe", LOADER_DLL):
        if not os.path.isfile(os.path.join(out, name)):
            print("FAILED: %s did not land in %s" % (name, out))
            return 1
    print("loader   %s beside the exe: %d B"
          % (LOADER_DLL, os.path.getsize(os.path.join(out, LOADER_DLL))))
    # The stamp is the other file whose absence is invisible: the shipped engine
    # would start, edit and write through tables that may no longer belong to the
    # player's data, and would say ok:true.  Say which case this is.
    print("strays   0 -- no build output inside app\\")
    print("archive  %7.1f MB  %3d builds -> %s"
          % (arch_bytes / (1024.0 ** 2), arch_n, ARCHIVE_DIR))
    print("stamp    %s" % ("_golden/dat_stamp.json %d B" % stamp_bytes
                           if stamp_bytes else
                           "ABSENT -- the stale-.dat guard will not run"))

    # ---- prove the bundled interpreter alone can import the bundled engine --
    py = os.path.join(out, "runtime", "python.exe")
    app = os.path.join(out, "app")
    # The second assertion is not decoration: `datstamp.stamp_path()` is the only
    # thing that stops a shipped folder from silently writing through tables that
    # no longer match the player's `.dat`, and it finds the file by walking up
    # from `cwd`.  A bundle whose stamp landed one directory too high would pass
    # an existence check on disk and still fail here, which is why the check runs
    # from inside the shipped layout.
    probe = subprocess.run(
        [py, "-X", "utf8", "-c",
         "import sys; sys.path.insert(0, r'%s'); "
         "from aoe2mod import api; "
         "from aoe2mod.intent import compiler as C; "
         "from aoe2mod.dat import datstamp as DS; "
         "n = len(C.load_schema()[0]['intents']); "
         "p = DS.stamp_path(); "
         "print('bundled ok: python', sys.version.split()[0], "
         "'intents', n, 'stamp', (p and __import__('os').path.basename(p)) or 'NONE')"
         % app],
        cwd=app, capture_output=True, text=True, timeout=180,
        # Without this the self-check imports the engine and leaves
        # `__pycache__` in the SHIPPING folder: measured 2026-11-09, 145 .pyc
        # across `app/` and `runtime/Lib/`, which the copy step had just been
        # careful to strip.  A fresh bundle went from 598 to 743 files for a
        # reason no log line mentioned.
        env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
    )
    ok = (probe.returncode == 0 and "bundled ok" in (probe.stdout or "")
          and "stamp dat_stamp.json" in (probe.stdout or ""))
    print("self-check  %s" % ("ok -- " + probe.stdout.strip() if ok
                             else "FAILED\n" + (probe.stderr or "")[-800:]))
    if not ok:
        return 1
    # The self-check runs the shipped interpreter, so this is the one place a
    # `.pyc` can appear after the copy step already dropped them.  Count instead
    # of trusting the env var above.
    # Two folders, two promises.  `app/` is our code and must stay clean -- that
    # is the 159-file / 28 MB regression this check was written for.  `runtime/`
    # belongs to CPython, which caches the four modules it imports before
    # `sitecustomize` can speak (measured 2026-11-11); counting those as a
    # packaging failure would mean the assertion can only pass on a folder
    # nobody has opened yet.
    leftover, runtime_caches = [], []
    for base, _dirs, files in os.walk(out):
        for name in files:
            if not name.endswith((".pyc", ".pyo")):
                continue
            rel = os.path.relpath(os.path.join(base, name), out)
            (runtime_caches if rel.split(os.sep)[0] == "runtime"
             else leftover).append(rel)
    if leftover:
        print("FAILED: %d bytecode files inside app/ (first: %s)"
              % (len(leftover), leftover[0]))
        return 1
    print("pyc      0 in app/ (%d CPython start-up caches under runtime/, baked at "
          "build time)" % len(runtime_caches))
    print("BUNDLE: %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
