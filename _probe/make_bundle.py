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
import io
import os
import shutil
import subprocess
import sys
import _paths as P

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DEFAULT_OUT = P.BUNDLE
EXE = P.EXE
RUNTIME_SRC = r"C:\Users\26913\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python"

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
       set AOE2MOD_GAME_ROOT=D:\\Games\\Steam\\steamapps\\common\\AoE2DE

2. 生成的模组会装进游戏自己的 profile 目录，然后在游戏的「创建游戏」界面
   的「数据模组：」下拉框里选它。

数据模组只在「数据模组」下拉框里选，不需要在模组界面里「启用」开关。

文件夹里都是什么
----------------
  aoe2-mod-workshop.exe   外壳（Tauri + WebView2）
  runtime\\                自带的 Python 3.12，只需要标准库
  app\\                    引擎与界面（aoe2mod\\ + tools\\）
  %TEMP%\\aoe2-mod-workshop.log   启动日志，出问题先看它

卸载
----
整个文件夹删掉即可。回收站里的模组请自己去清空。
"""


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
    for entry in os.listdir(lib_src):
        if entry in SKIP_DIRS or entry == "__pycache__":
            continue
        src = os.path.join(lib_src, entry)
        out = os.path.join(lib_dst, entry)
        if os.path.isdir(src):
            shutil.copytree(src, out, ignore=no_pyc)
        else:
            shutil.copy2(src, out)
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


def copy_golden(dst):
    """app/_golden/ = the files the shipped engine must read to refuse bad data.

    ONLY `dat_stamp.json`.  The folder next to it in the repo is 42 MB of offset
    tables that the Python engine never opens: it parses the `.dat` itself, and
    the tables are an artefact of how the offsets were MEASURED.  What the engine
    does need is the stamp, because `aoe2mod/dat/datstamp.py:74` looks for
    `<app>/_golden/dat_stamp.json` and `aoe2mod/api.py:253` refuses to parse data
    the tables were not measured from.

    Without this file a shipped folder has no stamp at all, and the guard that
    exists to stop a patched `.dat` from being written through stale offsets
    silently does nothing -- which is exactly the failure the guard was built for
    (2026-10-28: Steam replaced the `.dat`, every sampled `hit_points` offset was
    4397 bytes off for civilisation 1, and `/api/stat` answered ok:true).
    """
    out = os.path.join(dst, "_golden")
    os.makedirs(out, exist_ok=True)
    src = os.path.join(REPO, "_golden", "dat_stamp.json")
    if not os.path.isfile(src):
        return 0
    shutil.copy2(src, os.path.join(out, "dat_stamp.json"))
    return os.path.getsize(os.path.join(out, "dat_stamp.json"))


def main(argv=None):
    ap = argparse.ArgumentParser(description="assemble the installed layout")
    ap.add_argument("--out", default=DEFAULT_OUT)
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
        shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out, exist_ok=True)

    shutil.copy2(EXE, os.path.join(out, "aoe2-mod-workshop.exe"))
    # Beside the exe, not inside app\ or runtime\: the Windows loader searches
    # the directory of the image before anywhere else.
    shutil.copy2(dll_src, os.path.join(out, LOADER_DLL))
    rt_mb, rt_n = copy_runtime(os.path.join(out, "runtime"))
    app_mb, app_n = copy_app(os.path.join(out, "app"))
    stamp_bytes = copy_golden(os.path.join(out, "app"))
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
    leftover = []
    for base, _dirs, files in os.walk(out):
        for name in files:
            if name.endswith((".pyc", ".pyo")):
                leftover.append(os.path.join(base, name))
    if leftover:
        print("FAILED: %d bytecode files inside the package (first: %s)"
              % (len(leftover), leftover[0]))
        return 1
    print("pyc      0 -- the self-check ran with PYTHONDONTWRITEBYTECODE=1")
    print("BUNDLE: %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
