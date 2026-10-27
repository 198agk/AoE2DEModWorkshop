# -*- coding: utf-8 -*-
"""Assemble the installed folder for the NATIVE build: no Python runtime.

What changed from the previous version
--------------------------------------
The shell used to spawn `runtime\\python.exe`, so the folder carried a 34.5 MB
stripped CPython and 38 `.py` files.  The engine is a Rust library now, linked
into the exe, so `runtime\\` is gone and `app\\` holds only what is genuinely
data:

    aoe2-mod-workshop.exe     the shell AND the engine, one image
    WebView2Loader.dll        the loader the exe cannot start without
    app\\aoe2mod\\ui\\static\\   index.html -- the screen, editable
    app\\aoe2mod\\schema\\      intents.json etc -- the format description,
                              editable, which is the project's standing rule
    README.txt

`aoe2mod/ui/static/index.html` and `aoe2mod/schema/*.json` stay OUTSIDE the
binary on purpose: they are what the owner edits constantly, and a copy inside
the exe would mean a recompile per wording change.
"""
import argparse
import io
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DEFAULT_OUT = r"D:\Software\AI\AoE2ModWorkshop"
EXE = r"D:\Software\AI\AGE2\desktop\src-tauri\target\release\aoe2-mod-workshop.exe"
LOADER_DLL = "WebView2Loader.dll"

README = """帝国时代 2 决定版 · 模组工坊
===============================

怎么启动
--------
双击 aoe2-mod-workshop.exe。没有控制台窗口，不用装 Python，也不用装别的东西。

它需要什么
----------
1. 本机的《帝国时代 2 决定版》（Steam 版）。第一次启动会自动找游戏目录；
   找不到时可以用环境变量指定：

       set AOE2MOD_GAME_ROOT=D:\\Games\\Steam\\steamapps\\common\\AoE2DE

2. 生成的模组会装进游戏自己的 profile 目录，然后在游戏的「创建游戏」界面
   的「数据模组：」下拉框里选它。

数据模组只在「数据模组」下拉框里选，不需要在模组界面里「启用」开关。

文件夹里都是什么
----------------
  aoe2-mod-workshop.exe   外壳 + 引擎（同一个程序，读 .dat 的代码在里面）
  WebView2Loader.dll      Windows 的 WebView2 装载器，缺了程序起不来
  app\\aoe2mod\\ui\\static\\  界面（index.html），可以直接改
  app\\aoe2mod\\schema\\     格式说明（JSON），可以直接改
  %TEMP%\\aoe2-mod-workshop.log   启动日志，出问题先看它

改界面或改说明不用重新编译：那两个目录就在外面，改完重启程序即可。

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


def copy_app(dst):
    """Only the two directories the exe reads at run time, and only their data."""
    os.makedirs(dst, exist_ok=True)
    pairs = [
        ("aoe2mod/ui/static", "aoe2mod/ui/static"),
        ("aoe2mod/schema", "aoe2mod/schema"),
    ]
    for rel_src, rel_dst in pairs:
        src = os.path.join(REPO, rel_src)
        if not os.path.isdir(src):
            print("REFUSING: missing %s" % src)
            return None
        out = os.path.join(dst, rel_dst)
        shutil.copytree(
            src, out,
            # `__init__.py` too: it is a Python package marker, and this folder
            # ships no Python.  Leaving it in would make the "no .py" assertion
            # below fail on a file that could never be imported anyway --
            # which is exactly what happened the first time this ran.
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo",
                                          "__init__.py"))
    return size_of(dst)


def main(argv=None):
    ap = argparse.ArgumentParser(description="assemble the native installed folder")
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)

    out = os.path.abspath(args.out)
    if not os.path.isfile(EXE):
        print("REFUSING: the shell is not built at %s" % EXE)
        return 1
    dll_src = os.path.join(os.path.dirname(EXE), LOADER_DLL)
    if not os.path.isfile(dll_src):
        print("REFUSING: %s is not next to the release exe." % LOADER_DLL)
        print("          Without it the exe dies in the loader with a modal")
        print("          dialog and writes no log line at all.")
        return 1
    if os.path.isdir(out) and os.listdir(out):
        if not args.force:
            print("REFUSING: %s is not empty (pass --force)" % out)
            return 1
        shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out, exist_ok=True)

    shutil.copy2(EXE, os.path.join(out, "aoe2-mod-workshop.exe"))
    shutil.copy2(dll_src, os.path.join(out, LOADER_DLL))
    app_stats = copy_app(os.path.join(out, "app"))
    if app_stats is None:
        return 1
    with io.open(os.path.join(out, "README.txt"), "w",
                 encoding="utf-8", newline="\r\n") as fh:
        fh.write(README)

    exe_mb = os.path.getsize(os.path.join(out, "aoe2-mod-workshop.exe")) / (1024.0 ** 2)
    total_mb, total_n = size_of(out)
    print("shell    %7.1f MB  (engine linked in)" % exe_mb)
    print("app      %7.1f MB  %5d files" % (app_stats[0] / (1024.0 ** 2), app_stats[1]))
    print("TOTAL    %7.1f MB  %5d files  -> %s" % (total_mb / (1024.0 ** 2), total_n, out))

    for name in ("aoe2-mod-workshop.exe", LOADER_DLL):
        if not os.path.isfile(os.path.join(out, name)):
            print("FAILED: %s did not land in %s" % (name, out))
            return 1
    print("loader   %s: %d B" % (LOADER_DLL,
                                 os.path.getsize(os.path.join(out, LOADER_DLL))))

    # The claim is "no Python needed".  Assert it rather than trusting the copy:
    # if a python.exe or a .py ever reappears here, this is the place to notice.
    py_exes = []
    py_files = []
    for base, _dirs, files in os.walk(out):
        for f in files:
            if f.lower().endswith(".py"):
                py_files.append(os.path.join(base, f))
            if f.lower().startswith("python") and f.lower().endswith(".exe"):
                py_exes.append(os.path.join(base, f))
    print("python exes: %d   .py files: %d" % (len(py_exes), len(py_files)))
    if py_exes or py_files:
        print("FAILED: this folder is supposed to need no Python")
        for p in (py_exes + py_files)[:5]:
            print("   %s" % p)
        return 1
    print("BUNDLE: %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
